"""Bounded lexical mutations of a hook body; always restore exact bytes."""
import re
from harness.fakes import workspace_path
from stages.quality import junit,assertion_failure


def candidates(source):
    # Restrict mutation sites to text inside method/class braces, not signatures.
    masked=re.sub(r'//[^\n]*|/\*.*?\*/|@?"(?:\\.|""|[^"\\])*"',lambda m:' '*len(m.group()),source,flags=re.S)
    method=re.search(r'\)\s*\{',masked)
    if not method:return []
    start=method.end();depth=1;end=start
    while end<len(masked) and depth:
        depth+=(masked[end]=='{')-(masked[end]=='}');end+=1
    if start<0 or end<=start:return []
    body=masked[start:end-1];values=[]
    for pattern,replacement in [(r'>=','>'),(r'<=','<'),(r'==','!='),(r'&&','||'),(r'\|\|','&&'),(r'\btrue\b','false'),(r'\bfalse\b','true')]:
        for match in re.finditer(pattern,body):
            values.append(source[:start+match.start()]+replacement+source[start+match.end():])
    for match in re.finditer(r'(?<![\w.])\d+(?![\w.])',body):
        values.append(source[:start+match.start()]+str(int(match.group())+1)+source[start+match.end():])
    return list(dict.fromkeys(values))[:5]


def run(workspace,hooks,planned,sandbox):
    reports=[]
    for hook in hooks:
        related=[t for t in planned if t.ac in hook.get('refs',[])]
        if not related:continue
        path=workspace_path(workspace,'product/'+hook['file']);original=path.read_bytes()
        changes=candidates(original.decode())
        for i,source in enumerate(changes):
            try:
                path.write_text(source,encoding='utf-8')
                result=sandbox.run('test','backend',filter=related[0].ac)
                cases=junit(workspace,result,related)
                assertion=any(c.status=='failed' and assertion_failure(c) for c in cases)
                reports.append({'hook':hook['id'],'mutation':i,'status':'killed' if assertion else 'survived' if cases and all(c.status=='passed' for c in cases) else 'invalid'})
            finally:
                path.write_bytes(original)
                assert path.read_bytes()==original
        if len(changes)<3:reports.append({'hook':hook['id'],'status':'not_run','reason':'Недостаточно применимых мутаций'})
    return reports
