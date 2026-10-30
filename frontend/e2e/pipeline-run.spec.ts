import {expect, test} from '@playwright/test';
import {makeProject, makeRun, mockApi} from './fixtures';

test.describe('Прогон конвейера', () => {
  test('статусы этапов и ворот из прогона, находки, решение человека и перезапуск', async ({page}) => {
    const project = makeProject('Заявки на ремонт');
    const run = makeRun(
      project.id,
      [
        {key: 'analysis', status: 'succeeded', summary: 'Ролей: 3, критериев: 9', gate: {gate: 'G0', passed: true, decided_by: 'code', findings: []}},
        {
          key: 'spec',
          status: 'waiting_human',
          gate: {gate: 'G1', passed: false, decided_by: 'code', findings: [{path: 'entities.Ticket', code: 'REF_UNRESOLVED', severity: 'error', message: 'Нет сущности Employee'}]},
        },
      ],
      'waiting',
      [{id: 'Q-01', text: 'Считать ли выходные рабочим временем?', options: ['Да', 'Нет'], default: 'Нет', why: 'От этого зависит SLA'}],
    );
    const api = await mockApi(page, {projects: [project], runs: [run]});
    await page.goto(`/projects/${project.id}/flow`);

    await expect(page.locator('app-run-panel')).toContainText('Ждёт человека');
    await expect(page.locator('app-run-panel')).toContainText('120 000 из 1 500 000 токенов');
    await expect(page.locator('[data-key="analysis"]')).toContainText('Готово');
    await expect(page.locator('[data-key="gate:G1"]')).toContainText('Ждёт решения');

    await page.locator('[data-key="gate:G1"]').click();
    const panel = page.locator('#station-panel');
    await expect(panel).toContainText('REF_UNRESOLVED');
    await panel.getByRole('button', {name: 'Принять и продолжить'}).click();
    await expect.poll(() => api.requests.some(r => r.url.endsWith('/gates/G1/decision') && (r.body as {decision: string}).decision === 'approve')).toBe(true);

    await page.locator('app-run-panel').getByRole('radio', {name: 'Да'}).check();
    await page.getByRole('button', {name: 'Ответить и продолжить'}).click();
    await expect.poll(() => api.requests.find(r => r.url.endsWith('/answers'))?.body).toEqual({answers: {'Q-01': 'Да'}});

    await page.locator('[data-key="analysis"]').click();
    await expect(panel).toContainText('Ролей: 3, критериев: 9');
    await panel.getByRole('button', {name: 'Перезапустить шаг'}).click();
    await expect.poll(() => api.requests.some(r => r.url.endsWith('/stages/analysis/retry'))).toBe(true);
  });

  test('запуск конвейера с выбранной автономностью', async ({page}) => {
    const project = makeProject('Парковки');
    const api = await mockApi(page, {projects: [project]});
    await page.goto(`/projects/${project.id}/flow`);

    await page.locator('app-run-panel').getByRole('combobox', {name: 'Автономность'}).selectOption('A1');
    await page.getByRole('button', {name: 'Запустить конвейер'}).click();
    await expect.poll(() => api.requests.find(r => r.url.endsWith('/runs') && r.method === 'POST')?.body).toMatchObject({autonomy: 'A1'});
    await expect(page.locator('app-run-panel')).toContainText('Режим A1');
  });
});
