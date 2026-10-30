import io
import json
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from pydantic import BaseModel

from harness.http_retry import RateLimitExceeded, open_with_rate_limit_retry


class Clock:
    def __init__(self):
        self.now = 0
        self.waits = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.now += seconds


class Output(BaseModel):
    count: int


class RateLimitTests(unittest.TestCase):
    def error(self, status=429, headers=None):
        return urllib.error.HTTPError('http://local/v1', status, 'provider error', headers or {}, io.BytesIO(b'local-secret'))

    def test_waits_at_most_one_minute_and_bounds_request_timeout(self):
        clock = Clock()
        timeouts = []
        def opener(request, timeout):
            timeouts.append(timeout)
            raise self.error(headers={'Retry-After': '7'})
        with self.assertRaisesRegex(RateLimitExceeded, '429.*60'):
            open_with_rate_limit_retry(opener, object(), timeout=120, sleep=clock.sleep, clock=clock.monotonic)
        self.assertEqual(clock.now, 60)
        self.assertGreater(len(timeouts), 4)
        self.assertLessEqual(timeouts[-1], 4)

    def test_does_not_retry_non_rate_limit_error(self):
        clock = Clock()
        with self.assertRaises(urllib.error.HTTPError):
            open_with_rate_limit_retry(lambda *a, **k: (_ for _ in ()).throw(self.error(400)), object(), timeout=120, sleep=clock.sleep, clock=clock.monotonic)
        self.assertEqual(clock.waits, [])

    def test_all_llm_clients_recover_or_stop_without_extra_retry_windows(self):
        from harness.agent import OpenRouter
        from harness.llm import Gateway, HTTPTransport, LocalLLM
        for client_name in ('agent', 'gateway', 'eval'):
            for exhausted in (False, True):
                with self.subTest(client=client_name, exhausted=exhausted):
                    clock = Clock()
                    requests = []
                    records = []
                    def opener(request, timeout):
                        requests.append(request)
                        if exhausted or len(requests) <= 2:
                            raise self.error()
                        body = {'model': 'local-model', 'choices': [{'message': {'content': '{"count":1}'}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 1, 'completion_tokens': 1}}
                        return io.BytesIO(json.dumps(body).encode())
                    with patch.dict('os.environ', {'LLM_BASE_URL': 'http://local/v1', 'LLM_API_KEY': 'local-secret', 'OPENROUTER_API_KEY': 'other-secret', 'LLM_MODEL': 'local-model'}), \
                         patch('harness.http_retry.time.sleep', side_effect=clock.sleep), \
                         patch('harness.http_retry.time.monotonic', side_effect=clock.monotonic), \
                         patch('urllib.request.urlopen', side_effect=opener):
                        if client_name == 'agent':
                            client = OpenRouter(opener=opener, sleep=clock.sleep, retries=1)
                            invoke = lambda: client.complete([], None)
                        elif client_name == 'gateway':
                            transport = HTTPTransport(opener=opener)
                            client = Gateway(transport=transport, budget=lambda: (0, 100000, 0, 10),
                                             start=lambda fields: records.append(fields) or len(records)-1,
                                             finish=lambda index, fields: records[index].update(fields))
                            invoke = lambda: client(task_class='writer', system='s', user='u', output='text')
                        else:
                            client = LocalLLM(transport=HTTPTransport(opener=opener))
                            invoke = lambda: client(task_class='req_extract', system='s', user='u', output=Output)
                        if exhausted:
                            with self.assertRaisesRegex(RateLimitExceeded, '429.*60') as caught:
                                invoke()
                            self.assertNotIn('local-secret', str(caught.exception))
                            self.assertEqual(clock.now, 60)
                            if records:
                                self.assertEqual(records[-1]['status'], 'provider_error')
                        else:
                            invoke()
                            self.assertEqual(len(requests), 3)
                            self.assertGreater(clock.now, 0)
                    for request in requests:
                        self.assertTrue(request.full_url.startswith('http://local/'))
                        self.assertEqual(request.get_header('Authorization'), 'Bearer local-secret')
