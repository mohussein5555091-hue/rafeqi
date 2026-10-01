// Stand-in for backend/app/progression.py while the frontend runs on sample data (until Phase 5).
// Same rules (data/rules/progression.yaml); tests/e2e/specs/progression.spec.ts checks it against
// data/rules/progression_cases.json, the same worked examples the backend tests use.
import type { ExerciseResult, Target } from '../types';

const REPS_PER_STEP = 1; // progression.yaml: reps_per_step

/** "8–10" → [8, 10]; "15" or "10 each" → [15, 15] / [10, 10]. */
export function repRange(reps: string): [number, number] {
  const n = (reps.match(/\d+/g) ?? []).map(Number);
  if (!n.length) throw new Error(`no rep count in ${reps}`);
  return [n[0], n[1] ?? n[0]];
}

export function nextTarget(sets: number, reps: string, weightStepKg: number, startWeightKg: number, last?: ExerciseResult | null): Target {
  const [low, high] = repRange(reps);
  if (!last || last.sets === 0) return { sets, reps: low, weightKg: startWeightKg, reason: 'start' };
  const w = last.weightKg;
  if (last.struggled || last.sets < sets) {
    if (last.struggled && last.reps < low && weightStepKg > 0) return { sets, reps: low, weightKg: Math.max(0, w - weightStepKg), reason: 'dropWeight' };
    return { sets, reps: Math.min(Math.max(last.reps, low), high), weightKg: w, reason: 'repeat' };
  }
  if (last.reps >= high) {
    return weightStepKg > 0 ? { sets, reps: low, weightKg: w + weightStepKg, reason: 'addWeight' } : { sets, reps: high, weightKg: w, reason: 'repeat' };
  }
  return { sets, reps: Math.min(last.reps + REPS_PER_STEP, high), weightKg: w, reason: 'addReps' };
}
