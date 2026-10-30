import io
import json
import multiprocessing
import os
import tempfile
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from unittest.mock import patch

from contracts.stage import ContractError
from harness.llm_throttle import Limiter, open_throttled


def concurrent_reservation(path, barrier, queue):
    limiter = Limiter(path=Path(path), tpm=100, rpm=0, concurrent=0, window=60, safety=0, bytes_per_token=3, max_wait=60)
    barrier.wait()
    try:
        limiter.reserve('shared', 40, 120, sleep=lambda _: (_ for _ in ()).throw(RuntimeError('wait')))
        queue.put('admitted')
    except RuntimeError:
        queue.put('wait')


class ThrottleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'limiter.json'
        self.now = 1000.0

    def tearDown(self):
        self.tmp.cleanup()

    def limiter(self, **settings):
        return Limiter(path=self.path, tpm=100, rpm=settings.get('rpm', 0), concurrent=settings.get('concurrent', 0), window=60,
                       safety=0, bytes_per_token=3, max_wait=60)

    def wait(self, delay):
        self.now += delay

    def test_reservations_replaced_by_actual_usage_and_rpm_remains(self):
        limiter = self.limiter(rpm=2)
        with patch('harness.llm_throttle.time.time', side_effect=lambda: self.now):
            first = limiter.reserve('scope', 60, 120, sleep=self.wait)
            limiter.finish(first, 10)
            limiter.reserve('scope', 60, 120, sleep=self.wait)
            self.assertEqual(self.now, 1000)
            limiter.reserve('scope', 20, 120, sleep=self.wait)
            self.assertEqual(self.now, 1060)

    def test_pending_request_survives_window_and_concurrency_wait_is_bounded(self):
        limiter = self.limiter(concurrent=1)
        with patch('harness.llm_throttle.time.time', side_effect=lambda: self.now):
            limiter.reserve('scope', 20, 120, sleep=self.wait)
            with self.assertRaisesRegex(RuntimeError, 'лимит'):
                limiter.reserve('scope', 20, 120, sleep=self.wait)
            self.assertEqual(self.now, 1060)

    def test_orphan_reservation_keeps_unknown_usage_for_window_after_timeout(self):
        limiter=self.limiter()
        with patch('harness.llm_throttle.time.time',side_effect=lambda:self.now):
            limiter.reserve('scope',60,10,sleep=self.wait)
            self.now=1061
            limiter.reserve('scope',60,120,sleep=self.wait)
        self.assertEqual(self.now,1075)

    def test_oversize_and_corrupt_state_fail_before_network(self):
        limiter = self.limiter()
        with self.assertRaisesRegex(ContractError, 'запрос'):
            limiter.reserve('scope', 101, 120)
        self.path.write_text('{broken')
        with self.assertRaisesRegex(ContractError, 'журнал'):
            limiter.reserve('scope', 10, 120)

    def test_cross_process_reservations_are_atomic(self):
        context = multiprocessing.get_context('fork')
        barrier = context.Barrier(3)
        queue = context.Queue()
        processes = [context.Process(target=concurrent_reservation, args=(str(self.path), barrier, queue)) for _ in range(3)]
        for process in processes: process.start()
        for process in processes:
            process.join(10)
            self.assertEqual(process.exitcode, 0)
        self.assertEqual(sorted(queue.get(timeout=2) for _ in processes), ['admitted', 'admitted', 'wait'])

    def test_network_uses_shared_key_scope_and_state_has_no_prompt_or_key(self):
        environment = {'LLM_TPM_LIMIT': '10000', 'LLM_RPM_LIMIT': '60', 'LLM_RATE_SAFETY_TOKENS': '20',
                       'LLM_RATE_LIMIT_FILE': str(self.path), 'LLM_MAX_PARALLEL': '1'}
        request = urllib.request.Request('http://local/v1/chat/completions',
            data=json.dumps({'model': 'local', 'messages': [{'role': 'user', 'content': 'PRIVATE-PROMPT'}], 'max_tokens': 100}).encode(),
            headers={'Authorization': 'Bearer PRIVATE-KEY'})
        with patch.dict(os.environ, environment):
            response = open_throttled(lambda *a, **k: io.BytesIO(b'{"usage":{"prompt_tokens":4,"completion_tokens":2}}'), request, timeout=120)
            self.assertIn('usage', json.loads(response.read()))
        state = self.path.read_text()
        self.assertNotIn('PRIVATE', state)
        self.assertEqual(json.loads(state)[0]['tokens'], 6)
        self.assertFalse(json.loads(state)[0]['pending'])

    def test_rpm_wait_after_429_never_extends_hard_retry_minute(self):
        from harness.http_retry import RateLimitExceeded, open_with_rate_limit_retry
        request=urllib.request.Request('http://local/v1/chat/completions',data=b'{"messages":[],"max_tokens":10}')
        attempts=[]
        def opener(*args,**kwargs):
            attempts.append(1)
            raise urllib.error.HTTPError('http://local',429,'limit',{'Retry-After':'3'},io.BytesIO(b''))
        initial=self.now
        with patch.dict(os.environ,{'LLM_TPM_LIMIT':'10000','LLM_RPM_LIMIT':'1','LLM_RATE_LIMIT_FILE':str(self.path)}), \
             patch('harness.llm_throttle.time.time',side_effect=lambda:self.now):
            with self.assertRaises(RateLimitExceeded):
                open_with_rate_limit_retry(opener,request,timeout=120,sleep=self.wait,clock=lambda:self.now)
        self.assertEqual(self.now-initial,60)
        self.assertEqual(len(attempts),1)

    def test_default_agent_request_gets_finite_output_cap_when_limits_enabled(self):
        from harness.agent import OpenRouter
        sent=[]
        def opener(request,timeout):
            sent.append(json.loads(request.data))
            return io.BytesIO(b'{"model":"local","choices":[{"message":{"content":"OK"},"finish_reason":"stop"}],"usage":{"prompt_tokens":1,"completion_tokens":1}}')
        with patch.dict(os.environ,{'LLM_TPM_LIMIT':'10000','LLM_RPM_LIMIT':'60','LLM_RATE_LIMIT_FILE':str(self.path),
                                    'LLM_BASE_URL':'http://local/v1','LLM_MODEL':'local','LLM_API_KEY':'test-key'}):
            OpenRouter(opener=opener).complete([],None)
        self.assertEqual(sent[0]['max_tokens'],4096)


if __name__ == '__main__':
    unittest.main()
