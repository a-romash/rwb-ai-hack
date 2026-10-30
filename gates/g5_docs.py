import re
from contracts.gates import GateResult,Finding
from stages.quality import read
from harness.fakes import workspace_path
from stages.report import analysis_roles


def check(workspace,artifacts):
    workspace=workspace.resolve()
    read(workspace,artifacts,'report')  # the report must exist even though only docs are inspected
    analysis=read(workspace,artifacts,'analysis',optional=True);app=read(workspace,artifacts,'app',optional=True)
    findings=[];docs=workspace_path(workspace,artifacts.get('docs','product/docs'))
    text='\n'.join(p.read_text(encoding='utf-8') for p in docs.rglob('*.md')) if docs.exists() else ''
    def add(code,message,severity='error'):findings.append(Finding(path='docs',code=code,severity=severity,message=message))
    for ac in analysis.get('acceptance',[]):
        if ac['id'] not in text:add('DOC_AC_MISSING','Критерий отсутствует в трассировке')
    for role in analysis_roles(analysis,app):
        safe=re.sub(r'[^a-zA-Z0-9_-]','_',role)
        if not (docs/f'role-{safe}.md').is_file():add('DOC_ROLE_MISSING','Нет руководства роли')
    narrative=workspace_path(workspace,'reports/narrative.json')
    if narrative.is_file():
        import json
        source=json.loads(narrative.read_text()).get('text','')
        # Ignore identifiers and placeholder contents, inspect only model prose.
        prose=re.sub(r'\{\{.*?\}\}|(?:AC|BR|REQ|US)-[A-Za-z0-9_-]+','',source)
        if re.search(r'\b\d+(?:[.,]\d+)?\b',prose):add('DOC_NUMBER_LITERAL','Числа в тексте модели должны быть плейсхолдерами','warning')
    if re.search(r'\{\{.+?\}\}',text):add('DOC_PLACEHOLDER','Плейсхолдер не разрешён')
    for path in docs.rglob('*.md') if docs.exists() else []:
        for link in re.findall(r'\]\(([^)]+)\)',path.read_text()):
            if '://' not in link and not link.startswith('#'):
                relative=str(path.parent.relative_to(workspace))+'/'+link.split('#')[0]
                try:exists=workspace_path(workspace,relative).exists()
                except Exception:exists=False
                if not exists:add('DOC_BROKEN_LINK','Битая ссылка','warning')
    return GateResult(gate='G5',passed=not any(f.severity=='error' for f in findings),findings=findings)
