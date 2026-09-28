import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  Check, ChevronLeft, ChevronRight, Dumbbell, Footprints, Info, Play, X, ArrowDown, Shield, Zap, TrendingDown, Bandage,
} from 'lucide-react';
import {
  AppShell, BodyMap, Button, Card, ChipGroup, Icon, LinkButton, ProgressBar, QueryView, ScalePicker, SwapBadge, cn, type RegionState,
} from '@/components';
import { useI18n } from '@/i18n';
import { api } from '@/data/api';
import { useQuery } from '@/data/useQuery';
import type { BodyRegion, Exercise, SessionExercise, SetLog, Workout } from '@/types';

const fmtRest = (sec: number, t: (k: string, v?: Record<string, string | number>) => string) =>
  sec >= 120 && sec % 60 === 0 ? t('units.minutesShort', { n: sec / 60 }) : t('units.secondsShort', { n: sec });

function useExerciseMap() {
  const q = useQuery(() => api.getExercises());
  return useMemo(() => new Map((q.data ?? []).map((e) => [e.id, e])), [q.data]);
}

/** Week overview of the training program. */
export function WorkoutPlan() {
  const { t, l, date } = useI18n();
  const q = useQuery(() => api.getWorkoutWeek());
  const exMap = useExerciseMap();
  const [selected, setSelected] = useState<string>();
  return (
    <AppShell title={t('nav.workouts')} sub={q.data ? t('workouts.programSub', { week: q.data.weekNumber, total: q.data.totalWeeks }) : undefined}>
      <QueryView query={q}>
        {(w) => {
          const current = w.sessions.find((s) => s.id === selected) ?? w.sessions.find((s) => s.status === 'today') ?? w.sessions[0];
          const done = w.sessions.filter((s) => s.status === 'done').length;
          return (
            <>
              <div className="flex items-center justify-between lg:justify-end lg:gap-2">
                <Button variant="secondary" size="icon" icon={ChevronLeft} iconFlip aria-label={t('workouts.prevWeek')} />
                <strong className="min-w-32 text-center">{date(w.start)} – {date(w.end)}</strong>
                <Button variant="secondary" size="icon" icon={ChevronRight} iconFlip aria-label={t('workouts.nextWeek')} />
              </div>
              <ol className="m-0 grid list-none grid-cols-1 gap-2.5 p-0 lg:grid-cols-7">
                {(['sat', 'sun', 'mon', 'tue', 'wed', 'thu', 'fri'] as const).map((day) => {
                  const s = w.sessions.find((x) => x.day === day);
                  return (
                    <li key={day}>
                      <button type="button" disabled={!s} onClick={() => s && setSelected(s.id)} aria-current={s?.id === current.id ? 'true' : undefined}
                        className={cn('flex min-h-[72px] w-full items-center gap-3.5 rounded-card px-4 py-3 text-start lg:min-h-[88px] lg:flex-col lg:items-start lg:gap-0.5 lg:rounded-lg',
                          !s ? 'hidden bg-neutral-100 text-neutral-700 lg:flex' : s.status === 'done' ? 'bg-sage-100' : s.status === 'today' ? 'bg-accent text-bg' : 'bg-surface hover:bg-neutral-300',
                          s && s.id === current.id && s.status !== 'today' && 'ring-2 ring-inset ring-accent')}>
                        {s && <span className={cn('grid h-tap w-tap place-items-center rounded-full lg:hidden', s.status === 'done' ? 'bg-sage-600 text-bg' : s.status === 'today' ? 'bg-bg text-ink' : 'bg-bg')}><Icon as={s.status === 'done' ? Check : s.name.en.includes('Lower') ? Footprints : Dumbbell} /></span>}
                        <span className="flex flex-1 flex-col">
                          <span className="text-xs">{t(`enums.weekdayShort.${day}`)} {s && date(s.date, { day: 'numeric' })}</span>
                          <strong className="text-[15.5px]">{s ? l(s.name) : t('planReady.rest')}</strong>
                          {s && <span className="text-xs">{s.status === 'done' && s.summary ? t('workouts.doneMeta', { min: s.summary.minutes, done: s.summary.setsDone, total: s.summary.setsTotal }) : s.status === 'today' ? t('workouts.todayMeta', { min: s.estMinutes }) : t('units.minutesShort', { n: s.estMinutes })}</span>}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ol>
              <div className="flex items-center gap-2.5 text-[13px]"><ProgressBar value={done} max={w.sessions.length} label={t('workouts.weekProgress')} /><span className="whitespace-nowrap font-semibold">{t('workouts.doneOf', { done, total: w.sessions.length })}</span></div>
              <p className="m-0 text-[12.5px] text-neutral-700">{t('workouts.deload', { week: w.deloadWeek })}</p>
              <div className="hidden lg:block"><SessionPanel s={current} exMap={exMap} /></div>
            </>
          );
        }}
      </QueryView>
    </AppShell>
  );
}

function ExerciseRow({ e, i, ex }: { e: SessionExercise; i: number; ex?: Exercise }) {
  const { t, l } = useI18n();
  return (
    <li className="flex flex-col gap-2 rounded-lg bg-surface px-4 pb-3.5 pt-4">
      <div className="flex items-start gap-3">
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-bg text-[13px] font-bold">{i + 1}</span>
        <div className="min-w-0 flex-1">
          <strong className="block text-[15.5px] leading-snug">{l(ex?.name)}</strong>
          <div className="mt-1 flex flex-wrap gap-3 text-[12.5px] text-neutral-800">
            <span><strong>{e.sets}</strong> × {e.reps}</span><span>{t('workouts.rest', { t: fmtRest(e.restSec, t) })}</span><span>{t('workouts.rpe', { n: e.rpe })}</span>
          </div>
        </div>
        <Link to={`/exercises/${e.exerciseId}`} aria-label={t('workouts.howTo', { name: l(ex?.name) })} className="grid h-tap w-tap place-items-center rounded-full text-neutral-700 hover:bg-neutral-300"><Icon as={Info} size={18} /></Link>
      </div>
      {e.swap && <div className="ps-11"><SwapBadge label={t(e.swap.kind === 'added' ? 'workouts.addedFor' : 'workouts.swappedFor', { area: t('body.shoulderL') })} /></div>}
    </li>
  );
}

function SessionPanel({ s, exMap }: { s: Workout; exMap: Map<string, Exercise> }) {
  const { t, l } = useI18n();
  if (!s.exercises.length) return <Card><h2 className="m-0 text-2xl">{l(s.name)}</h2><p className="m-0 text-neutral-800">{t('workouts.detailsSoon')}</p></Card>;
  return (
    <Card className="p-6">
      <div className="flex items-start justify-between"><h2 className="m-0 text-3xl">{l(s.name)}</h2><LinkButton to={`/workouts/${s.id}/log`}>{t('workouts.start')}</LinkButton></div>
      <ol className="m-0 grid list-none grid-cols-2 gap-2.5 p-0">{s.exercises.map((e, i) => <ExerciseRow key={e.exerciseId} e={e} i={i} ex={exMap.get(e.exerciseId)} />)}</ol>
      <p className="m-0 text-[12.5px] text-neutral-700">{t('workouts.rpeHelp')}</p>
    </Card>
  );
}

/** One session: exercises, sets, reps, rest, RPE and injury swap badges. */
export function Session() {
  const { id = '' } = useParams();
  const { t, l, date } = useI18n();
  const q = useQuery(() => api.getWorkout(id), [id]);
  const exMap = useExerciseMap();
  return (
    <AppShell back title={q.data ? l(q.data.name) : t('nav.workouts')} sub={q.data ? `${t(`enums.weekday.${q.data.day}`)} ${date(q.data.date)} · ${t('workouts.about', { min: q.data.estMinutes })}` : undefined}>
      <QueryView query={q}>
        {(s) => (
          <>
            <div className="flex flex-wrap gap-2">
              <span className="rounded-pill bg-neutral-100 px-3 py-1 text-xs">{t('workouts.nExercises', { n: s.exercises.length })}</span>
              <span className="rounded-pill bg-neutral-100 px-3 py-1 text-xs">{t('workouts.nSets', { n: s.exercises.reduce((a, e) => a + e.sets, 0) })}</span>
              <span className="rounded-pill bg-neutral-100 px-3 py-1 text-xs">{t('workouts.warmup', { n: s.warmupMinutes })}</span>
            </div>
            <ol className="m-0 grid list-none gap-2.5 p-0 lg:grid-cols-2">{s.exercises.map((e, i) => <ExerciseRow key={e.exerciseId} e={e} i={i} ex={exMap.get(e.exerciseId)} />)}</ol>
            <p className="m-0 text-[12.5px] text-neutral-700">{t('workouts.rpeHelp')}</p>
            {s.status !== 'done' && s.exercises.length > 0 && <LinkButton to={`/workouts/${s.id}/log`} size="lg" block className="lg:w-auto lg:self-start">{t('workouts.start')}</LinkButton>}
          </>
        )}
      </QueryView>
    </AppShell>
  );
}

/** How-to page: media placeholder, steps, cues, mistakes, muscles, alternatives. */
export function ExerciseDetail() {
  const { id = '' } = useParams();
  const { t, l } = useI18n();
  const q = useQuery(() => Promise.all([api.getExercise(id), api.getPlan()]), [id]);
  return (
    <AppShell back hideTabs title={q.data ? l(q.data[0].name) : ''}>
      <QueryView query={q}>
        {([ex, plan]) => {
          const swap = plan.injurySwaps.find((s) => s.toExerciseId === ex.id);
          const marks = Object.fromEntries([...ex.muscles.primary.map((r) => [r, 'muscle']), ...ex.muscles.secondary.map((r) => [r, 'muscle2'])]) as Partial<Record<BodyRegion, RegionState>>;
          return (
            <div className="grid gap-5 lg:grid-cols-[1fr_1fr]">
              <div className="flex flex-col gap-4">
                <div className="washed relative grid h-56 place-items-center overflow-hidden rounded-card bg-sage-200 lg:h-80" aria-label={t('exercise.media')}>
                  {ex.mediaUrl ? <img src={ex.mediaUrl} alt="" className="h-full w-full object-cover" /> : (
                    <span className="relative flex flex-col items-center gap-2 text-sage-900"><span className="grid h-16 w-16 place-items-center rounded-full bg-bg"><Icon as={Play} size={26} /></span><span className="text-[12.5px] font-semibold">{t('exercise.mediaPlaceholder')}</span></span>
                  )}
                </div>
                {swap && <SwapBadge label={t('workouts.swappedFor', { area: t('body.shoulderL') })} />}
                <section><h2 className="m-0 mb-2 text-xl">{t('exercise.howTo')}</h2>
                  <ol className="m-0 flex flex-col gap-1.5 ps-5 text-[14.5px]">{ex.steps.map((s, i) => <li key={i}>{l(s)}</li>)}</ol></section>
              </div>
              <div className="flex flex-col gap-4">
                <Card tone="sage"><h3 className="m-0 text-base text-sage-800">{t('exercise.cues')}</h3>
                  {ex.cues.map((c, i) => <span key={i} className="flex gap-2.5 text-sm"><Icon as={Check} size={17} className="mt-0.5 text-sage-600" />{l(c)}</span>)}</Card>
                <Card tone="accent"><h3 className="m-0 text-base text-accent-800">{t('exercise.mistakes')}</h3>
                  {ex.mistakes.map((c, i) => <span key={i} className="flex gap-2.5 text-sm"><Icon as={X} size={17} className="mt-0.5 text-accent-600" />{l(c)}</span>)}</Card>
                <Card className="flex-row items-center gap-4">
                  <BodyMap view="front" marks={marks} width={110} showLabels={false} />
                  <div className="flex flex-col gap-2 text-[13.5px]"><h3 className="m-0 text-base">{t('exercise.muscles')}</h3><span>{l(ex.muscleNames)}</span></div>
                </Card>
                <section className="flex flex-col gap-2"><h2 className="m-0 text-xl">{t('exercise.alternatives')}</h2>
                  {ex.alternatives.map((a, i) => (
                    <div key={i} className="flex min-h-[60px] items-center gap-3 rounded-pill bg-surface py-2 pe-3 ps-2">
                      <span className={cn('grid h-tap w-tap place-items-center rounded-full', a.kind === 'easier' ? 'bg-sage-200 text-sage-800' : 'bg-warn-100 text-warn-800')}><Icon as={a.kind === 'easier' ? ArrowDown : Shield} size={18} /></span>
                      <div className="flex-1 leading-tight"><strong className="block text-[14.5px]">{l(a.name)}</strong><span className="text-xs text-neutral-700">{t(`exercise.kind.${a.kind}`)}</span></div>
                    </div>
                  ))}
                </section>
              </div>
            </div>
          );
        }}
      </QueryView>
    </AppShell>
  );
}

/** Big-target set logger with last session reference, rest timer, then post-session pain check. */
export function WorkoutLogger() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const { t, l, num } = useI18n();
  const q = useQuery(() => Promise.all([api.getWorkout(id), api.getExercises(), api.getInjuries()]), [id]);
  const [exIdx, setExIdx] = useState(0);
  const [logs, setLogs] = useState<Record<string, SetLog[]>>({});
  const [draft, setDraft] = useState<SetLog | null>(null);
  const [rest, setRest] = useState<number | null>(null);
  const [finished, setFinished] = useState(false);
  const [pain, setPain] = useState<Record<string, number>>({});
  const [flags, setFlags] = useState<string[]>(['none']);
  useEffect(() => {
    if (rest === null) return;
    if (rest <= 0) { setRest(null); return; }
    const timer = setTimeout(() => setRest((r) => (r === null ? null : r - 1)), 1000);
    return () => clearTimeout(timer);
  }, [rest]);

  return (
    <AppShell back hideTabs title={q.data ? l(q.data[1].find((e) => e.id === q.data![0].exercises[exIdx]?.exerciseId)?.name) : ''}>
      <QueryView query={q}>
        {([w, exs, injuries]) => {
          const active = injuries.filter((i) => i.status !== 'resolved');
          const main = active[0];
          if (finished) {
            const redFlag = flags.some((f) => f !== 'none');
            const prevPain = main?.painLog.at(-2)?.pain;
            return (
              <div className="mx-auto flex w-full max-w-xl flex-col gap-4">
                <h2 className="m-0 text-2xl">{t('logger.doneTitle')}</h2>
                <div className="grid grid-cols-3 gap-2 text-center">
                  {[[num(Object.values(logs).flat().length), t('logger.setsLogged')], [String(w.exercises.length), t('logger.exercises')], ['1', t('logger.newRecord')]].map(([v, k]) => (
                    <div key={k} className="rounded-lg bg-sage-100 px-1.5 py-3.5"><span className="block font-heading text-2xl">{v}</span><span className="text-xs">{k}</span></div>
                  ))}
                </div>
                {active.map((inj) => (
                  <Card key={inj.id}>
                    <strong className="flex items-center gap-2.5"><Icon as={Bandage} className="text-warn-600" />{t('logger.painQ', { area: t(`body.${inj.region}`) })}</strong>
                    <ScalePicker label={t('logger.painLabel')} values={[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]} value={pain[inj.id]} dangerFrom={6} onChange={(v) => setPain({ ...pain, [inj.id]: v })} />
                    <div className="flex justify-between text-[11.5px] text-neutral-700"><span>{t('logger.pain0')}</span><span>{t('logger.pain10')}</span></div>
                    <span className="text-[13px]">{t('logger.anyOfThese')}</span>
                    <ChipGroup label={t('logger.anyOfThese')} options={(['sharpPain', 'swelling', 'numbness', 'none'] as const).map((f) => ({ id: f, label: t(`redFlags.${f}`) }))}
                      value={flags} onChange={(v) => setFlags(v.at(-1) === 'none' || v.length === 0 ? ['none'] : v.filter((x) => x !== 'none'))} />
                  </Card>
                ))}
                {main && !redFlag && pain[main.id] !== undefined && prevPain !== undefined && pain[main.id] < prevPain && (
                  <div className="flex items-start gap-3 rounded-lg bg-sage-100 px-4 py-4 text-sm text-sage-900"><Icon as={TrendingDown} />{t('logger.painDown', { prev: prevPain })}</div>
                )}
                <Button size="lg" onClick={async () => {
                  await api.finishWorkout(w.id, pain, flags.filter((f) => f !== 'none'));
                  const warn = main && (redFlag || Object.values(pain).some((p) => p >= 6));
                  nav(warn ? `/injuries/${main.id}/warning` : '/', { replace: true });
                }}>{t('logger.saveFinish')}</Button>
              </div>
            );
          }

          const se = w.exercises[exIdx];
          if (!se) return <p>{t('workouts.detailsSoon')}</p>;
          const done = logs[se.exerciseId] ?? [];
          const setNo = done.length;
          const last = se.lastTime?.[setNo] ?? se.lastTime?.at(-1);
          const cur = draft ?? { reps: last?.reps ?? 10, weightKg: last?.weightKg ?? 10, rpe: se.rpe };
          const logSet = async () => {
            const next = [...done, cur];
            setLogs({ ...logs, [se.exerciseId]: next }); setDraft(null);
            await api.logSet(w.id, se.exerciseId, setNo, cur);
            if (next.length >= se.sets) { if (exIdx + 1 < w.exercises.length) { setExIdx(exIdx + 1); setRest(null); } else setFinished(true); }
            else setRest(se.restSec);
          };
          return (
            <div className="mx-auto flex w-full max-w-xl flex-col gap-3.5">
              <span className="text-[13px] text-neutral-700">{t('logger.exerciseOf', { n: exIdx + 1, total: w.exercises.length })} · {l(exs.find((e) => e.id === se.exerciseId)?.name)}</span>
              {rest !== null && (
                <div className="flex items-center gap-3 rounded-card bg-sage-100 px-4 py-3.5" role="timer" aria-live="off">
                  <span className="grid h-[72px] w-[72px] shrink-0 place-items-center rounded-full bg-sage-600 font-bold text-bg tabular">{Math.floor(rest / 60)}:{String(rest % 60).padStart(2, '0')}</span>
                  <div className="flex-1"><strong className="block text-sage-900">{t('logger.rest')}</strong><span className="text-[12.5px] text-sage-800">{t('logger.nextSet', { n: setNo + 1, total: se.sets })}</span></div>
                  <Button variant="secondary" size="sm" onClick={() => setRest(rest + 30)}>{t('logger.plus30')}</Button>
                  <Button variant="secondary" size="sm" onClick={() => setRest(null)}>{t('logger.skip')}</Button>
                </div>
              )}
              <table className="w-full border-separate border-spacing-y-1.5 text-sm">
                <thead><tr className="text-start text-[11.5px] text-neutral-700"><th className="ps-3 text-start font-normal">{t('logger.set')}</th><th className="text-start font-normal">{t('logger.lastTime')}</th><th className="text-start font-normal">{t('logger.repsKg')}</th><th className="text-start font-normal">{t('logger.rpeShort')}</th></tr></thead>
                <tbody>
                  {Array.from({ length: se.sets }, (_, i) => {
                    const lg = done[i]; const lt = se.lastTime?.[i];
                    return (
                      <tr key={i} className={cn('h-[52px]', lg ? 'bg-sage-100' : i === setNo ? 'outline outline-2 -outline-offset-2 outline-accent' : 'bg-surface text-neutral-700')}>
                        <td className="rounded-s-pill ps-3 font-bold">{i + 1}</td>
                        <td className="text-neutral-700">{lt ? `${lt.reps} × ${num(lt.weightKg, 1)}` : '—'}</td>
                        <td className="font-bold">{lg ? `${lg.reps} × ${num(lg.weightKg, 1)}` : i === setNo ? <span className="text-accent-700">{t('logger.now')}</span> : '—'}</td>
                        <td className="rounded-e-pill pe-3">{lg ? lg.rpe : ''}{lg && <Icon as={Check} size={16} className="ms-2 inline text-sage-700" />}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <div className="grid grid-cols-2 gap-2.5">
                <Card className="items-center gap-1.5 p-3"><span className="text-xs text-neutral-700">{t('logger.repsTarget', { reps: se.reps })}</span>
                  <Stepper value={cur.reps} step={1} label={t('logger.reps')} onChange={(reps) => setDraft({ ...cur, reps })} /></Card>
                <Card className="items-center gap-1.5 p-3"><span className="text-xs text-neutral-700">{t('logger.weightKg')}</span>
                  <Stepper value={cur.weightKg} step={se.weightStepKg ?? 2.5} label={t('logger.weightKg')} onChange={(weightKg) => setDraft({ ...cur, weightKg })} /></Card>
              </div>
              <span className="text-[12.5px] text-neutral-700">{t('logger.howHard', { n: se.rpe })}</span>
              <ScalePicker size="lg" label={t('logger.rpeShort')} values={[6, 7, 8, 9, 10]} value={cur.rpe} onChange={(rpe) => setDraft({ ...cur, rpe })} />
              <div className="mt-2 flex gap-2.5">
                <Button variant="danger" size="lg" icon={Zap} onClick={() => setFinished(true)}>{t('logger.pain')}</Button>
                <Button size="lg" icon={Check} className="flex-1" onClick={logSet}>{t('logger.logSet', { n: setNo + 1 })}</Button>
              </div>
            </div>
          );
        }}
      </QueryView>
    </AppShell>
  );
}

function Stepper({ value, onChange, step, label }: { value: number; onChange: (v: number) => void; step: number; label: string }) {
  const { t, num } = useI18n();
  return (
    <div className="flex items-center gap-1.5" role="group" aria-label={label}>
      <button type="button" aria-label={t('common.decrease', { label })} onClick={() => onChange(Math.max(0, value - step))} className="grid h-14 w-14 place-items-center rounded-full bg-bg text-xl font-bold">−</button>
      <output className="min-w-11 text-center font-heading text-[34px] tabular">{num(value, 1)}</output>
      <button type="button" aria-label={t('common.increase', { label })} onClick={() => onChange(value + step)} className="grid h-14 w-14 place-items-center rounded-full bg-bg text-xl font-bold">+</button>
    </div>
  );
}
