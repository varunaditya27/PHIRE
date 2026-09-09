import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30 * 1000,
  expect: {
    timeout: 5000,
  },
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    // Base URL for the app – will be set via env variable when running.
    baseURL: process.env.PHIRE_FRONTEND_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
