# Rafeqi — the original plan

Re-read this at the start of every phase. Kept word for word as given; later additions are listed at the end.

---

You are helping me build "Rafeqi" (رفيقي), a web app that acts as a personal trainer and nutritionist for people in Egypt. I'm an AI engineer and a QA/test automation specialist, but I have never built a website or a database. Explain what you're doing in plain language, give me the exact commands to run, and stop at the end of each phase so I can test before you continue.

The frontend is in ./design, exported from Claude Design: Index.dc.html shows every design, and ./design/code is a working React + TypeScript + Tailwind app (Vite, React Router) with a route per screen, sample data in src/mocks/sampleData.ts, all data access through src/data/api.ts, UI text in en.json/ar.json, and design tokens in tailwind.config.ts. Read ./design/code/README.md first. Copy ./design/code into ./frontend and use it as the frontend; keep ./design unchanged as the reference. Connect the backend by replacing the contents of src/data/api.ts with real API calls, keeping the same function names and TypeScript types, and keep the look exactly as designed. Book PDFs are in ./books (never commit them). This session builds the foundation. A later session adds the local LLM and RAG, so leave a clean place for them.

## Goal of the proof of concept

Prove the app produces a good workout plan, a good Egyptian nutrition plan, and handles injuries safely. No smartwatch or fitness band features yet, but keep the design ready to add them later, and ready for a mobile app that uses the same backend.

## Tech stack (use this unless you see a strong reason not to; explain any change)

- Frontend: React + TypeScript + Vite + Tailwind, reusing the components in ./design. React Router. English and Arabic with RTL (i18n).
- Backend: Python 3.12 + FastAPI, Pydantic, SQLAlchemy 2 + Alembic migrations.
- Database: SQLite (one file), written so switching to PostgreSQL later is only a config change.
- Auth: email + password, passwords hashed with argon2, sessions in an httpOnly SameSite=Lax cookie, rate-limited login. No third-party auth service.
- Tests: pytest for the backend, Playwright for end-to-end.
- One command to run everything locally, documented in README.md. Check which OS I'm on and write instructions for it.

## Hard requirements

1. The first page anyone sees is Log in / Sign up. Every other page requires login.
2. Every user sees only their own data. Every table holding user data has a user_id, and every query filters by the logged-in user. Write tests proving user A cannot read or change user B's data through any endpoint.
3. Data persists: when a user logs in again, their profile, plan, logs, and check-ins are all there.
4. After first sign-up, the user completes the onboarding questionnaire (see the design), then gets a generated plan. Users must be 18 or older.
5. There is NO chat. Users never send free-form messages to the AI. The only user input is the onboarding questionnaire, workout/pain logs, and a weekly check-in questionnaire with fixed questions plus one optional note (max 300 characters). The LLM (next session) runs only after onboarding and after each weekly check-in.

## Phases (stop after each one)

### Phase 1 - Project setup
Folders: frontend/ (copied from ./design/code), backend/, data/, books/, scripts/, tests/. In frontend/, run npm install and npm run typecheck and fix every error without changing the design. Tooling, .gitignore (books/, data/uploads/, the database file, .env, node_modules), secrets in .env, README. Show me the designed screens running in my browser with the sample data, and how to open them on my phone on the same Wi-Fi.

### Phase 2 - Database and auth
Design the schema and show it to me as a diagram before writing migrations. At least these tables: users, sessions, profiles (questionnaire answers), injuries, plans (versioned, with a JSON "reasons" field explaining each decision), training_programs, program_days, exercises (tags: movement pattern, joints loaded, range of motion, equipment, difficulty; plus description, step-by-step instructions, form cues, common mistakes, image_url or GIF path, video_url, media source and license), exercise_substitutions, workout_logs, set_logs, pain_logs, foods (per 100 g: kcal, protein, carbs, fat, fiber; Arabic and English names; everyday units with gram equivalents; source), grocery_items (generic item name in Arabic and English, e.g. "Milk", "Chicken breast", "Fish fillet"; category; shelf life: weekly or monthly; buying unit and typical pack size, e.g. 1 L, 1 kg, 30 eggs; NO brand names and NO prices anywhere), a mapping from foods/ingredients to grocery_items, recipes, recipe_ingredients, recipe_steps, meal_plans, meal_plan_items, grocery_lists, grocery_list_items, pantry_items, checkins (weight, measurements, photo paths), checkin_answers (one row per question answered), weekly_reviews (AI text, plan changes, citations, model used), llm_calls (task, model, tokens, latency, cost). Endpoints: sign up, log in, log out, change password, delete my account and all my data.

### Phase 3 - Onboarding questionnaire
Save answers step by step so a user can leave and resume. Server-side validation with sensible ranges. Any health-screening "yes" sets a conservative flag used by the plan engine.

### Phase 4 - Plan engine (the heart of the app)
All numbers come from deterministic, tested Python code, never from an LLM. The LLM (next session) only writes explanations and weekly reviews.

- Rules live in editable YAML under data/rules/ (nutrition.yaml, training.yaml, safety.yaml). Each rule records its source (book + chapter/page). Use clearly marked placeholder values for now; next session we extract the real values from the books.
- Nutrition: BMR (Mifflin-St Jeor) x activity factor, goal adjustment, protein per kg, fat minimum, carbs from the remainder. Safety bounds: calorie floor, maximum weekly weight-loss rate, more conservative targets when the health flag is set. Every number stores a one-line reason.
- Training: choose a program template by experience, days per week, goal, and equipment. Templates will come from: Fundamentals Hypertrophy Program (beginners), Upper Lower Strength and Size Program (intermediate, 4 days), Intermediate Advanced LPP Program, all by Jeff Nippard, encoded as JSON in data/programs/. Start with one small sample template so the pipeline works end to end.
- Injuries: exclude exercises whose tags match an active injury's painful movements or restrictions; substitute the closest exercise with the same movement pattern that avoids them; reduce load for "recovering" injuries; store the reason for each swap. Red flags (sharp pain, swelling, numbness, worsening pain, or pain rising in pain_logs) pause that body area and show "see a doctor or physiotherapist". Never diagnose.
- Meals: pick recipes and scale portions to hit daily calories within +/-5% and protein at or above target, respecting dislikes, allergies, meals per day, and cooking time. There is no budget or price logic anywhere. Use a small optimizer (scipy or PuLP), not guessing. Seed 10 sample Egyptian recipes for now; the real ones come from the Arabic recipe book next session.
- Grocery list (generated automatically whenever the meal plan is created or changes):
  1. Expand the week's meals into ingredients and grams, map each ingredient to a generic grocery item, and sum per item.
  2. Split by shelf life: weekly list = fresh items (vegetables, fruit, bread, chicken, meat, fish, milk, yogurt, eggs, cheese); monthly list = staples (rice, pasta, lentils, fava beans, oats, oil, tahini, spices, frozen items) using the week's amount x 4.3.
  3. Subtract what's in the pantry, convert grams to buying units (kg, g, L, pieces, eggs), and round up to sensible pack sizes.
  4. Group by category (Vegetables & fruit; Meat, chicken & fish; Dairy & eggs; Bread & bakery; Pantry staples; Spices & sauces) No prices or cost estimates.
  5. Item names are always generic ("Milk 3 L", "Chicken breast 1.5 kg", "Fish fillet 1 kg", "Eggs 18"), never brands. Also produce a plain-text version for copying into WhatsApp.
  Unit tests: totals match the meal plan, monthly staples don't appear in the weekly list, pantry subtraction works, no brand names, no prices.
- Weekly check-in questions live in data/checkin_questions.yaml (id, English and Arabic text, answer type, options, range), so I can change them without code changes. Use the questions in the design.
- Weekly review engine: from the check-in answers, workout logs, and weight trend, decide the changes in code, in small bounded steps: calories, progress or deload lifts, swap exercises the user marked as uncomfortable, reduce load or pause areas where pain went up, replace meals the user wants changed with recipes that fit the same macros, then regenerate the grocery list. Store each change with a reason. Red-flag answers skip the normal review and show "see a doctor or physiotherapist".
- Unit tests for every rule, plus 5 test personas (beginner woman losing fat; intermediate man with a left shoulder injury; advanced lifter; someone with a health flag; someone fasting in Ramadan with 2 meals a day). Check each generated plan against the safety bounds.

### Phase 5 - Connect the frontend
Replace the contents of src/data/api.ts with real API calls (same function names and types, so the screens don't change). Use the designed loading, empty, and error states. Arabic/RTL working end to end. Make the site installable as a home-screen web app (PWA manifest and icons).

### Phase 6 - The rest of the screens
Workout logging, pain logging, weekly check-in questionnaire (photos stored on disk under data/uploads/<user_id>/, never public, served only to their owner), weekly review page (show the engine's changes and reasons for now; the AI text comes next session), grocery list with weekly/monthly tabs, checkboxes, "I already have this", pantry, and copy-as-text, progress charts, profile and settings including "regenerate my plan".

## After each phase

Run the tests, show me how to try it by hand, and list anything you assumed.

## Added since this plan was written (these stay as built)

- `weight_logs` (daily weight).
- The movement vocabulary (`data/vocab/movements.yaml`).
- Per-exercise workout logging with exact targets (`data/rules/progression.yaml`).
- Colour palette 1b.

### Workout plan changes (requested after Phase 5; these stay as built)

1. **Warm-up before every session** (about 8–10 min), its own section above the exercises:
   5 min of easy general movement chosen by equipment (bike or incline walk at the gym; marching in place, jump rope or a
   brisk walk at home); 3–4 dynamic mobility moves for the day's muscles (arm circles, band pull-aparts… for upper days;
   leg swings, bodyweight squats, glute bridges… for lower days); 2–3 lighter ramp-up sets of the first main exercise
   (50% × 8, 75% × 4, plus 90% × 2 from 60 kg; none below 10 kg), with the weights worked out from that session's target.
   Any move ruled out by an injury's painful movements or restrictions (movement vocabulary) is skipped, with the reason.
2. **Cool-down after every session** (about 5–8 min), its own section after the exercises with a "Done" tick:
   4–5 static stretches for the muscles trained that day (most-trained first), 30–45 s each (both sides for one-sided
   stretches), then 1 min of slow breathing. The warm-up has a "Done" tick too.
3. **Cardio in the weekly plan**, decided by the engine from goal, experience, equipment, health flag and injuries:
   fat loss 2–3 × 20–30 min easy (talking pace) + a daily step target; muscle gain / strength 1–2 short sessions;
   recomposition about 2. Type by equipment and injury: incline walk, bike, elliptical, brisk walk, marching, jump rope;
   injured legs mean the bike or walking, never running or jumping; the health flag means easy and no jumping.
   On rest days first, then after lifting, never on the day before a leg day. Cardio days show in the Workouts week,
   open like any other day, and are marked done with the minutes actually done (`cardio_logs`).
   **Calories count cardio once:** the activity level already includes it, so it's never added on top, and the
   calorie reasons say so (`nutrition.yaml` `cardio_counted`).
4. **Every warm-up move, stretch and cardio type has the same how-to page as the exercises** (image, steps, cues,
   mistakes, video link). They live in the exercise catalogue with `type`: strength, cardio, mobility or stretch.
5. **All of these rules are in `data/rules/training.yaml`** (`session`, `full_body_legs`, `warmup`, `cooldown`, `cardio`,
   `swaps`, and `start_load.max_kg`) and marked `placeholder: true` until the real values are extracted from the books
   (the Jeff Nippard programs' warm-up protocols; the recomposition guide's cardio).
6. **Fixes:** every full-body day has a squat or hip hinge (or, when injuries rule both out, another leg exercise);
   the number of exercises follows the session length chosen (`session.exercises_by_minutes`), topped up from the
   program's other days when injuries remove too many; the time estimate is worked out from the sets, rests, warm-up
   and cool-down; starting weights are more conservative and capped per experience level.
7. **Number inputs** (questionnaire, check-in weight and measurements, the weight log): tap the number to type it
   (the phone's number keyboard, with a decimal point where needed); + and − stay for small changes, and holding one
   repeats faster and faster; the fields start empty with an "e.g." placeholder; typed values are checked against the
   same ranges with a clear message ("Weight must be between 35 and 250 kg"); "." or "," and Arabic digits both work.
8. **Swap any exercise** from the session or the logger: why (equipment not available / machine busy / can't do it /
   it causes pain) → 2–4 alternatives with the same movement pattern and muscles that fit the equipment and every
   active injury (from `exercise_substitutions` and the movement vocabulary) → "Just today" (that session only) or
   "From now on" (the program for every week; kept by the weekly review and "regenerate", which never put the old
   exercise back; undo from the exercise's page). "Equipment not available" also saves that equipment as missing in
   the profile, so future plans avoid it. "It causes pain" also offers to add or update an injury. A swapped-in
   exercise starts as "find your weight" and progresses from there, and shows a badge with the reason.
   Rebuilding the plan for a swap or an injury keeps the week's meals and grocery list when the nutrition targets
   haven't changed.

### Photos, "Why this plan", and removing ingredients (requested after the workout plan update; these stay as built)

1. **Exercise photos are never cropped:** the photo box takes the photo's own proportions (object-fit: contain on a
   plain background), on the exercise page and in every thumbnail, on phones and desktop. Catalogue alternatives that
   are exercises in the catalogue link to their page with a thumbnail; "No equipment needed" is its own label (the
   loader refuses "Other equipment" for a bodyweight-only alternative). A browser test measures that the whole photo
   is inside its box at its original proportions.
2. **"Why this plan"** (`/plan/why`; linked from "Your plan is ready", Home and Profile): every decision in the plan
   (calories, protein, carbs and fat, program, days and session length, sets/reps/RPE, starting weights,
   progression, deload, warm-up, cool-down, cardio, each injury or equipment swap or exclusion, every recipe's
   portions) with the answers it used, the rule in plain language, its source (book, chapter, page and a 1–2 sentence
   quote) and the result. Built only from the reasons the engine stores with the plan and the rule files' `summary`,
   `uses`, `source`, `placeholder` and `ref` fields (the rule loader refuses a rule without them, and a
   non-placeholder rule without a book reference). Placeholders show "Not yet from a book"; the top says
   "X of Y decisions backed by your books". English and Arabic. The AI summary at the top is a reserved slot until the
   AI phase.
3. **Remove an ingredient** from any meal card or recipe page: one-tap reason ("I don't like it" / "Not available right
   now"), then 1–3 replacements with the same role (`foods.yaml` `role`: eggs → cheese or yogurt), sized to give about
   the same protein, carbs or fat, or "Remove without replacing"; then "Just this meal" or "Always". "Always" changes
   every meal of the week that has it; "Always" and every "I don't like it" add it to the profile's disliked foods, so
   every later plan (weekly review, "regenerate") leaves it out and drops recipes it is essential to. Essential
   ingredients (`recipes.yaml` `essential: true`, e.g. lentils in lentil soup) can't be removed: the screen offers to
   swap the whole meal. The meal's and the day's numbers are worked out again at once; if the day fell below its
   targets (protein first), other portions move by at most ½ portion in quarter steps (a small MILP, calories within
   ±5%, else ±8%), or a snack is suggested, and the day says what changed. The grocery list is rebuilt from what's
   really cooked. Removed and replaced ingredients are struck through with Undo (undo reverses the whole choice,
   including the dislike). Rules: `nutrition.yaml` `ingredients` (placeholder).
