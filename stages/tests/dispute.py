import json
import hashlib
from contracts.verification import Dispute,DisputeDecision,TestsManifest
from contracts.stage import ContractError
from harness.fakes import workspace_path
from stages.quality import read,write,junit,assertion_failure
from stages.tests import save
from stages.tests.lint import lint


def resolve(dispute:Dispute,workspace,llm,sandbox)->DisputeDecision:
    plan=TestsManifest.model_validate(read(workspace,{'tests':'reports/tests.json'},'tests'))
    test=next((t for t in plan.tests if t.id==dispute.test and t.ac==dispute.ac),None)
    if not test:raise ContractError('Оспариваемый тест не найден')
    history=workspace_path(workspace,'reports/disputes.json')
    records=json.loads(history.read_text()) if history.exists() else []
    if any(r['test']==test.id for r in records):raise ContractError('Повторный спор запрещён')
    analysis=read(workspace,{'analysis':'spec/analysis.json'},'analysis')
    ac=next(a for a in analysis['acceptance'] if a['id']==test.ac)
    path=workspace_path(workspace,test.file);original=path.read_bytes()
    decision=llm(task_class='qa',system='Decide whether the test contradicts the original acceptance criterion. Never see the production implementation.',user=json.dumps({'dispute':dispute.model_dump(),'ac':ac,'test':original.decode()},ensure_ascii=False),output=DisputeDecision,task_id=test.ac)
    if decision.decision=='fix':
        try:
            code=llm(task_class='qa',system='Correct only the disputed test to match the AC.',user=json.dumps({'ac':ac,'test':original.decode(),'reason':decision.reason},ensure_ascii=False),output='code',task_id=test.ac)
            if lint(code,test.ac):raise ContractError('Исправление не прошло линтер')
            path.write_text(code)
            if not sandbox.run('build','backend').ok:raise ContractError('Исправление не собрано')
            stubs=read(workspace,{'stubs':'reports/redproof-stubs.json'},'stubs')
            stub=stubs.get(dispute.hook)
            if not stub:raise ContractError('Нет сохранённой заглушки для спора')
            hook_path=workspace_path(workspace,stub['file']);hook_original=hook_path.read_bytes()
            try:
                hook_path.write_text(stub['source'])
                cases=junit(workspace,sandbox.run('test','backend',filter=test.ac),[test])
            finally:hook_path.write_bytes(hook_original)
            valid=all(c.status=='passed' for c in cases) if test.neutral else any(c.status=='failed' and assertion_failure(c) for c in cases)
            if not valid:raise ContractError('Red-proof исправления не подтверждён')
            test.failure_kind='none' if test.neutral else 'assertion'
            test.red_proof=None if test.neutral else True
            test.lint=[]
            save(workspace,plan)
            from gates.g2_redproof import check
            gate=check(workspace,{'tests':'reports/tests.json'})
            if not gate.passed:raise ContractError('Исправление не прошло G2')
            accept=getattr(sandbox,'approve_test_change',None)
            if accept is None:raise ContractError('Не подключено доверенное принятие хэша платформой')
            accept(test.file, hashlib.sha256((test.id+dispute.reason).encode()).hexdigest(), gate)
        except Exception:
            path.write_bytes(original)
            save(workspace,plan)
            decision=DisputeDecision(decision='reject',reason='Исправление не прошло повторную проверку')
    records.append({'test':test.id,'ac':test.ac,'decision':decision.decision,'reason':decision.reason,'old_hash':hashlib.sha256(original).hexdigest(),'new_hash':hashlib.sha256(path.read_bytes()).hexdigest()})
    write(workspace,'reports/disputes.json',records)
    if decision.decision=='fix':save(workspace,plan)
    return decision
