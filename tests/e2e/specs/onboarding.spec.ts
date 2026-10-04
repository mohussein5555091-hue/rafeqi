import { SIGNED_OUT, api, expect, test, waitForContent } from './helpers';

test.use({ storageState: SIGNED_OUT });

test('sign up, then the questionnaire: saved step by step, survives a reload, resumes, then builds the plan', async ({ page }) => {
  // Sign up: every page leads to the questionnaire until it's finished.
  await page.goto('/signup');
  await page.getByLabel('First name').fill('Mona');
  await page.getByLabel('Email').fill(`mona-${Date.now()}@example.com`);
  await page.getByLabel('Password', { exact: true }).fill('password1');
  await page.getByRole('checkbox').check();
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page).toHaveURL(/\/onboarding\/about$/);
  await page.goto('/groceries');
  await expect(page).toHaveURL(/\/onboarding\/about$/);
  await waitForContent(page);

  // Under 18 can't continue.
  const age = page.getByRole('group', { name: 'Age' });
  for (let i = 0; i < 15; i++) await age.getByRole('button', { name: /^Decrease/ }).click(); // 30 → 16
  await expect(page.getByText('You need to be 18 or older')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Next' })).toBeDisabled();
  for (let i = 0; i < 4; i++) await age.getByRole('button', { name: /^Increase/ }).click(); // 16 → 20
  await page.getByRole('radio', { name: 'Female' }).check({ force: true });
  await page.getByRole('button', { name: 'Next' }).click();

  await expect(page).toHaveURL(/\/onboarding\/goal$/);
  await page.getByRole('radio', { name: /Build muscle/ }).click();
  await page.getByRole('button', { name: 'Next' }).click();
  await expect(page).toHaveURL(/\/onboarding\/training$/);

  // Reload mid-way: the answers are on the server, and /onboarding resumes at this step.
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
  await waitForContent(page);

  // The plan on screen is the one the engine saved.
  const plan = await api(page, '/plan');
  await expect(page.getByText(plan.calories.toLocaleString('en-GB'), { exact: true })).toBeVisible();
  expect(plan.program.daysPerWeek).toBe(3);
  await page.getByRole('link', { name: 'See my workout plan' }).click();
  await expect(page).toHaveURL(/\/workouts$/);
  await waitForContent(page);
});

test('signing up with an email that already has an account says so', async ({ page }) => {
  await page.goto('/signup');
  await page.getByLabel('First name').fill('Omar');
  await page.getByLabel('Email').fill('omar@example.com'); // the shared account
  await page.getByLabel('Password', { exact: true }).fill('password1');
  await page.getByRole('checkbox').check();
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByText('There\'s already an account with this email')).toBeVisible();
  await expect(page).toHaveURL(/\/signup$/);
});
