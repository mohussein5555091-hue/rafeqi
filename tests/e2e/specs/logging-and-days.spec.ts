import type { Page } from '@playwright/test';
import { SIGNED_OUT, TODAY, api, expect, freshUser, test, waitForContent } from './helpers';

const loaded = (page: Page, sel: string) =>
  expect.poll(() => page.locator(sel).evaluateAll((imgs: HTMLImageElement[]) => imgs.length > 0 && imgs.every((i) => i.complete && i.naturalWidth > 0))).toBe(true);

type Target = { sets: number; reps: number; weightKg: number };
/** "3 × 10 @ 22.5 kg", or "3 × 12" for bodyweight: how the screens write a target or a result. */
const fmt = (r: Target) => (r.weightKg ? `${r.sets} × ${r.reps} @ ${r.weightKg} kg` : `${r.sets} × ${r.reps}`);

test.describe('own account', () => {
  test.use({ storageState: SIGNED_OUT });

  test('logger: one tap per exercise, one row to edit, finish marks the rest as planned, then effort and pain; it\'s saved', async ({ page }) => {
    await freshUser(page);
    const week = await api(page, '/workouts/week');
    const today = week.sessions.find((s: { status: string; kind: string }) => s.kind === 'strength' && s.status === 'today');
    const ex: { exerciseId: string; target: Target }[] = today.exercises;
    const n = ex.length;

    await page.goto(`/workouts/${today.id}/log`);
    await waitForContent(page);
    const cards = page.getByTestId('log-card');
    await expect(cards).toHaveCount(n); // the whole session on one page
    await loaded(page, '[data-testid="log-card"] img');

    const first = cards.nth(0);
    // A new account has no history: every target is the starting weight from the plan engine.
    await expect(first).toContainText(`Target ${fmt(ex[0].target)} · Starting weight`);
    await expect(first.getByRole('link', { name: /^How to do / })).toBeVisible();
    await first.getByRole('button', { name: /^Done as planned/ }).click();
    await expect(first).toContainText(`Done: ${fmt(ex[0].target)}`); // exactly the target

    // Something was different: one row (sets, reps, weight) plus "struggled".
    const second = cards.nth(1);
    await second.getByRole('button', { name: /^Edit / }).click();
    await second.getByLabel('Reps').fill('5');
    await second.getByRole('switch', { name: 'I struggled on the last set' }).click();
    await second.getByRole('button', { name: 'Save' }).click();
    const edited = { ...ex[1].target, reps: 5 };
    await expect(second).toContainText(`Done: ${fmt(edited)} · last set was a struggle`);
    await expect(page.getByText(`2 of ${n} exercises logged`, { exact: true })).toBeVisible();

    // The explanation page opens mid-workout without losing anything.
    await cards.nth(2).getByRole('link', { name: /^How to do / }).click();
    await expect(page).toHaveURL(new RegExp(`/exercises/${ex[2].exerciseId}$`));
    await page.goBack();
    await waitForContent(page);
    await expect(cards.nth(1)).toContainText(`Done: ${fmt(edited)}`);

    await page.getByRole('button', { name: 'Finish workout' }).click();
    await expect(page.getByRole('heading', { name: 'Session done' })).toBeVisible();
    await expect(page.getByText(`${n}/${n}`, { exact: true })).toBeVisible(); // untouched exercises counted as done as planned
    const save = page.getByRole('button', { name: 'Save & finish' });
    await expect(save).toBeDisabled(); // the effort question is required
    await page.getByRole('radiogroup', { name: 'Workout effort from 1 to 10' }).getByRole('radio', { name: '7' }).click();
    await page.getByRole('radiogroup', { name: 'Pain from 0 to 10' }).getByRole('radio', { name: '2' }).click();
    await save.click();

    await expect(page).toHaveURL(new RegExp(`/workouts/${today.id}$`));
    await waitForContent(page);
    const check = async () => {
      await expect(page.getByText('Effort 7/10')).toBeVisible();
      await expect(page.getByText('Left shoulder after: 2/10')).toBeVisible();
      const results = page.getByTestId('logged-result');
      await expect(results).toHaveCount(n);
      await expect(results.nth(0)).toContainText(fmt(ex[0].target));
      await expect(results.nth(1)).toContainText(fmt(edited));
      await expect(results.nth(n - 1)).toContainText(fmt(ex[n - 1].target)); // untouched → its target
      await expect(page.getByRole('link', { name: 'Start workout' })).toHaveCount(0); // done: nothing left to start
    };
    await check();
    await page.reload(); // saved on the server, not just on this page
    await waitForContent(page);
    await check();
    // The pain check is on the injury's pain trend.
    const shoulder = (await api(page, '/injuries'))[0];
    expect(shoulder.painLog).toEqual([{ date: TODAY, pain: 2 }]);
  });

  test('a red flag after a workout pauses the area and shows "see a doctor"', async ({ page }) => {
    await freshUser(page);
    const today = (await api(page, '/workouts/week')).sessions.find((s: { status: string; kind: string }) => s.kind === 'strength' && s.status === 'today');
    await page.goto(`/workouts/${today.id}/log`);
    await waitForContent(page);
    await page.getByRole('button', { name: 'Finish workout' }).click();
    await page.getByRole('radiogroup', { name: 'Workout effort from 1 to 10' }).getByRole('radio', { name: '6' }).click();
    await page.getByRole('radiogroup', { name: 'Pain from 0 to 10' }).getByRole('radio', { name: '3' }).click();
    await page.getByRole('button', { name: 'Swelling', exact: true }).click();
    await page.getByRole('button', { name: 'Save & finish' }).click();
    await expect(page).toHaveURL(/\/injuries\/[\w-]+\/warning$/);
    await expect(page.getByRole('alertdialog')).toContainText('doctor or physiotherapist');
    const shoulder = (await api(page, '/injuries'))[0];
    expect(shoulder.paused).toBe(true);
    expect(shoulder.redFlags.swelling).toBe(true);
  });
});

test('workout week: every day opens its full session, with previous / next arrows', async ({ page, isMobile }) => {
  const week = await api(page, '/workouts/week');
  // Lifting on Sat, Mon, Wed, Thu; cardio on the rest days Tue and Fri (never the day before a leg day).
  expect(week.sessions.map((s: { day: string; kind: string; status: string }) => `${s.day}:${s.kind}:${s.status}`)).toEqual(
    ['sat:strength:missed', 'mon:strength:today', 'tue:cardio:planned', 'wed:strength:planned', 'thu:strength:planned', 'fri:cardio:planned']);
  const [sat, mon, tue, wed, thu, fri] = week.sessions;

  await page.goto('/workouts');
  await waitForContent(page);
  await page.getByRole('link', { name: new RegExp(sat.name.en) }).first().click(); // a past day
  if (!isMobile) await page.getByRole('link', { name: 'Details', exact: true }).click(); // desktop selects it in the side panel first
  await expect(page).toHaveURL(new RegExp(`/workouts/${sat.id}$`));
  await waitForContent(page);

  const rows = page.getByTestId('exercise-row');
  await expect(rows).toHaveCount(sat.exercises.length);
  for (const r of await rows.all()) {
    await expect(r.getByRole('link', { name: /^How to do / })).toHaveAttribute('href', /^\/exercises\/ex_/);
    await expect(r).toContainText(/\d+ × \d+/); // sets × reps
    await expect(r).toContainText(/Rest \d+/);
    await expect(r).toContainText(/RPE \d/);
  }
  await expect(page.getByText('Missed', { exact: true })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Start workout' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Previous workout' })).toBeDisabled();

  await page.getByRole('link', { name: 'Next workout' }).click(); // today
  await expect(page).toHaveURL(new RegExp(`/workouts/${mon.id}$`));
  await expect(page.getByRole('link', { name: 'Start workout' })).toBeVisible();

  await page.getByRole('link', { name: 'Next workout' }).click(); // a cardio day
  await expect(page).toHaveURL(new RegExp(`/workouts/${tue.id}$`));
  await waitForContent(page);
  await expect(page.getByTestId('cardio')).toContainText('You can mark it done on Tuesday.');

  await page.getByRole('link', { name: 'Next workout' }).click(); // a future lifting day
  await expect(page).toHaveURL(new RegExp(`/workouts/${wed.id}$`));
  await waitForContent(page);
  await expect(rows).toHaveCount(wed.exercises.length);
  await expect(page.getByRole('link', { name: 'Start workout' })).toHaveCount(0);
  await expect(page.getByText('You can start this workout on Wednesday.')).toBeVisible();
  await expect(page.getByTestId('logged-result')).toHaveCount(0);

  await page.getByRole('link', { name: 'Next workout' }).click();
  await expect(page).toHaveURL(new RegExp(`/workouts/${thu.id}$`));
  await page.getByRole('link', { name: 'Next workout' }).click();
  await expect(page).toHaveURL(new RegExp(`/workouts/${fri.id}$`));
  await expect(page.getByRole('button', { name: 'Next workout' })).toBeDisabled();
  await page.getByRole('link', { name: 'Previous workout' }).click();
  await expect(page).toHaveURL(new RegExp(`/workouts/${thu.id}$`));
});

test('nutrition week: each day opens that exact date, with previous / next arrows and its own totals', async ({ page }) => {
  await page.goto('/nutrition?view=week');
  await waitForContent(page);
  await expect(page.locator('main ol > li a')).toHaveCount(7);
  await page.getByRole('link', { name: /^Meals for Friday/ }).click();
  await expect(page).toHaveURL(/\/nutrition\/day\/2026-10-09$/);
  await waitForContent(page);

  const friday = await api(page, '/meals/day/2026-10-09');
  const meals = page.getByTestId('meal-card');
  await expect(meals).toHaveCount(friday.meals.length);
  await expect(page.getByText(friday.meals[0].name.en)).toBeVisible();
  for (const m of await meals.all()) {
    await expect(m).toContainText(/\d+ kcal/);
    await expect(m).toContainText(/P\s?\d+/);
    await expect(m.getByRole('button', { name: 'Swap' })).toBeVisible();
  }
  const total = friday.meals.reduce((a: number, m: { kcal: number }) => a + m.kcal, 0);
  await expect(page.getByTestId('daily-total')).toContainText(total.toLocaleString('en-GB'));
  await expect(page.getByRole('button', { name: 'Next day' })).toBeDisabled(); // the week ends on Friday

  await page.getByRole('link', { name: 'Previous day' }).click();
  await expect(page).toHaveURL(/\/nutrition\/day\/2026-10-08$/);
  const thursday = await api(page, '/meals/day/2026-10-08');
  await expect(page.getByText(thursday.meals[0].name.en)).toBeVisible();

  // Each meal links to its recipe page.
  await expect(page.getByRole('link', { name: 'Recipe' }).first()).toHaveAttribute('href', `/nutrition/recipes/${thursday.meals[0].recipeId}`);
  await page.getByRole('link', { name: 'Recipe' }).first().click();
  await expect(page).toHaveURL(new RegExp(`/nutrition/recipes/${thursday.meals[0].recipeId}$`));
  await waitForContent(page);
  await expect(page.getByRole('heading', { name: 'Ingredients' })).toBeVisible();
});
