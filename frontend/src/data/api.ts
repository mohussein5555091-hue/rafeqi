// The data layer. Every screen reads through these functions, which call the FastAPI backend under /api
// (the Vite dev server forwards /api to it, so the session cookie stays on one origin).
// The function names and types are the same ones the screens were designed against.
import type {
  CheckIn, CheckInDraft, Dashboard, Exercise, ExerciseResult, GroceryItem, GroceryList, Injury, InjuryInput, InjuryStatus, LocalizedText,
  Meal, MealDay, MealWeekDay, OnboardingState, OnboardingStep, PantryItem, Plan, PlanGenerationStep, Progress, QuestionnaireAnswers,
  Recipe, User, Weekday, ActiveSwap, ExerciseAlternative, SwapReason, WeeklyReview, WeightLog, Workout, WorkoutLog, WorkoutWeek,
} from '@/types';

export class NotFoundError extends Error {
  constructor(what: string) { super(`${what} not found`); this.name = 'NotFoundError'; }
}

/** Any other answer that isn't OK. `message` is the backend's error code, e.g. "email_taken". */
export class ApiError extends Error {
  constructor(public status: number, public detail: unknown) {
    super(typeof detail === 'string' ? detail : `request failed (${status})`);
    this.name = 'ApiError';
  }
}

/** Fired when the session has ended (logged out elsewhere, expired): the app goes back to Log in. */
export const UNAUTHORIZED_EVENT = 'rafeqi:unauthorized';

async function request<T>(method: string, path: string, body?: unknown, { authCheck = true } = {}): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    credentials: 'same-origin',
    headers: body === undefined ? { Accept: 'application/json' } : { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.ok) return (res.status === 204 ? undefined : await res.json()) as T;
  const detail = await res.json().then((j) => j?.detail, () => undefined);
  if (res.status === 401 && authCheck) window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  if (res.status === 404) throw new NotFoundError(path);
  throw new ApiError(res.status, detail);
}
const get = <T,>(path: string) => request<T>('GET', path);
const send = <T,>(method: 'POST' | 'PUT' | 'PATCH' | 'DELETE', path: string, body?: unknown) => request<T>(method, path, body);

// ── Backend shapes that differ from the screens' types (everything else is already the screens' shape) ──

interface MeOut {
  id: string; email: string; firstName: string; lastName: string; language: User['language']; theme: User['theme'];
  memberSince: string; onboardingComplete: boolean; hasPlan: boolean;
}
interface OnboardingOut {
  step: OnboardingStep; completed: boolean; missing: string[]; conservative: boolean;
  about: Pick<QuestionnaireAnswers, 'sex' | 'age' | 'heightCm' | 'weightKg'> & { waistCm: number | null } | null;
  goal: Pick<QuestionnaireAnswers, 'goal' | 'pace'> | null;
  training: Pick<QuestionnaireAnswers, 'experience' | 'daysPerWeek' | 'sessionMinutes' | 'location'> | null;
  injuries: (InjuryInput & { id: string; status: InjuryStatus })[];
  injuriesAnswered: boolean;
  health: QuestionnaireAnswers['health'] | null;
  food: QuestionnaireAnswers['food'] | null;
}
interface ReasonOut { rule: string; en: string; ar: string; source: string }
interface PlanOut {
  id: string; createdAt: string; calories: number; maintenanceCalories: number; proteinG: number; carbsG: number; fatG: number;
  conservative: boolean; reasons: Record<string, ReasonOut[]>;
  program: null | {
    name: LocalizedText; daysPerWeek: number; totalWeeks: number; currentWeek: number;
    days: {
      id: string; weekday: Weekday; name: LocalizedText;
      exercises: { exerciseId: string; replacedName: LocalizedText | null; injuryId: string | null; injuryRegion: Injury['region'] | null;
        swapKind: string | null; reasons: ReasonOut[] }[];
    }[];
  };
}

const WEEK: Weekday[] = ['sat', 'sun', 'mon', 'tue', 'wed', 'thu', 'fri'];
const CARDIO = 'cardio-';

/** Shown in the questionnaire until the person changes them. Age, height and weight start empty (typed in). */
const DEFAULT_ANSWERS: QuestionnaireAnswers = {
  sex: 'male', goal: 'loseFat', pace: 'steady', experience: 'intermediate', daysPerWeek: 4,
  sessionMinutes: 60, location: 'gym', injuries: [],
  health: { heartCondition: false, diabetes: false, pregnancy: false, recentSurgery: false, exerciseMedication: false },
  food: { mealsPerDay: 4, dislikes: [], allergies: ['none'], fasting: [], cookingMinutes: 30 },
};

function toAnswers(o: OnboardingOut): QuestionnaireAnswers {
  const d = DEFAULT_ANSWERS;
  const about = o.about ? { ...o.about, waistCm: o.about.waistCm ?? undefined } : {};
  return {
    ...d, ...about, ...(o.goal ?? {}), ...(o.training ?? {}),
    injuries: o.injuries.map(({ region, side, type, severity, painfulMovements, restrictions }) => ({ region, side, type, severity, painfulMovements, restrictions })),
    health: o.health ?? d.health,
    food: o.food ?? d.food,
  } as QuestionnaireAnswers;
}

const toState = (o: OnboardingOut): OnboardingState => ({ answers: toAnswers(o), step: o.step, completed: o.completed });

function toUser(me: MeOut, o: OnboardingOut): User {
  const a = toAnswers(o);
  return {
    ...a, age: a.age ?? 0, heightCm: a.heightCm ?? 0, weightKg: a.weightKg ?? 0, // filled in once the questionnaire's first step is saved
    id: me.id, email: me.email, firstName: { en: me.firstName, ar: me.firstName }, lastName: { en: me.lastName, ar: me.lastName },
    language: me.language, theme: me.theme, memberSince: me.memberSince, onboardingComplete: me.onboardingComplete, hasPlan: me.hasPlan,
  };
}

const both = (lines: ReasonOut[] = []): LocalizedText => ({ en: lines.map((r) => r.en).join(' '), ar: lines.map((r) => r.ar).join(' ') });

const dayKind = (name: LocalizedText): 'upper' | 'lower' | 'full' =>
  (/upper/i.test(name.en) ? 'upper' : /lower/i.test(name.en) ? 'lower' : 'full');

function toPlan(p: PlanOut): Plan {
  const days = p.program?.days ?? [];
  const swaps = new Map<string, Plan['injurySwaps'][number]>();
  for (const e of days.flatMap((d) => d.exercises)) {
    if (e.swapKind !== 'swapped' || !e.injuryId || !e.injuryRegion || !e.replacedName || swaps.has(e.exerciseId)) continue;
    const why = e.reasons.find((r) => r.rule === 'training.injuries') ?? e.reasons[0];
    swaps.set(e.exerciseId, { injuryId: e.injuryId, region: e.injuryRegion, fromName: e.replacedName, toExerciseId: e.exerciseId,
      reason: why ? { en: why.en, ar: why.ar } : { en: '', ar: '' } });
  }
  return {
    id: p.id, createdAt: p.createdAt.slice(0, 10), calories: p.calories, maintenanceCalories: p.maintenanceCalories,
    proteinG: p.proteinG, carbsG: p.carbsG, fatG: p.fatG, conservative: p.conservative,
    rationale: { calories: both(p.reasons.calories), protein: both(p.reasons.protein), carbs: both(p.reasons.carbs), fat: both(p.reasons.fat) },
    program: {
      name: p.program?.name ?? { en: '', ar: '' }, daysPerWeek: p.program?.daysPerWeek ?? 0, totalWeeks: p.program?.totalWeeks ?? 0,
      currentWeek: p.program?.currentWeek ?? 1, why: both(p.reasons.training),
      schedule: WEEK.map((day) => {
        const d = days.find((x) => x.weekday === day);
        return d ? { day, sessionId: d.id, kind: dayKind(d.name) } : { day };
      }),
    },
    injurySwaps: [...swaps.values()],
  };
}

const ONBOARDING_BODY: Record<Exclude<OnboardingStep, 'review'>, (a: QuestionnaireAnswers) => unknown> = {
  about: (a) => ({ sex: a.sex, age: a.age, heightCm: a.heightCm, weightKg: a.weightKg, waistCm: a.waistCm ?? null }),
  goal: (a) => ({ goal: a.goal, pace: a.pace }),
  training: (a) => ({ experience: a.experience, daysPerWeek: a.daysPerWeek, sessionMinutes: a.sessionMinutes, location: a.location }),
  injuries: (a) => ({ injuries: a.injuries.map(injuryBody) }),
  health: (a) => a.health,
  food: (a) => a.food,
};

function injuryBody(i: InjuryInput) {
  return { region: i.region, side: i.side, type: i.type, severity: i.severity, painfulMovements: i.painfulMovements, restrictions: i.restrictions };
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** The exercise catalogue changes only with a new release, so it's fetched once per visit. */
let exercises: Promise<Exercise[]> | null = null;

/** Exercise results still being saved, per workout: finishing waits for them. */
const saving = new Map<string, Set<Promise<unknown>>>();

const average = (xs: number[]) => xs.reduce((a, x) => a + x, 0) / xs.length;
const addDays = (iso: string, n: number) => new Date(Date.parse(`${iso}T00:00:00Z`) + n * 86_400_000).toISOString().slice(0, 10);

export const api = {
  // ── Auth ──
  async login(email: string, password: string): Promise<User> {
    await request('POST', '/auth/login', { email, password }, { authCheck: false });
    return api.getUser();
  },
  /** Ticking "I'm 18 or older" on the sign-up form is required to get here. */
  async signup(input: { firstName: string; email: string; password: string }): Promise<User> {
    await request('POST', '/auth/signup', { ...input, adultConfirmed: true }, { authCheck: false });
    return api.getUser();
  },
  /** Email reset isn't built yet: the Forgot password page explains how to get a new password for now. */
  async requestPasswordReset(_email: string): Promise<void> { /* nothing to send yet */ },
  async changePassword(current: string, next: string): Promise<void> {
    await send('POST', '/auth/change-password', { currentPassword: current, newPassword: next });
  },
  async logout(): Promise<void> {
    await request('POST', '/auth/logout', undefined, { authCheck: false }).catch(() => undefined); // already logged out is fine
  },
  /** Deletes the account and everything in it, including progress photos. */
  async deleteMyData(): Promise<void> { await send('DELETE', '/me'); },

  // ── User & plan ──
  async getUser(): Promise<User> {
    const [me, o] = await Promise.all([get<MeOut>('/me'), get<OnboardingOut>('/onboarding')]);
    return toUser(me, o);
  },
  /** Name, language and theme. Questionnaire answers change through the onboarding steps. */
  async updateUser(patch: Partial<Pick<User, 'firstName' | 'lastName' | 'language' | 'theme'>>): Promise<User> {
    await send('PATCH', '/me', {
      firstName: patch.firstName?.en, lastName: patch.lastName?.en, language: patch.language, theme: patch.theme,
    });
    return api.getUser();
  },
  async getPlan(): Promise<Plan> { return toPlan(await get<PlanOut>('/plan')); },
  /**
   * Builds a new plan version from the saved answers (POST /api/plan). The engine answers in a second or two;
   * onStep marks each stage on the wait screen as it goes, and the last one only once the plan is saved.
   */
  async generatePlan(onStep?: (step: PlanGenerationStep) => void): Promise<Plan> {
    const steps: PlanGenerationStep[] = ['calories', 'program', 'injuries', 'meals'];
    let shown = 0;
    let finished = false;
    const pace = (async () => {
      while (!finished && shown < steps.length - 1) { await sleep(700); if (!finished) onStep?.(steps[shown++]); }
    })();
    try {
      const plan = await send<PlanOut>('POST', '/plan');
      finished = true;
      await pace;
      while (shown < steps.length) { onStep?.(steps[shown++]); await sleep(250); }
      return toPlan(plan);
    } finally {
      finished = true;
    }
  },

  // ── Onboarding questionnaire (backend: /api/onboarding) ──
  async getOnboarding(): Promise<OnboardingState> { return toState(await get<OnboardingOut>('/onboarding')); },
  /** Saves one step (PUT /api/onboarding/{step}); the backend checks every answer again. */
  async saveOnboardingStep(step: Exclude<OnboardingStep, 'review'>, answers: QuestionnaireAnswers): Promise<OnboardingState> {
    if (step === 'about' && (answers.age === undefined || answers.age < 18)) throw new Error('must_be_adult');
    return toState(await send<OnboardingOut>('PUT', `/onboarding/${step}`, ONBOARDING_BODY[step](answers)));
  },
  /** POST /api/onboarding/complete: every step must be answered. */
  async completeOnboarding(): Promise<OnboardingState> { return toState(await send<OnboardingOut>('POST', '/onboarding/complete')); },

  // ── Dashboard (put together from the endpoints below) ──
  async getDashboard(): Promise<Dashboard> {
    const [user, plan, week, mealDay, injuries, reviews, weights, nextCheckIn] = await Promise.all([
      api.getUser(), api.getPlan(), api.getWorkoutWeek(), api.getMealDay(), api.getInjuries(), api.getReviews(),
      get<WeightLog[]>('/weights'), api.getNextCheckIn(),
    ]);
    const today = mealDay.date;
    const recent = weights.filter((w) => w.date > addDays(today, -7) && w.date <= today).map((w) => w.weightKg);
    const avg = recent.length ? average(recent) : weights.at(-1)?.weightKg ?? user.weightKg;
    const first = weights[0]?.weightKg ?? user.weightKg;
    return {
      user, plan, mealDay, nextCheckIn,
      today: week.sessions.find((s) => s.date === today) ?? null,
      nextSession: week.sessions.find((s) => s.status === 'planned') ?? null,
      injuries: injuries.filter((i) => i.status !== 'resolved'),
      latestReview: reviews.find((r) => r.state === 'ready') ?? null,
      weightAvgKg: Math.round(avg * 10) / 10,
      weightChangeKg: Math.round((avg - first) * 10) / 10,
      weightToday: weights.find((w) => w.date === today) ?? null,
    };
  },

  // ── Body weight ──
  /** Saves today's weight (or corrects it: one entry per day). Backend: POST /api/weights. */
  async logWeight(weightKg: number): Promise<WeightLog> {
    return send<WeightLog>('POST', '/weights', { weightKg: Math.round(weightKg * 10) / 10 });
  },

  // ── Training ──
  async getWorkoutWeek(): Promise<WorkoutWeek> { return get<WorkoutWeek>('/workouts/week'); },
  /** A lifting session, or a rest day's cardio (ids "cardio-sat" …). */
  async getWorkout(id: string): Promise<Workout> {
    return id.startsWith(CARDIO) ? get<Workout>(`/cardio/${encodeURIComponent(id.slice(CARDIO.length))}`) : get<Workout>(`/workouts/${encodeURIComponent(id)}`);
  },
  /** Ticks the warm-up or the cool-down as done (today's session). */
  async tickSection(workoutId: string, section: 'warmup' | 'cooldown', done: boolean): Promise<void> {
    await send('PUT', `/workouts/${encodeURIComponent(workoutId)}/${section}`, { done });
  },
  /** Marks that day's cardio done with the minutes actually done (null = undo). */
  async logCardio(day: Weekday, minutes: number | null): Promise<void> {
    await (minutes === null ? send('DELETE', `/cardio/${day}`) : send('PUT', `/cardio/${day}`, { minutes }));
  },
  /** 2–4 exercises to swap to, for this reason (same movement and muscles, fit the equipment and injuries). */
  async getAlternatives(workoutId: string, exerciseId: string, reason: SwapReason): Promise<ExerciseAlternative[]> {
    return get<ExerciseAlternative[]>(`/workouts/${encodeURIComponent(workoutId)}/exercises/${encodeURIComponent(exerciseId)}/alternatives?reason=${reason}`);
  },
  /**
   * Swaps an exercise. "today": this session only. "always": the program from now on (a new plan version, so the
   * session's id changes: use the returned workoutId). "equipment" also saves that equipment as missing.
   */
  async swapExercise(workoutId: string, exerciseId: string, toExerciseId: string, reason: SwapReason, scope: 'today' | 'always'): Promise<{ workoutId: string; swapId: string }> {
    return send('POST', `/workouts/${encodeURIComponent(workoutId)}/exercises/${encodeURIComponent(exerciseId)}/swap`, { toExerciseId, reason, scope });
  },
  async getSwaps(): Promise<ActiveSwap[]> { return get<ActiveSwap[]>('/swaps'); },
  /** Undoes a swap ("from now on" brings the original exercise back). */
  async undoSwap(id: string): Promise<void> { await send('DELETE', `/swaps/${encodeURIComponent(id)}`); },
  async getExercise(id: string): Promise<Exercise> { return get<Exercise>(`/exercises/${encodeURIComponent(id)}`); },
  async getExercises(): Promise<Exercise[]> {
    exercises ??= get<Exercise[]>('/exercises').catch((e) => { exercises = null; throw e; });
    return exercises;
  },
  /**
   * Saves one exercise's result as soon as it's tapped (null = undo). Logging again replaces it.
   * Backend: one set_logs row per set, all with the same reps and weight (backend/app/workouts.py).
   */
  async logExercise(workoutId: string, exerciseId: string, result: ExerciseResult | null): Promise<void> {
    const path = `/workouts/${encodeURIComponent(workoutId)}/exercises/${encodeURIComponent(exerciseId)}`;
    const p = result ? send('PUT', path, result) : send('DELETE', path);
    const pending = saving.get(workoutId) ?? new Set();
    saving.set(workoutId, pending.add(p));
    try { await p; } finally { pending.delete(p); }
  },
  /**
   * Exercises missing from log.results were skipped. The effort rating and the pain check are stored.
   * Returns the injuries the pain check paused (sharp pain, swelling, numbness, pain too high or rising): the plan is
   * rebuilt without them and the screen shows "see a doctor or physiotherapist".
   */
  async finishWorkout(workoutId: string, log: WorkoutLog, painByInjury: Record<string, number>, redFlags: string[]): Promise<{ paused: string[] }> {
    await Promise.allSettled([...(saving.get(workoutId) ?? [])]);
    return send<{ paused: string[] }>('POST', `/workouts/${encodeURIComponent(workoutId)}/finish`, {
      effort: log.effort,
      pain: Object.entries(painByInjury).map(([injuryId, pain]) => ({ injuryId, pain })),
      redFlags,
      done: Object.keys(log.results), // anything else was skipped
    });
  },

  // ── Nutrition ──
  /** One date's meals (today when no date). */
  async getMealDay(date?: string): Promise<MealDay> { return get<MealDay>(`/meals/day/${date ?? 'today'}`); },
  async getMealWeek(): Promise<MealWeekDay[]> { return get<MealWeekDay[]>('/meals/week'); },
  /** Other recipes for this meal, each with the portion that keeps the day on target (backend/app/engine/meals.py). */
  async getSwapOptions(mealId: string): Promise<Meal[]> { return get<Meal[]>(`/meals/${encodeURIComponent(mealId)}/swap-options`); },
  async swapMeal(_date: string, mealId: string, replacement: Meal): Promise<MealDay> {
    return send<MealDay>('POST', `/meals/${encodeURIComponent(mealId)}/swap`, { recipeId: replacement.recipeId ?? replacement.id });
  },
  async getRecipe(id: string): Promise<Recipe> { return get<Recipe>(`/recipes/${encodeURIComponent(id)}`); },

  // ── Groceries ──
  async getGroceryList(): Promise<GroceryList> { return get<GroceryList>('/groceries'); },
  async updateGroceryItem(id: string, patch: Partial<Pick<GroceryItem, 'checked' | 'haveIt'>>): Promise<GroceryList> {
    return send<GroceryList>('PATCH', `/groceries/items/${encodeURIComponent(id)}`, patch);
  },
  async getPantry(): Promise<PantryItem[]> { return get<PantryItem[]>('/pantry'); },

  // ── Injuries ──
  async getInjuries(): Promise<Injury[]> { return get<Injury[]>('/injuries'); },
  async getInjury(id: string): Promise<Injury> { return get<Injury>(`/injuries/${encodeURIComponent(id)}`); },
  /** Adds or edits an injury; the plan is rebuilt around it. */
  async saveInjury(input: InjuryInput & { id?: string; status?: Injury['status'] }): Promise<Injury> {
    const body = { ...injuryBody(input), status: input.status ?? 'active' };
    return input.id ? send<Injury>('PUT', `/injuries/${encodeURIComponent(input.id)}`, body) : send<Injury>('POST', '/injuries', body);
  },
  async deleteInjury(id: string): Promise<void> { await send('DELETE', `/injuries/${encodeURIComponent(id)}`); },

  // ── Check-in & reviews ──
  /** When the next weekly check-in opens, and whether it's due now. */
  async getNextCheckIn(): Promise<Dashboard['nextCheckIn']> { return get<Dashboard['nextCheckIn']>('/checkins/next'); },
  /** The weight starts empty, with last week's as the placeholder. */
  async getCheckInDraft(): Promise<CheckInDraft> {
    const d = await get<CheckInDraft>('/checkins/draft');
    return { ...d, draft: { ...d.draft, body: { ...d.draft.body, weightKg: undefined } } };
  },
  /** Saves the check-in and runs the weekly review, which builds next week's plan. Returns the review's id. */
  async submitCheckIn(checkIn: CheckIn): Promise<{ reviewId: string }> {
    const { body, ...rest } = checkIn;
    return send<{ reviewId: string }>('POST', '/checkins', { ...rest, body: { ...body, photos: {} } }); // photo upload: Phase 6
  },
  async getReviews(): Promise<WeeklyReview[]> { return get<WeeklyReview[]>('/reviews'); },
  async getReview(id: string): Promise<WeeklyReview> { return get<WeeklyReview>(`/reviews/${encodeURIComponent(id)}`); },

  // ── Progress ──
  async getProgress(): Promise<Progress> { return get<Progress>('/progress'); },
};

export type Api = typeof api;
