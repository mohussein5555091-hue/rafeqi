# Putting Rafeqi online for friends (Render + a free PostgreSQL)

This puts the whole app (screens and API) at one https address like `https://rafeqi.onrender.com`, with the data in a
free hosted PostgreSQL database, sign-up closed behind an invite code, and daily backups to your PC.
Nothing here costs money. Budget about 30–45 minutes the first time.

What runs where:

| Piece | Where | Free plan limits that matter |
|---|---|---|
| The app (built React screens + FastAPI) | Render, one "web service" running `Dockerfile` | Sleeps after 15 min with no visitors; the next visit takes about a minute to wake it. Its disk is wiped on every deploy. |
| The database | Neon (or Supabase), PostgreSQL | 0.5 GB on Neon's free plan: plenty for a few friends. |
| Progress photos | In the database (`RAFEQI_PHOTO_STORAGE=database`) | Because Render's disk is wiped. Photos are made smaller in the browser first (about 200–400 KB each). |
| Exercise photos | Inside the app image, served by the app itself | 6 MB in total, so **Cloudflare Pages isn't needed**. |

You need: your GitHub account with this repository, and an email address for Render and Neon.

---

## 1. Create the database (Neon)

1. Go to <https://neon.tech> → **Sign up** (GitHub login is easiest).
2. **Create project**: name `rafeqi`, PostgreSQL version **16**, region **AWS Europe (Frankfurt)**
   (the closest Neon region to Egypt). Leave everything else as it is.
3. On the project's **Dashboard**, find **Connection string**. Turn **Connection pooling** *off* (the app keeps its own
   few connections; either works, but the direct one is simpler). Copy the string. It looks like:

   ```
   postgresql://rafeqi_owner:AbCd1234@ep-cool-name-123456.eu-central-1.aws.neon.tech/rafeqi?sslmode=require
   ```

   Keep it secret: it is the password to everyone's data. Paste it somewhere private for step 2 (not in the repository).

> **Supabase instead?** Create a project (region: Frankfurt), then **Project Settings → Database → Connection string →
> URI**, choose **Session pooler** (port 5432), and put your database password into it. Everything else is the same.

## 2. Create the app on Render

1. Go to <https://render.com> → **Get started** → sign up with GitHub, and allow Render to see this repository.
2. **New +** → **Blueprint** → pick the `rafeqi` repository → branch **master**. Render reads `render.yaml` from the
   repository and shows one service, **rafeqi** (free, Docker).
3. It asks for the values marked "you paste it":

   | Name | What to put |
   |---|---|
   | `RAFEQI_DATABASE_URL` | the Neon connection string from step 1 (exactly as copied; `postgres://…` works too) |
   | `RAFEQI_INVITE_CODE` | a code you'll give your friends, e.g. `nile-2026` (capitals and spaces are ignored) |

   The others are filled in for you: `RAFEQI_ENV=production`, `RAFEQI_PHOTO_STORAGE=database`, and
   `RAFEQI_SECRET_KEY`, which Render generates as a long random value. (The app refuses to start in production without
   a real secret key.)
4. Click **Apply**. The first build takes 5–10 minutes (it builds the screens, then the backend). Watch **Logs**: at the
   end you see the migrations run, `Loaded 55 exercises, 32 foods, …` and `Uvicorn running`.
5. Open the address Render shows (e.g. `https://rafeqi.onrender.com`). Render handles https; plain http is redirected.

> **Region:** the Blueprint doesn't fix one. Choose **Frankfurt** when Render asks, so the app sits next to the database.

## 3. First visit

1. Open the address on your phone → **Sign up** → you'll see **Invite code**: type your code.
2. Add it to your home screen: **Android (Chrome):** menu ⋮ → **Install app** (or **Add to Home screen**).
   **iPhone (Safari):** Share → **Add to Home Screen**. It opens full screen with the Rafeqi icon.
3. Send friends the address and the invite code. Anyone without the code sees "That invite code isn't right".

To close sign-up completely, change `RAFEQI_INVITE_CODE` (Render → rafeqi → **Environment**) to something nobody knows.
To open it to anyone, delete the variable.

## 4. Updates

Every push to `master` redeploys automatically (`autoDeploy: true`). Database changes (migrations) and the exercise and
food catalogue are applied on every start, and only ever add or change; nobody's data is reset. The free service is
briefly unavailable during a deploy.

## 5. Reading feedback

People can use **Profile & settings → Send feedback**. On your PC, with the Neon string:

```bash
# Windows PowerShell
$env:RAFEQI_DATABASE_URL="postgresql://…neon.tech/rafeqi?sslmode=require"; npm run feedback
# Linux / macOS
RAFEQI_DATABASE_URL="postgresql://…" npm run feedback
```

## 6. Backups (daily, to your PC)

`npm run backup` saves every table (and photos) into one file in `backups/` (never committed) and keeps the newest 14.
It works the same for the local SQLite file and for Neon.

**Once by hand** (PowerShell, in the `rafeqi` folder):

```powershell
$env:RAFEQI_DATABASE_URL="postgresql://…neon.tech/rafeqi?sslmode=require"; npm run backup
```

You should see `Backed up N rows from 30 tables … to backups\rafeqi-2026-10-05T0300Z.json.gz`.

**Every day automatically (Windows Task Scheduler):**

1. Create `D:\rafeqi\backup.cmd` (use your real folder and string):

   ```bat
   @echo off
   cd /d D:\rafeqi
   set RAFEQI_DATABASE_URL=postgresql://…neon.tech/rafeqi?sslmode=require
   npm run backup -- --keep 30 >> backups\backup.log 2>&1
   ```

2. Start → **Task Scheduler** → **Create Basic Task** → name "Rafeqi backup" → **Daily**, 03:00 → **Start a program**
   → `D:\rafeqi\backup.cmd` → Finish. In its **Properties**, tick **Run whether user is logged on or not** and
   **Run task as soon as possible after a scheduled start is missed**.

(Linux/macOS: `crontab -e` and add `0 3 * * * cd ~/rafeqi && RAFEQI_DATABASE_URL="postgresql://…" npm run backup`.)

Neon also keeps its own short history (see **Branches → Restore** in Neon); the files on your PC are your own copy.

### Restoring

Restore only goes into an **empty** database (it refuses one that already has accounts, so two sets of data can never
mix). For example, to move everything into a new Neon database after an accident:

1. In Neon, create a new branch or project and copy its connection string.
2. On your PC:

   ```powershell
   npm run restore -- backups\rafeqi-2026-10-05T0300Z.json.gz --url "postgresql://…new…"
   ```

   It creates the tables (latest version), loads every row, and prints `Restored N rows …`.
3. In Render → rafeqi → **Environment**, set `RAFEQI_DATABASE_URL` to the new string → **Save** (it redeploys).

To try a backup locally instead: `npm run restore -- backups\….json.gz --url sqlite:///D:/rafeqi/data/restored.db`.

## 7. Running the production version on your PC (optional)

```bash
# in .env: RAFEQI_ENV=production and a long RAFEQI_SECRET_KEY (npm run setup already made one)
npm start            # builds the screens, migrates, then serves everything on http://localhost:8000
```

In production mode the app redirects plain http to https, so on your PC open it through a tunnel (`npm run tunnel`)
or keep `RAFEQI_ENV=development` for everyday use (`npm run dev`).

## 8. If something goes wrong

| What you see | What to do |
|---|---|
| Render build fails at `npm ci` or `uv sync` | Open **Logs**; usually a lockfile changed without being committed. Run `npm install` / `uv sync` locally, commit, push. |
| Logs say `RAFEQI_SECRET_KEY must be set…` | Render → Environment → add `RAFEQI_SECRET_KEY` with **Generate**. |
| Logs show `connection … failed` or `password authentication failed` | The database string is wrong or expired: copy it again from Neon. It must end with `?sslmode=require`. |
| The first page takes a minute | The free service was asleep. Normal on the free plan. |
| "That invite code isn't right" for everyone | Check `RAFEQI_INVITE_CODE` in Render → Environment. |
| Progress photos vanish after a deploy | `RAFEQI_PHOTO_STORAGE` must be `database` on Render. |

Secrets live only in Render's **Environment** page and in your private notes, never in the repository (`.env` is
git-ignored, and `render.yaml` only names the variables).
