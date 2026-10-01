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
npm run test:e2e       # Playwright only (starts the app for you if it isn't running)
```

After a Playwright run, `npm --prefix tests/e2e run report` opens the HTML report (with traces of any failures).

## Database and accounts

| Command | What it does |
|---|---|
| `npm run db:migrate` | Creates or updates the tables to the latest version (runs automatically with `npm run dev`). |
| `npm run db:seed` | Loads the catalogue from `data/catalogue/`. It refuses to load and lists every problem if any exercise uses a tag that isn't in `data/vocab/movements.yaml`. Safe to re-run. |
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

API endpoints so far (try them at http://localhost:5173/api/docs):
`POST /api/auth/signup`, `POST /api/auth/login`, `POST /api/auth/logout`, `POST /api/auth/change-password`,
`GET/PATCH/DELETE /api/me`, `GET/POST /api/weights`, `DELETE /api/weights/{id}`,
`GET /api/onboarding`, `PUT /api/onboarding/{about|goal|training|injuries|health|food}`, `POST /api/onboarding/complete`.

## Settings (.env)

`.env` is created by `npm run setup` and is never committed. The template is `.env.example`.

| Variable | Meaning |
|---|---|
| `RAFEQI_ENV` | `development` or `production` |
| `RAFEQI_SECRET_KEY` | Random secret, for anything that needs signing later |
| `RAFEQI_DATABASE_URL` | Optional. Defaults to SQLite at `data/rafeqi.db`. For PostgreSQL later, set this one line. |

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
- [ ] Phase 4: plan engine
- [ ] Phase 5: connect the frontend
- [ ] Phase 6: remaining screens
