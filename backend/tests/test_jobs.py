import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.database import get_session
from app.main import app
from app.tasks import celery_app, execute_agent, resolve_agent


class Reply:
    def __init__(self, text):
        self.text = text
        self.messages = None

    def complete(self, messages, tools=None, response_format=None):
        self.messages = messages
        return {
            "model": "qwen/qwen3.8-27b",
            "finish_reason": "stop",
            "attempts": 1,
            "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5, "cost": 0},
            "message": {"role": "assistant", "content": self.text},
        }


class ExecuteTest(unittest.TestCase):
    def test_task_registered(self):
        self.assertIn("pipeline.run_agent", celery_app.tasks)

    def test_analyst_runs_in_a_workspace(self):
        reply = Reply('{"summary":"готово"}')
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["WORKSPACES_DIR"] = tmp
            try:
                result = execute_agent("секрет задачи", "analyst", "project-1", client=reply)
            finally:
                os.environ.pop("WORKSPACES_DIR", None)
            self.assertTrue(os.path.isdir(os.path.join(tmp, "project-1")))
        self.assertEqual(result["agent"], "analyst")
        self.assertEqual(result["subtype"], "success")
        self.assertIn("готово", result["result"])
        self.assertNotIn("messages", result)
        self.assertEqual(reply.messages[1]["content"], "секрет задачи")
        self.assertNotIn("секрет задачи", reply.messages[0]["content"])

    def test_agent_names_and_workspace_escape(self):
        self.assertEqual(resolve_agent("developer").name, "developer")
        for name in ("missing", "../harness", "Analyst"):
            with self.subTest(name=name):
                with self.assertRaises(LookupError):
                    resolve_agent(name)
        reply = Reply('{"summary":"x"}')
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["WORKSPACES_DIR"] = tmp
            try:
                with self.assertRaises(LookupError):
                    execute_agent("x", "analyst", "..", client=reply)
            finally:
                os.environ.pop("WORKSPACES_DIR", None)


class JobsApiTest(unittest.TestCase):
    def setUp(self):
        self.project = SimpleNamespace(id=uuid4(), requirements="Требования проекта")

        def get(model, ident):
            return self.project if ident == self.project.id else None

        def session():
            yield SimpleNamespace(get=get)

        app.dependency_overrides[get_session] = session
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def test_enqueue_and_read(self):
        url = f"/api/projects/{self.project.id}/jobs"
        with patch("app.projects.run_agent.delay", return_value=SimpleNamespace(id="job-1")) as delay:
            created = self.client.post(url, json={"agent": "analyst"})
        self.assertEqual(created.status_code, 202, created.text)
        self.assertEqual(created.json()["status"], "queued")
        delay.assert_called_once_with("Требования проекта", "analyst", str(self.project.id))

        with patch("app.projects.run_agent.delay", return_value=SimpleNamespace(id="job-2")) as delay:
            custom = self.client.post(url, json={"agent": "developer", "prompt": "Своя задача"})
        self.assertEqual(custom.status_code, 202, custom.text)
        delay.assert_called_once_with("Своя задача", "developer", str(self.project.id))

        payload = {"agent": "analyst", "subtype": "success", "result": '{"summary":"готово"}', "num_turns": 1}
        with patch("app.projects.run_agent.AsyncResult", return_value=SimpleNamespace(state="SUCCESS", result=payload)):
            done = self.client.get(url + "/job-1")
        self.assertEqual(done.status_code, 200, done.text)
        self.assertEqual(done.json()["status"], "success")
        self.assertEqual(done.json()["result"], payload["result"])
        self.assertEqual(done.json()["num_turns"], 1)

        with patch("app.projects.run_agent.AsyncResult", return_value=SimpleNamespace(state="STARTED", result=None)):
            started = self.client.get(url + "/job-2")
        self.assertEqual(started.json()["status"], "started")
        self.assertIsNone(started.json()["result"])

    def test_missing_agent_broker_and_project(self):
        url = f"/api/projects/{self.project.id}/jobs"
        self.assertEqual(self.client.post(url, json={"agent": "ghost"}).status_code, 404)
        self.assertEqual(self.client.post(url, json={"agent": "../harness"}).status_code, 422)
        with patch("app.projects.run_agent.delay", side_effect=RuntimeError("postgres://pipeline:secret-broker-password@db/pipeline")):
            down = self.client.post(url, json={"agent": "analyst"})
        self.assertEqual(down.status_code, 503, down.text)
        self.assertNotIn("secret-broker-password", down.text)
        self.assertEqual(self.client.get(f"/api/projects/{uuid4()}/jobs/job-1").status_code, 404)
        self.assertEqual(self.client.get(url + "/not a job").status_code, 404)
        with patch("app.projects.run_agent.AsyncResult", side_effect=RuntimeError("postgres://pipeline:secret-broker-password@db/pipeline")):
            broken = self.client.get(url + "/job-1")
        self.assertEqual(broken.status_code, 503, broken.text)
        self.assertNotIn("secret-broker-password", broken.text)


if __name__ == "__main__":
    unittest.main()
