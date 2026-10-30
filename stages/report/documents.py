"""Deterministic documentation and metrics; model text never supplies numbers."""
import json
import os
from pathlib import Path
from harness.fakes import workspace_path


def metrics(snapshot,develop,root,ac_count):
    result=dict(snapshot.get('metrics',{}));totals=result.get('totals',{})
    hooks=develop.get('hooks',[])
    attempts=[h.get('attempts') for h in hooks]
    result['attempts_per_hook']=sum(attempts)/len(attempts) if attempts and all(isinstance(a,int) for a in attempts) else None
    result['first_pass_rate']=sum(h.get('status')=='implemented' and h.get('attempts')==1 for h in hooks)/len(hooks) if hooks else None
    tokens=None if totals.get('unknown_usage_calls') or any(totals.get(k) is None for k in ('tokens_in','tokens_out')) else totals['tokens_in']+totals['tokens_out']
    result['tokens_per_ac']=tokens/ac_count if tokens is not None and ac_count else None
    result['interventions']=totals.get('manual_interventions')
    source=deterministic=0
    files=[]
    for folder,dirs,names in os.walk(root/'product'):
        # Prune restored packages and build output: rglob would walk them first, minutes on a bind mount.
        dirs[:]=[d for d in dirs if d not in ('node_modules','bin','obj','dist','.git','.nuget','.npm','.angular')]
        files.extend(Path(folder)/name for name in names)
    for path in files:
        if path.suffix not in ('.cs','.ts','.html','.css','.sql'):continue
        try:lines=sum(bool(line.strip()) for line in path.read_text().splitlines())
        except (UnicodeError,OSError):continue
        source+=lines
        if not any(p.lower() in ('hooks','custom') for p in path.parts):deterministic+=lines
    result['deterministic_code_ratio']=deterministic/source if source else None
    return result


def documents(root,analysis,app,ui,verification,report,text):
    docs=workspace_path(root,'product/docs');docs.mkdir(parents=True,exist_ok=True)
    navigation=['  - Паспорт: index.md','  - Система: system.md','  - Эксплуатация: operations.md','  - Трассировка: trace.md']
    roles=app.get('roles',{}) or {r['id']:{'name':r.get('name',r['id'])} for r in analysis.get('roles',[])}
    import re
    for role,data in roles.items():
        safe=re.sub(r'[^a-zA-Z0-9_-]','_',role);name=data.get('name',role)
        body=['# '+name]
        for story in analysis.get('user_stories',[]):
            if story.get('role')!=role:continue
            body+=['','## '+story['id']+' — '+story.get('want','Сценарий')]
            walk=ui.get('walks',{}).get(story['id'])
            if walk:
                body += [f'{i}. `{json.dumps(step,ensure_ascii=False)}`' for i,step in enumerate(walk.get('steps',[]),1)]
            else:body+=['Проход интерфейса отсутствует; сценарий не проверен.']
        body+=['','Скриншоты текущего прогона не предоставлены.']
        (docs/f'role-{safe}.md').write_text('\n'.join(body)+'\n')
        navigation.append(f'  - {name}: role-{safe}.md')
    entities=app.get('entities',{})
    system=['# Система','','## Сущности','','```mermaid','erDiagram']
    for name,data in entities.items():
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',name):continue
        system += ['    '+name+' {']
        for field,spec in data.get('fields',{}).items():
            if re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',field):system+=['        string '+field]
        system+=['    }']
    system+=['```','']
    for title,key in [('Права','permissions'),('Параметры','params'),('Состояния','state_machines'),('События','events'),('Интеграции','integrations')]:
        system+=['## '+title,'','```json',json.dumps(app.get(key,{}),ensure_ascii=False,indent=2),'```','']
    (docs/'system.md').write_text('\n'.join(system))
    trace=['# Трассировка','','| REQ | US | BR | AC | Хуки | Тесты | Статус |','|---|---|---|---|---|---|---|']
    for ac in analysis.get('acceptance',[]):
        stories=[u for u in analysis.get('user_stories',[]) if u['id'] in ac.get('stories',[])]
        req=sorted({r for u in stories for r in u.get('req',[])})
        hooks=[name for name,h in app.get('hooks',{}).items() if ac['id'] in h.get('traces',[])]
        row=next((r for r in report.ac if r.id==ac['id']),None)
        trace+=['| '+' | '.join([', '.join(req),', '.join(ac.get('stories',[])),', '.join(ac.get('rules',[])),ac['id'],', '.join(hooks),str(row.tests if row else 0),row.status if row else 'not_checked'])+' |']
    (docs/'trace.md').write_text('\n'.join(trace)+'\n')
    (docs/'index.md').write_text(text)
    (docs/'operations.md').write_text('# Эксплуатация\n\nЗапуск: `docker compose -f infra/docker-compose.yml up -d --wait`.\n\nСтатусы сервисов: `docker compose -f infra/docker-compose.yml ps`.\nЛоги: `docker compose -f infra/docker-compose.yml logs`.\n\nПри ошибке health проверьте подключение БД, миграции и переменные окружения продукта. Секреты платформы в продукт не передаются.\n')
    workspace_path(root,'product/mkdocs.yml').write_text('site_name: Документация продукта\ntheme:\n  name: material\ndocs_dir: docs\nnav:\n'+'\n'.join(navigation)+'\n')
