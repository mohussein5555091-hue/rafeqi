# Overnight report

Work done unattended, in the priority order you gave. Each numbered item has its own commit (commit IDs are in the
"Done" list at the end). Decisions I made on my own are marked **Decision**; anything that needs you is under
"Needs your input".

Before starting:
- `docs/PLAN-AI.md` does not exist in the repository (not on `master` or this branch, not in the history). Item 18
  (the AI module) was therefore built from your description in the request and from `docs/PLAN.md`; see item 18.
- `npm run setup` could not download Playwright's Chromium in this cloud machine (the download host is blocked). The
  machine already has Chromium, so `tests/e2e/playwright.config.ts` now accepts `PW_CHROMIUM_PATH=/path/to/chromium`
  to use an installed browser. Nothing changes on your PC: without the variable it uses Playwright's own browser.

## Priority 1: bugs from your testing

### 1. Swapping an exercise and regenerating the plan ("Couldn't save")

- Checked through the real API (uvicorn on a fresh copy of the seeded database) with fresh accounts: beginner,
  intermediate and advanced; gym and home; no injury, lower back, left shoulder, right knee; every swap reason;
  "Just today" and "From now on"; then "Regenerate my plan". Every call succeeded.
- The one way I could make the app show "Couldn't save" from a swap: swapping on a **past** session. The server
  refuses it ("session is over"), but the Swap button was still offered in the logger. That's item 2, now fixed.
- New backend tests: a fresh account swaps for every reason (just today and from now on) and then regenerates; past and
  finished sessions refuse swaps.
- Found while checking: after several "From now on" swaps a session can lose an exercise (6 → 5). That's the session-length
  rule working as designed (a barbell exercise adds a ramp-up set, so the 6th exercise no longer fits in 60 minutes).
  After many "Equipment not available" swaps, a lower-body day can drop to 3 exercises because every machine was marked
  missing; item 7 (editable missing equipment) is the way back.

### 2. Past sessions

- No Swap button on a past (or finished) session, in the session page, the desktop side panel and the logger; the
  session says "Past sessions can't be changed." (Arabic too). The server refuses swaps on past or finished sessions
  for both scopes (409 `session_is_over`).

### 3. Workouts header

- The header shows the real program name ("Full body (sample) · week 1 of 8"), sent by the API as `programName`.

### 4. Warm-up injury filtering and the wording

- **Cause:** an injury's painful movements and restrictions ruled out matching exercises *whatever body part they
  load*. So "No overhead lifting" given for a lower back removed arm circles, and "deadlift hurts" removed the glute
  bridge (tagged as a hip hinge).
- **Fix (Decision):** every painful movement, and the restrictions "No overhead lifting" and "Limit range", now only
  rule out exercises that load the injured area's joints (`joint_of_injury: true` in `data/vocab/movements.yaml`).
  "No jumping or running" still applies whatever the area (impact jars the whole body).
  Result: lower back keeps arm circles, cat-cow and the glute bridge, loses the barbell squat, goblet squat, deadlifts and
  the standing overhead press; the leg press and split squat stay.
- **Tag review** of all 54 catalogue entries. Changed: barbell squat also loads the shoulder (the bar sits on it);
  goblet squat also loads the spine (the weight is held in front); jump rope also loads the spine (landing).
  Everything else looked right for the rules as they are.
- **Sentences:** each painful movement now has a phrase ("pressing overhead", "bending at the hips under load, like a
  deadlift"); restrictions are quoted. Examples:
  - "Not in your warm-up: Bodyweight squat. It involves squatting, which hurts your right knee."
  - "Not in your warm-up: Arm circles. It goes against the "No overhead lifting" restriction for your left shoulder."
  - "Barbell bench press → Floor press: Floor press avoids bench pressing, which hurts your left shoulder."
  Arabic versions for each (`training.yaml` `injuries.explain`, `warmup.explain`).
- Tests: `tests/backend/test_injury_rules.py` (lower back, shoulder, knee; every exercise, warm-up move and stretch in
  36 generated programs checked against the injury; every reason checked for being a full sentence).

### 5. Lower-back injury: back-friendly leg exercises; honest badges; ramp-up on the first compound lift

- With item 4, the leg press, split squat and (new) **dumbbell step-up** are no longer ruled out by a sore lower back;
  the barbell squat, goblet squat and deadlifts are.
- **Decision:** a leg exercise ruled out by an injury may now be replaced across the squat ↔ lunge patterns
  (`training.yaml` `injuries.related_patterns`, penalty `different_pattern: 2`), and replacing a loaded exercise with a
  bodyweight-only one costs `lose_load: 3`. So the barbell squat becomes the leg press at the gym, a step-up or split
  squat at home, and never the bodyweight squat while something loaded fits.
- New catalogue entry `ex_step_up` (photos from Free Exercise DB, public domain; starting load 0.1 × body weight per
  dumbbell, a marked placeholder like the others).
- "Added to support your …" is now "Added because of your …" (Arabic: "اتضاف بسبب …"), and it only appears on the
  leg exercise added because an injury ruled out the day's squat and hinge. An exercise the weekly review swapped
  because you marked it uncomfortable is now `review`, not `swapped`, so it no longer shows "Swapped for your <area>".
- Ramp-up sets go on the first main **compound** lift (two or more joints, with a weight): never a leg extension,
  curl or calf raise. The session screen uses the same rule.
- Tests in `tests/backend/test_injury_rules.py`.

### 6. Swap alternatives keep the movement direction and main muscles

- Alternatives with the same movement pattern come first, as before. When fewer than two exist, the extra ones must
  now have the **same direction** (`training.yaml` `swaps.directions`: push, pull, knee-dominant legs, hip-dominant legs,
  calves, core, carry) as well as a shared main muscle. So a curl is never offered a triceps pushdown and a leg
  extension is never offered a deadlift.
- Tests: `tests/backend/test_swap_alternatives.py` checks every strength exercise × 6 kinds of person × 4 reasons.

### 7. Missing equipment in Profile & settings; experience is required

- Profile & settings has a new "Equipment" row ("All available" / "1 missing") opening `/profile/equipment`: the
  equipment of your training place with a tick for each. Saving rebuilds the plan around it (meals and grocery list
  stay), and equipment that comes back also ends the "from now on" swaps that were made because it was missing.
  API: `GET/PUT /api/me/equipment` (added to the isolation test).
- The experience question starts with nothing picked; "Next" stays disabled with "Pick one to continue: it sets your
  program and starting weights." (**Decision:** required rather than a silent default, as you suggested.)
- **Note:** "Equipment not available" marks the whole equipment type as missing (e.g. every "Machine"), because the
  catalogue only knows equipment types, not individual machines. Untick it here to get them back.

### 8. Exercise images, the band pull-apart alternative, "Other equipment"

- Photos were already shown whole (object-fit: contain) since the previous update. Checked again with a new browser
  test that measures **every** photo on the session page (warm-up, exercises, cool-down), the logger, the swap sheet and
  three exercise pages, on desktop and phone size.
- The band pull-apart alternative has its photo through the API. The missing photo you saw is almost certainly a
  database seeded before the photos were added: the catalogue only reaches the database with `npm run db:seed`.
  **Decision:** `npm run dev` now runs `db:seed` too (it only updates the catalogue, never your data), so a pulled
  update always shows the current exercises and photos.
- "Other equipment" is now "Different equipment: dumbbells" / "Different equipment: cable machine" (Arabic: "أداة تانية:
  …"). The equipment comes from the catalogue entry, or from a new `equipment` field for alternatives that aren't in the
  catalogue yet (the loader refuses an "equipment" alternative without it). Migration `38c1e339409b` adds the column.

### Priority 1 extra: the planned lighter (deload) week is now real

- Before: the week view said "Week 5 is a lighter week" but nothing changed in week 5.
- Now, in the program's deload week (`deload_week` in the program file, 5 of 8 in both samples) every session has
  `sets_minus` fewer sets (never below 1) and a target effort `rpe_minus` lower (`training.yaml` `deload`, both 1,
  marked placeholders), and each exercise's target is **last time's weight and reps** (no progression step that week;
  target reason "Lighter week: same weight as last time"). The week after, progression picks up as usual.
- **Decision:** it's applied when the week is shown and logged (`views/training.py` `scheduled_deload`), because a plan
  version is one week that repeats; the plan itself isn't rebuilt for it. If a check-in already made the week lighter,
  it is not applied twice.
- Week view: in week 5 a box says "This is your lighter week: 1 set fewer and effort 1 lower on every exercise, at the
  same weights…" (or "…because your check-in said training felt very hard"); before week 5 the old line stays; after it,
  nothing. Session pages show a "Lighter week" chip. The "Why this plan" deload text now says "same weights" too.
- The check-in-triggered deload is unchanged.
- Tests: `test_the_planned_lighter_week_has_fewer_sets_lower_effort_and_the_same_weights`,
  `test_a_check_in_lighter_week_is_not_made_lighter_twice`. New `tests/backend/test_i18n.py` checks en/ar have the same keys.

**Priority 1 full run:** backend suite, typecheck and all 295 browser tests (desktop + phone) pass. The one backend
failure on the way (the face pull had no alternative without a cable once alternatives had to keep their direction) was
a tagging gap: the face pull now lists the upper back as a main muscle (it is: rear shoulders and upper back), so rows
are offered.

## Priority 2: logging

### 9. "Do this workout today" and "Move to another day"

- On an upcoming session of this week (status "planned"): **Do this workout today** and **Move to another day** (a sheet
  with every day from today to Friday; days that don't work are greyed out with why). A moved session says "Moved from
  Wednesday" and has "Back to Wednesday".
- Rules (`training.yaml` `reschedule`, placeholder, and `backend/app/engine/schedule.py`): only to today or later this
  week; not onto a day that already has a workout; two sessions that share a main muscle keep at least
  `min_rest_days: 1` full day between them. Examples with Upper/Lower: Upper B (Wed) can go to Tuesday or Friday; Lower B
  (Thu) can't go to Tuesday ("Too close to Lower body A on Monday: the same muscles need a rest day in between").
- **Decisions:** a move is stored per week and program weekday (`workout_moves`, migration `9c4a13242f74`), so it
  survives a plan rebuild that week and never leaks into the next week. Cardio stays on its own day. Only upcoming
  sessions move (not missed ones, as you specified; it would be easy to allow "Do this missed workout today" later).
  "Do this workout today" isn't offered when today already has a workout.
- API: `GET /api/workouts/{id}/move-options`, `POST /api/workouts/{id}/move {date}` (both in the isolation test).
- Tests: `tests/backend/test_move_workout.py`, browser test in `overnight-fixes.spec.ts`.

### 10. "Log each set" inside Edit

- In the logger's Edit, a **Log each set** switch turns the one row into one row per set, prefilled from the row (or
  from what was logged). Each set has its own reps and weight; "Add a set" / "Remove the last set". The saved result,
  the session page and "Last time" show each set ("10 × 22.5 kg, 9 × 22.5 kg, 10 × 20 kg").
- Stored in `set_logs` as one row per set with its own reps and weight (the table already allowed it; no migration).
  The API takes an optional `perSet` list; results come back with `perSet` when the sets differ.
- **Progression with real per-set values (Decision):** the weight is the heaviest one used; the reps are the fewest
  done at that weight; only sets at that weight count as "all planned sets done". So a lighter last set means "same
  weight again", and reps 10/9/8 means "one more rep than 8". Three new worked examples in
  `data/rules/progression_cases.json`.
- Tests: backend (`test_workout_logging.py`, `test_progression.py`) and a browser test.

**Priority 2 full run:** backend suite, typecheck and all 299 browser tests pass.

## Priority 3: "Why this plan"

### 11. Three source labels

- **What was counted as "from a book":** only the resting-burn formula (`nutrition.yaml` `bmr`, Mifflin-St Jeor). It
  isn't from your books: it's a standard formula from a journal article. It's now marked `kind: formula` and shows
  **"Standard formula"** with "Original source: American Journal of Clinical Nutrition… p. 241–247" and the quote.
- The three labels: **"From your books"** (a rule with `placeholder: false` and a `ref` to one of your books),
  **"Standard formula"** (`kind: formula`, original source shown), **"Not yet from a book"** (placeholders). The rule
  loader refuses any other `kind`, and a formula that is still a placeholder.
- So today: 0 rules from your books, 1 standard formula, everything else "Not yet from a book" (correct until the books
  phase).

### 12. Counting rules and decisions; grouping

- The top says "X of Y rules from your books · A of B decisions" (each rule counted once; Y is the rules this plan
  uses), plus "1 of the decisions use a standard formula, shown with its original source."
- Decisions that share a rule (a starting weight per exercise, one load reason per injured exercise…) are one card per
  section: the rule in plain language, the answers and the source once, and "N decisions use this rule" folded
  (`<details>`, closed by default); a rule used once still shows as a single decision card.
- API: every decision has `ruleKey` and `source.kind`; the page data has `rules {total, fromBooks, formulas}` and
  `formulas`.
- Tests: `test_why.py` (labels, counts, a rule from a book counts as from your books) and `why.spec.ts`.

**Priority 3 full run:** backend suite, typecheck and all 301 browser tests pass.

## Priority 4: Phase 6

### 13. Check-in, review, progress, profile

Already built and connected before tonight (checked, with their existing tests): the weekly review page with the
engine's changes and reasons (the AI text slot stays empty until the AI phase), past reviews, progress charts from real
data (weight entries with the 7-day average, measurements, strength per lift, personal records), and Profile & settings
(edit each questionnaire step, "Regenerate my plan", language, theme, change password, delete account). What was
missing, now done:

- **Progress photos** (front, side, back): picked in the check-in's first step, sent after the check-in is saved, made
  smaller in the browser first (at most 1600 px, JPEG). Stored on disk as `data/uploads/<user_id>/<checkin>-<view>.jpg`
  (git-ignored), never in a public folder; served only to their owner by `GET /api/photos/{checkin}/{view}` with
  `Cache-Control: private, no-store` (anyone else gets 404). Only real JPEG/PNG/WebP files (checked by their first
  bytes, not the file name) up to 8 MB. Sending one again replaces it. They show in Progress → Photos (compare first and
  latest), and deleting the account deletes the folder.
  **Decision:** the upload sends the image itself as the request body instead of a multipart form, so no new Python
  package is needed.
- **Questions from `data/checkin_questions.yaml`:** new `GET /api/checkins/questions`; the check-in screens now show
  each question's wording (English and Arabic) and use its ranges from the file (weight, measurements, note length).
  Changing the wording or a range in the file changes the screens with no code change. (The step layout and answer
  controls stay as designed.)
- Tests: `tests/backend/test_photos.py` (upload, privacy, bad files, size, listing, account deletion, the questions
  endpoint), isolation list updated, and a browser test that uploads a photo and checks another account can't see it.

**Priority 4 full run:** backend suite and typecheck pass; 301 of 303 browser tests passed on the first run. The 2
failures (desktop + phone, same test) were a real regression from using the file's wording: the measurement error read
"Waist (cm) must be between…". The tiles now drop the "(cm)" from the file's label; the test passes again.

## Priority 5: ready for friends on Render (prepared, not deployed)

### 14. PostgreSQL

- `RAFEQI_DATABASE_URL` in `.env` (or the host's environment) chooses the database; empty = the local SQLite file, as
  before. Hosted URLs as Neon/Supabase/Render give them (`postgres://…` or `postgresql://…`) are accepted as they are
  (the app adds the driver name). New dependency: `psycopg[binary]` (PostgreSQL driver). Connections are checked before
  use (hosted databases drop idle ones).
- **Tested on a real PostgreSQL 16 server in this machine:** all migrations up, all the way down and up again, and
  the **whole backend test suite** (opt-in: `RAFEQI_TEST_POSTGRES_URL=postgresql://postgres:…@localhost:5432/postgres
  npm run test:backend`; each test gets its own database copied from a migrated template). SQLite stays the default
  for tests.
- **Bugs this found** (SQLite never checks text lengths; PostgreSQL does): `plans.rules_version` was 40 characters
  for a 50-character value, and `program_exercises.swap_kind` was 8 for "equipment". Both widened (migration
  `ca0a41b6cb56`), with a test that the values fit.

### 15. Production mode

- `RAFEQI_ENV=production`: the backend serves the built React app (`npm run build` → `frontend/dist`) at the same
  address as the API (every non-`/api` path is a file from `dist` or the app itself, so links like `/workouts/…` work
  on reload). Hashed scripts are cached for a year, `index.html` never.
- **https only:** plain http is redirected to https (308), except `/api/health` for the host's health check; answers
  carry HSTS, `X-Content-Type-Options`, `X-Frame-Options: DENY` and `Referrer-Policy`. The session cookie is
  `Secure` (it already was in production) as well as `HttpOnly` and `SameSite=Lax`. Behind Render's proxy, uvicorn
  runs with `--proxy-headers` so the app sees the visitor's https.
- **Secret key from the environment:** in production the app refuses to start unless `RAFEQI_SECRET_KEY` is set to a
  random value of at least 32 characters.
- **Progress photos on a host with a wiped disk (Decision):** Render's free plan loses its disk on every deploy, so
  `RAFEQI_PHOTO_STORAGE=database` keeps photos in a `photo_blobs` table (migration `9ca9d581002d`) instead of
  `data/uploads/`. Same private API either way. Locally the default stays on disk, as in the plan.
- Tried for real here: a production server on port 8099 answered the app, an exercise photo and the API at one
  address, redirected http to https, and set a `Secure` cookie.
- `npm run start` builds the frontend and runs the backend in this mode on your PC (with `RAFEQI_ENV=production` and a
  secret in `.env`).
- Tests: `tests/backend/test_production.py`, `test_photos.py` (database storage).

### 16. Invite-only sign-up, "Send feedback", daily backups, installable app

- **Invite code:** set `RAFEQI_INVITE_CODE` (in `.env` or on Render). The sign-up form then shows "Invite code" and the
  server refuses sign-ups without the right code ("That invite code isn't right…"; spaces and capitals don't matter).
  Without the variable, sign-up stays open (as now, and as the tests use). `GET /api/auth/config` tells the form.
- **Send feedback:** Profile & settings → "Send feedback" (up to 1000 characters) → saved in a new `feedback` table
  (migration `a6147c496007`) with the page and time. It goes to you, never to the AI (this isn't chat with the
  coach). Read it with `npm run feedback`. Deleting an account deletes its feedback.
- **Backups:** `npm run backup` writes `backups/rafeqi-<date>.json.gz` (git-ignored) with every table and any photo
  files, keeping the newest 14 (`--keep`). It reads through SQLAlchemy, so it works the same on SQLite and PostgreSQL
  and needs no `pg_dump`. `npm run restore -- <file> [--url …]` upgrades the target to the latest schema, refuses a
  database that already has accounts, then loads everything. Tested: a backup restores row for row, and a backup taken
  from PostgreSQL restores into SQLite. Daily scheduling and restore steps: `docs/DEPLOY.md`.
- **Installable app:** the manifest and icons were already there (Phase 5). Added a small service worker
  (`frontend/public/sw.js`, registered only in the built app) so it opens quickly and offline shows the app instead of
  a browser error. It never stores anything from `/api`. Checked in Chromium against a production server: it registers
  and the manifest loads with its 192/512/maskable icons.
