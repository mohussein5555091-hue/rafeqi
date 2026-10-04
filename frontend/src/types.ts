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
  /** The questionnaire is finished (until then every page leads back to it). */
  onboardingComplete: boolean;
  /** A plan has been built (after onboarding, until then the plan pages wait for it). */
  hasPlan: boolean;
}

/** What the onboarding questionnaire produces (also used to regenerate). The numbers start empty until typed. */
export type QuestionnaireAnswers = Pick<User,
  'sex' | 'waistCm' | 'goal' | 'pace' | 'experience' |
  'daysPerWeek' | 'sessionMinutes' | 'location' | 'health' | 'food'> & { age?: number; heightCm?: number; weightKg?: number; injuries: InjuryInput[] };

// ── Plan ─────────────────────────────────────────────────────────────
export interface ExerciseSwap {
  injuryId: string;
  /** The injured body area the swap is for. */
  region: BodyRegion;
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
    /** kind: what the day trains, for the week strip ("Upper" / "Lower" / "Full"). */
    schedule: { day: Weekday; sessionId?: string; kind?: 'upper' | 'lower' | 'full' }[];
  };
  injurySwaps: ExerciseSwap[];
  /** true when a health-check answer was "yes" → lighter loads, lower RPE. */
  conservative: boolean;
}

export type PlanGenerationStep = 'calories' | 'program' | 'injuries' | 'meals';

export type OnboardingStep = 'about' | 'goal' | 'training' | 'injuries' | 'health' | 'food' | 'review';
/** Backend: GET /api/onboarding. The answers so far, and the step to resume at. */
export interface OnboardingState { answers: QuestionnaireAnswers; step: OnboardingStep; completed: boolean }

// ── Training ─────────────────────────────────────────────────────────
/** Where an exercise's demonstration media comes from (shown as a credit on the detail page). */
export interface MediaSource {
  name: string; // "Free Exercise DB"
  url: string;
  license: string; // "Unlicense (public domain)"
  note?: LocalizedText; // e.g. "Closest match: standing variation"
}

/** strength: in the program · cardio · mobility: warm-up moves · stretch: cool-down. All have the same how-to page. */
export type ExerciseType = 'strength' | 'cardio' | 'mobility' | 'stretch';

export interface Exercise {
  id: string;
  type: ExerciseType;
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
  alternatives: { exerciseId?: string; name: LocalizedText; kind: 'easier' | 'injuryFriendly' | 'equipment' | 'noEquipment'; imageUrl?: string }[];
}

/**
 * One exercise's result. Logged in one tap ("Done as planned") or one row when something was different.
 * The backend stores it as one set_logs row per set, all with the same reps and weight.
 */
export interface ExerciseResult { sets: number; reps: number; weightKg: number; struggled: boolean }

/** Why the target is what it is (data/rules/progression.yaml). */
/** findWeight: an exercise the person swapped in, with no history yet: a light suggestion to find their weight. */
export type TargetReason = 'start' | 'addReps' | 'addWeight' | 'repeat' | 'dropWeight' | 'findWeight';
export interface Target { sets: number; reps: number; weightKg: number; reason: TargetReason }

export interface SessionExercise {
  exerciseId: string;
  sets: number;
  reps: string; // "8–10", "10 each side"
  restSec: number;
  rpe: number; // target effort (RPE)
  /** Changed for an injury (swapped / added), or swapped by the person (user) with their reason. */
  swap?: ExerciseSwapInfo;
  lastTime?: ExerciseResult;
  /** This session's exact target, from last time and the progression rules. "Done as planned" saves exactly this. */
  target: Target;
  weightStepKg?: number;
}

export type SwapReason = 'equipment' | 'busy' | 'cantDo' | 'pain';
export type ExerciseSwapInfo =
  | { kind: 'swapped' | 'added'; injuryId: string; region: BodyRegion }
  | { kind: 'user'; scope: 'today' | 'always'; reason: SwapReason; why: LocalizedText; fromExerciseId: string; swapId?: string };

/** An exercise to swap to: same movement and muscles, fits the equipment and injuries, with the target it starts at. */
export interface ExerciseAlternative { exerciseId: string; name: LocalizedText; imageUrl?: string; muscleNames: LocalizedText; target: Target }

/** A "from now on" swap in effect (can be undone from the exercise's page). */
export interface ActiveSwap {
  id: string; fromExerciseId: string; toExerciseId: string; reason: SwapReason; why: LocalizedText;
  fromName: LocalizedText; toName: LocalizedText; createdAt: string;
}

/** Before every session: easy movement, mobility moves for the day's muscles, then lighter sets of the first exercise. */
export interface Warmup {
  minutes: number;
  general?: { exerciseId: string; minutes: number };
  moves: { exerciseId: string; amount: LocalizedText }[];
  rampUp?: { exerciseId: string; sets: { pct: number; reps: number; weightKg: number }[] };
  /** Moves left out because they'd hurt an injury, with why. */
  skipped: { exerciseId: string; why: LocalizedText }[];
  done: boolean;
}

/** After every session: stretches for the muscles trained, then slow breathing. */
export interface Cooldown {
  minutes: number;
  stretches: { exerciseId: string; seconds: number; eachSide: boolean }[];
  breathing?: { exerciseId: string; minutes: number };
  done: boolean;
}

export interface CardioSession {
  exerciseId: string;
  minutes: number;
  intensity: 'easy' | 'moderate';
  intensityName: LocalizedText;
  when: 'restDay' | 'afterLifting';
  done?: { minutes: number };
}

/** One training session ("Workout"): lifting (strength), or a rest day with cardio. */
export interface Workout {
  id: string;
  kind: 'strength' | 'cardio';
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
  warmup?: Warmup;
  cooldown?: Cooldown;
  /** Cardio that day: after lifting, or the whole session on a rest day. */
  cardio?: CardioSession;
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
  cardio: { sessionsPerWeek: number; stepsPerDay: number; why: LocalizedText };
}

// ── Nutrition ────────────────────────────────────────────────────────
export type MealSlot = 'breakfast' | 'lunch' | 'snack' | 'dinner' | 'suhoor' | 'iftar'; // suhoor / iftar: Ramadan days

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
  /** What the meal is made of, after the person's removals and replacements (at this meal's portion). */
  ingredients?: MealIngredient[];
  /** The engine moved this portion to keep the day on target after an ingredient change. */
  portionChange?: { from: number; to: number };
}

// ── Removing an ingredient (backend/app/views/ingredients.py) ──
export type RemoveReason = 'dislike' | 'unavailable'; // "I don't like it" / "Not available right now"
export type RemoveScope = 'meal' | 'always'; // "Just this meal" / "Always"
export interface MealIngredient {
  foodId: string;
  name: LocalizedText;
  grams: number;
  amount: LocalizedText;
  /** What makes the dish: removing it means swapping the meal. */
  essential: boolean;
  status: 'kept' | 'removed' | 'replaced';
  replacement?: { foodId: string; name: LocalizedText; grams: number; amount: LocalizedText };
  change?: { reason: RemoveReason; scope: RemoveScope };
}
export interface IngredientReplacement { foodId: string; name: LocalizedText; grams: number; kcal: number; proteinG: number; carbsG: number; fatG: number }
export interface ReplacementOptions { foodId: string; name: LocalizedText; essential: boolean; role: string; options: IngredientReplacement[] }
/** What the engine changed on a day after an ingredient change, and a snack when portions couldn't close the gap. */
export interface DayNote {
  lines: LocalizedText[];
  snack: { recipeId: string; name: LocalizedText; portion: number; kcal: number; protein: number } | null;
  onTarget: boolean;
}

export interface MealDay {
  date: ISODate;
  day: Weekday;
  isTrainingDay: boolean;
  meals: Meal[];
  note?: DayNote;
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
  /** Quantities are already scaled to the user's portion. With a meal, each says if it was removed or replaced. */
  ingredients: (Pick<MealIngredient, 'name' | 'amount'> & Partial<MealIngredient>)[];
  /** The meal this recipe page belongs to (opened from its card): Remove / Undo act on it. */
  mealId?: string;
  mealDate?: ISODate;
  portion?: number;
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
  /** A red flag paused this area: no exercises for it until it's checked by a professional. */
  paused?: boolean;
}

// ── Weekly check-in & review ─────────────────────────────────────────
export type Obstacle = 'work' | 'travel' | 'illness' | 'motivation' | 'fasting' | 'other';
export type Scale5 = 1 | 2 | 3 | 4 | 5;

export interface CheckIn {
  id: string;
  weekNumber: number;
  submittedAt?: string;
  body: {
    weightKg?: number; // empty until typed (last week's weight is the placeholder)
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
  kind: 'calories' | 'exercise' | 'injury' | 'meals';
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
  /** Only what was measured that week. */
  measurements: { date: ISODate; waist?: number; hips?: number; chest?: number; arm?: number; thigh?: number }[];
  lifts: { exerciseId: string; name: LocalizedText; unit: LocalizedText; points: { date: ISODate; kg: number }[] }[];
  records: { exerciseId: string; name: LocalizedText; date: ISODate; value: LocalizedText }[];
  photos: { date: ISODate; view: 'front' | 'side' | 'back'; url?: string }[];
}

/** Backend: GET /api/checkins/draft. A check-in pre-filled from this week, with last week's numbers to compare. */
export interface CheckInDraft {
  draft: CheckIn;
  last: { weightKg: number; measurementsCm: Record<string, number> };
  mealOptions: { id: string; name: LocalizedText }[];
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

// ── "Why this plan" (GET /api/plan/why): every decision, built from the engine's stored reasons and the rule files ──
export type WhyGroupId = 'calories' | 'protein' | 'carbsFat' | 'program' | 'schedule' | 'volume' | 'startWeights' | 'progression'
  | 'deload' | 'warmup' | 'cooldown' | 'cardio' | 'exercises' | 'meals' | 'review';
/** One questionnaire answer a rule used. `key` is the answer's name (sex, weight_kg, injuries, checkin, …). */
export interface WhyAnswer { key: string; value: unknown }
/** Where a rule comes from. Placeholders aren't from a book yet: only `text` (what will be checked) is given. */
export interface WhySource { placeholder: boolean; text: string; book?: string; chapter?: string | null; page?: string; quote?: LocalizedText }
export interface WhyDecision {
  rule: string; group: WhyGroupId; context: LocalizedText | null; answers: WhyAnswer[];
  summary: LocalizedText; source: WhySource; result: LocalizedText;
}
export interface WhyPlan {
  planId: string; version: number; createdAt: string;
  aiSummary: LocalizedText | null; // written by the local LLM in the AI phase; null until then
  total: number; backed: number;
  groups: { id: WhyGroupId; decisions: WhyDecision[] }[];
}
