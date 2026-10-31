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

    def test_g2_feedback_reaches_the_model_with_rejected_cases(self):
        analysis = {'acceptance': [{'id': 'AC-01', 'rules': [], 'gherkin': TABLE}]}
        old = [{'id': 'AC-01-1', 'ac': 'AC-01', 'inputs': {'value': 5}, 'expected': False},
               {'id': 'AC-01-2', 'ac': 'AC-01', 'inputs': {'value': 5}, 'expected': True}]
        (_, why), = hook_cases.contradictions(old)
        new = [{'id': f'AC-01-{n}', 'ac': 'AC-01', 'inputs': {'value': v}, 'expected': v >= 5} for n, v in ((1, 4), (2, 5), (3, 6))]
        llm = FakeLLM({('qa', 'Allowed'): [{'cases': new}]})
        cases, source = hook_cases.build(self.hook, {}, analysis, llm, {'AC-01': [why]}, old)
        # Gherkin rows alone would skip the model; the finding sends the criterion back to it.
        self.assertEqual((len(cases), source), (3, 'model'))
        packet = json.loads(llm.calls[0]['user'])['previous_cases_rejected']
        self.assertEqual((packet['why'], packet['cases']), ([why], old))
        self.assertEqual(hook_cases.contradictions(new), [])

    def test_hook_without_inputs_is_accepted(self):
        from stages.tests import _hooks
        with tempfile.TemporaryDirectory() as folder:
            hooks = [{'id': 'PaymentUrl', 'method': 'Allow', 'parameters': []}]
            (Path(folder) / 'hooks.json').write_text(json.dumps(hooks), encoding='utf-8')
            self.assertEqual(_hooks(Path(folder), {'hooks': 'hooks.json'}), hooks)
            (Path(folder) / 'hooks.json').write_text(json.dumps([{'id': 'Old', 'method': 'Allow'}]), encoding='utf-8')
            with self.assertRaises(ContractError):
                _hooks(Path(folder), {'hooks': 'hooks.json'})


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
                                   ('test', 'backend'): [ok(reports={'junit': 'product/reports/junit/backend/run.xml'})] * 4})
            result = execute(StageInput(run_id='r', stage='tests', attempt=1, requirements='r', artifacts=artifacts), root, llm, sandbox)
            manifest = json.loads((root / result.artifacts['tests']).read_text(encoding='utf-8'))
            # AC-03 has hook cases; AC-01, AC-02, AC-08 get API scenarios from app.json (neutral for red-proof).
            self.assertEqual([t['ac'] for t in manifest['tests']], ['AC-01', 'AC-02', 'AC-03', 'AC-08'])
            by_ac = {t['ac']: t for t in manifest['tests']}
            self.assertTrue(by_ac['AC-03']['red_proof'])
            self.assertEqual(by_ac['AC-03']['failure_kind'], 'assertion')
            self.assertEqual((by_ac['AC-02']['level'], by_ac['AC-02']['neutral']), ('api', True))
            self.assertIn('product/backend/tests/App.Acceptance.Tests/cases/scenarios/AC-02.json', manifest['hashes'])
            case_file = 'product/backend/tests/App.Acceptance.Tests/cases/hooks/ResolutionRequired.json'
            self.assertIn(case_file, manifest['hashes'])
            self.assertEqual(len(json.loads((root / case_file).read_text(encoding='utf-8'))['cases']), 3)
            source = (root / 'product/backend/tests/App.Acceptance.Tests/Generated/AC_03.cs').read_text(encoding='utf-8')
            self.assertIn('Trait("AC", "AC-03")', source)
            sources = json.loads((root / 'reports/test-cases.json').read_text(encoding='utf-8'))['sources']
            self.assertEqual(sources['ResolutionRequired'], 'model')
            self.assertEqual(sources['SlaDeadline'], 'budget')
            self.assertTrue(any(path.startswith('product/admin-web/e2e/') for path in json.loads((root / 'reports/test-cases.json').read_text())['e2e']))


class E2ETest(unittest.TestCase):
    def test_rows_and_nav_follow_what_the_screen_shows(self):
        from stages.tests import e2e
        app = json.loads((FIXTURES / 'app.json').read_text(encoding='utf-8'))
        ui = json.loads((FIXTURES / 'ui.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as tmp:
            e2e.generate(Path(tmp), ui, app)
            spec = (Path(tmp) / 'product/admin-web/e2e/US-03.spec.ts').read_text(encoding='utf-8')
        # Ticket[1] is not the second row of MyTickets: rows are found by the seed record's text.
        self.assertIn('getByTestId("my-tickets.row").filter({hasText: "Сломался стул"}).first().click()', spec)
        self.assertIn('getByTestId("ticket-detail.nav-ResolveTicketForm").click()', spec)
        self.assertNotIn('nth(', spec)

    def test_status_of_a_plain_enum_field(self):
        from stages.tests import e2e
        app = {'entities': {'Zone': {'fields': {'name': {'type': 'string'}, 'state': {'type': 'enum'}}}}}
        widgets = [{'kind': 'field', 'testid': 'zones.name', 'field': 'Zone.name'},
                   {'kind': 'field', 'testid': 'zones.state', 'field': 'Zone.state'}]
        ui = {'screens': {'Zones': {'widgets': widgets}},
              'walks': {'US-01': {'steps': [{'open': 'Zones'}, {'expect': {'status': 'active'}}]}}}
        with tempfile.TemporaryDirectory() as tmp:
            e2e.generate(Path(tmp), ui, app)
            spec = (Path(tmp) / 'product/admin-web/e2e/US-01.spec.ts').read_text(encoding='utf-8')
        self.assertIn("""getByTestId("zones.state").first()).toContainText(new RegExp("active", 'i'))""", spec)

    def test_broken_walk_is_skipped_not_fatal(self):
        from stages.tests import e2e
        ui = {'screens': {'Zones': {'widgets': []}},
              'walks': {'US-01': {'steps': [{'open': 'Zones'}]}, 'US-02': {'steps': [{'open': 'Zones'}, {'fill': 'Zone.nope', 'value': 1}]}}}
        with tempfile.TemporaryDirectory() as tmp:
            files, skipped = e2e.generate(Path(tmp), ui, {})
        self.assertEqual(files, ['product/admin-web/e2e/US-01.spec.ts'])
        self.assertEqual(list(skipped), ['US-02'])

    def test_detail_opens_from_a_list_row_and_seed_fields_keep_their_case(self):
        from stages.tests import e2e
        app = {'seed': {'Vehicle': [{'id': 'v1', 'licensePlate': 'А001АА'}]}}
        screens = {'Vehicles': {'pattern': 'list', 'nav': ['Vehicle'], 'widgets': []},
                   'Vehicle': {'pattern': 'detail', 'widgets': [{'kind': 'field', 'testid': 'vehicle.plate', 'field': 'Report.plate'}]}}
        steps = [{'open': 'Vehicles'}, {'tap': 'Vehicle'}, {'fill': 'Report.plate', 'value': {'seed': 'Vehicle[0].licensePlate'}}]
        ui = {'screens': screens, 'walks': {'US-01': {'steps': steps},
                                            'US-02': {'steps': steps[:2] + [{'fill': 'Report.plate', 'value': {'seed': 'Vehicle[0].licenseplate'}}]}}}
        with tempfile.TemporaryDirectory() as tmp:
            _, skipped = e2e.generate(Path(tmp), ui, app)
            spec = (Path(tmp) / 'product/admin-web/e2e/US-01.spec.ts').read_text(encoding='utf-8')
        self.assertIn('getByTestId("vehicles.row").first().click()', spec)
        self.assertIn('.fill("А001АА")', spec)
        app['commands'] = {'Report': {'input': {'at': {'type': 'datetime'}}}}
        screens['Vehicle']['widgets'].append({'kind': 'field', 'testid': 'vehicle.at', 'field': 'Report.at'})
        ui['walks'] = {'US-03': {'steps': steps[:2] + [{'fill': 'Report.at', 'value': {'gen': 'any'}}]}}
        with tempfile.TemporaryDirectory() as tmp:
            e2e.generate(Path(tmp), ui, app)
            spec = (Path(tmp) / 'product/admin-web/e2e/US-03.spec.ts').read_text(encoding='utf-8')
        self.assertIn('.fill("2030-01-01T10:00")', spec)
        # A seed field that does not exist skips the walk instead of typing "None".
        self.assertEqual(list(skipped), ['US-02'])


class ScenariosTest(unittest.TestCase):
    def test_command_scenario_walks_the_state_machine(self):
        from stages.tests.scenarios import build
        app = json.loads((FIXTURES / 'app.json').read_text(encoding='utf-8'))
        analysis = json.loads((FIXTURES / 'analysis.json').read_text(encoding='utf-8'))
        flows = build(app, analysis)
        self.assertEqual(sorted(flows), ['AC-01', 'AC-02', 'AC-03', 'AC-08'])
        steps = flows['AC-03'][0]['steps']
        # Create as the role allowed to create, take it to in_progress, then resolve and read back.
        self.assertEqual([(s['as'], s['path'].rsplit('/', 1)[-1]) for s in steps],
                         [('employee', 'Ticket'), ('engineer', 'TakeTicket'), ('engineer', 'ResolveTicket'), ('engineer', '{id}'),
                          ('engineer', 'events')])
        # The transition reaches the outbox under the event name the ui stage derives.
        self.assertEqual(steps[-1]['expect']['contains'], {'type': 'TicketResolved', 'entity_id': '{id}'})
        self.assertEqual(steps[2]['expect'], {'status': 200, 'json': {'status': 'resolved'}})
        self.assertEqual(steps[2]['body']['id'], '{id}')
        self.assertEqual(flows['AC-01'][0]['source'], 'create')

    def test_timer_only_transition_gets_no_scenario(self):
        from stages.tests.scenarios import build
        app = json.loads((FIXTURES / 'app.json').read_text(encoding='utf-8'))
        analysis = json.loads((FIXTURES / 'analysis.json').read_text(encoding='utf-8'))
        # AC-07 needs the overdue state, reachable only by the timer: no HTTP scenario is invented.
        self.assertNotIn('AC-07', build(app, analysis))

