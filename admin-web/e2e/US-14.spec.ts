import {test, expect, devices} from '@playwright/test';
test("US-14", async ({page}) => {
  await page.addInitScript((role) => localStorage.setItem('role', role), "ROLE-02");
  await page.goto("/AdminDashboard");
  await expect(page).toHaveURL(new RegExp("/AdminDashboard(?:[/?#]|$)"));
  await expect(page.getByTestId("admin-dashboard.total-vehicles").first()).toBeVisible();
  await expect(page.getByTestId("admin-dashboard.total-zones").first()).toBeVisible();
  await expect(page.getByTestId("admin-dashboard.total-events").first()).toBeVisible();
});
