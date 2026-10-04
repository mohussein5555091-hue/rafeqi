import { api, expect, test, waitForContent } from './helpers';

// The targets themselves are computed and tested in the backend (app/progression.py, tests/backend/test_progression.py,
// against data/rules/progression_cases.json). This checks the screen shows exactly what the backend decided.
test('each session shows one exact target per exercise, from the plan engine', async ({ page }) => {
  const week = await api(page, '/workouts/week');
  const s = week.sessions.find((x: { status: string }) => x.status === 'planned');
  await page.goto(`/workouts/${s.id}`);
  await waitForContent(page);
  const rows = page.locator('main ol > li');
  for (const [i, e] of s.exercises.entries()) {
    const t = e.target;
    await expect(rows.nth(i)).toContainText(t.weightKg ? `${t.sets} × ${t.reps} @ ${t.weightKg} kg` : `${t.sets} × ${t.reps}`);
    await expect(rows.nth(i)).toContainText(`Range ${e.reps}`);
    await expect(rows.nth(i)).toContainText('Starting weight'); // no history yet on the shared account
  }
});
