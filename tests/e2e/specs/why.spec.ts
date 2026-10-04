import type { Page } from '@playwright/test';
import { api, expect, test, waitForContent } from './helpers';

// "Why this plan": every reason the plan engine stored with the plan is on the page, each with its source or the
// "Not yet from a book" badge. Uses the shared read-only account (intermediate, left shoulder injury).

type Reason = { rule: string; en: string; ar: string };
type PlanOut = { reasons: Record<string, Reason[]>; program: { days: { reasons: Reason[]; exercises: { reasons: Reason[] }[] }[] } };

async function storedReasons(page: Page): Promise<Reason[]> {
  const plan: PlanOut = await api(page, '/plan');
  return [
    ...Object.values(plan.reasons).flat(),
    ...plan.program.days.flatMap((d) => [...d.reasons, ...d.exercises.flatMap((e) => e.reasons)]),
  ];
}

test('every reason in the plan is on the page, with its source or the placeholder badge', async ({ page }) => {
  const reasons = await storedReasons(page);
  const why = await api(page, '/plan/why');
  expect(why.total).toBe(reasons.length);
  await page.goto('/plan/why');
  await waitForContent(page);
  await expect(page.getByRole('heading', { name: 'Why this plan', level: 1 })).toBeVisible();
  await expect(page.getByTestId('backed')).toContainText(`${why.backed} of ${why.total} decisions backed by your books`);
  await expect(page.getByTestId('ai-summary')).toBeVisible(); // the slot for the AI phase's summary

  const cards = page.getByTestId('decision');
  await expect(cards).toHaveCount(reasons.length);
  const shown = await page.getByTestId('result').allInnerTexts();
  for (const r of reasons) expect(shown, r.rule).toContain(r.en);
  // Every card: the answers used (or "Not from your answers"), the rule, and a source or the badge.
  for (const card of await cards.all()) {
    await expect(card).toContainText('Your answers used');
    await expect(card).toContainText('The rule');
    const badge = await card.getByTestId('placeholder-badge').count();
    const book = await card.getByTestId('book').count();
    expect(badge + book, await card.getAttribute('data-rule') ?? '').toBe(1);
  }
  await expect(page.getByTestId('placeholder-badge')).toHaveCount(why.total - why.backed);
  // The one rule from a published source: book, page and a short quote.
  const bmr = page.locator('[data-rule="nutrition.bmr"]');
  await expect(bmr.getByTestId('book')).toContainText('Clinical Nutrition');
  await expect(bmr.getByTestId('book')).toContainText('p. 241–247');
  await expect(bmr.locator('blockquote')).toBeVisible();
  await expect(bmr).toContainText(/Sex: (Male|Female)/);
});

test('every kind of decision has its section, and the injury swap names the injury', async ({ page }) => {
  await page.goto('/plan/why');
  await waitForContent(page);
  for (const name of ['Calories', 'Protein', 'Carbs and fat', 'Program choice', 'Days and session length', 'Sets, reps and effort (RPE)',
    'Starting weights', 'Progression', 'Lighter weeks (deload)', 'Warm-up', 'Cool-down', 'Cardio', 'Exercise swaps and exclusions',
    'Meal choices and portions']) {
    await expect(page.getByRole('heading', { name, level: 2 }), name).toBeVisible();
  }
  const injury = page.locator('[data-rule="training.injuries"]').first();
  await expect(injury).toContainText('Injuries: Left shoulder');
  // The jump links go to their section.
  await page.getByRole('navigation', { name: 'Jump to' }).getByRole('link', { name: /^Meal choices and portions/ }).click();
  await expect(page).toHaveURL(/#why-meals$/);
});

test('in Arabic too', async ({ page }) => {
  const why = await api(page, '/plan/why');
  await page.goto('/plan/why');
  await waitForContent(page);
  await page.locator('button:visible', { hasText: 'عربي' }).first().click();
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
  await expect(page.getByTestId('backed')).toContainText(`${why.backed} من ${why.total} قرار مدعومين من كتبك`);
  await expect(page.getByTestId('placeholder-badge').first()).toHaveText('لسه مش من كتاب');
  const reasons = await storedReasons(page);
  const shown = await page.getByTestId('result').allInnerTexts();
  for (const r of reasons) expect(shown, r.rule).toContain(r.ar);
});

test('linked from "Your plan is ready", the dashboard and Profile', async ({ page }) => {
  for (const from of ['/plan-ready', '/', '/profile']) {
    await page.goto(from);
    await waitForContent(page);
    await page.getByTestId('why-link').click();
    await expect(page, from).toHaveURL(/\/plan\/why$/);
  }
});
