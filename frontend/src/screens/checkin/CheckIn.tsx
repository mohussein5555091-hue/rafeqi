import { useEffect, useState } from 'react';
import { Navigate, useNavigate, useParams } from 'react-router-dom';
import { Camera, Lock, Plus, Bandage } from 'lucide-react';
import { BodyMap, Button, Card, ChipGroup, Field, FlowShell, Icon, NumberStepper, QueryView, ScalePicker, Segmented, Slider, cn, type RegionState } from '@/components';
import { useI18n } from '@/i18n';
import { api } from '@/data/api';
import { useQuery } from '@/data/useQuery';
import { MORE_LESS_FOODS, NOTE_MAX, OBSTACLES } from '@/constants';
import type { BodyRegion, CheckIn as CheckInData, Exercise, Injury, LocalizedText, Scale5 } from '@/types';

export const CHECKIN_STEPS = ['body', 'training', 'injuries', 'nutrition', 'life', 'note'] as const;
type StepId = (typeof CHECKIN_STEPS)[number];
const STORAGE = 'rafeqi.checkin';

type Ctx = {
  c: CheckInData; set: (p: Partial<CheckInData>) => void;
  last: { weightKg: number; measurementsCm: Record<string, number> };
  mealOptions: { id: string; name: LocalizedText }[];
  exercises: Exercise[]; injuries: Injury[];
};

/** Weekly check-in — the user's only feedback channel (~3 min, no chat). */
export function CheckIn() {
  const { step = 'body' } = useParams<{ step: StepId }>();
  const { t } = useI18n();
  const nav = useNavigate();
  const q = useQuery(() => Promise.all([api.getCheckInDraft(), api.getExercises(), api.getInjuries()]));
  const [c, setC] = useState<CheckInData | null>(() => { const raw = sessionStorage.getItem(STORAGE); return raw ? JSON.parse(raw) : null; });
  useEffect(() => { if (!c && q.data) setC(q.data[0].draft); }, [q.data, c]);
  useEffect(() => { if (c) sessionStorage.setItem(STORAGE, JSON.stringify(c)); }, [c]);

  const idx = CHECKIN_STEPS.indexOf(step as StepId);
  if (idx < 0) return <Navigate to="/check-in/body" replace />;
  const go = (i: number) => nav(`/check-in/${CHECKIN_STEPS[i]}`);
  const isLast = idx === CHECKIN_STEPS.length - 1;

  const submit = async () => {
    if (!c) return;
    const { reviewId } = await api.submitCheckIn(c);
    sessionStorage.removeItem(STORAGE);
    nav(`/reviews/${reviewId}?writing=1`, { replace: true });
  };

  return (
    <FlowShell title={t(`checkIn.${step}.title`)} step={idx + 1} total={CHECKIN_STEPS.length}
      onBack={idx > 0 ? () => go(idx - 1) : undefined} backLabel={idx === 0 ? undefined : t('common.back')}
      onNext={isLast ? submit : () => go(idx + 1)} nextLabel={isLast ? t('checkIn.submit') : undefined} nextDisabled={!c}
      footerNote={isLast ? t('checkIn.reviewTime') : undefined}>
      <QueryView query={q}>
        {([draft, exercises, injuries]) => {
          if (!c) return null;
          const ctx: Ctx = { c, set: (p) => setC({ ...c, ...p }), last: draft.last, mealOptions: draft.mealOptions, exercises, injuries: injuries.filter((i) => i.status !== 'resolved') };
          const Step = { body: BodyStep, training: TrainingStep, injuries: InjuriesStep, nutrition: NutritionStep, life: LifeStep, note: NoteStep }[step as StepId];
          return <Step {...ctx} />;
        }}
      </QueryView>
    </FlowShell>
  );
}

function BodyStep({ c, set, last }: Ctx) {
  const { t, num } = useI18n();
  const m = c.body.measurementsCm;
  return (
    <>
      <Field label={t('checkIn.body.weight')} hint={t('checkIn.body.lastWeek', { kg: num(last.weightKg, 1) })}>
        <NumberStepper label={t('checkIn.body.weight')} value={c.body.weightKg} step={0.1} digits={1} onChange={(weightKg) => set({ body: { ...c.body, weightKg } })} unit={t('units.kg')} />
      </Field>
      <Field label={t('checkIn.body.measurements')}>
        <div className="grid grid-cols-3 gap-2">
          {(['waist', 'hips', 'chest', 'arm', 'thigh'] as const).map((k) => (
            <label key={k} className="flex min-h-[60px] flex-col rounded-lg bg-surface px-3.5 py-2">
              <span className="text-[11.5px] text-neutral-700">{t(`checkIn.body.m.${k}`)}</span>
              <input type="number" inputMode="decimal" step="0.5" className="w-full bg-transparent text-[17px] font-bold" value={m[k] ?? ''}
                onChange={(e) => set({ body: { ...c.body, measurementsCm: { ...m, [k]: e.target.value ? Number(e.target.value) : undefined } } })} />
              <span className="text-[10.5px] text-neutral-700">{t('checkIn.body.was', { v: num(last.measurementsCm[k] ?? 0, 1) })}</span>
            </label>
          ))}
        </div>
      </Field>
      <Field label={t('checkIn.body.photos')} hint={<span className="flex gap-1.5"><Icon as={Lock} size={14} />{t('checkIn.body.photosPrivate')}</span>}>
        <div className="grid grid-cols-3 gap-2">
          {(['front', 'side', 'back'] as const).map((v) => (
            <label key={v} className="flex h-[104px] cursor-pointer flex-col items-center justify-center gap-1.5 rounded-lg border-2 border-dashed border-neutral-400 bg-neutral-100 text-[13px] font-semibold hover:bg-neutral-200">
              <Icon as={Camera} />{c.body.photos[v] ? t('checkIn.body.added') : t(`checkIn.body.view.${v}`)}
              <input type="file" accept="image/*" className="sr-only" onChange={(e) => e.target.files?.[0] && set({ body: { ...c.body, photos: { ...c.body.photos, [v]: e.target.files[0].name } } })} />
            </label>
          ))}
        </div>
      </Field>
    </>
  );
}

function TrainingStep({ c, set, exercises }: Ctx) {
  const { t, l } = useI18n();
  const tr = c.training;
  const setTr = (p: Partial<CheckInData['training']>) => set({ training: { ...tr, ...p } });
  const [adding, setAdding] = useState(false);
  return (
    <>
      <Field label={t('checkIn.training.sessions', { n: tr.sessionsPlanned })}>
        <ScalePicker label={t('checkIn.training.sessions', { n: tr.sessionsPlanned })} values={Array.from({ length: tr.sessionsPlanned + 1 }, (_, i) => i)} value={tr.sessionsDone} onChange={(sessionsDone) => setTr({ sessionsDone })} />
      </Field>
      <Field label={t('checkIn.training.difficulty', { label: t(`scales.difficulty.${tr.difficulty}`) })}>
        <ScalePicker label={t('checkIn.training.difficultyLabel')} values={[1, 2, 3, 4, 5]} value={tr.difficulty} onChange={(v) => setTr({ difficulty: v as Scale5 })} />
      </Field>
      <Field label={t('checkIn.training.soreness', { label: t(`scales.soreness.${tr.soreness}`) })}>
        <ScalePicker label={t('checkIn.training.sorenessLabel')} values={[1, 2, 3, 4, 5]} value={tr.soreness} onChange={(v) => setTr({ soreness: v as Scale5 })} />
      </Field>
      <Field label={t('checkIn.training.feltOff')}>
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

function InjuriesStep({ c, set, injuries }: Ctx) {
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
            <strong className="flex items-center gap-2"><Icon as={Bandage} size={18} className="text-accent-600" />{t('checkIn.injuries.painQ', { area: t(`body.${inj.region}`) })}</strong>
            <ScalePicker label={t('logger.painLabel')} values={[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]} value={entry.pain} dangerFrom={6} onChange={(pain) => upd({ pain })} />
            <Segmented label={t('checkIn.injuries.trend')} value={entry.trend} onChange={(trend) => upd({ trend })} options={(['better', 'same', 'worse'] as const).map((k) => ({ id: k, label: t(`enums.trend.${k}`) }))} />
          </Card>
        );
      })}
      <Card className="flex-row items-center gap-2.5">
        <BodyMap view="front" marks={marks} onToggle={toggle} width={64} showLabels={false} />
        <BodyMap view="back" marks={marks} onToggle={toggle} width={64} showLabels={false} />
        <div className="flex-1 text-[13.5px]"><strong className="block text-[14.5px]">{t('checkIn.injuries.newPain')}</strong>{t('checkIn.injuries.newPainHint')}</div>
      </Card>
      <div className="flex flex-col gap-1.5">
        <span className="text-[13px] text-neutral-700">{t('checkIn.injuries.safety')}</span>
        {(['sharpPain', 'swelling', 'numbness'] as const).map((k) => (
          <div key={k} className="flex items-center gap-2.5 rounded-pill bg-surface py-1.5 pe-1.5 ps-4">
            <span className="flex-1 text-sm">{t(`checkIn.injuries.flag.${k}`)}</span>
            <Segmented className="min-h-tap shrink-0" label={t(`checkIn.injuries.flag.${k}`)} value={c.redFlags[k] ? 'yes' : 'no'} onChange={(v) => set({ redFlags: { ...c.redFlags, [k]: v === 'yes' } })}
              options={[{ id: 'no', label: t('common.no') }, { id: 'yes', label: t('common.yes') }]} />
          </div>
        ))}
        <span className={cn('text-xs', Object.values(c.redFlags).some(Boolean) ? 'font-bold text-warn-700' : 'text-neutral-700')}>{t('checkIn.injuries.flagNote')}</span>
      </div>
    </>
  );
}

function NutritionStep({ c, set, mealOptions }: Ctx) {
  const { t, l } = useI18n();
  const n = c.nutrition;
  const setN = (p: Partial<CheckInData['nutrition']>) => set({ nutrition: { ...n, ...p } });
  const foods = MORE_LESS_FOODS.map((f) => ({ id: f as string, label: t(`enums.food.${f}`) }));
  return (
    <>
      <Field label={<span className="flex justify-between"><span>{t('checkIn.nutrition.adherence')}</span><strong className="text-[15px] text-ink">{n.adherencePct}%</strong></span>}>
        <Slider label={t('checkIn.nutrition.adherence')} min={0} max={100} step={5} value={n.adherencePct} onChange={(adherencePct) => setN({ adherencePct })} />
      </Field>
      <Field label={t('checkIn.nutrition.hunger', { label: t(`scales.hunger.${n.hunger}`) })}>
        <ScalePicker label={t('checkIn.nutrition.hungerLabel')} values={[1, 2, 3, 4, 5]} value={n.hunger} onChange={(v) => setN({ hunger: v as Scale5 })} />
      </Field>
      <Field label={t('checkIn.nutrition.change')}><ChipGroup label={t('checkIn.nutrition.change')} options={mealOptions.map((m) => ({ id: m.id, label: l(m.name) }))} value={n.mealsToChange} onChange={(mealsToChange) => setN({ mealsToChange })} /></Field>
      <Field label={t('checkIn.nutrition.more')}><ChipGroup label={t('checkIn.nutrition.more')} options={foods} value={n.moreOf} onChange={(moreOf) => setN({ moreOf, lessOf: n.lessOf.filter((x) => !moreOf.includes(x)) })} /></Field>
      <Field label={t('checkIn.nutrition.less')}><ChipGroup label={t('checkIn.nutrition.less')} options={foods} value={n.lessOf} onChange={(lessOf) => setN({ lessOf, moreOf: n.moreOf.filter((x) => !lessOf.includes(x)) })} /></Field>
    </>
  );
}

function LifeStep({ c, set }: Ctx) {
  const { t } = useI18n();
  const life = c.life;
  const setL = (p: Partial<CheckInData['life']>) => set({ life: { ...life, ...p } });
  return (
    <>
      {(['sleep', 'energy', 'stress'] as const).map((k) => (
        <Field key={k} label={t(`checkIn.life.${k}`, { n: life[k] })}>
          <ScalePicker label={t(`checkIn.life.${k}`, { n: life[k] })} values={[1, 2, 3, 4, 5]} value={life[k]} onChange={(v) => setL({ [k]: v as Scale5 })} />
        </Field>
      ))}
      <Field label={t('checkIn.life.days')}><ScalePicker label={t('checkIn.life.days')} values={[2, 3, 4, 5, 6]} value={life.daysAvailable} onChange={(daysAvailable) => setL({ daysAvailable })} /></Field>
      <Field label={t('checkIn.life.obstacles')}><ChipGroup label={t('checkIn.life.obstacles')} options={OBSTACLES.map((o) => ({ id: o, label: t(`enums.obstacle.${o}`) }))} value={life.obstacles} onChange={(obstacles) => setL({ obstacles })} /></Field>
    </>
  );
}

function NoteStep({ c, set }: Ctx) {
  const { t, num } = useI18n();
  const len = c.note?.length ?? 0;
  return (
    <>
      <Field htmlFor="ci-note" label={<span className="text-sm font-semibold text-ink">{t('checkIn.note.label')} <span className="font-normal text-neutral-700">· {t('common.optional')}</span></span>}
        hint={<span className="flex justify-between"><span>{t('checkIn.note.hint')}</span><span className={cn('font-bold', len > NOTE_MAX - 30 && 'text-accent-700')} aria-live="polite">{t('checkIn.note.count', { n: len, max: NOTE_MAX })}</span></span>}>
        <textarea id="ci-note" maxLength={NOTE_MAX} value={c.note ?? ''} onChange={(e) => set({ note: e.target.value.slice(0, NOTE_MAX) })}
          className="min-h-[168px] resize-none rounded-lg border border-divider bg-surface px-4 py-4 text-[15.5px] focus-visible:border-accent-700" />
      </Field>
      <Card className="gap-1.5 text-[13.5px]">
        <strong className="text-[14.5px]">{t('checkIn.note.summary')}</strong>
        <span>{t('checkIn.note.summary1', { kg: num(c.body.weightKg, 1), done: c.training.sessionsDone, total: c.training.sessionsPlanned, pain: c.injuries[0]?.pain ?? 0, trend: t(`enums.trend.${c.injuries[0]?.trend ?? 'same'}`) })}</span>
        <span>{t('checkIn.note.summary2', { pct: c.nutrition.adherencePct, hunger: c.nutrition.hunger, sleep: c.life.sleep })}</span>
      </Card>
    </>
  );
}
