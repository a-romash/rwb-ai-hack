import tempfile
import unittest
from pathlib import Path
from pydantic import BaseModel
from contracts.stage import BudgetExceeded, ContractError
from harness.llm import Gateway, TransportError

class Output(BaseModel):
    count: int

class Client:
    def __init__(self, answers): self.answers = iter(answers); self.calls = 0
    def complete(self, messages, **kwargs):
        self.calls += 1
        return {'content': next(self.answers), 'usage': {'prompt_tokens': 2}, 'finish_reason': 'stop'}

class Tests(unittest.TestCase):
    def gateway(self, client, **kw):
        self.records = []
        def start(data): self.records.append(data); return len(self.records)-1
        def finish(i, data): self.records[i].update(data)
        return Gateway(start=start, finish=finish, budget=lambda: (0, 1000, 0, 10), transport=client, **kw)
    def test_repair_and_cache(self):
        client = Client(['bad', '{"count": 3}'])
        with tempfile.TemporaryDirectory() as tmp:
            gateway = self.gateway(client, cache_dir=Path(tmp))
            args = dict(task_class='qa', system='s', user='u', output=Output)
            self.assertEqual(gateway(**args).count, 3)
            self.assertEqual(gateway(**args).count, 3)
            self.assertEqual(client.calls, 2)
            self.assertEqual(len(self.records), 3)
            self.assertTrue(self.records[-1]['from_cache'])
    def test_retry_and_schema_failure(self):
        class RetryClient:
            calls = 0
            def complete(self, messages, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    raise TransportError('HTTP 429', retryable=True)
                return {'content': 'invalid', 'usage': {}, 'finish_reason': 'stop'}
        client = RetryClient()
        gateway = self.gateway(client, sleep=lambda _: None)
        with self.assertRaises(ContractError):
            gateway(task_class='qa', system='s', user='u', output=Output)
        self.assertEqual(client.calls, 4)
        self.assertEqual([r['status'] for r in self.records], ['provider_error', 'schema_error', 'schema_error', 'schema_error'])

    def test_budget_exhausted_does_not_call_transport(self):
        client = Client([])
        gateway = self.gateway(client)
        gateway.budget = lambda: (1000, 1000, 0, 10)
        with self.assertRaises(BudgetExceeded):
            gateway(task_class='qa', system='s', user='u', output=Output)
        self.assertEqual(client.calls, 0)

    def test_retry_stops_when_previous_usage_is_unknown(self):
        client = Client([])
        gateway = self.gateway(client, sleep=lambda _: None)
        class Failure:
            calls = 0
            def complete(self, *args, **kwargs):
                self.calls += 1
                raise TransportError('HTTP 429', retryable=True)
        failure = Failure()
        gateway.transport = failure
        gateway.budget = lambda: (None if self.records else 0, 1000, 0, 10)
        with self.assertRaises(BudgetExceeded):
            gateway(task_class='qa', system='s', user='u', output=Output)
        self.assertEqual(failure.calls, 1)
        self.assertIsNone(self.records[0]['usage'])

    def test_retry_allowed_when_zero_usage_explicit(self):
        gateway = self.gateway(Client([]), sleep=lambda _: None)
        class FailureThenSuccess:
            calls = 0
            def complete(self, *args, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    raise TransportError('HTTP 429', retryable=True, usage={'prompt_tokens': 0, 'completion_tokens': 0})
                return {'content': '{"count":2}', 'usage': {'prompt_tokens': 1, 'completion_tokens': 1}, 'finish_reason': 'stop'}
        transport = FailureThenSuccess()
        gateway.transport = transport
        gateway.budget = lambda: (None if any(x.get('usage') is None for x in self.records) else 0, 1000, 0, 10)
        self.assertEqual(gateway(task_class='qa', system='s', user='u', output=Output).count, 2)
        self.assertEqual(transport.calls, 2)

    def test_unsupported_schema_falls_back(self):
        class Fallback:
            calls = 0
            def complete(self, messages, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    raise TransportError('HTTP 400', unsupported_schema=True)
                assert kwargs['schema'] is None
                return {'content': '{"count": 7}', 'usage': {}, 'finish_reason': 'stop'}
        gateway = self.gateway(Fallback())
        self.assertEqual(gateway(task_class='qa', system='s', user='u', output=Output).count, 7)

    def test_multiple_code_blocks_rejected(self):
        gateway = self.gateway(Client(['<<<CODE\na\nCODE>>>\n<<<CODE\nb\nCODE>>>'] * 3))
        with self.assertRaises(ContractError):
            gateway(task_class='hook_1', system='s', user='u', output='code')

    def test_cache_separates_profile_and_policy(self):
        from harness.llm import TASKS
        client = Client(['plain', 'profile', 'policy'])
        with tempfile.TemporaryDirectory() as tmp:
            gateway = self.gateway(client, cache_dir=Path(tmp))
            args = dict(task_class='writer', system='s', user='u', output='text')
            self.assertEqual(gateway(**args), 'plain')
            gateway.profile = 'L'
            self.assertEqual(gateway(**args), 'profile')
            original = TASKS['writer']
            try:
                TASKS['writer'] = (None, 0, .3, 2000)
                self.assertEqual(gateway(**args), 'policy')
            finally:
                TASKS['writer'] = original

    def test_context_rejected_before_http(self):
        client = Client([])
        gateway = self.gateway(client, tokenizer=lambda _: 20000)
        with self.assertRaises(ContractError): gateway(task_class='qa', system='s', user='u', output=Output)
        self.assertEqual(client.calls, 0)
    def test_code_validation(self):
        gateway = self.gateway(Client(['bad', '<<<CODE\nhello\nCODE>>>']))
        self.assertEqual(gateway(task_class='hook_1', system='s', user='u', output='code'), 'hello')

if __name__ == '__main__': unittest.main()
