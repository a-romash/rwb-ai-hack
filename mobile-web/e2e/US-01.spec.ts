import {test, expect, devices} from '@playwright/test';
test.use({...devices['Pixel 7']});
test("US-01", async ({page}) => {
  await page.addInitScript((role) => localStorage.setItem('role', role), "ROLE-01");
  await page.goto("/MobileParkingZoneList");
  await expect(page).toHaveURL(new RegExp("/MobileParkingZoneList(?:[/?#]|$)"));
  await expect(page.getByTestId("mobile-parking-zone-list.state").first()).toContainText("active");
  await expect(page.getByTestId("mobile-parking-zone-list.row").filter({hasText: "517641"}).first()).toBeVisible();
  await page.getByTestId("mobile-parking-zone-list.row").first().click();
  await expect(page).toHaveURL(new RegExp("/MobileParkingZoneDetail(?:[/?#]|$)"));
  await expect(page.getByTestId("mobile-parking-zone-detail.state").first()).toContainText("active");
  await expect(page.getByTestId("mobile-parking-zone-detail.external-zone-id").first()).toBeVisible();
  await expect(page.getByTestId("mobile-parking-zone-detail.display-name").first()).toBeVisible();
  await expect(page.getByTestId("mobile-parking-zone-detail.state").first()).toBeVisible();
});
