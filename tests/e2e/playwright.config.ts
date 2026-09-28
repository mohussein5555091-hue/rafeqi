import { defineConfig, devices } from '@playwright/test';
import { AUTH_FILE } from './specs/helpers';

// Starts the whole app (backend + frontend) with the root `npm run dev`,
// or reuses it if it's already running.
export default defineConfig({
  testDir: './specs',
  fullyParallel: true,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: { baseURL: 'http://localhost:5173', trace: 'retain-on-failure' },
  webServer: {
    command: 'npm run dev',
    cwd: '../..',
    url: 'http://localhost:5173',
    reuseExistingServer: true,
    timeout: 120_000,
  },
  projects: [
    // Logs in once and saves the session; every other test starts already signed in.
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    { name: 'desktop', use: { ...devices['Desktop Chrome'], storageState: AUTH_FILE }, dependencies: ['setup'] },
    { name: 'mobile', use: { ...devices['Pixel 7'], storageState: AUTH_FILE }, dependencies: ['setup'] },
  ],
});
