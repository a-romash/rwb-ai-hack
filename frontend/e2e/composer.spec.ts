import {expect, test} from '@playwright/test';
import {mockApi} from './fixtures';

test.describe('Новый проект', () => {
  test('пустая форма объясняет, чего не хватает', async ({page}) => {
    await mockApi(page);
    await page.goto('/projects/new');

    await page.getByRole('button', {name: 'Создать проект'}).click();
    await expect(page.getByText('Назовите проект: так его будет проще найти.')).toBeVisible();
    await expect(page.getByText('Опишите, что нужно создать. Без требований агентам не с чем работать.')).toBeVisible();
  });

  test('пример из кейса, подсказка полноты и создание проекта', async ({page}) => {
    const api = await mockApi(page);
    await page.goto('/projects/new');

    await page.getByRole('button', {name: 'Пример из кейса'}).click();
    await expect(page.getByLabel('Название')).toHaveValue('Парковочный помощник для технических служб');
    await expect(page.getByText('6 из 6')).toBeVisible();

    await page.getByRole('button', {name: 'Создать проект'}).click();
    await expect(page).toHaveURL(/\/projects\/[^/]+\/flow$/);
    await expect(page.getByText('Проект создан')).toBeVisible();

    const created = api.requests.find(request => request.method === 'POST' && request.url.endsWith('/api/projects'));
    expect(created?.body).toMatchObject({name: 'Парковочный помощник для технических служб'});
    expect((created?.body as {requirements: string}).requirements).toContain('Система должна');
  });

  test('уход с заполненной формы просит подтверждения', async ({page}) => {
    await mockApi(page);
    await page.goto('/projects/new');
    await page.getByLabel('Название').fill('Черновик');

    await page.getByRole('link', {name: 'Отмена'}).click();
    const dialog = page.getByRole('alertdialog');
    await expect(dialog).toContainText('Уйти без сохранения?');
    await dialog.getByRole('button', {name: 'Остаться'}).click();
    await expect(page).toHaveURL(/\/projects\/new$/);
  });
});
