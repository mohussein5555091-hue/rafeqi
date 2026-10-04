import type { Locator, Page } from '@playwright/test';
import { api, expect, test, waitForContent } from './helpers';

const loaded = (img: Locator) => expect.poll(() => img.evaluate((i: HTMLImageElement) => i.complete && i.naturalWidth > 0)).toBe(true);
const card = (page: Page, heading: string) => page.locator('div', { has: page.getByRole('heading', { name: heading, exact: true }) }).last();

/** This week's lifting sessions (from the API) and their exercises (the week also has cardio days). */
async function sessions(page: Page): Promise<{ id: string; exercises: { exerciseId: string }[] }[]> {
  return (await api(page, '/workouts/week')).sessions.filter((s: { kind: string }) => s.kind === 'strength');
}

test('each exercise in every session has a thumbnail and an info button', async ({ page }) => {
  for (const s of await sessions(page)) {
    await page.goto(`/workouts/${s.id}`);
    await waitForContent(page);
    const rows = page.getByTestId('exercise-row');
    await expect(rows, s.id).toHaveCount(s.exercises.length);
    for (const row of await rows.all()) {
      await loaded(row.locator('img').first());
      await expect(row.getByRole('link', { name: /^How to do / })).toBeVisible();
    }
  }
});

test('tapping an exercise opens a full explanation', async ({ page }) => {
  const week = await sessions(page);
  await page.goto(`/workouts/${week[0].id}`);
  await waitForContent(page);
  await page.getByTestId('exercise-row').first().getByRole('link').first().click();
  await expect(page).toHaveURL(new RegExp(`/exercises/${week[0].exercises[0].exerciseId}$`));

  const ids = new Set(week.flatMap((s) => s.exercises.map((e) => e.exerciseId)));
  for (const id of ids) {
    await page.goto(`/exercises/${id}`);
    await waitForContent(page);
    await loaded(page.locator('main figure img').first());
    const video = page.getByRole('link', { name: /Watch video/ });
    await expect(video).toHaveAttribute('target', '_blank');
    await expect(video).toHaveAttribute('href', /^https:\/\/www\.youtube\.com\/results\?search_query=.+proper\+form$/);
    await expect(page.locator('main figure + p')).not.toBeEmpty(); // one-line description
    expect(await page.locator('section', { has: page.getByRole('heading', { name: 'How to do it' }) }).locator('ol > li').count(), id).toBeGreaterThanOrEqual(3);
    const cues = await card(page, 'Form cues').locator('span').count();
    expect(cues, `${id} cues`).toBeGreaterThanOrEqual(3);
    expect(cues, `${id} cues`).toBeLessThanOrEqual(5);
    expect(await card(page, 'Common mistakes').locator('span').count(), id).toBeGreaterThanOrEqual(2);
    await expect(page.getByRole('heading', { name: 'Muscles worked' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Alternatives' })).toBeVisible();
    await expect(page.getByText('Free Exercise DB')).toBeVisible();
  }
});

test('an exercise swapped for the injury says so on its page', async ({ page }) => {
  const plan = await api(page, '/plan');
  const swapped = plan.program.days.flatMap((d: { exercises: { swapKind: string; injuryId: string; exerciseId: string }[] }) => d.exercises)
    .find((e: { swapKind: string; injuryId: string }) => e.swapKind === 'swapped' && e.injuryId);
  await page.goto(`/exercises/${swapped.exerciseId}`);
  await waitForContent(page);
  await expect(page.getByText('Swapped for your left shoulder').first()).toBeVisible();
});
