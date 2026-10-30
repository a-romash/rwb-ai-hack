import os
import tempfile
import unittest
from unittest.mock import patch, Mock
from types import SimpleNamespace
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import engine, get_session
from app.models import Artifact, Project, StageRun
from app.runs import router


class RunApiTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_path = os.environ.get("WORKSPACES_DIR")
        os.environ["WORKSPACES_DIR"] = self.temp.name
        self.conn = engine.connect()
        self.tx = self.conn.begin()
        self.db = Session(bind=self.conn, join_transaction_mode="create_savepoint")
        self.project = Project(name="Test", requirements="original")
        self.db.add(self.project)
        self.db.flush()
        self.app = FastAPI()
        self.app.include_router(router, prefix="/api")
        self.app.dependency_overrides[get_session] = lambda: self.db
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()
        self.db.close()
        self.tx.rollback()
        self.conn.close()
        self.temp.cleanup()
        if self.old_path is None:
            os.environ.pop("WORKSPACES_DIR", None)
        else:
            os.environ["WORKSPACES_DIR"] = self.old_path

    def test_create_snapshot_list_and_read(self):
        advance = Mock()
        def workspace(base, project_id, run_id, requirements):
            path = Path(base) / str(project_id) / "runs" / str(run_id)
            (path / "input").mkdir(parents=True)
            (path / "input" / "requirements.md").write_text(requirements)
            return path
        with patch.dict("sys.modules", {"app.runner": SimpleNamespace(advance=advance)}), patch("app.runs.create_workspace", side_effect=workspace):
            response = self.client.post(f"/api/projects/{self.project.id}/runs", json={"autonomy": "A2"})
        self.assertEqual(response.status_code, 201, response.text)
        run = response.json()
        self.assertEqual(len(run["stages"]), 8)
        advance.assert_called_once()
        run_id = run["id"]
        self.assertEqual(self.client.get(f"/api/runs/{run_id}").json()["id"], run_id)
        self.assertEqual(len(self.client.get(f"/api/projects/{self.project.id}/runs").json()), 1)
        self.assertEqual(self.client.get(f"/api/runs/{run_id}/files", params={"path": "input/requirements.md"}).text, "original")
        self.assertEqual(self.client.get(f"/api/runs/{run_id}/files", params={"path": "../escape"}).status_code, 422)
        self.assertEqual(self.client.get(f"/api/runs/{run_id}/files", params={"path": "missing"}).status_code, 404)
        self.assertEqual(self.client.get(f"/api/runs/{run_id}/metrics").json()["totals"]["calls"], 0)
        self.assertEqual(self.client.get(f"/api/runs/{run_id}/events").json()[0]["type"], "run.created")
        from sqlalchemy import select
        stage = self.db.scalar(select(StageRun).where(StageRun.run_id == run_id, StageRun.stage == "analysis"))
        stage.status = "succeeded"
        self.db.add(Artifact(run_id=stage.run_id, stage_run_id=stage.id, name="analysis", path="spec/analysis.json", kind="json", hash="abc", size=1))
        self.db.flush()
        self.assertEqual(len(self.client.get(f"/api/runs/{run_id}/artifacts").json()), 1)
        self.db.add(StageRun(run_id=stage.run_id, stage="analysis", attempt=2, status="pending"))
        self.db.flush()
        self.assertEqual(self.client.get(f"/api/runs/{run_id}/artifacts").json(), [])

    def test_missing_and_validation(self):
        self.assertEqual(self.client.get(f"/api/runs/{uuid4()}").status_code, 404)
        self.assertEqual(self.client.get(f"/api/projects/{uuid4()}/runs").status_code, 404)
        self.assertEqual(self.client.post(f"/api/projects/{uuid4()}/runs", json={}).status_code, 404)
        self.assertEqual(self.client.post(f"/api/projects/{self.project.id}/runs", json={"budget": {"tokens": 0}}).status_code, 422)
