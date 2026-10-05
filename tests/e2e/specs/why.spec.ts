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

type Why = { total: number; backed: number; formulas: number; rules: { total: number; fromBooks: number; formulas: number };
  groups: { id: string; decisions: { ruleKey: string; source: { kind: string } }[] }[] };

/** One card per rule in each section: (section, rule) pairs, with their source kind. */
const units = (why: Why) => why.groups.flatMap((g) => [...new Map(g.decisions.map((d) => [d.ruleKey, d.source.kind])).values()]);

test('every reason in the plan is on the page, with its source or the placeholder badge', async ({ page }) => {
  const reasons = await storedReasons(page);
  const why: Why = await api(page, '/plan/why');
  expect(why.total).toBe(reasons.length);
  await page.goto('/plan/why');
  await waitForContent(page);
  await expect(page.getByRole('heading', { name: 'Why this plan', level: 1 })).toBeVisible();
  await expect(page.getByTestId('backed')).toContainText(
    `${why.rules.fromBooks} of ${why.rules.total} rules from your books · ${why.backed} of ${why.total} decisions`);
  await expect(page.getByTestId('formulas-note')).toContainText('1 of the decisions use a standard formula');
  await expect(page.getByTestId('ai-summary')).toBeVisible(); // the slot for the AI phase's summary

  await expect(page.getByTestId('decision')).toHaveCount(reasons.length);
  const shown = await page.getByTestId('result').allTextContents();
  for (const r of reasons) expect(shown, r.rule).toContain(r.en);
  // One source block per rule card: from your books, standard formula, or "Not yet from a book".
  const kinds = units(why);
  await expect(page.getByTestId('source')).toHaveCount(kinds.length);
  await expect(page.getByTestId('placeholder-badge')).toHaveCount(kinds.filter((k) => k === 'placeholder').length);
  await expect(page.getByTestId('formula-badge')).toHaveCount(kinds.filter((k) => k === 'formula').length);
  await expect(page.getByTestId('book-badge')).toHaveCount(kinds.filter((k) => k === 'book').length);
  // The resting-burn formula: a standard formula with its original source, page and a short quote (not "from your books").
  const bmr = page.locator('[data-rule="nutrition.bmr"]');
  await expect(bmr.getByTestId('formula-badge')).toHaveText('Standard formula');
  await expect(bmr.getByTestId('book')).toContainText('Original source: American Journal of Clinical Nutrition');
  await expect(bmr.getByTestId('book')).toContainText('p. 241–247');
  await expect(bmr.locator('blockquote')).toBeVisible();
  await expect(bmr).toContainText(/Sex: (Male|Female)/);
});

test('repeated decisions are grouped under their rule, folded until opened', async ({ page }) => {
  await page.goto('/plan/why');
  await waitForContent(page);
  const start = page.getByTestId('rule-group').and(page.locator('[data-rule="training.start_load"]'));
  await expect(start).toHaveCount(1);
  await expect(start.getByTestId('source')).toHaveCount(1); // the rule and its source once
  const first = start.getByTestId('decision').first();
  await expect(first).toBeHidden();
  await start.locator('summary').click();
  await expect(first).toBeVisible();
  await expect(start.locator('summary')).toContainText(/\d+ decisions use this rule/);
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
  await expect(page.getByTestId('backed')).toContainText(`${why.rules.fromBooks} من ${why.rules.total} قواعد من كتبك · ${why.backed} من ${why.total} قرار`);
  await expect(page.getByTestId('placeholder-badge').first()).toHaveText('لسه مش من كتاب');
  const reasons = await storedReasons(page);
  const shown = await page.getByTestId('result').allTextContents();
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
