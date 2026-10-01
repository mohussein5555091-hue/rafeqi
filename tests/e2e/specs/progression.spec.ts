import { readFileSync } from 'node:fs';
import { expect, test } from '@playwright/test';
import { nextTarget } from '../../../frontend/src/mocks/progression';

// The sample-data stand-in must give the same targets as the backend (backend/app/progression.py):
// both are checked against the same worked examples.
const { cases } = JSON.parse(readFileSync(new URL('../../../data/rules/progression_cases.json', import.meta.url), 'utf8'));

test('sample-data targets follow the same progression rules as the backend', () => {
  for (const c of cases) expect(nextTarget(c.sets, c.reps, c.step, c.start, c.last), c.name).toEqual(c.target);
});

test('each session shows one exact target per exercise', async ({ page }) => {
  await page.goto('/workouts/w3_lower_b');
  const squat = page.locator('main ol > li').first();
  await expect(squat).toContainText('3 × 8 @ 10 kg');
  await expect(squat).toContainText('Range 8–10 each');
  await expect(squat).toContainText('Starting weight');
  await expect(page.locator('main ol > li').nth(1)).toContainText('3 × 11 @ 20 kg'); // last time 3 × 10 → +1 rep
});
