import json
import tempfile
import unittest
from pathlib import Path
from contracts.stage import StageInput
from harness.fakes import FakeLLM,FakeSandbox
from stages.quality import write
from stages.tests.lint import lint
from stages.verify.mutations import candidates
from stages.report import execute
from gates.g5_docs import check

class QualityTests(unittest.TestCase):
    def test_lint_and_mutations(self):
        self.assertIn('TEST_NO_AC',lint('Assert.True(true);','AC-1'))
        self.assertIn('TEST_FORBIDDEN',lint('AC-1 DateTime.Now','AC-1'))
        self.assertGreaterEqual(len(candidates('class A { bool F(int n) {return n>=2 && n<=4;} }')),3)

    def test_report_after_early_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            inp=StageInput(run_id='r',stage='report',attempt=1,requirements='r',artifacts={},snapshot={'status':'failed','metrics':{'totals':{'tokens_in':None}}})
            result=execute(inp,root,FakeLLM({'writer':['Проверки не завершены.']}),FakeSandbox({}))
            report=json.loads((root/result.artifacts['report']).read_text())
            self.assertEqual(report['run']['status'],'failed')
            self.assertEqual(len(report['not_done']),3)
            self.assertTrue(check(root,result.artifacts).passed)

    def test_e2e_deterministic_and_unknown_step_rejected(self):
        from stages.tests.e2e import generate
        from contracts.stage import ContractError
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            ui={'screens':{'List':{'route':'/items'}},'walks':{'US-1':{'platform':'web','covers':['AC-1'],'steps':[{'open':'List'},{'expect':{'testid':'items'}}]}}}
            files=generate(root,ui)
            self.assertIn('page.goto("/items")',(root/files[0]).read_text())
            ui['walks']['US-1']['steps']=[{'scan':'unknown'}]
            with self.assertRaises(ContractError):generate(root,ui)

    def test_mutation_restores_hook_on_sandbox_exception(self):
        from stages.verify.mutations import run
        from contracts.verification import PlannedTest
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'product/hook.cs';path.parent.mkdir()
            source=b'class Rule { public bool Check(int n) { return n>=5; } }'
            path.write_bytes(source)
            class Broken:
                def run(self,*args,**kwargs):raise RuntimeError('tool failed')
            with self.assertRaises(RuntimeError):
                run(root,[{'id':'Rule','file':'hook.cs','refs':['AC-01']}],[PlannedTest(id='AC-01',ac='AC-01',file='test.cs',level='unit')],Broken())
            self.assertEqual(path.read_bytes(),source)

    def test_lint_rejects_only_related_threshold(self):
        from stages.tests import rule_values
        analysis={'rules':[{'id':'BR-1','params':{'MIN':{'value':5}}},{'id':'BR-2','params':{'OTHER':{'value':10}}}]}
        values=rule_values(analysis,{'rules':['BR-1']})
        self.assertIn('TEST_FORBIDDEN',lint('// AC-1\nAssert.Equal(5, value);','AC-1',values))
        self.assertNotIn('TEST_FORBIDDEN',lint('// AC-1\nAssert.Equal(10, value);','AC-1',values))
