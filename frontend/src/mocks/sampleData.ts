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
  food: { mealsPerDay: 4, dislikes: ['liver', 'eggplant'], allergies: [], fasting: ['ramadan'], cookingMinutes: 30 },
  language: 'en',
  theme: 'system',
  memberSince: '2026-09-11',
};

// ── Exercises ────────────────────────────────────────────────────────
// Demonstration photos: Free Exercise DB (github.com/yuhonas/free-exercise-db), Unlicense / public domain.
// Videos: YouTube searches for now; the real links come from the program PDFs next session.
const freeExerciseDb = { name: 'Free Exercise DB', license: 'Unlicense (public domain)' };
export const exercises: Exercise[] = [
  {
    id: 'ex_db_floor_press',
    name: L('Neutral-grip dumbbell floor press', 'ضغط دمبل من الأرض بقبضة محايدة'),
    description: L('A chest press lying on the floor. The floor limits the range, which is kinder to sore shoulders. Trains chest and triceps.', 'ضغط صدر وأنت نايم على الأرض. الأرض بتحدّ المدى، وده أريح للكتف. بيشتغل على الصدر والترايسبس.'),
    imageUrl: '/exercises/Dumbbell_Floor_Press/0.jpg',
    imageFrames: ['/exercises/Dumbbell_Floor_Press/1.jpg'],
    videoUrl: 'https://www.youtube.com/results?search_query=Neutral+grip+dumbbell+floor+press+proper+form',
    mediaSource: { ...freeExerciseDb, url: 'https://github.com/yuhonas/free-exercise-db/tree/main/exercises/Dumbbell_Floor_Press' },
    muscles: { primary: ['chest'], secondary: ['armL', 'armR', 'shoulderL', 'shoulderR'] },
    muscleNames: L('Chest · triceps, front shoulders', 'الصدر · الترايسبس، مقدمة الكتف'),
    instructions: [
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
    description: L('A row lying face-down on an incline bench, so your lower back rests while your upper back works.', 'تجديف وأنت نايم على بطنك على بنش مائل، فأسفل ظهرك مرتاح وأعلى ظهرك هو اللي بيشتغل.'),
    imageUrl: '/exercises/Dumbbell_Incline_Row/0.jpg',
    imageFrames: ['/exercises/Dumbbell_Incline_Row/1.jpg'],
    videoUrl: 'https://www.youtube.com/results?search_query=Chest+supported+dumbbell+row+proper+form',
    mediaSource: { ...freeExerciseDb, url: 'https://github.com/yuhonas/free-exercise-db/tree/main/exercises/Dumbbell_Incline_Row' },
    muscles: { primary: ['upperBack'], secondary: ['armL', 'armR'] },
    muscleNames: L('Upper back · biceps', 'أعلى الظهر · البايسبس'),
    instructions: [
      L('Set a bench to about 30–45° and lie chest-down, a dumbbell in each hand, arms hanging straight.', 'اظبط البنش على 30–45 درجة ونام على بطنك، ودمبل في كل إيد ودراعك متدلّي.'),
      L('Pull the dumbbells up and back towards your hips.', 'اسحب الدمبل لفوق ولورا ناحية وسطك.'),
      L('Pause for a second with your shoulder blades squeezed.', 'اثبت ثانية ولوحي الكتف مضغوطين.'),
      L('Lower slowly until your arms are straight again.', 'نزّل ببطء لحد ما دراعك يفرد تاني.'),
    ],
    cues: [
      L('Lead with your elbows', 'الكوع هو اللي يقود الحركة'),
      L('Squeeze shoulder blades together', 'اضغط لوحي الكتف على بعض'),
      L('Keep your chest on the bench', 'صدرك لازق في البنش'),
      L('Look down, neck long', 'بصّ لتحت، ورقبتك مفرودة'),
    ],
    mistakes: [
      L('Shrugging to your ears', 'رفع الكتف ناحية الودن'),
      L('Lifting the chest off the bench to swing the weight', 'رفع صدرك من على البنش عشان تمرجح الوزن'),
      L('Cutting the range short at the bottom', 'تقصير المدى من تحت'),
    ],
    alternatives: [{ name: L('Seated cable row', 'تجديف بالكابل قاعد'), kind: 'easier' }],
  },
  {
    id: 'ex_landmine_press',
    name: L('Half-kneeling landmine press', 'ضغط لاندماين على ركبة واحدة'),
    description: L('A one-arm press at an angle using a bar anchored in a corner. Trains the shoulders without pressing straight overhead.', 'ضغط بإيد واحدة بزاوية ببار متثبّت في الركن. بيشتغل على الكتف من غير رفع فوق الراس على طول.'),
    imageUrl: '/exercises/Single-Arm_Linear_Jammer/0.jpg',
    imageFrames: ['/exercises/Single-Arm_Linear_Jammer/1.jpg'],
    videoUrl: 'https://www.youtube.com/results?search_query=Half+kneeling+landmine+press+proper+form',
    mediaSource: { ...freeExerciseDb, url: 'https://github.com/yuhonas/free-exercise-db/tree/main/exercises/Single-Arm_Linear_Jammer', note: L('Closest match in the image library: standing version. Yours is half-kneeling.', 'أقرب صورة متاحة: النسخة وأنت واقف. تمرينك على ركبة واحدة.'), },
    muscles: { primary: ['shoulderL', 'shoulderR'], secondary: ['chest', 'armL', 'armR', 'abdomen'] },
    muscleNames: L('Front shoulders · upper chest, triceps, core', 'مقدمة الكتف · أعلى الصدر، الترايسبس، البطن'),
    instructions: [
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
    description: L('Pull a bar down to your chest while seated, palms facing each other. Builds the wide back muscles (lats) and biceps.', 'اسحب مسكة لحد صدرك وأنت قاعد، وكفوفك في وش بعض. بيبني عضلات الظهر العريضة والبايسبس.'),
    imageUrl: '/exercises/V-Bar_Pulldown/0.jpg',
    imageFrames: ['/exercises/V-Bar_Pulldown/1.jpg'],
    videoUrl: 'https://www.youtube.com/results?search_query=Neutral+grip+lat+pulldown+proper+form',
    mediaSource: { ...freeExerciseDb, url: 'https://github.com/yuhonas/free-exercise-db/tree/main/exercises/V-Bar_Pulldown' },
    muscles: { primary: ['upperBack'], secondary: ['armL', 'armR'] },
    muscleNames: L('Lats · biceps', 'عضلات الظهر الجانبية · البايسبس'),
    instructions: [
      L('Sit with your thighs locked under the pad and hold the neutral handle, palms facing each other.', 'اقعد ورجلك مثبّتة تحت المسند، وامسك المسكة المحايدة وكفوفك في وش بعض.'),
      L('Lean back very slightly and lift your chest.', 'ارجع لورا سنّة صغيرة وارفع صدرك.'),
      L('Pull the handle to your upper chest, driving your elbows down.', 'اسحب المسكة لأعلى صدرك وانت بتنزّل كوعك لتحت.'),
      L('Let it rise slowly until your arms are straight.', 'سيبها تطلع ببطء لحد ما دراعك يفرد.'),
    ],
    cues: [
      L('Chest up to the handle', 'صدرك يطلع للمسكة'),
      L('Elbows down to your back pockets', 'الكوع ينزل ناحية جيوبك اللي ورا'),
      L('Shoulders away from your ears', 'الكتف بعيد عن ودانك'),
      L('Control the way up', 'اتحكّم في الطلعة'),
    ],
    mistakes: [
      L('Leaning far back', 'الرجوع لورا كتير'),
      L('Pulling with the arms only', 'السحب بالدراع بس'),
      L('Letting the weight yank you up', 'تسيب الوزن يشدّك لفوق فجأة'),
    ],
    alternatives: [{ name: L('Half-kneeling single-arm cable pulldown', 'سحب كابل بإيد واحدة على ركبة'), kind: 'injuryFriendly' }],
  },
  {
    id: 'ex_face_pull',
    name: L('Cable face pull', 'سحب للوجه بالكابل'),
    description: L('Pull a rope towards your face on a cable machine. Strengthens the rear shoulders and upper back, which helps shoulder health.', 'اسحب حبل ناحية وشك على جهاز الكابل. بيقوّي خلفية الكتف وأعلى الظهر، وده مفيد لصحة الكتف.'),
    imageUrl: '/exercises/Face_Pull/0.jpg',
    imageFrames: ['/exercises/Face_Pull/1.jpg'],
    videoUrl: 'https://www.youtube.com/results?search_query=Cable+face+pull+proper+form',
    mediaSource: { ...freeExerciseDb, url: 'https://github.com/yuhonas/free-exercise-db/tree/main/exercises/Face_Pull' },
    muscles: { primary: ['shoulderL', 'shoulderR'], secondary: ['upperBack'] },
    muscleNames: L('Rear shoulders · upper back', 'خلفية الكتف · أعلى الظهر'),
    instructions: [
      L('Set a rope on a cable at face height and hold it with thumbs pointing back towards you.', 'ثبّت الحبل في الكابل على مستوى وشك وامسكه والإبهام ناحيتك.'),
      L('Step back until your arms are straight, feet shoulder-width apart.', 'ارجع لورا لحد ما دراعك يفرد، ورجليك بعرض كتفك.'),
      L('Pull the rope towards your forehead, separating your hands as it comes in.', 'اسحب الحبل ناحية جبهتك وافتح إيديك وهو جاي.'),
      L('Hold one second, then return slowly.', 'اثبت ثانية، ورجّع ببطء.'),
    ],
    cues: [
      L('Thumbs point back at the end', 'الإبهام يشاور لورا في الآخر'),
      L('Elbows high, level with your hands', 'الكوع عالي، على مستوى إيدك'),
      L('Squeeze the back of your shoulders', 'اعصر خلفية الكتف'),
      L('Stand tall, no leaning', 'اقف مفرود من غير ميل'),
    ],
    mistakes: [
      L('Using too much weight', 'وزن تقيل زيادة'),
      L('Leaning back to pull', 'الميل لورا عشان تسحب'),
      L('Letting the elbows drop low', 'نزول الكوع لتحت'),
    ],
    alternatives: [{ name: L('Band pull-apart', 'فتح استك'), kind: 'easier' }],
  },
  {
    id: 'ex_pushdown',
    name: L('Cable triceps pushdown', 'ترايسبس بالكابل'),
    description: L('Push a cable bar down with your elbows pinned to your sides. Isolates the triceps at the back of the arm.', 'ادفع بار الكابل لتحت والكوع لازق في جنبك. بيركّز على الترايسبس في ضهر الدراع.'),
    imageUrl: '/exercises/Triceps_Pushdown/0.jpg',
    imageFrames: ['/exercises/Triceps_Pushdown/1.jpg'],
    videoUrl: 'https://www.youtube.com/results?search_query=Cable+triceps+pushdown+proper+form',
    mediaSource: { ...freeExerciseDb, url: 'https://github.com/yuhonas/free-exercise-db/tree/main/exercises/Triceps_Pushdown' },
    muscles: { primary: ['armL', 'armR'], secondary: [] },
    muscleNames: L('Triceps', 'الترايسبس'),
    instructions: [
      L('Stand facing a high cable with a bar, hands shoulder-width, elbows at your sides.', 'اقف قدام كابل عالي فيه بار، إيديك بعرض كتفك والكوع جنبك.'),
      L('Push the bar down until your arms are straight.', 'ادفع البار لتحت لحد ما دراعك يفرد.'),
      L('Squeeze your triceps for a second at the bottom.', 'اعصر الترايسبس ثانية تحت.'),
      L('Let the bar rise slowly to chest height.', 'سيب البار يطلع ببطء لحد صدرك.'),
    ],
    cues: [
      L('Elbows stay still', 'الكوع ثابت'),
      L('Slight forward lean from the hips', 'ميل بسيط لقدام من الوسط'),
      L('Wrists straight', 'الرسغ مفرود'),
      L('Full lockout every rep', 'افرد دراعك على الآخر كل عدّة'),
    ],
    mistakes: [
      L('Leaning over the bar', 'الميل على البار'),
      L('Elbows drifting forward', 'الكوع يروح لقدام'),
      L('Using your body weight to push', 'تدفع بوزن جسمك'),
    ],
    alternatives: [{ name: L('Band pushdown', 'ترايسبس بالاستك'), kind: 'easier' }],
  },
  {
    id: 'ex_incline_curl',
    name: L('Incline dumbbell curl', 'بايسبس دمبل على بنش مائل'),
    description: L('A biceps curl lying back on an incline bench, which stretches the biceps for more work per rep.', 'بايسبس وأنت مسنود على بنش مائل، وده بيمدّ البايسبس فكل عدّة بتشتغل أكتر.'),
    imageUrl: '/exercises/Incline_Dumbbell_Curl/0.jpg',
    imageFrames: ['/exercises/Incline_Dumbbell_Curl/1.jpg'],
    videoUrl: 'https://www.youtube.com/results?search_query=Incline+dumbbell+curl+proper+form',
    mediaSource: { ...freeExerciseDb, url: 'https://github.com/yuhonas/free-exercise-db/tree/main/exercises/Incline_Dumbbell_Curl' },
    muscles: { primary: ['armL', 'armR'], secondary: ['forearmL', 'forearmR'] },
    muscleNames: L('Biceps · forearms', 'البايسبس · الساعد'),
    instructions: [
      L('Set a bench to 45° and sit back, a dumbbell in each hand, arms hanging straight down.', 'اظبط البنش على 45 درجة واسند ظهرك، ودمبل في كل إيد ودراعك متدلّي.'),
      L('Curl both dumbbells up, palms facing up.', 'ارفع الدمبلين لفوق وكفوفك لفوق.'),
      L('Squeeze your biceps at the top.', 'اعصر البايسبس فوق.'),
      L('Lower slowly until your arms are fully straight.', 'نزّل ببطء لحد ما دراعك يفرد خالص.'),
    ],
    cues: [
      L('Keep upper arms still', 'الدراع من فوق ثابت'),
      L('Head and back stay on the bench', 'راسك وظهرك على البنش'),
      L('Lower for 2–3 seconds', 'نزّل في 2–3 ثواني'),
    ],
    mistakes: [
      L('Swinging the weights', 'مرجحة الأوزان'),
      L('Bringing the elbows forward at the top', 'تقديم الكوع لقدام فوق'),
      L('Stopping short of a full stretch', 'ماتفردش دراعك للآخر تحت'),
    ],
    alternatives: [{ name: L('Cable curl', 'بايسبس بالكابل'), kind: 'easier' }],
  },
  {
    id: 'ex_goblet_squat',
    name: L('Goblet squat', 'سكوات جوبلت'),
    description: L('A squat holding one dumbbell at your chest. The weight in front keeps you upright, so it is easy to learn. Trains thighs and glutes.', 'سكوات وأنت شايل دمبل واحد قدام صدرك. الوزن من قدام بيخليك واقف مفرود، فسهل تتعلمه. بيشتغل على الفخد والمؤخرة.'),
    imageUrl: '/exercises/Goblet_Squat/0.jpg',
    imageFrames: ['/exercises/Goblet_Squat/1.jpg'],
    videoUrl: 'https://www.youtube.com/results?search_query=Goblet+squat+proper+form',
    mediaSource: { ...freeExerciseDb, url: 'https://github.com/yuhonas/free-exercise-db/tree/main/exercises/Goblet_Squat' },
    muscles: { primary: ['thighL', 'thighR'], secondary: ['hipL', 'hipR'] },
    muscleNames: L('Front thighs, glutes · inner thighs', 'الفخد الأمامية، المؤخرة · الفخد الداخلية'),
    instructions: [
      L('Hold one dumbbell upright against your chest with both hands, feet a little wider than your hips.', 'امسك دمبل واحد واقف على صدرك بإيديك الاتنين، ورجليك أوسع شوية من وسطك.'),
      L('Sit down between your heels, keeping your chest up.', 'انزل كأنك بتقعد بين كعوبك، وصدرك لفوق.'),
      L('Go as low as you can with a flat back.', 'انزل لأوطى نقطة تقدر عليها وضهرك مفرود.'),
      L('Push the floor away to stand back up.', 'ادفع الأرض بقوة عشان تقوم.'),
    ],
    cues: [
      L('Knees follow your toes', 'الركبة في اتجاه صوابع رجلك'),
      L('Whole foot on the floor', 'رجلك كلها على الأرض'),
      L('Elbows inside the knees at the bottom', 'الكوع جوه الركبة تحت'),
    ],
    mistakes: [
      L('Heels lifting off the floor', 'الكعب يترفع من الأرض'),
      L('Knees caving inwards', 'الركبة تدخل لجوه'),
      L('Rounding the lower back at the bottom', 'تقويس أسفل الضهر تحت'),
    ],
    alternatives: [{ name: L('Bodyweight box squat', 'سكوات على كرسي بوزن الجسم'), kind: 'easier' }],
  },
  {
    id: 'ex_db_rdl',
    name: L('Dumbbell Romanian deadlift', 'رفعة رومانية بالدمبل'),
    description: L('A hip hinge with dumbbells: push your hips back with soft knees until you feel the back of your thighs stretch. Trains hamstrings and glutes.', 'ثني من الوسط بالدمبل: ارجع بوسطك لورا وركبتك مثنية سنة لحد ما تحس بشد في ضهر الفخد. بيشتغل على الفخد الخلفية والمؤخرة.'),
    imageUrl: '/exercises/Stiff-Legged_Dumbbell_Deadlift/0.jpg',
    imageFrames: ['/exercises/Stiff-Legged_Dumbbell_Deadlift/1.jpg'],
    videoUrl: 'https://www.youtube.com/results?search_query=Dumbbell+Romanian+deadlift+proper+form',
    mediaSource: { ...freeExerciseDb, url: 'https://github.com/yuhonas/free-exercise-db/tree/main/exercises/Stiff-Legged_Dumbbell_Deadlift' },
    muscles: { primary: ['thighL', 'thighR', 'hipL', 'hipR'], secondary: ['lowerBack'] },
    muscleNames: L('Hamstrings, glutes · lower back', 'الفخد الخلفية، المؤخرة · أسفل الضهر'),
    instructions: [
      L('Stand tall with a dumbbell in each hand in front of your thighs.', 'اقف مفرود ودمبل في كل إيد قدام فخدك.'),
      L('Bend your knees slightly and push your hips back.', 'اثني ركبتك سنة وارجع بوسطك لورا.'),
      L('Slide the dumbbells down your legs until you feel a strong stretch.', 'نزّل الدمبل جنب رجلك لحد ما تحس بشد قوي.'),
      L('Drive your hips forward to stand up.', 'ادفع وسطك لقدام عشان تقوم.'),
    ],
    cues: [
      L('Back flat the whole time', 'ضهرك مفرود طول الوقت'),
      L('Dumbbells close to your legs', 'الدمبل قريب من رجلك'),
      L('Hips go back, not down', 'وسطك يرجع لورا، مش ينزل لتحت'),
    ],
    mistakes: [
      L('Rounding the back to reach lower', 'تقوّس ضهرك عشان تنزل أكتر'),
      L('Turning it into a squat', 'تحولها لسكوات'),
      L('Leaning back at the top', 'تميل لورا فوق'),
    ],
    alternatives: [{ name: L('Glute bridge', 'رفع الحوض من الأرض'), kind: 'easier' }],
  },
  {
    id: 'ex_leg_press',
    name: L('Leg press', 'ليج برس'),
    description: L('A machine squat: you push a weighted platform away with your legs while your back stays supported. Trains thighs and glutes.', 'سكوات على الجهاز: بتزق منصة عليها وزن برجلك وضهرك مسنود. بيشتغل على الفخد والمؤخرة.'),
    imageUrl: '/exercises/Leg_Press/0.jpg',
    imageFrames: ['/exercises/Leg_Press/1.jpg'],
    videoUrl: 'https://www.youtube.com/results?search_query=Leg+press+proper+form',
    mediaSource: { ...freeExerciseDb, url: 'https://github.com/yuhonas/free-exercise-db/tree/main/exercises/Leg_Press' },
    muscles: { primary: ['thighL', 'thighR'], secondary: ['hipL', 'hipR'] },
    muscleNames: L('Front thighs · glutes', 'الفخد الأمامية · المؤخرة'),
    instructions: [
      L('Sit with your back flat on the pad, feet hip-width in the middle of the platform.', 'اقعد وضهرك لازق في المسند، ورجليك بعرض وسطك في نص المنصة.'),
      L('Release the safety handles.', 'فك مساكات الأمان.'),
      L('Lower the platform until your knees are bent to about 90°.', 'نزّل المنصة لحد ما ركبتك تتني حوالي 90 درجة.'),
      L('Press back up without locking your knees.', 'ادفع لفوق من غير ما تقفل ركبتك.'),
    ],
    cues: [
      L('Lower back stays on the pad', 'أسفل ضهرك لازق في المسند'),
      L('Push through your heels', 'ادفع بكعبك'),
      L('Knees in line with your feet', 'ركبتك على خط رجلك'),
    ],
    mistakes: [
      L('Locking the knees at the top', 'قفل الركبة فوق'),
      L('Hips rolling off the seat at the bottom', 'وسطك يترفع من الكرسي تحت'),
    ],
    alternatives: [{ name: L('Goblet squat', 'سكوات جوبلت'), kind: 'equipment' }],
  },
  {
    id: 'ex_seated_leg_curl',
    name: L('Seated leg curl', 'ثني رجل وأنت قاعد'),
    description: L('A machine curl for the back of the thighs, done seated so the hamstrings work in a long position.', 'تمرين جهاز لضهر الفخد، وأنت قاعد فالعضلة بتشتغل وهي ممدودة.'),
    imageUrl: '/exercises/Seated_Leg_Curl/0.jpg',
    imageFrames: ['/exercises/Seated_Leg_Curl/1.jpg'],
    videoUrl: 'https://www.youtube.com/results?search_query=Seated+leg+curl+proper+form',
    mediaSource: { ...freeExerciseDb, url: 'https://github.com/yuhonas/free-exercise-db/tree/main/exercises/Seated_Leg_Curl' },
    muscles: { primary: ['thighL', 'thighR'], secondary: ['shinL', 'shinR'] },
    muscleNames: L('Hamstrings · calves', 'الفخد الخلفية · السمانة'),
    instructions: [
      L('Sit with the pad just above your heels and the thigh pad locked down.', 'اقعد والمسند فوق كعبك على طول، ومسند الفخد مقفول عليك.'),
      L('Curl your heels down and back as far as you can.', 'اسحب كعبك لتحت ولورا على قد ما تقدر.'),
      L('Pause for a second.', 'اثبت ثانية.'),
      L('Let your legs come back up slowly.', 'رجّع رجلك لفوق ببطء.'),
    ],
    cues: [
      L('Hips stay on the seat', 'وسطك على الكرسي'),
      L('Slow on the way back', 'ببطء وأنت راجع'),
      L('Point your toes up', 'صوابع رجلك لفوق'),
    ],
    mistakes: [
      L('Jerking the weight', 'شد الوزن بعنف'),
      L('Cutting the range short', 'تقصير المدى'),
    ],
    alternatives: [{ name: L('Lying leg curl', 'ثني رجل وأنت نايم'), kind: 'equipment' }],
  },
  {
    id: 'ex_calf_raise',
    name: L('Standing calf raise', 'سمانة واقف'),
    description: L('Rising onto your toes against a weight, with a full stretch at the bottom. Trains the calves.', 'تطلع على صوابع رجلك وعليك وزن، مع مدّة كاملة تحت. بيشتغل على السمانة.'),
    imageUrl: '/exercises/Standing_Calf_Raises/0.jpg',
    imageFrames: ['/exercises/Standing_Calf_Raises/1.jpg'],
    videoUrl: 'https://www.youtube.com/results?search_query=Standing+calf+raise+proper+form',
    mediaSource: { ...freeExerciseDb, url: 'https://github.com/yuhonas/free-exercise-db/tree/main/exercises/Standing_Calf_Raises' },
    muscles: { primary: ['shinL', 'shinR'], secondary: [] },
    muscleNames: L('Calves', 'السمانة'),
    instructions: [
      L('Stand with the balls of your feet on the step and the pads on your shoulders.', 'اقف ومقدمة رجلك على الحافة والمساند على كتفك.'),
      L('Lower your heels as far as they go.', 'نزّل كعبك لآخره.'),
      L('Rise up onto your toes as high as you can.', 'اطلع على صوابعك لأعلى نقطة.'),
      L('Hold for a second at the top, then lower slowly.', 'اثبت ثانية فوق، وبعدين نزّل ببطء.'),
    ],
    cues: [
      L('Pause in the stretch at the bottom', 'اثبت في المدّة تحت'),
      L('Knees straight but not locked', 'ركبتك مفرودة من غير قفل'),
      L('Push through your big toe', 'ادفع بالصباع الكبير'),
    ],
    mistakes: [
      L('Bouncing at the bottom', 'النط تحت'),
      L('Half reps', 'عدّات نص مدى'),
    ],
    alternatives: [{ name: L('Calf raise on a step, bodyweight', 'سمانة على سلمة بوزن الجسم'), kind: 'easier' }],
  },
  {
    id: 'ex_split_squat',
    name: L('Dumbbell split squat', 'سبليت سكوات بالدمبل'),
    description: L('A staggered-stance squat with a dumbbell in each hand, one leg at a time. Trains thighs and glutes and evens out left and right.', 'سكوات ورجل قدام ورجل ورا ودمبل في كل إيد، رجل رجل. بيشتغل على الفخد والمؤخرة وبيعادل بين الشمال واليمين.'),
    imageUrl: '/exercises/Split_Squat_with_Dumbbells/0.jpg',
    imageFrames: ['/exercises/Split_Squat_with_Dumbbells/1.jpg'],
    videoUrl: 'https://www.youtube.com/results?search_query=Dumbbell+split+squat+proper+form',
    mediaSource: { ...freeExerciseDb, url: 'https://github.com/yuhonas/free-exercise-db/tree/main/exercises/Split_Squat_with_Dumbbells' },
    muscles: { primary: ['thighL', 'thighR', 'hipL', 'hipR'], secondary: [] },
    muscleNames: L('Front thighs, glutes', 'الفخد الأمامية، المؤخرة'),
    instructions: [
      L('Take a long step forward, a dumbbell in each hand, back heel off the floor.', 'خد خطوة طويلة لقدام، ودمبل في كل إيد، وكعب الرجل اللي ورا مرفوع.'),
      L('Lower straight down until your back knee nearly touches the floor.', 'انزل على طول لتحت لحد ما ركبة الرجل اللي ورا تقرب من الأرض.'),
      L('Push through your front foot to come back up.', 'ادفع برجلك اللي قدام عشان تطلع.'),
      L('Do all the reps, then switch legs.', 'خلّص العدّات وبعدين بدّل الرجل.'),
    ],
    cues: [
      L('Torso upright', 'جسمك مفرود'),
      L('Front knee over the middle of the foot', 'الركبة اللي قدام فوق نص الرجل'),
      L('Go down, not forward', 'انزل لتحت، مش لقدام'),
    ],
    mistakes: [
      L('Stance too narrow, like a tightrope', 'الرجلين على خط واحد كأنك ماشي على حبل'),
      L('Pushing off the back leg', 'تدفع بالرجل اللي ورا'),
    ],
    alternatives: [{ name: L('Split squat holding a support, bodyweight', 'سبليت سكوات بوزن الجسم وأنت ماسك حاجة'), kind: 'easier' }],
  },
  {
    id: 'ex_leg_extension',
    name: L('Leg extension', 'ليج إكستنشن'),
    description: L('A machine exercise that straightens the knee against a pad. Trains the front of the thighs on their own.', 'تمرين جهاز بتفرد فيه ركبتك ضد مسند. بيشتغل على الفخد الأمامية لوحدها.'),
    imageUrl: '/exercises/Leg_Extensions/0.jpg',
    imageFrames: ['/exercises/Leg_Extensions/1.jpg'],
    videoUrl: 'https://www.youtube.com/results?search_query=Leg+extension+proper+form',
    mediaSource: { ...freeExerciseDb, url: 'https://github.com/yuhonas/free-exercise-db/tree/main/exercises/Leg_Extensions' },
    muscles: { primary: ['thighL', 'thighR'], secondary: [] },
    muscleNames: L('Front thighs', 'الفخد الأمامية'),
    instructions: [
      L('Sit with your back on the pad and the roller on the front of your ankles.', 'اقعد وضهرك على المسند والرول قدام كاحلك.'),
      L('Straighten your legs until they are nearly locked.', 'افرد رجلك لحد ما تقرب تتفرد خالص.'),
      L('Squeeze the thighs for a second at the top.', 'اعصر الفخد ثانية فوق.'),
      L('Lower slowly to the start.', 'نزّل ببطء لمكان البداية.'),
    ],
    cues: [
      L('Hold the handles, stay seated', 'امسك المساكات وخليك قاعد'),
      L('Lower for 2–3 seconds', 'نزّل في 2–3 ثواني'),
      L('Knee in line with the machine\'s pivot', 'ركبتك على محور الجهاز'),
    ],
    mistakes: [
      L('Kicking the weight up', 'رمي الوزن لفوق'),
      L('Lifting the hips off the seat', 'رفع الوسط من الكرسي'),
    ],
    alternatives: [{ name: L('Wall sit', 'قعدة الحيطة'), kind: 'easier' }],
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
    { exerciseId: 'ex_db_floor_press', sets: 3, reps: '8–10', restSec: 120, rpe: 7, weightKg: 22.5, swap: { injuryId: 'inj_shoulder_l', kind: 'swapped' }, weightStepKg: 2, lastTime: { sets: 3, reps: 9, weightKg: 22.5, struggled: true } },
    { exerciseId: 'ex_cs_row', sets: 3, reps: '10–12', restSec: 90, rpe: 8, weightKg: 20, weightStepKg: 2, lastTime: { sets: 3, reps: 10, weightKg: 20, struggled: false } },
    { exerciseId: 'ex_landmine_press', sets: 3, reps: '10 each', restSec: 90, rpe: 7, weightKg: 15, swap: { injuryId: 'inj_shoulder_l', kind: 'swapped' }, weightStepKg: 2.5 },
    { exerciseId: 'ex_lat_pulldown', sets: 3, reps: '10–12', restSec: 90, rpe: 8, weightKg: 45, weightStepKg: 5 },
    { exerciseId: 'ex_face_pull', sets: 3, reps: '15', restSec: 60, rpe: 7, weightKg: 15, swap: { injuryId: 'inj_shoulder_l', kind: 'added' }, weightStepKg: 2.5 },
    { exerciseId: 'ex_pushdown', sets: 3, reps: '12', restSec: 60, rpe: 8, weightKg: 20, swap: { injuryId: 'inj_shoulder_l', kind: 'swapped' }, weightStepKg: 2.5 },
    { exerciseId: 'ex_incline_curl', sets: 2, reps: '12', restSec: 60, rpe: 8, weightKg: 10, weightStepKg: 1 },
  ],
};

const lowerA: Workout = {
  id: 'w3_lower_a',
  name: L('Lower body A', 'الجزء السفلي أ'),
  day: 'sat',
  date: '2026-09-26',
  status: 'done',
  estMinutes: 55,
  warmupMinutes: 6,
  exercises: [
    { exerciseId: 'ex_goblet_squat', sets: 3, reps: '8–10', restSec: 120, rpe: 7, weightKg: 24, weightStepKg: 2 },
    { exerciseId: 'ex_db_rdl', sets: 3, reps: '8–10', restSec: 120, rpe: 7, weightKg: 20, weightStepKg: 2 },
    { exerciseId: 'ex_leg_press', sets: 3, reps: '10–12', restSec: 120, rpe: 8, weightKg: 100, weightStepKg: 10 },
    { exerciseId: 'ex_seated_leg_curl', sets: 3, reps: '10–12', restSec: 90, rpe: 8, weightKg: 40, weightStepKg: 5 },
    { exerciseId: 'ex_calf_raise', sets: 3, reps: '12–15', restSec: 60, rpe: 8, weightKg: 50, weightStepKg: 5 },
  ],
  summary: { minutes: 52, setsDone: 14, setsTotal: 15, painByInjury: { inj_shoulder_l: 2 } },
  log: {
    effort: 7,
    results: {
      ex_goblet_squat: { sets: 3, reps: 10, weightKg: 24, struggled: false },
      ex_db_rdl: { sets: 3, reps: 10, weightKg: 20, struggled: false },
      ex_leg_press: { sets: 3, reps: 10, weightKg: 100, struggled: true },
      ex_seated_leg_curl: { sets: 3, reps: 12, weightKg: 40, struggled: false },
      ex_calf_raise: { sets: 2, reps: 15, weightKg: 50, struggled: false },
    },
  },
};

const lowerB: Workout = {
  id: 'w3_lower_b',
  name: L('Lower body B', 'الجزء السفلي ب'),
  day: 'wed',
  date: '2026-09-30',
  status: 'planned',
  estMinutes: 55,
  warmupMinutes: 6,
  exercises: [
    { exerciseId: 'ex_split_squat', sets: 3, reps: '8–10 each', restSec: 90, rpe: 7, weightKg: 10, weightStepKg: 2 },
    { exerciseId: 'ex_db_rdl', sets: 3, reps: '10–12', restSec: 120, rpe: 7, weightKg: 20, weightStepKg: 2, lastTime: { sets: 3, reps: 10, weightKg: 20, struggled: false } },
    { exerciseId: 'ex_leg_extension', sets: 3, reps: '12–15', restSec: 60, rpe: 8, weightKg: 35, weightStepKg: 5 },
    { exerciseId: 'ex_seated_leg_curl', sets: 3, reps: '12–15', restSec: 60, rpe: 8, weightKg: 35, weightStepKg: 5, lastTime: { sets: 3, reps: 12, weightKg: 40, struggled: false } },
    { exerciseId: 'ex_calf_raise', sets: 3, reps: '15', restSec: 60, rpe: 8, weightKg: 50, weightStepKg: 5, lastTime: { sets: 2, reps: 15, weightKg: 50, struggled: false } },
  ],
};

const upperB: Workout = {
  id: 'w3_upper_b',
  name: L('Upper body B', 'الجزء العلوي ب'),
  day: 'thu',
  date: '2026-10-01',
  status: 'planned',
  estMinutes: 58,
  warmupMinutes: 6,
  exercises: [
    { exerciseId: 'ex_cs_row', sets: 3, reps: '8–10', restSec: 120, rpe: 8, weightKg: 22, weightStepKg: 2 },
    { exerciseId: 'ex_db_floor_press', sets: 3, reps: '10–12', restSec: 120, rpe: 7, weightKg: 20, swap: { injuryId: 'inj_shoulder_l', kind: 'swapped' }, weightStepKg: 2 },
    { exerciseId: 'ex_lat_pulldown', sets: 3, reps: '8–10', restSec: 90, rpe: 8, weightKg: 50, weightStepKg: 5 },
    { exerciseId: 'ex_landmine_press', sets: 3, reps: '12 each', restSec: 90, rpe: 7, weightKg: 12.5, swap: { injuryId: 'inj_shoulder_l', kind: 'swapped' }, weightStepKg: 2.5 },
    { exerciseId: 'ex_face_pull', sets: 3, reps: '15', restSec: 60, rpe: 7, weightKg: 15, swap: { injuryId: 'inj_shoulder_l', kind: 'added' }, weightStepKg: 2.5 },
    { exerciseId: 'ex_incline_curl', sets: 3, reps: '10', restSec: 60, rpe: 8, weightKg: 10, weightStepKg: 1 },
    { exerciseId: 'ex_pushdown', sets: 2, reps: '12', restSec: 60, rpe: 8, weightKg: 20, swap: { injuryId: 'inj_shoulder_l', kind: 'swapped' }, weightStepKg: 2.5 },
  ],
};

export const workoutWeek: WorkoutWeek = {
  weekNumber: 3,
  totalWeeks: 8,
  start: '2026-09-26',
  end: '2026-10-02',
  deloadWeek: 5,
  sessions: [lowerA, upperA, lowerB, upperB],
};

// ── Meals & recipes ──────────────────────────────────────────────────
export const meals: Meal[] = [
  { id: 'm_ful_eggs', slot: 'breakfast', time: '08:30', name: L('Ful medames, eggs & baladi bread', 'فول مدمس وبيض وعيش بلدي'), portions: L('1 plate ful · 2 eggs + 2 whites · 1 baladi bread · tomato & cucumber', 'طبق فول · 2 بيض + 2 بياض · رغيف بلدي · طماطم وخيار'), kcal: 515, proteinG: 38, carbsG: 52, fatG: 17, recipeId: 'r_ful_eggs', eaten: true },
  { id: 'm_koshary', slot: 'lunch', time: '14:30', name: L('Koshary, lighter plate', 'كشري، طبق أخف'), portions: L('1 medium plate · extra lentils · less fried onion · 1 cup zabadi', 'طبق وسط · عدس زيادة · بصل مقلي أقل · علبة زبادي'), kcal: 630, proteinG: 30, carbsG: 100, fatG: 12 },
  { id: 'm_zabadi_oats', slot: 'snack', time: '18:30', name: L('Zabadi, banana & oats', 'زبادي وموز وشوفان'), portions: L('1 cup thick zabadi · 1 banana · 3 tbsp oats · 1 tsp honey', 'علبة زبادي · موزة · 3 معالق شوفان · معلقة عسل صغيرة'), kcal: 305, proteinG: 27, carbsG: 38, fatG: 5 },
  { id: 'm_chicken_molokhia', slot: 'dinner', time: '21:00', name: L('Grilled chicken, rice & molokhia', 'فراخ مشوية ورز وملوخية'), portions: L('250 g chicken · ½ cup rice · 1 ladle molokhia · lemon', '250 جم فراخ · نص كوباية رز · مغرفة ملوخية · ليمون'), kcal: 750, proteinG: 80, carbsG: 35, fatG: 33, recipeId: 'r_chicken_molokhia' },
];


/** Swap candidates: within ±10% of the meal's calories and protein. */
export const swapOptions: Record<string, Meal[]> = {
  m_koshary: [
    { id: 'm_hawawshi', slot: 'lunch', time: '14:30', name: L('Hawawshi, baked, lean beef', 'حواوشي في الفرن بلحمة قليلة الدهن'), portions: L('1 loaf · salad', 'رغيف · سلطة'), kcal: 640, proteinG: 34, carbsG: 68, fatG: 22 },
    { id: 'm_lentil_chicken', slot: 'lunch', time: '14:30', name: L('Lentil soup, bread & grilled chicken', 'شوربة عدس وعيش وفراخ مشوية'), portions: L('1 bowl · ½ baladi · 100 g chicken', 'طبق · نص رغيف بلدي · 100 جم فراخ'), kcal: 610, proteinG: 38, carbsG: 70, fatG: 16 },
    { id: 'm_macarona', slot: 'lunch', time: '14:30', name: L('Macarona with tomato & beef', 'مكرونة بالصلصة واللحمة'), portions: L('1 plate · 90 g beef mince', 'طبق · 90 جم لحمة مفرومة'), kcal: 650, proteinG: 32, carbsG: 84, fatG: 18 },
  ],
};

const M = (id: string, slot: Meal['slot'], time: string, name: LocalizedText, portions: LocalizedText, kcal: number, proteinG: number, carbsG: number, fatG: number, recipeId?: string): Meal =>
  ({ id, slot, time, name, portions, kcal, proteinG, carbsG, fatG, ...(recipeId && { recipeId }) });
const plain = (m: Meal): Meal => ({ ...m, eaten: undefined });
const lentilChicken = M('m_lentil_chicken', 'lunch', '14:30', L('Lentil soup, bread & grilled chicken', 'شوربة عدس وعيش وفراخ مشوية'), L('1 bowl lentil soup · ½ baladi bread · 100 g chicken', 'طبق شوربة عدس · نص رغيف بلدي · 100 جم فراخ'), 610, 38, 70, 16);
const fruitNuts = M('m_fruit_nuts', 'snack', '18:30', L('Fruit & a handful of nuts', 'فاكهة وحفنة مكسرات'), L('1 apple or 2 guavas · 20 g peanuts or almonds', 'تفاحة أو 2 جوافة · 20 جم سوداني أو لوز'), 250, 6, 26, 14);

/** The week's meal plan, one MealDay per date. Training days: sat, mon, wed, thu. */
export const mealDays: Record<string, MealDay> = Object.fromEntries(([
  { date: '2026-09-26', day: 'sat', isTrainingDay: true, meals: [plain(meals[0]), lentilChicken, plain(meals[2]),
    M('m_fish_rice', 'dinner', '21:00', L('Grilled fish, rice & salad', 'سمك مشوي ورز وسلطة'), L('300 g bolti or bouri · ¾ cup rice · green salad · tahini drizzle', '300 جم بلطي أو بوري · تلت أرباع كوباية رز · سلطة خضرا · شوية طحينة'), 770, 52, 80, 24)] },
  { date: '2026-09-27', day: 'sun', isTrainingDay: false, meals: [
    M('m_oats_milk', 'breakfast', '08:30', L('Oats with milk & banana', 'شوفان باللبن وموز'), L('½ cup oats · 1 cup milk · 1 banana · 1 tsp honey', 'نص كوباية شوفان · كوباية لبن · موزة · معلقة عسل صغيرة'), 420, 22, 62, 10),
    plain(meals[1]), fruitNuts,
    M('m_kofta_tahini', 'dinner', '21:00', L('Beef kofta, baladi bread & tahini', 'كفتة وعيش بلدي وطحينة'), L('200 g lean kofta · 1 baladi bread · 2 tbsp tahini · salad', '200 جم كفتة قليلة الدهن · رغيف بلدي · 2 معلقة طحينة · سلطة'), 900, 62, 58, 44)] },
  { date: '2026-09-28', day: 'mon', isTrainingDay: true, meals },
  { date: '2026-09-29', day: 'tue', isTrainingDay: false, meals: [
    M('m_cheese_egg_sandwich', 'breakfast', '08:30', L('Cheese & egg sandwich in baladi bread', 'ساندوتش جبنة وبيض في عيش بلدي'), L('1 baladi bread · 2 eggs · 40 g white cheese · tomato', 'رغيف بلدي · 2 بيض · 40 جم جبنة بيضا · طماطم'), 480, 30, 45, 19),
    M('m_shawarma_bowl', 'lunch', '14:30', L('Lentil soup & chicken shawarma bowl', 'شوربة عدس وبول شاورما فراخ'), L('1 cup lentil soup · 150 g chicken shawarma · ½ cup rice · salad & garlic yoghurt', 'كوباية شوربة عدس · 150 جم شاورما فراخ · نص كوباية رز · سلطة وزبادي بالتوم'), 720, 55, 70, 22),
    M('m_fruit_zabadi', 'snack', '18:30', L('Fruit & zabadi', 'فاكهة وزبادي'), L('1 cup zabadi · 1 orange or 2 guavas', 'علبة زبادي · برتقانة أو 2 جوافة'), 250, 14, 38, 4),
    M('m_pasta_tuna', 'dinner', '21:00', L('Pasta with tomato sauce & tuna', 'مكرونة بالصلصة والتونة'), L('1 plate pasta · 1 can tuna in water · tomato sauce', 'طبق مكرونة · علبة تونة مية · صلصة طماطم'), 750, 45, 95, 18)] },
  { date: '2026-09-30', day: 'wed', isTrainingDay: true, meals: [
    M('m_shakshuka', 'breakfast', '08:30', L('Shakshuka & baladi bread', 'شكشوكة وعيش بلدي'), L('3 eggs in tomato & pepper · 1 baladi bread', '3 بيض بالطماطم والفلفل · رغيف بلدي'), 470, 26, 44, 20),
    plain(meals[1]), plain(meals[2]),
    M('m_chicken_potatoes', 'dinner', '21:00', L('Oven chicken & potatoes', 'فراخ وبطاطس في الفرن'), L('250 g chicken · 2 medium potatoes · onion & tomato', '250 جم فراخ · 2 بطاطس وسط · بصل وطماطم'), 795, 70, 70, 24)] },
  { date: '2026-10-01', day: 'thu', isTrainingDay: true, meals: [plain(meals[0]),
    M('m_macarona_beef', 'lunch', '14:30', L('Macarona with beef mince', 'مكرونة باللحمة المفرومة'), L('1 plate pasta · 120 g lean beef mince · tomato sauce', 'طبق مكرونة · 120 جم لحمة مفرومة قليلة الدهن · صلصة طماطم'), 830, 50, 100, 24),
    plain(meals[2]),
    M('m_tuna_salad', 'dinner', '21:00', L('Tuna salad with baladi bread', 'سلطة تونة وعيش بلدي'), L('1 can tuna · 1 baladi bread · cucumber, tomato & lemon · 1 tsp olive oil', 'علبة تونة · رغيف بلدي · خيار وطماطم وليمون · معلقة زيت زيتون صغيرة'), 520, 42, 48, 16)] },
  { date: '2026-10-02', day: 'fri', isTrainingDay: false, meals: [
    M('m_late_breakfast', 'breakfast', '11:00', L('Late breakfast: ful, ta3meya & eggs', 'فطار متأخر: فول وطعمية وبيض'), L('1 plate ful · 2 pieces ta3meya · 2 eggs · ½ baladi bread', 'طبق فول · 2 طعمية · 2 بيض · نص رغيف بلدي'), 620, 30, 62, 26),
    M('m_mahshi_chicken', 'lunch', '16:00', L('Family lunch: mahshi & grilled chicken', 'غدا العيلة: محشي وفراخ مشوية'), L('6 pieces mahshi · ¼ grilled chicken, no skin · salad', '6 صوابع محشي · ربع فرخة مشوية من غير جلد · سلطة'), 1000, 70, 95, 36),
    { ...fruitNuts, time: '19:00' },
    M('m_light_dinner', 'dinner', '22:00', L('Light dinner: zabadi, cheese & cucumber', 'عشا خفيف: زبادي وجبنة وخيار'), L('1 cup zabadi · 60 g cottage or white cheese · cucumber', 'علبة زبادي · 60 جم جبنة قريش أو بيضا · خيار'), 330, 28, 16, 16)] },
] as MealDay[]).map((d) => [d.date, d]));

export const mealDay: MealDay = mealDays[TODAY];

/** One line per day for the week list, built from mealDays: the biggest meal, then the others. */
export const mealWeek: MealWeekDay[] = Object.values(mealDays).map((d) => {
  const main = d.meals.reduce((a, m) => (m.kcal > a.kcal ? m : a));
  const others = d.meals.filter((m) => m !== main);
  return {
    date: d.date, day: d.day, kcal: d.meals.reduce((a, m) => a + m.kcal, 0), main: main.name,
    others: L(others.map((m) => m.name.en).join(' · '), others.map((m) => m.name.ar).join(' · ')),
  };
});

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
const g = (id: string, en: string, ar: string, category: GroceryList['items'][number]['category'], qty: number, unit: GroceryList['items'][number]['unit'], period: 'week' | 'month', extra: Partial<{ checked: boolean; haveIt: boolean }> = {}) =>
  ({ id, name: L(en, ar), category, qty, unit, period, checked: false, haveIt: false, ...extra });

export const groceryList: GroceryList = {
  weekNumber: 3,
  start: '2026-09-26',
  end: '2026-10-02',
  changeNote: L('Updated after your weekly review. Fish fillet added; beef mince down from 1 kg to 0.5 kg.', 'اتحدّثت بعد مراجعتك الأسبوعية. اتضاف فيليه سمك، واللحمة المفرومة نزلت من 1 كجم لنص كيلو.'),
  items: [
    g('gi_tomatoes', 'Tomatoes', 'طماطم', 'produce', 2, 'kg', 'week', { checked: true }),
    g('gi_cucumbers', 'Cucumbers', 'خيار', 'produce', 1, 'kg', 'week'),
    g('gi_onions', 'Onions', 'بصل', 'produce', 1.5, 'kg', 'week'),
    g('gi_potatoes', 'Potatoes', 'بطاطس', 'produce', 2, 'kg', 'week'),
    g('gi_lemons', 'Lemons', 'ليمون', 'produce', 0.5, 'kg', 'week'),
    g('gi_garlic', 'Garlic', 'توم', 'produce', 250, 'g', 'week', { haveIt: true }),
    g('gi_molokhia', 'Molokhia, frozen', 'ملوخية مجمدة', 'produce', 1.4, 'kg', 'week'),
    g('gi_bananas', 'Bananas', 'موز', 'produce', 1.5, 'kg', 'week'),
    g('gi_chicken', 'Chicken breast', 'صدور فراخ', 'meat', 1.5, 'kg', 'week'),
    g('gi_fish', 'Fish fillet', 'فيليه سمك', 'meat', 0.6, 'kg', 'week'),
    g('gi_beef', 'Beef mince', 'لحمة مفرومة', 'meat', 0.5, 'kg', 'week'),
    g('gi_eggs', 'Eggs', 'بيض', 'dairy', 18, 'pcs', 'week', { checked: true }),
    g('gi_milk', 'Milk', 'لبن', 'dairy', 3, 'L', 'week'),
    g('gi_yogurt', 'Plain yogurt', 'زبادي', 'dairy', 7, 'cups', 'week'),
    g('gi_cheese', 'White cheese', 'جبنة بيضا', 'dairy', 250, 'g', 'week'),
    g('gi_bread', 'Baladi bread', 'عيش بلدي', 'bakery', 20, 'loaves', 'week', { checked: true }),
    g('gi_rice', 'Rice', 'رز', 'pantry', 3, 'kg', 'month'),
    g('gi_pasta', 'Pasta', 'مكرونة', 'pantry', 2, 'kg', 'month'),
    g('gi_lentils', 'Brown lentils', 'عدس بجبة', 'pantry', 1, 'kg', 'month'),
    g('gi_fava', 'Fava beans, dried', 'فول ناشف', 'pantry', 2, 'kg', 'month'),
    g('gi_oats', 'Oats', 'شوفان', 'pantry', 1, 'kg', 'month'),
    g('gi_olive_oil', 'Olive oil', 'زيت زيتون', 'pantry', 1, 'L', 'month', { haveIt: true }),
    g('gi_tahini', 'Tahini', 'طحينة', 'pantry', 500, 'g', 'month'),
    g('gi_cumin', 'Cumin', 'كمون', 'spices', 100, 'g', 'month'),
    g('gi_coriander', 'Ground coriander', 'كزبرة ناشفة', 'spices', 100, 'g', 'month'),
    g('gi_pepper', 'Black pepper', 'فلفل أسود', 'spices', 50, 'g', 'month', { haveIt: true }),
    g('gi_paste', 'Tomato paste', 'صلصة طماطم', 'spices', 2, 'jars', 'month'),
    g('gi_vinegar', 'Vinegar', 'خل', 'spices', 1, 'L', 'month'),
    g('gi_salt', 'Salt', 'ملح', 'spices', 1, 'kg', 'month', { haveIt: true }),
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
    groceryUpdate: { note: L('Fish fillet added', 'اتضاف فيليه سمك') },
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
