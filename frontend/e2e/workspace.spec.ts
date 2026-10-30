import {expect, test} from '@playwright/test';
import {makeProject, mockApi} from './fixtures';

test.describe('Рабочая область проекта', () => {
  test('конвейер RWB: шаги Э1–Э7 с воротами, выбор мышью и стрелками', async ({page, isMobile}) => {
    const project = makeProject('Парковочный помощник');
    await mockApi(page, {projects: [project]});
    await page.goto(`/projects/${project.id}/flow`);

    const panel = page.locator('#station-panel');
    await expect(panel.getByRole('heading', {level: 2, name: 'Анализ требований'})).toBeVisible();

    // 8 шагов и 7 ворот: G0, G1, G1.5, G2, G3, G4, G5
    const rows = page.locator('app-pipeline-timeline [data-key]');
    await expect(rows).toHaveCount(15);

    await page.locator('[data-key="develop"]').click();
    await expect(panel.getByRole('heading', {level: 2, name: 'Разработка'})).toBeVisible();
    await expect(panel).toContainText('Как это сделать?');

    if (!isMobile) {
      await page.locator('[data-key="develop"]').focus();
      await page.keyboard.press('ArrowDown');
      await expect(panel.getByRole('heading', {level: 2, name: 'Проверки и стенд'})).toBeVisible();
      await page.keyboard.press('ArrowDown');
      await expect(panel.getByRole('heading', {level: 2, name: 'Сборка и проверки'})).toBeVisible();
      await expect(page.locator('[data-key="gate:G3"]')).toBeFocused();
    }

    await page.locator('[data-key="verify"]').click();
    await expect(panel).toContainText('Агент не подключён');
    await panel.getByRole('button', {name: /G4/}).click();
    await expect(panel.getByRole('heading', {level: 2, name: 'Стенд'})).toBeVisible();
    await expect(panel).toContainText('Health, smoke и E2E');
  });

  test('запуск аналитика: инструкция этапа, опрос статуса и результат', async ({page}) => {
    const project = makeProject('Заявки на закупку', 'Руководитель согласует заявки больше 100 000 ₽.');
    const api = await mockApi(page, {
      projects: [project],
      jobSteps: [
        {status: 'pending'},
        {status: 'started'},
        {status: 'success', subtype: 'success', result: '{"summary":"Роли: сотрудник, руководитель. Неоднозначно: что такое «большая сумма»."}', num_turns: 2},
      ],
    });
    await page.goto(`/projects/${project.id}/flow`);

    await page.locator('#station-panel').getByRole('button', {name: 'Запустить аналитика'}).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog.getByRole('heading', {name: 'Запуск агента'})).toBeVisible();
    await expect(dialog.getByLabel('Инструкция')).toHaveValue(/Проведи бизнес-анализ/);
    await dialog.getByRole('button', {name: 'Запустить аналитика'}).click();

    await expect(page.getByText('Аналитик запущен')).toBeVisible();
    const created = api.requests.find(request => request.method === 'POST' && request.url.endsWith('/jobs'));
    expect(created?.body).toMatchObject({agent: 'analyst'});
    expect((created?.body as {prompt: string}).prompt).toContain('Руководитель согласует заявки');

    await page.getByRole('link', {name: /Запуски/}).click();
    const card = page.locator('app-job-card').first();
    await expect(card).toContainText('Готово', {timeout: 15_000});
    await expect(card).toContainText('Неоднозначно: что такое «большая сумма».');
    await expect(card).toContainText('Шагов');

    await page.getByRole('link', {name: 'Конвейер', exact: true}).click();
    await expect(page.locator('[data-key="analysis"]')).toHaveAttribute('data-tone', 'ok');
  });

  test('ошибка агента показывается как ошибка, а не как успех задачи', async ({page}) => {
    const project = makeProject('Без ключа модели');
    await mockApi(page, {
      projects: [project],
      jobSteps: [{status: 'success', subtype: 'error', result: 'OPENROUTER_API_KEY is not set', num_turns: 1}],
    });
    await page.goto(`/projects/${project.id}/runs`);

    await page.locator('app-runs-tab').getByRole('button', {name: 'Запустить аналитика'}).click();
    await page.getByRole('dialog').getByRole('button', {name: 'Запустить аналитика'}).click();

    const card = page.locator('app-job-card').first();
    await expect(card).toContainText('Ошибка агента', {timeout: 15_000});
    await expect(card).toContainText('OPENROUTER_API_KEY is not set');
    await expect(card).toHaveAttribute('data-tone', 'fail');
  });

  test('требования: правка, сохранение и защита от потери изменений', async ({page}) => {
    const project = makeProject('Склад', 'Кладовщик принимает товар.');
    const api = await mockApi(page, {projects: [project]});
    await page.goto(`/projects/${project.id}/requirements`);

    const editor = page.getByRole('textbox', {name: 'Требования проекта'});
    await expect(editor).toHaveValue('Кладовщик принимает товар.');
    await editor.fill('Кладовщик принимает товар и сканирует штрихкод.');
    await expect(page.getByText('Есть несохранённые изменения')).toBeVisible();

    await page.getByRole('link', {name: 'Конвейер', exact: true}).click();
    await expect(page.getByRole('alertdialog')).toContainText('Уйти без сохранения?');
    await page.getByRole('alertdialog').getByRole('button', {name: 'Остаться'}).click();

    await page.getByRole('button', {name: 'Сохранить требования'}).click();
    await expect(page.getByText('Требования сохранены')).toBeVisible();
    const patch = api.requests.find(request => request.method === 'PATCH');
    expect(patch?.body).toEqual({requirements: 'Кладовщик принимает товар и сканирует штрихкод.'});
    await expect(page.getByText('Есть несохранённые изменения')).toHaveCount(0);
  });

  test('переименование проекта', async ({page}) => {
    const project = makeProject('Старое название');
    await mockApi(page, {projects: [project]});
    await page.goto(`/projects/${project.id}/flow`);

    await page.getByRole('button', {name: 'Переименовать'}).click();
    const input = page.getByLabel('Название проекта');
    await input.fill('Новое название');
    await input.press('Enter');
    await expect(page.getByRole('heading', {level: 1, name: 'Новое название'})).toBeVisible();
    await expect(page.getByText('Проект переименован')).toBeVisible();
  });

  test('несуществующий проект: понятная ошибка и путь назад', async ({page}) => {
    await mockApi(page);
    await page.goto('/projects/00000000-0000-0000-0000-000000000000/flow');
    const alert = page.getByRole('alert');
    await expect(alert).toContainText('Проект не найден');
    await alert.getByRole('link', {name: 'К проектам'}).click();
    await expect(page).toHaveURL(/\/projects$/);
  });
});
