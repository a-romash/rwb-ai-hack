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
    def test_reasoning_payload_has_one_budget(self):
        import io, json
        from harness.llm import HTTPTransport
        sent = []
        def opener(request, timeout):
            sent.append(json.loads(request.data))
            return io.BytesIO(json.dumps({'choices': [{'message': {'content': '{}'}, 'finish_reason': 'stop'}]}).encode())
        transport = HTTPTransport(api_key='k', opener=opener)
        transport.complete([], schema=None, effort='low', reasoning_tokens=1500, temperature=1.0, max_tokens=10)
        # OpenRouter answers 400 when both reasoning.effort and reasoning.max_tokens are present.
        self.assertEqual(sent[0]['reasoning'], {'enabled': True, 'max_tokens': 1500})
    def test_dropped_connection_is_a_retryable_transport_error(self):
        import http.client
        from harness.llm import HTTPTransport
        def opener(request, timeout):
            raise http.client.RemoteDisconnected('Remote end closed connection without response')
        with self.assertRaises(TransportError) as caught:
            HTTPTransport(api_key='k', opener=opener).complete([], schema=None, effort=None, reasoning_tokens=0, temperature=0, max_tokens=10)
        self.assertTrue(caught.exception.retryable)
    def test_truncated_json_is_asked_again_with_larger_budget(self):
        class Truncating:
            budgets = []
            def complete(self, messages, *, max_tokens, **kwargs):
                self.budgets.append(max_tokens)
                if len(self.budgets) < 3:
                    return {'content': '{"cou', 'usage': {}, 'finish_reason': 'length'}
                return {'content': '{"count": 5}', 'usage': {}, 'finish_reason': 'stop'}
        client = Truncating()
        self.assertEqual(self.gateway(client)(task_class='qa', system='s', user='u', output=Output).count, 5)
        self.assertEqual(client.budgets, [2500, 5000, 10000])
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
    def test_each_attempt_reports_the_messages_it_sent(self):
        gateway = self.gateway(Client(['bad', '{"count": 3}']))
        gateway(task_class='qa', system='s', user='u', output=Output)
        self.assertEqual([len(r['messages']) for r in self.records], [2, 4])
        self.assertEqual((self.records[0]['output'], self.records[0]['status']), ('bad', 'schema_error'))
        self.assertIn('Исправь формат ответа', self.records[1]['messages'][-1]['content'])
    def test_empty_extraction_is_asked_again_and_never_cached(self):
        from stages.analysis.models import Extraction
        client = Client(['{"requirements": [], "noise": []}', '{"requirements": [], "noise": ["S-001"]}'])
        with tempfile.TemporaryDirectory() as tmp:
            gateway = self.gateway(client, cache_dir=Path(tmp))
            self.assertEqual(gateway(task_class='req_extract', system='s', user='u', output=Extraction).noise, ['S-001'])
            self.assertEqual([r['status'] for r in self.records], ['schema_error', 'repaired'])
            self.assertEqual(len(list(Path(tmp).rglob('*.json'))), 1)

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



    def test_unknown_usage_allows_only_bounded_retry_inside_same_call(self):
        class Retry:
            calls=0
            def complete(self,*args,**kwargs):
                self.calls+=1
                if self.calls==1:
                    raise TransportError('HTTP 429',retryable=True)
                return {'content':'{"count":7}','usage':{'prompt_tokens':2,'completion_tokens':3},'finish_reason':'stop'}
        client=Retry()
        gateway=self.gateway(client,sleep=lambda _:None)
        def budget(excluded=()):
            unknown=[i for i,r in enumerate(self.records) if r.get('status')=='provider_error']
            return (None if any(i not in excluded for i in unknown) else 0,1000,0,10)
        gateway.budget=budget
        gateway.budget_excluding=budget
        self.assertEqual(gateway(task_class='qa',system='s',user='u',output=Output).count,7)
        self.assertIsNone(self.records[0]['usage'])
        with self.assertRaises(BudgetExceeded):
            gateway(task_class='qa',system='s',user='different',output=Output)
        self.assertEqual(client.calls,2)

class LocalEndpointConfigurationTests(unittest.TestCase):
    def test_agent_and_transport_use_local_credentials_without_openrouter_fields(self):
        import json
        from unittest.mock import patch
        from harness.agent import OpenRouter
        from harness.llm import HTTPTransport
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return json.dumps({'model': 'local-model', 'choices': [{'message': {'content': '{}'}, 'finish_reason': 'stop'}]}).encode()
        requests = []
        def opener(request, timeout):
            requests.append(request)
            return Response()
        with patch.dict('os.environ', {'LLM_BASE_URL': 'http://10.10.10.10:4000/v1', 'LLM_API_KEY': 'local-secret', 'LLM_MODEL': 'local-model', 'OPENROUTER_API_KEY': 'other-secret'}):
            OpenRouter(opener=opener).complete([], None)
            HTTPTransport(opener=opener).complete([], schema=None, effort='high', reasoning_tokens=100, temperature=.2, max_tokens=20)
        for req in requests:
            self.assertEqual(req.get_header('Authorization'), 'Bearer local-secret')
            self.assertEqual(json.loads(req.data)['model'], 'local-model')
            self.assertNotIn('provider', json.loads(req.data))
            self.assertNotIn('reasoning', json.loads(req.data))
