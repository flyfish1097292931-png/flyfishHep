"""Handoff acceptance tests: records are reports, never execution evidence."""
import copy
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from flyfishhep.exceptions import ContractError
from test_core import invoke


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'research'

    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('flyfishhep.handoff'), 'handoff API missing')
        return importlib.import_module('flyfishhep.handoff')

    def init(self):
        return self.api().initialize_handoff(self.root, 'analytic-task', 'Which assumptions imply the identity?')

    def safety(self, result):
        self.assertIs(result['automatic_execution'], False)
        self.assertIs(result['execution_authorized'], False)
        self.assertEqual(result['scientific_validity'], 'not_assessed')
        self.assertEqual(result['publication'], 'human-only')
        self.assertEqual(result['evidence_verification'], 'reported_only')

    def test_cumulative_size_refusal_preserves_readable_history(self):
        from flyfishhep.validation import MAX_FILE_BYTES
        first = self.init()
        record = copy.deepcopy(first['record'])
        record['open_questions'] = ['x' * (MAX_FILE_BYTES // 2)]
        second = self.api().update_handoff(self.root, record, first['revision'])
        before = (self.root / 'research.json').read_bytes()
        with self.assertRaises(ContractError):
            self.api().update_handoff(self.root, record, second['revision'])
        self.assertEqual((self.root / 'research.json').read_bytes(), before)
        self.assertEqual(self.api().show_handoff(self.root)['revision'], second['revision'])
        self.assertFalse((self.root / 'research.json.lock').exists())

    def test_cli_roundtrip_and_history(self):
        result = invoke('handoff', 'init', self.root, '--id', 'literature', '--question', 'What is known?')
        self.assertEqual(result.returncode, 0, result.stderr)
        first = json.loads(result.stdout)
        exported = invoke('handoff', 'show', self.root, '--record-only')
        record = json.loads(exported.stdout)
        self.assertEqual(record, first['record'])
        record['next_check'] = dict(kind='literature', question='Is there a counterexample?', method='Read source', decision_rule='Revise if found')
        record['open_questions'] = ['Are assumptions necessary?']
        source = Path(self.temp.name) / 'edit.json'
        source.write_text(json.dumps(record))
        updated = invoke('handoff', 'update', self.root, '--from', source, '--base', first['revision'])
        self.assertEqual(updated.returncode, 0, updated.stdout)
        second = json.loads(updated.stdout)
        self.safety(second)
        self.assertEqual(second['workflow'], 'perform_check_in_host')
        self.assertEqual(json.loads(invoke('handoff', 'show', self.root).stdout), second)
        history = json.loads(invoke('handoff', 'history', self.root).stdout)
        self.safety(history)
        self.assertEqual([x['revision'] for x in history['revisions']], [first['revision'], second['revision']])
        self.assertEqual(history['revisions'][1]['parent'], first['revision'])
        before = (self.root / 'research.json').read_bytes()
        stale = invoke('handoff', 'update', self.root, '--from', source, '--base', first['revision'])
        self.assertEqual(stale.returncode, 2)
        self.assertEqual((self.root / 'research.json').read_bytes(), before)

    def plan(self, result):
        record = copy.deepcopy(result['record'])
        record['next_check'] = dict(kind='derivation', question='Does the identity follow?', method='Expand both sides', decision_rule='Revise on mismatch')
        return record

    def test_record_contract_refusals_preserve_bytes(self):
        first = self.init()
        base = first['record']
        cases = [dict(mode='confirm'), dict(question=' '), dict(mode=[]), dict(state='suspended'),
                 dict(decision='suspend'), dict(assumptions='x'), dict(open_questions=[1]),
                 dict(requested_actions=[None]), dict(stop_conditions={}), dict(evidence={}),
                 dict(execution_authorized=True), dict(next_check={}), dict(observation={}),
                 dict(evidence=[dict(id='../bad', kind='note', reference='x', summary='x')]),
                 dict(evidence=[dict(id='ok', kind='verified', reference='x', summary='x')]),
                 dict(evidence=[dict(id='ok', kind='note', reference='', summary='x')]),
                 dict(evidence=[dict(id='ok', kind='note', reference='x', summary='x')]*2),
                 dict(observation=dict(basis_revision='unknown', summary='done', evidence_ids=[]))]
        before = (self.root / 'research.json').read_bytes()
        for change in cases:
            with self.subTest(change=change):
                record = dict(base, **change)
                with self.assertRaises(ContractError):
                    self.api().update_handoff(self.root, record, first['revision'])
                self.assertEqual((self.root / 'research.json').read_bytes(), before)
        for project_id, question in [('../bad', 'q'), ('ok', ''), (False, 'q')]:
            with self.assertRaises(ContractError):
                self.api().initialize_handoff(Path(self.temp.name) / 'invalid', project_id, question)

    def test_confirmation_change_requires_explore_revise(self):
        first = self.init()
        record = self.plan(first)
        record['mode'] = 'confirm'
        confirmed = self.api().update_handoff(self.root, record, first['revision'])
        for key, value in [('question', 'new target'), ('assumptions', ['new']), ('next_check', dict(record['next_check'], method='new method'))]:
            for mode, decision in [('confirm', 'continue'), ('explore', 'continue'), ('confirm', 'revise')]:
                changed = dict(record, **{key: value}, mode=mode, decision=decision)
                with self.subTest(key=key, mode=mode, decision=decision), self.assertRaises(ContractError):
                    self.api().update_handoff(self.root, changed, confirmed['revision'])
        changed = dict(record, question='new target', mode='explore', decision='revise')
        revised = self.api().update_handoff(self.root, changed, confirmed['revision'])
        self.assertEqual(revised['record'], changed)
        self.assertEqual(self.api().handoff_history(self.root)['revisions'][1]['record'], record)

    def test_observation_binding_and_workflow_do_not_reuse_old_results(self):
        first = self.init()
        record = self.plan(first)
        for basis in [first['revision'], '0'*64]:
            bad = dict(record, observation=dict(basis_revision=basis, summary='done', evidence_ids=[]))
            with self.assertRaises(ContractError):
                self.api().update_handoff(self.root, bad, first['revision'])
        planned = self.api().update_handoff(self.root, record, first['revision'])
        record['evidence'] = [dict(id='note-1', kind='note', reference='/not/read', summary='Reported algebra')]
        record['observation'] = dict(basis_revision=planned['revision'], summary='Reported identity', evidence_ids=['missing'])
        with self.assertRaises(ContractError):
            self.api().update_handoff(self.root, record, planned['revision'])
        record['observation']['evidence_ids'] = ['note-1']
        observed = self.api().update_handoff(self.root, record, planned['revision'])
        self.assertTrue(observed['observation_applies_to_current_check'])
        self.assertEqual(observed['workflow'], 'review_observation')
        for key, value in [('question', 'different question'), ('assumptions', ['different']), ('next_check', dict(record['next_check'], method='different method'))]:
            changed = dict(record, **{key: value})
            observed = self.api().update_handoff(self.root, changed, observed['revision'])
            self.assertFalse(observed['observation_applies_to_current_check'])
            self.assertEqual(observed['workflow'], 'perform_check_in_host')
        changed['decision'] = 'human_review'
        reviewed = self.api().update_handoff(self.root, changed, observed['revision'])
        self.assertEqual(reviewed['workflow'], 'human_review')
        changed.update(state='suspended', decision='suspend')
        suspended = self.api().update_handoff(self.root, changed, reviewed['revision'])
        self.assertEqual(suspended['workflow'], 'suspend')
        self.safety(suspended)

    def test_entire_chain_is_validated_on_every_read_and_update(self):
        first = self.init()
        second = self.api().update_handoff(self.root, self.plan(first), first['revision'])
        third = self.api().update_handoff(self.root, dict(second['record'], decision='human_review'), second['revision'])
        target = self.root / 'research.json'
        original = json.loads(target.read_text())
        cases = []
        for field, value in [('project_id', 'changed'), ('schema_version', True), ('extra', 1), ('revisions', [])]:
            cases.append(dict(original, **{field: value}))
        for index, field, value in [(0, 'parent', 'bad'), (1, 'parent', None), (0, 'revision', 'bad'), (0, 'extra', 1)]:
            bad = copy.deepcopy(original)
            bad['revisions'][index][field] = value
            cases.append(bad)
        bad = copy.deepcopy(original)
        bad['revisions'].reverse()
        cases.append(bad)
        # A recomputed hash does not bypass the record or historical observation contract.
        for change in [dict(mode='confirm'), dict(observation=dict(basis_revision=second['revision'], summary='future', evidence_ids=[]))]:
            bad = copy.deepcopy(original)
            bad['revisions'][0]['record'].update(change)
            parent = None
            for entry in bad['revisions']:
                entry['parent'] = parent
                entry['revision'] = hashlib.sha256(json.dumps(dict(project_id=bad['project_id'], parent=parent, record=entry['record']), sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
                parent = entry['revision']
            cases.append(bad)
        for bad in cases:
            target.write_text(json.dumps(bad))
            before = target.read_bytes()
            for operation in [lambda: self.api().show_handoff(self.root), lambda: self.api().handoff_history(self.root), lambda: self.api().update_handoff(self.root, third['record'], third['revision'])]:
                with self.subTest(bad=bad), self.assertRaises(ContractError):
                    operation()
                self.assertEqual(target.read_bytes(), before)

    def test_invalid_json_and_payloads_refuse_without_writes(self):
        first = self.init()
        target = self.root / 'research.json'
        original = target.read_bytes()
        for raw in ['{"schema_version":1,"schema_version":1}', '{"x":NaN}', '{"x":1e9999}', '['*140 + '0' + ']'*140]:
            target.write_text(raw)
            with self.assertRaises(ContractError):
                self.api().show_handoff(self.root)
            target.write_bytes(original)
            source = Path(self.temp.name) / 'bad.json'
            source.write_text(raw)
            result = invoke('handoff', 'update', self.root, '--from', source, '--base', first['revision'])
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['status'], 'refused')
            self.assertEqual(target.read_bytes(), original)
        nested = []
        for _ in range(140):
            nested = [nested]
        for record in [dict(first['record'], question=nested), dict(first['record'], question=float('nan'))]:
            with self.assertRaises(ContractError):
                self.api().update_handoff(self.root, record, first['revision'])
            self.assertEqual(target.read_bytes(), original)

    def test_exploration_cannot_be_relabelled_confirmation(self):
        first = self.init()
        planned = self.api().update_handoff(self.root, self.plan(first), first['revision'])
        observation = dict(basis_revision=planned['revision'], summary='Reported result', evidence_ids=[])
        observed = self.api().update_handoff(self.root, dict(planned['record'], observation=observation), planned['revision'])
        before = (self.root / 'research.json').read_bytes()
        with self.assertRaises(ContractError):
            self.api().update_handoff(self.root, dict(observed['record'], mode='confirm'), observed['revision'])
        self.assertEqual((self.root / 'research.json').read_bytes(), before)
        confirmed = self.api().update_handoff(self.root, dict(observed['record'], mode='confirm', observation=None), observed['revision'])
        self.assertEqual(confirmed['workflow'], 'perform_check_in_host')
        with self.assertRaises(ContractError):
            self.api().update_handoff(self.root, dict(confirmed['record'], observation=observation), confirmed['revision'])
        observation['basis_revision'] = confirmed['revision']
        checked = self.api().update_handoff(self.root, dict(confirmed['record'], observation=observation), confirmed['revision'])
        self.assertEqual(checked['workflow'], 'review_observation')
        revised = self.api().update_handoff(self.root, dict(checked['record'], mode='explore', decision='revise', question='new'), checked['revision'])
        new_confirmation = self.api().update_handoff(self.root, dict(revised['record'], mode='confirm', observation=None), revised['revision'])
        with self.assertRaises(ContractError):
            self.api().update_handoff(self.root, dict(new_confirmation['record'], observation=observation), new_confirmation['revision'])
        # Even a prior matching confirmation cannot be carried through an explore->confirm transition.
        back = self.api().update_handoff(self.root, dict(checked['record'], mode='explore', decision='revise'), new_confirmation['revision'])
        with self.assertRaises(ContractError):
            self.api().update_handoff(self.root, dict(back['record'], mode='confirm'), back['revision'])

    def test_atomic_locking_and_existing_research_preserved(self):
        first = self.init()
        target = self.root / 'research.json'
        lock = self.root / 'research.json.lock'
        before = target.read_bytes()
        with self.assertRaises(ContractError):
            self.init()
        self.assertEqual(target.read_bytes(), before)
        lock.write_text('someone else')
        for operation in [lambda: self.init(), lambda: self.api().update_handoff(self.root, self.plan(first), first['revision']), lambda: self.api().show_handoff(self.root), lambda: self.api().handoff_history(self.root)]:
            with self.assertRaises(ContractError):
                operation()
            self.assertEqual(lock.read_text(), 'someone else')
            self.assertEqual(target.read_bytes(), before)
        lock.unlink()
        with patch('os.replace', side_effect=OSError('injected atomic replacement failure')):
            with self.assertRaises(OSError):
                self.api().update_handoff(self.root, self.plan(first), first['revision'])
        self.assertEqual(target.read_bytes(), before)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['research.json'])
        # A second writer must fail rather than wait or remove the first writer's lock.
        import os
        real_replace = os.replace
        def competing_replace(source, destination):
            self.assertEqual(Path(source).parent, self.root)
            self.assertTrue(lock.exists())
            with self.assertRaises(ContractError):
                self.api().update_handoff(self.root, first['record'], first['revision'])
            self.assertTrue(lock.exists())
            real_replace(source, destination)
        with patch('os.replace', side_effect=competing_replace):
            second = self.api().update_handoff(self.root, self.plan(first), first['revision'])
        self.assertFalse(lock.exists())
        self.assertEqual(self.api().show_handoff(self.root), second)

    def test_symlinks_and_traversal_are_refused(self):
        first = self.init()
        target = self.root / 'research.json'
        before = target.read_bytes()
        alias = Path(self.temp.name) / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        roots = [alias, alias / 'child', self.root / '..' / 'research']
        for root in roots:
            for operation in [lambda: self.api().initialize_handoff(root, 'x', 'q'), lambda: self.api().show_handoff(root), lambda: self.api().handoff_history(root), lambda: self.api().update_handoff(root, first['record'], first['revision'])]:
                with self.subTest(root=str(root)), self.assertRaises(ContractError):
                    operation()
        outside = Path(self.temp.name) / 'outside.json'
        outside.write_bytes(before)
        target.unlink()
        target.symlink_to(outside)
        for operation in [lambda: self.init(), lambda: self.api().show_handoff(self.root), lambda: self.api().update_handoff(self.root, first['record'], first['revision'])]:
            with self.assertRaises(ContractError):
                operation()
        self.assertEqual(outside.read_bytes(), before)
        target.unlink()
        target.write_bytes(before)
        lock = self.root / 'research.json.lock'
        lock.symlink_to(Path(self.temp.name) / 'nonexistent')
        for operation in [lambda: self.init(), lambda: self.api().show_handoff(self.root), lambda: self.api().update_handoff(self.root, first['record'], first['revision'])]:
            with self.assertRaises(ContractError):
                operation()
            self.assertTrue(lock.is_symlink())
        self.assertEqual(target.read_bytes(), before)

    def test_attach_preserves_numerical_evidence_and_never_executes(self):
        from flyfishhep import core, runner
        from test_core import CoreTests
        fixture = CoreTests()
        fixture.project = self.root
        fixture.populated()
        core.freeze_project(self.root)
        receipt = runner.run_project(self.root, allow_exec=True)
        before = {str(path.relative_to(self.root)): path.read_bytes()
                  for path in self.root.rglob('*') if path.is_file()}
        with patch('subprocess.run', side_effect=AssertionError('no subprocess')), patch('subprocess.Popen', side_effect=AssertionError('no process')), patch('socket.socket', side_effect=AssertionError('no network')):
            first = self.init()
            record = self.plan(first)
            record['evidence'] = [dict(id='reported-run', kind='run', reference=receipt['run_id'], summary='Not audited by handoff')]
            record['requested_actions'] = ['run arbitrary.py', 'publish paper']
            updated = self.api().update_handoff(self.root, record, first['revision'])
            self.safety(updated)
            self.safety(self.api().show_handoff(self.root))
            self.safety(self.api().handoff_history(self.root))
        for name, content in before.items():
            self.assertEqual((self.root / name).read_bytes(), content, name)
        self.assertNotIn('allowed', updated)

    def test_update_reads_latest_state_inside_lock(self):
        import os
        first = self.init()
        target = self.root / 'research.json'
        original = target.read_bytes()
        second = self.api().update_handoff(self.root, self.plan(first), first['revision'])
        advanced = target.read_bytes()
        target.write_bytes(original)
        real_open = os.open
        def advance_before_lock(path, flags, *args, **kwargs):
            if str(path).endswith('research.json.lock'):
                target.write_bytes(advanced)
            return real_open(path, flags, *args, **kwargs)
        with patch('os.open', side_effect=advance_before_lock):
            with self.assertRaises(ContractError):
                self.api().update_handoff(self.root, first['record'], first['revision'])
        self.assertEqual(target.read_bytes(), advanced)
        self.assertEqual(self.api().show_handoff(self.root), second)

    def test_cli_argument_refusals_are_json(self):
        for args in [('handoff',), ('handoff', 'init', self.root), ('handoff', 'unknown', self.root), ('handoff', 'show', self.root, '--bad')]:
            with self.subTest(args=args):
                result = invoke(*args)
                self.assertEqual(result.returncode, 2)
                self.assertTrue(result.stdout.strip(), 'refusals must be JSON on stdout')
                self.assertEqual(json.loads(result.stdout)['status'], 'refused')

    def test_lock_cleanup_does_not_remove_replacement_lock(self):
        first = self.init()
        lock = self.root / 'research.json.lock'
        def replace_lock(source, target):
            lock.unlink()
            lock.write_text('another owner')
            raise OSError('replacement interrupted')
        with patch('os.replace', side_effect=replace_lock):
            with self.assertRaises(OSError):
                self.api().update_handoff(self.root, self.plan(first), first['revision'])
        self.assertTrue(lock.exists(), 'cleanup must only remove its own lock inode')
        self.assertEqual(lock.read_text(), 'another owner')

    def test_initialize_show_without_project(self):
        result = self.init()
        self.assertFalse((self.root / 'project.json').exists())
        self.assertEqual(result, self.api().show_handoff(self.root))
        self.safety(result)
        self.assertEqual(result['workflow'], 'define_check')
        self.assertEqual(result['record'], dict(question='Which assumptions imply the identity?', mode='explore', state='active', assumptions=[], open_questions=[], evidence=[], next_check=None, observation=None, decision='continue', requested_actions=[], stop_conditions=[]))
        stored = json.loads((self.root / 'research.json').read_text())
        entry = stored['revisions'][0]
        canonical = json.dumps(dict(project_id='analytic-task', parent=None, record=result['record']), sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
        self.assertEqual(entry['revision'], hashlib.sha256(canonical).hexdigest())
        self.assertIsNone(entry['parent'])
