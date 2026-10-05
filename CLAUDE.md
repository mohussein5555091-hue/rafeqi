# Rafeqi · رفيقي — read this first

Rafeqi is a web app that acts as a personal trainer and nutritionist for people in Egypt, in English and Arabic (right-to-left).
It's a proof of concept: a good workout plan, a good Egyptian nutrition plan, and safe handling of injuries.
The owner is an AI engineer and QA/test-automation specialist who is new to web development. Explain things in plain
language, give exact commands, and add tests for everything.

The full plan is in [`docs/PLAN.md`](docs/PLAN.md). README.md has the longer user guide (Windows commands, phone testing,
database notes, the engine's rule table).

## Current phase

- Done: Phases 1–5 (setup, database + auth, onboarding questionnaire, plan engine, frontend connected to the backend),
  plus the updates listed at the end of `docs/PLAN.md` (warm-up, cool-down, cardio, exercise swaps, typed number
  inputs, session length and time estimate; whole exercise photos, the "Why this plan" page, removing ingredients).
  The sample data is gone from `frontend/` (the design reference in `design/` still has it).
- Done too: Phase 6 (progress photos stored privately, check-in questions from `data/checkin_questions.yaml`, review
  page, past reviews, progress charts, Profile & settings) and the overnight fixes in `docs/OVERNIGHT-REPORT.md`.
- The books and AI plan is **`docs/PLAN-AI.md`** (phases A–E; re-read it at the start of each of its phases).
  Done: Phase A (`npm run books:extract` → `data/private/books/`, git-ignored; README "Reading the books") and Phase B1
  (rule values from the books with `ref`; the rest stay `placeholder: true`; every conflict, mapping and gap in
  `data/REVIEW.md`). **Next: B2** (the three Nippard programs + exercise catalogue), then **B3** (recipes + foods table).
  The recipe book's Arabic digits OCR badly (٥ reads as "0", ٠ as "."): check every amount against
  `data/private/books/07-diet-cheat-recipes/images/`. The AI module exists (fake client, off by default).

Update this section and the Status list in README.md at the end of every phase.

## Rules (always)

1. **Read `docs/PLAN.md` before starting each phase.** Don't rely on memory or this summary.
2. **Commit at the end of every phase**, after all tests pass. Then stop: run the tests, say how to try it by hand, and list assumptions.
3. **Never commit** the books (`Books/`, `books/`, `*.pdf`), `.env`, the database (`data/*.db`, `*.sqlite3`), uploads
   (`data/uploads/`) or the book extracts (`data/private/`). `.gitignore` covers these. Check `git status` before every commit anyway.
   The untracked `design/palette-1b/` folder is the owner's private reference: leave it uncommitted.
4. **No prices, costs, budgets or brand names anywhere**: not in data, the API, or the UI. The grocery list uses generic
   names and amounts only. The catalogue loader rejects `price`/`cost`/`brand`/`budget` fields, and
   `tests/e2e/specs/every-page.spec.ts` checks every page.
5. **No chat with the AI.** Users never send free-form messages. The only inputs are the onboarding questionnaire,
   workout/pain logs, and the weekly check-in (fixed questions plus one optional note, max 300 characters).
   The LLM runs only after onboarding and after each weekly check-in.
6. **Every plan number comes from tested code** in `backend/app/engine/` (rules in `data/rules/*.yaml`), never from an LLM.
   The LLM only writes explanations and review text. Each number keeps a reason (EN + AR) with its rule and source.
7. Every user sees only their own data: every user table has `user_id` and every query filters by it.
   `tests/backend/test_isolation.py` must cover any new table or endpoint.
8. Keep the designed look exactly. `design/` is the read-only reference, so never edit it.
9. Tests must run without the books, the real database, `.env` or Ollama. Fake any LLM call in tests.
10. Every rule section in `data/rules/*.yaml` with an `explain` also has `summary` (plain language, EN + AR) and `uses`
    (the answers it reads); when a rule stops being a placeholder it needs `ref` (book, chapter, page, a 1–2 sentence
    quote). The "Why this plan" page is built from these, never from LLM text.

## Folder layout

```
backend/            Python 3.12 + FastAPI, SQLAlchemy 2, Alembic (managed by uv)
  app/api/          HTTP endpoints (auth, me, weights, onboarding, plans, training, nutrition, body)
  app/views/        Database rows → the screens' shapes (frontend/src/types.ts); app/week.py = "this week" of the plan
  app/engine/       The plan engine: nutrition, training, warmup (+ cool-down), cardio, injuries, meals (scipy MILP),
                    ingredients (replacements, day rebalancing), grocery, check-in, review
  app/views/why.py  "Why this plan": every stored reason + its rule's summary/uses/source/ref from data/rules/*.yaml
  app/models/       Database tables          app/schemas/  Request/response shapes (Pydantic)
  app/ai/           The AI layer: words around the engine's numbers (plan summary, weekly review); off unless enabled;
                    number check + template fallback; retrieval is an empty interface until the books phase
  migrations/       Alembic migrations (a test fails if models and migrations disagree)
frontend/           React + TypeScript + Vite + Tailwind; all data access goes through src/data/api.ts
data/               vocab/movements.yaml, catalogue/*.yaml, rules/*.yaml, programs/*.json, checkin_questions.yaml
                    (committed); rafeqi.db, uploads/ and private/ (book extracts) are private, never committed
docs/               PLAN.md (the plan), database.md (schema diagrams), personas.md (generated by npm run personas)
tests/backend/      pytest (personas.py = the 5 test personas)
tests/e2e/          Playwright (specs/)
scripts/            Helpers behind the npm commands (e2e-server.mjs, setup-env.mjs, lan.mjs, tunnel.mjs, …)
design/             Reference export from Claude Design. Never edited.
```

## Install, run, test

Needs **Node.js 20+**, **uv** (it installs Python 3.12 itself) and git. The same npm commands work on Windows and Linux.

```bash
# Linux only, if uv is missing:
curl -LsSf https://astral.sh/uv/install.sh | sh

npm run setup          # creates .env (random secret), installs everything, downloads Chromium, creates + seeds data/rafeqi.db
npm run dev            # app on http://localhost:5173, API docs at /api/docs (API itself on port 8000)
```

On a bare Linux machine Chromium also needs system libraries:
`(cd tests/e2e && npx playwright install --with-deps chromium)` (uses apt and needs root/sudo).
Without them, the backend tests and typecheck still work.

```bash
npm test               # everything: backend + typecheck + browser tests
npm run test:backend   # pytest only (about a minute)
npm run typecheck      # TypeScript only
npm run test:e2e       # Playwright only
npm run test:backend -- -k name                         # backend tests whose name matches
uv --directory backend run pytest ../tests/backend/test_plans.py -c pyproject.toml --rootdir .   # one file (needs -c / --rootdir)
```

How the tests stay independent of local files:
- **Backend (pytest):** `tests/backend/conftest.py` runs the real Alembic migrations into a temporary database once per run,
  then gives each test its own copy. Uploads go to a temporary folder and the clock is fixed. Nothing reads `data/rafeqi.db`
  or `.env`.
- **Browser (Playwright):** `scripts/e2e-server.mjs` deletes and recreates `tests/e2e/.data/` (ignored by git), migrates and
  seeds a fresh `e2e.db` there, then starts its own API on **8001** and web app on **5174**. It never touches
  `npm run dev` (8000/5173) or `data/rafeqi.db`. Ports 8001 and 5174 must be free.
  It sets `RAFEQI_TODAY=2026-10-05` (a Monday) and the browser clock to match (`test` from `specs/helpers.ts`).
  `auth.setup.ts` creates the shared read-only account; tests that change data call `freshUser(page)` for their own.
  Routes with ids are written as `/workouts/:today` etc. and filled in by `resolve()`.

Other commands: `npm run backup` / `npm run restore -- <file>`, `npm run feedback`, `npm run build` / `npm start`
(production mode; deploying: `docs/DEPLOY.md`). Backend tests on PostgreSQL: set `RAFEQI_TEST_POSTGRES_URL`.
`npm run db:migrate`, `npm run db:seed` (loads `data/catalogue/`, refuses on any bad tag/price/brand),
`npm run personas` (rewrites `docs/personas.md`), `npm run reset-password -- someone@example.com`.
Changing tables: edit `backend/app/models/`, then
`uv --directory backend run alembic revision --autogenerate -m "what changed"` and `npm run db:migrate`.
