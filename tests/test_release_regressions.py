"""Release-review regressions: real CLI execution, not physics certification."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
NORMAL = "import pathlib,sys\npathlib.Path(sys.argv[1], 'result.json').write_text('{\"metrics\":{\"error\":0}}')\n"


def invoke(*args):
    return subprocess.run([sys.executable, "-B", "-m", "flyfishhep", *map(str, args)],
                          cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
                          capture_output=True, text=True, timeout=15)


class ReleaseRegressions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / "project"
        self.project.mkdir()

    def populated(self, code=NORMAL, entry="calculate.py", timeout=5, outputs=None):
        spec = json.loads((ROOT / "examples/yang_mills_rg/project.json").read_text())
        spec["protocol"].update(inputs=[entry], command=["{python}", entry, "{output}"],
                                outputs=outputs or ["result.json"], timeout_seconds=timeout,
                                metrics=[{"key": "error", "op": "le", "threshold": 0.001}])
        (self.project / "project.json").write_text(json.dumps(spec), encoding="utf-8")
        (self.project / entry).write_text(code, encoding="utf-8")
        frozen = invoke("freeze", self.project)
        self.assertEqual(frozen.returncode, 0, frozen.stdout + frozen.stderr)

    def run_receipt(self):
        result = invoke("run", self.project, "--allow-exec")
        runs = sorted((self.project / ".flyfishhep/runs").iterdir())
        directory = runs[-1]
        self.assertTrue((directory / "receipt.json").is_file(), result.stdout + result.stderr)
        receipt = json.loads((directory / "receipt.json").read_text())
        self.assertEqual(json.loads(result.stdout), receipt)
        self.assertTrue((directory / "receipt.sha256").is_file())
        return result, receipt, directory

    def test_s1_option_shaped_entry_executes_frozen_file_contents(self):
        entry = "-cimport pathlib,sys,json;pathlib.Path(sys.argv[1],'result.json').write_text(json.dumps(dict(metrics=dict(error=0))))#.py"
        self.populated("print('FROZEN_FILE_EXECUTED', flush=True)\nraise RuntimeError('frozen failure')\n", entry=entry)
        result, receipt, directory = self.run_receipt()
        self.assertIn("FROZEN_FILE_EXECUTED", (directory / "stdout.txt").read_text())
        self.assertEqual(result.returncode, 1)
        self.assertEqual(receipt["returncode"], 1)
        self.assertEqual(receipt["outcome"], "non_answer")
        self.assertIn("frozen failure", (directory / "stderr.txt").read_text())
        self.assertFalse((directory / "output/result.json").exists())
        self.assertTrue(receipt["source_unchanged"])

    def assert_incomplete_inventory(self, receipt, directory):
        self.assertEqual(receipt["schema_version"], 1)
        self.assertEqual(receipt["outcome"], "non_answer")
        self.assertIsNone(receipt["files"])
        self.assertTrue(any(f.startswith("inventory_failed:") for f in receipt["failures"]))
        for command in ("audit", "report"):
            checked = invoke(command, self.project, "--run", receipt["run_id"])
            self.assertEqual(checked.returncode, 2, checked.stdout + checked.stderr)
            error = json.loads(checked.stdout)
            self.assertEqual(error["status"], "refused")
            self.assertIn("incomplete", error["error"])
            self.assertNotIn("verified", checked.stdout)

    def test_l1_symlink_output_retains_process_failure_receipt(self):
        code = ("import pathlib,sys\n"
                "pathlib.Path(sys.argv[1], 'result.json').symlink_to(pathlib.Path('calculate.py').resolve())\n"
                "sys.exit(7)\n")
        self.populated(code)
        result, receipt, directory = self.run_receipt()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(receipt["returncode"], 7)
        self.assertIs(receipt["timed_out"], False)
        self.assertIn("process_failed", receipt["failures"])
        self.assertTrue((directory / "output/result.json").is_symlink())
        self.assert_incomplete_inventory(receipt, directory)
        # Removing invalid evidence must not upgrade an incomplete receipt.
        (directory / "output/result.json").unlink()
        self.assert_incomplete_inventory(receipt, directory)

    def test_l1_oversize_sparse_output_retains_timeout_receipt(self):
        code = (NORMAL + "import time\n"
                "with pathlib.Path(sys.argv[1], 'large.dat').open('wb') as stream:\n"
                "    stream.truncate(50 * 1024 * 1024 + 1)\n"
                "time.sleep(5)\n")
        self.populated(code, timeout=1, outputs=["result.json", "large.dat"])
        result, receipt, directory = self.run_receipt()
        self.assertEqual(result.returncode, 1)
        self.assertIsNone(receipt["returncode"])
        self.assertIs(receipt["timed_out"], True)
        self.assertIn("timeout", receipt["failures"])
        self.assertEqual((directory / "output/large.dat").stat().st_size, 50 * 1024 * 1024 + 1)
        self.assert_incomplete_inventory(receipt, directory)

    def test_l2_deep_project_validate_returns_structured_refusal(self):
        (self.project / "project.json").write_text("[" * 1500 + "0" + "]" * 1500)
        result = invoke("validate", self.project)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "refused")
        self.assertIn("depth", json.loads(result.stdout)["error"])
        self.assertEqual(result.stderr, "")

    def test_l2_deep_project_next_returns_json_suggestion(self):
        (self.project / "project.json").write_text("[" * 1500 + "0" + "]" * 1500)
        result = invoke("next", self.project)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["action"], "define")
        self.assertIn("depth", json.loads(result.stdout)["reason"])
        self.assertEqual(result.stderr, "")

    def test_l2_deep_result_preserves_nonanswer_receipt(self):
        code = ("import pathlib,sys\n"
                "pathlib.Path(sys.argv[1], 'result.json').write_text('{\"metrics\":{\"error\":0},\"extra\":' + '['*1500 + '0' + ']'*1500 + '}')\n")
        self.populated(code)
        result, receipt, directory = self.run_receipt()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(receipt["returncode"], 0)
        self.assertIs(receipt["timed_out"], False)
        self.assertEqual(receipt["outcome"], "non_answer")
        self.assertTrue(any("depth" in failure for failure in receipt["failures"]))
        audit = invoke("audit", self.project)
        self.assertEqual(audit.returncode, 0, audit.stdout + audit.stderr)
        self.assertEqual(json.loads(audit.stdout)["outcome"], "non_answer")

    def test_l2_json_container_depth_is_bounded_at_128(self):
        from flyfishhep.core import ContractError
        from flyfishhep.validation import parse_json
        for opening, closing in (("[", "]"), ('{"child":', "}")):
            with self.subTest(opening=opening):
                parse_json(opening * 128 + "0" + closing * 128)
                with self.assertRaisesRegex(ContractError, "depth.*128"):
                    parse_json(opening * 129 + "0" + closing * 129)

    def test_n1_modules_import_in_fresh_processes(self):
        for module in ("validation", "core", "runner", "workflow", "cli", "exceptions"):
            with self.subTest(module=module):
                result = subprocess.run([sys.executable, "-B", "-c", "import flyfishhep." + module],
                                        cwd=ROOT, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_n1_core_reexports_same_contract_exception(self):
        from flyfishhep.core import ContractError
        try:
            from flyfishhep.exceptions import ContractError as SharedContractError
        except ImportError as exc:
            self.fail(str(exc))
        self.assertIs(ContractError, SharedContractError)
        self.assertTrue(issubclass(ContractError, ValueError))

    def test_n2_overflowing_float_metadata_is_rejected(self):
        from flyfishhep.exceptions import ContractError
        from flyfishhep.validation import parse_json
        for token in ("1e400", "-1e400"):
            with self.subTest(token=token):
                with self.assertRaisesRegex(ContractError, "finite"):
                    parse_json('{"metrics":{"error":0},"extra":' + token + '}')
        self.assertEqual(parse_json('{"extra":1e300}')["extra"], 1e300)

    def test_n2_overflowing_metadata_preserves_nonanswer_receipt(self):
        code = ("import pathlib,sys\n"
                "pathlib.Path(sys.argv[1], 'result.json').write_text('{\"metrics\":{\"error\":0},\"extra\":1e400}')\n")
        self.populated(code)
        result, receipt, directory = self.run_receipt()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(receipt["returncode"], 0)
        self.assertEqual(receipt["outcome"], "non_answer")
        self.assertTrue(any("finite" in failure for failure in receipt["failures"]))

    @unittest.skipUnless(hasattr(sys, "set_int_max_str_digits"), "interpreter has no integer digit limit")
    def test_n2_integer_decoder_valueerror_is_contracterror(self):
        from flyfishhep.exceptions import ContractError
        from flyfishhep.validation import parse_json
        previous = sys.get_int_max_str_digits()
        try:
            sys.set_int_max_str_digits(640)
            with self.assertRaisesRegex(ContractError, "invalid JSON"):
                parse_json('{"extra":' + "9" * 641 + '}')
        finally:
            sys.set_int_max_str_digits(previous)

    @unittest.skipUnless(hasattr(sys, "set_int_max_str_digits"), "interpreter has no integer digit limit")
    def test_n2_long_integer_result_preserves_nonanswer_receipt(self):
        code = ("import pathlib,sys\n"
                "pathlib.Path(sys.argv[1], 'result.json').write_text('{\"metrics\":{\"error\":0},\"extra\":' + '9'*5000 + '}')\n")
        self.populated(code)
        # Pin the decoder limit in the CLI process, independent of environment defaults.
        result = subprocess.run([sys.executable, "-B", "-c",
                                 "import sys; sys.set_int_max_str_digits(640); "
                                 "from flyfishhep.cli import main; raise SystemExit(main())",
                                 "run", str(self.project), "--allow-exec"],
                                cwd=ROOT, capture_output=True, text=True, timeout=15)
        runs = sorted((self.project / ".flyfishhep/runs").iterdir())
        self.assertTrue((runs[-1] / "receipt.json").exists(), result.stdout + result.stderr)
        receipt = json.loads((runs[-1] / "receipt.json").read_text())
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(receipt["outcome"], "non_answer")
        self.assertEqual(receipt["returncode"], 0)
        self.assertTrue(any("invalid JSON" in failure for failure in receipt["failures"]))


if __name__ == "__main__":
    unittest.main()
