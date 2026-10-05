# Review list: decisions for you

Every conflict between books, every number I had to map onto the questionnaire, every OCR doubt and every rule no book
covers. Nothing here was resolved silently: each item says what the app does **now** and what you could choose instead.
Page numbers are **PDF pages** (what your PDF viewer shows). Tick an item (`[x]`) or write your decision under it.

Books: (1) Upper Lower Strength and Size, (2) The Ultimate Guide to Body Recomposition, (3) Intermediate Advanced LPP,
(4) Fundamentals Hypertrophy, (5) Encyclopedia of Foods, (6) Strength Training Anatomy, (7) Diet & Cheat Book 1,
(8) Diet & Cheat Nutrition FAQ.

---

## Part B1: rules (`data/rules/*.yaml`)

### Conflicts between books

- [ ] **C1. Protein.**
  - (2) pp. 98–106: 1.2–1.6 g per **pound of lean mass**, more the leaner you are. For a 75 kg man at about 18% body fat that's about 188 g (2.5 g/kg of body weight).
  - (7) p. 50: 1.6–2.5 g per kg of body weight for athletic men, but only **0.8–1.2 g/kg for women**.
  - (1)/(3)/(4) FAQ (e.g. (4) p. 23): "0.8–1 g per pound of body weight as a ballpark" (1.8–2.2 g/kg).
  - **Now:** (2)'s sliding model for everyone. A 68 kg woman gets 124 g (1.8 g/kg); (7) would give 54–82 g.
- [ ] **C2. Fat.** (2) p. 108: 20–35% of calories, more with more body fat. (7) p. 50: 20–30%. **Now:** (2), so heavier
  people get up to 35%.
- [ ] **C3. Activity factors.**
  - (2) p. 69: by lifestyle, for people lifting 3–6 times a week: sedentary 1.2–1.5, lightly active 1.5–1.8, moderately active 1.8–2.0, highly active 2.0–2.2.
  - (7) p. 46: by exercise days: 1.2 / 1.375 (1–3 days) / 1.55 (3–5) / 1.725 (6–7) / **1.725 again** for "very heavy". The book repeats 1.725, which is almost certainly a typo for the usual 1.9. Checked by eye: the OCR read it correctly.
  - **Now:** (2)'s "lightly active" row (see D1). For a 3-day lifter that's 1.5, close to (7)'s 1.375–1.55.
- [ ] **C4. Energy in a kilo of fat.** (5) p. 64 and (7) pp. 44, 48: 3,500 kcal per pound (7,700 per kg). (2) p. 64 uses it
  but warns it "often overestimates" weight loss. **Now:** 7,700 kcal/kg, used only to show the expected weekly change and
  in the weekly review.
- [ ] **C5. Meals a day.** (2) pp. 131–134: 4–6 protein meals, 3–5 hours apart. (5) p. 65: three meals and occasional snacks.
  (7) p. 49 lists "eat every 3 hours" as a myth. **Now:** the person's own choice (2–5 meals); not changed.
- [ ] **C6. Cheat meals and refeeds.** (8) p. 4: a refeed day or cheat meal at the end of each diet period, depending on
  progress. (2) pp. 71–73: scheduled refeeds aren't needed for recomposition; an occasional "free meal" is fine.
  **Now:** neither (the app has no cheat or refeed days). Decide whether you want one.
- [ ] **C7. Water.** (8) p. 5: 4.5 litres a day. (2) p. 162: about 1 ml per kcal (about 2–3 L). (7) p. 60: "at least … litres a
  day" (the digit isn't readable in the OCR; to check by eye in B3). **Now:** the app gives no water target.
- [ ] **C8. Calorie floor.** (5) p. 64: under about 1,400 kcal it's hard to eat enough nutrients. Before B1 the app used
  1,200 (women) / 1,500 (men), not from a book. **Now:** 1,400 for everyone (lower than before for men, higher for women).
- [ ] **C9. Maximum weekly loss.** (5) pp. 64, 66: 1–2 pounds a week. Before B1 the app used 1% of body weight a week (not from a
  book). **Now:** at most 0.9 kg (2 lb) a week. For people under 90 kg that's looser than 1% was. Keep 1% as an extra limit?

### How the books' values were mapped onto the questionnaire

- [ ] **D1. No lifestyle question.** (2)'s activity table needs your job and daily activity. **Now:** everyone is treated as
  "lightly active" (1.5–1.8 by training days), because the plan gives a daily step target (about 8,000, (2) p. 177),
  which matches (2)'s example of "a desk job plus daily walks". 2 training days use 1.5, the row's lowest value, since the
  table starts at 3 days. *Option:* add a lifestyle question so the full table can be used.
- [ ] **D2. No body-fat question.** (2)'s protein (Figure 8B, p. 101) and fat (Figure 8E, p. 110) depend on body fat %.
  **Now:** estimated from BMI, age and sex with the Deurenberg formula (1991). "Why this plan" labels it "Standard formula";
  it's not from your books. (2) p. 96 says a rough estimate is good enough. *Option:* add an optional body-fat question.
- [ ] **D3. Fat-loss pace.** (2) gives about 20% under maintenance (p. 65), up to 20% for recomposition (p. 174), 20–30% for obese
  people (men above ~25% body fat, women above ~35%, p. 67), and 5–10% as a "small deficit" (p. 66).
  **Now:** gentle 10%, steady 20%, faster 20%. "Faster" becomes 25% only when the estimated body fat is above those
  thresholds. The pace question itself isn't in the books.
- [ ] **D4. Muscle-gain surplus.** (2) Table 5A: beginner ~25%, intermediate 15–20%, advanced 10–15%, all **for lean people**
  (men 8–12%, women 18–22% body fat). For higher body fat (2) p. 59 recommends maintenance or a deficit instead.
  **Now:** the lower end (25 / 15 / 10%) for whoever picks "build muscle", whatever their body fat. *Option:* use maintenance
  when the estimated body fat is above the "moderate" range.
- [ ] **D5. Strength goal.** None of the books has a separate "strength" calorie rule. **Now:** the same surplus as muscle
  gain.
- [ ] **D6. Recomposition.** (2) Table 5A: maintenance for beginners and intermediates; advanced lifters ±5–10% "depending on
  the primary goal". **Now:** maintenance for everyone (before B1 it was 10% under, not from a book).
- [ ] **D7. Carbs minimum.** (2) p. 107: never cut a macronutrient out. **Now:** carbs never below 50 g. The 50 is the app's
  number; it only matters in extreme cases.
- [ ] **D8. Warm-up ramp-up sets.** (1) p. 30 and (3) p. 29: 3–4 lighter sets before main lifts (example: bar × 15, then
  about 40%, 65%, 80% and 90% of the working weight for 5, 4, 3 and 2 reps). (4) p. 26: 1–3 light sets.
  **Now:** 40% × 5, 65% × 4, 80% × 3, plus 90% × 2 when the working weight is 60 kg or more. **The 60 kg is the app's
  number.** The bar × 15 set isn't shown separately.
- [ ] **D9. Warm-up moves.** The programs' dynamic drills (leg swings, glute squeeze, prone trap raise, cable rotations,
  overhead shrug, 2 × 12–15, plus 2–3 min of foam rolling) aren't all in the exercise catalogue yet. **Now:** the existing
  moves; leg swings changed to the books' "2 × 12 each leg". They'll be replaced with the programs' drills in B2.
  Foam rolling needs a roller; include it as optional?
- [ ] **D10. Cardio for muscle and strength.** (2) p. 178: easy cardio "not needed"; optionally 1–2 short interval sessions a
  week (e.g. 6 × 20 s fast, 40 s easy). **Now:** one 15-minute interval session a week.
  *Option:* none at all for these goals.
- [ ] **D11. Cardio placement.** (2) pp. 180–181: any time that fits, just not long or hard cardio right before lifting.
  **Now:** rest days first, then after lifting, and never the day before a leg day. That last part is the app's rule.
- [ ] **D12. Deload.** (3) p. 56 (week 9): mostly 2 sets instead of 3, with effort 1–2 RPE lower; (1) p. 11: lighter
  "mini-deload" weeks 1, 4 and 7. **Now:** one set fewer and RPE one lower. Which weeks are lighter comes from each
  program in B2.
- [ ] **D13. Ingredient swaps.** (8) p. 2: swap within the same food group by equal weight (carbs by the listed equal
  amounts). **Now:** the swap is matched by the same protein, carbs or fat. That's close to the FAQ's table, which gives
  equal amounts. The number of choices (3), the rounding (5 g) and the day rebalancing (at most ½ portion) are app
  settings.

### Rules no book covers (still "Not yet from a book")

- [ ] **N1. Ramadan.** Neither Arabic book mentions Ramadan, fasting, suhoor or iftar: searched in the OCR text and in the
  FAQ's own text layer. The closest is (2) pp. 132–134 on intermittent fasting: a moderate eating window, protein spread
  across it, and a slow-digesting last meal. **Now:** the app's Ramadan meal times (suhoor 03:30, iftar 18:00). Do you have
  another source for Ramadan?
- [ ] **N2. Weekly calorie review.** (2) ch. 6 (pp. 78–80) reviews calories only **once or twice a month**, using the 7-day
  average weight, waist and photos together. It then removes 100–250 kcal (from carbs or fat, never protein, fat ≥ 20%)
  or adds 1–2 × 30-min easy cardio; for muscle gain it adds 100–500 kcal. **Now:** the app checks every week and moves
  100 kcal. Switch to every 2 weeks with the book's steps?
- [ ] **N3. Cool-down.** No book gives a stretching cool-down. The programs only suggest 3–5 min of foam rolling after workouts
  if you're often sore ((4) p. 22). **Now:** 4–5 static stretches and a minute of breathing (the app's design). Keep,
  replace with foam rolling, or both?
- [ ] **N4. Starting weights.** The programs choose loads by %1RM or by effort (RPE) for the target reps; neither works before
  a first session. **Now:** body-weight ratios, capped by experience (the app's numbers).
- [ ] **N5. Lighter loads for a recovering injury** (80%, never below 50%), **red-flag thresholds** (pain 7/10, rising 3
  logs in a row), **health-flag numbers** (deficit ≤ 15%, RPE −1, 85% load, +30 s rest) and **no deficit in pregnancy**.
  These are medical safety settings. The books only say to check with a doctor ((5) pp. 64, 66) and not to train through
  pain that stops a full range of motion ((4) p. 22).
- [ ] **N6. Meal optimizer settings** (±5% calories, quarter portions, ½–2½ servings, a recipe at most 4 times a week)
  and the 4.3 weeks a month for staples: app settings.
- [ ] **N7. Check-in trigger for a lighter week** (difficulty 5/5, soreness 4/5 or effort RPE 9+): the app's thresholds.

### Waiting for B2 (they depend on the real programs)

Program choice, training days and session length, sets/reps/RPE/rest, a leg exercise on every full-body day, exercise
swaps and equipment substitutions. Their values come from the three program PDFs in B2.

### OCR doubts in the rules

- (7) p. 46: the last two activity factors are both printed 1.725 (see C3). Checked by eye.
- (7) p. 50: the OCR misread the protein numbers ("1٠,1 … 1,0"). Read by eye: 1.6–2.5 g/kg (men), 0.8–1.2 g/kg (women),
  fat 20–30%.
- (8) p. 2: the exchange table's carb column reads "86 الرز" where the page says "100g الرز". The swap rule doesn't use
  these numbers yet; they'll be checked by eye in B3.

### Found while working on B1 (not about the books)

- [ ] **F1. Saving a workout at the same moment from two places.** The logger now sends exercise results one after
  another and finishes only after the last one. That fixes a real race where a "Log each set" edit could be lost if
  "Save & finish" reached the server first. The server itself still allows two "today" workout logs if two devices save
  at the very same instant (no unique rule on user + date). Fixing that needs a migration that first merges any duplicate
  logs already in the database. Do it in the Render prep, or now?

---

## Part B2: programs and exercises

*(to come)*

## Part B3: recipes and foods

*(to come; every recipe amount will be checked against `data/private/books/07-diet-cheat-recipes/images/`)*
