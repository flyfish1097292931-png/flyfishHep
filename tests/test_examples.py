"""Offline stdlib checks for the two public, exploratory examples.

Run from the repository root: python -B -m unittest discover -s tests -v
The tests invoke the example scripts directly; no flyfishhep CLI is required.
"""

import csv
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def load_example(name):
    path = EXAMPLES / name / "calculation.py"
    spec = importlib.util.spec_from_file_location("example_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class YangMillsTests(unittest.TestCase):
    def test_rk4_matches_integrated_one_loop_equation(self):
        path = EXAMPLES / "yang_mills_rg" / "calculation.py"
        self.assertTrue(path.is_file(), "the reviewed Yang-Mills entry point is missing")
        model = load_example("yang_mills_rg")
        for nc, nf in ((2, 0), (3, 3), (3, 6)):
            for t in (0.0, 1.0, 4.0, 8.0):
                with self.subTest(nc=nc, nf=nf, t=t):
                    g0 = 0.8
                    b0 = (11 * nc - 2 * nf) / 3
                    expected = 1.0 / math.sqrt(1.0 / g0**2 + b0 * t / (8 * math.pi**2))
                    actual = model.rk4_coupling(g0, nc, nf, t, 32)
                    self.assertLessEqual(abs(actual - expected), 1e-8)
                    self.assertAlmostEqual(model.analytic_coupling(g0, nc, nf, t), expected, places=14)
                    self.assertGreater(actual, 0.0)
                    self.assertLessEqual(actual, g0)

    def test_one_loop_input_domain_is_validated(self):
        model = load_example("yang_mills_rg")
        for args in ((0.0, 3, 0, 1.0, 8), (0.5, 0, 0, 1.0, 8), (0.5, 3, 17, 1.0, 8), (0.5, 3, 0, -1.0, 8), (0.5, 3, 0, 1.0, 0)):
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    model.rk4_coupling(*args)


class AdS3Tests(unittest.TestCase):
    def test_arc_length_quadrature_matches_closed_form(self):
        path = EXAMPLES / "ads3_geodesic" / "calculation.py"
        self.assertTrue(path.is_file(), "the reviewed AdS3 entry point is missing")
        model = load_example("ads3_geodesic")
        for length, epsilon, ads_radius in ((2.0, 0.1, 1.0), (4.0, 0.02, 2.5), (0.5, 0.001, 0.7)):
            with self.subTest(length=length, epsilon=epsilon, ads_radius=ads_radius):
                numeric, error_estimate = model.numerical_geodesic_length(length, epsilon, ads_radius)
                exact = model.analytic_geodesic_length(length, epsilon, ads_radius)
                self.assertAlmostEqual(numeric, exact, delta=2e-10)
                self.assertLessEqual(error_estimate, 2e-10)
                self.assertGreater(numeric, 0.0)

    def test_adaptive_simpson_integrates_a_nontrivial_smooth_function(self):
        model = load_example("ads3_geodesic")
        actual, error_estimate = model.adaptive_simpson(lambda x: math.cos(x), 0.0, math.pi / 2, 1e-12)
        self.assertAlmostEqual(actual, 1.0, delta=2e-12)
        self.assertLessEqual(error_estimate, 1e-12)

    def test_geodesic_and_quadrature_domains_are_validated(self):
        model = load_example("ads3_geodesic")
        for args in ((0.0, 0.1, 1.0), (1.0, 0.0, 1.0), (1.0, 0.1, 0.0), (-1.0, 0.1, 1.0)):
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    model.numerical_geodesic_length(*args)
        with self.assertRaises(ValueError):
            model.adaptive_simpson(lambda x: x, 0.0, 1.0, -1.0)


class ExampleProtocolTests(unittest.TestCase):
    def test_each_example_is_a_self_contained_contract_workspace(self):
        for name in ("yang_mills_rg", "ads3_geodesic"):
            with self.subTest(name=name):
                example = EXAMPLES / name
                spec = json.loads((example / "project.json").read_text(encoding="utf-8"))
                protocol = spec["protocol"]
                self.assertEqual(spec["schema_version"], 1)
                self.assertEqual(spec["claim"]["status"], "exploratory")
                self.assertEqual(protocol["mode"], "exploratory")
                self.assertEqual(set(protocol["inputs"]), {"calculation.py", "notes.md"})
                self.assertEqual(set(protocol["outputs"]), {"result.json", "data.csv"})
                self.assertEqual(protocol["command"], ["{python}", "calculation.py", "{output}"])
                self.assertTrue(protocol["metrics"])
                self.assertTrue(spec["sources"])
                for input_name in protocol["inputs"]:
                    self.assertTrue((example / input_name).is_file(), input_name)

    def test_both_direct_commands_write_only_declared_finite_outputs(self):
        for name in ("yang_mills_rg", "ads3_geodesic"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp)
                entry = EXAMPLES / name / "calculation.py"
                completed = subprocess.run(
                    [sys.executable, str(entry), str(output)],
                    cwd=str(entry.parent),
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                self.assertEqual({p.name for p in output.iterdir()}, {"result.json", "data.csv"})
                result = json.loads((output / "result.json").read_text(encoding="utf-8"))
                metrics = result["metrics"]
                self.assertTrue(metrics)
                spec = json.loads((EXAMPLES / name / "project.json").read_text(encoding="utf-8"))
                declared_gates = {item["key"]: item for item in spec["protocol"]["metrics"]}
                self.assertEqual(set(metrics), set(declared_gates))
                for key, value in metrics.items():
                    self.assertIsInstance(value, (int, float), key)
                    self.assertNotIsInstance(value, bool, key)
                    self.assertTrue(math.isfinite(value), key)
                    self.assertLessEqual(value, declared_gates[key]["threshold"], key)
                with (output / "data.csv").open(newline="", encoding="utf-8") as stream:
                    rows = list(csv.DictReader(stream))
                self.assertTrue(rows)
                self.assertTrue(all(rows[0].keys()))
                for row in rows:
                    for value in row.values():
                        self.assertTrue(math.isfinite(float(value)), value)


if __name__ == "__main__":
    unittest.main()
