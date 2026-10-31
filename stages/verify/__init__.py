from contracts.stage import StageOutput,StageFailed,ContractError
from contracts.verification import TestsManifest,Verification,AcStatus,TestCase
from harness.workspace import describe
from stages.quality import read,write,junit


def execute(inp,workspace,llm,sandbox):
    workspace=workspace.resolve()
    plan=TestsManifest.model_validate(read(workspace,inp.artifacts,'tests'))
    analysis=read(workspace,inp.artifacts,'analysis')
    develop=read(workspace,inp.artifacts,'develop',optional=True)
    build={};cases=[];scans=[];stand={'up':False,'e2e':{},'down':False}
    mismatches=[p for p,h in plan.hashes.items() if describe(workspace,p)[0]!=h]
    # The stand builds every web app offline from its restored node_modules, so each one present is built here.
    targets=['backend']+[t for t,app in (('admin','admin-web'),('pwa','mobile-web')) if (workspace/'product'/app/'package.json').is_file()]
    for target in targets:
        try:result=sandbox.run('build',target)
        except ContractError as exc:
            # A platform the template cannot build yet is a failed check, not a crashed stage.
            build[target]=False;cases.append(TestCase(id=f'build/{target}',ac=None,level='unit',file='',status='not_run',message=str(exc)));continue
        # 127 from a tool inside the container is a failed build; only a missing docker CLI is fatal.
        if result.exit_code==127 and result.output_tail.startswith('Не удалось запустить инструмент'):raise StageFailed('Песочница недоступна')
        build[target]=result.ok
        if result.ok:
            tested=sandbox.run('test',target)
            planned=[t for t in plan.tests if t.level!='e2e'] if target=='backend' else []
            cases.extend(junit(workspace,tested,planned))
    mutations=[]
    if build.get('backend') and cases and all(c.status=='passed' for c in cases):
        from stages.verify.mutations import run
        hooks=read(workspace,inp.artifacts,'hooks')
        mutations=run(workspace,hooks,plan.tests,sandbox)
    scan=sandbox.run('scan','stack')
    from stages.verify.parsers import scan_results,playwright
    scans=scan_results(workspace,scan)
    try:
        if not getattr(sandbox,'keep_stand',False) or all(build.values()):
            stand['up']=sandbox.run('up','stack').ok
        if stand['up']:
            for target in [t for t in targets if t!='backend' and build.get(t)]:
                evidence=playwright(workspace,sandbox.run('e2e',target))
                stand['e2e'][target]=evidence['ok']
                stand.setdefault('e2e_results',{})[target]=evidence
    finally:
        if getattr(sandbox,'keep_stand',False) and stand['up']:
            from harness import prototype
            try:
                prototype.reset_data(inp.run_id)
                stand['data_reset']=True
                prototype.mark_ready(inp.run_id)
                stand['url']=prototype.url(inp.run_id)
            except Exception:
                stand['down']=sandbox.run('down','stack').ok
                raise
        else:
            stand['down']=sandbox.run('down','stack').ok
    status={}
    for ac in analysis.get('acceptance',[]):
        ident=ac['id'];tests=[c for c in cases if c.ac==ident];planned=[t for t in plan.tests if t.ac==ident]
        hook_specs=read(workspace,inp.artifacts,'hooks')
        hook_ids={h['id'] for h in hook_specs if ident in h.get('refs',[])}
        hooks=[h for h in develop.get('hooks',[]) if h.get('id') in hook_ids]
        implemented=bool(hooks) and all(h.get('status')=='implemented' for h in hooks)
        passed=bool(tests) and all(t.status=='passed' for t in tests) and not mismatches
        status[ident]=AcStatus(specified=True,tested=bool(tests),red_proof=all(t.red_proof is True for t in planned) if planned and not all(t.neutral for t in planned) else None,implemented=implemented,passes=passed,e2e=all(stand['e2e'].values()) if ac.get('ui') and stand['e2e'] else None,reason=None if passed and implemented else 'Реализация или проверка не подтверждена')
    report=Verification(build=build,tests=cases,mutations=mutations,scans=scans,stand={**stand,'hash_mismatches':mismatches},ac_status=status)
    write(workspace,'reports/verification.json',report.model_dump())
    return StageOutput(artifacts={'verification':'reports/verification.json'},summary='Проверки завершены; результаты в verification.json')
