import { readFileSync } from 'node:fs';
import { SIGNED_OUT, TODAY, api, expect, freshUser, logIn, test, waitForContent } from './helpers';

// Phase 5: the screens run on the real backend. Each test here changes data, so each makes its own account.
test.use({ storageState: SIGNED_OUT });

test('data persists: log out, log back in, and everything is still there', async ({ page }) => {
  const user = await freshUser(page);
  await page.goto('/groceries');
  await waitForContent(page);
  const first = page.locator('main li').first();
  const name = (await first.locator('span.text-\\[14\\.5px\\]').innerText()).split(' · ')[0];
  await first.getByRole('checkbox').click();
  await expect(first.getByRole('checkbox')).toHaveAttribute('aria-checked', 'true');

  await page.goto('/profile');
  await page.getByRole('button', { name: 'Log out' }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.goto('/groceries');
  await expect(page).toHaveURL(/\/login$/); // logged out for real: the cookie is gone

  await page.goto('/signup'); // (Log in would otherwise take you back to /groceries, where you were heading)
  await logIn(page, user);
  await page.goto('/groceries');
  await waitForContent(page);
  const again = page.locator('main li', { hasText: name }).first();
  await expect(again.getByRole('checkbox')).toHaveAttribute('aria-checked', 'true');
});

test('an ended session goes back to Log in', async ({ page, context }) => {
  await freshUser(page);
  await context.clearCookies();
  await page.goto('/workouts');
  await expect(page).toHaveURL(/\/login$/);
});

test('Arabic end to end: the backend\'s text is in Arabic, right to left, and the choice is saved to the account', async ({ page, browser }) => {
  const user = await freshUser(page);
  const meals = await api(page, '/meals/day/today');
  await page.locator('button:visible', { hasText: 'عربي' }).first().click();
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await expect(page.getByText('صباح الخير يا Omar')).toBeVisible();
  await expect(page.getByText(meals.meals[0].name.ar)).toBeVisible(); // meal names come from the backend in both languages
  await page.goto('/workouts');
  await waitForContent(page);
  const week = await api(page, '/workouts/week');
  await expect(page.getByText(week.sessions[1].name.ar).first()).toBeVisible();
  await expect.poll(async () => (await api(page, '/me')).language).toBe('ar');

  // Another device: logging in brings Arabic back.
  const other = await browser.newContext({ storageState: SIGNED_OUT });
  const p2 = await other.newPage();
  await logIn(p2, user);
  await expect(p2.locator('html')).toHaveAttribute('dir', 'rtl');
  await other.close();
});

test('swap a meal: the day stays on target and the grocery list follows', async ({ page }) => {
  await freshUser(page);
  const day = await api(page, '/meals/day/today');
  let pick: { mealIndex: number; option: { recipeId: string; name: { en: string } } } | undefined;
  for (const [i, m] of day.meals.entries()) {
    const options = await api(page, `/meals/${m.id}/swap-options`);
    if (options.length) { pick = { mealIndex: i, option: options[0] }; break; }
  }
  expect(pick, 'a meal today with a swap option').toBeTruthy();
  await page.goto(`/nutrition/day/${TODAY}`);
  await waitForContent(page);
  await page.getByTestId('meal-card').nth(pick!.mealIndex).getByRole('button', { name: 'Swap' }).click();
  const sheet = page.getByRole('dialog');
  await sheet.getByRole('radio', { name: new RegExp(pick!.option.name.en) }).click();
  await sheet.getByRole('button', { name: `Swap to ${pick!.option.name.en}` }).click();
  await expect(sheet).toHaveCount(0);
  await expect(page.getByTestId('meal-card').nth(pick!.mealIndex)).toContainText(pick!.option.name.en);
  await page.reload();
  await waitForContent(page);
  await expect(page.getByTestId('meal-card').nth(pick!.mealIndex)).toContainText(pick!.option.name.en);
  await page.goto('/groceries');
  await waitForContent(page);
  await expect(page.getByText(`you swapped`, { exact: false })).toBeVisible();
});

test('groceries: "I already have this" moves an item off the list to buy, and stays after a reload', async ({ page }) => {
  await freshUser(page);
  await page.goto('/groceries');
  await waitForContent(page);
  const toBuy = page.locator('main').getByText(/^\d+$/).first(); // the "to buy" count
  const before = Number(await toBuy.innerText());
  await page.getByRole('switch', { name: 'I already have this' }).first().click();
  await expect(toBuy).toHaveText(String(before - 1));
  await page.reload();
  await waitForContent(page);
  await expect(toBuy).toHaveText(String(before - 1));
  await expect(page.getByRole('switch', { name: 'I already have this' }).first()).toHaveAttribute('aria-checked', 'true');
});

test('add an injury: it\'s saved and the plan is rebuilt around it', async ({ page }) => {
  await freshUser(page);
  const before = (await api(page, '/plan')).id;
  await page.goto('/injuries/new');
  await waitForContent(page);
  await page.getByLabel('Area').selectOption('kneeR');
  await page.getByRole('button', { name: 'Squat', exact: true }).click();
  await page.getByRole('button', { name: 'Save changes' }).click();
  await expect(page).toHaveURL(/\/injuries\/[\w-]+$/);
  await waitForContent(page);
  await expect(page.getByRole('heading', { name: 'Right knee' })).toBeVisible();
  expect((await api(page, '/plan')).id).not.toBe(before);
  const used = (await api(page, '/workouts/week')).sessions.flatMap((s: { exercises: { exerciseId: string }[] }) => s.exercises.map((e) => e.exerciseId));
  expect(used).not.toContain('ex_bb_back_squat');
});

test('weekly check-in: six short steps, then the review with the engine\'s changes', async ({ page }) => {
  await freshUser(page);
  await page.goto('/check-in/body');
  await waitForContent(page);
  for (const step of ['training', 'injuries', 'nutrition', 'life', 'note']) {
    await page.getByRole('button', { name: 'Next' }).click();
    await expect(page).toHaveURL(new RegExp(`/check-in/${step}$`));
  }
  await page.getByLabel(/Anything else/).fill('Long week at work.');
  await page.getByRole('button', { name: 'Submit check-in' }).click();
  await expect(page).toHaveURL(/\/reviews\/[\w-]+/);
  await expect(page.getByRole('heading', { name: 'Week 1 review' })).toBeVisible({ timeout: 15_000 });
  await waitForContent(page);
  const reviews = await api(page, '/reviews');
  expect(reviews).toHaveLength(1);
  await expect(page.getByText(reviews[0].summary.en)).toBeVisible();
  // The check-in is done for this week.
  expect((await api(page, '/checkins/next')).due).toBe(false);
});

test.describe('designed states', () => {
  test('loading: skeletons while the data is on its way', async ({ page }) => {
    await freshUser(page);
    await page.route('**/api/workouts/week', async (route) => { await new Promise((r) => setTimeout(r, 1500)); await route.continue(); });
    await page.goto('/workouts');
    await expect(page.locator('[aria-busy="true"]').first()).toBeVisible();
    await waitForContent(page);
    await expect(page.getByText('0 of 4 done')).toBeVisible();
  });

  test('error: "Something didn\'t load", and Try again recovers', async ({ page }) => {
    await freshUser(page);
    let fail = true;
    await page.route('**/api/groceries', (route) => (fail ? route.fulfill({ status: 500, body: '{}' }) : route.continue()));
    await page.goto('/groceries');
    await expect(page.getByText('Something didn\'t load')).toBeVisible();
    fail = false;
    await page.getByRole('button', { name: 'Try again' }).click();
    await waitForContent(page);
    await expect(page.getByRole('switch', { name: 'I already have this' }).first()).toBeVisible();
  });

  test('not found: an id that isn\'t yours (or doesn\'t exist)', async ({ page }) => {
    await freshUser(page);
    await page.goto('/injuries/00000000-0000-0000-0000-000000000000');
    await expect(page.getByText('We couldn\'t find that')).toBeVisible();
  });

  test('empty: no reviews yet, nothing in the pantry', async ({ page }) => {
    await freshUser(page);
    await page.goto('/reviews');
    await expect(page.getByText('No reviews yet')).toBeVisible();
    await page.goto('/groceries/pantry');
    await expect(page.getByText('No staples saved yet')).toBeVisible();
  });
});

test('installable: the web app manifest and its icons', async ({ page, request }) => {
  await page.goto('/login');
  await expect(page.locator('link[rel="manifest"]')).toHaveAttribute('href', '/manifest.webmanifest');
  const manifest = await (await request.get('/manifest.webmanifest')).json();
  expect(manifest).toMatchObject({ short_name: 'Rafeqi', display: 'standalone', start_url: '/' });
  for (const icon of manifest.icons) {
    const res = await request.get(icon.src);
    expect(res.ok(), icon.src).toBeTruthy();
    expect(res.headers()['content-type']).toContain('image/png');
  }
  const purposes = manifest.icons.map((i: { purpose: string }) => i.purpose);
  expect(purposes).toEqual(expect.arrayContaining(['any', 'maskable']));
  expect(manifest.icons.map((i: { sizes: string }) => i.sizes)).toEqual(expect.arrayContaining(['192x192', '512x512']));
  expect((await request.get('/icons/apple-touch-icon.png')).ok()).toBeTruthy();
  // No prices in the manifest either.
  expect(readFileSync(new URL('../../../frontend/public/manifest.webmanifest', import.meta.url), 'utf8')).not.toMatch(/price|cost|budget/i);
});
