import json
import re
from contracts.stage import StageOutput,BudgetExceeded,ContractError
from contracts.report import Report,ReportRun,AcReport
from stages.quality import read,write
from harness.fakes import workspace_path


def execute(inp,workspace,llm,sandbox):
    workspace=workspace.resolve()
    analysis=read(workspace,inp.artifacts,'analysis',optional=True)
    app=read(workspace,inp.artifacts,'app',optional=True)
    verification=read(workspace,inp.artifacts,'verification',optional=True)
    snapshot=inp.snapshot or {}
    from stages.report.documents import metrics as calculate_metrics,documents
    develop=read(workspace,inp.artifacts,'develop',optional=True)
    metrics=calculate_metrics(snapshot,develop,workspace,len(analysis.get('acceptance',[])))
    ac=[]
    for item in analysis.get('acceptance',[]):
        state=verification.get('ac_status',{}).get(item['id'],{})
        tests=[t for t in verification.get('tests',[]) if t.get('ac')==item['id']]
        status='not_checked' if not state else 'not_implemented' if not state.get('implemented') else 'green' if state.get('passes') else 'red'
        ac.append(AcReport(id=item['id'],status=status,tests=len(tests),reason=state.get('reason','Не проверено')))
    missing=[]
    for key,data in [('analysis',analysis),('app',app),('verification',verification)]:
        if not data:missing.append({'what':key,'why':'Артефакт не создан'})
    report=Report(run=ReportRun(id=inp.run_id,status=snapshot.get('status','failed'),autonomy=inp.autonomy),verdict={'ac_total':len(ac),'ac_green':sum(a.status=='green' for a in ac),'ac_red':sum(a.status=='red' for a in ac),'ac_not_implemented':sum(a.status=='not_implemented' for a in ac)},ac=ac,assumptions=analysis.get('assumptions',[]),flags=snapshot.get('flags',[]),checks={k:verification.get(k) for k in ('build','tests','mutations','scans','stand')},metrics=metrics,not_done=missing,links={'stand':None,'docs':'product/docs/index.md','openapi':inp.artifacts.get('openapi')})
    write(workspace,'reports/report.json',report.model_dump())
    narrative='Связный текст не сформирован: бюджет модели недоступен.'
    try:
        narrative=llm(task_class='writer',system='Write a short Russian summary without numeric literals. Use {{ac:AC-ID}} for AC references. Never invent success or measurements.',user=json.dumps({'status':report.run.status,'not_done':missing},ensure_ascii=False),output='text')
    except BudgetExceeded:pass
    placeholders={'ac:'+a.id:a.status for a in ac}
    for key,value in app.get('params',{}).items():
        placeholders['param:'+key]=str(value.get('value') if isinstance(value,dict) else value)
    def flatten(prefix,value):
        if isinstance(value,dict):
            for key,item in value.items():flatten(prefix+'.'+key if prefix else key,item)
        elif not isinstance(value,list):placeholders['metric:'+prefix]='неизвестно' if value is None else str(value)
    flatten('',metrics)
    write(workspace,'reports/narrative.json',{'text':narrative})
    def replace(match):
        key=match.group(1)
        if key not in placeholders:raise ContractError('Неизвестный плейсхолдер '+key)
        return placeholders[key]
    rendered=re.sub(r'\{\{([^{}]+)\}\}',replace,narrative)
    text='# Отчёт\n\n'+rendered+'\n\n| AC | Статус | Тестов |\n|---|---|---|\n'+''.join(f'| {a.id} | {a.status} | {a.tests} |\n' for a in ac)
    target=workspace_path(workspace,'reports/report.md');target.write_text(text,encoding='utf-8')
    ui=read(workspace,inp.artifacts,'ui',optional=True)
    documents(workspace,analysis,app,ui,verification,report,text)
    return StageOutput(artifacts={'report':'reports/report.json','report_markdown':'reports/report.md','docs':'product/docs'},summary='Отчёт сформирован из фактических результатов')


def analysis_roles(analysis,app):
    return {r['id']:r.get('name',r['id']) for r in analysis.get('roles',[])} or {key:value.get('name',key) for key,value in app.get('roles',{}).items()}
