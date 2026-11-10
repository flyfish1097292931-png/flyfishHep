"""Shortcut acceptance tests exercise the real JSON CLI and write gate."""
import json
from pathlib import Path
import tempfile
import unittest

from flyfishhep import handoff
from test_core import invoke


class QuickTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'research'
        self.first = handoff.initialize_handoff(self.root, 'task', 'Main question?')

    def call(self, *args):
        result = invoke(*args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_question_plan_observe_suspend_cli_loop(self):
        added = self.call('handoff', 'question', self.root, '--text', 'Open question?', '--base', self.first['revision'])
        self.assertEqual(added['record']['question'], 'Main question?')
        self.assertEqual(added['record']['open_questions'], ['Open question?'])
        planned = self.call('handoff', 'plan', self.root, '--kind', 'derivation', '--question', 'Subquestion?', '--method', 'Expand', '--rule', 'Revise on mismatch', '--confirm', '--base', added['revision'])
        self.assertEqual(planned['record']['mode'], 'confirm')
        observed = self.call('handoff', 'observe', self.root, '--basis', planned['revision'], '--summary', 'Reported calculation', '--base', planned['revision'], '--decision', 'human_review')
        self.assertEqual(observed['workflow'], 'human_review')
        self.assertFalse(observed['execution_authorized'])
        self.assertEqual(observed['scientific_validity'], 'not_assessed')
        suspended = self.call('handoff', 'suspend', self.root, '--reason', 'Needs input', '--base', observed['revision'])
        self.assertEqual(suspended['workflow'], 'suspend')
        self.assertIn('Needs input', suspended['record']['stop_conditions'])
        self.assertEqual(handoff.show_handoff(self.root), suspended)

    def test_plan_change_requires_separate_reconfirmation(self):
        args = ('handoff', 'plan', self.root, '--kind', 'literature', '--question', 'q', '--method', 'Read', '--rule', 'r')
        confirmed = self.call(*args, '--confirm', '--base', self.first['revision'])
        before = (self.root / 'research.json').read_bytes()
        refused = invoke(*args, '--method', 'Different', '--confirm', '--base', confirmed['revision'])
        self.assertEqual(refused.returncode, 2)
        self.assertEqual((self.root / 'research.json').read_bytes(), before)
        revised = self.call(*args, '--method', 'Different', '--base', confirmed['revision'])
        self.assertEqual(revised['record']['mode'], 'explore')
        self.assertEqual(revised['record']['decision'], 'revise')
        self.assertEqual(revised['record']['question'], 'Main question?')

    def test_old_base_and_unknown_evidence_refuse_without_writes(self):
        planned = self.call('handoff', 'plan', self.root, '--kind', 'derivation', '--question', 'q', '--method', 'm', '--rule', 'r', '--base', self.first['revision'])
        before = (self.root / 'research.json').read_bytes()
        cases = [('question', '--text', 'x', '--base', self.first['revision']),
                 ('observe', '--summary', 's', '--basis', planned['revision'], '--evidence', 'absent', '--base', planned['revision']),
                 ('suspend', '--reason', 'x', '--base', self.first['revision'])]
        for operation, *args in cases:
            result = invoke('handoff', operation, self.root, *args)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertEqual((self.root / 'research.json').read_bytes(), before)

    def test_evidence_cli_and_repeated_observe_evidence(self):
        (self.root / 'note').write_text('notes')
        bound = self.call('evidence', 'bind-file', self.root, '--id', 'e1', '--file', 'note', '--locator', 'all', '--summary', 's', '--base', self.first['revision'])
        bound = self.call('evidence', 'bind-file', self.root, '--id', 'e2', '--file', 'note', '--locator', 'all', '--summary', 's', '--base', bound['revision'])
        planned = self.call('handoff', 'plan', self.root, '--kind', 'literature', '--question', 'q', '--method', 'm', '--rule', 'r', '--base', bound['revision'])
        observed = self.call('handoff', 'observe', self.root, '--basis', planned['revision'], '--summary', 's', '--evidence', 'e1', '--evidence', 'e2', '--base', planned['revision'])
        self.assertEqual(observed['record']['observation']['evidence_ids'], ['e1', 'e2'])
        checked = self.call('evidence', 'check', self.root)
        self.assertEqual(checked['status'], 'checked')
        self.assertTrue(checked['observation_evidence_current'])
        (self.root / 'note').unlink()
        checked = self.call('evidence', 'check', self.root)
        self.assertEqual(checked['findings'][0]['status'], 'missing')
        self.assertFalse(checked['observation_evidence_current'])
