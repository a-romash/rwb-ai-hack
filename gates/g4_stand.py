from contracts.gates import GateResult,Finding
from stages.quality import read


def check(workspace,artifacts):
    data=read(workspace,artifacts,'verification')['stand'];findings=[]
    if not data.get('up'):findings.append(Finding(path='stand',code='STAND_DOWN',severity='error',message='Стенд не поднят'))
    if not data.get('e2e') or not all(data['e2e'].values()):findings.append(Finding(path='stand/e2e',code='E2E_FAILED',severity='warning',message='E2E не подтверждён'))
    return GateResult(gate='G4',passed=not any(f.severity=='error' for f in findings),findings=findings)
