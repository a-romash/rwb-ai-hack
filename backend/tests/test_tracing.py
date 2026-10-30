import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from app import tracing

KEYS = {'LANGFUSE_HOST': 'http://langfuse', 'LANGFUSE_PUBLIC_KEY': 'pk', 'LANGFUSE_SECRET_KEY': 'sk'}


def call(**fields):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(**{'id': uuid4(), 'run_id': uuid4(), 'stage_run_id': uuid4(), 'task_id': 'spec.app', 'task_class': 'spec',
                              'model': 'm', 'status': 'schema_error', 'tokens_in': 10, 'tokens_out': 5, 'tokens_reasoning': None,
                              'tokens_cached': None, 'repair_rounds': 1, 'from_cache': False, 'context_profile': 'M',
                              'ts_start': now, 'ts_end': now, **fields})


class TracingTests(unittest.TestCase):
    def test_nothing_is_sent_without_keys(self):
        with patch.dict('os.environ', {**KEYS, 'LANGFUSE_SECRET_KEY': ''}), patch.object(tracing, '_send') as send:
            tracing.generation(call(), {'messages': []})
        send.assert_not_called()

    def test_failed_attempt_is_a_warning_generation_under_its_stage(self):
        row = call()
        with patch.dict('os.environ', KEYS), patch.object(tracing, '_send') as send:
            tracing.generation(row, {'messages': [{'role': 'user', 'content': 'u'}], 'output': '{"x"', 'error': 'bad json'})
        path, body = send.call_args.args
        span = body['resourceSpans'][0]['scopeSpans'][0]['spans'][0]
        attributes = {item['key']: item['value'] for item in span['attributes']}
        self.assertEqual(path, '/api/public/otel/v1/traces')
        self.assertEqual((span['traceId'], span['parentSpanId']), (row.run_id.hex, row.stage_run_id.hex[:16]))
        self.assertEqual(attributes['langfuse.observation.type'], {'stringValue': 'generation'})
        self.assertEqual(attributes['langfuse.observation.level'], {'stringValue': 'WARNING'})
        self.assertEqual(attributes['langfuse.observation.status_message'], {'stringValue': 'bad json'})
        self.assertIn('"content": "u"', attributes['langfuse.observation.input']['stringValue'])

