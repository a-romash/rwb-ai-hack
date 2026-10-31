from contracts.gates import GateResult,Finding
from contracts.verification import TestsManifest
import json
from harness.fakes import workspace_path
from stages.quality import read
from stages.tests.cases import CASES,contradictions


def check(workspace,artifacts):
    data=TestsManifest.model_validate(read(workspace,artifacts,'tests'))
    findings=[]
    def add(path,code,message):findings.append(Finding(path=path,code=code,severity='error',message=message))
    for ac in data.acceptance:
        if not any(t.ac==ac for t in data.tests):add('tests/'+ac,'AC_NO_TEST','Нет теста критерия')
    for t in data.tests:
        path='tests/'+t.id
        for code in t.lint:add(path,code,'Тест не прошёл линтер')
        if not data.build_ok or t.failure_kind in ('setup','compile','unknown'):add(path,'TEST_FAILS_WRONG','Нет доказательства падения на проверке')
        elif not t.neutral and t.red_proof is not True:add(path,'TEST_GREEN_ON_STUB','Тест не выявляет заглушку')
    root=workspace_path(workspace,CASES)
    for path in sorted(root.glob('*.json')) if root.is_dir() else []:
        for ac,message in contradictions(json.loads(path.read_text(encoding='utf-8')).get('cases') or []):
            add('tests/'+str(ac),'CASES_CONTRADICT',f'{path.stem}: {message}')
    return GateResult(gate='G2',passed=not findings,findings=findings)
