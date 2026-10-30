"""Small shared QA artifact helpers; no database or platform imports."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from contracts.stage import ContractError
from contracts.verification import TestCase
from harness.fakes import workspace_path


def read(root, artifacts, name, *, optional=False):
    path=artifacts.get(name)
    if not path:
        if optional: return {}
        raise ContractError(f'Нет артефакта {name}')
    try: return json.loads(workspace_path(root,path).read_text(encoding='utf-8'))
    except (ValueError,OSError) as exc: raise ContractError(f'Не читается {name}') from exc


def write(root, path, data):
    target=workspace_path(root,path);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def junit(root, result, planned):
    """An absent report proves nothing, even if the command exits zero."""
    report=result.reports.get('junit')
    if not report:
        return [TestCase(id=t.id,ac=t.ac,level=t.level,file=t.file,status='not_run',message='JUnit отсутствует') for t in planned]
    try: tree=ET.parse(workspace_path(root,report))
    except (OSError,ET.ParseError) as exc: raise ContractError('Некорректный JUnit') from exc
    cases=[]
    for node in tree.iter('testcase'):
        ident=node.attrib.get('classname','')+'.'+node.attrib.get('name','')
        match=next((t for t in planned if t.id==ident or t.id==node.attrib.get('name')),None)
        failure=node.find('failure');error=node.find('error')
        bad=failure if failure is not None else error
        status='skipped' if node.find('skipped') is not None else 'failed' if bad is not None else 'passed'
        cases.append(TestCase(id=ident,ac=match.ac if match else None,level=match.level if match else 'unit',file=match.file if match else node.attrib.get('file',''),status=status,message=(bad.attrib.get('type','')+': '+bad.attrib.get('message','')) if bad is not None else None))
    for t in planned:
        if not any(c.id==t.id or c.id.endswith('.'+t.id) for c in cases):
            cases.append(TestCase(id=t.id,ac=t.ac,level=t.level,file=t.file,status='not_run',message='Тест отсутствует в JUnit'))
    return cases
