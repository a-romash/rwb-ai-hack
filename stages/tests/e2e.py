"""Compile explicit UI walk steps; never ask a model to invent selectors."""
import json
from contracts.stage import ContractError
from harness.fakes import workspace_path


def generate(root,ui):
    files=[]
    screens=ui.get('screens',{})
    for ident,walk in ui.get('walks',{}).items():
        if not ident.replace('-','').isalnum():raise ContractError('Некорректный ID прохода')
        target='mobile-web' if walk.get('platform')=='mobile' else 'admin-web'
        lines=["import {test, expect, devices} from '@playwright/test';"]
        if target=='mobile-web':lines.append("test.use({...devices['Pixel 7']});")
        title=' '.join('@'+ac for ac in walk.get('covers',[]))+' '+ident
        lines.append('test('+json.dumps(title)+', async ({page}) => {')
        for step in walk.get('steps',[]):
            kinds=set(step)&{'open','fill','tap','expect'}
            if len(kinds)!=1:raise ContractError('Неподдерживаемый шаг UI')
            kind=next(iter(kinds));value=step[kind]
            if kind=='open':
                screen=screens.get(value,{})
                route=screen.get('route')
                if not route:raise ContractError('Экрану нужен явный route для E2E')
                lines.append('await page.goto('+json.dumps(route)+');')
            elif kind=='fill':
                if not isinstance(value,dict) or 'testid' not in value or 'value' not in value:raise ContractError('fill требует testid и value')
                lines.append('await page.getByTestId('+json.dumps(value['testid'])+').fill('+json.dumps(str(value['value']))+');')
            elif kind=='tap':
                selector=step.get('testid')
                if not selector:
                    actions=[a for screen in screens.values() for a in screen.get('actions',[]) if a.get('command')==value]
                    if len(actions)!=1:raise ContractError('Неоднозначный selector действия')
                    selector=actions[0]['testid']
                lines.append('await page.getByTestId('+json.dumps(selector)+').click();')
            else:
                if not isinstance(value,dict) or 'testid' not in value:raise ContractError('expect требует testid')
                selector='page.getByTestId('+json.dumps(value['testid'])+')'
                lines.append('await expect('+selector+').'+('toHaveText('+json.dumps(str(value['text']))+')' if 'text' in value else 'toBeVisible()')+';')
        lines.append('});')
        relative=f'product/{target}/e2e/{ident}.spec.ts'
        path=workspace_path(root,relative);path.parent.mkdir(parents=True,exist_ok=True);path.write_text('\n'.join(lines)+'\n')
        files.append(relative)
    return files
