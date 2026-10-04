import { test as setup } from '@playwright/test';
import { AUTH_FILE, TEST_USER, createUser, expect, logIn } from './helpers';

// The test database starts empty every run (scripts/e2e-server.mjs). This creates the shared account that most tests
// read from: questionnaire answered, plan built, and one weekly check-in sent (so there's a weekly review to show).
// Tests that change data make their own account instead (helpers.ts freshUser), so tests never step on each other.
setup('create the shared account, log in once and save the session', async ({ page }) => {
  await createUser(page.request, TEST_USER);
  const { draft } = await (await page.request.get('/api/checkins/draft')).json();
  const checkIn = { ...draft, body: { ...draft.body, weightKg: 87.6, measurementsCm: { waist: 95 } }, note: 'Good week.' };
  expect((await page.request.post('/api/checkins', { data: checkIn })).status()).toBe(201);
  await page.request.post('/api/auth/logout');
  await logIn(page);
  await page.context().storageState({ path: AUTH_FILE });
});
