import {test, expect, devices} from '@playwright/test';
test.use({...devices['Pixel 7']});
test("@AC-01 US-05", async ({page}) => {
  await page.addInitScript((role) => localStorage.setItem('role', role), "ROLE-01");
  await page.goto("/MobileParkingZoneList");
  await page.getByTestId("mobile-parking-zone-list.row").first().click();
  await expect(page).toHaveURL(new RegExp("/MobileParkingZoneDetail(?:[/?#]|$)"));
  await expect(page.getByTestId("mobile-parking-zone-detail.price-description").first()).toBeVisible();
  await expect(page.getByTestId("mobile-parking-zone-detail.tariff").first()).toBeVisible();
});
