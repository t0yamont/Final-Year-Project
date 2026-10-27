"""Analytic constant-power straight, NOT a racing simulator or telemetry."""
import math
from .config import ConfigError, validate_config


def run_fixture(config):
    """Return exact segment endpoints for a lossless, straight-line point mass.

    P is total wheel-delivered power. d(v^3)/ds = 3P/m and
    dt = m*(v_next^2-v^2)/(2P). Battery draw is deployment*dt/efficiency.
    No drag, tyres, braking, cornering, harvesting or traction limit is modelled.
    A request needing more than the available battery is rejected, not projected.
    """
    validate_config(config)
    vehicle, initial = config["vehicle"], config["initial"]
    mass = vehicle["mass_kg"]
    speed = initial["speed_m_per_s"]
    energy = initial["energy_j"]
    elapsed = distance = 0.0
    records = []
    for index, segment in enumerate(config["segments"]):
        power = vehicle["base_power_w"] + segment["deployment_w"]
        length = segment["length_m"]
        try:
            next_speed = math.cbrt(speed**3 + 3 * power * length / mass)
            # Rationalised expression avoids cancellation when power approaches zero.
            duration = 3 * length * (next_speed + speed) / (2 * (next_speed**2 + next_speed * speed + speed**2))
            draw = segment["deployment_w"] * duration / vehicle["discharge_efficiency"]
            next_energy = energy - draw
            if not all(math.isfinite(x) for x in [next_speed, duration, draw, next_energy]):
                raise ConfigError(f"segment {index} overflows numeric range")
        except OverflowError as exc:
            raise ConfigError(f"segment {index} overflows numeric range") from exc
        if duration <= 0 or next_speed <= 0:
            raise ConfigError(f"segment {index} gives invalid motion")
        if next_energy < initial["terminal_reserve_j"] - 1e-9:
            raise ConfigError(f"segment {index} deployment exceeds usable energy; no depletion solver exists yet")
        distance += length
        elapsed += duration
        if not math.isfinite(distance) or not math.isfinite(elapsed):
            raise ConfigError(f"segment {index} overflows cumulative numeric range")
        records.append({"segment": index, "distance_m": distance,
                        "speed_in_m_per_s": speed, "speed_out_m_per_s": next_speed,
                        "duration_s": duration, "elapsed_s": elapsed,
                        "requested_deployment_w": segment["deployment_w"],
                        "executed_deployment_w": segment["deployment_w"],
                        "battery_draw_j": draw, "remaining_energy_j": next_energy,
                        "provenance": config["provenance"]})
        speed, energy = next_speed, next_energy
    return records
