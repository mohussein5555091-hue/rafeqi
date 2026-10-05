import type { Page } from '@playwright/test';
import { SIGNED_OUT, api, createUser, expect, freshUser, test, waitForContent } from './helpers';

// Warm-up and cool-down sections, cardio days, swapping exercises, and typing numbers instead of tapping + / −.
// Each test that changes data has its own account.
test.use({ storageState: SIGNED_OUT });

type Session = { id: string; kind: string; status: string; day: string; exercises: { exerciseId: string }[] };
const todaySession = async (page: Page): Promise<Session> =>
  (await api(page, '/workouts/week')).sessions.find((s: Session) => s.kind === 'strength' && s.status === 'today');

// ── Typing numbers ──

test('questionnaire: typing 100 into weight saves 100; out of range says why', async ({ page }) => {
  await createUser(page.request, { plan: false });
  await page.goto('/onboarding/about');
  await waitForContent(page);
  const weight = page.getByRole('textbox', { name: 'Weight' });
  await expect(weight).toHaveValue('');
  await expect(weight).toHaveAttribute('placeholder', 'e.g. 80');
  await expect(weight).toHaveAttribute('inputmode', 'decimal'); // the phone's number keyboard, with a decimal point
  await expect(page.getByRole('textbox', { name: 'Age' })).toHaveAttribute('inputmode', 'numeric');

  await weight.fill('20');
  await weight.blur();
  await expect(page.getByRole('alert').filter({ hasText: 'Weight must be between 35 and 250 kg' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Next' })).toBeDisabled();

  await weight.fill('100');
  await page.getByRole('textbox', { name: 'Age' }).fill('31');
  await page.getByRole('textbox', { name: 'Height' }).fill('176');
  await expect(page.getByRole('alert')).toHaveCount(0);
  await page.getByRole('button', { name: 'Next' }).click();
  await expect(page).toHaveURL(/\/onboarding\/goal$/);
  const saved = await api(page, '/onboarding');
  expect(saved.about).toMatchObject({ weightKg: 100, age: 31, heightCm: 176 });
});

test('the + / − buttons still work, and holding one repeats', async ({ page }) => {
  await createUser(page.request, { plan: false });
  await page.goto('/onboarding/about');
  await waitForContent(page);
  const height = page.getByRole('textbox', { name: 'Height' });
  const plus = page.getByRole('button', { name: 'Increase Height' });
  await plus.click(); // from empty: starts at the placeholder value
  await expect(height).toHaveValue('170');
  await plus.click();
  await expect(height).toHaveValue('171');
  const box = await plus.boundingBox();
  await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2);
  await page.mouse.down();
  await page.waitForTimeout(1500); // held: keeps going, faster and faster
  await page.mouse.up();
  expect(Number(await height.inputValue())).toBeGreaterThan(175);
});

test('check-in weight starts empty and accepts a comma', async ({ page }) => {
  await freshUser(page);
  await page.goto('/check-in/body');
  await waitForContent(page);
  const weight = page.getByRole('textbox', { name: /weight/i }).first();
  await expect(weight).toHaveValue('');
  await expect(page.getByRole('button', { name: 'Next' })).toBeDisabled();
  await weight.fill('87,4');
  await expect(page.getByRole('button', { name: 'Next' })).toBeEnabled();
  const waist = page.locator('label', { hasText: 'Waist' }).getByRole('textbox');
  await waist.fill('5');
  await waist.blur();
  await expect(page.getByText('Waist must be between 40 and 200 cm')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Next' })).toBeDisabled();
});

// ── Warm-up, cool-down, cardio ──

test('a session has a warm-up above the exercises and a cool-down after, each with a Done tick', async ({ page }) => {
  await freshUser(page);
  const s = await todaySession(page);
  await page.goto(`/workouts/${s.id}`);
  await waitForContent(page);
  const warm = page.getByTestId('warmup');
  const cool = page.getByTestId('cooldown');
  await expect(warm).toContainText('Warm-up');
  await expect(warm).toContainText('5 min, easy pace');
  await expect(warm).toContainText(/Lighter sets of .+/);
  await expect(warm).toContainText(/40% · 5 reps @ [\d.]+ kg/); // the programs' loading pyramid (Upper/Lower p. 30)
  await expect(cool).toContainText('Cool-down');
  await expect(cool).toContainText(/each side|Hold \d+ s/);
  await expect(cool).toContainText('slow breathing');
  // Order on the page: warm-up, exercises, cool-down.
  const y = async (sel: string) => (await page.locator(sel).first().boundingBox())!.y;
  expect(await y('[data-testid="warmup"]')).toBeLessThan(await y('[data-testid="exercise-row"]'));
  expect(await y('[data-testid="exercise-row"]')).toBeLessThan(await y('[data-testid="cooldown"]'));
  // Every warm-up move and stretch opens its own how-to page.
  await warm.getByRole('link', { name: /^How to do / }).first().click();
  await waitForContent(page);
  await expect(page.getByRole('heading', { name: 'How to do it' })).toBeVisible();
  await expect(page.getByRole('link', { name: /Watch video/ })).toBeVisible();
  await page.goBack();
  await waitForContent(page);
  await warm.getByRole('switch', { name: 'Warm-up done' }).click();
  await cool.getByRole('switch', { name: 'Cool-down done' }).click();
  await expect.poll(async () => (await api(page, `/workouts/${s.id}`)).warmup.done).toBe(true);
  await page.reload();
  await waitForContent(page);
  await expect(page.getByTestId('warmup').getByRole('switch', { name: 'Warm-up done' })).toHaveAttribute('aria-checked', 'true');
  await expect(page.getByTestId('cooldown').getByRole('switch', { name: 'Cool-down done' })).toHaveAttribute('aria-checked', 'true');
});

test('cardio: the week shows cardio days, and cardio is marked done with the minutes', async ({ page }) => {
  await freshUser(page);
  const week = await api(page, '/workouts/week');
  expect(week.sessions.some((s: Session) => s.kind === 'cardio')).toBe(true);
  await page.goto('/workouts');
  await waitForContent(page);
  await expect(page.getByText(/cardio sessions a week/)).toBeVisible();
  await expect(page.getByText(/Every day: about [\d,]+ steps/)).toBeVisible();
  // Saturday (past): cardio after lifting. Mark it done with 20 minutes.
  const sat = week.sessions.find((s: Session) => s.day === 'sat');
  await page.goto(`/workouts/${sat.id}`);
  await waitForContent(page);
  const card = page.getByTestId('cardio');
  await expect(card).toContainText('After lifting');
  await card.getByRole('textbox', { name: 'Minutes done' }).fill('20');
  await card.getByRole('button', { name: 'Mark done' }).click();
  await expect(card).toContainText('Done: 20 min');
  await page.reload();
  await waitForContent(page);
  await expect(page.getByTestId('cardio')).toContainText('Done: 20 min');
});

// ── Swapping an exercise ──

async function openSwap(page: Page, sessionId: string, index = 0) {
  await page.goto(`/workouts/${sessionId}`);
  await waitForContent(page);
  const row = page.getByTestId('exercise-row').nth(index);
  await row.getByRole('button', { name: /^Swap: / }).click();
  return page.getByRole('dialog');
}

test('swap just for today: why → pick → just today; the badge says why', async ({ page }) => {
  await freshUser(page);
  const s = await todaySession(page);
  const sheet = await openSwap(page, s.id);
  await sheet.getByRole('radio', { name: /Machine is busy today/ }).click();
  const options = sheet.getByRole('radiogroup', { name: 'Pick the new exercise' }).getByRole('radio');
  await expect(options.first()).toBeVisible();
  const n = await options.count();
  expect(n).toBeGreaterThanOrEqual(1);
  expect(n).toBeLessThanOrEqual(4);
  await expect(sheet.getByRole('link', { name: /^How to do / }).first()).toBeVisible(); // each with its info button
  await expect(options.first()).toContainText('Find your weight');
  const name = (await options.first().locator('strong').innerText()).trim();
  await options.first().click();
  await sheet.getByRole('radio', { name: 'Just today' }).check({ force: true });
  await sheet.getByRole('button', { name: `Swap to ${name}` }).click();
  await expect(sheet).toHaveCount(0);
  const first = page.getByTestId('exercise-row').first();
  await expect(first).toContainText(name);
  await expect(first).toContainText('Swapped: machine busy');
  await page.reload();
  await waitForContent(page);
  await expect(page.getByTestId('exercise-row').first()).toContainText(name);
});

test('swap from now on, then undo it from the exercise page', async ({ page }) => {
  await freshUser(page);
  const s = await todaySession(page);
  const original = s.exercises[0].exerciseId;
  const sheet = await openSwap(page, s.id);
  await sheet.getByRole('radio', { name: /I can't do this exercise/ }).click();
  const pick = sheet.getByRole('radiogroup', { name: 'Pick the new exercise' }).getByRole('radio').first();
  await expect(pick).toBeVisible();
  const name = (await pick.locator('strong').innerText()).trim();
  await pick.click();
  await sheet.getByRole('radio', { name: 'From now on' }).check({ force: true });
  await sheet.getByRole('button', { name: `Swap to ${name}` }).click();
  await expect(page.getByTestId('exercise-row').first()).toContainText(name);
  const plan = await api(page, '/plan');
  const ids = plan.program.days.flatMap((d: { exercises: { exerciseId: string }[] }) => d.exercises.map((e) => e.exerciseId));
  expect(ids).not.toContain(original);

  await page.getByTestId('exercise-row').first().getByRole('link', { name: /^How to do / }).click();
  await waitForContent(page);
  const mine = page.getByTestId('my-swap');
  await expect(mine).toContainText('from now on');
  await mine.getByRole('button', { name: /^Undo swap/ }).click();
  await expect(page.getByText(/Swap undone/)).toBeVisible();
  const after = (await api(page, '/plan')).program.days.flatMap((d: { exercises: { exerciseId: string }[] }) => d.exercises.map((e) => e.exerciseId));
  expect(after).toContain(original);
});

test('"Equipment not available" leaves that equipment out of the alternatives', async ({ page }) => {
  await freshUser(page);
  const s = await todaySession(page); // Monday: lower body at the gym
  const index = s.exercises.findIndex((e) => e.exerciseId === 'ex_leg_press');
  expect(index).toBeGreaterThanOrEqual(0);
  const sheet = await openSwap(page, s.id, index);
  await sheet.getByRole('radio', { name: /Equipment not available/ }).click();
  await expect(sheet.getByRole('radiogroup', { name: 'Pick the new exercise' })).toBeVisible();
  const alts = await api(page, `/workouts/${s.id}/exercises/ex_leg_press/alternatives?reason=equipment`);
  expect(alts.map((a: { exerciseId: string }) => a.exerciseId)).not.toContain('ex_seated_leg_curl'); // machines are out
});

test('"It causes pain": after the swap it offers to add or update an injury', async ({ page }) => {
  await freshUser(page);
  const s = await todaySession(page);
  const sheet = await openSwap(page, s.id, 1);
  await sheet.getByRole('radio', { name: /It causes pain/ }).click();
  await sheet.getByRole('radiogroup', { name: 'Pick the new exercise' }).getByRole('radio').first().click();
  await sheet.getByRole('button', { name: /^Swap to / }).click();
  await expect(sheet.getByText('Did it hurt?')).toBeVisible();
  await expect(sheet.getByRole('button', { name: 'Update: Left shoulder' })).toBeVisible();
  await sheet.getByRole('button', { name: 'Add an injury' }).click();
  await expect(page).toHaveURL(/\/injuries\/new$/);
});

test('the logger has the warm-up, a Swap button on every exercise, and the cool-down', async ({ page }) => {
  await freshUser(page);
  const s = await todaySession(page);
  await page.goto(`/workouts/${s.id}/log`);
  await waitForContent(page);
  await expect(page.getByTestId('warmup')).toBeVisible();
  await expect(page.getByTestId('cooldown')).toBeVisible();
  const cards = page.getByTestId('log-card');
  await expect(cards.first().getByRole('button', { name: /^Swap: / })).toBeVisible();
  await expect(page.getByRole('button', { name: /^Swap: / })).toHaveCount(await cards.count());
});
