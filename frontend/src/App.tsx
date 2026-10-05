import { Navigate, Route, Routes } from 'react-router-dom';
import { RequireAuth } from '@/data/session';
import { Login, SignUp, ForgotPassword } from '@/screens/auth/AuthScreens';
import { Onboarding, OnboardingStart } from '@/screens/onboarding/Onboarding';
import { PlanGenerating, PlanReady } from '@/screens/onboarding/PlanScreens';
import { WhyPlan } from '@/screens/plan/WhyPlan';
import { Dashboard } from '@/screens/home/Dashboard';
import { WorkoutPlan, Session, ExerciseDetail, WorkoutLogger } from '@/screens/workouts/WorkoutScreens';
import { NutritionPlan, NutritionDay, RecipeDetail, Groceries, Pantry } from '@/screens/nutrition/NutritionScreens';
import { Injuries, InjuryDetail, InjuryEdit, InjuryWarning } from '@/screens/injuries/InjuryScreens';
import { CheckIn } from '@/screens/checkin/CheckIn';
import { WeeklyReview, ReviewHistory, Progress, Profile, ProfileEquipment, SendFeedback, ChangePassword } from '@/screens/review/ReviewAndProgress';

const auth = (el: JSX.Element) => <RequireAuth>{el}</RequireAuth>;

/** Route table — see README for the screen ↔ data map. No chat route by design. */
export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<SignUp />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />

      <Route path="/onboarding/generating" element={auth(<PlanGenerating />)} />
      <Route path="/onboarding/:step" element={auth(<Onboarding />)} />
      <Route path="/onboarding" element={auth(<OnboardingStart />)} />
      <Route path="/plan-ready" element={auth(<PlanReady />)} />
      <Route path="/plan/why" element={auth(<WhyPlan />)} />

      <Route path="/" element={auth(<Dashboard />)} />
      <Route path="/workouts" element={auth(<WorkoutPlan />)} />
      <Route path="/workouts/:id" element={auth(<Session />)} />
      <Route path="/workouts/:id/log" element={auth(<WorkoutLogger />)} />
      <Route path="/exercises/:id" element={auth(<ExerciseDetail />)} />

      <Route path="/nutrition" element={auth(<NutritionPlan />)} />
      <Route path="/nutrition/day/:date" element={auth(<NutritionDay />)} />
      <Route path="/nutrition/recipes/:id" element={auth(<RecipeDetail />)} />
      <Route path="/groceries" element={auth(<Groceries />)} />
      <Route path="/groceries/pantry" element={auth(<Pantry />)} />

      <Route path="/injuries" element={auth(<Injuries />)} />
      <Route path="/injuries/new" element={auth(<InjuryEdit />)} />
      <Route path="/injuries/:id" element={auth(<InjuryDetail />)} />
      <Route path="/injuries/:id/edit" element={auth(<InjuryEdit />)} />
      <Route path="/injuries/:id/warning" element={auth(<InjuryWarning />)} />

      <Route path="/check-in/:step" element={auth(<CheckIn />)} />
      <Route path="/check-in" element={<Navigate to="/check-in/body" replace />} />
      <Route path="/reviews" element={auth(<ReviewHistory />)} />
      <Route path="/reviews/:id" element={auth(<WeeklyReview />)} />

      <Route path="/progress" element={auth(<Progress />)} />
      <Route path="/profile" element={auth(<Profile />)} />
      <Route path="/profile/password" element={auth(<ChangePassword />)} />
      <Route path="/profile/equipment" element={auth(<ProfileEquipment />)} />
      <Route path="/profile/feedback" element={auth(<SendFeedback />)} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
