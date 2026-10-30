import json
import tempfile
import unittest
from pathlib import Path

from contracts.stage import SandboxResult, StageInput
from harness.fakes import FakeLLM, FakeSandbox
from stages.develop import execute


class NoTestsTest(unittest.TestCase):
    def test_hook_without_any_test_is_not_implemented(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hook = {'id': 'Allowed', 'file': 'backend/src/App.Domain/Hooks/AllowedHook.cs', 'refs': ['AC-01'],
                    'signature': 'public bool Validate(int value)', 'kind': 'validator'}
            (root / 'product/backend/src/App.Domain/Hooks').mkdir(parents=True)
            (root / 'product' / hook['file']).write_text('stub', encoding='utf-8')
            (root / 'product/hooks.json').write_text(json.dumps([hook]), encoding='utf-8')
            report = root / 'product/reports/junit/backend/empty.xml'
            report.parent.mkdir(parents=True)
            report.write_text('<testsuites/>', encoding='utf-8')
            ok = SandboxResult(ok=True, exit_code=0, duration_ms=1, failed=[], output_tail='')
            empty = ok.model_copy(update={'reports': {'junit': 'product/reports/junit/backend/empty.xml'}})
            sandbox = FakeSandbox({('build', 'backend'): [ok] * 6, ('test', 'backend'): [empty] * 6})
            llm = FakeLLM({('hook_1', 'Allowed'): ['body'], ('hook_2', 'Allowed'): ['body'],
                           ('hook_3', 'Allowed'): ['body'], ('hook_4', 'Allowed'): ['body'] * 3})
            out = execute(StageInput(run_id='r', stage='develop', attempt=1, requirements='r', artifacts={}), root, llm, sandbox)
            row = json.loads((root / out.artifacts['develop']).read_text(encoding='utf-8'))['hooks'][0]
            self.assertEqual(row['status'], 'stub')
            self.assertIn('нет ни одного теста', row['reason'])
            self.assertEqual((root / 'product' / hook['file']).read_text(encoding='utf-8'), 'stub')
