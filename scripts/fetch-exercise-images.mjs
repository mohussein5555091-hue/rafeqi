// Downloads exercise demonstration photos from the Free Exercise DB (public domain, Unlicense)
// into frontend/public/exercises/<Source_Id>/0.jpg, 1.jpg (start and end position).
// Usage: node scripts/fetch-exercise-images.mjs Dumbbell_Floor_Press Face_Pull …
//        (no arguments = the images used by the current sample exercises)
import { mkdirSync, existsSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const BASE = 'https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises';
const OUT = fileURLToPath(new URL('../frontend/public/exercises', import.meta.url));
const DEFAULT = [
  'Dumbbell_Floor_Press', 'Dumbbell_Incline_Row', 'Single-Arm_Linear_Jammer', 'V-Bar_Pulldown',
  'Face_Pull', 'Triceps_Pushdown', 'Incline_Dumbbell_Curl',
];

const ids = process.argv.slice(2).length ? process.argv.slice(2) : DEFAULT;
for (const id of ids) {
  mkdirSync(join(OUT, id), { recursive: true });
  for (const frame of ['0.jpg', '1.jpg']) {
    const dest = join(OUT, id, frame);
    if (existsSync(dest)) continue;
    const res = await fetch(`${BASE}/${id}/${frame}`);
    if (!res.ok) { console.error(`✗ ${id}/${frame}: HTTP ${res.status}`); process.exitCode = 1; continue; }
    writeFileSync(dest, Buffer.from(await res.arrayBuffer()));
    console.log(`✓ ${id}/${frame}`);
  }
}
