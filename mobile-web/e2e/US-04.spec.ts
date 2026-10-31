import {test, expect, devices} from '@playwright/test';
test.use({...devices['Pixel 7']});
test("@AC-02 US-04", async ({page}) => {
  await page.addInitScript((role) => localStorage.setItem('role', role), "ROLE-01");
  await page.goto("/MobileParkingZoneList");
  await page.getByTestId("mobile-parking-zone-list.row").first().click();
  await expect(page).toHaveURL(new RegExp("/MobileParkingZoneDetail(?:[/?#]|$)"));
  await expect(page.getByTestId("mobile-parking-zone-detail.external-zone-id").first()).toBeVisible();
  await expect(page.getByTestId("mobile-parking-zone-detail.geometry").first()).toBeVisible();
  await expect(page).toHaveURL(new RegExp("/MobileParkingZoneDetail(?:[/?#]|$)"));
  await expect(page.getByTestId("mobile-parking-zone-detail.state").first()).toContainText("in_zone");
  await expect(page.getByTestId("mobile-parking-zone-detail.external-zone-id").first()).toBeVisible();
  await expect(page.getByTestId("mobile-parking-zone-detail.geometry").first()).toBeVisible();
  await expect(page.getByTestId("mobile-parking-zone-detail.row").filter({hasText: "517641"}).first()).toBeVisible();
});
