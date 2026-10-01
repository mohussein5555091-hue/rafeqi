import { expect, test, type Page } from '@playwright/test';
import { waitForContent } from './helpers';

const loaded = (page: Page, sel: string) =>
  expect.poll(() => page.locator(sel).evaluateAll((imgs: HTMLImageElement[]) => imgs.length > 0 && imgs.every((i) => i.complete && i.naturalWidth > 0))).toBe(true);

test('logger: one tap per exercise, one row to edit, finish marks the rest as planned, then effort and pain', async ({ page }) => {
  await page.goto('/workouts/w3_upper_a/log');
  await waitForContent(page);
  const cards = page.getByTestId('log-card');
  await expect(cards).toHaveCount(7); // the whole session on one page
  await loaded(page, '[data-testid="log-card"] img');

  const press = cards.nth(0);
  // One exact target from last time (3 × 9, struggled) and the progression rules: same again.
  await expect(press).toContainText('Target 3 × 9 @ 22.5 kg · Same as last time');
  await expect(press).toContainText('Last time: 3 × 9 @ 22.5 kg · last set was a struggle');
  await expect(press.getByRole('link', { name: /^How to do / })).toBeVisible();
  await press.getByRole('button', { name: /^Done as planned/ }).click();
  await expect(press).toContainText('Done: 3 × 9 @ 22.5 kg'); // exactly the target

  // Something was different: one row (sets, reps, weight) plus "struggled".
  const row = cards.nth(1);
  await expect(row).toContainText('Target 3 × 11 @ 20 kg · +1 rep since last time');
  await row.getByRole('button', { name: /^Edit / }).click();
  await row.getByLabel('Reps').fill('9');
  await row.getByRole('switch', { name: 'I struggled on the last set' }).click();
  await row.getByRole('button', { name: 'Save' }).click();
  await expect(row).toContainText('Done: 3 × 9 @ 20 kg · last set was a struggle');
  await expect(page.getByText('2 of 7 exercises logged', { exact: true })).toBeVisible();

  // The explanation page opens mid-workout without losing anything.
  await cards.nth(2).getByRole('link', { name: /^How to do / }).click();
  await expect(page).toHaveURL(/\/exercises\/ex_landmine_press$/);
  await page.goBack();
  await waitForContent(page);
  await expect(cards.nth(1)).toContainText('Done: 3 × 9 @ 20 kg');

  await page.getByRole('button', { name: 'Finish workout' }).click();
  await expect(page.getByRole('heading', { name: 'Session done' })).toBeVisible();
  await expect(page.getByText('7/7', { exact: true })).toBeVisible(); // untouched exercises counted as done as planned
  const save = page.getByRole('button', { name: 'Save & finish' });
  await expect(save).toBeDisabled(); // the effort question is required
  await page.getByRole('radiogroup', { name: 'Workout effort from 1 to 10' }).getByRole('radio', { name: '7' }).click();
  await page.getByRole('radiogroup', { name: 'Pain from 0 to 10' }).getByRole('radio', { name: '2' }).click();
  await save.click();

  await expect(page).toHaveURL(/\/workouts\/w3_upper_a$/);
  await waitForContent(page);
  await expect(page.getByText('Effort 7/10')).toBeVisible();
  const results = page.getByTestId('logged-result');
  await expect(results).toHaveCount(7);
  await expect(results.nth(0)).toContainText('3 × 9 @ 22.5 kg');
  await expect(results.nth(2)).toContainText('3 × 10 @ 15 kg'); // untouched → its target
  await expect(results.nth(1)).toContainText('3 × 9 @ 20 kg');
  await expect(results.nth(6)).toContainText('2 × 12 @ 10 kg');
  await expect(page.getByRole('link', { name: 'Start workout' })).toHaveCount(0); // done: nothing left to start
});

test('workout week: every day opens its full session, with previous / next arrows', async ({ page, isMobile }) => {
  await page.goto('/workouts');
  await waitForContent(page);
  await page.getByRole('link', { name: /Lower body A/ }).click(); // a past day
  if (!isMobile) await page.getByRole('link', { name: 'Details', exact: true }).click(); // desktop selects it in the side panel first
  await expect(page).toHaveURL(/\/workouts\/w3_lower_a$/);
  await waitForContent(page);

  const rows = page.locator('main ol > li');
  await expect(rows).toHaveCount(5);
  for (const r of await rows.all()) {
    await expect(r.getByRole('link', { name: /^How to do / })).toHaveAttribute('href', /^\/exercises\/ex_/);
    await expect(r).toContainText(/\d+ × [\d–]+.* @ [\d.]+ kg/); // sets × reps @ weight
    await expect(r).toContainText(/Rest \d+/);
    await expect(r).toContainText(/RPE \d/);
  }
  await expect(page.getByText('What you did')).toBeVisible(); // past days show what was logged
  await expect(page.getByTestId('logged-result')).toHaveCount(5);
  await expect(page.getByText('Effort 7/10')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Start workout' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Previous workout' })).toBeDisabled();

  await page.getByRole('link', { name: 'Next workout' }).click(); // today
  await expect(page).toHaveURL(/\/workouts\/w3_upper_a$/);
  await expect(page.getByRole('link', { name: 'Start workout' })).toBeVisible();

  await page.getByRole('link', { name: 'Next workout' }).click(); // a future day
  await expect(page).toHaveURL(/\/workouts\/w3_lower_b$/);
  await waitForContent(page);
  await expect(rows).toHaveCount(5);
  await expect(page.getByRole('link', { name: 'Start workout' })).toHaveCount(0);
  await expect(page.getByText('You can start this workout on Wednesday.')).toBeVisible();
  await expect(page.getByTestId('logged-result')).toHaveCount(0);

  await page.getByRole('link', { name: 'Next workout' }).click();
  await expect(page).toHaveURL(/\/workouts\/w3_upper_b$/);
  await expect(page.getByRole('button', { name: 'Next workout' })).toBeDisabled();
  await page.getByRole('link', { name: 'Previous workout' }).click();
  await expect(page).toHaveURL(/\/workouts\/w3_lower_b$/);
});

test('nutrition week: each day opens that exact date, with previous / next arrows and its own totals', async ({ page }) => {
  await page.goto('/nutrition?view=week');
  await waitForContent(page);
  await expect(page.locator('main ol > li a')).toHaveCount(7);
  await page.getByRole('link', { name: /^Meals for Friday/ }).click();
  await expect(page).toHaveURL(/\/nutrition\/day\/2026-10-02$/);
  await waitForContent(page);

  const meals = page.getByTestId('meal-card');
  await expect(meals).toHaveCount(4);
  await expect(page.getByText('Family lunch: mahshi & grilled chicken')).toBeVisible();
  for (const m of await meals.all()) {
    await expect(m).toContainText(/\d+ kcal/);
    await expect(m).toContainText(/P\s?\d+/);
    await expect(m.getByRole('button', { name: 'Swap' })).toBeVisible();
  }
  await expect(page.getByTestId('daily-total')).toContainText('2,200');
  await expect(page.getByRole('button', { name: 'Next day' })).toBeDisabled(); // last day of the plan

  await page.getByRole('link', { name: 'Previous day' }).click();
  await expect(page).toHaveURL(/\/nutrition\/day\/2026-10-01$/);
  await expect(page.getByText('Macarona with beef mince')).toBeVisible();
  await expect(page.getByTestId('daily-total')).toContainText('2,170');

  // A day with recipes: each one links to its recipe page.
  await page.goto('/nutrition/day/2026-09-28');
  await waitForContent(page);
  await expect(page.getByRole('link', { name: 'Recipe' }).first()).toHaveAttribute('href', '/nutrition/recipes/r_ful_eggs');
  await page.getByRole('link', { name: 'Recipe' }).last().click();
  await expect(page).toHaveURL(/\/nutrition\/recipes\/r_chicken_molokhia$/);
});
