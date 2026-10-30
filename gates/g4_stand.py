from contracts.gates import GateResult,Finding
from stages.quality import read


def check(workspace,artifacts):
    data=read(workspace,artifacts,'verification')['stand'];findings=[]
    for ok,code,message in [(data.get('up'),'STAND_DOWN','Стенд не поднят'),(data.get('smoke'),'SMOKE_FAILED','Smoke не подтверждён')]:
        if not ok:findings.append(Finding(path='stand',code=code,severity='error',message=message))
    if not data.get('e2e') or not all(data['e2e'].values()):findings.append(Finding(path='stand/e2e',code='E2E_FAILED',severity='warning',message='E2E не подтверждён'))
    return GateResult(gate='G4',passed=not any(f.severity=='error' for f in findings),findings=findings)
