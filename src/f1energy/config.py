"""Strict, SI-unit contract for the offline analytic straight fixture."""
import json
import math
from pathlib import Path


class ConfigError(ValueError):
    """The supplied configuration does not satisfy the fixture contract."""


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ConfigError(f"duplicate key: {key}")
        result[key] = value
    return result


def _constant(value):
    raise ConfigError(f"non-finite JSON constant: {value}")


def _keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ConfigError(f"{label} must contain exactly: {', '.join(expected)}")


def _number(value, label, minimum=0.0, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{label} must be a finite number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite or value < minimum or (positive and value == 0):
        raise ConfigError(f"{label} is outside its allowed range")


def load_config(path):
    config = json.loads(Path(path).read_text(encoding="utf-8-sig"),
                        object_pairs_hook=_object, parse_constant=_constant)
    validate_config(config)
    return config


def validate_config(config):
    _keys(config, ["schema_version", "provenance", "seed", "vehicle", "initial", "segments"], "config")
    if type(config["schema_version"]) is not int or config["schema_version"] != 1:
        raise ConfigError("schema_version must be integer 1")
    if config["provenance"] != "synthetic_analytic_straight":
        raise ConfigError("this command accepts only synthetic_analytic_straight provenance")
    if type(config["seed"]) is not int or not 0 <= config["seed"] < 2**32:
        raise ConfigError("seed must be an integer in [0, 2**32)")
    vehicle = config["vehicle"]
    _keys(vehicle, ["mass_kg", "base_power_w", "electrical_limit_w", "discharge_efficiency"], "vehicle")
    for field in ["mass_kg", "base_power_w", "electrical_limit_w", "discharge_efficiency"]:
        _number(vehicle[field], field, positive=field in ["mass_kg", "discharge_efficiency"])
    if vehicle["discharge_efficiency"] > 1:
        raise ConfigError("discharge_efficiency must be in (0, 1]")
    initial = config["initial"]
    _keys(initial, ["speed_m_per_s", "energy_j", "terminal_reserve_j"], "initial")
    for field in initial:
        _number(initial[field], field, positive=field == "speed_m_per_s")
    if initial["terminal_reserve_j"] > initial["energy_j"]:
        raise ConfigError("terminal reserve exceeds initial energy")
    if not isinstance(config["segments"], list) or not config["segments"]:
        raise ConfigError("segments must be a non-empty list")
    for index, segment in enumerate(config["segments"]):
        _keys(segment, ["length_m", "deployment_w"], f"segment {index}")
        _number(segment["length_m"], f"segment {index} length_m", positive=True)
        _number(segment["deployment_w"], f"segment {index} deployment_w")
        if segment["deployment_w"] > vehicle["electrical_limit_w"]:
            raise ConfigError(f"segment {index} exceeds electrical_limit_w")
