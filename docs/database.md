# Rafeqi database

Generated from the schema review. Diagrams are Mermaid; VS Code and GitHub show them as pictures.

## Accounts, profile and injuries

Who you are, how you log in, your questionnaire answers, and your injuries with their pain history.

```mermaid
erDiagram
  users ||--o{ sessions : "logged in on"
  users ||--|| profiles : "answered"
  users ||--o{ injuries : "has"
  injuries ||--o{ pain_logs : "pain over time"
  users ||--o{ weight_logs : "weighs in"
  users {
    uuid id PK
    text email UK "stored lowercase"
    text password_hash "argon2id"
    text first_name
    text last_name
    text language "en or ar"
    text theme "light, dark or system"
    datetime adult_confirmed_at "ticked 18+ at sign-up"
    datetime created_at
    datetime last_login_at
  }
  sessions {
    uuid id PK
    uuid user_id FK
    text token_hash UK "SHA-256; raw token lives only in the cookie"
    datetime created_at
    datetime expires_at
    datetime last_seen_at
    datetime revoked_at "set on log out or password change"
    text user_agent
  }
  login_attempts {
    int id PK
    text email_hash "no user_id: may not be an account"
    text ip
    bool success
    datetime attempted_at
  }
  profiles {
    uuid user_id PK,FK "one row per user"
    text onboarding_step "where to resume"
    datetime completed_at "null until finished"
    text sex
    int age "18 to 90"
    real height_cm
    real weight_kg
    real waist_cm
    text goal
    text pace
    text experience
    int days_per_week
    int session_minutes
    text location "gym, homeDumbbells, bodyweight"
    int meals_per_day "2 to 5"
    int cooking_minutes
    json dislikes
    json allergies
    json fasting "ramadan, intermittent"
    bool heart_condition
    bool diabetes
    bool pregnancy
    bool recent_surgery
    bool exercise_medication
    bool conservative "true if any health answer is yes"
    datetime updated_at
  }
  injuries {
    uuid id PK
    uuid user_id FK
    text region "e.g. shoulderL"
    text side
    text type
    int severity "1 to 5"
    text status "active, recovering, resolved"
    json painful_movements "ids from vocab"
    json restrictions "ids from vocab"
    date since
    datetime paused_at "set by a red flag"
    datetime updated_at
  }
  pain_logs {
    uuid id PK
    uuid user_id FK
    uuid injury_id FK "null for new pain"
    text region
    int pain "0 to 10"
    bool sharp_pain
    bool swelling
    bool numbness
    bool worsening
    text source "workout or checkin"
    uuid workout_log_id FK
    uuid checkin_id FK
    datetime logged_at
  }
  weight_logs {
    uuid id PK
    uuid user_id FK "unique with date"
    date date "one row per person per day"
    real weight_kg "30 to 300"
    text source "daily or checkin"
    datetime updated_at
  }
```

## Plans and training

A plan is versioned: every change makes a new version and the old one stays for history. The program and its exercises hang off the plan, and your workout logs point back at them. Workouts are logged one result per exercise ("done as planned", or sets, reps and weight). Each result is saved as one `set_logs` row per set with the same reps and weight, and the session gets one effort rating. See `backend/app/workouts.py`.

```mermaid
erDiagram
  users ||--o{ plans : "has versions"
  plans ||--|| training_programs : "includes"
  training_programs ||--o{ program_days : "e.g. Upper A"
  program_days ||--o{ program_exercises : "in order"
  exercises ||--o{ program_exercises : "used in"
  exercises ||--o{ exercise_substitutions : "can be swapped for"
  program_days ||--o{ workout_logs : "done as"
  workout_logs ||--o{ set_logs : "sets"
  users ||--o{ workout_logs : "logs"
  plans {
    uuid id PK
    uuid user_id FK
    int version "unique with user_id"
    text status "active or superseded"
    text trigger "onboarding, checkin, regenerate"
    int calories
    int maintenance_calories
    int protein_g
    int carbs_g
    int fat_g
    bool conservative
    json reasons "one line per number, with its rule and source"
    json inputs "snapshot of the answers used"
    text rules_version
    datetime created_at
  }
  training_programs {
    uuid id PK
    uuid user_id FK
    uuid plan_id FK
    text template_id "file in data/programs"
    text name_en
    text name_ar
    int days_per_week
    int total_weeks
    int deload_week
    date start_date
  }
  program_days {
    uuid id PK
    uuid user_id FK
    uuid program_id FK
    int day_index
    text weekday
    text name_en
    text name_ar
    int est_minutes
    int warmup_minutes
  }
  program_exercises {
    uuid id PK
    uuid user_id FK
    uuid program_day_id FK
    text exercise_id FK
    int position
    int sets
    text reps "8-10, 10 each side"
    int rest_sec
    real target_rpe
    real load_factor "0.8 while recovering"
    real weight_step_kg
    real start_weight_kg "first session, no history yet"
    real weight_offset_kg "weekly review: one step, next session only"
    text replaced_exercise_id FK "what it swapped out"
    uuid injury_id FK "why it was swapped"
    json swap_reason
  }
  exercises {
    text id PK "slug, e.g. ex_face_pull"
    text name_en
    text name_ar
    text description_en "one line"
    text description_ar
    text movement_pattern "id from vocab"
    json joints_loaded "ids from vocab"
    text range_of_motion "id from vocab"
    json equipment "ids from vocab"
    text difficulty
    json primary_muscles
    json secondary_muscles
    json instructions "steps, en and ar"
    json cues "3 to 5"
    json mistakes
    text image_url
    json image_frames
    text video_url
    json media_source "name, url, license"
    text source "book and page"
  }
  exercise_substitutions {
    int id PK
    text exercise_id FK
    text substitute_id FK "null if not in catalogue yet"
    text name_en
    text name_ar
    text kind "easier, injuryFriendly, equipment"
    int priority
  }
  workout_logs {
    uuid id PK
    uuid user_id FK
    uuid plan_id FK
    uuid program_day_id FK
    int week_number
    date date
    text status "inProgress, done, skipped"
    int effort "how hard was today's workout, 1-10"
    datetime started_at
    datetime finished_at
  }
  set_logs {
    uuid id PK
    uuid user_id FK
    uuid workout_log_id FK
    text exercise_id FK
    int set_number
    int reps
    real weight_kg
    real rpe "10 on the last set if they struggled, else empty"
    datetime logged_at
  }
```

## Food, meals and groceries

Foods, recipes and grocery items form a shared catalogue. Your weekly meal plan picks recipes and scales portions. The grocery list is generated from it, minus your pantry. There are no prices or brands anywhere.

```mermaid
erDiagram
  foods ||--o{ recipe_ingredients : "used in"
  recipes ||--o{ recipe_ingredients : "made of"
  recipes ||--o{ recipe_steps : "cooked by"
  foods ||--o{ food_grocery_items : "bought as"
  grocery_items ||--o{ food_grocery_items : "covers"
  users ||--o{ meal_plans : "has"
  meal_plans ||--o{ meal_plan_items : "meals"
  recipes ||--o{ meal_plan_items : "chosen for"
  meal_plans ||--|| grocery_lists : "generates"
  grocery_lists ||--o{ grocery_list_items : "items"
  grocery_items ||--o{ grocery_list_items : "listed as"
  users ||--o{ pantry_items : "keeps at home"
  grocery_items ||--o{ pantry_items : "stocked as"
  foods {
    text id PK "slug"
    text name_en
    text name_ar
    real kcal_100g
    real protein_100g
    real carbs_100g
    real fat_100g
    real fiber_100g
    json units "1 baladi loaf = 90 g"
    json tags "for dislikes and allergies"
    text source
  }
  grocery_items {
    text id PK "slug, e.g. milk"
    text name_en "generic, never a brand"
    text name_ar
    text category
    text shelf_life "weekly or monthly"
    text buying_unit "kg, g, L, pcs"
    real pack_size "1 L, 1 kg, 30 eggs"
    real grams_per_unit "1 egg = 60 g"
  }
  food_grocery_items {
    text food_id PK,FK
    text grocery_item_id PK,FK
    real raw_grams_per_gram "cooked rice to dry rice = 0.4"
  }
  recipes {
    text id PK "slug"
    text name_en
    text name_ar
    json slots "breakfast, lunch, suhoor, iftar"
    int prep_min
    int cook_min
    int fridge_days
    int servings
    text storage_en
    text storage_ar
    text reheating_en
    text reheating_ar
    json tags
    text photo_url
    text source "book and page"
  }
  recipe_ingredients {
    int id PK
    text recipe_id FK
    text food_id FK
    real grams "per serving"
    text amount_en "1 ladle"
    text amount_ar
  }
  recipe_steps {
    int id PK
    text recipe_id FK
    int position
    text text_en
    text text_ar
    int timer_sec
  }
  meal_plans {
    uuid id PK
    uuid user_id FK
    uuid plan_id FK
    date week_start
    text status "active or superseded"
    datetime created_at
  }
  meal_plan_items {
    uuid id PK
    uuid user_id FK
    uuid meal_plan_id FK
    date date
    text slot
    text time
    text recipe_id FK
    real portion "scale factor from the optimizer"
    int kcal
    int protein_g
    int carbs_g
    int fat_g
    bool eaten
    text replaced_recipe_id FK
    json reason
  }
  grocery_lists {
    uuid id PK
    uuid user_id FK
    uuid meal_plan_id FK
    date week_start
    json change_note
    datetime created_at
  }
  grocery_list_items {
    uuid id PK
    uuid user_id FK
    uuid grocery_list_id FK
    text grocery_item_id FK
    text period "week or month"
    real grams_needed
    real qty "rounded up to packs"
    text unit
    bool checked
    bool have_it
  }
  pantry_items {
    uuid id PK
    uuid user_id FK
    text grocery_item_id FK "one row per item per user"
    text level "plenty, low, untracked"
    datetime updated_at
  }
```

## Check-ins, reviews and the AI log

The weekly check-in stores one row per answered question, so you can change the questions in YAML without touching the database. The review engine records every change it made and why. The AI text and its model are filled in next session.

```mermaid
erDiagram
  users ||--o{ checkins : "weekly"
  checkins ||--o{ checkin_answers : "one per question"
  checkins ||--o| weekly_reviews : "reviewed as"
  plans ||--o{ weekly_reviews : "before and after"
  weekly_reviews ||--o{ llm_calls : "text written by"
  users |o--o{ llm_calls : "for"
  checkins {
    uuid id PK
    uuid user_id FK
    int week_number
    date week_start "unique with user_id"
    text status "draft or submitted"
    datetime submitted_at
    real weight_kg "also written to weight_logs"
    real waist_cm
    real hips_cm
    real chest_cm
    real arm_cm
    real thigh_cm
    text photo_front_path "data/uploads/user_id/..."
    text photo_side_path
    text photo_back_path
    text note "optional, max 300 characters"
  }
  checkin_answers {
    uuid id PK
    uuid user_id FK
    uuid checkin_id FK
    text question_id "from data/checkin_questions.yaml"
    json value
    datetime answered_at
  }
  weekly_reviews {
    uuid id PK
    uuid user_id FK
    uuid checkin_id FK
    uuid plan_before_id FK
    uuid plan_after_id FK
    int week_number
    text state "pending, ready, failed"
    text status "onTrack, attention, warning"
    bool red_flag "skips the normal review"
    json changes "what, why, source"
    text ai_summary_en "next session"
    text ai_summary_ar
    json citations
    text model_used
    datetime created_at
  }
  llm_calls {
    uuid id PK
    uuid user_id FK "set to null when the account is deleted"
    uuid plan_id FK
    uuid weekly_review_id FK
    text task "plan_explanation or weekly_review"
    text model
    int prompt_tokens
    int completion_tokens
    int latency_ms
    real cost_usd "internal metric, never shown to users"
    text status
    text error
    datetime created_at
  }
```

## Later: smartwatches and fitness bands (not built yet)

```mermaid
erDiagram
  users ||--o{ device_connections : "links a watch or band"
  device_connections ||--o{ health_samples : "syncs"
  device_connections {
    uuid id PK
    uuid user_id FK
    text provider
    datetime connected_at
  }
  health_samples {
    uuid id PK
    uuid user_id FK
    text kind "steps, heart_rate, sleep"
    real value
    datetime start_at
    datetime end_at
  }
```

## Decisions

- **Two kinds of tables.** **Catalogue** tables (exercises, substitutions, foods, grocery items, recipes and their parts) are shared by everyone. They're read-only for users and loaded from files in `data/`, so their IDs are readable slugs like `ex_face_pull`. **User-data** tables hold one person's information: 19 tables plus `users`.
- **One controlled list of movement and joint tags.** `data/vocab/movements.yaml` holds every movement pattern, joint, range of motion, equipment item, painful movement and restriction, each labelled in English and Arabic. Injuries are checked against it when they're saved, the exercise catalogue when it's loaded, and a test checks that the frontend's option lists only use these ids.
- **user_id on every user row, including child rows.** A logged set already belongs to a workout that belongs to you. It still stores `user_id` itself, so every query is a plain `WHERE user_id = me` with no joins to get wrong. One helper applies it everywhere, and the isolation tests try user B's IDs on every endpoint.
- **Random IDs (UUIDs) for user data.** They can't be guessed by counting up from your own, and a future mobile app can create records offline and sync them later without clashes.
- **Deleting an account removes everything.** Every user table is deleted along with the user (`ON DELETE CASCADE`), and so is the `data/uploads/<user_id>/` photo folder. The exception is `llm_calls`: those rows stay with `user_id` set to null, so the monthly AI usage count stays correct. They hold counts and timings only, no personal content. A test checks that nothing else with that user_id is left.
- **Plans are never edited in place.** Onboarding creates version 1. Each weekly review or "regenerate my plan" creates the next version and marks the old one superseded. The review stores both, so you can always see what changed and why.
- **Sessions: only a fingerprint is stored.** The cookie holds a long random token. The database stores only its SHA-256 hash, so a copied database file can't be used to log in. Sessions last 30 days, and each visit extends them. Log out ends one session. Changing your password ends all the others.
- **Login rate limit that survives restarts.** Failed logins are written to `login_attempts`. After 5 failures for one email in 15 minutes, or 20 from one IP address, login is paused for that email or address. Old rows are deleted automatically.
- **Lists as JSON columns.** Short lists (tags, cues, allergies, reasons) are JSON. SQLAlchemy stores JSON the same way in SQLite and PostgreSQL, so switching databases stays a one-line config change.
- **Weight lives in one place.** `weight_logs` keeps one weight per person per day, from the dashboard's quick log or the weekly check-in. The progress chart's 7-day average and the weekly review's weight trend both read from it.
- **Arabic and English side by side.** Catalogue text is stored in `_en` and `_ar` column pairs. The API returns it as `{ en, ar }`, the `LocalizedText` type the screens already use.
- **What was removed.** No budget in the profile, no price on grocery items, no brands, and no units setting: the app is metric only. Exercises gain an image, extra frames, a video link, a one-line description, instructions, cues, mistakes and the media credit.
