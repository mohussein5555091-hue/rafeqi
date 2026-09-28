// All sample data for the proof of concept — Omar, 29, Cairo.
// Replace src/data/api.ts implementations with real requests; keep these shapes.
import type {
  User, Plan, Exercise, Workout, WorkoutWeek, MealDay, Meal, MealWeekDay, Recipe,
  GroceryList, PantryItem, Injury, CheckIn, WeeklyReview, Progress, LocalizedText,
} from '@/types';

const L = (en: string, ar: string): LocalizedText => ({ en, ar });

export const TODAY: string = '2026-09-28';

export const user: User = {
  id: 'u_omar',
  firstName: L('Omar', 'عمر'),
  lastName: L('Hassan', 'حسن'),
  email: 'omar.hassan@gmail.com',
  sex: 'male',
  age: 29,
  heightCm: 180,
  weightKg: 88,
  waistCm: 96,
  goal: 'loseFat',
  pace: 'steady',
  experience: 'intermediate',
  daysPerWeek: 4,
  sessionMinutes: 60,
  location: 'gym',
  health: { heartCondition: false, diabetes: false, pregnancy: false, recentSurgery: false, exerciseMedication: false },
  food: { mealsPerDay: 4, dislikes: ['liver', 'eggplant'], allergies: [], fasting: ['ramadan'], cookingMinutes: 30, weeklyBudgetEgp: 1800 },
  units: 'metric',
  language: 'en',
  theme: 'system',
  memberSince: '2026-09-11',
};

// ── Exercises ────────────────────────────────────────────────────────
export const exercises: Exercise[] = [
  {
    id: 'ex_db_floor_press',
    name: L('Neutral-grip dumbbell floor press', 'ضغط دمبل من الأرض بقبضة محايدة'),
    muscles: { primary: ['chest'], secondary: ['armL', 'armR', 'shoulderL', 'shoulderR'] },
    muscleNames: L('Chest · triceps, front shoulders', 'الصدر · الترايسبس، مقدمة الكتف'),
    steps: [
      L('Lie on the floor, knees bent, a dumbbell in each hand with palms facing each other.', 'نام على الأرض وركبك مثنية، ودمبل في كل إيد وكفوفك في وش بعض.'),
      L('Lower until your upper arms touch the floor.', 'نزّل لحد ما دراعك يلمس الأرض.'),
      L('Press up until your arms are straight.', 'ادفع لفوق لحد ما دراعك يفرد.'),
    ],
    cues: [L('Elbows about 45° from your body', 'الكوع حوالي 45 درجة من جسمك'), L('Pause lightly on the floor', 'وقفة خفيفة على الأرض'), L('Breathe out as you press', 'اطرد النفس وأنت بتدفع')],
    mistakes: [L('Bouncing the elbows off the floor', 'خبط الكوع في الأرض'), L('Flaring the elbows out wide', 'فتح الكوع لبرّه أوي')],
    alternatives: [{ name: L('Incline push-up on a bench', 'ضغط مائل على بنش'), kind: 'easier' }, { name: L('Machine chest press, neutral grip', 'ضغط صدر على الجهاز بقبضة محايدة'), kind: 'injuryFriendly' }],
  },
  {
    id: 'ex_cs_row',
    name: L('Chest-supported dumbbell row', 'تجديف دمبل بسند للصدر'),
    muscles: { primary: ['upperBack'], secondary: ['armL', 'armR'] },
    muscleNames: L('Upper back · biceps', 'أعلى الظهر · البايسبس'),
    steps: [L('Lie chest-down on an incline bench.', 'نام على بطنك على بنش مائل.'), L('Row the dumbbells to your hips.', 'اسحب الدمبل ناحية وسطك.')],
    cues: [L('Lead with your elbows', 'الكوع هو اللي يقود الحركة'), L('Squeeze shoulder blades together', 'اضغط لوحي الكتف على بعض')],
    mistakes: [L('Shrugging to your ears', 'رفع الكتف ناحية الودن')],
    alternatives: [{ name: L('Seated cable row', 'تجديف بالكابل قاعد'), kind: 'easier' }],
  },
  {
    id: 'ex_landmine_press',
    name: L('Half-kneeling landmine press', 'ضغط لاندماين على ركبة واحدة'),
    muscles: { primary: ['shoulderL', 'shoulderR'], secondary: ['chest', 'armL', 'armR', 'abdomen'] },
    muscleNames: L('Front shoulders · upper chest, triceps, core', 'مقدمة الكتف · أعلى الصدر، الترايسبس، البطن'),
    steps: [
      L('Kneel on your right knee, left foot forward, bar end in your left hand at shoulder height.', 'انزل على ركبتك اليمين، ورجلك الشمال قدام، وطرف البار في إيدك الشمال عند الكتف.'),
      L('Brace your stomach and squeeze your right glute.', 'شدّ بطنك واعصر عضلة المقعدة اليمين.'),
      L('Press the bar up and forward until your arm is long — not straight overhead.', 'ادفع البار لفوق ولقدام لحد ما دراعك يفرد — مش فوق راسك على طول.'),
      L('Lower for 2 seconds back to your shoulder.', 'نزّله في ثانيتين لحد كتفك.'),
    ],
    cues: [
      L("Ribs down — don't lean back", 'الضلوع لتحت — ماترجعش لورا'),
      L('Reach "up and out", like pushing a door shut', 'ادفع لفوق ولقدام، كأنك بتقفل باب'),
      L('Keep your wrist stacked over your elbow', 'خلّي رسغك فوق كوعك'),
      L('Breathe out as you press', 'اطرد النفس وأنت بتدفع'),
    ],
    mistakes: [
      L('Arching the lower back to finish the rep', 'تقويس أسفل الظهر عشان تكمّل العدّة'),
      L('Shrugging the shoulder up to your ear', 'رفع الكتف ناحية الودن'),
      L('Dropping the bar fast on the way down', 'تنزيل البار بسرعة'),
    ],
    alternatives: [
      { name: L('Incline push-up on a bench', 'ضغط مائل على بنش'), kind: 'easier' },
      { name: L('Single-arm cable press', 'ضغط كابل بإيد واحدة'), kind: 'injuryFriendly' },
      { name: L('Seated landmine press', 'ضغط لاندماين وأنت قاعد'), kind: 'easier' },
    ],
  },
  {
    id: 'ex_lat_pulldown',
    name: L('Neutral-grip lat pulldown', 'سحب علوي بقبضة محايدة'),
    muscles: { primary: ['upperBack'], secondary: ['armL', 'armR'] },
    muscleNames: L('Lats · biceps', 'عضلات الظهر الجانبية · البايسبس'),
    steps: [L('Sit with thighs under the pad, neutral handle.', 'اقعد ورجلك تحت المسند، ومسكة محايدة.'), L('Pull to your upper chest.', 'اسحب لأعلى صدرك.')],
    cues: [L('Chest up to the handle', 'صدرك يطلع للمسكة')],
    mistakes: [L('Leaning far back', 'الرجوع لورا كتير')],
    alternatives: [{ name: L('Half-kneeling single-arm cable pulldown', 'سحب كابل بإيد واحدة على ركبة'), kind: 'injuryFriendly' }],
  },
  {
    id: 'ex_face_pull',
    name: L('Cable face pull', 'سحب للوجه بالكابل'),
    muscles: { primary: ['shoulderL', 'shoulderR'], secondary: ['upperBack'] },
    muscleNames: L('Rear shoulders · upper back', 'خلفية الكتف · أعلى الظهر'),
    steps: [L('Set the rope at face height and pull it towards your forehead.', 'ثبّت الحبل على مستوى وشك واسحبه ناحية جبهتك.')],
    cues: [L('Thumbs point back at the end', 'الإبهام يشاور لورا في الآخر')],
    mistakes: [L('Using too much weight', 'وزن تقيل زيادة')],
    alternatives: [{ name: L('Band pull-apart', 'فتح استك'), kind: 'easier' }],
  },
  {
    id: 'ex_pushdown',
    name: L('Cable triceps pushdown', 'ترايسبس بالكابل'),
    muscles: { primary: ['armL', 'armR'], secondary: [] },
    muscleNames: L('Triceps', 'الترايسبس'),
    steps: [L('Elbows at your sides, push the bar down until your arms are straight.', 'الكوع جنبك، وادفع البار لتحت لحد ما دراعك يفرد.')],
    cues: [L('Elbows stay still', 'الكوع ثابت')],
    mistakes: [L('Leaning over the bar', 'الميل على البار')],
    alternatives: [{ name: L('Band pushdown', 'ترايسبس بالاستك'), kind: 'easier' }],
  },
  {
    id: 'ex_incline_curl',
    name: L('Incline dumbbell curl', 'بايسبس دمبل على بنش مائل'),
    muscles: { primary: ['armL', 'armR'], secondary: ['forearmL', 'forearmR'] },
    muscleNames: L('Biceps · forearms', 'البايسبس · الساعد'),
    steps: [L('Sit back on a 45° bench and curl both dumbbells.', 'اسند ظهرك على بنش 45 درجة وارفع الدمبلين.')],
    cues: [L('Keep upper arms still', 'الدراع من فوق ثابت')],
    mistakes: [L('Swinging the weights', 'مرجحة الأوزان')],
    alternatives: [{ name: L('Cable curl', 'بايسبس بالكابل'), kind: 'easier' }],
  },
];

// ── Plan ─────────────────────────────────────────────────────────────
export const plan: Plan = {
  id: 'plan_1',
  createdAt: '2026-09-11',
  calories: 2200,
  maintenanceCalories: 2700,
  proteinG: 175,
  carbsG: 225,
  fatG: 67,
  rationale: {
    calories: L('About 500 below your maintenance (~2,700) — a steady 0.5 kg a week.', 'حوالي 500 أقل من احتياجك (~2,700) — نزول ثابت نص كيلو في الأسبوع.'),
    protein: L('About 2 g per kg — protects muscle while you eat less. Chicken, eggs, ful, lentils, zabadi.', 'حوالي 2 جم لكل كيلو — بيحافظ على العضل وأنت بتاكل أقل. فراخ، بيض، فول، عدس، زبادي.'),
    carbs: L('Fuels four training days. Mostly rice, baladi bread, oats, fruit — more on gym days.', 'طاقة لأربع أيام تمرين. أغلبها رز وعيش بلدي وشوفان وفاكهة — أكتر في أيام الجيم.'),
    fat: L('Around 27% of calories for hormones and flavour — olive oil, tahini, eggs.', 'حوالي 27% من السعرات للهرمونات والطعم — زيت زيتون وطحينة وبيض.'),
  },
  program: {
    name: L('Upper / Lower · 4 days', 'علوي / سفلي · 4 أيام'),
    daysPerWeek: 4,
    totalWeeks: 8,
    currentWeek: 3,
    why: L(
      'Each muscle is trained twice a week in 60-minute sessions, which suits an intermediate lifter keeping strength while eating less. Fridays stay free.',
      'كل عضلة بتتمرن مرتين في الأسبوع في جلسات 60 دقيقة، وده مناسب لمتدرب متوسط عايز يحافظ على قوته وهو بياكل أقل. الجمعة إجازة.',
    ),
    schedule: [
      { day: 'sat', sessionId: 'w3_lower_a' }, { day: 'sun' }, { day: 'mon', sessionId: 'w3_upper_a' },
      { day: 'tue' }, { day: 'wed', sessionId: 'w3_lower_b' }, { day: 'thu', sessionId: 'w3_upper_b' }, { day: 'fri' },
    ],
  },
  injurySwaps: [
    { injuryId: 'inj_shoulder_l', fromName: L('Standing barbell overhead press', 'ضغط أكتاف بالبار واقف'), toExerciseId: 'ex_landmine_press', reason: L('Presses at an angle, not overhead — respects your "no overhead" restriction.', 'بيضغط بزاوية مش فوق الراس — بيحترم منع الرفع فوق الراس.') },
    { injuryId: 'inj_shoulder_l', fromName: L('Barbell bench press', 'بنش بريس بالبار'), toExerciseId: 'ex_db_floor_press', reason: L('The floor limits the range that aggravates the shoulder.', 'الأرض بتحدّ من المدى اللي بيضايق الكتف.') },
    { injuryId: 'inj_shoulder_l', fromName: L('Parallel-bar dips', 'ديبس على المتوازي'), toExerciseId: 'ex_pushdown', reason: L('Same triceps work without the deep shoulder stretch.', 'نفس شغل الترايسبس من غير شدّ الكتف.') },
  ],
  conservative: false,
};

// ── Workouts ─────────────────────────────────────────────────────────
const upperA: Workout = {
  id: 'w3_upper_a',
  name: L('Upper body A', 'الجزء العلوي أ'),
  day: 'mon',
  date: '2026-09-28',
  status: 'today',
  estMinutes: 58,
  warmupMinutes: 6,
  exercises: [
    { exerciseId: 'ex_db_floor_press', sets: 3, reps: '8–10', restSec: 120, rpe: 7, swap: { injuryId: 'inj_shoulder_l', kind: 'swapped' }, weightStepKg: 2, lastTime: [{ reps: 10, weightKg: 22.5, rpe: 7 }, { reps: 10, weightKg: 22.5, rpe: 7 }, { reps: 9, weightKg: 22.5, rpe: 8 }] },
    { exerciseId: 'ex_cs_row', sets: 3, reps: '10–12', restSec: 90, rpe: 8, weightStepKg: 2, lastTime: [{ reps: 12, weightKg: 20, rpe: 8 }, { reps: 11, weightKg: 20, rpe: 8 }, { reps: 10, weightKg: 20, rpe: 8 }] },
    { exerciseId: 'ex_landmine_press', sets: 3, reps: '10 each', restSec: 90, rpe: 7, swap: { injuryId: 'inj_shoulder_l', kind: 'swapped' }, weightStepKg: 2.5 },
    { exerciseId: 'ex_lat_pulldown', sets: 3, reps: '10–12', restSec: 90, rpe: 8, weightStepKg: 5 },
    { exerciseId: 'ex_face_pull', sets: 3, reps: '15', restSec: 60, rpe: 7, swap: { injuryId: 'inj_shoulder_l', kind: 'added' }, weightStepKg: 2.5 },
    { exerciseId: 'ex_pushdown', sets: 3, reps: '12', restSec: 60, rpe: 8, swap: { injuryId: 'inj_shoulder_l', kind: 'swapped' }, weightStepKg: 2.5 },
    { exerciseId: 'ex_incline_curl', sets: 2, reps: '12', restSec: 60, rpe: 8, weightStepKg: 1 },
  ],
};

export const workoutWeek: WorkoutWeek = {
  weekNumber: 3,
  totalWeeks: 8,
  start: '2026-09-26',
  end: '2026-10-02',
  deloadWeek: 5,
  sessions: [
    { id: 'w3_lower_a', name: L('Lower body A', 'الجزء السفلي أ'), day: 'sat', date: '2026-09-26', status: 'done', estMinutes: 55, warmupMinutes: 6, exercises: [], summary: { minutes: 52, setsDone: 18, setsTotal: 18, painByInjury: { inj_shoulder_l: 2 } } },
    upperA,
    { id: 'w3_lower_b', name: L('Lower body B', 'الجزء السفلي ب'), day: 'wed', date: '2026-09-30', status: 'planned', estMinutes: 55, warmupMinutes: 6, exercises: [] },
    { id: 'w3_upper_b', name: L('Upper body B', 'الجزء العلوي ب'), day: 'thu', date: '2026-10-01', status: 'planned', estMinutes: 58, warmupMinutes: 6, exercises: [] },
  ],
};

// ── Meals & recipes ──────────────────────────────────────────────────
export const meals: Meal[] = [
  { id: 'm_ful_eggs', slot: 'breakfast', time: '08:30', name: L('Ful medames, eggs & baladi bread', 'فول مدمس وبيض وعيش بلدي'), portions: L('1 plate ful · 2 eggs + 2 whites · 1 baladi bread · tomato & cucumber', 'طبق فول · 2 بيض + 2 بياض · رغيف بلدي · طماطم وخيار'), kcal: 515, proteinG: 38, carbsG: 52, fatG: 17, recipeId: 'r_ful_eggs', eaten: true },
  { id: 'm_koshary', slot: 'lunch', time: '14:30', name: L('Koshary, lighter plate', 'كشري، طبق أخف'), portions: L('1 medium plate · extra lentils · less fried onion · 1 cup zabadi', 'طبق وسط · عدس زيادة · بصل مقلي أقل · علبة زبادي'), kcal: 630, proteinG: 30, carbsG: 100, fatG: 12 },
  { id: 'm_zabadi_oats', slot: 'snack', time: '18:30', name: L('Zabadi, banana & oats', 'زبادي وموز وشوفان'), portions: L('1 cup thick zabadi · 1 banana · 3 tbsp oats · 1 tsp honey', 'علبة زبادي · موزة · 3 معالق شوفان · معلقة عسل صغيرة'), kcal: 305, proteinG: 27, carbsG: 38, fatG: 5 },
  { id: 'm_chicken_molokhia', slot: 'dinner', time: '21:00', name: L('Grilled chicken, rice & molokhia', 'فراخ مشوية ورز وملوخية'), portions: L('250 g chicken · ½ cup rice · 1 ladle molokhia · lemon', '250 جم فراخ · نص كوباية رز · مغرفة ملوخية · ليمون'), kcal: 750, proteinG: 80, carbsG: 35, fatG: 33, recipeId: 'r_chicken_molokhia' },
];

export const mealDay: MealDay = { date: TODAY, day: 'mon', isTrainingDay: true, meals };

/** Swap candidates: within ±10% of the meal's calories and protein. */
export const swapOptions: Record<string, Meal[]> = {
  m_koshary: [
    { id: 'm_hawawshi', slot: 'lunch', time: '14:30', name: L('Hawawshi, baked, lean beef', 'حواوشي في الفرن بلحمة قليلة الدهن'), portions: L('1 loaf · salad', 'رغيف · سلطة'), kcal: 640, proteinG: 34, carbsG: 68, fatG: 22 },
    { id: 'm_lentil_chicken', slot: 'lunch', time: '14:30', name: L('Lentil soup, bread & grilled chicken', 'شوربة عدس وعيش وفراخ مشوية'), portions: L('1 bowl · ½ baladi · 100 g chicken', 'طبق · نص رغيف بلدي · 100 جم فراخ'), kcal: 610, proteinG: 38, carbsG: 70, fatG: 16 },
    { id: 'm_macarona', slot: 'lunch', time: '14:30', name: L('Macarona with tomato & beef', 'مكرونة بالصلصة واللحمة'), portions: L('1 plate · 90 g beef mince', 'طبق · 90 جم لحمة مفرومة'), kcal: 650, proteinG: 32, carbsG: 84, fatG: 18 },
  ],
};

export const mealWeek: MealWeekDay[] = [
  { date: '2026-09-26', day: 'sat', kcal: 2200, main: L('Grilled fish, rice & salad', 'سمك مشوي ورز وسلطة'), others: L('Ful & eggs · lentil soup · zabadi', 'فول وبيض · شوربة عدس · زبادي') },
  { date: '2026-09-27', day: 'sun', kcal: 2200, main: L('Beef kofta, baladi bread & tahini', 'كفتة وعيش بلدي وطحينة'), others: L('Oats with milk · koshary · fruit', 'شوفان باللبن · كشري · فاكهة') },
  { date: '2026-09-28', day: 'mon', kcal: 2200, main: L('Chicken, rice & molokhia', 'فراخ ورز وملوخية'), others: L('Ful & eggs · koshary · zabadi & oats', 'فول وبيض · كشري · زبادي وشوفان') },
  { date: '2026-09-29', day: 'tue', kcal: 2200, main: L('Lentil soup & chicken shawarma bowl', 'شوربة عدس وبول شاورما فراخ'), others: L('Cheese & egg sandwich · pasta · fruit', 'ساندوتش جبنة وبيض · مكرونة · فاكهة') },
  { date: '2026-09-30', day: 'wed', kcal: 2200, main: L('Chicken & potatoes (swapped)', 'فراخ وبطاطس (بديل)'), others: L('Shakshuka · koshary · zabadi', 'شكشوكة · كشري · زبادي') },
  { date: '2026-10-01', day: 'thu', kcal: 2200, main: L('Macarona with beef mince', 'مكرونة باللحمة المفرومة'), others: L('Ful & eggs · tuna salad · fruit', 'فول وبيض · سلطة تونة · فاكهة') },
  { date: '2026-10-02', day: 'fri', kcal: 2200, main: L('Family lunch: mahshi & grilled chicken', 'غدا العيلة: محشي وفراخ مشوية'), others: L('Late breakfast · light dinner', 'فطار متأخر · عشا خفيف') },
];

export const recipes: Recipe[] = [
  {
    id: 'r_chicken_molokhia',
    name: L('Chicken, rice & molokhia', 'فراخ ورز وملوخية'),
    prepMin: 20, cookMin: 30, fridgeDays: 3, kcal: 750, proteinG: 80, carbsG: 35, fatG: 33,
    ingredients: [
      { name: L('Chicken breast, raw', 'صدور فراخ نيّة'), grams: 250, amount: L('250 g', '250 جم') },
      { name: L('Egyptian rice, dry', 'رز مصري ني'), grams: 40, amount: L('40 g', '40 جم') },
      { name: L('Molokhia, frozen', 'ملوخية مجمدة'), grams: 200, amount: L('200 g', '200 جم') },
      { name: L('Chicken stock', 'شوربة فراخ'), amount: L('250 ml', '250 مل') },
      { name: L('Garlic', 'توم'), grams: 12, amount: L('3 cloves · 12 g', '3 فصوص · 12 جم') },
      { name: L('Ground coriander', 'كزبرة ناشفة مطحونة'), grams: 2, amount: L('2 g · 1 tsp', '2 جم · معلقة صغيرة') },
      { name: L('Olive oil or ghee', 'زيت زيتون أو سمنة'), grams: 10, amount: L('10 g · 2 tsp', '10 جم · 2 معلقة صغيرة') },
      { name: L('Lemon, cumin, salt', 'ليمون، كمون، ملح'), amount: L('to taste', 'حسب الذوق') },
    ],
    steps: [
      { text: L('Rub the chicken with lemon, cumin, half the coriander and salt. Leave to marinate.', 'تبّل الفراخ بالليمون والكمون ونص الكزبرة والملح، وسيبها تتتبّل.'), timerSec: 900 },
      { text: L('Rinse the rice, add 90 ml water and a pinch of salt, cover and cook on low.', 'اغسل الرز، وضيف 90 مل مية ورشة ملح، وغطيه على نار هادية.'), timerSec: 1080 },
      { text: L('Grill or pan-cook the chicken, 6 minutes each side, until the juices run clear.', 'اشوي الفراخ 6 دقايق كل ناحية لحد ما تستوي.'), timerSec: 720 },
      { text: L('Bring the stock to a simmer, add the molokhia and stir. Keep it below a boil.', 'سخّن الشوربة، وضيف الملوخية وقلّب. ماتسيبهاش تغلي.'), timerSec: 300 },
      { text: L("Fry the garlic and remaining coriander in the oil until golden (the ta'leya), then stir into the molokhia.", 'حمّر التوم وباقي الكزبرة في الزيت (التقلية)، وضيفها على الملوخية.'), timerSec: 60 },
      { text: L('Slice the chicken, serve with the rice, molokhia and a squeeze of lemon.', 'قطّع الفراخ وقدّمها مع الرز والملوخية وعصرة ليمون.') },
    ],
    storage: L('Chicken and rice keep 3 days in the fridge; molokhia 2 days.', 'الفراخ والرز يستحملوا 3 أيام في التلاجة، والملوخية يومين.'),
    reheating: L("Reheat rice covered with a splash of water, 2 min in the microwave. Warm molokhia gently on the stove — don't let it boil or it separates.", 'سخّن الرز متغطي برشة مية دقيقتين في الميكروويف. سخّن الملوخية على نار هادية — ماتغليهاش عشان ماتفصلش.'),
  },
  {
    id: 'r_ful_eggs',
    name: L('Ful medames, eggs & baladi bread', 'فول مدمس وبيض وعيش بلدي'),
    prepMin: 5, cookMin: 10, fridgeDays: 3, kcal: 515, proteinG: 38, carbsG: 52, fatG: 17,
    ingredients: [
      { name: L('Cooked fava beans (ful)', 'فول مدمس'), grams: 200, amount: L('200 g · 1 plate', '200 جم · طبق') },
      { name: L('Eggs', 'بيض'), amount: L('2 whole + 2 whites', '2 بيضة + 2 بياض') },
      { name: L('Baladi bread', 'عيش بلدي'), amount: L('1 loaf', 'رغيف') },
      { name: L('Olive oil', 'زيت زيتون'), grams: 5, amount: L('5 g · 1 tsp', '5 جم · معلقة صغيرة') },
      { name: L('Cumin, lemon, salt', 'كمون، ليمون، ملح'), amount: L('to taste', 'حسب الذوق') },
      { name: L('Tomato & cucumber', 'طماطم وخيار'), amount: L('1 each', 'واحدة من كل نوع') },
    ],
    steps: [
      { text: L('Warm the ful with a splash of water, then mash lightly.', 'سخّن الفول برشة مية وهرسه شوية.'), timerSec: 300 },
      { text: L('Scramble or boil the eggs.', 'اعمل البيض مسلوق أو أومليت.'), timerSec: 480 },
      { text: L('Top the ful with olive oil, cumin and lemon. Serve with bread and salad.', 'حط على الفول زيت زيتون وكمون وليمون، وقدّمه مع العيش والسلطة.') },
    ],
    storage: L('Cooked ful keeps 3 days in the fridge.', 'الفول المطبوخ يستحمل 3 أيام في التلاجة.'),
    reheating: L('Reheat ful with a splash of water on the stove.', 'سخّن الفول برشة مية على النار.'),
  },
];

// ── Groceries (generic names only — never brands) ───────────────────
const g = (id: string, en: string, ar: string, category: GroceryList['items'][number]['category'], qty: number, unit: GroceryList['items'][number]['unit'], costEgp: number, period: 'week' | 'month', extra: Partial<{ checked: boolean; haveIt: boolean }> = {}) =>
  ({ id, name: L(en, ar), category, qty, unit, costEgp, period, checked: false, haveIt: false, ...extra });

export const groceryList: GroceryList = {
  weekNumber: 3,
  start: '2026-09-26',
  end: '2026-10-02',
  budgetEgp: 1800,
  changeNote: L('Updated after your weekly review. Fish fillet added; beef mince down from 1 kg to 0.5 kg.', 'اتحدّثت بعد مراجعتك الأسبوعية. اتضاف فيليه سمك، واللحمة المفرومة نزلت من 1 كجم لنص كيلو.'),
  items: [
    g('gi_tomatoes', 'Tomatoes', 'طماطم', 'produce', 2, 'kg', 50, 'week', { checked: true }),
    g('gi_cucumbers', 'Cucumbers', 'خيار', 'produce', 1, 'kg', 25, 'week'),
    g('gi_onions', 'Onions', 'بصل', 'produce', 1.5, 'kg', 35, 'week'),
    g('gi_potatoes', 'Potatoes', 'بطاطس', 'produce', 2, 'kg', 45, 'week'),
    g('gi_lemons', 'Lemons', 'ليمون', 'produce', 0.5, 'kg', 30, 'week'),
    g('gi_garlic', 'Garlic', 'توم', 'produce', 250, 'g', 25, 'week', { haveIt: true }),
    g('gi_molokhia', 'Molokhia, frozen', 'ملوخية مجمدة', 'produce', 1.4, 'kg', 105, 'week'),
    g('gi_bananas', 'Bananas', 'موز', 'produce', 1.5, 'kg', 60, 'week'),
    g('gi_chicken', 'Chicken breast', 'صدور فراخ', 'meat', 1.5, 'kg', 495, 'week'),
    g('gi_fish', 'Fish fillet', 'فيليه سمك', 'meat', 0.6, 'kg', 150, 'week'),
    g('gi_beef', 'Beef mince', 'لحمة مفرومة', 'meat', 0.5, 'kg', 225, 'week'),
    g('gi_eggs', 'Eggs', 'بيض', 'dairy', 18, 'pcs', 120, 'week', { checked: true }),
    g('gi_milk', 'Milk', 'لبن', 'dairy', 3, 'L', 150, 'week'),
    g('gi_yogurt', 'Plain yogurt', 'زبادي', 'dairy', 7, 'cups', 105, 'week'),
    g('gi_cheese', 'White cheese', 'جبنة بيضا', 'dairy', 250, 'g', 50, 'week'),
    g('gi_bread', 'Baladi bread', 'عيش بلدي', 'bakery', 20, 'loaves', 40, 'week', { checked: true }),
    g('gi_rice', 'Rice', 'رز', 'pantry', 3, 'kg', 105, 'month'),
    g('gi_pasta', 'Pasta', 'مكرونة', 'pantry', 2, 'kg', 70, 'month'),
    g('gi_lentils', 'Brown lentils', 'عدس بجبة', 'pantry', 1, 'kg', 70, 'month'),
    g('gi_fava', 'Fava beans, dried', 'فول ناشف', 'pantry', 2, 'kg', 110, 'month'),
    g('gi_oats', 'Oats', 'شوفان', 'pantry', 1, 'kg', 90, 'month'),
    g('gi_olive_oil', 'Olive oil', 'زيت زيتون', 'pantry', 1, 'L', 350, 'month', { haveIt: true }),
    g('gi_tahini', 'Tahini', 'طحينة', 'pantry', 500, 'g', 90, 'month'),
    g('gi_cumin', 'Cumin', 'كمون', 'spices', 100, 'g', 30, 'month'),
    g('gi_coriander', 'Ground coriander', 'كزبرة ناشفة', 'spices', 100, 'g', 25, 'month'),
    g('gi_pepper', 'Black pepper', 'فلفل أسود', 'spices', 50, 'g', 30, 'month', { haveIt: true }),
    g('gi_paste', 'Tomato paste', 'صلصة طماطم', 'spices', 2, 'jars', 60, 'month'),
    g('gi_vinegar', 'Vinegar', 'خل', 'spices', 1, 'L', 20, 'month'),
    g('gi_salt', 'Salt', 'ملح', 'spices', 1, 'kg', 10, 'month', { haveIt: true }),
  ],
};

export const pantry: PantryItem[] = [
  { id: 'p_olive_oil', name: L('Olive oil', 'زيت زيتون'), level: 'plenty' },
  { id: 'p_salt', name: L('Salt', 'ملح'), level: 'plenty' },
  { id: 'p_pepper', name: L('Black pepper', 'فلفل أسود'), level: 'plenty' },
  { id: 'p_garlic', name: L('Garlic', 'توم'), level: 'plenty' },
  { id: 'p_cumin', name: L('Cumin', 'كمون'), level: 'low' },
  { id: 'p_rice', name: L('Rice', 'رز'), level: 'low' },
  { id: 'p_tea', name: L('Tea & sugar', 'شاي وسكر'), level: 'untracked' },
];

// ── Injuries ─────────────────────────────────────────────────────────
export const injuries: Injury[] = [
  {
    id: 'inj_shoulder_l',
    region: 'shoulderL', side: 'left', type: 'tendon', severity: 2,
    painfulMovements: ['overheadPress', 'dips'],
    restrictions: ['noOverhead'],
    status: 'recovering',
    since: '2026-09-11',
    painLog: [
      { date: '2026-09-13', pain: 6 }, { date: '2026-09-15', pain: 5 }, { date: '2026-09-18', pain: 5 },
      { date: '2026-09-20', pain: 4 }, { date: '2026-09-22', pain: 4 }, { date: '2026-09-24', pain: 4 },
      { date: '2026-09-25', pain: 3 }, { date: '2026-09-26', pain: 2 }, { date: '2026-09-28', pain: 3 },
    ],
    avoided: [
      { from: L('Barbell overhead press', 'ضغط أكتاف بالبار'), to: L('Landmine press', 'ضغط لاندماين') },
      { from: L('Barbell bench press', 'بنش بريس بالبار'), to: L('DB floor press', 'ضغط دمبل من الأرض') },
      { from: L('Parallel-bar dips', 'ديبس على المتوازي'), to: L('Pushdown', 'ترايسبس بالكابل') },
      { from: L('Upright row', 'رفرفة عمودية'), to: L('Removed', 'اتشال') },
    ],
    redFlags: { sharpPain: false, swelling: false, numbness: false, worsening: false },
  },
  {
    id: 'inj_knee_r',
    region: 'kneeR', side: 'right', type: 'sprain', severity: 1,
    painfulMovements: [], restrictions: [],
    status: 'resolved', since: '2025-03-02', painLog: [], avoided: [],
    redFlags: { sharpPain: false, swelling: false, numbness: false, worsening: false },
  },
];

// ── Check-in draft (pre-filled from this week's data) ───────────────
export const checkInDraft: CheckIn = {
  id: 'ci_w3',
  weekNumber: 3,
  body: { weightKg: 86.1, measurementsCm: { waist: 93, hips: 102, chest: 106, arm: 36, thigh: 60 }, photos: {} },
  training: { sessionsDone: 3, sessionsPlanned: 4, difficulty: 3, soreness: 2, exerciseFeedback: [{ exerciseId: 'ex_db_floor_press', feel: 'tooEasy' }, { exerciseId: 'ex_lat_pulldown', feel: 'uncomfortable' }] },
  injuries: [{ injuryId: 'inj_shoulder_l', pain: 2, trend: 'better' }],
  newPainRegions: [],
  redFlags: { sharpPain: false, swelling: false, numbness: false },
  nutrition: { adherencePct: 80, hunger: 4, mealsToChange: ['m_fish_sayadeya'], moreOf: ['chicken', 'eggs'], lessOf: ['fish'] },
  life: { sleep: 3, energy: 4, stress: 3, daysAvailable: 4, obstacles: ['work'] },
  note: 'Work was crazy on Thursday so I missed Upper B. Shoulder felt fine on the landmine press but a bit tight on lat pulldowns.',
};

/** Previous measurements, shown as "was …" in the check-in. */
export const lastCheckIn = { weightKg: 86.8, measurementsCm: { waist: 94, hips: 102.5, chest: 106, arm: 36, thigh: 60.5 } };

/** Meals & foods the check-in lets the user pick from. */
export const checkInMealOptions = [
  { id: 'm_ful_eggs', name: L('Ful & eggs', 'فول وبيض') },
  { id: 'm_koshary', name: L('Koshary', 'كشري') },
  { id: 'm_fish_sayadeya', name: L('Fish sayadeya', 'صيادية سمك') },
  { id: 'm_kofta', name: L('Beef kofta', 'كفتة') },
  { id: 'm_zabadi_oats', name: L('Zabadi & oats', 'زبادي وشوفان') },
];

// ── Weekly reviews ───────────────────────────────────────────────────
export const reviews: WeeklyReview[] = [
  {
    id: 'rv_w3', weekNumber: 3, start: '2026-09-22', end: '2026-09-28', state: 'ready', status: 'onTrack',
    summary: L(
      "A solid week, Omar. You're down 0.7 kg — a little faster than planned — and your shoulder is clearly settling. Work cost you Thursday's session, and you were hungry most evenings. We've eased the deficit slightly and moved things around so next week is easier to hit.",
      'أسبوع كويس يا عمر. نزلت 0.7 كجم — أسرع شوية من المخطط — وكتفك واضح إنه بيتحسن. الشغل ضيّع عليك تمرين الخميس، وكنت جعان أغلب الليالي. خففنا العجز شوية ورتبنا الأيام عشان الأسبوع الجاي يبقى أسهل.',
    ),
    shortSummary: L('Down 0.7 kg, shoulder settling. +100 kcal on training days.', 'نزلت 0.7 كجم، والكتف بيتحسن. +100 سعرة في أيام التمرين.'),
    stats: { weightChangeKg: -0.7, sessionsDone: 3, sessionsPlanned: 4, pain: 2 },
    changes: [
      { kind: 'calories', what: L('2,200 → 2,300 kcal on training days', '2,200 ← 2,300 سعرة في أيام التمرين'), why: L('You lost 0.7 kg (goal 0.5) and felt hungry most evenings. The extra 100 kcal is carbs around your sessions, so rest days stay at 2,200.', 'نزلت 0.7 كجم (الهدف نص كيلو) وكنت جعان أغلب الليالي. الـ 100 سعرة الزيادة كربوهيدرات حوالين التمرين، وأيام الراحة تفضل 2,200.'), citation: L('Helms · Muscle & Strength Pyramid: Nutrition', 'هيلمز · هرم العضلات والقوة: التغذية') },
      { kind: 'exercise', what: L('Floor press: 24 → 26 kg dumbbells', 'ضغط الأرض: دمبل 24 ← 26 كجم'), why: L('You marked it "too easy" and hit the top of the rep range at RPE 7 with no shoulder pain.', 'قلت إنه "سهل أوي" ووصلت لآخر مدى العدّات بمجهود 7 من غير ألم.'), citation: L('Israetel · Scientific Principles of Hypertrophy', 'إسرائيتل · المبادئ العلمية للتضخيم') },
      { kind: 'exercise', what: L('Lat pulldown → half-kneeling single-arm cable pulldown', 'السحب العلوي ← سحب كابل بإيد واحدة على ركبة'), why: L('It felt uncomfortable on your left shoulder. One arm at a time lets you choose a pain-free angle.', 'كان مضايق كتفك الأيسر. إيد واحدة بتسمحلك تختار زاوية مريحة من غير ألم.'), citation: L('NSCA · Essentials of Strength Training', 'NSCA · أساسيات تدريب القوة') },
      { kind: 'meals', what: L('Fish sayadeya → grilled chicken & potatoes (Wed)', 'صيادية سمك ← فراخ مشوية وبطاطس (الأربع)'), why: L('You asked for less fish and more chicken. Same calories, +6 g protein.', 'طلبت سمك أقل وفراخ أكتر. نفس السعرات و+6 جم بروتين.'), citation: L('Helms · Muscle & Strength Pyramid: Nutrition', 'هيلمز · هرم العضلات والقوة: التغذية') },
    ],
    focus: [
      L("Train Sat, Mon, Tue, Thu — Upper B moves to Tuesday so a busy Thursday doesn't cost a session.", 'تمرّن السبت والاثنين والتلات والخميس — العلوي ب اتنقل للتلات عشان لو الخميس زحمة.'),
      L('Aim for 7 hours of sleep on at least 4 nights.', 'حاول تنام 7 ساعات على الأقل 4 ليالي.'),
      L('Keep the shoulder easy: stop any set that goes above 3/10 pain.', 'خلّي بالك من كتفك: وقّف أي مجموعة لو الألم عدّى 3/10.'),
    ],
    groceryUpdate: { note: L('Fish fillet added', 'اتضاف فيليه سمك'), totalEgp: 1685 },
  },
  {
    id: 'rv_w2', weekNumber: 2, start: '2026-09-15', end: '2026-09-21', state: 'ready', status: 'onTrack',
    summary: L('Four of four sessions — great consistency. Your shoulder is calming down, so we added 2.5 kg to the floor press. Koshary moved to training days, when you need the carbs most.', 'أربع جلسات من أربع — التزام رائع. كتفك بيهدى، فزودنا 2.5 كجم على الضغط من الأرض. الكشري اتنقل لأيام التمرين، لما بتحتاج الكربوهيدرات أكتر.'),
    shortSummary: L('4 of 4 sessions. Floor press +2.5 kg, koshary moved to training days.', '4 من 4 جلسات. ضغط الأرض +2.5 كجم، والكشري لأيام التمرين.'),
    stats: { weightChangeKg: -0.6, sessionsDone: 4, sessionsPlanned: 4, pain: 4 },
    changes: [], focus: [],
  },
  {
    id: 'rv_w1', weekNumber: 1, start: '2026-09-11', end: '2026-09-14', state: 'ready', status: 'attention',
    summary: L('Shoulder at 6/10 after pressing. We added face pulls and lowered pressing effort.', 'الكتف وصل 6/10 بعد الضغط. ضفنا سحب للوجه وقللنا مجهود الضغط.'),
    shortSummary: L('Shoulder at 6/10 after pressing. Added face pulls, lowered pressing effort.', 'الكتف 6/10 بعد الضغط. ضفنا سحب للوجه وقللنا المجهود.'),
    stats: { weightChangeKg: -0.6, sessionsDone: 2, sessionsPlanned: 2, pain: 6 },
    changes: [], focus: [],
  },
];

// ── Progress ─────────────────────────────────────────────────────────
const wKg = [88.0, 87.8, 88.1, 87.6, 87.7, 87.4, 87.5, 87.2, 87.3, 86.9, 87.0, 86.8, 86.9, 86.5, 86.6, 86.3, 86.4, 86.1];
export const progress: Progress = {
  since: '2026-09-11',
  weights: wKg.map((kg, i) => ({ date: new Date(Date.UTC(2026, 8, 11 + i)).toISOString().slice(0, 10), kg })),
  measurements: [
    { date: '2026-09-11', waist: 96, hips: 103.5, chest: 107, arm: 36, thigh: 61 },
    { date: '2026-09-15', waist: 95, hips: 103, chest: 106.5, arm: 36, thigh: 61 },
    { date: '2026-09-22', waist: 94, hips: 102.5, chest: 106, arm: 36, thigh: 60.5 },
    { date: '2026-09-28', waist: 93, hips: 102, chest: 106, arm: 36, thigh: 60 },
  ],
  lifts: [
    { exerciseId: 'ex_db_floor_press', name: L('Floor press', 'ضغط الأرض'), unit: L('kg per dumbbell', 'كجم لكل دمبل'), points: [{ date: '2026-09-13', kg: 20 }, { date: '2026-09-15', kg: 20 }, { date: '2026-09-20', kg: 22.5 }, { date: '2026-09-22', kg: 22.5 }, { date: '2026-09-24', kg: 22.5 }, { date: '2026-09-28', kg: 24 }] },
    { exerciseId: 'ex_rdl', name: L('Romanian deadlift', 'رفعة ميتة رومانية'), unit: L('kg', 'كجم'), points: [{ date: '2026-09-12', kg: 80 }, { date: '2026-09-19', kg: 85 }, { date: '2026-09-26', kg: 90 }] },
    { exerciseId: 'ex_leg_press', name: L('Leg press', 'دفع رجلين'), unit: L('kg', 'كجم'), points: [{ date: '2026-09-12', kg: 160 }, { date: '2026-09-19', kg: 180 }, { date: '2026-09-26', kg: 180 }] },
  ],
  records: [
    { exerciseId: 'ex_db_floor_press', name: L('Dumbbell floor press', 'ضغط دمبل من الأرض'), date: '2026-09-28', value: L('2 × 24 kg × 10', '2 × 24 كجم × 10') },
    { exerciseId: 'ex_rdl', name: L('Romanian deadlift', 'رفعة ميتة رومانية'), date: '2026-09-26', value: L('90 kg × 8', '90 كجم × 8') },
    { exerciseId: 'ex_leg_press', name: L('Leg press', 'دفع رجلين'), date: '2026-09-19', value: L('180 kg × 12', '180 كجم × 12') },
  ],
  photos: [{ date: '2026-09-11', view: 'front' }, { date: '2026-09-28', view: 'front' }],
};

export const nextCheckIn = { date: '2026-09-28', due: true };
