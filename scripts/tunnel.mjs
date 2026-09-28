// npm run tunnel → public https link to the running dev server (http://localhost:5173)
// through a free Cloudflare quick tunnel. No account needed. Ctrl+C closes the link.
// Anyone who has the link can open the site while this runs, so only run it while testing.
import { spawn } from 'node:child_process';
import { chmodSync, createWriteStream, existsSync, mkdirSync, renameSync } from 'node:fs';
import { get } from 'node:https';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const tools = join(root, 'tools');
const assets = { 'win32-x64': 'cloudflared-windows-amd64.exe', 'linux-x64': 'cloudflared-linux-amd64', 'linux-arm64': 'cloudflared-linux-arm64' };
const asset = assets[`${process.platform}-${process.arch}`];
const bin = join(tools, process.platform === 'win32' ? 'cloudflared.exe' : 'cloudflared');

function download(url, dest) {
  return new Promise((resolve, reject) => {
    get(url, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) return download(res.headers.location, dest).then(resolve, reject);
      if (res.statusCode !== 200) return reject(new Error(`Download failed: HTTP ${res.statusCode}`));
      const out = createWriteStream(`${dest}.part`);
      res.pipe(out);
      out.on('finish', () => out.close(() => { renameSync(`${dest}.part`, dest); resolve(); }));
    }).on('error', reject);
  });
}

if (!existsSync(bin)) {
  if (!asset) { console.error('Install cloudflared yourself (macOS: brew install cloudflared), then put it in tools/.'); process.exit(1); }
  mkdirSync(tools, { recursive: true });
  console.log(`Downloading ${asset} from Cloudflare's GitHub releases…`);
  await download(`https://github.com/cloudflare/cloudflared/releases/latest/download/${asset}`, bin);
  if (process.platform !== 'win32') chmodSync(bin, 0o755);
}

console.log('Opening tunnel to http://localhost:5173 (make sure `npm run dev` is running)…');
const child = spawn(bin, ['tunnel', '--no-autoupdate', '--url', 'http://localhost:5173'], { stdio: ['ignore', 'inherit', 'pipe'] });
let shown = false;
child.stderr.on('data', (buf) => {
  const text = buf.toString();
  const m = text.match(/https:\/\/[a-z0-9-]+\.trycloudflare\.com/);
  if (m && !shown) {
    shown = true;
    console.log(`\n  Open this on your phone:  ${m[0]}\n  (Ctrl+C here to close the link)\n`);
  }
  if (/ERR|error/i.test(text) && !/Cannot determine default origin certificate path/i.test(text)) process.stderr.write(text);
});
child.on('exit', (code) => process.exit(code ?? 0));
