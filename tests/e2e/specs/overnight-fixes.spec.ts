import { api, expect, test, waitForContent } from './helpers';

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
