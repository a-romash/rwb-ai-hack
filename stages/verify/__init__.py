from contracts.stage import StageOutput,StageFailed
from contracts.verification import TestsManifest,Verification,AcStatus
from harness.workspace import describe
from stages.quality import read,write,junit


def execute(inp,workspace,llm,sandbox):
    plan=TestsManifest.model_validate(read(workspace,inp.artifacts,'tests'))
    analysis=read(workspace,inp.artifacts,'analysis')
    develop=read(workspace,inp.artifacts,'develop',optional=True)
    build={};cases=[];scans=[];stand={'up':False,'smoke':False,'e2e':{},'down':False}
    mismatches=[p for p,h in plan.hashes.items() if describe(workspace,p)[0]!=h]
    for target in ('backend','admin','pwa'):
        result=sandbox.run('build',target)
        if result.exit_code==127:raise StageFailed('Песочница недоступна')
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
    # A successful command without machine-readable evidence is not a clean scan.
    if scan.reports.get('sarif'):
        from harness.fakes import workspace_path
        import json
        data=json.loads(workspace_path(workspace,scan.reports['sarif']).read_text())
        for run in data.get('runs',[]):
            for finding in run.get('results',[]):
                scans.append({'status':'finding','severity':finding.get('properties',{}).get('severity','unknown'),'message':finding.get('message',{}).get('text','')})
        scans.append({'status':'completed','ok':scan.ok})
    else:scans.append({'status':'not_run','reason':'Нет машинного отчёта сканера'})
    try:
        stand['up']=sandbox.run('up','stack').ok
        if stand['up']:
            stand['smoke']=sandbox.run('smoke','stack').ok
            for target in ('admin','pwa'):stand['e2e'][target]=sandbox.run('e2e',target).ok
    finally:
        stand['down']=sandbox.run('down','stack').ok
    status={}
    for ac in analysis.get('acceptance',[]):
        ident=ac['id'];tests=[c for c in cases if c.ac==ident];planned=[t for t in plan.tests if t.ac==ident]
        hooks=[h for h in develop.get('hooks',[]) if ident in h.get('refs',h.get('ac',[]))]
        implemented=bool(hooks) and all(h.get('status')=='implemented' for h in hooks)
        passed=bool(tests) and all(t.status=='passed' for t in tests)
        status[ident]=AcStatus(specified=True,tested=bool(tests),red_proof=all(t.red_proof is True for t in planned) if planned and not all(t.neutral for t in planned) else None,implemented=implemented,passes=passed,e2e=all(stand['e2e'].values()) if ac.get('ui') and stand['e2e'] else None,reason=None if passed and implemented else 'Реализация или проверка не подтверждена')
    report=Verification(build=build,tests=cases,mutations=mutations,scans=scans,stand={**stand,'hash_mismatches':mismatches},ac_status=status)
    write(workspace,'reports/verification.json',report.model_dump())
    return StageOutput(artifacts={'verification':'reports/verification.json'},summary='Проверки завершены; результаты в verification.json')
