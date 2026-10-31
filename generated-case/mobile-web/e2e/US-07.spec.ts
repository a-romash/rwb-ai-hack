import {test, expect, devices} from '@playwright/test';
test.use({...devices['Pixel 7']});
test("@AC-09 US-07", async ({page}) => {
  await page.addInitScript((role) => localStorage.setItem('role', role), "ROLE-01");
  await page.goto("/MobileParkingSessionList");
  await page.getByTestId("mobile-parking-session-list.row").first().click();
  await expect(page).toHaveURL(new RegExp("/MobileParkingSessionDetail(?:[/?#]|$)"));
  await expect(page.getByTestId("mobile-parking-session-detail.planned-end-at").first()).toBeVisible();
  await expect(page.getByTestId("mobile-parking-session-detail.ends-at").first()).toBeVisible();
  await expect(page.getByTestId("mobile-parking-session-detail.state").first()).toBeVisible();
  await expect(page.getByTestId("mobile-parking-session-detail.row").filter({hasText: "ВЭН-001"}).first()).toBeVisible();
});
