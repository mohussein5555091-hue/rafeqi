# Rafeqi · رفيقي

A personal trainer and nutritionist web app for people in Egypt. English and Arabic (right-to-left).
Proof of concept: a good workout plan, a good Egyptian nutrition plan, and safe handling of injuries.

## What's where

```
frontend/   React + TypeScript + Tailwind app (copied from design/…/code). The screens.
backend/    Python 3.12 + FastAPI. The API, database, plan engine.
  app/ai/   Reserved for the local LLM + RAG (next session). Writes text only, never numbers.
data/       vocab/movements.yaml (the allowed movement & joint tags), catalogue/ (exercises…),
            rules/ (YAML), programs/ (JSON), uploads/ (private photos, not committed), rafeqi.db (not committed),
            private/ (text extracted from the books, not committed)
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

- **Backend tests on PostgreSQL** (optional; SQLite is the default): with a PostgreSQL server running, set
  `RAFEQI_TEST_POSTGRES_URL=postgresql://postgres:PASSWORD@localhost:5432/postgres` and run `npm run test:backend`.
  Each test gets its own database copied from a migrated template.
- **Browser tests with an already-installed Chromium** (e.g. when Playwright can't download its own): set
  `PW_CHROMIUM_PATH` to the browser's path.

## Database and accounts

| Command | What it does |
|---|---|
| `npm run db:migrate` | Creates or updates the tables to the latest version (runs automatically with `npm run dev`). |
| `npm run db:seed` | Loads the catalogue from `data/catalogue/`: exercises, foods, generic grocery items and recipes. It refuses to load and lists every problem (an unknown tag, a missing translation, a link to something that doesn't exist, a price or brand field). Safe to re-run. |
| `npm run personas` | Writes [`docs/personas.md`](docs/personas.md): the plan the engine builds for each of the 5 test personas. |
| `npm run backup` | Saves every table (and photos on disk) into `backups/rafeqi-<date>.json.gz`, keeping the newest 14. Works for SQLite and PostgreSQL. See [`docs/DEPLOY.md`](docs/DEPLOY.md) for daily backups. |
| `npm run restore -- backups/….json.gz [--url …]` | Loads a backup into an **empty** database (refuses one that has accounts). |
| `npm run feedback` | Lists what people sent with "Send feedback" in Profile & settings. |
| `npm run build` / `npm start` | Builds the screens; `start` serves everything from the backend in production mode (see `docs/DEPLOY.md`). |
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
| Calories and macros: Mifflin-St Jeor × activity, goal as a % of maintenance, estimated body fat → protein per pound of lean mass and fat as a % of calories, carbs from the rest | `data/rules/nutrition.yaml` | `engine/nutrition.py` |
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

- **Values from the books** have `placeholder: false` and a `ref` (book, chapter, PDF page, a 1–2 sentence summary). Values no
  book covers yet are marked `placeholder: true` with a `PLACEHOLDER:` source. `data/REVIEW.md` lists every conflict between
  books, every mapping decision and every gap, for the owner to decide. Change a value in the YAML and the next plan uses it.
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
| `RAFEQI_SECRET_KEY` | Random secret. Required (at least 32 characters) in production. |
| `RAFEQI_DATABASE_URL` | Optional. Defaults to SQLite at `data/rafeqi.db`. PostgreSQL: paste the connection string (`postgres://…` from Neon/Supabase works as is). |
| `RAFEQI_INVITE_CODE` | Optional. When set, sign-up needs this code. |
| `RAFEQI_PHOTO_STORAGE` | `disk` (default, `data/uploads/`) or `database` (hosts that wipe the disk on deploy, like Render's free plan). |
| `RAFEQI_AI_ENABLED`, `ANTHROPIC_API_KEY` | AI texts (plan summary, weekly review). Off unless both are set. Limits: `RAFEQI_AI_RUNS_PER_WEEK`, `RAFEQI_AI_MONTHLY_LIMIT_USD`; models: `RAFEQI_AI_MODEL_PLAN`, `RAFEQI_AI_MODEL_REVIEW`. |
| `RAFEQI_TODAY` | Testing only, e.g. `2026-10-05`: the app acts as if today were that date (the browser tests use it). Ignored in production. |

## Exercise images and videos

- **Photos:** from the [Free Exercise DB](https://github.com/yuhonas/free-exercise-db) by yuhonas, released under the
  [Unlicense](https://github.com/yuhonas/free-exercise-db/blob/main/LICENSE.md). That makes them public domain: free to use, change and ship, with no attribution required. We credit it anyway on each exercise page.
  Each exercise has two photos (start and end position), which the app plays in a loop like a GIF. They're stored in
  `frontend/public/exercises/<Source_Id>/0.jpg, 1.jpg`. To add more: `node scripts/fetch-exercise-images.mjs Barbell_Squat Face_Pull`
  (IDs are the folder names in that repo's `exercises/` directory).
- **Videos:** for now, "Watch video" opens a YouTube search for "<exercise name> proper form". The real links will come from the Jeff Nippard program PDFs.

## Reading the books (`npm run books:extract`)

Phase A of `docs/PLAN-AI.md`: turns the PDFs in `Books/` into text and tables in `data/private/books/` (git-ignored:
the script refuses to run if it isn't). Runs only on your PC; nothing is uploaded.

One-time setup for the scanned books (OCR):

```powershell
scoop install tesseract        # the OCR program (no admin needed)
npm run books:extract          # downloads the Arabic + English OCR models into tools	essdata the first time
```

- `npm run books:extract` reads every book not done yet (about 5 minutes for all eight); `-- --force` redoes them,
  `-- --book diet-cheat-recipes --force` redoes one, `-- --report` only rewrites the summary.
- Per book, in `data/private/books/<NN>-<name>/`: `pages.jsonl` (one line per PDF page, with how it was read),
  `tables.jsonl` (rows and columns kept), `links.jsonl` (video links), `images/` (the recipe pages' cropped text, to
  check amounts by eye) and `meta.json`. `data/private/books/REPORT.md` is the summary.
- Page numbers are **PDF page numbers** (what a PDF viewer shows), so later citations can be checked in the PDF.
- The script is `scripts/books/extract.py` (its own dependencies, so the backend doesn't get PyMuPDF);
  its helpers are tested in `tests/backend/test_book_extract.py`, which also checks the private folders stay git-ignored.

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
- [x] Overnight fixes and additions (see `docs/OVERNIGHT-REPORT.md`): injury filtering and wording, back-friendly legs,
      swaps keep direction, editable equipment, a real lighter week, moving a session, logging each set, three source
      labels on "Why this plan"
- [x] Phase 6: progress photos (private), check-in questions from `data/checkin_questions.yaml`, weekly review, past
      reviews, progress charts, Profile & settings
- [x] Ready for friends on Render, prepared (PostgreSQL, production mode, invites, backups; `docs/DEPLOY.md`)
- [x] Books plan (`docs/PLAN-AI.md`) Phase A: the eight books read into `data/private/books/` (text, OCR, tables, links)
- [x] Books plan Phase B1: rule values from the books (calories, macros, warm-up, cardio, progression, deload, injuries,
      safety), with book and page; open questions in `data/REVIEW.md`
- [ ] Next: Phase B2 (the three Nippard programs and the exercise catalogue), then B3 (recipes and the foods table)
