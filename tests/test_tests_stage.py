import json
import tempfile
import unittest
from pathlib import Path

from contracts.stage import BudgetExceeded, ContractError, SandboxResult, StageInput
from harness.fakes import FakeLLM, FakeSandbox
from stages.tests import cases as hook_cases

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'contracts/fixtures/tickets'

TABLE = """# language: ru
Функция: Порог
  Структура сценария: Проверка порога
    Когда проверяют значение <value>
    Тогда результат равен <expected>
    Примеры:
      | value | expected |
      | 4 | нет |
      | 5 | да |
      | 6 | да |
"""


def ok(**kwargs):
    return SandboxResult(ok=True, exit_code=0, duration_ms=1, failed=[], output_tail='', **kwargs)


class HookCasesTest(unittest.TestCase):
    hook = {'id': 'Allowed', 'kind': 'validator', 'method': 'Validate', 'returns': 'bool', 'refs': ['AC-01'],
            'parameters': [{'name': 'value', 'type': 'int', 'source': 'input'},
                           {'name': 'MIN', 'type': 'int', 'source': 'param'}]}

    def test_matching_columns_need_no_model(self):
        analysis = {'acceptance': [{'id': 'AC-01', 'rules': [], 'gherkin': TABLE}]}

        def no_model(**kwargs):
            raise AssertionError('модель не нужна')
        cases, source = hook_cases.build(self.hook, {}, analysis, no_model)
        self.assertEqual(source, 'gherkin')
        self.assertEqual([(c.inputs, c.expected) for c in cases], [({'value': 4}, False), ({'value': 5}, True), ({'value': 6}, True)])

    def test_model_must_return_every_row(self):
        analysis = {'acceptance': [{'id': 'AC-01', 'rules': [], 'gherkin': TABLE.replace('| value |', '| число |')}]}
        rows = [{'id': f'AC-01-{n}', 'ac': 'AC-01', 'inputs': {'value': v}, 'expected': e} for n, v, e in ((1, 4, False), (2, 5, True))]
        llm = FakeLLM({('qa', 'Allowed'): [{'cases': rows}]})
        with self.assertRaises(ContractError):
            hook_cases.build(self.hook, {}, analysis, llm)
        llm = FakeLLM({('qa', 'Allowed'): [{'cases': rows + [{'id': 'AC-01-3', 'ac': 'AC-01', 'inputs': {'value': 6}, 'expected': True}]}]})
        cases, source = hook_cases.build(self.hook, {}, analysis, llm)
        self.assertEqual((len(cases), source), (3, 'model'))
        self.assertIn('AC-01-1', llm.calls[0]['user'])

    def test_budget_keeps_what_code_found(self):
        analysis = {'acceptance': [{'id': 'AC-01', 'rules': [], 'gherkin': TABLE.replace('| value |', '| число |')}]}
        llm = FakeLLM({('qa', 'Allowed'): [BudgetExceeded('нет бюджета')]})
        self.assertEqual(hook_cases.build(self.hook, {}, analysis, llm), ([], 'budget'))


class TestsStageTest(unittest.TestCase):
    def test_cases_classes_and_red_proof_on_canonical_fixture(self):
        from stages.scaffold import execute as scaffold
        from stages.tests import execute
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / 'spec').mkdir()
            for name in ('analysis', 'app', 'ui'):
                (root / f'spec/{name}.json').write_text((FIXTURES / f'{name}.json').read_text(encoding='utf-8'), encoding='utf-8')
            artifacts = {'analysis': 'spec/analysis.json', 'app': 'spec/app.json', 'ui': 'spec/ui.json'}
            out = scaffold(StageInput(run_id='r', stage='scaffold', attempt=1, requirements='r', artifacts=artifacts), root, None, None)
            artifacts.update(out.artifacts)
            ticket = {'title': 't', 'description': 'd', 'priority': 'high', 'author': '00000000-0000-0000-0000-000000000002',
                      'created_at': '2026-11-06T17:00:00+03:00', 'status': 'in_progress'}
            rows = [{'id': f'AC-03-{n}', 'ac': 'AC-03', 'expected': expected,
                     'inputs': {'resolveTicket': {'id': '00000000-0000-0000-0000-000000000001', 'resolution': text}, 'ticket': ticket}}
                    for n, text, expected in ((1, '', False), (2, '   ', False), (3, 'Заменён блок питания', True))]
            budget = BudgetExceeded('нет бюджета')
            llm = FakeLLM({('qa', 'ResolutionRequired'): [{'cases': rows}], ('qa', 'SlaDeadline'): [budget],
                           ('qa', 'SlaExpired'): [budget], ('qa', 'WorkCalendar'): [budget]})
            report = root / 'product/reports/junit/backend/run.xml'
            report.parent.mkdir(parents=True)
            report.write_text('<testsuite><testcase classname="App.Acceptance.Tests.Generated.AC_03_Tests" name="AC_03">'
                              '<failure message="Assert.Equal() Failure: Values differ"/></testcase></testsuite>')
            sandbox = FakeSandbox({('build', 'backend'): [ok()],
                                   ('test', 'backend'): [ok(reports={'junit': 'product/reports/junit/backend/run.xml'})]})
            result = execute(StageInput(run_id='r', stage='tests', attempt=1, requirements='r', artifacts=artifacts), root, llm, sandbox)
            manifest = json.loads((root / result.artifacts['tests']).read_text(encoding='utf-8'))
            self.assertEqual([t['ac'] for t in manifest['tests']], ['AC-03'])
            self.assertTrue(manifest['tests'][0]['red_proof'])
            self.assertEqual(manifest['tests'][0]['failure_kind'], 'assertion')
            case_file = 'product/backend/tests/App.Acceptance.Tests/cases/hooks/ResolutionRequired.json'
            self.assertIn(case_file, manifest['hashes'])
            self.assertEqual(len(json.loads((root / case_file).read_text(encoding='utf-8'))['cases']), 3)
            source = (root / 'product/backend/tests/App.Acceptance.Tests/Generated/AC_03.cs').read_text(encoding='utf-8')
            self.assertIn('Trait("AC", "AC-03")', source)
            sources = json.loads((root / 'reports/test-cases.json').read_text(encoding='utf-8'))['sources']
            self.assertEqual(sources['ResolutionRequired'], 'model')
            self.assertEqual(sources['SlaDeadline'], 'budget')
            self.assertTrue(any(path.startswith('product/admin-web/e2e/') for path in json.loads((root / 'reports/test-cases.json').read_text())['e2e']))
