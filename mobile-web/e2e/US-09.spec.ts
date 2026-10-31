import {test, expect, devices} from '@playwright/test';
test.use({...devices['Pixel 7']});
test("@AC-07 US-09", async ({page}) => {
  await page.addInitScript((role) => localStorage.setItem('role', role), "ROLE-01");
  await page.goto("/MobileParkingSessionList");
  await page.getByTestId("mobile-parking-session-list.row").first().click();
  await page.getByTestId("mobile-parking-session-detail.get-payment-url").click();
  await expect(page).toHaveURL(new RegExp("/MobileParkingSessionDetail(?:[/?#]|$)"));
});
