// Starts the app for the Playwright tests with its own fresh database, so the tests never touch
// data/rafeqi.db and work on a machine that has no .env, no database and no books (e.g. a Linux CI box).
//
// Every run: deletes tests/e2e/.data/, creates an empty database there, migrates and seeds it,
// then starts the API on port 8001 and the web app on port 5174 (the normal `npm run dev`
// uses 8000/5173, so both can run at the same time).
// Playwright runs this for you (see tests/e2e/playwright.config.ts).
import { spawn, spawnSync } from 'node:child_process';
import { mkdirSync, rmSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const API_PORT = 8001;
const WEB_PORT = 5174;

const root = fileURLToPath(new URL('..', import.meta.url));
const dataDir = fileURLToPath(new URL('../tests/e2e/.data/', import.meta.url));

rmSync(dataDir, { recursive: true, force: true });
mkdirSync(`${dataDir}uploads`, { recursive: true });

// Environment variables win over .env, so a developer's .env can't point the tests at the real database.
const env = {
  ...process.env,
  RAFEQI_ENV: 'development',
  RAFEQI_SECRET_KEY: 'e2e-tests-only',
  RAFEQI_DATABASE_URL: `sqlite:///${dataDir.replaceAll('\\', '/')}e2e.db`,
  RAFEQI_UPLOADS_DIR: `${dataDir}uploads`,
  RAFEQI_BACKEND_URL: `http://127.0.0.1:${API_PORT}`,
};

for (const script of ['db:migrate', 'db:seed']) {
  const r = spawnSync('npm', ['run', script], { cwd: root, env, stdio: 'inherit', shell: true });
  if (r.status !== 0) process.exit(r.status ?? 1);
}

const api = `uv --directory backend run uvicorn app.main:app --host 127.0.0.1 --port ${API_PORT}`;
const web = `npm --prefix frontend run dev -- --port ${WEB_PORT}`;
const child = spawn('npx', ['concurrently', '-k', '-n', 'api,web', '-c', 'blue,magenta', `"${api}"`, `"${web}"`],
  { cwd: root, env, stdio: 'inherit', shell: true });
for (const sig of ['SIGINT', 'SIGTERM']) process.on(sig, () => child.kill(sig));
child.on('exit', (code) => process.exit(code ?? 0));
