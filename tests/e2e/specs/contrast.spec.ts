import AxeBuilder from '@axe-core/playwright';
import type { Page } from '@playwright/test';
import { APP_ROUTES, PUBLIC_ROUTES, SIGNED_OUT, expect, resolve, test, waitForContent } from './helpers';

// Every page's text meets WCAG AA contrast (4.5:1, or 3:1 for large text) in light and dark mode,
// in English and Arabic. Runs on desktop only: the colours are the same on phones.
async function check(page: Page, route: string) {
  await page.goto(await resolve(page, route));
  await waitForContent(page);
  await page.waitForTimeout(250); // colour transitions settle
  const { violations } = await new AxeBuilder({ page }).withRules(['color-contrast']).analyze();
  const nodes = violations.flatMap((v) => v.nodes.map((n) => `${n.target.join(' ')} → ${n.any[0]?.message ?? ''}`));
  expect(nodes, `${route}`).toEqual([]);
}

for (const scheme of ['light', 'dark'] as const) {
  test.describe(`${scheme} mode`, () => {
    test.skip(({ isMobile }) => isMobile, 'same colours on phones');
    test.use({ colorScheme: scheme });

    test.describe('signed out', () => {
      test.use({ storageState: SIGNED_OUT });
      for (const route of PUBLIC_ROUTES) test(`${route} contrast`, async ({ page }) => check(page, route));
    });
    for (const route of APP_ROUTES) test(`${route} contrast`, async ({ page }) => check(page, route));
    test('Arabic dashboard contrast', async ({ page }) => {
      await page.goto('/');
      await page.locator('button:visible', { hasText: 'عربي' }).first().click();
      await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
      await check(page, '/');
    });
  });
}
