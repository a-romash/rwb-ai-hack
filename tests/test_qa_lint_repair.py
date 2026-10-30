import json
import tempfile
import unittest
from pathlib import Path
from contracts.stage import StageInput, SandboxResult
from harness.fakes import FakeLLM, FakeSandbox
from stages.quality import write
from stages.tests import execute

class LintRepairTest(unittest.TestCase):
    def test_retries_for_rule_literal_and_keeps_evidence_unknown_without_junit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();artifacts={}
            source=Path('contracts/fixtures/tickets')
            for name in ('analysis','app','hooks','openapi','ui'):
                write(root,name+'.json',json.loads((source/(name+'.json')).read_text()));artifacts[name]=name+'.json'
            bad='// AC-01\nAssert.Equal(5, actual);'
            fixed='// AC-01\nAssert.Equal(App.Domain.Params.MIN_VALUE, actual);'
            llm=FakeLLM({'qa':[bad,fixed]})
            ok=SandboxResult(ok=True,exit_code=0,duration_ms=1,failed=[],output_tail='')
            sandbox=FakeSandbox({('build','backend'):[ok],('test','backend'):[ok]})
            output=execute(StageInput(run_id='r',stage='tests',attempt=1,requirements='r',artifacts=artifacts),root,llm,sandbox)
            test=json.loads((root/output.artifacts['tests']).read_text())['tests'][0]
            self.assertEqual(test['lint'],[])
            self.assertEqual(test['failure_kind'],'unknown')
            self.assertEqual(len(llm.calls),2)
            self.assertIn('TEST_FORBIDDEN',llm.calls[1]['user'])
