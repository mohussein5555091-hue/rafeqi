import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Hourglass, Lock, CircleCheck, Dumbbell, Salad, Shield, ArrowRight } from 'lucide-react';
import { Breathing, Button, Card, Disclaimer, Icon, Kicker, LinkButton, PageControls, QueryView, StepList } from '@/components';
import { useI18n } from '@/i18n';
import { api } from '@/data/api';
import { useQuery } from '@/data/useQuery';
import { useSession } from '@/data/session';
import type { PlanGenerationStep } from '@/types';
import { WhyPlanLink } from '@/screens/plan/WhyPlan';

const STEPS: PlanGenerationStep[] = ['calories', 'program', 'injuries', 'meals'];

/** Calm wait screen while the local model builds the plan (30–90 s). */
export function PlanGenerating() {
  const { t, l } = useI18n();
  const { user, refresh } = useSession();
  const nav = useNavigate();
  const [done, setDone] = useState<PlanGenerationStep[]>([]);
  const [failed, setFailed] = useState(false);
  const started = useRef(false);

  const run = () => {
    setFailed(false); setDone([]);
    api.generatePlan((s) => setDone((d) => [...d, s]))
      .then(() => refresh().catch(() => undefined))
      .then(() => nav('/plan-ready', { replace: true }))
      .catch(() => setFailed(true));
  };
  useEffect(() => { if (!started.current) { started.current = true; run(); } }); // eslint-disable-line react-hooks/exhaustive-deps

  if (failed) {
    return (
      <div className="mx-auto flex min-h-screen max-w-xl flex-col gap-6 px-7 py-10">
        <div className="flex justify-end"><PageControls /></div>
        <span className="grid h-24 w-24 place-items-center rounded-full bg-accent-200 text-accent-700"><Icon as={Hourglass} size={40} /></span>
        <div><h1 className="m-0 mb-2 text-3xl">{t('generating.errorTitle')}</h1><p className="m-0 text-neutral-800">{t('generating.errorBody')}</p></div>
        <div className="mt-auto flex flex-col gap-2.5"><Button size="lg" onClick={run}>{t('common.retry')}</Button><LinkButton variant="secondary" size="lg" to="/onboarding/review">{t('generating.editAnswers')}</LinkButton></div>
      </div>
    );
  }

  const active = STEPS.find((s) => !done.includes(s));
  return (
    <div className="mx-auto flex min-h-screen max-w-xl flex-col gap-7 px-7 py-6">
      <div className="flex justify-end"><PageControls /></div>
      <div className="grid h-56 place-items-center"><Breathing mark={t('brand.mark')} /></div>
      <div><h1 className="m-0 mb-2 text-3xl">{t('generating.title', { name: user ? l(user.firstName) : '' })}</h1><p className="m-0 text-neutral-800">{t('generating.body')}</p></div>
      <StepList steps={STEPS.map((s) => ({ label: t(`generating.steps.${s}`), state: done.includes(s) ? 'done' : s === active ? 'active' : 'todo' }))} />
      <p className="m-0 mt-auto flex gap-1.5 text-xs text-neutral-700"><Icon as={Lock} size={14} />{t('generating.private')}</p>
    </div>
  );
}

export function PlanReady() {
  const { t, l, num } = useI18n();
  const q = useQuery(() => Promise.all([api.getPlan(), api.getUser(), api.getExercises()]));
  return (
    <div className="mx-auto flex min-h-screen max-w-3xl flex-col gap-5 px-5 py-6 lg:py-12">
      <div className="flex justify-end"><PageControls /></div>
      <QueryView query={q}>
        {([plan, user, exercises]) => (
          <>
            <div>
              <span className="flex items-center gap-1.5 text-[13px] font-bold text-sage-800"><Icon as={CircleCheck} size={16} />{t('planReady.ready')}</span>
              <h1 className="m-0 my-1.5 text-[34px] lg:text-5xl">{t('planReady.title', { name: l(user.firstName) })}</h1>
              <p className="m-0 text-neutral-800">{t('planReady.sub', { goal: t(`enums.goal.${user.goal}`), days: user.daysPerWeek })}</p>
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <Card className="gap-3.5 p-6">
                <Kicker>{t('planReady.dailyTarget')}</Kicker>
                <div className="flex items-baseline gap-2"><span className="font-heading text-5xl leading-none">{num(plan.calories)}</span><span>{t('units.kcal')}</span></div>
                <p className="m-0 text-sm text-neutral-800"><strong>{t('planReady.why')}</strong> {l(plan.rationale.calories)}</p>
                {([['protein', plan.proteinG, 'bg-sage-600'], ['carbs', plan.carbsG, 'bg-accent-500'], ['fat', plan.fatG, 'bg-neutral-600']] as const).map(([k, g, dot]) => (
                  <div key={k} className="flex items-start gap-3.5 border-t border-divider pt-3">
                    <span className={`mt-1.5 h-3.5 w-3.5 shrink-0 rounded-full ${dot}`} />
                    <div className="flex-1">
                      <div className="flex items-baseline justify-between"><strong>{t(`macros.${k}`)}</strong><span className="font-heading text-xl">{t('units.grams', { n: g })}</span></div>
                      <p className="m-0 mt-0.5 text-[13px] text-neutral-800">{l(plan.rationale[k])}</p>
                    </div>
                  </div>
                ))}
              </Card>
              <div className="flex flex-col gap-4">
                <Card tone="sage" className="p-6">
                  <Kicker className="text-sage-800">{t('planReady.program')}</Kicker>
                  <h2 className="m-0 text-2xl">{l(plan.program.name)}</h2>
                  <div className="grid grid-cols-7 gap-1 text-center text-[11px]">
                    {plan.program.schedule.map((d) => (
                      <span key={d.day} className={d.sessionId ? 'rounded-md bg-sage-600 py-2 font-bold text-bg' : 'rounded-md bg-bg py-2'}>
                        {t(`enums.weekdayShort.${d.day}`)}<br />{d.sessionId ? t(`planReady.${d.kind ?? 'full'}`) : t('planReady.rest')}
                      </span>
                    ))}
                  </div>
                  <p className="m-0 text-sm"><strong>{t('planReady.whyFits')}</strong> {l(plan.program.why)}</p>
                </Card>
                {plan.injurySwaps.length > 0 && (
                  <Card tone="warn" className="p-6">
                    <Kicker className="flex items-center gap-1.5 text-warn-800"><Icon as={Shield} size={14} />{t('planReady.changedFor', { area: t(`body.${plan.injurySwaps[0].region}`) })}</Kicker>
                    {plan.injurySwaps.map((s) => (
                      <div key={s.toExerciseId} className="flex flex-col gap-0.5 rounded-lg bg-bg px-3.5 py-3">
                        <span className="text-[13px] text-neutral-700 line-through">{l(s.fromName)}</span>
                        <strong className="flex items-start gap-1.5"><Icon as={ArrowRight} size={15} flip className="mt-1" />{l(exercises.find((e) => e.id === s.toExerciseId)?.name)}</strong>
                        <span className="text-[12.5px] text-neutral-800">{l(s.reason)}</span>
                      </div>
                    ))}
                  </Card>
                )}
              </div>
            </div>
            <WhyPlanLink />
            <div className="flex flex-col gap-2.5 lg:flex-row">
              <LinkButton to="/workouts" size="lg" icon={Dumbbell} className="lg:flex-1">{t('planReady.seeWorkouts')}</LinkButton>
              <LinkButton to="/nutrition" variant="secondary" size="lg" icon={Salad} className="lg:flex-1">{t('planReady.seeMeals')}</LinkButton>
            </div>
            <Disclaimer />
          </>
        )}
      </QueryView>
    </div>
  );
}
