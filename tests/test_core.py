import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def invoke(*args):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, "-B", "-m", "flyfishhep", *map(str, args)],
                          cwd=ROOT, env=env, text=True, capture_output=True)


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / "project"

    def populated(self, code=None):
        invoke("init", self.project, "--id", "HEP-TEST")
        spec_path = self.project / "project.json"
        spec = json.loads(spec_path.read_text())
        spec.update(title="Engineering fixture, not physics evidence", question="Does the frozen computation preserve evidence?", stage="construct")
        spec["theory"] = {key: (["test assumption"] if key == "assumptions" else "fixture-only: " + key) for key in spec["theory"]}
        spec["claim"].update(statement="Fixture returns a small error metric", scope="software test only", limitations=["not a physical claim"], forbidden_inferences=["scientific validity"])
        spec["protocol"].update(inputs=["calculate.py"], command=["{python}", "calculate.py", "{output}"], outputs=["result.json"],
            metrics=[{"key": "error", "op": "le", "threshold": 0.001}],
            disconfirming="error above threshold", independence="fixture only", failure_interpretation="software diagnosis")
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        source = code or 'import json, pathlib, sys\npathlib.Path(sys.argv[1], "result.json").write_text(json.dumps({"metrics": {"error": 0.0001}}))\n'
        (self.project / "calculate.py").write_text(source, encoding="utf-8")
        return spec

    def test_freeze_is_content_addressed_and_idempotent(self):
        self.populated()
        valid = invoke("validate", self.project)
        self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)
        first = invoke("freeze", self.project)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        packet = json.loads(first.stdout)
        self.assertRegex(packet["freeze_id"], r"^[a-f0-9]{64}$")
        second = json.loads(invoke("freeze", self.project).stdout)
        self.assertEqual(packet["freeze_id"], second["freeze_id"])
        frozen = self.project / ".flyfishhep" / "freezes" / packet["freeze_id"]
        self.assertEqual((frozen / "inputs" / "calculate.py").read_bytes(), (self.project / "calculate.py").read_bytes())

    def test_real_run_audit_and_claim_preservation(self):
        self.populated()
        before = (self.project / "project.json").read_bytes()
        invoke("freeze", self.project)
        result = invoke("run", self.project, "--allow-exec")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["outcome"], "criteria_met")
        self.assertEqual(receipt["scientific_status"], "exploratory")
        self.assertEqual(before, (self.project / "project.json").read_bytes())
        checked = invoke("audit", self.project, "--run", receipt["run_id"])
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        audit = json.loads(checked.stdout)
        self.assertEqual(audit["integrity"], "verified")
        self.assertEqual(audit["scientific_validity"], "not_assessed")
        self.assertTrue(audit["current_source_matches"])

    def test_next_and_report_follow_evidence_not_stage_labels(self):
        self.populated()
        proposed = invoke("next", self.project)
        self.assertEqual(proposed.returncode, 0, proposed.stdout + proposed.stderr)
        self.assertEqual(json.loads(proposed.stdout)["action"], "freeze")
        invoke("freeze", self.project)
        self.assertEqual(json.loads(invoke("next", self.project).stdout)["action"], "request_execution")
        run = json.loads(invoke("run", self.project, "--allow-exec").stdout)
        self.assertEqual(json.loads(invoke("next", self.project).stdout)["action"], "scientific_review")
        report = invoke("report", self.project, "--run", run["run_id"])
        self.assertEqual(report.returncode, 0, report.stdout + report.stderr)
        self.assertIn("not_assessed", report.stdout)
        self.assertIn("criteria_met", report.stdout)
        self.assertIn("error", report.stdout)
        with (self.project / "calculate.py").open("a") as stream:
            stream.write("# a new candidate\n")
        self.assertEqual(json.loads(invoke("next", self.project).stdout)["action"], "freeze")
        stale = invoke("report", self.project, "--run", run["run_id"])
        self.assertIn("historical", stale.stdout)

    def test_frozen_tampering_and_protocol_mutations_fail_closed(self):
        self.populated()
        frozen = json.loads(invoke("freeze", self.project).stdout)
        input_copy = self.project / ".flyfishhep" / "freezes" / frozen["freeze_id"] / "inputs" / "calculate.py"
        original = input_copy.read_bytes()
        input_copy.write_bytes(original + b"# tamper\n")
        rejected = invoke("run", self.project, "--allow-exec")
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("frozen input digest mismatch", rejected.stdout)

        self.populated()
        spec_path = self.project / "project.json"
        spec = json.loads(spec_path.read_text())
        spec["protocol"]["metrics"] = []
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        self.assertEqual(invoke("validate", self.project).returncode, 2)

        self.populated()
        (self.project / "outside.py").write_text("# outside\n")
        (self.project / "escape.py").symlink_to(self.project / "outside.py")
        spec = json.loads((self.project / "project.json").read_text())
        spec["protocol"]["inputs"] = ["escape.py"]
        spec["protocol"]["command"] = ["{python}", "escape.py", "{output}"]
        (self.project / "project.json").write_text(json.dumps(spec), encoding="utf-8")
        self.assertEqual(invoke("validate", self.project).returncode, 2)

    def test_execution_requires_explicit_permission(self):
        self.populated()
        invoke("freeze", self.project)
        denied = invoke("run", self.project)
        self.assertEqual(denied.returncode, 2)
        self.assertIn("execution denied", denied.stdout)
        self.assertFalse((self.project / ".flyfishhep" / "runs").exists())

    def test_packet_tampering_is_detected(self):
        self.populated()
        invoke("freeze", self.project)
        run = json.loads(invoke("run", self.project, "--allow-exec").stdout)
        run_dir = self.project / ".flyfishhep" / "runs" / run["run_id"]
        output = run_dir / "output" / "result.json"
        output.write_text('{"metrics":{"error":0.0}}', encoding="utf-8")
        tampered = invoke("audit", self.project, "--run", run["run_id"])
        self.assertEqual(tampered.returncode, 2)
        self.assertIn("digest/inventory mismatch", tampered.stdout)

    def test_registered_failure_is_a_valid_negative_not_nonanswer(self):
        source = chr(10).join(["import json, pathlib, sys", "pathlib.Path(sys.argv[1], 'result.json').write_text(json.dumps({'verdict': 'PASS', 'metrics': {'error': 0.1}}))"])
        self.populated(source)
        invoke("freeze", self.project)
        run = invoke("run", self.project, "--allow-exec")
        self.assertEqual(run.returncode, 1)
        receipt = json.loads(run.stdout)
        self.assertEqual(receipt["outcome"], "criteria_not_met")
        self.assertTrue(receipt["criteria"][0]["passed"] is False)
        audited = invoke("audit", self.project, "--run", receipt["run_id"])
        self.assertEqual(audited.returncode, 0, audited.stdout + audited.stderr)
        self.assertEqual(json.loads(audited.stdout)["outcome"], "criteria_not_met")

    def test_nonfinite_metrics_and_runner_written_verdicts_cannot_pass(self):
        source = chr(10).join(["import pathlib, sys", "pathlib.Path(sys.argv[1], 'result.json').write_text('{\"verdict\":\"PASS\",\"metrics\":{\"error\":NaN}}')"])
        self.populated(source)
        invoke("freeze", self.project)
        run = invoke("run", self.project, "--allow-exec")
        self.assertEqual(run.returncode, 1)
        self.assertEqual(json.loads(run.stdout)["outcome"], "non_answer")
        report = invoke("report", self.project)
        self.assertEqual(report.returncode, 0, report.stdout + report.stderr)
        self.assertNotIn("PASS", report.stdout)

    def test_timeout_is_retained_as_nonanswer(self):
        source = chr(10).join(["import time, pathlib, sys", "time.sleep(2)", "pathlib.Path(sys.argv[1], 'result.json').write_text('{}')"])
        self.populated(source)
        spec_path = self.project / "project.json"
        spec = json.loads(spec_path.read_text())
        spec["protocol"]["timeout_seconds"] = 0.05
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        invoke("freeze", self.project)
        result = invoke("run", self.project, "--allow-exec")
        self.assertEqual(result.returncode, 1)
        receipt = json.loads(result.stdout)
        self.assertTrue(receipt["timed_out"])
        self.assertEqual(receipt["outcome"], "non_answer")
        self.assertEqual(invoke("audit", self.project, "--run", receipt["run_id"]).returncode, 0)

    def test_init_creates_draft_without_overwrite(self):
        result = invoke("init", self.project, "--id", "HEP-TEST", "--domain", "qft-eft")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        data = json.loads((self.project / "project.json").read_text())
        self.assertEqual(data["id"], "HEP-TEST")
        self.assertEqual(data["stage"], "incubate")
        self.assertEqual(data["claim"]["status"], "exploratory")
        self.assertIs(data["authorization"]["network"], False)
        original = (self.project / "project.json").read_bytes()
        self.assertEqual(invoke("init", self.project, "--id", "OTHER").returncode, 2)
        self.assertEqual(original, (self.project / "project.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
