"""The complete public use case must run; a narrative alone is insufficient."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import flyfishhep
from flyfishhep import runner

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_ads3_case.py"


class CompleteCaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="flyfishhep-case-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.output = self.base / "case"

    def command(self, output=None, *args):
        env = os.environ.copy()
        # Source tests use the current package; installed tests use site-packages.
        env["PYTHONPATH"] = str(Path(flyfishhep.__file__).resolve().parent.parent)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run([sys.executable, "-B", str(SCRIPT), str(output or self.output), *args],
                              cwd=str(self.base), env=env, text=True, capture_output=True, timeout=90)

    def test_requires_explicit_execution_consent(self):
        self.assertTrue(SCRIPT.is_file(), "complete-use-case runner is not implemented")
        process = self.command()
        self.assertEqual(process.returncode, 2, process.stdout + process.stderr)
        self.assertFalse(self.output.exists())

    def test_prepare_only_is_nonexecuting_and_complete(self):
        process = self.command(None, "--prepare-only")
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        result = json.loads(process.stdout)
        self.assertEqual(result["status"], "prepared")
        work = self.output / "workspace"
        self.assertFalse((work / ".flyfishhep").exists())
        spec = json.loads((work / "project.json").read_text())
        for name in spec["protocol"]["inputs"]:
            self.assertTrue((work / name).is_file(), name)
        self.assertEqual((work / "geodesic.py").read_bytes(),
                         (ROOT / "examples" / "ads3_geodesic" / "calculation.py").read_bytes())

    def test_existing_output_is_never_overwritten(self):
        self.output.mkdir()
        marker = self.output / "keep.txt"
        marker.write_text("keep me", encoding="utf-8")
        process = self.command(None, "--allow-exec")
        self.assertEqual(process.returncode, 2)
        self.assertEqual(marker.read_text(), "keep me")
        self.assertEqual(list(self.output.iterdir()), [marker])

    def test_output_inside_source_is_refused_before_writes(self):
        output = ROOT / "must-not-create-case-output"
        process = self.command(output, "--allow-exec")
        self.assertEqual(process.returncode, 2, process.stdout + process.stderr)
        self.assertFalse(output.exists())

    def test_symlink_ancestor_is_refused(self):
        actual = self.base / "real"
        actual.mkdir()
        alias = self.base / "alias"
        try:
            alias.symlink_to(actual, target_is_directory=True)
        except OSError:
            self.skipTest("symlink creation not permitted")
        process = self.command(alias / "case", "--allow-exec")
        self.assertEqual(process.returncode, 2, process.stdout + process.stderr)
        self.assertEqual(list(actual.iterdir()), [])

    def test_full_case_preserves_failure_revises_and_hands_off(self):
        process = self.command(None, "--allow-exec")
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        summary = json.loads((self.output / "case-summary.json").read_text())
        self.assertEqual(summary["status"], "completed")
        self.assertEqual([r["outcome"] for r in summary["runs"]],
                         ["criteria_not_met", "criteria_met", "criteria_met"])
        self.assertTrue(summary["replay_csv_identical"])
        self.assertFalse(summary["cross_model_comparison"]["comparable"])
        self.assertTrue(summary["replay_comparison"]["comparable"])
        self.assertFalse(summary["historical_run_current"])
        self.assertTrue(summary["observation_evidence_current"])
        self.assertEqual(summary["handoff_decision"], "human_review")
        self.assertEqual(summary["scientific_validity"], "not_assessed")
        self.assertEqual(summary["publication"], "human-only")
        self.assertEqual(len(summary["rows"]), 6)
        for row in summary["rows"]:
            self.assertLess(row["numeric_exact_abs_error"], 1e-10)
            self.assertLess(row["refinement_abs_difference"], 1e-10)
            self.assertGreater(row["uv_log_abs_error"], 1e-8)
        transcript = json.loads((self.output / "commands.json").read_text())
        runs = [x for x in transcript if x["arguments"][0] == "run"]
        self.assertEqual([x["returncode"] for x in runs], [1, 0, 0])
        self.assertIn("asinh", (self.output / "report.md").read_text())
        self.assertIn("<svg", (self.output / "cutoff-error.svg").read_text())
        self.assertTrue((self.output / "index.html").is_file())
        work = self.output / "workspace"
        for item in summary["runs"]:
            audit = runner.audit_project(work, item["run_id"])
            self.assertEqual(audit["integrity"], "verified")
            self.assertEqual(audit["scientific_status"], "exploratory")
        # A real retained-output alteration must invalidate evidence, not be hidden.
        run_id = summary["runs"][-1]["run_id"]
        data = work / ".flyfishhep" / "runs" / run_id / "output" / "data.csv"
        with data.open("a", encoding="utf-8") as stream:
            stream.write("tampered\n")
        from flyfishhep.exceptions import ContractError
        with self.assertRaises(ContractError):
            runner.audit_project(work, run_id)


def load_recipe():
    import importlib.util
    spec = importlib.util.spec_from_file_location("complete_case_recipe", SCRIPT)
    assert spec is not None and spec.loader is not None
    recipe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(recipe)
    return recipe


class CommandFailureTests(unittest.TestCase):
    def assert_bad_study_stops(self, process_failure):
        from unittest.mock import patch
        recipe = load_recipe()
        with tempfile.TemporaryDirectory() as temp:
            output, workspace = recipe.prepare(Path(temp).resolve() / "case")
            if process_failure:
                (workspace / "study.py").write_text('raise RuntimeError("synthetic failure fixture")\n')
            else:
                config = json.loads((workspace / "study.json").read_text())
                config.update(tolerance=1e-2, refined_tolerance=1e-3)
                (workspace / "study.json").write_text(json.dumps(config))
            message = "process/evidence failure" if process_failure else "integration diagnostics failed"
            env = {"PYTHONPATH": str(Path(flyfishhep.__file__).resolve().parent.parent), "PYTHONDONTWRITEBYTECODE": "1"}
            with patch.dict(os.environ, env), self.assertRaisesRegex(ValueError, message):
                recipe.run_case(output, workspace)
            transcript = json.loads((output / "commands.json").read_text())
            runs = [row for row in transcript if row["arguments"][0] == "run"]
            self.assertEqual(len(runs), 1)
            actual = json.loads(runs[0]["stdout"])
            self.assertEqual(actual["outcome"], "non_answer" if process_failure else "criteria_not_met")
            self.assertFalse((output / "index.html").exists())
            self.assertFalse((output / "case-summary.json").exists())
            self.assertEqual(json.loads((workspace / "study.json").read_text())["prediction"], "uv_log")

    def test_process_failure_is_not_an_approximation_miss(self):
        self.assert_bad_study_stops(True)

    def test_integration_failure_is_not_an_approximation_miss(self):
        self.assert_bad_study_stops(False)

    def test_timeout_is_retained_in_transcript(self):
        from unittest.mock import patch
        recipe = load_recipe()
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            # Explicit synthetic timeout; not a substitute for a physics run.
            timeout = subprocess.TimeoutExpired(["fixture"], 60, output=b"partial output", stderr=b"partial error")
            with patch.object(recipe.subprocess, "run", side_effect=timeout):
                with self.assertRaisesRegex(ValueError, "timed out"):
                    recipe.Commands(output)("history", "fixture-workspace")
            record = json.loads((output / "commands.json").read_text())[0]
            self.assertTrue(record["timed_out"])
            self.assertIsNone(record["returncode"])
            self.assertEqual(record["stdout"], "partial output")
            self.assertEqual(record["stderr"], "partial error")


if __name__ == "__main__":
    unittest.main()
