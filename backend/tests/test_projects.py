import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import engine, get_session
from app.main import app


class ProjectsTest(unittest.TestCase):
    def setUp(self):
        self.connection = engine.connect()
        self.transaction = self.connection.begin()
        self.session = Session(bind=self.connection, join_transaction_mode="create_savepoint")
        app.dependency_overrides[get_session] = lambda: self.session
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.session.close()
        self.transaction.rollback()
        self.connection.close()

    def create_project(self, name="Помощник водителя"):
        response = self.client.post("/api/projects", json={
            "name": name, "requirements": "Предупреждать об окончании парковки",
        })
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_create_read_edit_preserves_pipeline(self):
        project = self.create_project()
        self.assertEqual(len(project["stages"]), 10)
        self.assertEqual([s["position"] for s in project["stages"]], list(range(1, 11)))
        self.assertEqual(project["stages"][0]["key"], "business_analysis")
        self.assertEqual(project["stages"][-1]["key"], "documentation")
        self.assertEqual({s["status"] for s in project["stages"]}, {"not_started"})
        project_id = project["id"]
        self.assertEqual(self.client.get(f"/api/projects/{project_id}").json(), project)
        response = self.client.patch(f"/api/projects/{project_id}", json={"requirements": "Новые требования"})
        self.assertEqual(response.status_code, 200, response.text)
        updated = response.json()
        self.assertEqual(updated["requirements"], "Новые требования")
        self.assertEqual(updated["name"], project["name"])
        self.assertEqual(updated["stages"], project["stages"])
        self.assertGreaterEqual(updated["updated_at"], project["updated_at"])
        self.assertEqual(self.client.get(f"/api/projects/{project_id}").json(), updated)

    def test_list_newest_first(self):
        first = self.create_project("Первый")
        second = self.create_project("Второй")
        ids = [p["id"] for p in self.client.get("/api/projects").json()]
        self.assertLess(ids.index(second["id"]), ids.index(first["id"]))

    def test_missing_project(self):
        url = f"/api/projects/{uuid4()}"
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.patch(url, json={"name": "Другой"}).status_code, 404)

    def test_validation_on_create_and_patch(self):
        project = self.create_project()
        for field, values in {
            "name": ["", "  ", "x" * 201, None],
            "requirements": ["", "\n ", "x" * 50001, None],
        }.items():
            for value in values:
                with self.subTest(field=field, value=str(value)[:20]):
                    data = {"name": "Проект", "requirements": "Требования", field: value}
                    self.assertEqual(self.client.post("/api/projects", json=data).status_code, 422)
                    self.assertEqual(self.client.patch(f"/api/projects/{project['id']}", json={field: value}).status_code, 422)
        valid = self.client.post("/api/projects", json={"name": "x" * 200, "requirements": "x" * 50000})
        self.assertEqual(valid.status_code, 201)
        self.assertEqual(self.client.post("/api/projects", json={"name": "x", "requirements": "x", "stages": []}).status_code, 422)

    def test_health(self):
        self.assertEqual(self.client.get("/api/health").json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
