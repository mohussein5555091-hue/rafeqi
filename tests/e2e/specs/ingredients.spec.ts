import type { Page } from '@playwright/test';
import { SIGNED_OUT, TODAY, api, expect, freshUser, test, waitForContent } from './helpers';

// Removing an ingredient from a meal: reasons, a same-role replacement, "Just this meal" / "Always", struck through
// with Undo, the day's note, the grocery list, and essential ingredients (swap the meal instead).
test.use({ storageState: SIGNED_OUT });

type Ingredient = { foodId: string; name: { en: string }; essential: boolean; status: string };
type Meal = { id: string; recipeId: string; name: { en: string }; ingredients: Ingredient[] };

const today = async (page: Page): Promise<Meal[]> => (await api(page, `/meals/day/${TODAY}`)).meals;

/** The first of today's meals with an ingredient matching `want` (checked against the API's replacement options). */
async function find(page: Page, want: (i: Ingredient, opts: { essential: boolean; options: unknown[] }) => boolean) {
  for (const [n, m] of (await today(page)).entries()) {
    for (const i of m.ingredients) {
      const opts = await api(page, `/meals/${m.id}/ingredients/${i.foodId}/replacements`);
      if (want(i, opts)) return { n, meal: m, ingredient: i, opts };
    }
  }
  throw new Error('no such ingredient today');
}

async function openIngredients(page: Page, n: number) {
  await page.goto('/nutrition');
  await waitForContent(page);
  const card = page.getByTestId('meal-card').nth(n);
  await card.getByRole('button', { name: /^Ingredients \(\d+\)$/ }).click();
  return card;
}

test('replace an ingredient just for this meal, see it struck through, then undo it', async ({ page }) => {
  await freshUser(page);
  const { n, meal, ingredient, opts } = await find(page, (i, o) => !i.essential && o.options.length > 0);
  const card = await openIngredients(page, n);
  const row = card.locator(`[data-food="${ingredient.foodId}"]`);
  await row.getByRole('button', { name: `Remove: ${ingredient.name.en}` }).click();
  const sheet = page.getByRole('dialog', { name: `Remove ${ingredient.name.en}` });
  await sheet.getByRole('radio', { name: /Not available right now/ }).click();
  const choice = sheet.getByRole('radiogroup', { name: 'Put something similar instead?' }).getByRole('radio');
  await expect(choice).toHaveCount((opts.options as unknown[]).length + 1); // the options, and "Remove without replacing"
  const first = (opts.options as { name: { en: string } }[])[0].name.en;
  await choice.first().click();
  await sheet.getByRole('radio', { name: 'Just this meal' }).check({ force: true });
  await sheet.getByRole('button', { name: `Replace with ${first}` }).click();
  await expect(sheet).toHaveCount(0);
  await expect(row).toHaveAttribute('data-status', 'replaced');
  await expect(row).toContainText(`→ ${first}`);
  await expect(row.locator('.line-through').first()).toContainText(ingredient.name.en); // struck through
  // Only this meal changed, and the grocery list says so.
  const others = (await today(page)).filter((m) => m.id !== meal.id).flatMap((m) => m.ingredients);
  expect(others.every((i) => i.status === 'kept')).toBe(true);
  expect((await api(page, '/groceries')).changeNote.en).toBe(`Updated: ${ingredient.name.en} replaced by ${first}.`);
  // Undo.
  await row.getByRole('button', { name: `Undo: ${ingredient.name.en}` }).click();
  await expect(row).toHaveAttribute('data-status', 'kept');
  await expect(page.getByTestId('day-note')).toHaveCount(0);
});

test('"I don\'t like it" + Always: gone from every meal this week, and the day shows what changed', async ({ page }) => {
  await freshUser(page);
  const { n, ingredient } = await find(page, (i, o) => !i.essential && o.options.length === 0); // a flavour: nothing replaces it
  const card = await openIngredients(page, n);
  await card.locator(`[data-food="${ingredient.foodId}"]`).getByRole('button', { name: /^Remove: / }).click();
  const sheet = page.getByRole('dialog');
  await sheet.getByRole('radio', { name: /I don't like it/ }).click();
  await expect(sheet.getByText("Nothing similar to put instead: it's simply left out.")).toBeVisible();
  await sheet.getByRole('radio', { name: 'Always' }).check({ force: true });
  await sheet.getByRole('button', { name: `Remove ${ingredient.name.en}` }).click();
  await expect(sheet).toHaveCount(0);
  await expect(page.getByTestId('day-note')).toContainText(`${ingredient.name.en} removed from`);
  const week = await api(page, '/meals/week');
  for (const d of week) {
    const meals: Meal[] = (await api(page, `/meals/day/${d.date}`)).meals;
    for (const i of meals.flatMap((m) => m.ingredients).filter((x) => x.foodId === ingredient.foodId)) {
      expect(i.status, d.date).toBe(i.essential ? 'kept' : 'removed');
    }
  }
});

test('an essential ingredient offers to swap the whole meal instead', async ({ page }) => {
  await freshUser(page);
  const { n, ingredient } = await find(page, (i) => i.essential);
  const card = await openIngredients(page, n);
  await card.locator(`[data-food="${ingredient.foodId}"]`).getByRole('button', { name: /^Remove: / }).click();
  const sheet = page.getByRole('dialog', { name: `Remove ${ingredient.name.en}` });
  await expect(sheet.getByTestId('essential')).toContainText(`${ingredient.name.en} is what makes this meal`);
  await sheet.getByRole('button', { name: 'Swap the meal' }).click();
  await expect(page.getByRole('dialog', { name: /^Swap / })).toBeVisible();
});

test('the recipe page has Remove and Undo too, for the meal it was opened from', async ({ page }) => {
  await freshUser(page);
  const { n, meal, ingredient } = await find(page, (i, o) => !i.essential && o.options.length > 0);
  await page.goto('/nutrition');
  await waitForContent(page);
  await page.getByTestId('meal-card').nth(n).getByRole('link', { name: 'Recipe' }).click();
  await expect(page).toHaveURL(new RegExp(`/nutrition/recipes/${meal.recipeId}\\?meal=${meal.id}$`));
  await waitForContent(page);
  const row = page.locator(`[data-food="${ingredient.foodId}"]`);
  await row.getByRole('button', { name: `Remove: ${ingredient.name.en}` }).click();
  const sheet = page.getByRole('dialog');
  await sheet.getByRole('radio', { name: /Not available right now/ }).click();
  await sheet.getByRole('radio', { name: 'Remove without replacing' }).click();
  await sheet.getByRole('button', { name: `Remove ${ingredient.name.en}` }).click();
  await expect(row).toHaveAttribute('data-status', 'removed');
  await expect(row).toContainText('Removed: not available');
  await row.getByRole('button', { name: /^Undo: / }).click();
  await expect(row).toHaveAttribute('data-status', 'kept');
});
