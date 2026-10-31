import {test, expect, devices} from '@playwright/test';
test("US-20", async ({page}) => {
  await page.addInitScript((role) => localStorage.setItem('role', role), "ROLE-02");
  await page.goto("/AdminDashboard");
  await expect(page).toHaveURL(new RegExp("/AdminDashboard(?:[/?#]|$)"));
});
