import { expect, test } from '@playwright/test';
import { SIGNED_OUT, logIn } from './helpers';

test.use({ storageState: SIGNED_OUT });

test('a signed-out visitor lands on Log in', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByLabel('Email')).toBeVisible();
});

test('the API is reachable through the frontend proxy', async ({ request }) => {
  const res = await request.get('/api/health');
  expect(res.ok()).toBeTruthy();
  expect((await res.json()).status).toBe('ok');
});

test('Arabic switches the page to right-to-left', async ({ page }) => {
  await page.goto('/login');
  await page.getByRole('button', { name: /العربية|Arabic/ }).first().click();
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
});

test('every other page requires login', async ({ page }) => {
  await page.goto('/groceries');
  await expect(page).toHaveURL(/\/login$/);
});

test('log in and reach the dashboard', async ({ page }) => {
  await logIn(page);
});
