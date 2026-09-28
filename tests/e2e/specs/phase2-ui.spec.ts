import { expect, test } from '@playwright/test';
import { SIGNED_OUT, waitForContent } from './helpers';

test('dashboard: log today\'s weight, with a range check', async ({ page }) => {
  await page.goto('/');
  await waitForContent(page);
  await page.getByRole('button', { name: 'Log today' }).click();
  const field = page.getByLabel('Today\'s weight', { exact: true });
  await field.fill('12');
  await page.getByRole('button', { name: 'Save today\'s weight' }).click();
  await expect(page.getByRole('alert').filter({ hasText: 'between 30 and 300' })).toBeVisible();
  await field.fill('88,1'); // comma decimals are accepted too
  await page.getByRole('button', { name: 'Save today\'s weight' }).click();
  await expect(page.getByText('Today: 88.1 kg')).toBeVisible();
});

test.describe('signed out', () => {
  test.use({ storageState: SIGNED_OUT });
  test('forgot password explains that email reset comes later', async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('link', { name: 'Forgot password?' }).click();
    await expect(page.getByRole('note')).toContainText('coming later');
    await expect(page.getByRole('textbox')).toHaveCount(0);
    await page.locator('button:visible', { hasText: 'عربي' }).first().click();
    await expect(page.getByRole('note')).toContainText('بعدين');
  });
});

test('profile has no metric/imperial setting', async ({ page }) => {
  await page.goto('/profile');
  await waitForContent(page);
  await expect(page.getByText('Language', { exact: true })).toBeVisible();
  await expect(page.getByText(/imperial|metric/i)).toHaveCount(0);
});
