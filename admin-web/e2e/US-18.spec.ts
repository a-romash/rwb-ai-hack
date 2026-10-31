import {test, expect, devices} from '@playwright/test';
test("US-18", async ({page}) => {
  await page.addInitScript((role) => localStorage.setItem('role', role), "ROLE-02");
  await page.goto("/AdminDashboard");
  await page.goto("/VehicleList");
  await page.getByTestId("vehicle-list.row").first().click();
  await expect(page).toHaveURL(new RegExp("/VehicleDetail(?:[/?#]|$)"));
  await expect(page.getByTestId("vehicle-detail.route-id").first()).toBeVisible();
  await expect(page.getByTestId("vehicle-detail.current-location").first()).toBeVisible();
  await expect(page.getByTestId("vehicle-detail.status").first()).toBeVisible();
  await expect(page.getByTestId("vehicle-detail.last-position-at").first()).toBeVisible();
});
