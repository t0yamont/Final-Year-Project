"""Periodic centreline geometry and conservative, closed-circuit speed limits.

Geometry is reconstructed, not a measured racing line. Independent lateral and
longitudinal acceleration limits are a point-mass approximation, not a tyre model.
"""
from dataclasses import dataclass
import math
import numpy as np
from numpy.polynomial import Polynomial
from scipy.integrate import quad
from scipy.interpolate import CubicSpline
from scipy.ndimage import gaussian_filter1d
from .event_power_lap import integrate_segment
from .power_lap import PowerState


def _positive(value, name, zero=False):
    if isinstance(value, (bool, np.bool_)) or not np.isscalar(value) or not np.isfinite(value) or value < 0 or (value == 0 and not zero):
        raise ValueError(f'{name} must be finite and {"nonnegative" if zero else "positive"}')
    return float(value)


@dataclass(frozen=True)
class CircuitGrid:
    parameter_m: np.ndarray  # N+1 periodic parameter boundaries; not exact arc length
    distance_m: np.ndarray   # N+1 integrated arc length boundaries
    xy_m: np.ndarray         # N+1, endpoint equals start
    curvature_per_m: np.ndarray
    max_abs_curvature_per_m: np.ndarray  # N cell maxima, including interior extrema
    cell_speed_cap_mps: np.ndarray

    @property
    def lengths_m(self):
        return np.diff(self.distance_m)


class PeriodicCentreline:
    def __init__(self, xy_m, smoothing_sigma_m=10., resample_spacing_m=5.):
        xy = np.asarray(xy_m, dtype=float)
        if xy.ndim != 2 or xy.shape[1] != 2 or len(xy) < 8 or not np.isfinite(xy).all():
            raise ValueError('require at least eight finite 2D vertices, without repeated endpoint')
        sigma = _positive(smoothing_sigma_m, 'smoothing sigma', zero=True)
        spacing = _positive(resample_spacing_m, 'resampling spacing')
        ds = np.linalg.norm(np.roll(xy, -1, axis=0) - xy, axis=1)
        if np.any(ds <= 1e-9):
            raise ValueError('duplicate consecutive vertices or repeated endpoint')
        self.source_length_m = float(ds.sum())
        self.smoothing_sigma_m = sigma
        self.signed_area_m2 = float(np.sum(xy[:, 0]*np.roll(xy[:, 1], -1)-xy[:, 1]*np.roll(xy[:, 0], -1))/2)
        n = max(8, math.ceil(self.source_length_m/spacing))
        self.knots = np.linspace(0., self.source_length_m, n+1)
        source_s = np.r_[0., np.cumsum(ds)]
        closed = np.vstack([xy, xy[0]])
        uniform = np.column_stack([np.interp(self.knots[:-1], source_s, closed[:, j]) for j in range(2)])
        if sigma:
            uniform = gaussian_filter1d(uniform, sigma/(self.source_length_m/n), axis=0, mode='wrap')
        self.spline = CubicSpline(self.knots, np.vstack([uniform, uniform[0]]), bc_type='periodic')
        # For k=C/D^(3/2), stationary curvature has 2*C'*D-3*C*D'=0.
        # Include every spline knot and real interior root, rather than hoping a
        # dense sample happens to hit each tight corner. Check nonzero tangents.
        candidates = list(self.knots)
        for i, width in enumerate(np.diff(self.knots)):
            px, py = [Polynomial(self.spline.c[:, i, j][::-1]).deriv() for j in range(2)]
            c = px*py.deriv()-py*px.deriv()
            d = px*px+py*py
            def roots_in(poly):
                return [float(z.real) for z in poly.roots() if abs(z.imag) < 1e-7 and 0 < z.real < width]
            if min(d(z) for z in [0., width]+roots_in(d.deriv())) <= 1e-12:
                raise ValueError('degenerate spline tangent')
            candidates.extend(self.knots[i]+z for z in roots_in(2*c.deriv()*d-3*c*d.deriv()))
        self.extrema_parameter_m = np.array(sorted(candidates))
        self.extrema_abs_curvature = np.abs(self.curvature(self.extrema_parameter_m))

    def curvature(self, parameter_m):
        first, second = self.spline(parameter_m, 1), self.spline(parameter_m, 2)
        return (first[..., 0]*second[..., 1]-first[..., 1]*second[..., 0])/np.sum(first*first, axis=-1)**1.5

    def grid(self, max_spacing_m=10., lateral_acceleration_mps2=20., max_speed_mps=95.):
        spacing = _positive(max_spacing_m, 'grid spacing')
        lateral = _positive(lateral_acceleration_mps2, 'lateral acceleration')
        ceiling = _positive(max_speed_mps, 'speed ceiling')
        edges = np.linspace(0., self.source_length_m, max(3, math.ceil(self.source_length_m/spacing))+1)
        lengths, maxima = [], []
        for left, right in zip(edges[:-1], edges[1:]):
            knots = self.knots[(self.knots > left) & (self.knots < right)]
            length, _ = quad(lambda t: float(np.linalg.norm(self.spline(t, 1))), left, right,
                             points=knots, epsabs=1e-8, epsrel=1e-10)
            lengths.append(length)
            mask = (self.extrema_parameter_m >= left) & (self.extrema_parameter_m <= right)
            maxima.append(max(float(np.max(np.abs(self.curvature([left, right])))),
                              float(np.max(self.extrema_abs_curvature[mask], initial=0.))))
        maxima = np.asarray(maxima)
        # Tiny inflation protects floating-point extremum/root error.
        maxima = maxima*(1+1e-10)+1e-14
        caps = np.minimum(ceiling, np.sqrt(lateral/np.maximum(maxima, 1e-30)))
        return CircuitGrid(edges, np.r_[0., np.cumsum(lengths)], self.spline(edges),
                           self.curvature(edges), maxima, caps)


def closed_braking_envelope(lengths_m, cell_speed_caps_mps, vehicle):
    """Largest periodic node envelope for friction braking plus quadratic drag.

    Cell caps hold everywhere within each cell. A node obeys BOTH adjacent cells.
    Backward bound is the exact solution used by the accepted event solver.
    This is an upper bound; forward acceleration feasibility is supplied by replay.
    """
    lengths, caps = np.asarray(lengths_m, dtype=float), np.asarray(cell_speed_caps_mps, dtype=float)
    if lengths.ndim != 1 or caps.shape != lengths.shape or len(lengths) < 3 or not np.isfinite(lengths).all() or not np.isfinite(caps).all() or np.any(lengths <= 0) or np.any(caps <= 0):
        raise ValueError('require matching positive finite cell lengths and caps, N >= 3')
    mass = _positive(vehicle.mass_kg, 'mass')
    brake = _positive(vehicle.friction_deceleration_m_per_s2, 'braking deceleration')
    drag = _positive(vehicle.drag_kg_per_m, 'drag', zero=True)
    q = np.minimum(caps, np.roll(caps, 1))**2
    for _ in range(len(q)+1):
        previous = q.copy()
        for i in range(len(q)-1, -1, -1):
            terminal = q[(i+1) % len(q)]
            if drag:
                exponent = 2*drag*lengths[i]/mass
                bound = math.inf if exponent > 700 else terminal*math.exp(exponent)+(mass*brake/drag)*math.expm1(exponent)
            else:
                bound = terminal+2*brake*lengths[i]
            q[i] = min(q[i], bound)
        if np.max(np.abs(q-previous)) <= 1e-10:
            return np.sqrt(np.r_[q, q[0]])
    raise RuntimeError('periodic braking envelope did not converge')


def simulate_circuit(grid, vehicle, initial_speed_mps, initial_energy_j, actions=0., reserve_j=0.,
                     sample_spacing_m=2., max_step_m=5., rtol=1e-9, atol=1e-9):
    """Replay a fixed per-cell policy; no speed clipping or energy reset at cells."""
    count = len(grid.lengths_m)
    actions = np.full(count, actions, dtype=float) if np.isscalar(actions) else np.asarray(actions, dtype=float)
    if actions.shape != (count,) or not np.isfinite(actions).all() or np.any((actions < 0) | (actions > 1)):
        raise ValueError('one action in [0,1] per cell required')
    envelope = closed_braking_envelope(grid.lengths_m, grid.cell_speed_cap_mps, vehicle)
    if initial_speed_mps > envelope[0]+1e-8:
        raise ValueError('initial speed exceeds closed-circuit braking envelope')
    state = PowerState(float(initial_speed_mps), float(initial_energy_j))
    nodes = [dict(position_m=0., speed_m_per_s=state.speed_m_per_s, energy_j=state.energy_j, elapsed_s=0.)]
    samples, events = [], []
    keys = ['battery_draw_j', 'electrical_work_j', 'base_work_j', 'drag_work_j',
            'friction_braking_work_j', 'kinetic_change_j', 'energy_residual_j']
    totals = dict.fromkeys(keys, 0.)
    largest_residual, max_cap_excess = 0., 0.
    for i, length in enumerate(grid.lengths_m):
        state, info = integrate_segment(vehicle, state, float(length), float(envelope[i+1]),
                         float(actions[i]), reserve_j=reserve_j, max_speed_m_per_s=float(grid.cell_speed_cap_mps[i]),
                         sample_spacing_m=sample_spacing_m, max_step_m=max_step_m, rtol=rtol, atol=atol)
        for key in keys:
            totals[key] += info[key]
        largest_residual = max(largest_residual, abs(info['energy_residual_j']))
        for row in info['samples']:
            row['cell_index'] = i
            max_cap_excess = max(max_cap_excess, row['speed_m_per_s']-grid.cell_speed_cap_mps[i])
        samples.extend(info['samples'])
        events.extend(dict(e, cell_index=i) for e in info['events'])
        nodes.append(dict(position_m=state.distance_m, speed_m_per_s=state.speed_m_per_s,
                          energy_j=state.energy_j, elapsed_s=state.elapsed_s))
    return dict(final_state=vars(state), duration_s=state.elapsed_s, totals=totals, nodes=nodes,
                samples=samples, events=events, braking_envelope_mps=envelope.tolist(),
                max_cell_energy_residual_j=largest_residual, max_sample_cap_excess_mps=max_cap_excess,
                speed_closure_error_mps=state.speed_m_per_s-initial_speed_mps,
                battery_closure_error_j=state.energy_j-initial_energy_j)


def periodic_speed_lap(grid, vehicle, initial_energy_j, actions=0., reserve_j=0., speed_tolerance_mps=1e-6,
                       **solver_options):
    """Shoot for equal start/end SPEED with fixed starting battery each trial.

    The resulting finite-energy lap is not a charge-sustaining repeated race lap.
    Battery is never reset during replay; only independent shooting trials restart.
    """
    from scipy.optimize import brentq
    _positive(speed_tolerance_mps, 'speed tolerance')
    _positive(vehicle.base_power_w, 'base power for periodic shooting')
    upper = float(closed_braking_envelope(grid.lengths_m, grid.cell_speed_cap_mps, vehicle)[0])
    cache = {}
    def trial(v):
        if v not in cache:
            cache[v] = simulate_circuit(grid, vehicle, v, initial_energy_j, actions, reserve_j,
                                        **solver_options)
        return cache[v]['speed_closure_error_mps']
    if abs(trial(upper)) <= speed_tolerance_mps:
        root = upper
    else:
        lower = min(1., upper/2)
        for _ in range(40):
            if trial(lower) >= 0:
                break
            lower /= 2
        else:
            raise RuntimeError('unable to bracket positive periodic speed')
        root = brentq(trial, lower, upper, xtol=speed_tolerance_mps/10)
    trial(root)
    result = cache[root]
    if abs(result['speed_closure_error_mps']) > speed_tolerance_mps:
        raise RuntimeError('periodic speed shooting failed tolerance')
    result['initial_speed_mps'] = root
    result['shooting_trials'] = len(cache)
    return result
