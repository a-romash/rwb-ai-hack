import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from contracts.gates import Finding, GateResult
from contracts.stage import ContractError, StageInput, StageOutput
from gates.core import check_gate, run_gate


class GateTests(unittest.TestCase):
    def test_missing_gate_is_explicit_and_strict_by_default(self):
        # All real gates exist now; point G1 at a module that does not.
        with tempfile.TemporaryDirectory() as tmp, patch.dict('gates.core.MODULES', {'G1': 'gates.g_absent'}):
            with self.assertRaises(ContractError):
                check_gate('G1', Path(tmp), {})
            result = check_gate('G1', Path(tmp), {}, allow_missing=True)
            self.assertEqual(result.findings[0].code, 'GATE_MISSING')

    def test_two_repairs_then_pass(self):
        finding = Finding(path='x', code='ERR', severity='error', message='Ошибка')
        results = [GateResult(gate='G1', passed=False, findings=[finding])]*2 + [GateResult(gate='G1', passed=True)]
        module = SimpleNamespace(repair=lambda inp, workspace, llm, findings: StageOutput(artifacts={}, summary='исправлено'))
        inp = StageInput(run_id='1', stage='spec', attempt=1, requirements='r', artifacts={})
        with tempfile.TemporaryDirectory() as tmp, patch('gates.core.check_gate', side_effect=results):
            output, rounds = run_gate('G1', module, inp, Path(tmp), None, StageOutput(artifacts={}, summary='x'))
        self.assertEqual(len(rounds), 3)
        self.assertTrue(rounds[-1].passed)
        self.assertEqual(output.summary, 'исправлено')

    def test_second_repair_receives_previous_repair_result(self):
        finding = Finding(path='x', code='ERR', severity='error', message='Ошибка')
        results = [GateResult(gate='G1', passed=False, findings=[finding])] * 2 + [GateResult(gate='G1', passed=True)]
        seen = []
        def repair(inp, workspace, llm, findings, previous_output=None):
            seen.append(previous_output.summary)
            return StageOutput(artifacts={}, summary=f'попытка {len(seen)}')
        inp = StageInput(run_id='1', stage='spec', attempt=1, requirements='r', artifacts={})
        with tempfile.TemporaryDirectory() as tmp, patch('gates.core.check_gate', side_effect=results):
            run_gate('G1', SimpleNamespace(repair=repair), inp, Path(tmp), None, StageOutput(artifacts={}, summary='исходный'))
        self.assertEqual(seen, ['исходный', 'попытка 1'])

if __name__ == '__main__':
    unittest.main()
