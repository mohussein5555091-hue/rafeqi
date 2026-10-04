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
