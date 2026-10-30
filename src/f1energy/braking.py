"""Open-path braking constraints under piecewise constant net deceleration."""
import math
from numbers import Real


def _number(value, label, positive=False):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f'{label} must be a real number')
    if not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError(f'{label} must be finite and {"positive" if positive else "nonnegative"}')
    return float(value)


def braking_envelope(distances_m, speed_limits_m_per_s, decelerations_m_per_s2,
                     terminal_speed_m_per_s=None):
    """Return maximum node speeds permitting downstream braking constraints.

    N+1 speed caps correspond to N positive segment lengths and N positive
    constant net deceleration magnitudes. The final optional speed is an upper
    bound, not an exact terminal-speed equality. Backward recurrence:
    v[i] = min(cap[i], sqrt(v[i+1]**2 + 2*a[i]*distance[i])).

    This is an open-path upper envelope, not a forward trajectory. It assumes
    braking can start immediately, net deceleration is available throughout a
    segment, and there are no reaction, jerk, grip variation or banking effects.
    It does not provide acceleration feasibility or closed-lap periodicity.
    """
    lengths = tuple(distances_m)
    caps = tuple(speed_limits_m_per_s)
    decels = tuple(decelerations_m_per_s2)
    if not lengths or len(caps) != len(lengths) + 1 or len(decels) != len(lengths):
        raise ValueError('require N positive lengths, N decelerations and N+1 speed caps, N >= 1')
    lengths = tuple(_number(x, 'distance', True) for x in lengths)
    decels = tuple(_number(x, 'deceleration', True) for x in decels)
    speeds = [_number(x, 'speed cap') for x in caps]
    if terminal_speed_m_per_s is not None:
        speeds[-1] = min(speeds[-1], _number(terminal_speed_m_per_s, 'terminal speed'))
    for i in range(len(lengths) - 1, -1, -1):
        # sqrt(a)*sqrt(s) avoids overflow in a*s for large finite inputs.
        braking_increment = math.sqrt(2.0) * math.sqrt(decels[i]) * math.sqrt(lengths[i])
        bound = math.hypot(speeds[i + 1], braking_increment)
        speeds[i] = min(speeds[i], bound)
    return tuple(speeds)
