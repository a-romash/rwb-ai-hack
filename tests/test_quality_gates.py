import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from stages.quality import write,junit
from contracts.stage import SandboxResult,StageInput
from contracts.verification import PlannedTest
from harness.fakes import FakeLLM,FakeSandbox
from stages.report import execute
from gates.g2_redproof import check as g2
from gates.g3_checks import check as g3
from gates.g4_stand import check as g4
from gates.g5_docs import check as g5

class GateCoverage(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def test_g2_all_codes(self):
        data={'schema_version':1,'tests':[{'id':'AC-01','ac':'AC-01','file':'product/test.cs','level':'unit','failure_kind':'none','red_proof':False,'lint':['TEST_NO_AC','TEST_FORBIDDEN']},{'id':'AC-02','ac':'AC-02','file':'product/test2.cs','level':'unit','failure_kind':'setup'}],'hashes':{},'acceptance':['AC-01','AC-02','AC-03'],'build_ok':True}
        write(self.root,'reports/tests.json',data)
        codes={f.code for f in g2(self.root,{'tests':'reports/tests.json'}).findings}
        self.assertEqual(codes,{'TEST_GREEN_ON_STUB','TEST_FAILS_WRONG','TEST_NO_AC','TEST_FORBIDDEN','AC_NO_TEST'})
        cases=[{'id':'AC-02-1','ac':'AC-02','inputs':{'x':1},'expected':True},{'id':'AC-02-2','ac':'AC-02','inputs':{'x':1},'expected':False}]
        write(self.root,'product/backend/tests/App.Acceptance.Tests/cases/hooks/Gate.json',{'cases':cases})
        found=[f for f in g2(self.root,{'tests':'reports/tests.json'}).findings if f.code=='CASES_CONTRADICT']
        self.assertEqual([f.path for f in found],['tests/AC-02'])
        self.assertIn('AC-02-1',found[0].message)
    def test_g3_g4_codes(self):
        data={'schema_version':1,'build':{'backend':False},'tests':[{'id':'x','ac':'AC-01','level':'unit','file':'x','status':'skipped'}],'mutations':[{'hook':'X','status':'survived'}],'scans':[{'severity':'critical'}],'stand':{'up':False,'smoke':False,'e2e':{},'hash_mismatches':['x']},'ac_status':{'AC-01':{'specified':True,'tested':True,'red_proof':True,'implemented':True,'passes':False,'e2e':None,'reason':'red'}}}
        write(self.root,'verification.json',data)
        artifacts={'verification':'verification.json'}
        self.assertTrue({'BUILD_FAILED','TEST_HASH_MISMATCH','AC_RED','MUTANT_SURVIVED','SCAN_HIGH','SKIPPED_AS_PASS'} <= {f.code for f in g3(self.root,artifacts).findings})
        self.assertEqual({'STAND_DOWN','E2E_FAILED'},{f.code for f in g4(self.root,artifacts).findings})
    def test_junit_trait_mapping_and_missing_report(self):
        planned=[PlannedTest(id='AC-01',ac='AC-01',file='test.cs',level='unit')]
        result=SandboxResult(ok=False,exit_code=1,duration_ms=1,failed=[],output_tail='',reports={'junit':'junit.xml'})
        (self.root/'junit.xml').write_text('<testsuite><testcase classname="RuleTests" name="Boundary"><properties><property name="AC" value="AC-01"/></properties><failure type="Xunit.Sdk.EqualException" message="Assert.Equal"/></testcase></testsuite>')
        cases=junit(self.root,result,planned)
        self.assertEqual(len(cases),1);self.assertEqual(cases[0].ac,'AC-01');self.assertEqual(cases[0].status,'failed')
        result.reports={};self.assertEqual(junit(self.root,result,planned)[0].status,'not_run')
    def test_two_domain_reports_and_doc_gates(self):
        for domain in ('tickets','equipment'):
            artifacts={}
            source=Path('contracts/fixtures')/domain
            for key in ('analysis','app','ui','develop'):
                write(self.root,key+'.json',json.loads((source/(key+'.json')).read_text()));artifacts[key]=key+'.json'
            inp=StageInput(run_id=domain,stage='report',attempt=1,requirements='r',artifacts=artifacts,snapshot=json.loads((source/'snapshot-failed.json').read_text()))
            out=execute(inp,self.root,FakeLLM({'writer':['Проверки не завершены.']}),FakeSandbox({}))
            self.assertTrue(g5(self.root,{**artifacts,**out.artifacts}).passed)
            report=json.loads((self.root/'reports/report.json').read_text());self.assertEqual(report['run']['status'],'failed')
            docs=self.root/'product/docs'
            for path in docs.glob('role-*.md'):path.unlink()
            (docs/'trace.md').write_text('{{unknown}}\n[bad](missing.md)')
            (docs/'index.md').write_text('empty')
            findings={f.code for f in g5(self.root,{**artifacts,**out.artifacts}).findings}
            self.assertTrue({'DOC_AC_MISSING','DOC_ROLE_MISSING','DOC_PLACEHOLDER','DOC_BROKEN_LINK'}<=findings)
    def test_verify_keeps_failed_and_skipped_checks_partial(self):
        from stages.verify import execute as verify
        from harness.workspace import describe
        fixtures=Path('contracts/fixtures/tickets');artifacts={}
        for name in ('analysis','app','hooks','develop'):
            write(self.root,name+'.json',json.loads((fixtures/(name+'.json')).read_text()));artifacts[name]=name+'.json'
        (self.root/'product').mkdir();(self.root/'product/test.cs').write_text('protected')
        manifest={'schema_version':1,'tests':[{'id':'AC-01','ac':'AC-01','file':'product/test.cs','level':'unit','red_proof':True,'failure_kind':'assertion'}],'hashes':{'product/test.cs':describe(self.root,'product/test.cs')[0]},'acceptance':['AC-01'],'build_ok':True}
        write(self.root,'reports/tests.json',manifest);artifacts['tests']='reports/tests.json'
        ok=SandboxResult(ok=True,exit_code=0,duration_ms=1,failed=[],output_tail='')
        bad=SandboxResult(ok=False,exit_code=1,duration_ms=1,failed=['failed'],output_tail='failed')
        sandbox=FakeSandbox({('build','backend'):[ok],('build','admin'):[bad],('build','pwa'):[bad],('test','backend'):[ok],('scan','stack'):[ok],('up','stack'):[bad],('down','stack'):[ok]})
        out=verify(StageInput(run_id='r',stage='verify',attempt=1,requirements='r',artifacts=artifacts),self.root,FakeLLM({}),sandbox)
        data=json.loads((self.root/out.artifacts['verification']).read_text())
        self.assertFalse(data['ac_status']['AC-01']['passes'])
        self.assertEqual(data['tests'][0]['status'],'not_run')
        self.assertFalse(g3(self.root,out.artifacts).passed)
        self.assertFalse(g4(self.root,out.artifacts).passed)
        self.assertEqual(sandbox.calls[-1]['kind'],'down')

    def test_healthy_prototype_is_published_without_smoke(self):
        from stages.verify import execute as verify
        write(self.root,'analysis.json',{'roles':[],'acceptance':[]})
        write(self.root,'tests.json',{'tests':[],'hashes':{},'acceptance':[],'build_ok':True})
        ok=SandboxResult(ok=True,exit_code=0,duration_ms=1,failed=[],output_tail='')
        sandbox=FakeSandbox({('build','backend'):[ok],('test','backend'):[ok],('scan','stack'):[ok],('up','stack'):[ok]})
        sandbox.keep_stand=True
        inp=StageInput(run_id='r',stage='verify',attempt=1,requirements='r',artifacts={'analysis':'analysis.json','tests':'tests.json'})
        with patch('harness.prototype.reset_data') as reset, patch('harness.prototype.mark_ready') as ready, patch('harness.prototype.url',return_value='/agent-prototype/'):
            output=verify(inp,self.root,FakeLLM({}),sandbox)
        stand=json.loads((self.root/output.artifacts['verification']).read_text())['stand']
        self.assertEqual(stand['url'],'/agent-prototype/')
        self.assertNotIn('smoke',[call['kind'] for call in sandbox.calls])
        reset.assert_called_once_with('r');ready.assert_called_once_with('r')
        self.assertTrue(g4(self.root,output.artifacts).passed)

    def test_warm_runtime_never_publishes_stale_output_after_failed_build(self):
        from stages.verify import execute as verify
        write(self.root,'analysis.json',{'roles':[],'acceptance':[]})
        write(self.root,'tests.json',{'tests':[],'hashes':{},'acceptance':[],'build_ok':True})
        for app in ('admin-web','mobile-web'):
            write(self.root,f'product/{app}/package.json',{})
            old=self.root/f'product/{app}/dist/{app}/browser/index.html'
            old.parent.mkdir(parents=True);old.write_text('previous attempt')
        ok=SandboxResult(ok=True,exit_code=0,duration_ms=1,failed=[],output_tail='')
        bad=SandboxResult(ok=False,exit_code=1,duration_ms=1,failed=['build failed'],output_tail='build failed')
        sandbox=FakeSandbox({('build','backend'):[ok],('test','backend'):[ok],('build','admin'):[bad],
                             ('build','pwa'):[bad],('scan','stack'):[ok],('down','stack'):[ok]})
        sandbox.keep_stand=True
        output=verify(StageInput(run_id='r',stage='verify',attempt=1,requirements='r',artifacts={'analysis':'analysis.json','tests':'tests.json'}),self.root,FakeLLM({}),sandbox)
        self.assertFalse(any(call['kind']=='up' for call in sandbox.calls))
        self.assertFalse(json.loads((self.root/output.artifacts['verification']).read_text())['stand']['up'])
    def test_dispute_rejection_and_single_attempt(self):
        from stages.tests.dispute import resolve
        from contracts.verification import Dispute
        from contracts.stage import ContractError
        (self.root/'product').mkdir();(self.root/'product/test.cs').write_text('original')
        write(self.root,'reports/tests.json',{'schema_version':1,'tests':[{'id':'test','ac':'AC-01','file':'product/test.cs','level':'unit'}],'hashes':{},'acceptance':['AC-01'],'build_ok':True})
        write(self.root,'spec/analysis.json',{'acceptance':[{'id':'AC-01'}]})
        dispute=Dispute(test='test',ac='AC-01',reason='question',hook='Hook')
        decision=resolve(dispute,self.root,FakeLLM({'qa':[{'decision':'reject','reason':'Тест соответствует AC'}]}),FakeSandbox({}))
        self.assertEqual(decision.decision,'reject');self.assertEqual((self.root/'product/test.cs').read_text(),'original')
        with self.assertRaises(ContractError):resolve(dispute,self.root,FakeLLM({}),FakeSandbox({}))
    def test_dispute_fix_restores_production_hook_and_accepts_hash(self):
        from stages.tests.dispute import resolve
        from contracts.verification import Dispute
        from harness.workspace import describe
        product=self.root/'product';product.mkdir()
        hook=product/'hook.cs';hook.write_text('implemented')
        test=product/'test.cs';test.write_text('original')
        write(self.root,'reports/tests.json',{'schema_version':1,'tests':[{'id':'AC-01','ac':'AC-01','file':'product/test.cs','level':'unit','failure_kind':'assertion','red_proof':True}],'hashes':{'product/test.cs':describe(self.root,'product/test.cs')[0]},'acceptance':['AC-01'],'build_ok':True})
        write(self.root,'spec/analysis.json',{'acceptance':[{'id':'AC-01'}]})
        write(self.root,'reports/redproof-stubs.json',{'Hook':{'file':'product/hook.cs','source':'stub'}})
        (self.root/'junit.xml').write_text('<testsuite><testcase classname="AC_01" name="Boundary"><failure type="Xunit.Sdk.EqualException" message="Assert.Equal"/></testcase></testsuite>')
        ok=SandboxResult(ok=True,exit_code=0,duration_ms=1,failed=[],output_tail='')
        red=SandboxResult(ok=False,exit_code=1,duration_ms=1,failed=['Assert'],output_tail='',reports={'junit':'junit.xml'})
        class Sandbox(FakeSandbox):
            accepted=[]
            def approve_test_change(self,*args):self.accepted.append(args)
        sandbox=Sandbox({('build','backend'):[ok],('test','backend'):[red]})
        llm=FakeLLM({'qa':[{'decision':'fix','reason':'Исправить ожидание'},'// AC-01\nAssert.Equal(true, actual);']})
        result=resolve(Dispute(test='AC-01',ac='AC-01',hook='Hook',reason='wrong'),self.root,llm,sandbox)
        self.assertEqual(result.decision,'fix');self.assertEqual(hook.read_text(),'implemented')
        self.assertEqual(len(sandbox.accepted),1)
