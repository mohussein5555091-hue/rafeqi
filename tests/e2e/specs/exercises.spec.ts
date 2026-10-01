import { expect, test, type Locator, type Page } from '@playwright/test';
import { waitForContent } from './helpers';

const loaded = (img: Locator) => expect.poll(() => img.evaluate((i: HTMLImageElement) => i.complete && i.naturalWidth > 0)).toBe(true);
const card = (page: Page, heading: string) => page.locator('div', { has: page.getByRole('heading', { name: heading, exact: true }) }).last();

/** The sample week's sessions and how many exercises each has. */
const SESSIONS = { w3_lower_a: 5, w3_upper_a: 7, w3_lower_b: 5, w3_upper_b: 7 };

test('each exercise in every session has a thumbnail and an info button', async ({ page }) => {
  for (const [id, n] of Object.entries(SESSIONS)) {
    await page.goto(`/workouts/${id}`);
    await waitForContent(page);
    const rows = page.locator('main ol > li');
    await expect(rows, id).toHaveCount(n);
    for (const row of await rows.all()) {
      await loaded(row.locator('img').first());
      await expect(row.getByRole('link', { name: /^How to do / })).toBeVisible();
    }
  }
});

test('tapping an exercise opens a full explanation', async ({ page }) => {
  await page.goto('/workouts/w3_upper_a');
  await waitForContent(page);
  await page.locator('main ol > li').first().getByRole('link').first().click();
  await expect(page).toHaveURL(/\/exercises\/ex_db_floor_press$/);

  const ids = new Set<string>();
  for (const id of Object.keys(SESSIONS)) {
    await page.goto(`/workouts/${id}`);
    await waitForContent(page);
    const hrefs = await page.locator('main ol > li a[aria-label^="How to do"]').evaluateAll((as) => as.map((a) => a.getAttribute('href')!));
    hrefs.forEach((h) => ids.add(h));
  }
  expect(ids.size).toBe(14); // every exercise in the sample week

  for (const href of ids) {
    await page.goto(href);
    await waitForContent(page);
    await loaded(page.locator('main figure img').first());
    const video = page.getByRole('link', { name: /Watch video/ });
    await expect(video).toHaveAttribute('target', '_blank');
    await expect(video).toHaveAttribute('href', /^https:\/\/www\.youtube\.com\/results\?search_query=.+proper\+form$/);
    await expect(page.locator('main figure + p')).not.toBeEmpty(); // one-line description
    expect(await page.locator('section', { has: page.getByRole('heading', { name: 'How to do it' }) }).locator('ol > li').count(), href).toBeGreaterThanOrEqual(3);
    const cues = await card(page, 'Form cues').locator('span').count();
    expect(cues, `${href} cues`).toBeGreaterThanOrEqual(3);
    expect(cues, `${href} cues`).toBeLessThanOrEqual(5);
    expect(await card(page, 'Common mistakes').locator('span').count(), href).toBeGreaterThanOrEqual(2);
    await expect(page.getByRole('heading', { name: 'Muscles worked' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Alternatives' })).toBeVisible();
    await expect(page.getByText('Free Exercise DB')).toBeVisible();
  }
});
