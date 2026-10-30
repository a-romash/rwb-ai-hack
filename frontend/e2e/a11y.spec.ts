import AxeBuilder from '@axe-core/playwright';
import {expect, Page, test} from '@playwright/test';
import {makeProject, mockApi} from './fixtures';

async function expectNoSeriousViolations(page: Page) {
  const results = await new AxeBuilder({page}).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
  const serious = results.violations.filter(violation => violation.impact === 'serious' || violation.impact === 'critical');
  expect(serious.map(violation => `${violation.id}: ${violation.nodes.map(node => node.target.join(' ')).join(', ')}`)).toEqual([]);
}

for (const theme of ['light', 'dark'] as const) {
  test.describe(`Доступность, ${theme === 'light' ? 'светлая' : 'тёмная'} тема`, () => {
    test.beforeEach(async ({page}) => {
      await page.addInitScript(value => localStorage.setItem('tuiDark', value), String(theme === 'dark'));
    });

    test('список проектов', async ({page}) => {
      await mockApi(page, {projects: [makeProject('Парковочный помощник')]});
      await page.goto('/projects');
      await expect(page.locator('a.project')).toHaveCount(1);
      await expectNoSeriousViolations(page);
    });

    test('новый проект', async ({page}) => {
      await mockApi(page);
      await page.goto('/projects/new');
      await expect(page.getByRole('heading', {level: 1, name: 'Новый проект'})).toBeVisible();
      await expectNoSeriousViolations(page);
    });

    test('линия потока', async ({page}) => {
      const project = makeProject('Парковочный помощник');
      await mockApi(page, {projects: [project]});
      await page.goto(`/projects/${project.id}/flow`);
      await expect(page.locator('#station-panel')).toBeVisible();
      await page.waitForTimeout(1500); // линия дорисовывается — проверяем финальное состояние
      await expectNoSeriousViolations(page);
    });
  });
}
