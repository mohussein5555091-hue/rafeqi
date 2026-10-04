import { defineConfig, devices } from '@playwright/test';
import { AUTH_FILE } from './specs/helpers';

// Starts its own copy of the app (backend + frontend) on ports 8001/5174 with a fresh, seeded
// test database in tests/e2e/.data/ (see scripts/e2e-server.mjs). Your `npm run dev` on 5173
// and data/rafeqi.db are never touched, and both can run at the same time.
const WEB = 'http://localhost:5174';

export default defineConfig({
  testDir: './specs',
  fullyParallel: true,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  // PW_CHROMIUM_PATH: use an already-installed Chromium instead of Playwright's own download (e.g. a cloud machine).
  use: { baseURL: WEB, trace: 'retain-on-failure', launchOptions: process.env.PW_CHROMIUM_PATH ? { executablePath: process.env.PW_CHROMIUM_PATH } : {} },
  webServer: {
    command: 'node scripts/e2e-server.mjs',
    cwd: '../..',
    url: WEB,
    // Always start fresh, so every run gets a new empty database.
    reuseExistingServer: false,
    timeout: 180_000,
  },
  projects: [
    // Logs in once and saves the session; every other test starts already signed in.
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    { name: 'desktop', use: { ...devices['Desktop Chrome'], storageState: AUTH_FILE }, dependencies: ['setup'] },
    { name: 'mobile', use: { ...devices['Pixel 7'], storageState: AUTH_FILE }, dependencies: ['setup'] },
  ],
});
