import {test, expect, devices} from '@playwright/test';
test("US-12", async ({page}) => {
  await page.addInitScript((role) => localStorage.setItem('role', role), "ROLE-02");
  await page.goto("/GetZoneTariffForm");
  await page.getByTestId("get-zone-tariff-form.zone-id").fill("517641");
  await page.getByTestId("get-zone-tariff-form.submit").click();
  await expect(page).toHaveURL(new RegExp("/ParkingZoneDetail(?:[/?#]|$)"));
  await expect(page.getByTestId("parking-zone-detail.tariff").first()).toBeVisible();
  await expect(page.getByTestId("parking-zone-detail.price").first()).toBeVisible();
  await expect(page.getByTestId("parking-zone-detail.price-description").first()).toBeVisible();
  await expect(page.getByTestId("parking-zone-detail.state").first()).toBeVisible();
});
