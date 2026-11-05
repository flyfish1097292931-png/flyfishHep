"""Read-only history/compare acceptance tests; fixtures are software only."""
import importlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from flyfishhep import core, runner
import test_core
from test_core import invoke


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / "project"

    def api(self):
        self.assertIsNotNone(importlib.util.find_spec("flyfishhep.history"), "history API is missing")
        return importlib.import_module("flyfishhep.history")

    def populated(self, code=None):
        fixture = test_core.CoreTests()
        fixture.project = self.project
        return fixture.populated(code)

    def run_fixture(self, code=None):
        if not self.project.exists():
            self.populated(code)
        core.freeze_project(self.project)
        return runner.run_project(self.project, allow_exec=True)

    def test_history_audits_every_entry_and_is_read_only(self):
        good = self.run_fixture()
        other = self.run_fixture()
        runs = self.project / ".flyfishhep/runs"
        (runs / other["run_id"] / "output/result.json").write_text("{}")
        (runs / "incomplete").mkdir()
        (runs / "plain-file").write_text("not a run")
        (runs / "symlink").symlink_to(runs / good["run_id"], target_is_directory=True)
        (self.project / "project.json").write_text("{broken")
        before = {str(p): (p.lstat().st_mtime_ns, p.read_bytes() if p.is_file() else None)
                  for p in self.project.rglob("*") if not p.is_symlink()}
        with patch.object(runner.subprocess, "run", side_effect=AssertionError("execution forbidden")):
            result = self.api().history_project(self.project)
        after = {str(p): (p.lstat().st_mtime_ns, p.read_bytes() if p.is_file() else None)
                 for p in self.project.rglob("*") if not p.is_symlink()}
        self.assertEqual(before, after)
        self.assertEqual(result["counts"], {"total": 5, "verified": 1, "refused": 4})
        self.assertEqual([r["run_id"] for r in result["runs"]], sorted(p.name for p in runs.iterdir()))
        verified = [r for r in result["runs"] if r["integrity"] == "verified"]
        self.assertEqual(verified[0]["outcome"], "criteria_met")
        self.assertFalse(verified[0]["current_source_matches"])
        for row in result["runs"]:
            if row["integrity"] == "refused":
                self.assertNotIn("outcome", row)
                self.assertTrue(row["error"])
        cli = invoke("history", self.project)
        self.assertEqual(cli.returncode, 2)
        self.assertEqual(json.loads(cli.stdout), result)

    def test_same_freeze_compare_and_cli(self):
        left = self.run_fixture()
        right = self.run_fixture()
        api = self.api()
        self.assertTrue(hasattr(api, "compare_runs"), "compare API is missing")
        before = core.inventory(self.project)
        with patch.object(runner.subprocess, "run", side_effect=AssertionError("no execution")):
            result = api.compare_runs(self.project, left["run_id"], right["run_id"])
        self.assertEqual(core.inventory(self.project), before)
        self.assertTrue(result["comparable"])
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["scientific_validity"], "not_assessed")
        self.assertEqual(result["publication"], "human-only")
        self.assertEqual(result["criteria"], [{"key": "error", "op": "le", "threshold": 0.001,
            "left_value": 0.0001, "right_value": 0.0001, "left_passed": True, "right_passed": True,
            "delta": 0.0, "delta_reason": None}])
        cli = invoke("compare", self.project, "--left", left["run_id"], "--right", right["run_id"])
        self.assertEqual(cli.returncode, 0, cli.stderr)
        self.assertEqual(json.loads(cli.stdout), result)
        self.assertEqual(api.compare_runs(self.project, left["run_id"], left["run_id"])["criteria"][0]["delta"], 0)

    def test_comparison_gates_refused_different_freeze_and_non_answer(self):
        left = self.run_fixture()
        (self.project / "calculate.py").write_text("raise SystemExit(1)\n")
        right = self.run_fixture()
        api = self.api()
        different = api.compare_runs(self.project, left["run_id"], right["run_id"])
        self.assertFalse(different["comparable"])
        self.assertEqual(different["reason"], "different_freeze")
        self.assertEqual(different["criteria"], [])
        self.assertFalse(different["left"]["current_source_matches"])
        self.assertTrue(different["right"]["current_source_matches"])
        failed = api.compare_runs(self.project, right["run_id"], right["run_id"])
        self.assertFalse(failed["comparable"])
        self.assertEqual(failed["reason"], "non_answer_or_incomplete_criteria")
        self.assertEqual(failed["criteria"], [])
        self.assertEqual(invoke("history", self.project).returncode, 0)
        for a, b, code in [(left["run_id"], right["run_id"], 0), (right["run_id"], right["run_id"], 0),
                           ("missing", left["run_id"], 2), (left["run_id"], "../escape", 2)]:
            cli = invoke("compare", self.project, "--left", a, "--right", b)
            self.assertEqual(cli.returncode, code, cli.stdout + cli.stderr)
            result = json.loads(cli.stdout)
            self.assertFalse(result["comparable"])
            self.assertEqual(result["criteria"], [])
            if code == 2:
                self.assertEqual(result["status"], "refused")

    def replace_metrics(self, receipt, metrics):
        """Construct a self-consistent software packet; not execution attestation."""
        directory = self.project / ".flyfishhep/runs" / receipt["run_id"]
        (directory / "output/result.json").write_text(json.dumps({"metrics": metrics}))
        spec = core.load_freeze(self.project, receipt["freeze_id"])[0]
        receipt.update(runner.evaluate(spec, directory / "output", receipt["returncode"], False, True))
        receipt["files"] = runner.packet_files(directory)
        (directory / "receipt.json").write_bytes(core.json_bytes(receipt))
        (directory / "receipt.sha256").write_text(core.digest(core.json_bytes(receipt)))

    def test_delta_direction_overflow_and_boolean_non_answer(self):
        left = self.run_fixture()
        right = self.run_fixture()
        api = self.api()
        self.replace_metrics(left, {"error": 1.0})
        self.replace_metrics(right, {"error": 3.0})
        result = api.compare_runs(self.project, left["run_id"], right["run_id"])
        self.assertEqual(result["criteria"][0]["delta"], 2.0)
        self.assertFalse(result["criteria"][0]["left_passed"])
        self.assertEqual(invoke("history", self.project).returncode, 0)
        self.replace_metrics(left, {"error": -1e308})
        self.replace_metrics(right, {"error": 1e308})
        result = api.compare_runs(self.project, left["run_id"], right["run_id"])
        self.assertIsNone(result["criteria"][0]["delta"])
        self.assertEqual(result["criteria"][0]["delta_reason"], "nonfinite_delta")
        json.dumps(result, allow_nan=False)
        cli = invoke("compare", self.project, "--left", left["run_id"], "--right", right["run_id"])
        self.assertEqual(cli.returncode, 0, cli.stdout)
        self.replace_metrics(right, {"error": True})
        result = api.compare_runs(self.project, left["run_id"], right["run_id"])
        self.assertFalse(result["comparable"])
        self.assertEqual(result["criteria"], [])

    def test_run_container_and_root_safety(self):
        core.initialize(self.project, "TEST")
        metadata = self.project / ".flyfishhep"
        metadata.write_text("not a directory")
        with self.assertRaises(core.ContractError):
            self.api().history_project(self.project)
        metadata.unlink()
        metadata.mkdir()
        runs = metadata / "runs"
        runs.write_text("not a directory")
        with self.assertRaises(core.ContractError):
            self.api().history_project(self.project)
        runs.unlink()
        runs.symlink_to(self.project, target_is_directory=True)
        with self.assertRaises(core.ContractError):
            self.api().history_project(self.project)
        runs.unlink()
        link = Path(self.temp.name) / "linked"
        link.symlink_to(self.project, target_is_directory=True)
        with self.assertRaises(core.ContractError):
            self.api().history_project(link)

    def test_compare_requires_explicit_identifiers(self):
        receipt = self.run_fixture()
        for bad in (None, "", "../escape", True):
            result = self.api().compare_runs(self.project, bad, receipt["run_id"])
            self.assertEqual(result["status"], "refused")
            self.assertFalse(result["comparable"])
            self.assertEqual(result["right"]["integrity"], "verified")

    def test_partial_criteria_and_evidence_symlink_are_not_comparable(self):
        spec = self.populated()
        spec["protocol"]["metrics"].append({"key": "missing", "op": "ge", "threshold": 0})
        (self.project / "project.json").write_text(json.dumps(spec))
        receipt = self.run_fixture()
        self.assertEqual(len(receipt["criteria"]), 1)
        result = self.api().compare_runs(self.project, receipt["run_id"], receipt["run_id"])
        self.assertFalse(result["comparable"])
        self.assertEqual(result["reason"], "non_answer_or_incomplete_criteria")
        self.assertEqual(result["criteria"], [])
        directory = self.project / ".flyfishhep/runs" / receipt["run_id"]
        target = directory / "output/result.json"
        target.unlink()
        target.symlink_to(self.project / "project.json")
        result = self.api().compare_runs(self.project, receipt["run_id"], receipt["run_id"])
        self.assertEqual(result["status"], "refused")
        self.assertNotIn("outcome", result["left"])
        self.assertEqual(self.api().history_project(self.project)["counts"]["refused"], 1)

    def test_malformed_receipt_does_not_abort_history(self):
        broken = self.run_fixture()
        good = self.run_fixture()
        directory = self.project / ".flyfishhep/runs" / broken["run_id"]
        broken["freeze_id"] = []
        (directory / "receipt.json").write_bytes(core.json_bytes(broken))
        (directory / "receipt.sha256").write_text(core.digest(core.json_bytes(broken)))
        result = self.api().history_project(self.project)
        self.assertEqual(result["counts"], {"total": 2, "verified": 1, "refused": 1})
        (directory / "receipt.sha256").write_bytes(b"\xff")
        self.assertEqual(self.api().history_project(self.project)["counts"]["refused"], 1)
        (self.project / "calculate.py").write_text("# current source changed")
        result = self.api().compare_runs(self.project, good["run_id"], good["run_id"])
        self.assertTrue(result["comparable"])
        self.assertFalse(result["left"]["current_source_matches"])
        (self.project / "project.json").write_text("broken json")
        result = self.api().compare_runs(self.project, good["run_id"], good["run_id"])
        self.assertTrue(result["comparable"])
        self.assertFalse(result["right"]["current_source_matches"])

    def test_empty_history_is_explicit_not_success_evidence(self):
        core.initialize(self.project, "TEST")
        result = self.api().history_project(self.project)
        self.assertEqual(result["status"], "no_runs")
        self.assertEqual(result["runs"], [])
        self.assertEqual(result["counts"], {"total": 0, "verified": 0, "refused": 0})
        self.assertEqual(result["scientific_validity"], "not_assessed")
        cli = invoke("history", self.project)
        self.assertEqual(cli.returncode, 0, cli.stderr)
        self.assertEqual(json.loads(cli.stdout), result)
        for path in (self.project / "missing", Path(self.temp.name)):
            with self.assertRaises(core.ContractError):
                self.api().history_project(path)
            cli = invoke("history", path)
            self.assertEqual(cli.returncode, 2)
            self.assertEqual(json.loads(cli.stdout)["status"], "refused")
