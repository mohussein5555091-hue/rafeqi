import type { Locator, Page } from '@playwright/test';
import { api, createUser, expect, freshUser, test, waitForContent } from './helpers';

// Bugs found while testing by hand (docs/OVERNIGHT-REPORT.md, priority 1). Read-only: the shared account.

test('the Workouts header shows the real program name', async ({ page }) => {
  await page.goto('/workouts');
  await waitForContent(page);
  await expect(page.getByText('Fundamentals: Upper / Lower · week')).toBeVisible();
});

test('a past session has no Swap button and says it can\'t be changed', async ({ page }) => {
  const week = await api(page, '/workouts/week');
  const sat = week.sessions.find((s: { day: string; kind: string }) => s.day === 'sat' && s.kind === 'strength')!;
  expect(sat.status).not.toBe('today');
  await page.goto(`/workouts/${sat.id}`);
  await waitForContent(page);
  await expect(page.getByTestId('exercise-row').first()).toBeVisible();
  await expect(page.getByRole('button', { name: /^Swap/ })).toHaveCount(0);
  await expect(page.getByTestId('past-locked')).toHaveText("Past sessions can't be changed.");
});

test('missing equipment can be changed in Profile & settings, and the plan follows', async ({ page }) => {
  await freshUser(page);
  await page.goto('/profile');
  await waitForContent(page);
  await expect(page.getByRole('link', { name: /Equipment.*All available/ })).toBeVisible();
  await page.getByRole('link', { name: /Equipment/ }).click();
  await expect(page).toHaveURL(/\/profile\/equipment$/);
  await waitForContent(page);
  await page.getByRole('checkbox', { name: 'Machine', exact: true }).click();
  await page.getByRole('button', { name: 'Save' }).click();
  await expect(page).toHaveURL(/\/profile$/);
  await expect(page.getByRole('link', { name: /Equipment.*1 missing/ })).toBeVisible();
  const plan = await api(page, '/plan');
  const ids = plan.program.days.flatMap((d: { exercises: { exerciseId: string }[] }) => d.exercises.map((e) => e.exerciseId));
  expect(ids).not.toContain('ex_leg_press');
});

/** True when the whole photo shows inside its box (object-fit: contain, nothing outside the visible frame). */
async function wholePhoto(img: Locator) {
  await img.scrollIntoViewIfNeeded(); // thumbnails load lazily
  await expect.poll(() => img.evaluate((i: HTMLImageElement) => i.complete && i.naturalWidth > 0)).toBe(true);
  return img.evaluate((i: HTMLImageElement) => {
    const box = i.getBoundingClientRect();
    const frame = (i.closest('figure') ?? i.parentElement!).getBoundingClientRect();
    const scale = Math.min(box.width / i.naturalWidth, box.height / i.naturalHeight);
    const w = i.naturalWidth * scale, h = i.naturalHeight * scale;
    const left = box.left + (box.width - w) / 2, top = box.top + (box.height - h) / 2;
    return getComputedStyle(i).objectFit === 'contain'
      && left >= frame.left - 0.5 && top >= frame.top - 0.5 && left + w <= frame.right + 0.5 && top + h <= frame.bottom + 0.5;
  });
}

async function everyPhotoWhole(page: Page) {
  const imgs = await page.locator('main img').all();
  expect(imgs.length).toBeGreaterThan(0);
  for (const img of imgs) expect(await wholePhoto(img), await img.getAttribute('src') ?? '').toBe(true);
}

test('every exercise photo is whole: session (warm-up, exercises, cool-down), logger, swap sheet, alternatives', async ({ page }) => {
  await freshUser(page);
  const week = await api(page, '/workouts/week');
  const today = week.sessions.find((s: { status: string; kind: string }) => s.status === 'today' && s.kind === 'strength');
  await page.goto(`/workouts/${today.id}`);
  await waitForContent(page);
  await everyPhotoWhole(page);
  await page.goto(`/workouts/${today.id}/log`);
  await waitForContent(page);
  await everyPhotoWhole(page);
  await page.getByRole('button', { name: /^Swap:/ }).first().click();
  const sheet = page.getByRole('dialog');
  await sheet.getByRole('radio', { name: /Machine is busy today/ }).click();
  await expect(sheet.getByRole('radiogroup', { name: 'Pick the new exercise' }).getByRole('radio').first()).toBeVisible();
  for (const img of await sheet.locator('img').all()) expect(await wholePhoto(img)).toBe(true);
  for (const id of ['ex_face_pull', 'ex_leg_press', 'ex_seated_leg_curl']) {
    await page.goto(`/exercises/${id}`);
    await waitForContent(page);
    await everyPhotoWhole(page);
  }
});

test('alternatives: the band pull-apart has its photo; equipment alternatives name the equipment', async ({ page }) => {
  await page.goto('/exercises/ex_face_pull');
  await waitForContent(page);
  const band = page.getByTestId('alternative').filter({ hasText: 'Band pull-apart' });
  await expect(band.locator('img')).toHaveAttribute('src', '/exercises/Band_Pull_Apart/0.jpg');
  await page.goto('/exercises/ex_leg_press');
  await waitForContent(page);
  await expect(page.getByTestId('alternative').filter({ hasText: 'Goblet squat' })).toContainText('Different equipment: dumbbells');
  await page.goto('/exercises/ex_lateral_raise');
  await waitForContent(page);
  await expect(page.getByTestId('alternative').filter({ hasText: 'Cable lateral raise' })).toContainText('Different equipment: cable machine');
  await expect(page.getByText('Other equipment')).toHaveCount(0);
});

test('move an upcoming session: today is taken (says why), another day works and the week follows', async ({ page }) => {
  await freshUser(page);
  const week = await api(page, '/workouts/week');
  const wed = week.sessions.find((s: { day: string; kind: string }) => s.day === 'wed' && s.kind === 'strength');
  await page.goto(`/workouts/${wed.id}`);
  await waitForContent(page);
  await expect(page.getByRole('button', { name: 'Do this workout today' })).toBeDisabled();
  await expect(page.getByTestId('today-why')).toContainText('Monday already has Upper body 1');
  await page.getByRole('button', { name: 'Move to another day' }).click();
  const sheet = page.getByRole('dialog');
  await expect(sheet.getByTestId('move-option').filter({ hasText: 'Thursday' })).toBeDisabled();
  await sheet.getByTestId('move-option').filter({ hasText: 'Tuesday' }).click();
  await expect(sheet).toHaveCount(0);
  await expect(page.getByTestId('moved-from')).toHaveText('Moved from Wednesday');
  const after = await api(page, '/workouts/week');
  expect(after.sessions.find((s: { id: string }) => s.id === wed.id).day).toBe('tue');
  await page.getByRole('button', { name: 'Back to Wednesday' }).click();
  await expect(page.getByTestId('moved-from')).toHaveCount(0);
});

test('log each set: one row per set, prefilled; the result and "last time" show every set', async ({ page }) => {
  await freshUser(page);
  const week = await api(page, '/workouts/week');
  const today = week.sessions.find((s: { status: string; kind: string }) => s.status === 'today' && s.kind === 'strength');
  const ex = today.exercises.find((e: { target: { weightKg: number } }) => e.target.weightKg > 0);
  const kg: number = ex.target.weightKg;
  await page.goto(`/workouts/${today.id}/log`);
  await waitForContent(page);
  const card = page.getByTestId('log-card').filter({ has: page.locator(`a[href="/exercises/${ex.exerciseId}"]`) }).first();
  await card.getByRole('button', { name: /^Edit / }).click();
  await card.getByRole('switch', { name: 'Log each set' }).click();
  const rows = card.getByTestId('set-rows').locator('li').filter({ hasText: /^Set / });
  await expect(rows).toHaveCount(ex.target.sets);
  await expect(card.getByLabel('Set 1: Reps')).toHaveValue(String(ex.target.reps));
  const lighter = String(kg - ex.weightStepKg);
  await card.getByLabel(`Set ${ex.target.sets}: Weight, kg`).fill(lighter);
  await card.getByRole('button', { name: 'Save' }).click();
  await expect(card).toContainText(`${ex.target.reps} × ${lighter} kg`);
  // Saved set by set on the server.
  await page.getByRole('button', { name: 'Finish workout' }).click();
  await page.getByRole('radiogroup', { name: 'Workout effort from 1 to 10' }).getByRole('radio', { name: '7', exact: true }).click();
  await page.getByRole('button', { name: 'Save & finish' }).click();
  await expect(page).toHaveURL(new RegExp(`/workouts/${today.id}$`));
  const done = (await api(page, '/workouts/week')).sessions.find((s: { id: string }) => s.id === today.id);
  expect(done.log.results[ex.exerciseId].perSet.at(-1)).toEqual({ reps: ex.target.reps, weightKg: Number(lighter) });
});

// A tiny real JPEG (1×1 pixel), so the browser can read it and the server accepts it as a photo.
const JPEG_1PX = Buffer.from('/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=', 'base64');

test('weekly check-in: the questions come from the questions file, and a progress photo is stored privately', async ({ page }) => {
  await freshUser(page);
  const questions = await api(page, '/checkins/questions');
  const weight = questions.questions.find((q: { id: string }) => q.id === 'weight_kg');
  await page.goto('/check-in/body');
  await waitForContent(page);
  await expect(page.getByText(weight.text.en).first()).toBeVisible();
  await page.getByRole('textbox', { name: weight.text.en }).fill('87.5');
  await page.getByTestId('photo-front').setInputFiles({ name: 'front.jpg', mimeType: 'image/jpeg', buffer: JPEG_1PX });
  await expect(page.getByText('Added')).toBeVisible();
  for (const step of ['training', 'injuries', 'nutrition', 'life', 'note']) {
    await page.getByRole('button', { name: 'Next' }).click();
    await expect(page).toHaveURL(new RegExp(`/check-in/${step}$`));
  }
  await page.getByRole('button', { name: 'Submit check-in' }).click();
  await expect(page).toHaveURL(/\/reviews\/[\w-]+/);
  await expect.poll(async () => (await api(page, '/progress')).photos.length).toBe(1);
  const [photo] = (await api(page, '/progress')).photos;
  expect(photo.view).toBe('front');
  await page.goto('/progress');
  await waitForContent(page);
  await expect(page.getByTestId('single-photo').locator('img')).toHaveAttribute('src', photo.url); // one photo shows on its own
  const mine = await page.request.get(photo.url);
  expect(mine.status()).toBe(200);
  expect(mine.headers()['cache-control']).toBe('private, no-store');
  // Someone else (a new account in a fresh browser context) can't see it.
  const other = await page.context().browser()!.newContext({ baseURL: 'http://localhost:5174' });
  await createUser(other.request, { plan: false });
  expect((await other.request.get(photo.url)).status()).toBe(404);
  await other.close();
});
