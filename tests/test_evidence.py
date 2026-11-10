"""Evidence bindings describe byte identity, not scientific validity."""
import copy
import importlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from flyfishhep import handoff
from flyfishhep.exceptions import ContractError


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'research'
        self.first = handoff.initialize_handoff(self.root, 'task', 'Question?')

    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('flyfishhep.evidence'), 'evidence API missing')
        return importlib.import_module('flyfishhep.evidence')

    def test_file_roundtrip_drift_missing_and_readonly(self):
        api = self.api()
        (self.root / 'note.txt').write_bytes(b'original')
        bound = api.bind_file(self.root, 'e1', 'note.txt', 'line 1', 'reported note', self.first['revision'])
        self.assertEqual(bound['record']['evidence'][0]['binding']['kind'], 'file')
        planned_record = copy.deepcopy(bound['record'])
        planned_record['next_check'] = dict(kind='derivation', question='q', method='m', decision_rule='r')
        planned = handoff.update_handoff(self.root, planned_record, bound['revision'])
        observed_record = copy.deepcopy(planned['record'])
        observed_record['observation'] = dict(basis_revision=planned['revision'], summary='reported', evidence_ids=['e1'])
        handoff.update_handoff(self.root, observed_record, planned['revision'])
        before = (self.root / 'research.json').read_bytes()
        with patch('subprocess.run', side_effect=AssertionError('no execution')), patch('socket.socket', side_effect=AssertionError('no network')):
            checked = api.check_evidence(self.root)
            self.assertEqual(checked['findings'][0]['status'], 'unchanged')
            self.assertTrue(checked['observation_evidence_current'])
            self.assertEqual(checked['scientific_validity'], 'not_assessed')
            (self.root / 'note.txt').write_bytes(b'changed')
            checked = api.check_evidence(self.root)
            self.assertEqual(checked['findings'][0]['status'], 'changed')
            self.assertEqual(checked['affected_observation_evidence_ids'], ['e1'])
            self.assertFalse(checked['observation_evidence_current'])
            (self.root / 'note.txt').unlink()
            self.assertEqual(api.check_evidence(self.root)['findings'][0]['status'], 'missing')
        self.assertEqual((self.root / 'research.json').read_bytes(), before)

    def test_legacy_reference_never_opened_and_chain_preserved(self):
        api = self.api()
        record = copy.deepcopy(self.first['record'])
        record['evidence'] = [dict(id='legacy', kind='source', reference='/private/never-read', summary='report')]
        old = handoff.update_handoff(self.root, record, self.first['revision'])
        raw = (self.root / 'research.json').read_bytes()
        checked = api.check_evidence(self.root)
        self.assertEqual(checked['findings'][0]['status'], 'reported_only')
        self.assertEqual((self.root / 'research.json').read_bytes(), raw)
        (self.root / 'note').write_text('new')
        api.bind_file(self.root, 'new', 'note', 'all', 'new', old['revision'])
        chain = handoff.handoff_history(self.root)['revisions']
        self.assertEqual(chain[:2], json.loads(raw)['revisions'])
        self.assertEqual(chain[2]['parent'], old['revision'])

    def test_binding_and_id_tampering_refused(self):
        api = self.api()
        (self.root / 'note').write_text('x')
        bound = api.bind_file(self.root, 'e1', 'note', 'all', 's', self.first['revision'])
        before = (self.root / 'research.json').read_bytes()
        for changed in [dict(bound['record']['evidence'][0], summary='replacement'), dict(bound['record']['evidence'][0], binding=dict(kind='file', path='../escape', sha256='0'*64, locator='x'))]:
            with self.assertRaises(ContractError):
                handoff.update_handoff(self.root, dict(bound['record'], evidence=[changed]), bound['revision'])
        with self.assertRaises(ContractError):
            api.bind_file(self.root, 'e2', 'note', 'all', 's', self.first['revision'])
        self.assertEqual((self.root / 'research.json').read_bytes(), before)

    def test_real_run_historical_binding_drift_and_tamper(self):
        from flyfishhep import core, runner
        from test_core import CoreTests
        api = self.api()
        fixture = CoreTests()
        self.root = self.root / 'numerical'
        fixture.project = self.root
        fixture.populated()
        self.first = handoff.initialize_handoff(self.root, 'task', 'Question?')
        core.freeze_project(self.root)
        receipt = runner.run_project(self.root, allow_exec=True)
        (self.root / 'calculate.py').write_text('# source drift')
        with patch('subprocess.run', side_effect=AssertionError('no execution')), patch('socket.socket', side_effect=AssertionError('no network')):
            bound = api.bind_run(self.root, 'run1', receipt['run_id'], 'historical run', self.first['revision'])
            checked = api.check_evidence(self.root)
        finding = checked['findings'][0]
        self.assertEqual(finding['status'], 'verified')
        self.assertFalse(finding['current_source_matches'])
        self.assertEqual(bound['record']['evidence'][0]['binding']['freeze_id'], receipt['freeze_id'])
        packet = self.root / '.flyfishhep' / 'runs' / receipt['run_id']
        (packet / 'stdout.txt').write_text('tampered')
        self.assertEqual(api.check_evidence(self.root)['findings'][0]['status'], 'refused')
        with self.assertRaises(ContractError):
            api.bind_run(self.root, 'bad', receipt['run_id'], 'bad', bound['revision'])

    def test_only_used_ids_affected_and_fake_new_binding_refused(self):
        api = self.api()
        (self.root / 'note').write_text('original')
        bound = api.bind_file(self.root, 'used', 'note', 'all', 's', self.first['revision'])
        bound = api.bind_file(self.root, 'unused', 'note', 'all', 's', bound['revision'])
        record = copy.deepcopy(bound['record'])
        record['next_check'] = dict(kind='literature', question='q', method='m', decision_rule='r')
        planned = handoff.update_handoff(self.root, record, bound['revision'])
        record['observation'] = dict(basis_revision=planned['revision'], summary='s', evidence_ids=['used'])
        current = handoff.update_handoff(self.root, record, planned['revision'])
        fake = dict(id='fake', kind='source', reference='note', summary='s', binding=dict(kind='file', path='note', locator='all', sha256='0'*64))
        with self.assertRaises(ContractError):
            handoff.update_handoff(self.root, dict(record, evidence=record['evidence']+[fake]), current['revision'])
        (self.root / 'note').write_text('changed')
        self.assertEqual(api.check_evidence(self.root)['affected_observation_evidence_ids'], ['used'])
        (self.root / 'note').unlink()
        (self.root / 'note').symlink_to(self.root / 'research.json')
        self.assertEqual(api.check_evidence(self.root)['findings'][0]['status'], 'refused')

    def test_legacy_reused_id_invalidates_old_observation(self):
        api = self.api()
        record = copy.deepcopy(self.first['record'])
        record['next_check'] = dict(kind='literature', question='q', method='m', decision_rule='r')
        planned = handoff.update_handoff(self.root, record, self.first['revision'])
        record['evidence'] = [dict(id='old', kind='note', reference='x', summary='old')]
        record['observation'] = dict(basis_revision=planned['revision'], summary='s', evidence_ids=['old'])
        observed = handoff.update_handoff(self.root, record, planned['revision'])
        # A valid legacy schema-1 chain, produced before IDs became immutable.
        document = json.loads((self.root / 'research.json').read_text())
        changed = copy.deepcopy(record)
        changed['evidence'][0]['summary'] = 'different content'
        document['revisions'].append(handoff._entry('task', observed['revision'], changed))
        (self.root / 'research.json').write_text(json.dumps(document))
        report = handoff.show_handoff(self.root)
        self.assertFalse(report['observation_applies_to_current_check'])
        self.assertEqual(report['workflow'], 'perform_check_in_host')
        self.assertFalse(api.check_evidence(self.root)['observation_evidence_current'])
        unchanged = handoff.update_handoff(self.root, dict(changed, open_questions=['new question']), report['revision'])
        self.assertFalse(unchanged['observation_applies_to_current_check'])

    def test_missing_run_and_current_drift_affect_only_observation(self):
        from flyfishhep import core, runner
        from test_core import CoreTests, invoke
        api = self.api()
        self.root = self.root / 'numerical'
        fixture = CoreTests()
        fixture.project = self.root
        fixture.populated()
        first = handoff.initialize_handoff(self.root, 'task', 'q')
        core.freeze_project(self.root)
        receipt = runner.run_project(self.root, allow_exec=True)
        cli = invoke('evidence', 'bind-run', self.root, '--id', 'r1', '--run', receipt['run_id'], '--summary', 's', '--base', first['revision'])
        self.assertEqual(cli.returncode, 0, cli.stdout)
        bound = json.loads(cli.stdout)
        record = copy.deepcopy(bound['record'])
        record['next_check'] = dict(kind='calculation', question='q', method='m', decision_rule='r')
        planned = handoff.update_handoff(self.root, record, bound['revision'])
        record['observation'] = dict(basis_revision=planned['revision'], summary='s', evidence_ids=['r1'])
        handoff.update_handoff(self.root, record, planned['revision'])
        self.assertTrue(api.check_evidence(self.root)['observation_evidence_current'])
        (self.root / 'calculate.py').write_text('# drift')
        checked = api.check_evidence(self.root)
        self.assertEqual(checked['findings'][0]['status'], 'verified')
        self.assertEqual(checked['affected_observation_evidence_ids'], ['r1'])
        self.assertFalse(checked['observation_evidence_current'])
        packet = self.root / '.flyfishhep' / 'runs' / receipt['run_id']
        (packet / 'receipt.json').unlink()
        self.assertEqual(api.check_evidence(self.root)['findings'][0]['status'], 'missing')

    def test_paths_and_oversize_refused(self):
        api = self.api()
        (self.root / 'note').write_text('x')
        (self.root / 'alias').symlink_to(self.root / 'note')
        alias = self.root.parent / 'alias-root'
        alias.symlink_to(self.root, target_is_directory=True)
        for path in ['../note', '/absolute', 'a/../note', 'alias', 'a//b']:
            with self.subTest(path=path), self.assertRaises(ContractError):
                api.bind_file(self.root, 'e', path, 'all', 's', self.first['revision'])
        with self.assertRaises(ContractError):
            api.bind_file(alias / 'child', 'e', 'note', 'all', 's', self.first['revision'])
        with patch('flyfishhep.validation.MAX_FILE_BYTES', 1):
            (self.root / 'note').write_text('too big')
            with self.assertRaises(ContractError):
                api.bind_file(self.root, 'e', 'note', 'all', 's', self.first['revision'])
