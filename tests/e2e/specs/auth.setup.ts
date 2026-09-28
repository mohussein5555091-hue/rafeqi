import { test as setup } from '@playwright/test';
import { AUTH_FILE, logIn } from './helpers';

setup('log in once and save the session', async ({ page }) => {
  await logIn(page);
  await page.context().storageState({ path: AUTH_FILE });
});
