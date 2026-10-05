import { useEffect, useRef, useState } from 'react';
import { Navigate, useNavigate, useParams } from 'react-router-dom';
import { Camera, Lock, Plus, Bandage } from 'lucide-react';
import { BodyMap, Button, Card, ChipGroup, Field, FlowShell, Icon, NumberStepper, QueryView, ScalePicker, Segmented, Slider, cn, inRange, parseNumber, useToast, type RegionState } from '@/components';
import { useI18n } from '@/i18n';
import { api, type PhotoView } from '@/data/api';
import { useQuery } from '@/data/useQuery';
import { useSession } from '@/data/session';
import { MORE_LESS_FOODS, NOTE_MAX, OBSTACLES } from '@/constants';
import type { BodyRegion, CheckIn as CheckInData, CheckInQuestions, Exercise, Injury, LocalizedText, Scale5 } from '@/types';

export const CHECKIN_STEPS = ['body', 'training', 'injuries', 'nutrition', 'life', 'note'] as const;
type StepId = (typeof CHECKIN_STEPS)[number];
const STORAGE = 'rafeqi.checkin';

type Ctx = {
  c: CheckInData; set: (p: Partial<CheckInData>) => void;
  last: { weightKg: number; measurementsCm: Record<string, number> };
  mealOptions: { id: string; name: LocalizedText }[];
  exercises: Exercise[]; injuries: Injury[];
  /** A question's wording from data/checkin_questions.yaml, and its range. */
  q: (id: string) => string; range: (id: string, fallback: [number, number]) => [number, number];
  /** The photos picked this time (kept in memory until the check-in is sent). */
  photos: Partial<Record<PhotoView, File>>; setPhoto: (view: PhotoView, file: File) => void;
};

/** The question helpers for a loaded questions file. */
function questionText(qs: CheckInQuestions | undefined, l: (x: LocalizedText) => string) {
  const by = new Map((qs?.questions ?? []).map((x) => [x.id, x]));
  return {
    q: (id: string) => { const x = by.get(id); return x ? l(x.text) : id; },
    range: (id: string, fallback: [number, number]): [number, number] => {
      const x = by.get(id);
      return x?.min !== undefined && x?.max !== undefined ? [x.min, x.max] : fallback;
    },
    maxLength: (id: string, fallback: number) => by.get(id)?.maxLength ?? fallback,
  };
}

/** Weekly check-in — the user's only feedback channel (~3 min, no chat). */
export function CheckIn() {
  const { step = 'body' } = useParams<{ step: StepId }>();
  const { t, l } = useI18n();
  const nav = useNavigate();
  const toast = useToast();
  const { refresh } = useSession();
  const [sending, setSending] = useState(false);
  const q = useQuery(() => Promise.all([api.getCheckInDraft(), api.getExercises(), api.getInjuries(), api.getWorkoutWeek(), api.getCheckInQuestions()]));
  // After a reload the picked photo files are gone (only their names were kept): they're asked for again.
  const [c, setC] = useState<CheckInData | null>(() => {
    const raw = sessionStorage.getItem(STORAGE);
    return raw ? { ...JSON.parse(raw), body: { ...JSON.parse(raw).body, photos: {} } } : null;
  });
  const photos = useRef<Partial<Record<PhotoView, File>>>({});
  const qt = questionText(q.data?.[4], l);
  useEffect(() => { if (!c && q.data) setC(q.data[0].draft); }, [q.data, c]);
  useEffect(() => { if (c) sessionStorage.setItem(STORAGE, JSON.stringify(c)); }, [c]);

  const idx = CHECKIN_STEPS.indexOf(step as StepId);
  if (idx < 0) return <Navigate to="/check-in/body" replace />;
  const go = (i: number) => nav(`/check-in/${CHECKIN_STEPS[i]}`);
  const isLast = idx === CHECKIN_STEPS.length - 1;

  const submit = async () => {
    if (!c) return;
    setSending(true);
    const sent = await api.submitCheckIn(c, photos.current).catch(() => null);
    setSending(false);
    if (!sent) { toast({ message: t('common.saveFailed'), tone: 'error' }); return; }
    const { reviewId } = sent;
    sessionStorage.removeItem(STORAGE);
    refresh().catch(() => undefined); // the check-in is no longer due
    nav(`/reviews/${reviewId}?writing=1`, { replace: true });
  };

  return (
    <FlowShell title={t(`checkIn.${step}.title`)} step={idx + 1} total={CHECKIN_STEPS.length}
      onBack={idx > 0 ? () => go(idx - 1) : undefined} backLabel={idx === 0 ? undefined : t('common.back')}
      onNext={isLast ? submit : () => go(idx + 1)} nextLabel={isLast ? t('checkIn.submit') : undefined} nextDisabled={!c || sending || (step === 'body' && !bodyStepValid(c, qt.range))}
      footerNote={isLast ? t('checkIn.reviewTime') : undefined}>
      <QueryView query={q}>
        {([draft, catalogue, injuries, week]) => {
          if (!c) return null;
          // Only exercises in this week's program can be marked (the weekly review changes the program).
          const inProgram = new Set(week.sessions.flatMap((s) => s.exercises.map((e) => e.exerciseId)));
          const exercises = catalogue.filter((e) => inProgram.has(e.id));
          const ctx: Ctx = { c, set: (p) => setC({ ...c, ...p }), last: draft.last, mealOptions: draft.mealOptions, exercises, injuries: injuries.filter((i) => i.status !== 'resolved'),
            q: qt.q, range: qt.range, photos: photos.current,
            setPhoto: (view, file) => { photos.current = { ...photos.current, [view]: file }; setC({ ...c, body: { ...c.body, photos: { ...c.body.photos, [view]: file.name } } }); } };
          const Step = { body: BodyStep, training: TrainingStep, injuries: InjuriesStep, nutrition: NutritionStep, life: LifeStep, note: NoteStep }[step as StepId];
          return <Step {...ctx} />;
        }}
      </QueryView>
    </FlowShell>
  );
}

/** Ranges come from data/checkin_questions.yaml (these are only used until it has loaded; the backend checks again). */
const WEIGHT: [number, number] = [30, 300];
const MEASURE_RANGES: Record<MeasureKey, [number, number]> = { waist: [40, 200], hips: [40, 200], chest: [40, 200], arm: [15, 70], thigh: [25, 100] };
type MeasureKey = 'waist' | 'hips' | 'chest' | 'arm' | 'thigh';
const MEASURES: MeasureKey[] = ['waist', 'hips', 'chest', 'arm', 'thigh'];
type Range = Ctx['range'];

/** Step 1 is ready when the weight is typed and every measurement given is in range. */
export const bodyStepValid = (c: CheckInData, range: Range = (_, f) => f) => inRange(c.body.weightKg, ...range('weight_kg', WEIGHT))
  && MEASURES.every((k) => c.body.measurementsCm[k] === undefined || inRange(c.body.measurementsCm[k], ...range(`${k}_cm`, MEASURE_RANGES[k])));

/** One measurement tile: type the number (number keyboard with a decimal point); "," and Arabic digits work too. */
function MeasureInput({ label, lo, hi, value, was, onChange }: { label: string; lo: number; hi: number; value?: number; was?: number; onChange: (v: number | undefined) => void }) {
  const { t, num } = useI18n();
  const [text, setText] = useState(value === undefined ? '' : String(value));
  const [left, setLeft] = useState(false);
  const v = parseNumber(text);
  const error = !left || text.trim() === '' ? undefined : Number.isNaN(v) ? t('common.notANumber', { label })
    : !inRange(v, lo, hi) ? t('common.range', { label, min: lo, max: hi, unit: t('units.cm') }) : undefined;
  return (
    <label className={cn('flex min-h-[60px] flex-col rounded-lg bg-surface px-3.5 py-2', error && 'ring-2 ring-inset ring-warn-600')}>
      <span className="text-[11.5px] text-neutral-700">{label}</span>
      <input type="text" inputMode="decimal" enterKeyHint="next" dir="ltr" aria-invalid={!!error} className="w-full bg-transparent text-[17px] font-bold"
        placeholder={was !== undefined ? t('common.eg', { n: num(was, 1) }) : undefined} value={text}
        onBlur={() => setLeft(true)}
        onChange={(e) => { setText(e.target.value); const n = parseNumber(e.target.value); onChange(Number.isNaN(n) ? undefined : n); }} />
      <span className="text-[10.5px] text-neutral-700">{t('checkIn.body.was', { v: was === undefined ? '—' : num(was, 1) })}</span>
      {error && <span role="alert" className="text-[11.5px] text-warn-700">{error}</span>}
    </label>
  );
}

function BodyStep({ c, set, last, q, range, setPhoto }: Ctx) {
  const { t } = useI18n();
  const m = c.body.measurementsCm;
  const [wLo, wHi] = range('weight_kg', WEIGHT);
  return (
    <>
      <Field label={q('weight_kg')} hint={t('checkIn.body.lastWeek', { kg: last.weightKg })}>
        <NumberStepper label={q('weight_kg')} value={c.body.weightKg} step={0.1} digits={1} min={wLo} max={wHi} placeholder={last.weightKg}
          onChange={(weightKg) => set({ body: { ...c.body, weightKg } })} unit={t('units.kg')} />
      </Field>
      <Field label={t('checkIn.body.measurements')}>
        <div className="grid grid-cols-3 gap-2">
          {MEASURES.map((k) => (
            <MeasureInput key={k} label={q(`${k}_cm`).replace(/\s*\((cm|سم)\)$/, '')} lo={range(`${k}_cm`, MEASURE_RANGES[k])[0]} hi={range(`${k}_cm`, MEASURE_RANGES[k])[1]} value={m[k]} was={last.measurementsCm[k]} onChange={(v) => set({ body: { ...c.body, measurementsCm: { ...m, [k]: v } } })} />
          ))}
        </div>
      </Field>
      <Field label={t('checkIn.body.photos')} hint={<span className="flex gap-1.5"><Icon as={Lock} size={14} />{t('checkIn.body.photosPrivate')}</span>}>
        <div className="grid grid-cols-3 gap-2">
          {(['front', 'side', 'back'] as const).map((v) => (
            <label key={v} className="flex h-[104px] cursor-pointer flex-col items-center justify-center gap-1.5 rounded-lg border-2 border-dashed border-neutral-400 bg-neutral-100 text-[13px] font-semibold hover:bg-neutral-200">
              <Icon as={Camera} />{c.body.photos[v] ? t('checkIn.body.added') : t(`checkIn.body.view.${v}`)}
              <input type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" aria-label={t(`checkIn.body.view.${v}`)} data-testid={`photo-${v}`} onChange={(e) => e.target.files?.[0] && setPhoto(v, e.target.files[0])} />
            </label>
          ))}
        </div>
      </Field>
    </>
  );
}

function TrainingStep({ c, set, exercises, q }: Ctx) {
  const { t, l } = useI18n();
  const tr = c.training;
  const setTr = (p: Partial<CheckInData['training']>) => set({ training: { ...tr, ...p } });
  const [adding, setAdding] = useState(false);
  return (
    <>
      <Field label={t('checkIn.training.sessions', { q: q('sessions_done'), n: tr.sessionsPlanned })}>
        <ScalePicker label={t('checkIn.training.sessions', { q: q('sessions_done'), n: tr.sessionsPlanned })} values={Array.from({ length: tr.sessionsPlanned + 1 }, (_, i) => i)} value={tr.sessionsDone} onChange={(sessionsDone) => setTr({ sessionsDone })} />
      </Field>
      <Field label={t('checkIn.training.difficulty', { q: q('difficulty'), label: t(`scales.difficulty.${tr.difficulty}`) })}>
        <ScalePicker label={q('difficulty')} values={[1, 2, 3, 4, 5]} value={tr.difficulty} onChange={(v) => setTr({ difficulty: v as Scale5 })} />
      </Field>
      <Field label={t('checkIn.training.soreness', { q: q('soreness'), label: t(`scales.soreness.${tr.soreness}`) })}>
        <ScalePicker label={q('soreness')} values={[1, 2, 3, 4, 5]} value={tr.soreness} onChange={(v) => setTr({ soreness: v as Scale5 })} />
      </Field>
      <Field label={q('exercise_feedback')}>
        <div className="flex flex-col gap-2">
          {tr.exerciseFeedback.map((f, i) => (
            <Card key={f.exerciseId} className="gap-1.5 px-3 py-2.5">
              <strong className="px-1 text-sm">{l(exercises.find((e) => e.id === f.exerciseId)?.name)}</strong>
              <Segmented className="min-h-tap" label={l(exercises.find((e) => e.id === f.exerciseId)?.name)} value={f.feel}
                onChange={(feel) => setTr({ exerciseFeedback: tr.exerciseFeedback.map((x, j) => (j === i ? { ...x, feel } : x)) })}
                options={(['tooEasy', 'tooHard', 'uncomfortable'] as const).map((k) => ({ id: k, label: t(`enums.feel.${k}`) }))} />
            </Card>
          ))}
          {adding ? (
            <select className="h-12 rounded-pill border border-divider bg-surface px-4" defaultValue="" onChange={(e) => { setTr({ exerciseFeedback: [...tr.exerciseFeedback, { exerciseId: e.target.value, feel: 'tooHard' }] }); setAdding(false); }}>
              <option value="" disabled>{t('checkIn.training.pick')}</option>
              {exercises.filter((e) => !tr.exerciseFeedback.some((f) => f.exerciseId === e.id)).map((e) => <option key={e.id} value={e.id}>{l(e.name)}</option>)}
            </select>
          ) : <Button variant="ghost" icon={Plus} className="self-start" onClick={() => setAdding(true)}>{t('checkIn.training.pickAnother')}</Button>}
        </div>
      </Field>
    </>
  );
}

function InjuriesStep({ c, set, injuries, q }: Ctx) {
  const { t } = useI18n();
  const marks = Object.fromEntries(c.newPainRegions.map((r) => [r, 'attn'])) as Partial<Record<BodyRegion, RegionState>>;
  const toggle = (r: BodyRegion) => set({ newPainRegions: c.newPainRegions.includes(r) ? c.newPainRegions.filter((x) => x !== r) : [...c.newPainRegions, r] });
  return (
    <>
      {injuries.map((inj) => {
        const entry = c.injuries.find((x) => x.injuryId === inj.id) ?? { injuryId: inj.id, pain: 0, trend: 'same' as const };
        const upd = (p: Partial<typeof entry>) => set({ injuries: [...c.injuries.filter((x) => x.injuryId !== inj.id), { ...entry, ...p }] });
        return (
          <Card key={inj.id}>
            <strong className="flex items-center gap-2"><Icon as={Bandage} size={18} className="text-accent-600" />{t('checkIn.injuries.painQ', { area: t(`body.${inj.region}`), q: q('injury_pain') })}</strong>
            <ScalePicker label={t('logger.painLabel')} values={[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]} value={entry.pain} dangerFrom={6} onChange={(pain) => upd({ pain })} />
            <Segmented label={t('checkIn.injuries.trend')} value={entry.trend} onChange={(trend) => upd({ trend })} options={(['better', 'same', 'worse'] as const).map((k) => ({ id: k, label: t(`enums.trend.${k}`) }))} />
          </Card>
        );
      })}
      <Card className="flex-row items-center gap-2.5">
        <BodyMap view="front" marks={marks} onToggle={toggle} width={64} showLabels={false} />
        <BodyMap view="back" marks={marks} onToggle={toggle} width={64} showLabels={false} />
        <div className="flex-1 text-[13.5px]"><strong className="block text-[14.5px]">{q('new_pain_regions')}</strong>{t('checkIn.injuries.newPainHint')}</div>
      </Card>
      <div className="flex flex-col gap-1.5">
        <span className="text-[13px] text-neutral-700">{t('checkIn.injuries.safety')}</span>
        {(['sharpPain', 'swelling', 'numbness'] as const).map((k) => (
          <div key={k} className="flex items-center gap-2.5 rounded-pill bg-surface py-1.5 pe-1.5 ps-4">
            <span className="flex-1 text-sm">{q(FLAG_IDS[k])}</span>
            <Segmented className="min-h-tap shrink-0" label={q(FLAG_IDS[k])} value={c.redFlags[k] ? 'yes' : 'no'} onChange={(v) => set({ redFlags: { ...c.redFlags, [k]: v === 'yes' } })}
              options={[{ id: 'no', label: t('common.no') }, { id: 'yes', label: t('common.yes') }]} />
          </div>
        ))}
        <span className={cn('text-xs', Object.values(c.redFlags).some(Boolean) ? 'font-bold text-warn-700' : 'text-neutral-700')}>{t('checkIn.injuries.flagNote')}</span>
      </div>
    </>
  );
}

const FLAG_IDS = { sharpPain: 'sharp_pain', swelling: 'swelling', numbness: 'numbness' } as const;

function NutritionStep({ c, set, mealOptions, q }: Ctx) {
  const { t, l } = useI18n();
  const n = c.nutrition;
  const setN = (p: Partial<CheckInData['nutrition']>) => set({ nutrition: { ...n, ...p } });
  const foods = MORE_LESS_FOODS.map((f) => ({ id: f as string, label: t(`enums.food.${f}`) }));
  return (
    <>
      <Field label={<span className="flex justify-between"><span>{q('adherence_pct')}</span><strong className="text-[15px] text-ink">{n.adherencePct}%</strong></span>}>
        <Slider label={q('adherence_pct')} min={0} max={100} step={5} value={n.adherencePct} onChange={(adherencePct) => setN({ adherencePct })} />
      </Field>
      <Field label={t('checkIn.nutrition.hunger', { q: q('hunger'), label: t(`scales.hunger.${n.hunger}`) })}>
        <ScalePicker label={q('hunger')} values={[1, 2, 3, 4, 5]} value={n.hunger} onChange={(v) => setN({ hunger: v as Scale5 })} />
      </Field>
      <Field label={q('meals_to_change')}><ChipGroup label={q('meals_to_change')} options={mealOptions.map((m) => ({ id: m.id, label: l(m.name) }))} value={n.mealsToChange} onChange={(mealsToChange) => setN({ mealsToChange })} /></Field>
      <Field label={q('more_of')}><ChipGroup label={q('more_of')} options={foods} value={n.moreOf} onChange={(moreOf) => setN({ moreOf, lessOf: n.lessOf.filter((x) => !moreOf.includes(x)) })} /></Field>
      <Field label={q('less_of')}><ChipGroup label={q('less_of')} options={foods} value={n.lessOf} onChange={(lessOf) => setN({ lessOf, moreOf: n.moreOf.filter((x) => !lessOf.includes(x)) })} /></Field>
    </>
  );
}

function LifeStep({ c, set, q }: Ctx) {
  const { t } = useI18n();
  const life = c.life;
  const setL = (p: Partial<CheckInData['life']>) => set({ life: { ...life, ...p } });
  return (
    <>
      {(['sleep', 'energy', 'stress'] as const).map((k) => (
        <Field key={k} label={t('checkIn.life.scale', { q: q(k), n: life[k] })}>
          <ScalePicker label={t('checkIn.life.scale', { q: q(k), n: life[k] })} values={[1, 2, 3, 4, 5]} value={life[k]} onChange={(v) => setL({ [k]: v as Scale5 })} />
        </Field>
      ))}
      <Field label={q('days_available')}><ScalePicker label={q('days_available')} values={[2, 3, 4, 5, 6]} value={life.daysAvailable} onChange={(daysAvailable) => setL({ daysAvailable })} /></Field>
      <Field label={q('obstacles')}><ChipGroup label={q('obstacles')} options={OBSTACLES.map((o) => ({ id: o, label: t(`enums.obstacle.${o}`) }))} value={life.obstacles} onChange={(obstacles) => setL({ obstacles })} /></Field>
    </>
  );
}

function NoteStep({ c, set, q }: Ctx) {
  const { t, num } = useI18n();
  const len = c.note?.length ?? 0;
  return (
    <>
      <Field htmlFor="ci-note" label={<span className="text-sm font-semibold text-ink">{q('note')} <span className="font-normal text-neutral-700">· {t('common.optional')}</span></span>}
        hint={<span className="flex justify-between"><span>{t('checkIn.note.hint')}</span><span className={cn('font-bold', len > NOTE_MAX - 30 && 'text-accent-700')} aria-live="polite">{t('checkIn.note.count', { n: len, max: NOTE_MAX })}</span></span>}>
        <textarea id="ci-note" maxLength={NOTE_MAX} value={c.note ?? ''} onChange={(e) => set({ note: e.target.value.slice(0, NOTE_MAX) })}
          className="min-h-[168px] resize-none rounded-lg border border-divider bg-surface px-4 py-4 text-[15.5px] focus-visible:border-accent-700" />
      </Field>
      <Card className="gap-1.5 text-[13.5px]">
        <strong className="text-[14.5px]">{t('checkIn.note.summary')}</strong>
        <span>{t('checkIn.note.summary1', { kg: c.body.weightKg === undefined ? '—' : num(c.body.weightKg, 1), done: c.training.sessionsDone, total: c.training.sessionsPlanned, pain: c.injuries[0]?.pain ?? 0, trend: t(`enums.trend.${c.injuries[0]?.trend ?? 'same'}`) })}</span>
        <span>{t('checkIn.note.summary2', { pct: c.nutrition.adherencePct, hunger: c.nutrition.hunger, sleep: c.life.sleep })}</span>
      </Card>
    </>
  );
}
