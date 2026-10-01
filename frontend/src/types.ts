// Domain types shared by the mock data, the data layer and the screens.
// Anything the user reads that comes from the backend is LocalizedText so
// the API can return both languages (or the backend can pick one later).

export type Lang = 'en' | 'ar';
export type LocalizedText = { en: string; ar: string };
export type ISODate = string; // "2026-09-28"
export type Weekday = 'sat' | 'sun' | 'mon' | 'tue' | 'wed' | 'thu' | 'fri';

/** The one status language used across the app. */
export type Status = 'onTrack' | 'attention' | 'warning';

export type BodyRegion =
  | 'head' | 'neck' | 'chest' | 'abdomen' | 'upperBack' | 'lowerBack'
  | 'shoulderL' | 'shoulderR' | 'armL' | 'armR' | 'forearmL' | 'forearmR'
  | 'hipL' | 'hipR' | 'thighL' | 'thighR' | 'kneeL' | 'kneeR'
  | 'shinL' | 'shinR' | 'ankleL' | 'ankleR';

// ── User & questionnaire ─────────────────────────────────────────────
export type Goal = 'loseFat' | 'buildMuscle' | 'recomp' | 'strength';
export type Pace = 'gentle' | 'steady' | 'faster';
export type Experience = 'beginner' | 'intermediate' | 'advanced';
export type TrainingLocation = 'gym' | 'homeDumbbells' | 'bodyweight';
export type FastingHabit = 'ramadan' | 'intermittent';

export interface HealthAnswers {
  heartCondition: boolean;
  diabetes: boolean;
  pregnancy: boolean;
  recentSurgery: boolean;
  exerciseMedication: boolean;
}

export interface FoodPreferences {
  mealsPerDay: 2 | 3 | 4 | 5;
  dislikes: string[]; // food ids, see FOOD_OPTIONS
  allergies: string[];
  fasting: FastingHabit[];
  cookingMinutes: 15 | 30 | 60;
}

export interface User {
  id: string;
  firstName: LocalizedText;
  lastName: LocalizedText;
  email: string;
  sex: 'male' | 'female';
  age: number;
  heightCm: number;
  weightKg: number;
  waistCm?: number;
  goal: Goal;
  pace: Pace;
  experience: Experience;
  daysPerWeek: 2 | 3 | 4 | 5 | 6;
  sessionMinutes: 45 | 60 | 75 | 90;
  location: TrainingLocation;
  health: HealthAnswers;
  food: FoodPreferences;
  language: Lang;
  theme: 'light' | 'dark' | 'system';
  memberSince: ISODate;
}

/** What the onboarding questionnaire produces (also used to regenerate). */
export type QuestionnaireAnswers = Pick<User,
  'sex' | 'age' | 'heightCm' | 'weightKg' | 'waistCm' | 'goal' | 'pace' | 'experience' |
  'daysPerWeek' | 'sessionMinutes' | 'location' | 'health' | 'food'> & { injuries: InjuryInput[] };

// ── Plan ─────────────────────────────────────────────────────────────
export interface ExerciseSwap {
  injuryId: string;
  fromName: LocalizedText;
  toExerciseId: string;
  reason: LocalizedText;
}

export interface Plan {
  id: string;
  createdAt: ISODate;
  calories: number;
  maintenanceCalories: number;
  proteinG: number;
  carbsG: number;
  fatG: number;
  rationale: { calories: LocalizedText; protein: LocalizedText; carbs: LocalizedText; fat: LocalizedText };
  program: {
    name: LocalizedText;
    daysPerWeek: number;
    totalWeeks: number;
    currentWeek: number;
    why: LocalizedText;
    schedule: { day: Weekday; sessionId?: string }[];
  };
  injurySwaps: ExerciseSwap[];
  /** true when a health-check answer was "yes" → lighter loads, lower RPE. */
  conservative: boolean;
}

export type PlanGenerationStep = 'calories' | 'program' | 'injuries' | 'meals';

// ── Training ─────────────────────────────────────────────────────────
/** Where an exercise's demonstration media comes from (shown as a credit on the detail page). */
export interface MediaSource {
  name: string; // "Free Exercise DB"
  url: string;
  license: string; // "Unlicense (public domain)"
  note?: LocalizedText; // e.g. "Closest match: standing variation"
}

export interface Exercise {
  id: string;
  name: LocalizedText;
  /** One line: what the exercise is and what it trains. */
  description: LocalizedText;
  /** Demonstration image (start position); also used as the row thumbnail. */
  imageUrl?: string;
  /** Extra frames (e.g. end position) played in a loop like a GIF, after imageUrl. */
  imageFrames?: string[];
  /** Opens in a new tab. For now a YouTube search; real links come from the program PDFs. */
  videoUrl?: string;
  mediaSource?: MediaSource;
  muscles: { primary: BodyRegion[]; secondary: BodyRegion[] };
  muscleNames: LocalizedText;
  instructions: LocalizedText[];
  cues: LocalizedText[];
  mistakes: LocalizedText[];
  alternatives: { exerciseId?: string; name: LocalizedText; kind: 'easier' | 'injuryFriendly' | 'equipment' }[];
}

/**
 * One exercise's result. Logged in one tap ("Done as planned") or one row when something was different.
 * The backend stores it as one set_logs row per set, all with the same reps and weight.
 */
export interface ExerciseResult { sets: number; reps: number; weightKg: number; struggled: boolean }

export interface SessionExercise {
  exerciseId: string;
  sets: number;
  reps: string; // "8–10", "10 each side"
  restSec: number;
  rpe: number; // target effort (RPE)
  /** Planned weight per set. Missing for bodyweight exercises. */
  weightKg?: number;
  swap?: { injuryId: string; kind: 'swapped' | 'added' };
  lastTime?: ExerciseResult;
  weightStepKg?: number;
}

/** One training session ("Workout"). */
export interface Workout {
  id: string;
  name: LocalizedText;
  day: Weekday;
  date: ISODate;
  status: 'done' | 'today' | 'planned' | 'missed';
  estMinutes: number;
  warmupMinutes: number;
  exercises: SessionExercise[];
  summary?: { minutes: number; setsDone: number; setsTotal: number; painByInjury: Record<string, number> };
  /** What was logged, once the session is finished. */
  log?: WorkoutLog;
}

export interface WorkoutLog {
  /** "How hard was today's workout?" 1–10, asked once at the end. */
  effort: number;
  results: Record<string, ExerciseResult>; // by exerciseId; an exercise that was skipped has no entry
}

export interface WorkoutWeek {
  weekNumber: number;
  totalWeeks: number;
  start: ISODate;
  end: ISODate;
  deloadWeek: number;
  sessions: Workout[];
}

// ── Nutrition ────────────────────────────────────────────────────────
export type MealSlot = 'breakfast' | 'lunch' | 'snack' | 'dinner';

export interface Meal {
  id: string;
  slot: MealSlot;
  time: string; // "08:30"
  name: LocalizedText;
  portions: LocalizedText; // everyday Egyptian portions: "1 baladi bread", "1 ladle"
  kcal: number;
  proteinG: number;
  carbsG: number;
  fatG: number;
  recipeId?: string;
  eaten?: boolean;
}

export interface MealDay {
  date: ISODate;
  day: Weekday;
  isTrainingDay: boolean;
  meals: Meal[];
}

export interface MealWeekDay {
  date: ISODate;
  day: Weekday;
  kcal: number;
  main: LocalizedText;
  others: LocalizedText;
}

export interface Recipe {
  id: string;
  name: LocalizedText;
  photoUrl?: string;
  prepMin: number;
  cookMin: number;
  fridgeDays: number;
  kcal: number;
  proteinG: number;
  carbsG: number;
  fatG: number;
  /** Quantities are already scaled to the user's portion. */
  ingredients: { name: LocalizedText; grams?: number; amount: LocalizedText }[];
  steps: { text: LocalizedText; timerSec?: number }[];
  storage: LocalizedText;
  reheating: LocalizedText;
}

// ── Groceries ────────────────────────────────────────────────────────
export type GroceryCategory = 'produce' | 'meat' | 'dairy' | 'bakery' | 'pantry' | 'spices';
export type GroceryUnit = 'kg' | 'g' | 'L' | 'ml' | 'pcs' | 'loaves' | 'cups' | 'jars';

/** Generic item names only — never brands. */
export interface GroceryItem {
  id: string;
  name: LocalizedText;
  category: GroceryCategory;
  qty: number;
  unit: GroceryUnit;
  period: 'week' | 'month';
  checked: boolean;
  haveIt: boolean;
}

export interface GroceryList {
  weekNumber: number;
  start: ISODate;
  end: ISODate;
  changeNote?: LocalizedText; // shown when the plan update changed the list
  items: GroceryItem[];
}

export interface PantryItem {
  id: string;
  name: LocalizedText;
  level: 'plenty' | 'low' | 'untracked';
}

// ── Injuries ─────────────────────────────────────────────────────────
export type InjuryType = 'joint' | 'tendon' | 'strain' | 'sprain' | 'postSurgery' | 'unsure';
export type InjuryStatus = 'active' | 'recovering' | 'resolved';

export interface InjuryInput {
  region: BodyRegion;
  side: 'left' | 'right' | 'both' | 'none';
  type: InjuryType;
  severity: 1 | 2 | 3 | 4 | 5;
  painfulMovements: string[]; // movement ids, see MOVEMENT_OPTIONS
  restrictions: string[]; // restriction ids, see RESTRICTION_OPTIONS
}

export interface Injury extends InjuryInput {
  id: string;
  status: InjuryStatus;
  since: ISODate;
  painLog: { date: ISODate; pain: number }[];
  avoided: { from: LocalizedText; to: LocalizedText }[];
  redFlags: { sharpPain: boolean; swelling: boolean; numbness: boolean; worsening: boolean };
}

// ── Weekly check-in & review ─────────────────────────────────────────
export type Obstacle = 'work' | 'travel' | 'illness' | 'motivation' | 'fasting' | 'other';
export type Scale5 = 1 | 2 | 3 | 4 | 5;

export interface CheckIn {
  id: string;
  weekNumber: number;
  submittedAt?: string;
  body: {
    weightKg: number;
    measurementsCm: { waist?: number; hips?: number; chest?: number; arm?: number; thigh?: number };
    photos: { front?: string; side?: string; back?: string }; // private storage keys
  };
  training: {
    sessionsDone: number;
    sessionsPlanned: number;
    difficulty: Scale5;
    soreness: Scale5;
    exerciseFeedback: { exerciseId: string; feel: 'tooEasy' | 'tooHard' | 'uncomfortable' }[];
  };
  injuries: { injuryId: string; pain: number; trend: 'better' | 'same' | 'worse' }[];
  newPainRegions: BodyRegion[];
  redFlags: { sharpPain: boolean; swelling: boolean; numbness: boolean };
  nutrition: { adherencePct: number; hunger: Scale5; mealsToChange: string[]; moreOf: string[]; lessOf: string[] };
  life: { sleep: Scale5; energy: Scale5; stress: Scale5; daysAvailable: number; obstacles: Obstacle[] };
  note?: string; // max 300 characters
}

export interface ReviewChange {
  kind: 'calories' | 'exercise' | 'meals';
  what: LocalizedText;
  why: LocalizedText;
  citation: LocalizedText; // the book a recommendation comes from
}

export interface WeeklyReview {
  id: string;
  weekNumber: number;
  start: ISODate;
  end: ISODate;
  state: 'ready' | 'pending' | 'failed';
  status: Status;
  summary: LocalizedText;
  shortSummary: LocalizedText;
  stats: { weightChangeKg: number; sessionsDone: number; sessionsPlanned: number; pain?: number };
  changes: ReviewChange[];
  focus: LocalizedText[];
  groceryUpdate?: { note: LocalizedText };
}

// ── Body weight (one entry per day; the check-in weight is saved here too) ──
export interface WeightLog {
  id: string;
  date: ISODate;
  weightKg: number;
  source: 'daily' | 'checkin';
}

// ── Progress ─────────────────────────────────────────────────────────
export interface Progress {
  since: ISODate;
  weights: { date: ISODate; kg: number }[];
  measurements: { date: ISODate; waist: number; hips: number; chest: number; arm: number; thigh: number }[];
  lifts: { exerciseId: string; name: LocalizedText; unit: LocalizedText; points: { date: ISODate; kg: number }[] }[];
  records: { exerciseId: string; name: LocalizedText; date: ISODate; value: LocalizedText }[];
  photos: { date: ISODate; view: 'front' | 'side' | 'back'; url?: string }[];
}

// ── Dashboard (aggregated by the data layer) ────────────────────────
export interface Dashboard {
  user: User;
  plan: Plan;
  today: Workout | null;
  nextSession: Workout | null;
  mealDay: MealDay;
  nextCheckIn: { date: ISODate; due: boolean };
  injuries: Injury[];
  latestReview: WeeklyReview | null;
  weightAvgKg: number;
  /** Today's entry, if already logged (the dashboard's quick "log today's weight"). */
  weightToday: WeightLog | null;
  weightChangeKg: number;
}
