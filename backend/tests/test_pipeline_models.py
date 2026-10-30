import unittest
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import engine
from app.models import Artifact, LLMCall, Project, Question, Run, StageRun, TestHash


class PipelineModelsTest(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.session = Session(bind=self.connection, join_transaction_mode="create_savepoint")
        project = Project(name="Test", requirements="original")
        self.session.add(project)
        self.session.flush()
        self.run = Run(project_id=project.id, requirements=project.requirements, workspace_path="/tmp/run",
                       tokens_limit=100, minutes_limit=1)
        self.session.add(self.run)
        self.session.flush()
        self.stage = StageRun(run_id=self.run.id, stage="analysis", attempt=1)
        self.session.add(self.stage)
        self.session.flush()

    def tearDown(self):
        self.session.close()
        self.transaction.rollback()
        self.connection.close()

    def assert_duplicate(self, first, duplicate):
        self.session.add(first)
        self.session.flush()
        with self.assertRaises(IntegrityError):
            with self.session.begin_nested():
                self.session.add(duplicate)
                self.session.flush()

    def test_unique_stage_attempt(self):
        with self.assertRaises(IntegrityError):
            with self.session.begin_nested():
                self.session.add(StageRun(run_id=self.run.id, stage="analysis", attempt=1))
                self.session.flush()
        self.session.add(StageRun(run_id=self.run.id, stage="analysis", attempt=2))
        self.session.flush()

    def test_unique_artifact_question_and_hash(self):
        def artifact():
            return Artifact(run_id=self.run.id, stage_run_id=self.stage.id, name="analysis", path="x", kind="json", hash="a", size=1)
        def question():
            return Question(run_id=self.run.id, stage_run_id=self.stage.id, qid="Q-1", payload={})
        def test_hash():
            return TestHash(run_id=self.run.id, path="tests/a", hash="a", reason="redproof")
        for factory in (artifact, question, test_hash):
            self.assert_duplicate(factory(), factory())

    def test_unknown_usage_stays_null(self):
        call = LLMCall(run_id=self.run.id, stage_run_id=self.stage.id, task_class="qa", provider="fake", model="fake", context_profile="M")
        self.session.add(call)
        self.session.flush()
        self.session.refresh(call)
        self.assertIsNone(call.tokens_in)
        self.assertIsNone(call.tokens_out)
        self.assertEqual(call.status, "started")
