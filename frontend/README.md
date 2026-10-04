# Rafeqi · رفيقي — web frontend

AI personal trainer and nutritionist for Egypt. Every screen reads and writes through `src/data/api.ts`, which calls the FastAPI backend in `../backend` (Phase 5). The original sample-data version is kept in `../design/` as the reference.

React 18 · TypeScript · Tailwind 3 · Vite · React Router 6 · lucide-react. No chat and no "Ask" tab: all input goes through structured forms, plus one optional 300-character note in the weekly check-in.

```bash
npm install
npm run dev        # http://localhost:5173 — needs the API too: use `npm run dev` in the project root, which starts both
npm run typecheck
```

## Folder layout

```
src/
  types.ts              Domain types: User, Plan, Workout, Exercise, Meal, Recipe, GroceryItem, Injury, CheckIn, WeeklyReview, Progress…
  data/api.ts           Data layer: one async function per screen need, calling /api (the Vite server forwards it to FastAPI).
  data/useQuery.ts      Tiny loading/error/reload hook (swap for TanStack Query if you like).
  data/session.tsx      Signed-in user (checked against the session cookie), login/signup/logout, language and theme
                        saved to the account, <RequireAuth> (questionnaire first, then the plan, then everything else).
  i18n/en.json, ar.json All UI text. index.tsx = provider, t(), l() for LocalizedText, number and date formatting.
  theme.tsx             Light / dark / system (adds .dark to <html>).
  constants.ts          Option ids for forms (labels live in the translation files under enums.*).
  components/           Shared UI: Button, Card, Chip, Badge/StatusBadge/SwapBadge/CitationChip, ProgressBar/StepProgress,
                        Field/TextInput/PasswordInput/Segmented/ScalePicker/NumberStepper/Slider/Toggle/Checkbox/Tabs,
                        LineChart/MacroRing/MacroBars, BodyMap, Loading/Empty/Error states, QueryView, Toasts, Disclaimer,
                        AppShell (sidebar + bottom tabs), AppBar, FlowShell (multi-step flows)
  screens/              One component per screen (below)
```

## Rules the code follows

- **No hard-coded UI text.** Components call `t('key')`. Text that comes from the backend is `LocalizedText { en, ar }`, read with `l(text)`.
- **RTL everywhere.** Only logical utilities are used (`ms-/me-/ps-/pe-/start-/end-/text-start`, `rtl:` for mirroring icons). `<html dir>` is set from the language. Charts stay left-to-right (time axis) in both languages.
- **Organic tokens** live in `tailwind.config.ts` → CSS variables in `index.css` (`:root` light, `.dark` dark):
  `bg, surface, ink, divider, accent-100…900` (terracotta), `sage-100…900`, `neutral-100…900`, `warn-100…800`; radii `sm md lg card pill`; spacing `o-1…o-8`, `tap` (44px); `shadow-sm/md/lg`; fonts `font-heading` (Caprasimo → Lalezar in Arabic) and `font-body` (Figtree → Readex Pro).
- **One status language:** `onTrack` (sage), `attention` (terracotta), `warning` (clay red). Use `<StatusBadge status=…/>`.
- **Grocery items use generic names only**, never brands.
- **Touch targets** are at least 44px (`min-h-tap`, `h-tap w-tap`). The logger's "Done as planned" buttons are 54px.
- **Loading, empty and error states** go through `<QueryView>` on every data screen.

## Screens, routes and data

| # | Screen | Component (file) | Route | Data (api.ts) |
|---|---|---|---|---|
| 1 | Log in | `Login` (auth/AuthScreens) | `/login` | `login()` |
| 1 | Sign up | `SignUp` (auth/AuthScreens) | `/signup` | `signup()` |
| 1 | Forgot password | `ForgotPassword` (auth/AuthScreens) | `/forgot-password` | `requestPasswordReset()` |
| 2a–g | Onboarding questionnaire | `Onboarding` (onboarding/Onboarding) | `/onboarding/:step` (`about, goal, training, injuries, health, food, review`) | `getOnboarding`, `saveOnboardingStep` (each step saved on Next), `completeOnboarding` |
| 3 | Plan generation wait | `PlanGenerating` (onboarding/PlanScreens) | `/onboarding/generating` | `generatePlan(onStep)` |
| 4 | Your plan is ready | `PlanReady` (onboarding/PlanScreens) | `/plan-ready` | `getPlan()`, `getUser()`, `getExercises()` |
| 5 | Dashboard | `Dashboard` (home/Dashboard) | `/` | `getDashboard()` |
| 6 | Workout plan (week) | `WorkoutPlan` (workouts/WorkoutScreens) | `/workouts` | `getWorkoutWeek()`, `getExercises()` |
| 6 | Workout day (any day of the week; prev/next arrows; what was logged on past days; Start only today) | `Session` (workouts/WorkoutScreens) | `/workouts/:id` | `getWorkout(id)`, `getWorkoutWeek()`, `getInjuries()` |
| 7 | Exercise detail | `ExerciseDetail` (workouts/WorkoutScreens) | `/exercises/:id` | `getExercise(id)`, `getPlan()` |
| 8 | Workout logger (one page, one result per exercise) + effort rating + pain check | `WorkoutLogger` (workouts/WorkoutScreens) | `/workouts/:id/log` | `getWorkout`, `getExercises`, `getInjuries`, `logExercise`, `finishWorkout` |
| 9 | Nutrition plan (day / week, swap) | `NutritionPlan` (nutrition/NutritionScreens) | `/nutrition`, `/nutrition?view=week` | `getMealDay`, `getPlan`, `getMealWeek`, `getSwapOptions`, `swapMeal` |
| 9 | Nutrition day (one date, prev/next arrows) | `NutritionDay` (nutrition/NutritionScreens) | `/nutrition/day/:date` | `getMealDay(date)`, `getPlan`, `getMealWeek`, `swapMeal` |
| 10 | Recipe detail | `RecipeDetail` (nutrition/NutritionScreens) | `/nutrition/recipes/:id` | `getRecipe(id)` |
| 11 | Grocery list | `Groceries` (nutrition/NutritionScreens) | `/groceries` | `getGroceryList`, `updateGroceryItem` |
| 11 | Pantry | `Pantry` (nutrition/NutritionScreens) | `/groceries/pantry` | `getPantry()` |
| 12 | Injuries list | `Injuries` (injuries/InjuryScreens) | `/injuries` | `getInjuries()` |
| 12 | Injury detail | `InjuryDetail` (injuries/InjuryScreens) | `/injuries/:id` | `getInjury`, `saveInjury` |
| 12 | Add / edit injury | `InjuryEdit` (injuries/InjuryScreens) | `/injuries/new`, `/injuries/:id/edit` | `getInjury`, `saveInjury`, `deleteInjury` |
| 12 | Stop-and-see-a-doctor warning | `InjuryWarning` (injuries/InjuryScreens) | `/injuries/:id/warning` | `getInjury(id)` |
| 13a–f | Weekly check-in | `CheckIn` (checkin/CheckIn) | `/check-in/:step` (`body, training, injuries, nutrition, life, note`) | `getCheckInDraft`, `getExercises`, `getInjuries`, `submitCheckIn` |
| 14 | Weekly review (+ writing wait) | `WeeklyReview` (review/ReviewAndProgress) | `/reviews/:id` (`?writing=1` shows the 30–90 s wait) | `getReview(id)` |
| 14 | Past reviews | `ReviewHistory` (review/ReviewAndProgress) | `/reviews` | `getReviews()` |
| 15 | Progress | `Progress` (review/ReviewAndProgress) | `/progress` | `getProgress()` |
| 16 | Profile & settings | `Profile` (review/ReviewAndProgress) | `/profile` | `getUser`, `getInjuries`, `deleteMyData`, `logout` |
| 16 | Change password | `ChangePassword` (review/ReviewAndProgress) | `/profile/password` | `changePassword()` |

Every route except log in, sign up and forgot password is wrapped in `<RequireAuth>`. Mobile shows bottom tabs (Home, Workouts, Nutrition, Groceries, Progress); the Home tab gets a dot when the check-in is due, and the profile is in the header. Desktop (`lg:`) shows the left sidebar instead.

## The backend connection

1. `src/data/api.ts` calls the endpoints under `/api` (list: http://localhost:5173/api/docs) and turns their answers into the
   types in `src/types.ts`. Screens never call `fetch` themselves.
2. Answers: 401 → back to Log in (the session ended); 404 → `NotFoundError` (the "We couldn't find that" state); anything
   else → `ApiError` with the backend's error code (e.g. `email_taken`), shown as the screen's error state or a toast.
3. `generatePlan` shows its four steps while the engine works (about a second). The weekly review is written by the engine
   straight away for now; the AI text (next session) will arrive with `state: 'pending'` and the screen will poll `getReview`.
4. Backend text (meal names, reasons, review changes) arrives as `{ en, ar }`; `l()` picks the language.
5. Progress photo upload comes in Phase 6 (`CheckIn.body.photos` isn't sent yet).
6. Installable as a home-screen app: `public/manifest.webmanifest` and `public/icons/` (redraw with `node scripts/make-icons.mjs`).
