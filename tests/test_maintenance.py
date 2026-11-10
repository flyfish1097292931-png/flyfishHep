"""Maintenance safety tests; never recursively launch this repository's suite."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'maintenance_check.py'
spec = importlib.util.spec_from_file_location('maintenance_check', SCRIPT)
assert spec is not None and spec.loader is not None
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class MaintenanceTests(unittest.TestCase):
    def test_snapshot_disables_implicit_git_helpers(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            with mock.patch.object(m, 'run_check', wraps=m.run_check) as calls:
                m.snapshot(root, 5)
            self.assertTrue(calls.call_args_list)
            for call in calls.call_args_list:
                argv = call.args[0]
                self.assertIn('--no-pager', argv)
                self.assertIn('core.fsmonitor=false', argv)
                self.assertIn('core.untrackedCache=false', argv)
                if 'diff' in argv:
                    self.assertIn('--no-ext-diff', argv)
                    self.assertIn('--no-textconv', argv)

    def test_no_consent_never_runs_source(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            with mock.patch.object(m, 'snapshot', return_value={'status': 'passed'}), mock.patch.object(m, 'run_check') as run:
                report = m.collect(root, False, False, None, 1)
            run.assert_not_called()
            self.assertEqual(report['local']['status'], 'incomplete')
            self.assertEqual(report['local']['checks']['unittest']['status'], 'not_run')
            self.assertEqual(report['scientific_validity'], 'not_assessed')

    def test_reviewed_commands_and_github_unknown(self):
        def fake(argv, root, timeout, **kw):
            return dict(argv=argv, status='unknown' if argv[0] == 'gh' else 'passed', exit_code=None if argv[0] == 'gh' else 0,
                        duration_seconds=0, stdout='', stderr='', timed_out=False)
        with tempfile.TemporaryDirectory() as d, mock.patch.object(m, 'snapshot', return_value={'status': 'passed'}), mock.patch.object(m, 'run_check', side_effect=fake):
            report = m.collect(Path(d).resolve(), True, True, 'owner/repo', 1)
        self.assertEqual(report['local']['status'], 'passed')
        self.assertEqual(report['github']['status'], 'incomplete')
        self.assertEqual(report['status'], 'incomplete')
        self.assertIn('--allow-exec', report['local']['checks']['smoke']['argv'])
        self.assertEqual(len(report['github']['checks']), 3)

    def test_github_partial_and_invalid_payloads(self):
        def fake(argv, root, timeout, **kw):
            payload = '[]' if argv[1] == 'issue' else '[NaN]'
            return dict(argv=argv, status='passed', exit_code=0, duration_seconds=0,
                        stdout=payload, stderr='', timed_out=False, stdout_truncated=False)
        with tempfile.TemporaryDirectory() as d, mock.patch.object(m, 'snapshot', return_value={'status': 'passed'}), mock.patch.object(m, 'run_check', side_effect=fake):
            report = m.collect(Path(d).resolve(), False, True, 'owner/repo', 1)
        self.assertEqual(report['github']['checks']['issues']['observed_count'], 0)
        for name in ('pull_requests', 'actions'):
            self.assertEqual(report['github']['checks'][name]['status'], 'unknown')
            self.assertNotIn('observed_count', report['github']['checks'][name])
        self.assertEqual(report['status'], 'incomplete')

    def test_snapshot_unavailable_blocks_execution(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(m, 'snapshot', return_value={'status': 'incomplete'}), mock.patch.object(m, 'run_check') as run:
            report = m.collect(Path(d).resolve(), True, False, None, 1)
        run.assert_not_called()
        self.assertEqual(report['local']['checks']['smoke']['status'], 'not_run')

    def test_nested_python_uses_reviewed_source(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            (root / 'reviewed_probe.py').write_text('VALUE = 123\n')
            nested = "import os,subprocess,sys; os.chdir('/'); subprocess.run([sys.executable,'-c','import reviewed_probe; print(reviewed_probe.VALUE)'], check=True)"
            result = m.run_check([sys.executable, '-c', nested], root, 5)
            self.assertEqual(result['status'], 'passed')
            self.assertIn('123', result['stdout'])

    def test_failed_local_wins_over_unknown(self):
        self.assertEqual(m.aggregate(['failed', 'unknown']), 'failed')
        self.assertEqual(m.aggregate(['passed', 'not_run']), 'incomplete')

    def test_runner_bounded_and_missing(self):
        with tempfile.TemporaryDirectory() as d:
            r = m.run_check([sys.executable, '-c', "print('x'*100000)"], Path(d).resolve(), 5)
            self.assertEqual(r['status'], 'passed')
            self.assertTrue(r['stdout_truncated'])
            self.assertLessEqual(len(r['stdout']), m.OUTPUT_LIMIT)
            self.assertEqual(m.run_check(['/nonexistent/maintenance-command'], Path(d).resolve(), 1)['status'], 'unknown')
            self.assertEqual(m.run_check([sys.executable, '-c', 'raise SystemExit(3)'], Path(d).resolve(), 1)['status'], 'failed')

    @unittest.skipUnless(os.name == 'posix', 'POSIX process group contract')
    def test_timeout_kills_descendant(self):
        with tempfile.TemporaryDirectory() as d:
            marker = Path(d).resolve() / 'escaped'
            child = "import time; from pathlib import Path; time.sleep(1); Path(%r).touch()" % str(marker)
            code = 'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",%r]); time.sleep(10)' % child
            result = m.run_check([sys.executable, '-c', code], Path(d).resolve(), .1)
            self.assertTrue(result['timed_out'])
            self.assertEqual(result['status'], 'unknown')
            time.sleep(1.1)
            self.assertFalse(marker.exists())

    def test_atomic_refusals_preserve_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve() / 'repo'; root.mkdir()
            output = Path(d).resolve() / 'report.json'
            m.write_report(output, {'ok': True}, root)
            before = output.read_bytes()
            for bad in ({'x': float('nan')}, {'x': 'x' * m.REPORT_LIMIT}):
                with self.assertRaises(ValueError):
                    m.write_report(output, bad, root)
                self.assertEqual(output.read_bytes(), before)
            with self.assertRaises(ValueError):
                m.write_report(root / 'report.json', {}, root)
            link = Path(d).resolve() / 'link'; link.symlink_to(output)
            with self.assertRaises(ValueError):
                m.write_report(link, {}, root)
            folder = Path(d).resolve() / 'linked'; folder.symlink_to(root, target_is_directory=True)
            with self.assertRaises(ValueError):
                m.write_report(folder / 'report.json', {}, root)

    def test_real_fixture_static_and_execution(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve() / 'repo'; root.mkdir()
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            subprocess.run(['git', '-C', str(root), '-c', 'user.name=fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '--allow-empty', '-qm', 'fixture'], check=True)
            (root / 'tests').mkdir(); (root / 'scripts').mkdir()
            (root / 'tests' / 'test_tiny.py').write_text('import unittest\nclass Tiny(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\n')
            (root / 'scripts' / 'smoke_examples.py').write_text('print("fixture smoke only")\n')
            static = m.collect(root, False, False, None, 5)
            self.assertEqual(static['status'], 'incomplete')
            self.assertEqual(static['source_before']['status'], 'passed')
            real = m.collect(root, True, False, None, 5)
            self.assertEqual(real['local']['status'], 'passed')
            self.assertEqual(real['status'], 'passed')
            (root / 'tests' / 'test_tiny.py').write_text('# changed\n')
            self.assertNotEqual(real['source_before']['tree_sha256'], m.snapshot(root, 5)['tree_sha256'])

    def test_cli_rejects_relative_root_and_bad_repo(self):
        with self.assertRaises(SystemExit):
            m.main(['--root', '.', '--output', '/unused.json'])
        with self.assertRaises(SystemExit):
            m.main(['--root', '/a', '--output', '/unused.json', '--github', '--repo', '--bad'])


if __name__ == '__main__':
    unittest.main()
