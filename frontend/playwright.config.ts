import path from 'node:path';
import { defineConfig, devices } from '@playwright/test';

const backendHost = process.env.E2E_BACKEND_HOST ?? '127.0.0.1';
const backendPort = process.env.E2E_BACKEND_PORT ?? '8000';
const frontendPort = process.env.E2E_FRONTEND_PORT ?? '5173';
const backendUrl = `http://${backendHost}:${backendPort}`;
const frontendUrl = `http://127.0.0.1:${frontendPort}`;
const reuseExisting = !process.env.CI && process.env.E2E_REUSE_SERVERS === 'true';
const repoRoot = path.resolve(import.meta.dirname, '..');

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.spec.ts',
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  timeout: 30_000,
  expect: { timeout: 7_500 },
  grepInvert: process.env.E2E_INCLUDE_LIVE === 'true' ? undefined : /@live/,
  reporter: [
    [process.env.CI ? 'line' : 'list'],
    ['html', { outputFolder: 'e2e-artifacts/html-report', open: 'never' }],
  ],
  outputDir: 'e2e-artifacts/test-results',
  use: {
    baseURL: frontendUrl,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      name: 'isolated-fastapi',
      command: 'node frontend/e2e/support/start-server.mjs backend',
      cwd: repoRoot,
      url: `${backendUrl}/api/health`,
      reuseExistingServer: reuseExisting,
      timeout: 60_000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
    {
      name: 'vite',
      command: 'node frontend/e2e/support/start-server.mjs frontend',
      cwd: repoRoot,
      url: frontendUrl,
      reuseExistingServer: reuseExisting,
      timeout: 60_000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
  ],
});
