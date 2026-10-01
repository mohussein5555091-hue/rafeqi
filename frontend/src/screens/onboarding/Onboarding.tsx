import { useState } from 'react';
import { Navigate, useNavigate, useParams } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import {
  Flame, BicepsFlexed, RefreshCw, Dumbbell, Building2, House, PersonStanding, CircleCheck, HeartHandshake, Ruler, X, Sparkles,
  User as UserIcon, Target, Bandage, HeartPulse, Utensils, Lock, MoonStar,
} from 'lucide-react';
import {
  BodyMap, Button, Card, ChipGroup, Field, FlowShell, Icon, NumberStepper, QueryView, ScalePicker, Segmented, cn, useToast, type RegionState,
} from '@/components';
import { useI18n } from '@/i18n';
import { api } from '@/data/api';
import { useQuery } from '@/data/useQuery';
import type { BodyRegion, InjuryInput, QuestionnaireAnswers } from '@/types';
import { ALLERGIES, EXPERIENCE, FOODS, GOALS, HEALTH_KEYS, INJURY_TYPES, LOCATIONS, MOVEMENTS, PACES, REGION_LIST, RESTRICTIONS, sideOf } from '@/constants';

export const ONBOARDING_STEPS = ['about', 'goal', 'training', 'injuries', 'health', 'food', 'review'] as const;
type StepId = (typeof ONBOARDING_STEPS)[number];

type StepProps = { a: QuestionnaireAnswers; set: (patch: Partial<QuestionnaireAnswers>) => void };

/** /onboarding: picks up at the step the person reached last time. */
export function OnboardingStart() {
  const q = useQuery(() => api.getOnboarding());
  return q.data ? <Navigate to={`/onboarding/${q.data.step}`} replace /> : <QueryView query={q}>{() => null}</QueryView>;
}

/** Onboarding questionnaire: 7 steps. Each step is saved when you tap Next, so you can stop and come back. */
export function Onboarding() {
  const q = useQuery(() => api.getOnboarding());
  return q.data ? <OnboardingFlow initial={q.data.answers} /> : <div className="p-5"><QueryView query={q}>{() => null}</QueryView></div>;
}

function OnboardingFlow({ initial }: { initial: QuestionnaireAnswers }) {
  const { step = 'about' } = useParams<{ step: StepId }>();
  const nav = useNavigate();
  const { t } = useI18n();
  const toast = useToast();
  const [a, setA] = useState<QuestionnaireAnswers>(initial);
  const [saving, setSaving] = useState(false);
  const idx = ONBOARDING_STEPS.indexOf(step as StepId);
  if (idx < 0) return <Navigate to="/onboarding/about" replace />;
  const set = (patch: Partial<QuestionnaireAnswers>) => setA((prev) => ({ ...prev, ...patch }));
  const go = (i: number) => nav(`/onboarding/${ONBOARDING_STEPS[i]}`);
  const isLast = idx === ONBOARDING_STEPS.length - 1;
  const Step = { about: AboutStep, goal: GoalStep, training: TrainingStep, injuries: InjuriesStep, health: HealthStep, food: FoodStep, review: ReviewStep }[step as StepId];
  const next = async () => {
    setSaving(true);
    try {
      if (isLast) { await api.completeOnboarding(); nav('/onboarding/generating'); }
      else { await api.saveOnboardingStep(step as Exclude<StepId, 'review'>, a); go(idx + 1); }
    } catch {
      toast({ message: t('onboarding.saveFailed'), tone: 'error' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <FlowShell
      title={t(`onboarding.${step}.title`)} intro={t(`onboarding.${step}.intro`)}
      step={idx + 1} total={ONBOARDING_STEPS.length}
      onBack={idx > 0 ? () => go(idx - 1) : undefined}
      onNext={next}
      nextLabel={isLast ? t('onboarding.review.build') : undefined}
      nextDisabled={saving || (step === 'about' && a.age < 18)}
      footerNote={isLast ? t('onboarding.review.buildNote') : undefined}
    >
      <Step a={a} set={set} />
    </FlowShell>
  );
}

function AboutStep({ a, set }: StepProps) {
  const { t } = useI18n();
  return (
    <>
      <Field label={t('onboarding.about.sex')}>
        <Segmented label={t('onboarding.about.sex')} value={a.sex} onChange={(sex) => set({ sex })} options={[{ id: 'male', label: t('enums.sex.male') }, { id: 'female', label: t('enums.sex.female') }]} />
      </Field>
      <Field label={t('onboarding.about.age')} hint={t('onboarding.about.adultsOnly')} error={a.age < 18 ? t('onboarding.about.under18') : undefined}>
        <NumberStepper label={t('onboarding.about.age')} value={a.age} min={16} max={90} onChange={(age) => set({ age })} unit={t('units.years')} />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label={t('onboarding.about.height')}><NumberStepper label={t('onboarding.about.height')} value={a.heightCm} min={130} max={220} onChange={(heightCm) => set({ heightCm })} unit={t('units.cm')} /></Field>
        <Field label={t('onboarding.about.weight')}><NumberStepper label={t('onboarding.about.weight')} value={a.weightKg} step={0.5} digits={1} min={35} max={250} onChange={(weightKg) => set({ weightKg })} unit={t('units.kg')} /></Field>
      </div>
      <Field label={<>{t('onboarding.about.waist')} <span className="text-neutral-600">· {t('common.optional')}</span></>} hint={<span className="flex gap-1.5"><Icon as={Ruler} size={14} />{t('onboarding.about.waistHint')}</span>}>
        <NumberStepper label={t('onboarding.about.waist')} value={a.waistCm ?? 90} min={50} max={180} onChange={(waistCm) => set({ waistCm })} unit={t('units.cm')} />
      </Field>
    </>
  );
}

function OptionCard({ selected, onClick, icon, title, sub }: { selected: boolean; onClick: () => void; icon: LucideIcon; title: string; sub?: string }) {
  return (
    <button type="button" role="radio" aria-checked={selected} onClick={onClick}
      className={cn('flex min-h-[68px] items-center gap-3.5 rounded-lg border-2 px-4 py-2.5 text-start', selected ? 'border-accent-700 bg-accent-100' : 'border-transparent bg-surface hover:bg-neutral-300')}>
      <span className={cn('grid h-tap w-tap shrink-0 place-items-center rounded-full', selected ? 'bg-accent text-on-accent' : 'bg-bg')}><Icon as={icon} /></span>
      <span className="flex-1"><strong className="block text-base">{title}</strong>{sub && <span className="text-[13px] text-neutral-800">{sub}</span>}</span>
      {selected && <Icon as={CircleCheck} className="text-accent-700" />}
    </button>
  );
}

function GoalStep({ a, set }: StepProps) {
  const { t } = useI18n();
  const icons: Record<string, LucideIcon> = { loseFat: Flame, buildMuscle: BicepsFlexed, recomp: RefreshCw, strength: Dumbbell };
  return (
    <>
      <div role="radiogroup" aria-label={t('onboarding.goal.title')} className="flex flex-col gap-2.5">
        {GOALS.map((g) => <OptionCard key={g} selected={a.goal === g} onClick={() => set({ goal: g })} icon={icons[g]} title={t(`enums.goal.${g}`)} sub={t(`onboarding.goal.sub.${g}`)} />)}
      </div>
      <h2 className="m-0 mt-2 text-base">{t('onboarding.goal.pace')}</h2>
      <div role="radiogroup" aria-label={t('onboarding.goal.pace')} className="grid grid-cols-3 gap-2">
        {PACES.map((p) => (
          <button key={p} type="button" role="radio" aria-checked={a.pace === p} onClick={() => set({ pace: p })}
            className={cn('flex min-h-16 flex-col items-center justify-center rounded-md px-1 text-sm font-semibold', a.pace === p ? 'bg-accent font-bold text-on-accent' : 'bg-surface hover:bg-neutral-300')}>
            {t(`enums.pace.${p}`)}<span className="text-[11.5px] font-normal">{t(`onboarding.goal.paceRate.${p}`)}</span>
          </button>
        ))}
      </div>
      <p className="m-0 text-[12.5px] text-neutral-700">{t('onboarding.goal.paceHint')}</p>
    </>
  );
}

function TrainingStep({ a, set }: StepProps) {
  const { t } = useI18n();
  const locIcons: Record<string, LucideIcon> = { gym: Building2, homeDumbbells: House, bodyweight: PersonStanding };
  return (
    <>
      <Field label={t('onboarding.training.experience')} hint={t(`onboarding.training.expHint.${a.experience}`)}>
        <Segmented label={t('onboarding.training.experience')} value={a.experience} onChange={(experience) => set({ experience })} options={EXPERIENCE.map((e) => ({ id: e, label: t(`enums.experience.${e}`) }))} />
      </Field>
      <Field label={t('onboarding.training.days')}>
        <ScalePicker label={t('onboarding.training.days')} values={[2, 3, 4, 5, 6]} value={a.daysPerWeek} onChange={(v) => set({ daysPerWeek: v as QuestionnaireAnswers['daysPerWeek'] })} />
      </Field>
      <Field label={t('onboarding.training.length')}>
        <Segmented label={t('onboarding.training.length')} value={a.sessionMinutes} onChange={(sessionMinutes) => set({ sessionMinutes })}
          options={([45, 60, 75, 90] as const).map((m) => ({ id: m, label: t('units.minutesShort', { n: m }) }))} />
      </Field>
      <Field label={t('onboarding.training.location')}>
        <div role="radiogroup" aria-label={t('onboarding.training.location')} className="flex flex-col gap-2">
          {LOCATIONS.map((l) => (
            <button key={l} type="button" role="radio" aria-checked={a.location === l} onClick={() => set({ location: l })}
              className={cn('flex min-h-14 items-center gap-3 rounded-pill border-2 px-4 font-semibold', a.location === l ? 'border-accent-700 bg-accent-100 font-bold' : 'border-transparent bg-surface hover:bg-neutral-300')}>
              <Icon as={locIcons[l]} />{t(`enums.location.${l}`)}{a.location === l && <Icon as={CircleCheck} className="ms-auto text-accent-700" />}
            </button>
          ))}
        </div>
      </Field>
    </>
  );
}

/** Also reused by the injury add/edit screen. */
export function InjuryDetailsForm({ value, onChange }: { value: InjuryInput; onChange: (v: InjuryInput) => void }) {
  const { t } = useI18n();
  return (
    <div className="flex flex-col gap-4">
      {sideOf(value.region) !== 'none' && (
        <Field label={t('injury.side')}>
          <Segmented label={t('injury.side')} value={value.side} onChange={(side) => onChange({ ...value, side })}
            options={(['left', 'right', 'both'] as const).map((s) => ({ id: s, label: t(`enums.side.${s}`) }))} />
        </Field>
      )}
      <Field label={t('injury.type')}>
        <ChipGroup label={t('injury.type')} options={INJURY_TYPES.map((x) => ({ id: x, label: t(`enums.injuryType.${x}`) }))} value={[value.type]} onChange={(v) => v.length && onChange({ ...value, type: v[v.length - 1] })} />
      </Field>
      <Field label={t('injury.severity', { n: value.severity })} hint={<span className="flex justify-between"><span>{t('injury.mild')}</span><span>{t('injury.severe')}</span></span>}>
        <ScalePicker label={t('injury.severityLabel')} values={[1, 2, 3, 4, 5]} value={value.severity} onChange={(v) => onChange({ ...value, severity: v as InjuryInput['severity'] })} />
      </Field>
      <Field label={t('injury.movements')}>
        <ChipGroup label={t('injury.movements')} options={MOVEMENTS.map((m) => ({ id: m, label: t(`enums.movement.${m}`) }))} value={value.painfulMovements} onChange={(painfulMovements) => onChange({ ...value, painfulMovements })} />
      </Field>
      <Field label={t('injury.restrictions')}>
        <ChipGroup label={t('injury.restrictions')} options={RESTRICTIONS.map((m) => ({ id: m, label: t(`enums.restriction.${m}`) }))} value={value.restrictions} onChange={(restrictions) => onChange({ ...value, restrictions })} />
      </Field>
    </div>
  );
}

function InjuriesStep({ a, set }: StepProps) {
  const { t } = useI18n();
  const selected = a.injuries.map((i) => i.region);
  const toggle = (region: BodyRegion) => set({
    injuries: selected.includes(region)
      ? a.injuries.filter((i) => i.region !== region)
      : [...a.injuries, { region, side: sideOf(region), type: 'unsure', severity: 2, painfulMovements: [], restrictions: [] }],
  });
  const marks = Object.fromEntries(selected.map((r) => [r, 'select'])) as Partial<Record<BodyRegion, RegionState>>;
  return (
    <>
      <div className="flex justify-around rounded-card bg-surface py-3.5">
        <BodyMap view="front" marks={marks} onToggle={toggle} width={138} />
        <BodyMap view="back" marks={marks} onToggle={toggle} width={138} />
      </div>
      <details className="rounded-lg bg-neutral-100 px-4 py-2">
        <summary className="min-h-tap cursor-pointer content-center text-sm font-semibold">{t('onboarding.injuries.pickFromList')}</summary>
        <div className="flex flex-wrap gap-2 pb-2">
          <ChipGroup label={t('onboarding.injuries.pickFromList')} options={REGION_LIST.map((r) => ({ id: r, label: t(`body.${r}`) }))} value={selected} onChange={(next) => {
            const added = next.find((r) => !selected.includes(r)); const removed = selected.find((r) => !next.includes(r));
            toggle((added ?? removed)!);
          }} />
        </div>
      </details>
      {a.injuries.length === 0 && <Button variant="ghost" className="self-start" onClick={() => set({ injuries: [] })}>{t('onboarding.injuries.none')}</Button>}
      {a.injuries.map((inj, i) => (
        <Card key={inj.region} className="gap-4">
          <div className="flex items-center justify-between"><h3 className="m-0 text-xl">{t(`body.${inj.region}`)}</h3>
            <Button variant="secondary" size="icon" icon={X} aria-label={t('common.remove')} onClick={() => toggle(inj.region)} /></div>
          <InjuryDetailsForm value={inj} onChange={(v) => set({ injuries: a.injuries.map((x, j) => (j === i ? v : x)) })} />
        </Card>
      ))}
    </>
  );
}

function HealthStep({ a, set }: StepProps) {
  const { t } = useI18n();
  const anyYes = HEALTH_KEYS.some((k) => a.health[k]);
  return (
    <>
      {HEALTH_KEYS.map((k) => (
        <div key={k} className="flex items-center gap-3 rounded-lg bg-surface py-2.5 pe-2.5 ps-4">
          <span className="flex-1 text-[14.5px] leading-snug">{t(`onboarding.health.q.${k}`)}</span>
          <Segmented className="min-h-tap shrink-0" label={t(`onboarding.health.q.${k}`)} value={a.health[k] ? 'yes' : 'no'}
            onChange={(v) => set({ health: { ...a.health, [k]: v === 'yes' } })} options={[{ id: 'no', label: t('common.no') }, { id: 'yes', label: t('common.yes') }]} />
        </div>
      ))}
      {anyYes && (
        <div role="status" className="flex items-start gap-3 rounded-lg bg-accent-100 px-4 py-4 text-accent-900">
          <Icon as={HeartHandshake} className="text-accent-700" />
          <div className="text-sm"><strong className="mb-0.5 block text-[15px]">{t('onboarding.health.yesTitle')}</strong>{t('onboarding.health.yesBody')}</div>
        </div>
      )}
      <p className="m-0 flex gap-1.5 text-xs text-neutral-700"><Icon as={Lock} size={14} />{t('onboarding.health.private')}</p>
    </>
  );
}

function FoodStep({ a, set }: StepProps) {
  const { t } = useI18n();
  const f = a.food;
  const setFood = (patch: Partial<QuestionnaireAnswers['food']>) => set({ food: { ...f, ...patch } });
  return (
    <>
      <Field label={t('onboarding.food.meals')}>
        <Segmented label={t('onboarding.food.meals')} value={f.mealsPerDay} onChange={(mealsPerDay) => setFood({ mealsPerDay })} options={([2, 3, 4, 5] as const).map((n) => ({ id: n, label: String(n) }))} />
      </Field>
      <Field label={t('onboarding.food.dislikes')}><ChipGroup label={t('onboarding.food.dislikes')} options={FOODS.map((x) => ({ id: x, label: t(`enums.food.${x}`) }))} value={f.dislikes} onChange={(dislikes) => setFood({ dislikes })} /></Field>
      <Field label={t('onboarding.food.allergies')}>
        <ChipGroup label={t('onboarding.food.allergies')} options={ALLERGIES.map((x) => ({ id: x, label: t(`enums.allergy.${x}`) }))} value={f.allergies}
          onChange={(v) => setFood({ allergies: v.at(-1) === 'none' ? ['none'] : v.filter((x) => x !== 'none') })} />
      </Field>
      <Field label={t('onboarding.food.fasting')}>
        <ChipGroup label={t('onboarding.food.fasting')} options={(['ramadan', 'intermittent'] as const).map((x) => ({ id: x, label: t(`enums.fasting.${x}`) }))} value={f.fasting} onChange={(fasting) => setFood({ fasting })} />
      </Field>
      <Field label={t('onboarding.food.cooking')}>
        <Segmented label={t('onboarding.food.cooking')} value={f.cookingMinutes} onChange={(cookingMinutes) => setFood({ cookingMinutes })} options={([15, 30, 60] as const).map((m) => ({ id: m, label: t(`onboarding.food.cook.${m}`) }))} />
      </Field>
    </>
  );
}

function ReviewStep({ a }: StepProps) {
  const { t, num } = useI18n();
  const nav = useNavigate();
  const anyYes = HEALTH_KEYS.some((k) => a.health[k]);
  const rows: { step: StepId; icon: LucideIcon; value: string }[] = [
    { step: 'about', icon: UserIcon, value: t('onboarding.review.aboutValue', { sex: t(`enums.sex.${a.sex}`), age: a.age, height: a.heightCm, weight: num(a.weightKg, 1), waist: a.waistCm ?? '—' }) },
    { step: 'goal', icon: Target, value: `${t(`enums.goal.${a.goal}`)} · ${t(`enums.pace.${a.pace}`)}` },
    { step: 'training', icon: Dumbbell, value: t('onboarding.review.trainingValue', { exp: t(`enums.experience.${a.experience}`), days: a.daysPerWeek, min: a.sessionMinutes, where: t(`enums.location.${a.location}`) }) },
    { step: 'injuries', icon: Bandage, value: a.injuries.length ? a.injuries.map((i) => `${t(`body.${i.region}`)} · ${t(`enums.injuryType.${i.type}`)} · ${i.severity}/5`).join(' — ') : t('onboarding.review.noInjuries') },
    { step: 'health', icon: HeartPulse, value: t(anyYes ? 'onboarding.review.healthFlag' : 'onboarding.review.healthClear') },
    { step: 'food', icon: Utensils, value: t('onboarding.review.foodValue', { meals: a.food.mealsPerDay }) },
  ];
  return (
    <div className="flex flex-col gap-2.5">
      {rows.map((r) => (
        <div key={r.step} className="flex items-center gap-3 rounded-lg bg-surface py-3 pe-2 ps-4">
          <Icon as={r.icon} className="text-accent-700" />
          <div className="min-w-0 flex-1"><strong className="block text-sm">{t(`onboarding.${r.step}.title`)}</strong><span className="text-[13px] text-neutral-800">{r.value}</span></div>
          <Button variant="ghost" size="sm" onClick={() => nav(`/onboarding/${r.step}`)}>{t('common.edit')}</Button>
        </div>
      ))}
      {a.food.fasting.includes('ramadan') && <p className="m-0 flex gap-1.5 text-xs text-neutral-700"><Icon as={MoonStar} size={14} />{t('onboarding.review.ramadanNote')}</p>}
      <p className="m-0 flex gap-1.5 text-xs text-neutral-700"><Icon as={Sparkles} size={14} />{t('onboarding.review.changeLater')}</p>
    </div>
  );
}
