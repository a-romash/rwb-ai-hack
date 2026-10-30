import json
import tempfile
import unittest
from pathlib import Path
from contracts.stage import StageInput
from harness.fakes import FakeLLM,FakeSandbox
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
            ui={'screens':{'ItemList':{'platform':'web','widgets':[{'kind':'status','field':'Item.status','testid':'item-list.status'}],
                                       'actions':[{'command':'TakeItem','testid':'item-list.take'}]}},
                'walks':{'US-01':{'platform':'web','covers':['AC-01'],'steps':[{'open':'ItemList'},{'tap':'TakeItem'},{'expect':{'status':'taken'}}]}}}
            files=generate(root,ui)
            text=(root/files[0]).read_text()
            self.assertIn('page.goto("/ItemList")',text)
            self.assertIn('getByTestId("item-list.take").click()',text)
            self.assertIn('getByTestId("item-list.status")',text)
            self.assertEqual(generate(root,ui),files)
            ui['walks']['US-01']['steps']=[{'open':'ItemList'},{'scan':'Item.code','value':'x'}]
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

    def test_mutant_killed_by_any_ac_of_the_hook(self):
        from types import SimpleNamespace
        from stages.verify.mutations import run
        from contracts.verification import PlannedTest
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'product').mkdir();(root/'product/hook.cs').write_text('class Rule { public bool Check(int n) { return n>=5 && n<=9 && true; } }')
            class OnlySecondKills:
                filters=[]
                def run(self,kind,target,filter=None):
                    self.filters.append(filter)
                    failure='<failure type="Xunit.Sdk.EqualException" message="Assert.Equal() Failure"/>' if filter=='AC-02' else ''
                    (root/'junit.xml').write_text(f'<testsuite><testcase classname="AC_0x" name="{filter}"><properties><property name="AC" value="{filter}"/></properties>{failure}</testcase></testsuite>')
                    return SimpleNamespace(reports={'junit':'junit.xml'})
            sandbox=OnlySecondKills()
            planned=[PlannedTest(id=ac,ac=ac,file='t.cs',level='unit') for ac in ('AC-01','AC-02')]
            reports=run(root,[{'id':'Rule','file':'hook.cs','refs':['AC-01','AC-02']}],planned,sandbox)
        self.assertTrue(reports and all(r['status']=='killed' for r in reports),reports)
        self.assertEqual(sandbox.filters[:2],['AC-01','AC-02'])

    def test_lint_rejects_only_related_threshold(self):
        from stages.tests import rule_values
        analysis={'rules':[{'id':'BR-1','params':{'MIN':{'value':5}}},{'id':'BR-2','params':{'OTHER':{'value':10}}}]}
        values=rule_values(analysis,{'rules':['BR-1']})
        self.assertIn('TEST_FORBIDDEN',lint('// AC-1\nAssert.Equal(5, value);','AC-1',values))
        self.assertNotIn('TEST_FORBIDDEN',lint('// AC-1\nAssert.Equal(10, value);','AC-1',values))
