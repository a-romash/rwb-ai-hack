import {expect, test} from '@playwright/test';

test('has the app title', async ({page}) => {
  await page.goto('/');
  await expect(page).toHaveTitle('Admin');
});
