import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import { ClipboardCheck, Check, Utensils, Soup, Apple, Drumstick, Egg, NotebookPen, Sprout, Weight, WifiOff } from 'lucide-react';
import {
  AppShell, Button, Card, CitationChip, Disclaimer, EmptyState, Icon, Kicker, LineChart, LinkButton, MacroBars, MacroRing, QueryView, Skeleton, StatusBadge, SwapBadge,
  TextInput, cn, useToast,
} from '@/components';
import { useI18n } from '@/i18n';
import { api } from '@/data/api';
import { useQuery } from '@/data/useQuery';
import type { Dashboard as DashboardData, MealSlot, WeightLog } from '@/types';

export const mealIcon: Record<MealSlot, LucideIcon> = { breakfast: Egg, lunch: Soup, snack: Apple, dinner: Drumstick };

function DashboardSkeleton() {
  return (
    <div aria-busy="true" className="grid gap-4 lg:grid-cols-3">
      {[0, 1, 2].map((i) => (
        <div key={i} className="flex flex-col gap-3 rounded-card bg-surface p-6"><Skeleton className="h-3 w-1/3" /><Skeleton className="h-6 w-2/3" /><Skeleton className="h-3 w-1/2" /><Skeleton className="h-12" /></div>
      ))}
    </div>
  );
}

/** Home. Shows today's session & meals, check-in state, injury status and the latest coach note. */
export function Dashboard() {
  const { t, l, date } = useI18n();
  const q = useQuery(() => api.getDashboard());
  const title = q.data ? t('dashboard.greeting', { name: l(q.data.user.firstName) }) : t('nav.home');
  return (
    <AppShell title={title} sub={date(new Date().toISOString().slice(0, 10), { weekday: 'long', day: 'numeric', month: 'long' })}>
      <QueryView query={q} loading={<DashboardSkeleton />}>
        {(d) => <DashboardBody d={d} offline={false} />}
      </QueryView>
    </AppShell>
  );
}

function DashboardBody({ d, offline }: { d: DashboardData; offline: boolean }) {
  const { t, l, num, date } = useI18n();
  const eaten = d.mealDay.meals.filter((m) => m.eaten);
  const sum = (k: 'kcal' | 'proteinG' | 'carbsG' | 'fatG') => eaten.reduce((a, m) => a + m[k], 0);
  const swaps = d.today?.exercises.filter((e) => e.swap).length ?? 0;
  const shoulder = d.injuries[0];

  return (
    <>
      {offline && <div role="alert" className="flex items-center gap-3 rounded-pill bg-warn-100 px-5 py-3 text-warn-800"><Icon as={WifiOff} />{t('dashboard.offline')}</div>}
      {d.nextCheckIn.due ? (
        <Card tone="attn" className="ring-2 ring-inset ring-attn-300 lg:flex-row lg:items-center">
          <div className="flex flex-1 items-center gap-3">
            <span className="grid h-tap w-tap place-items-center rounded-full bg-attn-600 text-bg"><Icon as={ClipboardCheck} /></span>
            <div><strong className="block">{t('dashboard.checkInDue')}</strong><span className="text-[13px]">{t('dashboard.checkInDueSub')}</span></div>
          </div>
          <LinkButton to="/check-in/body">{t('dashboard.startCheckIn')}</LinkButton>
        </Card>
      ) : (
        <p className="m-0 text-sm text-neutral-800">{t('dashboard.nextCheckIn', { date: date(d.nextCheckIn.date, { weekday: 'long', day: 'numeric', month: 'long' }) })}</p>
      )}

      <div className="grid gap-4 lg:grid-cols-[1.25fr_1fr_.9fr]">
        {d.today ? (
          <Card>
            <div className="flex items-center justify-between"><Kicker>{t('dashboard.todaySession')}</Kicker><span className="text-[12.5px] text-neutral-700">{t('dashboard.weekOf', { week: d.plan.program.currentWeek, total: d.plan.program.totalWeeks })}</span></div>
            <h2 className="m-0 text-2xl">{l(d.today.name)}</h2>
            <span className="text-[13.5px] text-neutral-800">{t('workouts.sessionMeta', { n: d.today.exercises.length, min: d.today.estMinutes })}</span>
            {swaps > 0 && <SwapBadge label={t('dashboard.adjustedFor', { n: swaps, area: t('body.shoulderL') })} />}
            <div className="mt-1 flex gap-2">
              {d.today.status === 'today' && <LinkButton to={`/workouts/${d.today.id}/log`} className="flex-1">{t('workouts.start')}</LinkButton>}
              <LinkButton to={`/workouts/${d.today.id}`} variant="secondary">{t('common.view')}</LinkButton>
            </div>
          </Card>
        ) : (
          <EmptyState icon={Sprout} title={t('dashboard.restDay')} body={d.nextSession ? t('dashboard.nextSessionOn', { name: l(d.nextSession.name), day: t(`enums.weekday.${d.nextSession.day}`) }) : undefined} />
        )}

        <Card>
          <div className="flex items-center justify-between"><Kicker>{t('dashboard.todayMeals')}</Kicker><Link to="/nutrition" className="text-[13px] font-semibold">{t('nav.mealPlan')}</Link></div>
          <div className="flex items-center gap-4">
            <MacroRing eaten={sum('kcal')} target={d.plan.calories} label={t('dashboard.kcalLeft')} />
            <MacroBars rows={[
              { label: t('macros.protein'), value: t('dashboard.gLeft', { n: d.plan.proteinG - sum('proteinG') }), pct: (sum('proteinG') / d.plan.proteinG) * 100, tone: 'sage' },
              { label: t('macros.carbs'), value: t('dashboard.gLeft', { n: d.plan.carbsG - sum('carbsG') }), pct: (sum('carbsG') / d.plan.carbsG) * 100, tone: 'accent' },
              { label: t('macros.fat'), value: t('dashboard.gLeft', { n: d.plan.fatG - sum('fatG') }), pct: (sum('fatG') / d.plan.fatG) * 100, tone: 'neutral' },
            ]} />
          </div>
          <ul className="m-0 flex list-none flex-col gap-1.5 p-0">
            {d.mealDay.meals.map((m) => (
              <li key={m.id} className="flex min-h-[52px] items-center gap-3 rounded-pill bg-bg py-1.5 pe-4 ps-1.5">
                <span className={cn('grid h-10 w-10 place-items-center rounded-full', m.eaten ? 'bg-sage-600 text-bg' : 'bg-surface')}><Icon as={m.eaten ? Check : mealIcon[m.slot] ?? Utensils} size={17} /></span>
                <div className="min-w-0 flex-1 leading-tight"><span className="block text-[11.5px] text-neutral-700">{t(`enums.mealSlot.${m.slot}`)} · {m.eaten ? t('dashboard.eaten') : m.time}</span><strong className="text-sm">{l(m.name)}</strong></div>
                <span className="whitespace-nowrap text-[13px] font-semibold">{t('units.kcalN', { n: num(m.kcal) })}</span>
              </li>
            ))}
          </ul>
        </Card>

        <div className="grid grid-cols-2 gap-3 lg:grid-cols-1 lg:gap-4">
          {shoulder ? (
            <Card className="gap-1.5">
              <StatusBadge status={shoulder.status === 'active' ? 'warning' : 'attention'} label={t(`enums.injuryStatus.${shoulder.status}`)} />
              <strong className="mt-1">{t(`body.${shoulder.region}`)}</strong>
              <div className="hidden lg:block">
                <LineChart ariaLabel={t('injuries.painTrend')} series={[{ values: shoulder.painLog.map((p) => p.pain), tone: 'warn', dots: true }]} labels={[date(shoulder.painLog[0].date), date(shoulder.painLog.at(-1)!.date)]} min={0} max={10} height={80} axisWidth={20} legend={false} />
              </div>
              <span className="text-[12.5px] text-neutral-800">{t('dashboard.painNow', { now: shoulder.painLog.at(-1)?.pain ?? 0, from: shoulder.painLog[0]?.pain ?? 0 })}</span>
              <Link to={`/injuries/${shoulder.id}`} className="mt-auto flex min-h-8 items-end text-[13px] font-semibold">{t('common.details')}</Link>
            </Card>
          ) : null}
          <Card className="gap-1.5">
            <StatusBadge status="onTrack" />
            <strong className="mt-1">{t('dashboard.weight')}</strong>
            <span className="text-[12.5px] text-neutral-800">{t('dashboard.weightAvg', { avg: num(d.weightAvgKg, 1), change: num(d.weightChangeKg, 1) })}</span>
            <WeightQuickLog today={d.weightToday} last={d.weightAvgKg} />
            <Link to="/progress" className="mt-auto flex min-h-8 items-end text-[13px] font-semibold">{t('nav.progress')}</Link>
          </Card>
        </div>
      </div>

      {d.latestReview ? (
        <Card tone="sage">
          <Kicker className="flex items-center gap-1.5 text-sage-800"><Icon as={NotebookPen} size={14} />{t('dashboard.coachNote', { week: d.latestReview.weekNumber })}</Kicker>
          <p className="m-0 text-[15px] leading-relaxed">{l(d.latestReview.summary)}</p>
          <div className="flex flex-wrap items-center justify-between gap-2">
            {d.latestReview.changes[0] && <CitationChip source={l(d.latestReview.changes[0].citation)} />}
            <Link to={`/reviews/${d.latestReview.id}`} className="text-[13px] font-semibold text-sage-800">{t('dashboard.fullReview')}</Link>
          </div>
        </Card>
      ) : (
        <EmptyState title={t('dashboard.noNotesTitle')} body={t('dashboard.noNotesBody')} />
      )}
      <Disclaimer className="lg:hidden" />
    </>
  );
}

/** "Log today's weight": one field inside the Weight card. One entry per day; saving again corrects it. */
function WeightQuickLog({ today, last }: { today: WeightLog | null; last: number }) {
  const { t, num } = useI18n();
  const toast = useToast();
  const [saved, setSaved] = useState(today);
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(String(today?.weightKg ?? last));
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    const kg = Number(value.replace(',', '.').replace('٫', '.'));
    if (!Number.isFinite(kg) || kg < 30 || kg > 300) return setError(t('dashboard.weightRange'));
    setBusy(true);
    try {
      setSaved(await api.logWeight(kg));
      setEditing(false);
      setError(undefined);
      toast({ message: t('dashboard.weightSaved'), tone: 'success' });
    } catch {
      setError(t('dashboard.weightFailed'));
    } finally {
      setBusy(false);
    }
  };

  if (!editing) {
    return saved ? (
      <span className="flex flex-wrap items-center gap-x-1.5 text-[12.5px]">
        <Icon as={Check} size={15} className="text-sage-700" />{t('dashboard.weightToday', { kg: num(saved.weightKg, 1) })}
        <button type="button" onClick={() => { setValue(String(saved.weightKg)); setEditing(true); }} className="min-h-tap font-semibold text-accent-700 hover:underline">{t('common.edit')}</button>
      </span>
    ) : (
      <Button variant="secondary" size="sm" icon={Weight} className="self-start" onClick={() => setEditing(true)}>{t('dashboard.logWeight')}</Button>
    );
  }
  return (
    <form onSubmit={save} noValidate className="flex flex-col gap-1.5">
      <label htmlFor="today-weight" className="text-[12.5px]">{t('dashboard.todayWeightLabel')}</label>
      <div className="flex items-center gap-1.5">
        <TextInput id="today-weight" inputMode="decimal" dir="ltr" autoFocus value={value} invalid={!!error} className="min-w-0 flex-1 text-start"
          aria-describedby={error ? 'today-weight-error' : undefined} onChange={(e) => setValue(e.target.value)} />
        <span className="text-[13px]">{t('units.kg')}</span>
        <Button type="submit" size="icon" icon={Check} aria-label={t('dashboard.saveWeight')} disabled={busy} />
      </div>
      {error && <span id="today-weight-error" role="alert" className="text-xs text-warn-700">{error}</span>}
    </form>
  );
}
