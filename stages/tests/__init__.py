import hashlib
import json
import re
from contracts.stage import StageOutput,ContractError,BudgetExceeded
from contracts.verification import TestsManifest,PlannedTest
from harness.fakes import workspace_path
from stages.quality import read,write,junit
from stages.tests.lint import lint


def context(analysis,app,hooks,openapi,ac):
    ids=ac.get('rules',[])
    return {'acceptance':ac,'requirements':[r for r in analysis.get('requirements',[])],
            'rules':[r for r in analysis.get('rules',[]) if r['id'] in ids],
            'params':app.get('params',{}),'hooks':[{k:v for k,v in h.items() if k in ('id','signature','contract','examples','allowed_api','refs')} for h in hooks if ac['id'] in h.get('refs',[])],
            'openapi':openapi}


def execute(inp,workspace,llm,sandbox):
    analysis=read(workspace,inp.artifacts,'analysis');app=read(workspace,inp.artifacts,'app')
    hooks=read(workspace,inp.artifacts,'hooks');api=read(workspace,inp.artifacts,'openapi')
    tests=[]
    for ac in analysis.get('acceptance',[]):
        ident=ac['id']
        if not re.fullmatch(r'AC-[A-Za-z0-9_-]+',ident):raise ContractError('Недопустимый AC id')
        file=f'product/backend/tests/App.Acceptance.Tests/Generated/{ident.replace("-","_")}.cs'
        packet=context(analysis,app,hooks,api,ac)
        try:
            code=llm(task_class='qa',system='Write xUnit tests using the supplied public contracts only. Tag each test with Trait("AC", acceptance.id). Use TestClock, never real time. Expected results must come from AC examples, not production algorithms. Return C# code only.',user=json.dumps(packet,ensure_ascii=False),output='code',task_id=ident)
        except BudgetExceeded:break
        target=workspace_path(workspace,file);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(code,encoding='utf-8')
        tests.append(PlannedTest(id=ident,ac=ident,file=file,level='unit',neutral=ac.get('neutral_expectation',False),lint=lint(code,ident)))
    from stages.tests.e2e import generate
    generate(workspace, read(workspace,inp.artifacts,'ui'))
    build=sandbox.run('build','backend')
    for repair_round in range(2):
        if build.ok:break
        for t in tests:
            packet=context(analysis,app,hooks,api,next(ac for ac in analysis['acceptance'] if ac['id']==t.ac))
            code=llm(task_class='qa',system='Repair only this C# test compilation. Preserve AC and assertions.',user=json.dumps({'contract':packet,'test':workspace_path(workspace,t.file).read_text(),'errors':build.failed},ensure_ascii=False),output='code',task_id=t.ac)
            workspace_path(workspace,t.file).write_text(code,encoding='utf-8');t.lint=lint(code,t.ac)
        build=sandbox.run('build','backend')
    manifest=TestsManifest(tests=tests,hashes={},acceptance=[a['id'] for a in analysis.get('acceptance',[])],build_ok=build.ok)
    if build.ok:
        for t in tests:
            result=sandbox.run('test','backend',filter=t.ac)
            cases=junit(workspace,result,[t])
            failed=[c for c in cases if c.status=='failed']
            assertion=any(c.message and ('assert' in c.message.lower() or 'xunit' in c.message.lower()) for c in failed)
            t.failure_kind='assertion' if assertion else 'setup' if failed else 'none' if all(c.status=='passed' for c in cases) else 'unknown'
            t.red_proof=None if t.neutral else assertion
    else:
        for t in tests:t.failure_kind='compile'
    save(workspace,manifest)
    return StageOutput(artifacts={'tests':'reports/tests.json'},summary=f'Тесты для {len(tests)} из {len(manifest.acceptance)} AC')


def save(workspace,manifest):
    manifest.hashes={}
    for directory in ('product/backend/tests','product/admin-web/e2e','product/mobile-web/e2e'):
        root=workspace_path(workspace,directory)
        if root.exists():
            for path in sorted(root.rglob('*')):
                if path.is_file() and not any(part in ('bin','obj','node_modules') for part in path.parts):
                    relative=str(path.relative_to(workspace));workspace_path(workspace,relative)
                    manifest.hashes[relative]=hashlib.sha256(path.read_bytes()).hexdigest()
    write(workspace,'reports/tests.json',manifest.model_dump())


def repair(inp,workspace,llm,findings, *, sandbox=None):
    # Reuse accepted contracts, regenerate only addressed tests in a temporary view.
    data=TestsManifest.model_validate(read(workspace,{'tests':'reports/tests.json'},'tests'))
    selected={f.path.removeprefix('tests/') for f in findings}
    analysis=read(workspace,inp.artifacts,'analysis')
    affected={t.ac for t in data.tests if t.id in selected}|(selected & set(data.acceptance))
    for t in data.tests:
        if t.ac not in affected:continue
        code=llm(task_class='qa',system='Repair the test according to findings, preserving its AC. Return C#.',user=json.dumps({'acceptance':next(a for a in analysis['acceptance'] if a['id']==t.ac),'test':workspace_path(workspace,t.file).read_text(),'findings':[f.model_dump() for f in findings]},ensure_ascii=False),output='code',task_id=t.ac)
        workspace_path(workspace,t.file).write_text(code);t.lint=lint(code,t.ac)
        if sandbox is None:raise ContractError('Для repair требуется песочница')
        build=sandbox.run('build','backend');data.build_ok=build.ok
        result=sandbox.run('test','backend',filter=t.ac) if build.ok else None
        cases=junit(workspace,result,[t]) if result else []
        assertion=any(c.status=='failed' and c.message and ('assert' in c.message.lower() or 'xunit' in c.message.lower()) for c in cases)
        t.failure_kind='compile' if not build.ok else 'assertion' if assertion else 'none' if cases and all(c.status=='passed' for c in cases) else 'unknown'
        t.red_proof=None if t.neutral else assertion
    save(workspace,data)
    return StageOutput(artifacts={'tests':'reports/tests.json'},summary='Требуется повторная проверка исправленных тестов')
