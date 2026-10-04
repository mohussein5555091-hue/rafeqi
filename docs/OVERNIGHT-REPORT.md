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
