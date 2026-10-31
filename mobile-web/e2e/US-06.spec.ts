import {test, expect, devices} from '@playwright/test';
test.use({...devices['Pixel 7']});
test("@AC-09 US-06", async ({page}) => {
  await page.addInitScript((role) => localStorage.setItem('role', role), "ROLE-01");
  await page.goto("/MobileParkingSessionList");
  await page.getByTestId("mobile-parking-session-list.nav-MobileParkingSessionForm").click();
  await page.getByTestId("mobile-parking-session-form.zone-id").fill("517641");
  await page.getByTestId("mobile-parking-session-form.started-at").fill("e2e-value");
  await page.getByTestId("mobile-parking-session-form.ends-at").fill("e2e-value");
  await page.getByTestId("mobile-parking-session-form.state").fill("{'values': ['active', 'expired', 'cancelled']}");
  await page.getByTestId("mobile-parking-session-form.planned-end-at").fill("e2e-value");
  await page.getByTestId("mobile-parking-session-form.create").click();
  await expect(page).toHaveURL(new RegExp("/MobileParkingSessionDetail(?:[/?#]|$)"));
  await expect(page.getByTestId("mobile-parking-session-detail.status").first()).toContainText("active");
  await expect(page.getByTestId("mobile-parking-session-detail.ends-at").first()).toBeVisible();
});
