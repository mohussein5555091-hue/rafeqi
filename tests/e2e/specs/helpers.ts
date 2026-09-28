import { expect, type Page } from '@playwright/test';

export const AUTH_FILE = '.auth/user.json';
/** For tests that must start signed out. */
export const SIGNED_OUT = { cookies: [], origins: [] };

// Phase 1: the frontend runs on sample data, so any email + 8-character password works.
// Phase 2 replaces this with a real test account.
export const TEST_USER = { email: 'omar@example.com', password: 'password1' };

export async function logIn(page: Page) {
  await page.goto('/login');
  await page.getByLabel('Email').fill(TEST_USER.email);
  await page.getByLabel('Password', { exact: true }).fill(TEST_USER.password);
  await page.getByRole('button', { name: 'Log in' }).click();
  await expect(page).toHaveURL(/\/$/);
}

/** Waits until no loading skeleton is left on the page. */
export async function waitForContent(page: Page) {
  await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
}

export const PUBLIC_ROUTES = ['/login', '/signup', '/forgot-password'];

/** Every screen behind login (see frontend/README.md), with sample-data ids. */
export const APP_ROUTES = [
  ...['about', 'goal', 'training', 'injuries', 'health', 'food', 'review'].map((s) => `/onboarding/${s}`),
  '/onboarding/generating', '/plan-ready',
  '/', '/workouts', '/workouts/w3_upper_a', '/workouts/w3_upper_a/log', '/exercises/ex_landmine_press',
  '/nutrition', '/nutrition?view=week', '/nutrition/recipes/r_chicken_molokhia', '/groceries', '/groceries/pantry',
  '/injuries', '/injuries/inj_shoulder_l', '/injuries/new', '/injuries/inj_shoulder_l/edit', '/injuries/inj_shoulder_l/warning',
  ...['body', 'training', 'injuries', 'nutrition', 'life', 'note'].map((s) => `/check-in/${s}`),
  '/reviews', '/reviews/rv_w3', '/progress', '/profile', '/profile/password',
];
