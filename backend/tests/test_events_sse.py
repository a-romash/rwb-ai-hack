import asyncio
import unittest
from types import SimpleNamespace

from app.database import SessionLocal
from app.models import Event, Project, Run
from app.runs import events_stream


class EventStreamTest(unittest.TestCase):
    def test_last_id_and_transactional_notification(self):
        with SessionLocal.begin() as db:
            project = Project(name="SSE", requirements="r")
            db.add(project)
            db.flush()
            run = Run(project_id=project.id, requirements="r", workspace_path="/tmp/test", tokens_limit=100, minutes_limit=1)
            db.add(run)
            db.flush()
            old = Event(run_id=run.id, type="old", payload={})
            db.add(old)
            db.flush()
            run_id, old_id, project_id = run.id, old.id, project.id

        class Request:
            async def is_disconnected(self):
                return False

        async def check():
            with SessionLocal() as db:
                response = await events_stream(run_id, Request(), db, str(old_id))
                stream = response.body_iterator
                next_event = asyncio.create_task(anext(stream))
                await asyncio.sleep(.1)
                with SessionLocal.begin() as writer:
                    writer.add(Event(run_id=run_id, type="new", payload={"value": 42}))
                data = await asyncio.wait_for(next_event, timeout=1.5)
                self.assertIn("event: new", data)
                self.assertNotIn("event: old", data)
                self.assertIn('"value": 42', data)
                await stream.aclose()
        try:
            asyncio.run(check())
        finally:
            with SessionLocal.begin() as db:
                db.delete(db.get(Project, project_id))
