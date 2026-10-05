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
  'V-Bar_Pulldown', 'Walking_Treadmill', 'Air_Bike', 'Barbell_Hip_Thrust', 'Bent_Over_Barbell_Row', 'Butterfly',
  'Cable_Crossover', 'Cable_One_Arm_Tricep_Extension', 'Cable_Rear_Delt_Fly', 'Cable_Seated_Lateral_Raise',
  'Close-Grip_Barbell_Bench_Press', 'Crunches', 'Dip_Machine', 'Dumbbell_Bicep_Curl', 'Dumbbell_Lunges',
  'EZ-Bar_Curl', 'Hammer_Curls', 'Hanging_Leg_Raise', 'Incline_Dumbbell_Press', 'Leverage_Incline_Chest_Press',
  'Lying_Dumbbell_Tricep_Extension', 'Lying_Leg_Curls', 'Lying_T-Bar_Row', 'One_Arm_Lat_Pulldown', 'Plank',
  'Reverse_Machine_Flyes', 'Romanian_Deadlift', 'Seated_Bent-Over_Rear_Delt_Raise', 'Seated_Cable_Rows',
  'Single-Leg_Leg_Extension', 'Single_Leg_Glute_Bridge', 'Standing_Biceps_Cable_Curl', 'Thigh_Abductor',
  'Underhand_Cable_Pulldowns', 'Wide-Grip_Lat_Pulldown',
  'Ab_Roller', 'Arnold_Dumbbell_Press', 'Ball_Leg_Curl', 'Barbell_Shrug', 'Cable_Rope_Overhead_Triceps_Extension',
  'Dips_-_Chest_Version', 'EZ-Bar_Skullcrusher', 'Front_Barbell_Squat', 'Hyperextensions_Back_Extensions',
  'Leverage_High_Row', 'Lying_Cambered_Barbell_Row', 'Monster_Walk', 'One_Arm_Dumbbell_Preacher_Curl', 'Pull_Through',
  'Reverse_Barbell_Curl', 'Smith_Machine_Close-Grip_Bench_Press', 'Spider_Curl', 'Straight-Arm_Pulldown',
  'Upright_Cable_Row',
  'Barbell_Incline_Bench_Press_-_Medium_Grip', 'Cable_Crunch', 'Floor_Press', 'Good_Morning', 'JM_Press', 'Leverage_Chest_Press',
  'Leverage_Iso_Row', 'Leverage_Shoulder_Press', 'Push_Press', 'Reverse_Hyperextension', 'Seated_Calf_Raise', 'Split_Squats',
  'Stiff-Legged_Barbell_Deadlift',
  'Bent-Arm_Dumbbell_Pullover', 'Bench_Dips', 'Standing_Dumbbell_Calf_Raise', 'Weighted_Sissy_Squat',
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
