// Creates .env from .env.example with a fresh random secret. Never overwrites an existing .env.
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { randomBytes } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const env = `${root}.env`;

if (existsSync(env)) {
  console.log('.env already exists — leaving it unchanged.');
} else {
  const secret = randomBytes(48).toString('base64url');
  const text = readFileSync(`${root}.env.example`, 'utf8').replace('RAFEQI_SECRET_KEY=replace-me', `RAFEQI_SECRET_KEY=${secret}`);
  writeFileSync(env, text);
  console.log('Created .env with a new random secret key.');
}
