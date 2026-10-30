import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from app.llm_binding import make_llm


class Session:
    calls = []
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def get(self, model, key):
        return SimpleNamespace(config={}, workspace_path='/tmp/project/runs/run', started_at=datetime.now(timezone.utc), created_at=datetime.now(timezone.utc), tokens_limit=1000, minutes_limit=10)
    def scalars(self, query): return SimpleNamespace(all=lambda: self.calls)


class BindingTest(unittest.TestCase):
    def test_budget_unknown_is_never_zero(self):
        run_id, stage_id = uuid4(), uuid4()
        with patch('app.llm_binding.SessionLocal', Session):
            gateway = make_llm(run_id, stage_id, transport=object())
            Session.calls = [SimpleNamespace(id=1, status='started', tokens_in=None, tokens_out=None)]
            self.assertIsNone(gateway.budget()[0])
            Session.calls = [SimpleNamespace(id=1, status='ok', tokens_in=4, tokens_out=5)]
            self.assertEqual(gateway.budget()[0], 9)
            Session.calls = [SimpleNamespace(id=1, status='ok', tokens_in=4, tokens_out=None)]
            self.assertIsNone(gateway.budget()[0])
            self.assertEqual(gateway.budget_excluding([1])[0], 0)
            Session.calls = []
