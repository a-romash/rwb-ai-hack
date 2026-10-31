import {defineConfig, devices} from '@playwright/test';

// In the sandbox and CI the stand is already up: BASE_URL points at it (http://mobile inside the
// stand network) and no dev server starts. Locally, without BASE_URL, Playwright runs ng serve.
const baseURL = process.env['BASE_URL'] ?? 'http://127.0.0.1:4300';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env['CI'],
  retries: process.env['CI'] ? 1 : 0,
  reporter: [['list'], ['json', {outputFile: '../reports/e2e/pwa.json'}]],
  use: {baseURL, permissions: ['geolocation', 'notifications'], geolocation: {latitude: 59.9386, longitude: 30.3141}},
  projects: [{name: 'mobile', use: {...devices['Pixel 7']}}],
  webServer: process.env['BASE_URL']
    ? undefined
    : {command: 'npm start', url: baseURL, reuseExistingServer: !process.env['CI']},
});
