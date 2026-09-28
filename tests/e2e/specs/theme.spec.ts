import { expect, test } from '@playwright/test';
import { SIGNED_OUT } from './helpers';

test.use({ storageState: SIGNED_OUT });
const html = (page: import('@playwright/test').Page) => page.locator('html');

test.describe('device in dark mode', () => {
  test.use({ colorScheme: 'dark' });
  test('defaults to the device setting', async ({ page }) => {
    await page.goto('/login');
    await expect(html(page)).toHaveClass(/\bdark\b/);
  });
});

test.describe('device in light mode', () => {
  test.use({ colorScheme: 'light' });
  test('defaults to the device setting', async ({ page }) => {
    await page.goto('/login');
    await expect(html(page)).not.toHaveClass(/\bdark\b/);
  });

  test('toggle switches the theme and remembers it after reload', async ({ page }) => {
    await page.goto('/login');
    const toggle = page.locator('[data-testid="theme-toggle"]:visible');
    await toggle.click();
    await expect(html(page)).toHaveClass(/\bdark\b/);
    await expect(toggle).toHaveAttribute('aria-pressed', 'true');
    await page.reload();
    await expect(html(page)).toHaveClass(/\bdark\b/);
    await page.goto('/signup');
    await expect(html(page)).toHaveClass(/\bdark\b/);
    await page.locator('[data-testid="theme-toggle"]:visible').click();
    await expect(html(page)).not.toHaveClass(/\bdark\b/);
  });
});
