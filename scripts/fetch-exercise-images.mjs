// Downloads exercise demonstration photos from the Free Exercise DB (public domain, Unlicense)
// into frontend/public/exercises/<Source_Id>/0.jpg, 1.jpg (start and end position).
// Usage: node scripts/fetch-exercise-images.mjs Dumbbell_Floor_Press Face_Pull …
//        (no arguments = every image used by data/catalogue/exercises.yaml)
import { mkdirSync, existsSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const BASE = 'https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises';
const OUT = fileURLToPath(new URL('../frontend/public/exercises', import.meta.url));
const DEFAULT = [
  'Arm_Circles', 'Band_Pull_Apart', 'Barbell_Bench_Press_-_Medium_Grip', 'Barbell_Deadlift', 'Barbell_Squat',
  'Bicycling_Stationary', 'Bodyweight_Squat', 'Bodyweight_Walking_Lunge', 'Butt_Lift_Bridge',
  'Calf_Stretch_Hands_Against_Wall', 'Cat_Stretch', 'Chest_And_Front_Of_Shoulder_Stretch', 'Childs_Pose',
  'Dumbbell_Bench_Press', 'Dumbbell_Floor_Press', 'Dumbbell_Incline_Row', 'Dumbbell_Shoulder_Press', 'Dumbbell_Step_Ups',
  'Dynamic_Chest_Stretch', 'Elliptical_Trainer', 'Face_Pull', 'Front_Leg_Raises', 'Goblet_Squat', 'Hamstring_Stretch',
  'Inchworm', 'Incline_Dumbbell_Curl', 'Inverted_Row', 'Kneeling_Hip_Flexor', 'Leg_Extensions', 'Leg_Press',
  'Middle_Back_Stretch', 'One-Arm_Dumbbell_Row', 'Overhead_Lat', 'Overhead_Triceps', 'Pullups', 'Pushups',
  'Quad_Stretch', 'Rope_Jumping', 'Seated_Biceps', 'Seated_Glute', 'Seated_Leg_Curl', 'Shoulder_Stretch',
  'Side_Lateral_Raise', 'Single-Arm_Linear_Jammer', 'Split_Squat_with_Dumbbells', 'Standing_Calf_Raises',
  'Standing_Hip_Circles', 'Standing_Military_Press', 'Stiff-Legged_Dumbbell_Deadlift', 'Triceps_Pushdown',
  'V-Bar_Pulldown', 'Walking_Treadmill',
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
