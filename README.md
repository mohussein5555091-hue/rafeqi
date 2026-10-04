# Rafeqi · رفيقي

A personal trainer and nutritionist web app for people in Egypt. English and Arabic (right-to-left).
Proof of concept: a good workout plan, a good Egyptian nutrition plan, and safe handling of injuries.

## What's where

```
frontend/   React + TypeScript + Tailwind app (copied from design/…/code). The screens.
backend/    Python 3.12 + FastAPI. The API, database, plan engine.
  app/ai/   Reserved for the local LLM + RAG (next session). Writes text only, never numbers.
data/       vocab/movements.yaml (the allowed movement & joint tags), catalogue/ (exercises…),
            rules/ (YAML), programs/ (JSON), uploads/ (private photos, not committed), rafeqi.db (not committed)
docs/       database.md: the schema diagrams
tests/      backend/ (pytest) and e2e/ (Playwright, in a browser)
scripts/    Small helpers used by the npm commands below
design/     Reference export from Claude Design. Never edited.
Books/      Source PDFs. Never committed (see .gitignore).
```

## Requirements (Windows 11)

- **Node.js 20+** (you have 24): https://nodejs.org
- **uv** (you have it): manages Python 3.12 and the backend packages.
  If missing: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
- **Git**

Run every command below from the project folder (`D:\rafeqi`) in PowerShell or Windows Terminal.

## First time only

```powershell
npm run setup
```

This creates `.env` with a random secret key, installs the frontend, backend and test packages, downloads the test browser,
creates the database (`data/rafeqi.db`) and loads the exercise catalogue. It's safe to run again.

## Run everything

```powershell
npm run dev
```

- App: http://localhost:5173
- API docs: http://localhost:5173/api/docs
- Stop: `Ctrl + C`

`npm run dev` first brings the database up to date (`db:migrate`), then starts two programs together. **api** (blue) is FastAPI on port 8000. **web** (magenta) is the Vite dev server on port 5173, which also forwards every `/api/...` request to the API. Your browser only ever talks to port 5173. Both reload by themselves when you save a file.

### Open it on your phone (same Wi-Fi)

1. Start the app with `npm run dev`.
2. In a second terminal, run `npm run lan`. It prints something like `http://192.168.1.5:5173`.
3. Type that address into your phone's browser.

If the phone can't connect:
- Your Wi-Fi must be set to **Private**, because Windows only lets Node.js accept connections on Private networks. Settings → Network & internet → Wi-Fi → (your network) → Network profile type → **Private**. This needs an administrator account.
  Or in an **admin** PowerShell: `Set-NetConnectionProfile -InterfaceAlias Wi-Fi -NetworkCategory Private`
- The first time, Windows may ask whether to allow **Node.js** on the network. Tick **Private networks** and click **Allow**.
- Some routers have "AP / client isolation" turned on, which stops devices seeing each other. Guest networks often do this. Use the tunnel below instead.

### Install it on your phone's home screen

Rafeqi is an installable web app (a "PWA"): it gets its own icon and opens full screen, without the browser bar.

- **Android (Chrome):** open the app, tap **⋮** → **Add to Home screen** (or **Install app**).
- **iPhone (Safari):** open the app, tap **Share** → **Add to Home Screen**.

Chrome only offers "Install" on `https` links or `localhost`, so on a phone use the tunnel link below (on the Wi-Fi
address, Android still offers **Add to Home screen**). The icons are in `frontend/public/icons/`; `node scripts/make-icons.mjs` redraws them.

### Or: open it through an https link (Cloudflare quick tunnel)

Works from any network, even mobile data. Free, with no account.

```powershell
npm run dev        # terminal 1
npm run tunnel     # terminal 2: prints https://<random-words>.trycloudflare.com
```

The first run downloads Cloudflare's `cloudflared` program into `tools/` (not committed). The link changes every time, and **anyone who has it can open the site while the tunnel runs**, so only run it while testing and press `Ctrl + C` when you're done.

## Tests

```powershell
npm test               # everything: backend + typecheck + browser tests
npm run test:backend   # pytest only (fast)
npm run typecheck      # TypeScript only
npm run test:e2e       # Playwright only (starts its own copy of the app with a fresh test database)
npm run test:backend -- -k swap                      # only the backend tests whose name contains "swap"
npm run test:e2e -- specs/phase5.spec.ts --project=desktop   # one browser test file, desktop only
```

The tests never use your `data/rafeqi.db`. Backend tests build a temporary database from the migrations, and the browser
tests start their own copy of the app on ports 8001/5174 with a fresh, seeded database in `tests/e2e/.data/`
(rebuilt on every run, not committed). So `npm run dev` can keep running while you test.

The browser tests pretend today is Monday 5 October 2026 (`RAFEQI_TODAY`), so "today's workout" never depends on the
real weekday. They first create one shared account (questionnaire, plan and one check-in) that read-only tests use; any test
that changes data signs up its own new account, so tests can run side by side.

After a Playwright run, `npm --prefix tests/e2e run report` opens the HTML report (with traces of any failures).

## Database and accounts

| Command | What it does |
|---|---|
| `npm run db:migrate` | Creates or updates the tables to the latest version (runs automatically with `npm run dev`). |
| `npm run db:seed` | Loads the catalogue from `data/catalogue/`: exercises, foods, generic grocery items and recipes. It refuses to load and lists every problem (an unknown tag, a missing translation, a link to something that doesn't exist, a price or brand field). Safe to re-run. |
| `npm run personas` | Writes [`docs/personas.md`](docs/personas.md): the plan the engine builds for each of the 5 test personas. |
| `npm run reset-password -- someone@example.com` | Admin: sets a new password for someone. You type it twice, hidden. It logs them out everywhere and lifts any login lock-out. Email reset comes later. |

- The tables are described, with diagrams, in [`docs/database.md`](docs/database.md).
- **Changing the tables:** edit the models in `backend/app/models/`, then run
  `uv --directory backend run alembic revision --autogenerate -m "what changed"` and `npm run db:migrate`.
  A test fails if the models and the migrations ever disagree.
- **Start from an empty database:** stop the app, delete `data/rafeqi.db`, then run `npm run db:migrate` and `npm run db:seed`.
  This deletes every account.
- **Accounts:** passwords are hashed with argon2id. You log in with an httpOnly, SameSite=Lax cookie that lasts 30 days, and each visit extends it.
  After 5 wrong passwords for one email (or 20 from one IP address) in 15 minutes, logging in is paused for 15 minutes.
- **Everyone sees only their own data:** every table with personal data has a `user_id`, and every query filters by it.
  `tests/backend/test_isolation.py` fails if a table or endpoint is added without being covered.
- **Delete my account** removes every row and the photo folder. The one exception is `llm_calls`: those rows keep their counts with no owner, so AI usage totals stay correct.

API endpoints (try them at http://localhost:5173/api/docs). The screens call them through `frontend/src/data/api.ts`.

| Area | Endpoints |
|---|---|
| Account | `POST /api/auth/signup`, `/login`, `/logout`, `/change-password` · `GET/PATCH/DELETE /api/me` |
| Questionnaire & plan | `GET /api/onboarding`, `PUT /api/onboarding/{about\|goal\|training\|injuries\|health\|food}`, `POST /api/onboarding/complete` · `GET/POST /api/plan` · `GET /api/plan/why` ("Why this plan": every decision with its answers, rule, source and result) |
| Weight | `GET/POST /api/weights`, `DELETE /api/weights/{id}` |
| Training | `GET /api/exercises`, `/api/exercises/{id}` · `GET /api/workouts/week`, `/api/workouts/{id}` · `PUT/DELETE /api/workouts/{id}/exercises/{exercise_id}` (log one exercise / undo) · `POST /api/workouts/{id}/finish` (effort + pain check) · `PUT /api/workouts/{id}/warmup`, `/cooldown` (Done ticks) |
| Swaps & cardio | `GET /api/workouts/{id}/exercises/{exercise_id}/alternatives?reason=…` · `POST /api/workouts/{id}/exercises/{exercise_id}/swap` (just today / from now on) · `GET /api/swaps`, `DELETE /api/swaps/{id}` (undo) · `GET/PUT/DELETE /api/cardio/{weekday}` (a cardio day; marked done with minutes) |
| Nutrition | `GET /api/meals/week`, `/api/meals/day/{date or today}`, `/api/meals/{id}/swap-options` · `POST /api/meals/{id}/swap` · `GET /api/recipes/{id}?meal={meal id}` · `GET /api/meals/{id}/ingredients/{food}/replacements` · `POST /api/meals/{id}/ingredients/{food}/remove` (just this meal / always; rebalances the day) · `DELETE /api/meals/{id}/ingredients/{food}` (undo) · `GET /api/groceries`, `PATCH /api/groceries/items/{id}` · `GET /api/pantry` |
| Injuries | `GET/POST /api/injuries`, `GET/PUT/DELETE /api/injuries/{id}` (saving one rebuilds the plan around it) |
| Check-in & reviews | `GET /api/checkins/next`, `/api/checkins/draft` · `POST /api/checkins` (runs the weekly review) · `GET /api/reviews`, `/api/reviews/{id}` · `GET /api/progress` |

How a week works: weeks run Saturday to Friday. A plan holds one week of sessions and meals, and it repeats until the
next plan version, so each date uses the plan's day with the same weekday. Only today's session can be logged. The weekly
check-in opens on Thursday. A red flag after a workout (sharp pain, swelling, numbness, pain of 7 or more, or pain rising
three times in a row) pauses that body area and rebuilds the plan without it.

## The plan engine

Every number in a plan comes from plain, tested Python in `backend/app/engine/`, never from an AI model. The AI (next session)
only writes the explanations and the weekly-review text. Each number keeps a one-line reason (English and Arabic) with the rule and its source.

| What | Rules | Code |
|---|---|---|
| Calories and macros: Mifflin-St Jeor × activity, goal adjustment, protein per kg, fat minimum, carbs from the rest | `data/rules/nutrition.yaml` | `engine/nutrition.py` |
| Safety: calorie floor, maximum weekly loss, health-flag limits, no deficit in pregnancy, red flags | `data/rules/safety.yaml` | `engine/nutrition.py`, `engine/injuries.py` |
| Program: template choice, equipment and injury swaps, lighter loads, starting weights (capped per experience), exercises that fit the session length, a leg exercise on every full-body day, the time estimate, the person's own swaps and missing equipment | `data/rules/training.yaml`, `data/programs/*.json` | `engine/training.py`, `engine/injuries.py` |
| Warm-up (general, mobility moves, ramp-up sets) and cool-down (stretches, breathing) | `data/rules/training.yaml` (`warmup`, `cooldown`) | `engine/warmup.py` |
| Cardio: sessions and minutes by goal, type by equipment and injuries, placement, daily steps (counted once in calories) | `data/rules/training.yaml` (`cardio`), `nutrition.yaml` (`cardio_counted`) | `engine/cardio.py` |
| Meals: recipes and portions picked by an optimizer (scipy MILP), every day ±5% calories, protein ≥ target; foods the person removed for good are left out | `data/rules/nutrition.yaml` (`meals`) | `engine/meals.py` |
| Removing an ingredient: same-role replacements sized to match, essential ingredients (swap the meal instead), the day rebalanced (small portion changes, or a snack) | `data/rules/nutrition.yaml` (`ingredients`), `data/catalogue/foods.yaml` (`role`), `recipes.yaml` (`essential`) | `engine/ingredients.py` |
| Grocery list: weekly fresh items, monthly staples × 4.3, pantry, pack sizes, WhatsApp text | `data/catalogue/grocery_items.yaml` | `engine/grocery.py` |
| Weekly check-in questions | `data/checkin_questions.yaml` | `engine/checkin.py` |
| Weekly review: calories, deload, too easy / too hard / uncomfortable, pain, meals to change | all of the above | `engine/review.py` |
| Session targets from last time (double progression) | `data/rules/progression.yaml` | `app/progression.py` |

- **All values are placeholders for now**, clearly marked `placeholder: true` with a `PLACEHOLDER:` source. The real values,
  with book and page, are extracted from the books next session. Change a value in the YAML and the next plan uses it; no code changes.
- `backend/app/plans.py` reads the answers, runs the engine and saves a plan version (plans are never edited: each change is version n+1).
- The 5 test personas are in `tests/backend/personas.py`; `tests/backend/test_personas.py` checks each plan against the safety bounds.
- **"Why this plan"** (`/plan/why`, linked from "Your plan is ready", Home and Profile) lists every decision in the plan from
  the stored reasons and each rule's `summary`, `uses`, `source` and `ref` (book, chapter, page, short quote) in the YAML files
  (`backend/app/views/why.py`). Rules still marked `placeholder: true` show "Not yet from a book"; the top says how many
  decisions are backed by the books. Never AI text: the AI summary slot at the top is filled in the AI phase.

## Settings (.env)

`.env` is created by `npm run setup` and is never committed. The template is `.env.example`.

| Variable | Meaning |
|---|---|
| `RAFEQI_ENV` | `development` or `production` |
| `RAFEQI_SECRET_KEY` | Random secret, for anything that needs signing later |
| `RAFEQI_DATABASE_URL` | Optional. Defaults to SQLite at `data/rafeqi.db`. For PostgreSQL later, set this one line. |
| `RAFEQI_TODAY` | Testing only, e.g. `2026-10-05`: the app acts as if today were that date (the browser tests use it). Ignored in production. |

## Exercise images and videos

- **Photos:** from the [Free Exercise DB](https://github.com/yuhonas/free-exercise-db) by yuhonas, released under the
  [Unlicense](https://github.com/yuhonas/free-exercise-db/blob/main/LICENSE.md). That makes them public domain: free to use, change and ship, with no attribution required. We credit it anyway on each exercise page.
  Each exercise has two photos (start and end position), which the app plays in a loop like a GIF. They're stored in
  `frontend/public/exercises/<Source_Id>/0.jpg, 1.jpg`. To add more: `node scripts/fetch-exercise-images.mjs Barbell_Squat Face_Pull`
  (IDs are the folder names in that repo's `exercises/` directory).
- **Videos:** for now, "Watch video" opens a YouTube search for "<exercise name> proper form". The real links will come from the Jeff Nippard program PDFs.

## No prices, anywhere

Rafeqi never shows prices, costs or budgets, because people shop at different stores. The grocery list gives generic item names and amounts only. `tests/e2e/specs/every-page.spec.ts` checks every page in English and Arabic.

## Status

- [x] Phase 1: project setup; designed screens running on sample data
- [x] Phase 2: database and auth (the frontend still uses sample data until Phase 5)
- [x] Phase 3: onboarding questionnaire (backend saves each step and checks every answer; the screens call it through `src/data/api.ts`, still on sample data until Phase 5)
- [x] Phase 4: plan engine (all rule values are placeholders until extracted from the books)
- [x] Phase 5: every screen runs on the real backend (no more sample data), Arabic end to end, installable on a phone
- [x] Workout plan update: warm-up and cool-down in every session, cardio in the week, swap any exercise, typed number
      inputs, fuller sessions with honest time estimates (see "Added since" in `docs/PLAN.md`)
- [x] Whole exercise photos (never cropped), "Why this plan" page, removing an ingredient from a meal (see "Added since")
- [ ] Phase 6: remaining screens
