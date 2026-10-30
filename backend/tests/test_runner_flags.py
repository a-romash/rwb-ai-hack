import json
import tempfile
import unittest
from pathlib import Path

from app.runner import _dependent_paths, _is_app_path

ROOT = Path(__file__).resolve().parents[2]


class DependentPathsTest(unittest.TestCase):
    def test_only_app_paths_have_dependents(self):
        self.assertTrue(_is_app_path('hooks.SlaDeadline'))
        self.assertTrue(_is_app_path('/state_machines/TicketFlow/transitions/0'))
        self.assertTrue(_is_app_path('app.permissions[2]'))
        for path in ('tests/AC-01', 'build/backend', 'screens.TicketList.live', 'stand', 'docs', ''):
            self.assertFalse(_is_app_path(path), path)

    def test_dependents_from_json_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'spec').mkdir()
            (root / 'spec/app.json').write_text((ROOT / 'contracts/fixtures/tickets/app.json').read_text(encoding='utf-8'), encoding='utf-8')
            paths = _dependent_paths(root, {'app': 'spec/app.json'}, 'hooks.SlaDeadline')
            self.assertIn('entities.Ticket.fields.due_at', paths)
            self.assertNotIn('hooks.SlaDeadline', paths)
            self.assertEqual(_dependent_paths(root, {'app': 'spec/app.json'}, 'tests/AC-01'), [])

    def test_broken_specification_does_not_fail_the_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'spec').mkdir()
            (root / 'spec/app.json').write_text(json.dumps({'schema_version': 1}), encoding='utf-8')
            with self.assertLogs(level='ERROR'):
                self.assertEqual(_dependent_paths(root, {'app': 'spec/app.json'}, 'hooks.X'), [])
