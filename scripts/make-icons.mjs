// Draws the home-screen icons in frontend/public/icons/: the brand mark (Caprasimo "R", white on the indigo accent),
// with the test browser (Chromium from `npm run setup`). Needs internet once, for the font. Run: node scripts/make-icons.mjs
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const { chromium } = createRequire(new URL('../tests/e2e/package.json', import.meta.url))('@playwright/test');
const out = fileURLToPath(new URL('../frontend/public/icons/', import.meta.url));
const ACCENT = '#4B55A8'; // --color-accent in frontend/src/index.css

// Google Fonts sends just the one letter when asked with text=R.
const css = await (await fetch('https://fonts.googleapis.com/css2?family=Caprasimo&text=R', { headers: { 'User-Agent': 'Mozilla/5.0 Chrome/120' } })).text();
const font = Buffer.from(await (await fetch(css.match(/url\((https:[^)]+)\)/)[1])).arrayBuffer()).toString('base64');

// circle: the brand mark with see-through corners. square: full bleed, for "maskable" and Apple icons (the phone rounds them).
const html = (size, shape, scale) => `<!doctype html><style>
@font-face{font-family:Caprasimo;src:url(data:font/woff2;base64,${font}) format("woff2");font-display:block}
html,body{margin:0;background:transparent}
.i{width:${size}px;height:${size}px;background:${ACCENT};${shape === 'circle' ? 'border-radius:50%;' : ''}display:grid;place-items:center;
font-family:Caprasimo;color:#fff;font-size:${Math.round(size * scale)}px;line-height:1}</style><div class="i">R</div>`;

const browser = await chromium.launch();
const page = await browser.newPage();
for (const [name, size, shape, scale] of [
  ['icon-192.png', 192, 'circle', 0.56], ['icon-512.png', 512, 'circle', 0.56],
  ['icon-maskable-512.png', 512, 'square', 0.42], ['apple-touch-icon.png', 180, 'square', 0.5], ['favicon-32.png', 32, 'circle', 0.6],
]) {
  await page.setViewportSize({ width: size, height: size });
  await page.setContent(html(size, shape, scale));
  await page.evaluate(() => document.fonts.ready);
  await page.locator('.i').screenshot({ path: out + name, omitBackground: true });
  console.log(`frontend/public/icons/${name}`);
}
await browser.close();
