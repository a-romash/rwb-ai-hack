"""Requires migrated PostgreSQL; executes stages synchronously, without a worker."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Project, Question, Run, StageRun
from app import runner
from harness.registry import STAGES
from harness.workspace import create_workspace


class RunnerIntegration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project_id, self.run_id = uuid4(), uuid4()
        root = create_workspace(Path(self.temp.name), self.project_id, self.run_id, 'Исходные требования')
        with SessionLocal.begin() as session:
            session.add(Project(id=self.project_id, name='Integration', requirements='Требования'))
            session.add(Run(id=self.run_id, project_id=self.project_id, requirements='Исходные требования',
                            workspace_path=str(root), tokens_limit=1000, minutes_limit=60,
                            config={'fake_stages': True}, autonomy='A2'))
            session.add_all([StageRun(run_id=self.run_id, stage=stage.key, attempt=1, status='pending') for stage in STAGES])

    def tearDown(self):
        with SessionLocal.begin() as session:
            project = session.get(Project, self.project_id)
            session.delete(project)
        self.temp.cleanup()

    def test_fake_run_and_duplicate_delivery(self):
        queued = []
        with patch('app.tasks.run_stage.apply_async', side_effect=lambda args, queue: queued.append(args[0])):
            runner.advance(self.run_id)
            while queued:
                stage_id = queued.pop(0)
                runner.execute(stage_id)
                runner.execute(stage_id)
        with SessionLocal() as session:
            run = session.get(Run, self.run_id)
            stages = session.scalars(select(StageRun).where(StageRun.run_id == self.run_id)).all()
            self.assertEqual(run.status, 'partial')  # Missing real gates mean checks were not run.
            self.assertEqual(len(stages), 8)
            self.assertTrue(all(stage.status == 'succeeded' for stage in stages))

    def test_answer_is_forwarded_and_queued(self):
        with SessionLocal.begin() as session:
            run = session.get(Run, self.run_id)
            run.status = 'waiting'
            stage = session.scalar(select(StageRun).where(StageRun.run_id == self.run_id, StageRun.stage == 'analysis'))
            stage.status = 'waiting_input'
            session.add(Question(run_id=self.run_id, stage_run_id=stage.id, qid='Q-01', payload={'id': 'Q-01'}))
        with patch('app.tasks.run_stage.apply_async') as enqueue:
            runner.answer(self.run_id, {'Q-01': 'Да'})
            enqueue.assert_called_once()
        with SessionLocal() as session:
            stage = session.scalar(select(StageRun).where(StageRun.run_id == self.run_id, StageRun.stage == 'analysis'))
            question = session.scalar(select(Question).where(Question.run_id == self.run_id))
            self.assertEqual(stage.status, 'queued')
            self.assertEqual(question.answer, 'Да')

    def test_failed_stage_still_runs_report_with_failed_snapshot(self):
        from harness.fake_stages import analysis, report
        original = report.execute
        snapshots = []
        def record(inp, *args):
            snapshots.append(inp.snapshot)
            return original(inp, *args)
        queued = []
        with patch.object(analysis, 'execute', side_effect=RuntimeError('сломано')), patch.object(report, 'execute', side_effect=record), patch('app.tasks.run_stage.apply_async', side_effect=lambda args, queue: queued.append(args[0])):
            runner.advance(self.run_id)
            while queued:
                runner.execute(queued.pop(0))
        with SessionLocal() as session:
            self.assertEqual(session.get(Run, self.run_id).status, 'failed')
        self.assertEqual(snapshots[0]['status'], 'failed')

    def test_publish_failure_keeps_queued(self):
        with patch('app.tasks.run_stage.apply_async', side_effect=RuntimeError('offline')):
            runner.advance(self.run_id)
        with SessionLocal() as session:
            stage = session.scalar(select(StageRun).where(StageRun.run_id == self.run_id, StageRun.stage == 'analysis'))
            self.assertEqual(stage.status, 'queued')

    def test_secret_is_redacted(self):
        import os
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-secret-value'}):
            self.assertNotIn('test-secret-value', runner._safe_error(RuntimeError('key test-secret-value')))

    def test_dependents_contract(self):
        import sys
        from types import SimpleNamespace
        from contracts.stage import ContractError
        root = Path(self.temp.name)
        (root / 'app.json').write_text('{"schema_version":1}', encoding='utf-8')
        module = SimpleNamespace(dependents=lambda app, path: ['hooks.Fix', path, 'hooks.Fix'])
        with patch.dict(sys.modules, {'contracts.app': module}):
            self.assertEqual(runner._dependent_paths(root, {'app': 'app.json'}, 'entities.E'), ['hooks.Fix'])
        self.assertEqual(runner._dependent_paths(root, {}, 'entities.E'), [])
        with patch.dict(sys.modules, {'contracts.app': SimpleNamespace(dependents=lambda *_: 'wrong')}):
            with self.assertRaises(ContractError):
                runner._dependent_paths(root, {'app': 'app.json'}, 'entities.E')
