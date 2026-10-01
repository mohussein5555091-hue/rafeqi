import { expect, test } from '@playwright/test';
import { waitForContent } from './helpers';

test('onboarding: answers are saved step by step, survive a reload, resume where you left off, then build the plan', async ({ page }) => {
  await page.goto('/onboarding');
  await expect(page).toHaveURL(/\/onboarding\/about$/);
  await waitForContent(page);

  // Under 18 can't continue.
  const age = page.getByRole('group', { name: 'Age' });
  for (let i = 0; i < 12; i++) await age.getByRole('button', { name: /^Decrease/ }).click();
  await expect(page.getByText('You need to be 18 or older')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Next' })).toBeDisabled();
  for (let i = 0; i < 3; i++) await age.getByRole('button', { name: /^Increase/ }).click(); // 17 → 20
  await page.getByRole('radio', { name: 'Female' }).check({ force: true });
  await page.getByRole('button', { name: 'Next' }).click();

  await expect(page).toHaveURL(/\/onboarding\/goal$/);
  await page.getByRole('radio', { name: /Build muscle/ }).click();
  await page.getByRole('button', { name: 'Next' }).click();
  await expect(page).toHaveURL(/\/onboarding\/training$/);

  // Reload mid-way: the answers are still there, and /onboarding resumes at this step.
  await page.reload();
  await page.goto('/onboarding');
  await expect(page).toHaveURL(/\/onboarding\/training$/);
  await page.getByRole('radio', { name: '3', exact: true }).click(); // days per week
  await page.getByRole('button', { name: 'Next' }).click();
  for (const step of ['injuries', 'health', 'food']) {
    await expect(page).toHaveURL(new RegExp(`/onboarding/${step}$`));
    await page.getByRole('button', { name: 'Next' }).click();
  }

  await expect(page).toHaveURL(/\/onboarding\/review$/);
  await expect(page.getByText(/Female · 20 ·/)).toBeVisible();
  await expect(page.getByText('Build muscle', { exact: false })).toBeVisible();
  await expect(page.getByText(/Intermediate · 3 days/)).toBeVisible();
  await page.getByRole('button', { name: 'Build my plan' }).click();
  await expect(page).toHaveURL(/\/onboarding\/generating$/);
  await expect(page).toHaveURL(/\/plan-ready$/, { timeout: 15_000 });
});
