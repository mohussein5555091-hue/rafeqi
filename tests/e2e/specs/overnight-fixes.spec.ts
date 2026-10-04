import type { Locator, Page } from '@playwright/test';
import { api, expect, freshUser, test, waitForContent } from './helpers';

// Bugs found while testing by hand (docs/OVERNIGHT-REPORT.md, priority 1). Read-only: the shared account.

test('the Workouts header shows the real program name', async ({ page }) => {
  await page.goto('/workouts');
  await waitForContent(page);
  await expect(page.getByText('Upper / Lower (sample) · week')).toBeVisible();
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
  await expect(page.getByTestId('today-why')).toContainText('Monday already has Lower body A');
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
