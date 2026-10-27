import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from f1energy.config import ConfigError, load_config, validate_config
from f1energy.fixture import run_fixture
from f1energy.cli import verify


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config(ROOT / "configs/toy.json")

    def test_constant_power_against_independent_time_domain_identity(self):
        row = run_fixture(self.config)[0]
        vehicle = self.config["vehicle"]
        v0 = self.config["initial"]["speed_m_per_s"]
        power = vehicle["base_power_w"] + self.config["segments"][0]["deployment_w"]
        t = row["duration_s"]
        expected_speed = math.sqrt(v0**2 + 2 * power * t / vehicle["mass_kg"])
        self.assertAlmostEqual(row["speed_out_m_per_s"], expected_speed, places=10)
        # Simpson quadrature independently integrates v(t) for the travelled distance.
        count = 1000
        h = t / count
        speeds = [math.sqrt(v0**2 + 2 * power * j * h / vehicle["mass_kg"]) for j in range(count + 1)]
        distance = h / 3 * (speeds[0] + speeds[-1] + 4 * sum(speeds[1:-1:2]) + 2 * sum(speeds[2:-1:2]))
        self.assertAlmostEqual(distance, 100.0, places=8)

    def test_energy_efficiency_and_reproducibility(self):
        rows = run_fixture(self.config)
        self.assertEqual(rows, run_fixture(self.config))
        draw = sum(row["executed_deployment_w"] * row["duration_s"] / 0.9 for row in rows)
        self.assertAlmostEqual(rows[-1]["remaining_energy_j"], 400000 - draw)
        self.assertGreaterEqual(rows[-1]["remaining_energy_j"], 50000)

    def test_coasting_and_deployment_changes_motion(self):
        off = copy.deepcopy(self.config)
        for segment in off["segments"]:
            segment["deployment_w"] = 0
        self.assertGreater(run_fixture(off)[-1]["elapsed_s"], run_fixture(self.config)[-1]["elapsed_s"])
        off["vehicle"]["base_power_w"] = 0
        rows = run_fixture(off)
        self.assertAlmostEqual(rows[-1]["elapsed_s"], 300 / 30)
        self.assertAlmostEqual(rows[-1]["speed_out_m_per_s"], 30)
        self.assertEqual(rows[-1]["remaining_energy_j"], 400000)

    def test_invalid_config_values(self):
        for key, bad in [("mass_kg", 0), ("mass_kg", True), ("base_power_w", -1),
                         ("electrical_limit_w", float("inf")), ("discharge_efficiency", 1.1),
                         ("mass_kg", float("nan")), ("mass_kg", 10**1000)]:
            config = copy.deepcopy(self.config)
            config["vehicle"][key] = bad
            with self.subTest(key=key, bad=repr(bad)[:20]), self.assertRaises(ConfigError):
                validate_config(config)
        for value in [True, -1, 1.2]:
            config = copy.deepcopy(self.config)
            config["seed"] = value
            with self.assertRaises(ConfigError):
                validate_config(config)

    def test_schema_and_provenance_are_strict(self):
        mutations = [("provenance", "real"), ("schema_version", True), ("segments", [])]
        for key, value in mutations:
            config = copy.deepcopy(self.config)
            config[key] = value
            with self.assertRaises(ConfigError):
                validate_config(config)
        config = copy.deepcopy(self.config)
        config["vehicle"]["mystery_parameter"] = 1
        with self.assertRaises(ConfigError):
            validate_config(config)
        for field, value in [("length_m", 0), ("deployment_w", 40001)]:
            config = copy.deepcopy(self.config)
            config["segments"][0][field] = value
            with self.assertRaises(ConfigError):
                validate_config(config)

    def test_depletion_is_rejected_without_partial_simulation_claim(self):
        self.config["initial"]["energy_j"] = 50000
        with self.assertRaisesRegex(ConfigError, "no depletion solver"):
            run_fixture(self.config)
        self.config["initial"]["terminal_reserve_j"] = 50001
        with self.assertRaises(ConfigError):
            validate_config(self.config)

    def test_json_duplicates_and_nonfinite_constants(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            for content in ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}']:
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(ConfigError):
                    load_config(path)

    def test_manifest_hashes_and_overwrite_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            summary = verify(ROOT / "configs/toy.json", output)
            self.assertEqual(summary["status"], "completed")
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["seed"], 0)
            self.assertEqual(manifest["split_ids"], [])
            self.assertTrue(manifest["source"]["package_files_sha256"])
            for item in manifest["outputs"]:
                self.assertEqual(item["sha256"], hashlib.sha256((output / item["path"]).read_bytes()).hexdigest())
            with self.assertRaises(FileExistsError):
                verify(ROOT / "configs/toy.json", output)

    def test_cli_help_and_failure_exit(self):
        import os
        environment = dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONDONTWRITEBYTECODE="1")
        help_result = subprocess.run([sys.executable, "-m", "f1energy.cli", "--help"],
                                     env=environment, capture_output=True, text=True)
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("verify", help_result.stdout)
        bad = subprocess.run([sys.executable, "-m", "f1energy.cli", "verify", "--config", "missing.json", "--output", "unused"],
                             cwd=ROOT, env=environment, capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)
        self.assertNotIn("Traceback", bad.stderr)
        self.assertFalse((ROOT / "unused").exists())

    def test_educational_dp_matches_exhaustive_search(self):
        spec = importlib.util.spec_from_file_location("energy_allocation", ROOT / "learning/energy_allocation.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.dynamic_programming(), module.exhaustive())
        self.assertEqual(module.dynamic_programming(), (24, (0, 1, 1)))


if __name__ == "__main__":
    unittest.main()
