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
