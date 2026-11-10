"""Bounded host executor: real local observations, never scientific approval."""
import importlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from flyfishhep import handoff


class HostTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'workspace'
        initial = handoff.initialize_handoff(self.root, 'host-test', 'What does the file report?')
        record = dict(initial['record'], next_check=dict(kind='derivation', question='Read the note?', method='Read local note', decision_rule='Review the reported bytes'))
        self.plan = handoff.update_handoff(self.root, record, initial['revision'])
        (self.root / 'note.txt').write_bytes(b'real note\n')

    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('flyfishhep.hostloop'), 'host executor missing')
        return importlib.import_module('flyfishhep.hostloop')

    def test_read_file_real_roundtrip(self):
        api = self.api()
        prepared = api.prepare(self.root, 'read-file', path='note.txt')
        request_id = prepared['request_id']
        self.assertEqual(prepared['state'], 'prepared')
        self.assertEqual(api.prepare(self.root, 'read-file', path='note.txt')['request_id'], request_id)
        done = api.execute(self.root, request_id, allow_exec=True, scope='read-file')
        self.assertEqual(done['state'], 'completed')
        self.assertEqual(done['output']['text'], 'real note\n')
        accepted = api.accept(self.root, request_id)
        self.assertEqual(accepted['state'], 'accepted')
        record = handoff.show_handoff(self.root)['record']
        self.assertEqual(record['observation']['basis_revision'], self.plan['revision'])
        self.assertEqual(record['evidence'][0]['kind'], 'note')
        self.assertEqual(api.resume(self.root, request_id)['state'], 'accepted')
        self.assertEqual(len(handoff.handoff_history(self.root)['revisions']), 3)

    def test_grant_scopes_and_budgets_fail_closed(self):
        from flyfishhep.exceptions import ContractError
        api = self.api()
        for change in [dict(timeout=0), dict(timeout=True), dict(timeout=301), dict(attempt_max=0), dict(attempt_max=2), dict(attempt_max=True)]:
            with self.subTest(change=change), self.assertRaises(ContractError):
                api.prepare(self.root, 'read-file', path='note.txt', **change)
        request = api.prepare(self.root, 'read-file', path='note.txt')['request_id']
        for options in [{}, dict(allow_exec=True), dict(allow_exec=True, scope='python'), dict(allow_exec=True, scope='read-file', timeout=0), dict(allow_exec=True, scope='read-file', timeout=301), dict(allow_exec=True, scope='read-file', attempt_max=2)]:
            with self.subTest(options=options), self.assertRaises(ContractError):
                api.execute(self.root, request, **options)
            self.assertEqual(api.status(self.root, request)['state'], 'prepared')
        api.execute(self.root, request, allow_exec=True, scope='read-file')

    def test_stale_drift_and_stopped_handoff_refuse(self):
        from flyfishhep.exceptions import ContractError
        api = self.api()
        request = api.prepare(self.root, 'read-file', path='note.txt')['request_id']
        (self.root / 'note.txt').write_bytes(b'drift')
        with self.assertRaises(ContractError):
            api.execute(self.root, request, allow_exec=True, scope='read-file')
        (self.root / 'note.txt').write_bytes(b'real note\n')
        latest = handoff.update_handoff(self.root, dict(self.plan['record'], open_questions=['new']), self.plan['revision'])
        with self.assertRaises(ContractError):
            api.execute(self.root, request, allow_exec=True, scope='read-file')
        for record in [dict(latest['record'], decision='human_review'), dict(latest['record'], state='suspended', decision='suspend'), dict(latest['record'], next_check=None)]:
            latest = handoff.update_handoff(self.root, record, latest['revision'])
            with self.assertRaises(ContractError):
                api.prepare(self.root, 'read-file', path='note.txt')

    def test_real_python_example_and_audit(self):
        import shutil
        from flyfishhep import core
        from flyfishhep.exceptions import ContractError
        api = self.api()
        example = Path(__file__).resolve().parents[1] / 'examples' / 'ads3_geodesic'
        shutil.copytree(example, self.root, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.flyfishhep', '__pycache__'))
        with self.assertRaises(ContractError):
            api.prepare(self.root, 'python')
        core.freeze_project(self.root)
        request = api.prepare(self.root, 'python')['request_id']
        done = api.execute(self.root, request, allow_exec=True, scope='python')
        self.assertEqual(done['output']['outcome'], 'criteria_met')
        self.assertEqual(api.accept(self.root, request)['state'], 'accepted')
        audit = api.prepare(self.root, 'audit-run', run_id=done['output']['run_id'])
        audited = api.execute(self.root, audit['request_id'], allow_exec=True, scope='audit-run')
        self.assertEqual(audited['output']['integrity'], 'verified')
        self.assertEqual(api.accept(self.root, audit['request_id'])['state'], 'accepted')
        self.assertEqual(handoff.show_handoff(self.root)['record']['evidence'][-1]['kind'], 'run')

    def test_accept_crash_window_is_idempotent(self):
        from unittest.mock import patch
        api = self.api()
        request = api.prepare(self.root, 'read-file', path='note.txt')['request_id']
        api.execute(self.root, request, allow_exec=True, scope='read-file')
        original = api._write
        def interrupted(path, value):
            if path.name == 'state.json' and value.get('state') == 'accepted':
                raise OSError('crash after durable handoff commit')
            return original(path, value)
        with patch.object(api, '_write', side_effect=interrupted), self.assertRaises(OSError):
            api.accept(self.root, request)
        history = (self.root / 'research.json').read_bytes()
        self.assertEqual(api.accept(self.root, request)['state'], 'accepted')
        self.assertEqual((self.root / 'research.json').read_bytes(), history)

    def test_accept_reconciliation_after_later_suspension(self):
        from unittest.mock import patch
        from flyfishhep.quick import suspend
        api = self.api()
        request = api.prepare(self.root, 'read-file', path='note.txt')['request_id']
        api.execute(self.root, request, allow_exec=True, scope='read-file')
        original = api._write
        def interrupted(path, value):
            if path.name == 'state.json' and value.get('state') == 'accepted':
                raise OSError('state persistence interrupted')
            return original(path, value)
        with patch.object(api, '_write', side_effect=interrupted), self.assertRaises(OSError):
            api.accept(self.root, request)
        current = handoff.show_handoff(self.root)
        suspend(self.root, 'operator stopped after completed acceptance', current['revision'])
        before = (self.root / 'research.json').read_bytes()
        self.assertEqual(api.accept(self.root, request)['state'], 'accepted')
        self.assertEqual((self.root / 'research.json').read_bytes(), before)
        self.assertEqual(handoff.show_handoff(self.root)['record']['state'], 'suspended')

    def test_already_accepted_readback_after_human_review(self):
        api = self.api()
        request = api.prepare(self.root, 'read-file', path='note.txt')['request_id']
        api.execute(self.root, request, allow_exec=True, scope='read-file')
        api.accept(self.root, request)
        current = handoff.show_handoff(self.root)
        handoff.update_handoff(self.root, dict(current['record'], decision='human_review'), current['revision'])
        before = (self.root / 'research.json').read_bytes()
        self.assertEqual(api.accept(self.root, request)['state'], 'accepted')
        self.assertEqual((self.root / 'research.json').read_bytes(), before)

    def test_repeated_execute_never_invokes_tool(self):
        from unittest.mock import patch
        api = self.api()
        request = api.prepare(self.root, 'read-file', path='note.txt')['request_id']
        done = api.execute(self.root, request, allow_exec=True, scope='read-file')
        with patch.object(api, '_inputs', side_effect=AssertionError('must not invoke tool or reread source')):
            self.assertEqual(api.execute(self.root, request), done)
        (self.root / '.flyfishhep/host' / request / 'output.json').write_text('{}')
        from flyfishhep.exceptions import ContractError
        for action in (api.status, api.resume, api.accept, api.execute):
            with self.assertRaises(ContractError):
                action(self.root, request)

    def test_real_process_death_never_repeats_python(self):
        import shutil
        import subprocess
        import sys
        from flyfishhep import core
        from flyfishhep.exceptions import ContractError
        api = self.api()
        example = Path(__file__).resolve().parents[1] / 'examples/ads3_geodesic'
        shutil.copytree(example, self.root, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.flyfishhep', '__pycache__'))
        core.freeze_project(self.root)
        request = api.prepare(self.root, 'python')['request_id']
        script = 'import os,sys; from flyfishhep import hostloop,runner; real=runner.run_project\ndef interrupted(root,allow,**kwargs):\n real(root,allow,**kwargs); os._exit(77)\nrunner.run_project=interrupted\nhostloop.execute(sys.argv[1],sys.argv[2],allow_exec=True,scope="python")'
        process = subprocess.run([sys.executable, '-B', '-c', script, str(self.root), request], capture_output=True)
        self.assertEqual(process.returncode, 77, process.stderr)
        runs = self.root / '.flyfishhep/runs'
        self.assertEqual(len(list(runs.iterdir())), 1)
        with self.assertRaises(ContractError):
            api.execute(self.root, request, allow_exec=True, scope='python')
        # Explicit operator action: investigated process death, release only stale lock.
        (self.root / '.flyfishhep/host/lock').unlink()
        self.assertEqual(api.status(self.root, request)['state'], 'running')
        self.assertEqual(api.resume(self.root, request)['recovery'], 'manual_review')
        with self.assertRaises(ContractError):
            api.execute(self.root, request, allow_exec=True, scope='python')
        self.assertEqual(len(list(runs.iterdir())), 1)

    def test_paths_tamper_and_oversize_refuse(self):
        from flyfishhep.exceptions import ContractError
        api = self.api()
        (self.root / 'alias').symlink_to(self.root / 'note.txt')
        for path in ['../outside', '/etc/passwd', 'alias', 'missing', '.']:
            with self.subTest(path=path), self.assertRaises((ContractError, OSError)):
                api.prepare(self.root, 'read-file', path=path)
        (self.root / 'huge').write_bytes(b'x' * (api.MAX_BYTES + 1))
        with self.assertRaises(ContractError):
            api.prepare(self.root, 'read-file', path='huge')
        request = api.prepare(self.root, 'read-file', path='note.txt')['request_id']
        manifest = self.root / '.flyfishhep/host' / request / 'manifest.json'
        content = json.loads(manifest.read_text())
        content['tool'] = 'python'
        manifest.write_text(json.dumps(content))
        with self.assertRaises(ContractError):
            api.execute(self.root, request, allow_exec=True, scope='python')
        alias = Path(self.temp.name) / 'workspace-alias'
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ContractError):
            api.prepare(alias, 'read-file', path='note.txt')

    def test_state_and_linked_run_tamper_refuse(self):
        from flyfishhep.exceptions import ContractError
        from flyfishhep import core
        import shutil
        api = self.api()
        request = api.prepare(self.root, 'read-file', path='note.txt')['request_id']
        state_path = self.root / '.flyfishhep/host' / request / 'state.json'
        value = json.loads(state_path.read_text())
        if 'payload' in value:
            value['payload']['attempts'] = 99
        else:
            value['attempts'] = 99
        state_path.write_text(json.dumps(value))
        with self.assertRaises(ContractError):
            api.status(self.root, request)
        example = Path(__file__).resolve().parents[1] / 'examples/ads3_geodesic'
        shutil.copytree(example, self.root, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.flyfishhep', '__pycache__'))
        core.freeze_project(self.root)
        request = api.prepare(self.root, 'python')['request_id']
        done = api.execute(self.root, request, allow_exec=True, scope='python')
        output = self.root / '.flyfishhep/runs' / done['output']['run_id'] / 'output/result.json'
        output.write_text('{}')
        for action in (api.status, api.resume, api.accept, api.execute):
            with self.subTest(action=action), self.assertRaises(ContractError):
                action(self.root, request)

    def test_accept_after_pause_or_new_record_never_overwrites(self):
        from flyfishhep.exceptions import ContractError
        api = self.api()
        request = api.prepare(self.root, 'read-file', path='note.txt')['request_id']
        api.execute(self.root, request, allow_exec=True, scope='read-file')
        current = self.plan
        for changes in [dict(open_questions=['new record']), dict(decision='human_review'), dict(state='suspended', decision='suspend')]:
            current = handoff.update_handoff(self.root, dict(current['record'], **changes), current['revision'])
            before = (self.root / 'research.json').read_bytes()
            with self.assertRaises(ContractError):
                api.accept(self.root, request)
            self.assertEqual((self.root / 'research.json').read_bytes(), before)

    def test_binary_read_and_timeout_outcome_is_not_retried(self):
        import time
        from unittest.mock import patch
        from flyfishhep.exceptions import ContractError
        api = self.api()
        (self.root / 'binary').write_bytes(b'\xff\x00')
        request = api.prepare(self.root, 'read-file', path='binary', timeout=1)['request_id']
        done = api.execute(self.root, request, allow_exec=True, scope='read-file')
        self.assertEqual(done['output']['bytes_base64'], '/wA=')
        self.assertNotIn('text', done['output'])
        request = api.prepare(self.root, 'read-file', path='note.txt', timeout=1)['request_id']
        real = api._read
        active = [False]
        def slow(path):
            if path.name == 'note.txt' and active[0]:
                time.sleep(2)
            return real(path)
        # Delay the execution read only, not freeze/hash validation.
        original = api._deadline
        from contextlib import contextmanager
        @contextmanager
        def deadline(seconds):
            with original(seconds):
                active[0] = True
                try:
                    yield
                finally:
                    active[0] = False
        with patch.object(api, '_deadline', side_effect=deadline), patch.object(api, '_read', side_effect=slow):
            with self.assertRaises(ContractError):
                api.execute(self.root, request, allow_exec=True, scope='read-file')
        self.assertEqual(api.status(self.root, request)['state'], 'unknown')
        with self.assertRaises(ContractError):
            api.execute(self.root, request, allow_exec=True, scope='read-file')

    def test_read_snapshot_and_encoding_size_budget(self):
        from flyfishhep.exceptions import ContractError
        api = self.api()
        request = api.prepare(self.root, 'read-file', path='note.txt')['request_id']
        snapshot = self.root / '.flyfishhep/host' / request / 'input.json'
        self.assertTrue(snapshot.is_file(), 'prepare must preserve exact frozen bytes')
        import base64
        self.assertEqual(base64.b64decode(json.loads(snapshot.read_text())['bytes_base64']), b'real note\n')
        snapshot.write_text('{}')
        with self.assertRaises(ContractError):
            api.execute(self.root, request, allow_exec=True, scope='read-file')
        (self.root / 'bounded').write_bytes(b'\x00' * (256 * 1024))
        bounded = api.prepare(self.root, 'read-file', path='bounded')['request_id']
        self.assertEqual(api.execute(self.root, bounded, allow_exec=True, scope='read-file')['state'], 'completed')
        (self.root / 'bounded').write_bytes(b'x' * (256 * 1024 + 1))
        with self.assertRaises(ContractError):
            api.prepare(self.root, 'read-file', path='bounded')

    def test_host_symlink_lock_and_python_input_drift_refuse(self):
        from flyfishhep.exceptions import ContractError
        from flyfishhep import core
        import shutil
        api = self.api()
        directory = self.root / '.flyfishhep'
        directory.mkdir()
        outside = Path(self.temp.name) / 'outside-host'
        outside.mkdir()
        (directory / 'host').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ContractError):
            api.prepare(self.root, 'read-file', path='note.txt')
        self.assertEqual(list(outside.iterdir()), [])
        (directory / 'host').unlink()
        request = api.prepare(self.root, 'read-file', path='note.txt')['request_id']
        lock = directory / 'host/lock'
        lock.write_text('other owner')
        with self.assertRaises(ContractError):
            api.execute(self.root, request, allow_exec=True, scope='read-file')
        self.assertEqual(lock.read_text(), 'other owner')
        lock.unlink()
        example = Path(__file__).resolve().parents[1] / 'examples/ads3_geodesic'
        shutil.copytree(example, self.root, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.flyfishhep', '__pycache__'))
        core.freeze_project(self.root)
        request = api.prepare(self.root, 'python')['request_id']
        with self.assertRaises(ContractError):
            api.execute(self.root, request)
        source = self.root / 'calculation.py'
        source.write_bytes(source.read_bytes() + b'\n# source drift')
        with self.assertRaises(ContractError):
            api.execute(self.root, request, allow_exec=True, scope='python')
        self.assertFalse((directory / 'runs').exists())

    def test_read_rejects_final_component_replaced_after_path_check(self):
        from unittest.mock import patch
        api = self.api()
        outside = Path(self.temp.name) / 'secret'
        outside.write_text('outside')
        target = self.root / 'note.txt'
        original = api._root
        def changed(path):
            checked = original(path)
            if checked == target:
                target.unlink()
                target.symlink_to(outside)
            return checked
        from flyfishhep.exceptions import ContractError
        with patch.object(api, '_root', side_effect=changed):
            with self.assertRaises((ContractError, OSError)):
                api._read(target)

    def test_installed_cli_json_noexec_and_errors(self):
        from test_core import invoke
        prepared = invoke('host', 'prepare', self.root, '--tool', 'read-file', '--file', 'note.txt')
        self.assertEqual(prepared.returncode, 0, prepared.stdout)
        request = json.loads(prepared.stdout)['request_id']
        denied = invoke('host', 'execute', self.root, request)
        self.assertEqual(denied.returncode, 2, denied.stdout)
        self.assertEqual(json.loads(denied.stdout)['status'], 'refused')
        completed = invoke('host', 'execute', self.root, request, '--allow-exec', '--scope', 'read-file')
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertEqual(json.loads(completed.stdout)['state'], 'completed')
        self.assertEqual(json.loads(invoke('host', 'accept', self.root, request).stdout)['state'], 'accepted')
        for args in [('host',), ('host', 'prepare', self.root, '--tool', 'shell'), ('host', 'execute', self.root, request, '--argv', 'sh')]:
            result = invoke(*args)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['status'], 'refused')

    def test_handoff_change_during_input_preflight_refuses(self):
        from unittest.mock import patch
        from flyfishhep.exceptions import ContractError
        api = self.api()
        request = api.prepare(self.root, 'read-file', path='note.txt')['request_id']
        original = api._inputs
        def changed(*args):
            result = original(*args)
            handoff.update_handoff(self.root, dict(self.plan['record'], decision='human_review'), self.plan['revision'])
            return result
        with patch.object(api, '_inputs', side_effect=changed):
            with self.assertRaises(ContractError):
                api.execute(self.root, request, allow_exec=True, scope='read-file')
        self.assertEqual(api.status(self.root, request)['state'], 'prepared')

    def test_python_rechecks_bound_freeze_after_running_commit(self):
        from unittest.mock import patch
        from flyfishhep.exceptions import ContractError
        from flyfishhep import core
        import shutil
        api = self.api()
        example = Path(__file__).resolve().parents[1] / 'examples/ads3_geodesic'
        shutil.copytree(example, self.root, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.flyfishhep', '__pycache__'))
        source = self.root / 'notes.md'
        original_bytes = source.read_bytes()
        other = original_bytes + b'\nchanged input'
        source.write_bytes(other)
        core.freeze_project(self.root)
        source.write_bytes(original_bytes)
        core.freeze_project(self.root)
        request = api.prepare(self.root, 'python')['request_id']
        original_write = api._write
        def changed(path, value):
            result = original_write(path, value)
            if path.name == 'state.json' and value.get('state') == 'running':
                source.write_bytes(other)
            return result
        with patch.object(api, '_write', side_effect=changed):
            with self.assertRaises(ContractError):
                api.execute(self.root, request, allow_exec=True, scope='python')
        self.assertFalse((self.root / '.flyfishhep/runs').exists())
        self.assertEqual(api.status(self.root, request)['state'], 'unknown')

    def test_runner_refuses_freeze_change_after_host_dispatch_precheck(self):
        from unittest.mock import patch
        from flyfishhep import core, runner
        from flyfishhep.exceptions import ContractError
        import shutil
        api = self.api()
        example = Path(__file__).resolve().parents[1] / 'examples/ads3_geodesic'
        shutil.copytree(example, self.root, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.flyfishhep', '__pycache__'))
        source = self.root / 'notes.md'
        approved_bytes = source.read_bytes()
        changed_bytes = approved_bytes + b'\nOrdinary revised research note.\n'
        source.write_bytes(changed_bytes)
        changed_freeze = core.freeze_project(self.root)['freeze_id']
        source.write_bytes(approved_bytes)
        approved_freeze = core.freeze_project(self.root)['freeze_id']
        self.assertNotEqual(approved_freeze, changed_freeze)
        prepared = api.prepare(self.root, 'python')
        self.assertEqual(prepared['manifest']['inputs']['freeze_id'], approved_freeze)
        self.assertEqual(prepared['manifest']['inputs']['runner_sources'], runner.runner_identity())
        real_run = runner.run_project
        def changed_at_runner_entry(*args, **kwargs):
            # Both host prechecks saw A; the runner now selects ordinary freeze B.
            source.write_bytes(changed_bytes)
            return real_run(*args, **kwargs)
        with patch.object(runner, 'run_project', side_effect=changed_at_runner_entry) as dispatch, \
                patch.object(runner.subprocess, 'run', return_value=runner.subprocess.CompletedProcess([], 0)) as launch:
            with self.assertRaises(ContractError):
                api.execute(self.root, prepared['request_id'], allow_exec=True, scope='python')
            launch.assert_not_called()
        dispatch.assert_called_once_with(self.root, True, expected_freeze_id=approved_freeze)
        self.assertFalse((self.root / '.flyfishhep/runs').exists())
        state = api.status(self.root, prepared['request_id'])
        self.assertEqual(state['state'], 'unknown')
        self.assertEqual(state['attempts'], 1)
        self.assertEqual(state['grant'], dict(request_id=prepared['request_id'], scope='python', timeout=30, attempt_max=1))
        self.assertEqual(state['recovery'], 'manual_review')
        with patch.object(runner.subprocess, 'run') as launch:
            for action in (api.execute, api.accept):
                with self.assertRaises(ContractError):
                    action(self.root, prepared['request_id'])
            launch.assert_not_called()

    def test_cli_plugin_json_roundtrip(self):
        import argparse
        api = self.api()
        parser = argparse.ArgumentParser()
        api.register_cli(parser.add_subparsers(dest='command', required=True))
        prepared = api.dispatch(parser.parse_args(['host', 'prepare', str(self.root), '--tool', 'read-file', '--file', 'note.txt']))
        request = prepared['request_id']
        done = api.dispatch(parser.parse_args(['host', 'execute', str(self.root), request, '--allow-exec', '--scope', 'read-file']))
        self.assertEqual(json.loads(json.dumps(done))['output']['text'], 'real note\n')
        self.assertEqual(api.dispatch(parser.parse_args(['host', 'status', str(self.root), request]))['state'], 'completed')
        self.assertEqual(api.dispatch(parser.parse_args(['host', 'resume', str(self.root), request]))['state'], 'completed')
        self.assertEqual(api.dispatch(parser.parse_args(['host', 'accept', str(self.root), request]))['state'], 'accepted')


if __name__ == '__main__':
    unittest.main()
