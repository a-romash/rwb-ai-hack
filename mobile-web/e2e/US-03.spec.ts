import {test, expect, devices} from '@playwright/test';
test.use({...devices['Pixel 7']});
test("US-03", async ({page}) => {
  await page.addInitScript((role) => localStorage.setItem('role', role), "ROLE-01");
  await page.goto("/MobileParkingZoneList");
  await page.getByTestId("mobile-parking-zone-list.row").first().click();
  await page.getByTestId("mobile-parking-zone-detail.nav-MobileGetCurrentZoneForm").click();
  await page.getByTestId("mobile-get-current-zone-form.vehicle-id").fill("ВЭН-001");
  await page.getByTestId("mobile-get-current-zone-form.submit").click();
  await expect(page).toHaveURL(new RegExp("/MobileParkingZoneDetail(?:[/?#]|$)"));
  await expect(page.getByTestId("mobile-parking-zone-detail.state").first()).toContainText("in_zone");
});
