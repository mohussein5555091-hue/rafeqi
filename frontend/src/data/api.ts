// The data layer. Every screen reads through these functions — swap the mock
// bodies for real HTTP calls (keep the signatures) to connect a backend.
import * as mock from '@/mocks/sampleData';
import { nextTarget } from '@/mocks/progression';
import type {
  CheckIn, Dashboard, Exercise, GroceryItem, GroceryList, Injury, InjuryInput, Meal, MealDay,
  MealWeekDay, PantryItem, Plan, PlanGenerationStep, Progress, QuestionnaireAnswers, Recipe,
  ExerciseResult, User, WeeklyReview, WeightLog, Workout, WorkoutLog, WorkoutWeek,
} from '@/types';

const wait = (ms = 250) => new Promise((r) => setTimeout(r, ms));
const clone = <T,>(v: T): T => structuredClone(v);

export class NotFoundError extends Error {
  constructor(what: string) { super(`${what} not found`); this.name = 'NotFoundError'; }
}

// In-memory state so the prototype feels real between screens.
let groceries = clone(mock.groceryList);
let injuryStore = clone(mock.injuries);
let mealDays = clone(mock.mealDays);
/** Adds each exercise's target, as the backend will (app/progression.py). */
const withTargets = (w: mock.PlannedWorkout): Workout => ({
  ...w,
  exercises: w.exercises.map(({ startWeightKg, ...e }) => ({ ...e, target: nextTarget(e.sets, e.reps, e.weightStepKg ?? 0, startWeightKg ?? 0, e.lastTime) })),
});
let workoutWeek: WorkoutWeek = { ...clone(mock.workoutWeek), sessions: mock.workoutWeek.sessions.map((s) => withTargets(clone(s))) };
let weightToday: WeightLog | null = null;

export const api = {
  // ── Auth ──
  async login(email: string, password: string): Promise<User> {
    await wait(400);
    if (!email.includes('@') || password.length < 8) throw new Error('invalid_credentials');
    return clone(mock.user);
  },
  async signup(input: { firstName: string; email: string; password: string }): Promise<User> {
    await wait(400);
    return { ...clone(mock.user), email: input.email, firstName: { en: input.firstName, ar: input.firstName } };
  },
  async requestPasswordReset(_email: string): Promise<void> { await wait(300); },
  async changePassword(_current: string, _next: string): Promise<void> { await wait(300); },
  async logout(): Promise<void> { await wait(100); },
  async deleteMyData(): Promise<void> { await wait(500); },

  // ── User & plan ──
  async getUser(): Promise<User> { await wait(); return clone(mock.user); },
  async updateUser(patch: Partial<User>): Promise<User> { await wait(); return { ...clone(mock.user), ...patch }; },
  async getPlan(): Promise<Plan> { await wait(); return clone(mock.plan); },
  /**
   * Plan generation runs on a local model and takes 30–90 s.
   * onStep is called as each stage finishes so the wait screen can show progress.
   */
  async generatePlan(_answers: QuestionnaireAnswers, onStep?: (step: PlanGenerationStep) => void): Promise<Plan> {
    for (const step of ['calories', 'program', 'injuries', 'meals'] as PlanGenerationStep[]) { await wait(900); onStep?.(step); }
    return clone(mock.plan);
  },

  // ── Dashboard ──
  async getDashboard(): Promise<Dashboard> {
    await wait();
    const avg = mock.progress.weights.slice(-7).reduce((a, w) => a + w.kg, 0) / 7;
    return {
      user: clone(mock.user),
      plan: clone(mock.plan),
      today: clone(workoutWeek.sessions.find((s) => s.date === mock.TODAY) ?? null),
      nextSession: clone(workoutWeek.sessions.find((s) => s.status === 'planned') ?? null),
      mealDay: clone(mealDays[mock.TODAY]),
      nextCheckIn: clone(mock.nextCheckIn),
      injuries: clone(injuryStore.filter((i) => i.status !== 'resolved')),
      latestReview: clone(mock.reviews.find((r) => r.weekNumber === 2) ?? null),
      weightAvgKg: Math.round(avg * 10) / 10,
      weightChangeKg: Math.round((avg - mock.progress.weights[0].kg) * 10) / 10,
      weightToday: clone(weightToday),
    };
  },

  // ── Body weight ──
  /** Saves today's weight (or corrects it: one entry per day). Backend: POST /api/weights. */
  async logWeight(weightKg: number): Promise<WeightLog> {
    await wait(300);
    weightToday = { id: weightToday?.id ?? 'w_today', date: new Date().toISOString().slice(0, 10), weightKg: Math.round(weightKg * 10) / 10, source: 'daily' };
    return clone(weightToday);
  },

  // ── Training ──
  async getWorkoutWeek(): Promise<WorkoutWeek> { await wait(); return clone(workoutWeek); },
  async getWorkout(id: string): Promise<Workout> {
    await wait();
    const s = workoutWeek.sessions.find((x) => x.id === id);
    if (!s) throw new NotFoundError('workout');
    return clone(s);
  },
  async getExercise(id: string): Promise<Exercise> {
    await wait();
    const e = mock.exercises.find((x) => x.id === id);
    if (!e) throw new NotFoundError('exercise');
    return clone(e);
  },
  async getExercises(): Promise<Exercise[]> { await wait(100); return clone(mock.exercises); },
  /**
   * Saves one exercise's result as soon as it's tapped (null = undo). Logging again replaces it.
   * Backend: one set_logs row per set, all with the same reps and weight (backend/app/workouts.py).
   */
  async logExercise(_workoutId: string, _exerciseId: string, _result: ExerciseResult | null): Promise<void> { await wait(150); },
  /** Exercises missing from log.results were skipped. Backend: finish_workout() also stores the effort rating. */
  async finishWorkout(workoutId: string, log: WorkoutLog, painByInjury: Record<string, number>, _redFlags: string[]): Promise<void> {
    await wait(300);
    const results = Object.values(log.results);
    workoutWeek = {
      ...workoutWeek,
      sessions: workoutWeek.sessions.map((s) => (s.id !== workoutId ? s : {
        ...s, status: 'done', log: clone(log),
        summary: { minutes: s.estMinutes, setsDone: results.reduce((a, r) => a + r.sets, 0), setsTotal: s.exercises.reduce((a, e) => a + e.sets, 0), painByInjury },
      })),
    };
  },

  // ── Nutrition ──
  /** One date's meals (today when no date). */
  async getMealDay(date: string = mock.TODAY): Promise<MealDay> {
    await wait();
    const d = mealDays[date];
    if (!d) throw new NotFoundError('meal day');
    return clone(d);
  },
  async getMealWeek(): Promise<MealWeekDay[]> { await wait(); return clone(mock.mealWeek); },
  async getSwapOptions(mealId: string): Promise<Meal[]> { await wait(); return clone(mock.swapOptions[mealId] ?? []); },
  async swapMeal(date: string, mealId: string, replacement: Meal): Promise<MealDay> {
    await wait();
    const d = mealDays[date];
    if (!d) throw new NotFoundError('meal day');
    mealDays = { ...mealDays, [date]: { ...d, meals: d.meals.map((m) => (m.id === mealId ? { ...replacement, time: m.time } : m)) } };
    return clone(mealDays[date]);
  },
  async getRecipe(id: string): Promise<Recipe> {
    await wait();
    const r = mock.recipes.find((x) => x.id === id);
    if (!r) throw new NotFoundError('recipe');
    return clone(r);
  },

  // ── Groceries ──
  async getGroceryList(): Promise<GroceryList> { await wait(); return clone(groceries); },
  async updateGroceryItem(id: string, patch: Partial<Pick<GroceryItem, 'checked' | 'haveIt'>>): Promise<GroceryList> {
    groceries = { ...groceries, items: groceries.items.map((i) => (i.id === id ? { ...i, ...patch } : i)) };
    return clone(groceries);
  },
  async getPantry(): Promise<PantryItem[]> { await wait(); return clone(mock.pantry); },

  // ── Injuries ──
  async getInjuries(): Promise<Injury[]> { await wait(); return clone(injuryStore); },
  async getInjury(id: string): Promise<Injury> {
    await wait();
    const i = injuryStore.find((x) => x.id === id);
    if (!i) throw new NotFoundError('injury');
    return clone(i);
  },
  async saveInjury(input: InjuryInput & { id?: string; status?: Injury['status'] }): Promise<Injury> {
    await wait();
    const existing = input.id ? injuryStore.find((x) => x.id === input.id) : undefined;
    const next: Injury = existing
      ? { ...existing, ...input, id: existing.id }
      : { ...input, id: `inj_${Date.now()}`, status: input.status ?? 'active', since: mock.TODAY, painLog: [], avoided: [], redFlags: { sharpPain: false, swelling: false, numbness: false, worsening: false } };
    injuryStore = existing ? injuryStore.map((x) => (x.id === next.id ? next : x)) : [...injuryStore, next];
    return clone(next);
  },
  async deleteInjury(id: string): Promise<void> { await wait(); injuryStore = injuryStore.filter((x) => x.id !== id); },

  // ── Check-in & reviews ──
  async getCheckInDraft(): Promise<{ draft: CheckIn; last: typeof mock.lastCheckIn; mealOptions: typeof mock.checkInMealOptions }> {
    await wait();
    return { draft: clone(mock.checkInDraft), last: clone(mock.lastCheckIn), mealOptions: clone(mock.checkInMealOptions) };
  },
  /** Returns the id of the review that will be written (30–90 s on the backend). */
  async submitCheckIn(_checkIn: CheckIn): Promise<{ reviewId: string }> { await wait(500); return { reviewId: 'rv_w3' }; },
  async getReviews(): Promise<WeeklyReview[]> { await wait(); return clone(mock.reviews); },
  async getReview(id: string): Promise<WeeklyReview> {
    await wait();
    const r = mock.reviews.find((x) => x.id === id);
    if (!r) throw new NotFoundError('review');
    return clone(r);
  },

  // ── Progress ──
  async getProgress(): Promise<Progress> { await wait(); return clone(mock.progress); },
};

export type Api = typeof api;
