import {test, expect, devices} from '@playwright/test';
test.use({...devices['Pixel 7']});
test("US-10", async ({page}) => {
  await page.addInitScript((role) => localStorage.setItem('role', role), "ROLE-01");
  await page.goto("/MobileParkingZoneList");
  await expect(page).toHaveURL(new RegExp("/MobileParkingZoneList(?:[/?#]|$)"));
  await expect(page.getByTestId("mobile-parking-zone-list.external-zone-id").first()).toBeVisible();
  await expect(page.getByTestId("mobile-parking-zone-list.display-name").first()).toBeVisible();
  await expect(page.getByTestId("mobile-parking-zone-list.geometry").first()).toBeVisible();
  await expect(page.getByTestId("mobile-parking-zone-list.state").first()).toBeVisible();
  await expect(page.getByTestId("mobile-parking-zone-list.price").first()).toBeVisible();
  await page.getByTestId("mobile-parking-zone-list.row").first().click();
});
