"""Normalize machine scanner and Playwright results without trusting exit zero."""
import json
from harness.fakes import workspace_path
from contracts.stage import ContractError


def scan_results(root,result):
    paths=result.reports
    if not paths:return [{'status':'not_run','reason':'Нет машинного отчёта сканера'}]
    scans=[]
    for kind,path in paths.items():
        if kind not in ('sarif','json'):continue
        data=json.loads(workspace_path(root,path).read_text())
        if isinstance(data,list):
            scans.extend({'status':'finding','severity':'high','message':d.get('Description','Обнаружен секрет')} for d in data)
        elif 'runs' in data:
            for run in data['runs']:
                rules={r['id']:r for r in run.get('tool',{}).get('driver',{}).get('rules',[])}
                for item in run.get('results',[]):
                    rule=rules.get(item.get('ruleId'),{})
                    score=rule.get('properties',{}).get('security-severity')
                    severity=item.get('properties',{}).get('severity')
                    if not severity:
                        severity='critical' if score and float(score)>=9 else 'high' if score and float(score)>=7 else 'medium' if item.get('level')=='warning' else 'unknown'
                    scans.append({'status':'finding','severity':severity,'message':item.get('message',{}).get('text','')})
        elif 'Results' in data:
            for target in data['Results']:
                for item in target.get('Vulnerabilities',[]) or []:
                    scans.append({'status':'finding','severity':item.get('Severity','unknown').lower(),'message':item.get('VulnerabilityID','')})
        else:raise ContractError('Неизвестный формат отчёта сканера')
        scans.append({'status':'completed','ok':result.ok})
    return scans or [{'status':'not_run','reason':'Формат отчёта не поддерживается'}]


def playwright(root,result):
    path=result.reports.get('json')
    if not path:return {'ok':False,'reason':'Нет JSON Playwright','tests':[]}
    data=json.loads(workspace_path(root,path).read_text());tests=[]
    def visit(suite):
        for spec in suite.get('specs',[]):
            for test in spec.get('tests',[]):
                results=test.get('results',[])
                tests.append({'title':spec.get('title',''),'status':results[-1].get('status','not_run') if results else 'not_run'})
        for child in suite.get('suites',[]):visit(child)
    for suite in data.get('suites',[]):visit(suite)
    return {'ok':result.ok and bool(tests) and all(t['status']=='passed' for t in tests),'tests':tests}
