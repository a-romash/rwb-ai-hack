import {defineConfig, devices} from '@playwright/test';

const PORT = 4310;

/**
 * E2E-сценарии Студии. API подменяется в каждом тесте (e2e/fixtures.ts),
 * поэтому тесты не зависят от бэкенда и идут в CI без Docker.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: {timeout: 7_000},
  fullyParallel: true,
  forbidOnly: Boolean(process.env['CI']),
  retries: process.env['CI'] ? 1 : 0,
  reporter: [['list'], ['html', {open: 'never'}]],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    locale: 'ru-RU',
    timezoneId: 'Europe/Moscow',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: `npx ng serve --port ${PORT} --host 127.0.0.1`,
    url: `http://127.0.0.1:${PORT}`,
    reuseExistingServer: !process.env['CI'],
    timeout: 180_000,
  },
  projects: [
    {name: 'desktop', use: {...devices['Desktop Chrome'], viewport: {width: 1440, height: 900}}},
    {name: 'mobile', use: {...devices['Pixel 7']}},
  ],
});
