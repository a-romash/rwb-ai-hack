import {expect, test} from '@playwright/test';
import {makeProject, mockApi} from './fixtures';

test.describe('Список проектов', () => {
  test('пустой список приглашает начать и показывает конвейер RWB', async ({page}) => {
    await mockApi(page);
    await page.goto('/projects');

    await expect(page.getByRole('heading', {level: 1, name: 'Проекты'})).toBeVisible();
    await expect(page.getByRole('heading', {level: 2, name: 'Проектов пока нет'})).toBeVisible();
    await expect(page.locator('app-pipeline-chain li')).toHaveCount(8);
    await page.getByRole('link', {name: 'Создать проект'}).click();
    await expect(page).toHaveURL(/\/projects\/new$/);
  });

  test('таблица проектов, поиск и пустой результат поиска', async ({page}) => {
    await mockApi(page, {projects: [makeProject('Парковочный помощник'), makeProject('Заявки на закупку')]});
    await page.goto('/projects');

    const rows = page.locator('a.project');
    await expect(rows).toHaveCount(2);
    await expect(page.getByText('2 проекта')).toBeVisible();

    await page.getByRole('searchbox', {name: 'Найти проект по названию'}).fill('парков');
    await expect(rows).toHaveCount(1);
    await expect(rows.first()).toContainText('Парковочный помощник');

    await page.getByRole('searchbox', {name: 'Найти проект по названию'}).fill('нет такого');
    await expect(page.getByText('Нет проектов с «нет такого» в названии.')).toBeVisible();
    await page.getByRole('button', {name: 'Сбросить поиск'}).click();
    await expect(rows).toHaveCount(2);
  });

  test('ошибка загрузки объясняет, что делать, и даёт повторить', async ({page}) => {
    await mockApi(page, {failList: true});
    await page.goto('/projects');

    const alert = page.getByRole('alert');
    await expect(alert).toContainText('Сервис временно недоступен');
    await expect(alert).toContainText('docker compose');
    await expect(alert.getByRole('button', {name: 'Повторить'})).toBeVisible();
  });
});
