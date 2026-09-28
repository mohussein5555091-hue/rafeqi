import { expect, test, type Page } from '@playwright/test';
import { APP_ROUTES, PUBLIC_ROUTES, SIGNED_OUT, waitForContent } from './helpers';

// Money must never appear: people shop at different stores, so Rafeqi shows no prices, costs or budgets.
// (Careful in Arabic: سعرة/سعرات means *calories*, so the bare word سعر is not matched.)
const MONEY = /\bEGP\b|\bL\.?E\b|\bbudget|\bprices?\b|\bpriced\b|\bcost estimate|\btotal cost|ج\.م|جنيه|ميزانية|أسعار|الأسعار|تكلفة/i;

async function checkPage(page: Page, route: string) {
  await page.goto(route);
  await waitForContent(page);
  for (const lang of ['en', 'ar'] as const) {
    // Exactly one light/dark toggle is visible (sidebar on desktop, header on phones).
    await expect(page.locator('[data-testid="theme-toggle"]:visible'), `theme toggle on ${route} (${lang})`).toHaveCount(1);
    const text = await page.locator('body').innerText();
    expect(text.match(MONEY)?.[0], `money text on ${route} (${lang})`).toBeUndefined();
    if (lang === 'en') {
      await page.locator('button:visible', { hasText: 'عربي' }).first().click();
      await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
      await waitForContent(page);
    }
  }
}

test.describe('public pages', () => {
  test.use({ storageState: SIGNED_OUT });
  for (const route of PUBLIC_ROUTES) test(`${route}: theme toggle, no prices`, async ({ page }) => checkPage(page, route));
});

test.describe('signed-in pages', () => {
  for (const route of APP_ROUTES) test(`${route}: theme toggle, no prices`, async ({ page }) => checkPage(page, route));
});
