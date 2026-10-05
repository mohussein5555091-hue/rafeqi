import type { Locator, Page } from '@playwright/test';
import { api, expect, test, waitForContent } from './helpers';

const loaded = (img: Locator) => expect.poll(() => img.evaluate((i: HTMLImageElement) => i.complete && i.naturalWidth > 0)).toBe(true);
/** The Free Exercise DB has no photo for these: the app shows its placeholder (data/REVIEW.md, Part B2). */
const NO_PHOTO = new Set(['ex_cable_kickback', 'ex_single_leg_lying_curl', 'ex_lat_pull_in', 'ex_machine_lateral_raise', 'ex_single_leg_press',
  'ex_smith_reverse_lunge', 'ex_cable_hip_abduction', 'ex_sliding_leg_curl', 'ex_band_pulldown', 'ex_db_leg_curl']);
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
    for (const [i, row] of (await rows.all()).entries()) {
      if (NO_PHOTO.has(s.exercises[i].exerciseId)) await expect(row.locator('img')).toHaveCount(0);
      else await loaded(row.locator('img').first());
      await expect(row.getByRole('link', { name: /^How to do / })).toBeVisible();
    }
  }
});

test('tapping an exercise opens a full explanation', async ({ page }) => {
  test.setTimeout(90_000); // it opens every exercise of the week (about 18 with the real program)
  const week = await sessions(page);
  await page.goto(`/workouts/${week[0].id}`);
  await waitForContent(page);
  await page.getByTestId('exercise-row').first().getByRole('link').first().click();
  await expect(page).toHaveURL(new RegExp(`/exercises/${week[0].exercises[0].exerciseId}$`));

  const ids = new Set(week.flatMap((s) => s.exercises.map((e) => e.exerciseId)));
  for (const id of ids) {
    await page.goto(`/exercises/${id}`);
    await waitForContent(page);
    if (NO_PHOTO.has(id)) await expect(page.getByText('Demonstration coming soon')).toBeVisible();
    else await loaded(page.locator('main figure img').first());
    const video = page.getByRole('link', { name: /Watch video/ });
    await expect(video).toHaveAttribute('target', '_blank');
    // The program book's demo video when it prints one (Fundamentals pp. 88–91), a YouTube search otherwise.
    await expect(video).toHaveAttribute('href', /^https:\/\/(www\.youtube\.com\/(watch\?v=[\w-]+|results\?search_query=.+proper\+form$)|youtu\.be\/[\w-]+)/);
    const media = NO_PHOTO.has(id) ? 'main [aria-label="Exercise demonstration"]' : 'main figure';
    await expect(page.locator(`${media} + p`)).not.toBeEmpty(); // one-line description
    expect(await page.locator('section', { has: page.getByRole('heading', { name: 'How to do it' }) }).locator('ol > li').count(), id).toBeGreaterThanOrEqual(3);
    const cues = await card(page, 'Form cues').locator('span').count();
    expect(cues, `${id} cues`).toBeGreaterThanOrEqual(3);
    expect(cues, `${id} cues`).toBeLessThanOrEqual(5);
    expect(await card(page, 'Common mistakes').locator('span').count(), id).toBeGreaterThanOrEqual(2);
    await expect(page.getByRole('heading', { name: 'Muscles worked' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Alternatives' })).toBeVisible();
    if (!NO_PHOTO.has(id)) await expect(page.getByText('Free Exercise DB')).toBeVisible(); // the photo's source
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

/** Where the photo actually shows inside its <img> box with object-fit: contain, compared with the box around it. */
async function photoFit(img: Locator) {
  return img.evaluate((i: HTMLImageElement) => {
    const box = i.getBoundingClientRect();
    const frame = (i.closest('figure') ?? i.parentElement!).getBoundingClientRect();
    const scale = Math.min(box.width / i.naturalWidth, box.height / i.naturalHeight);
    const w = i.naturalWidth * scale, h = i.naturalHeight * scale;
    const left = box.left + (box.width - w) / 2, top = box.top + (box.height - h) / 2;
    return {
      fit: getComputedStyle(i).objectFit,
      inside: left >= frame.left - 0.5 && top >= frame.top - 0.5 && left + w <= frame.right + 0.5 && top + h <= frame.bottom + 0.5,
      onScreen: left >= -0.5 && left + w <= window.innerWidth + 0.5,
      ratio: w / h, natural: i.naturalWidth / i.naturalHeight, share: (w * h) / (frame.width * frame.height),
    };
  });
}

test('exercise photos are shown whole: nothing cut off, original proportions', async ({ page }) => {
  await page.goto('/exercises/ex_band_pull_apart');
  await waitForContent(page);
  const photo = page.locator('main figure img').first();
  await loaded(photo);
  const fit = await photoFit(photo);
  expect(fit.fit).toBe('contain');
  expect(fit.inside && fit.onScreen).toBe(true);
  expect(fit.ratio).toBeCloseTo(fit.natural, 2);
  expect(fit.share, 'the box follows the photo, so it is mostly photo').toBeGreaterThan(0.6);
  await page.screenshot({ path: test.info().outputPath('band-pull-apart.png'), fullPage: true });

  // Its alternative, Arm circles: a thumbnail, the right label, and a link to its own page.
  const alt = page.getByTestId('alternative').filter({ hasText: 'Arm circles' });
  await expect(alt).toContainText('No equipment needed');
  await expect(alt).not.toContainText('Other equipment');
  const thumb = alt.locator('img');
  await loaded(thumb);
  expect((await photoFit(thumb)).fit).toBe('contain');
  expect((await photoFit(thumb)).inside).toBe(true);
  await alt.click();
  await expect(page).toHaveURL(/\/exercises\/ex_arm_circles$/);
  await waitForContent(page);
  await loaded(page.locator('main figure img').first());
  expect((await photoFit(page.locator('main figure img').first())).inside).toBe(true);
});

test('session thumbnails show the whole photo too', async ({ page }) => {
  const [s] = await sessions(page);
  await page.goto(`/workouts/${s.id}`);
  await waitForContent(page);
  for (const img of await page.getByTestId('exercise-row').locator('img').all()) {
    await loaded(img);
    const fit = await photoFit(img);
    expect(fit.fit).toBe('contain');
    expect(fit.inside).toBe(true);
  }
});
