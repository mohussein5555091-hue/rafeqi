// Option ids used by forms. Labels live in the translation files under `enums.*`.
import type { BodyRegion, Goal, Pace, Experience, TrainingLocation, InjuryType, Obstacle } from '@/types';

export const GOALS: Goal[] = ['loseFat', 'buildMuscle', 'recomp', 'strength'];
export const PACES: Pace[] = ['gentle', 'steady', 'faster'];
export const EXPERIENCE: Experience[] = ['beginner', 'intermediate', 'advanced'];
export const LOCATIONS: TrainingLocation[] = ['gym', 'homeDumbbells', 'bodyweight'];
export const INJURY_TYPES: InjuryType[] = ['joint', 'tendon', 'strain', 'sprain', 'postSurgery', 'unsure'];
export const MOVEMENTS = ['overheadPress', 'benchPress', 'dips', 'pullUps', 'lateralRaise', 'pushUps', 'squat', 'deadlift', 'lunges', 'running'] as const;
export const RESTRICTIONS = ['noOverhead', 'limitRange', 'noImpact', 'noHeavyLoad', 'noneSeen'] as const;
export const FOODS = ['liver', 'eggplant', 'okra', 'fish', 'mushrooms', 'lentils', 'beef', 'dairy'] as const;
export const ALLERGIES = ['none', 'nuts', 'lactose', 'gluten', 'eggs', 'shellfish', 'sesame'] as const;
export const MORE_LESS_FOODS = ['chicken', 'eggs', 'fish', 'beef', 'lentils', 'fruit', 'potatoes', 'rice', 'bread', 'tahini'] as const;
export const OBSTACLES: Obstacle[] = ['work', 'travel', 'illness', 'motivation', 'fasting', 'other'];
export const HEALTH_KEYS = ['heartCondition', 'diabetes', 'pregnancy', 'recentSurgery', 'exerciseMedication'] as const;
export const WEEKDAYS = ['sat', 'sun', 'mon', 'tue', 'wed', 'thu', 'fri'] as const;
export const NOTE_MAX = 300;

/** Regions offered as a chip list next to the body map (for precise 44px targets). */
export const REGION_LIST: BodyRegion[] = [
  'neck', 'shoulderL', 'shoulderR', 'upperBack', 'lowerBack', 'chest', 'abdomen', 'armL', 'armR',
  'forearmL', 'forearmR', 'hipL', 'hipR', 'thighL', 'thighR', 'kneeL', 'kneeR', 'shinL', 'shinR', 'ankleL', 'ankleR',
];

export const sideOf = (r: BodyRegion): 'left' | 'right' | 'none' => (r.endsWith('L') ? 'left' : r.endsWith('R') ? 'right' : 'none');
