import {expect, test} from '@playwright/test';

test('installable PWA shell', async ({page}) => {
  await page.goto('/');
  await expect(page.locator('link[rel="manifest"]')).toHaveCount(1);
  await expect(page.getByRole('banner')).toBeVisible();
});
