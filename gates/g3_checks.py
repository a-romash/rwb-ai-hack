from contracts.gates import GateResult,Finding
from contracts.verification import Verification
from stages.quality import read


def check(workspace,artifacts):
    data=Verification.model_validate(read(workspace,artifacts,'verification'));findings=[]
    def add(path,code,message,severity='error'):findings.append(Finding(path=path,code=code,severity=severity,message=message))
    for target,ok in data.build.items():
        if not ok:add('build/'+target,'BUILD_FAILED','Цель не собрана')
    for path in data.stand.get('hash_mismatches',[]):add(path,'TEST_HASH_MISMATCH','Изменён защищённый тест')
    for ac,status in data.ac_status.items():
        if not status.passes:add('acceptance/'+ac,'AC_RED','Критерий не подтверждён','warning')
    for mutation in data.mutations:
        if mutation.get('status')=='survived':add('hooks/'+mutation['hook'],'MUTANT_SURVIVED','Мутация выжила','warning')
    if not data.mutations:add('mutations','MUTATION_NOT_RUN','Мутации не проверены','warning')
    for scan in data.scans:
        if scan.get('severity','').lower() in ('high','critical'):add('scans','SCAN_HIGH','Опасная находка сканера')
        if scan.get('status')=='completed' and not scan.get('ok',False):add('scans','SCAN_FAILED','Сканер завершился ошибкой')
        if scan.get('status')=='not_run':add('scans','SCAN_NOT_RUN','Сканирование не подтверждено')
    for t in data.tests:
        if t.status in ('skipped','not_run'):add('tests/'+t.id,'SKIPPED_AS_PASS','Проверка не выполнена')
    return GateResult(gate='G3',passed=not any(f.severity=='error' for f in findings),findings=findings)
