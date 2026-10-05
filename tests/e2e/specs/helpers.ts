import { expect, test as base, type APIRequestContext, type Page } from '@playwright/test';

export { expect };

export const AUTH_FILE = '.auth/user.json';
/** For tests that must start signed out. */
export const SIGNED_OUT = { cookies: [], origins: [] };

/** The test server pretends today is this Monday (RAFEQI_TODAY in scripts/e2e-server.mjs); the browser's clock matches. */
export const TODAY = '2026-10-05';
export const WEEK_START = '2026-10-03'; // Saturday

/**
 * Every test runs with the browser's clock on TODAY (the server's "today"), in the morning.
 * Timers still run normally; only the date is fixed.
 */
export const test = base.extend({
  page: async ({ page }, use) => {
    await page.clock.setFixedTime(new Date(`${TODAY}T08:00:00Z`));
    await use(page);
  },
});

/** The shared account, created by auth.setup.ts with a finished questionnaire, a plan and one weekly check-in. */
export const TEST_USER = { email: 'omar@example.com', password: 'password1', firstName: 'Omar' };

/** The questionnaire the test accounts answer: a left-shoulder injury, 4 days a week (Sat, Mon, Wed, Thu). */
export const ANSWERS = {
  about: { sex: 'male', age: 29, heightCm: 180, weightKg: 88, waistCm: 96 },
  goal: { goal: 'loseFat', pace: 'steady' },
  training: { experience: 'intermediate', daysPerWeek: 4, sessionMinutes: 60, location: 'gym', dailyActivity: 'onFeet' },
  injuries: { injuries: [{ region: 'shoulderL', side: 'left', type: 'tendon', severity: 3, painfulMovements: ['overheadPress', 'benchPress'], restrictions: ['noOverhead'] }] },
  health: { heartCondition: false, diabetes: false, pregnancy: false, recentSurgery: false, exerciseMedication: false },
  food: { mealsPerDay: 4, dislikes: ['liver'], allergies: ['none'], fasting: [], cookingMinutes: 30 },
};

async function ok(res: Awaited<ReturnType<APIRequestContext['get']>>) {
  expect(res.ok(), `${res.url()} → ${res.status()} ${await res.text()}`).toBeTruthy();
  return res.status() === 204 ? undefined : res.json();
}

/**
 * Signs up through the API (the page's cookie becomes that account), answers the questionnaire and builds the plan.
 * Used by tests that change data, so each has its own account and tests can run in parallel.
 */
export async function createUser(request: APIRequestContext, { email, password = TEST_USER.password, plan = true } = {} as { email?: string; password?: string; plan?: boolean }) {
  email ??= `user-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
  await ok(await request.post('/api/auth/signup', { data: { firstName: TEST_USER.firstName, email, password, adultConfirmed: true } }));
  if (plan) {
    for (const [step, body] of Object.entries(ANSWERS)) await ok(await request.put(`/api/onboarding/${step}`, { data: body }));
    await ok(await request.post('/api/onboarding/complete'));
    await ok(await request.post('/api/plan'));
  }
  return { email, password };
}

/** A new account with a plan, logged in on this page. */
export async function freshUser(page: Page) {
  const user = await createUser(page.request);
  await page.goto('/');
  await waitForContent(page);
  return user;
}

export async function logIn(page: Page, user: { email: string; password: string } = TEST_USER) {
  await page.goto('/login');
  await page.getByLabel('Email').fill(user.email);
  await page.getByLabel('Password', { exact: true }).fill(user.password);
  await page.getByRole('button', { name: 'Log in' }).click();
  await expect(page).toHaveURL(/\/$/);
}

/** Waits until no loading skeleton is left on the page. */
export async function waitForContent(page: Page) {
  await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
}

export async function api<T = any>(page: Page, path: string): Promise<T> { // eslint-disable-line @typescript-eslint/no-explicit-any
  return ok(await page.request.get(`/api${path}`));
}

export const PUBLIC_ROUTES = ['/login', '/signup', '/forgot-password'];

/**
 * Every screen behind login (see frontend/README.md). `:name` parts are filled in from the logged-in account's data
 * by `resolve()`. /onboarding/generating isn't here: opening it builds a new plan (onboarding.spec.ts covers it).
 */
export const APP_ROUTES = [
  ...['about', 'goal', 'training', 'injuries', 'health', 'food', 'review'].map((s) => `/onboarding/${s}`),
  '/plan-ready', '/plan/why',
  '/', '/workouts', '/workouts/:today', '/workouts/:planned', '/workouts/:cardio', '/workouts/:today/log', '/exercises/:exercise',
  '/exercises/ex_cat_cow', '/exercises/ex_quad_stretch', '/exercises/ex_bike',
  '/nutrition', '/nutrition?view=week', `/nutrition/day/${TODAY}`, '/nutrition/recipes/:recipe', '/groceries', '/groceries/pantry',
  '/injuries', '/injuries/:injury', '/injuries/new', '/injuries/:injury/edit', '/injuries/:injury/warning',
  ...['body', 'training', 'injuries', 'nutrition', 'life', 'note'].map((s) => `/check-in/${s}`),
  '/reviews', '/reviews/:review', '/progress', '/profile', '/profile/password',
];

/** Fills in the `:name` parts of a route with real ids from the account. */
export async function resolve(page: Page, route: string): Promise<string> {
  if (!route.includes(':')) return route;
  const week = await api(page, '/workouts/week');
  const lifting = week.sessions.filter((s: { kind: string }) => s.kind === 'strength');
  const today = lifting.find((s: { status: string }) => s.status === 'today');
  const values: Record<string, () => Promise<string>> = {
    today: async () => today.id,
    planned: async () => lifting.find((s: { status: string }) => s.status === 'planned').id,
    cardio: async () => week.sessions.find((s: { kind: string }) => s.kind === 'cardio').id,
    exercise: async () => today.exercises[0].exerciseId,
    recipe: async () => (await api(page, `/meals/day/${TODAY}`)).meals[0].recipeId,
    injury: async () => (await api(page, '/injuries'))[0].id,
    review: async () => (await api(page, '/reviews'))[0].id,
  };
  let out = route;
  for (const name of route.match(/:\w+/g) ?? []) out = out.replace(name, await values[name.slice(1)]());
  return out;
}
