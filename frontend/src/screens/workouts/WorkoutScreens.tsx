import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  Check, ChevronLeft, ChevronRight, Dumbbell, ExternalLink, Footprints, Info, X, ArrowDown, Shield, Zap, TrendingDown, Bandage, Pencil, Undo2,
} from 'lucide-react';
import {
  AppShell, BodyMap, Button, Card, ChipGroup, ExerciseMedia, ExerciseThumb, Icon, LinkButton, ProgressBar, QueryView, ScalePicker, SwapBadge,
  TextInput, Toggle, buttonClass, cn, type RegionState,
} from '@/components';
import { useI18n } from '@/i18n';
import { api } from '@/data/api';
import { useQuery } from '@/data/useQuery';
import type { BodyRegion, Exercise, ExerciseResult, Injury, SessionExercise, Workout, WorkoutWeek } from '@/types';

type T = (k: string, v?: Record<string, string | number>) => string;

const fmtRest = (sec: number, t: T) =>
  sec >= 120 && sec % 60 === 0 ? t('units.minutesShort', { n: sec / 60 }) : t('units.secondsShort', { n: sec });

/** What "Done as planned" logs: exactly the session's target. */
export const asPlanned = (e: SessionExercise): ExerciseResult => ({ sets: e.target.sets, reps: e.target.reps, weightKg: e.target.weightKg, struggled: false });

function useFormat() {
  const { t, num } = useI18n();
  /** "3 × 9 @ 22.5 kg" (or "3 × 12" for bodyweight) */
  const result = (r: Pick<ExerciseResult, 'sets' | 'reps' | 'weightKg'>) =>
    (r.weightKg ? t('workouts.target', { sets: r.sets, reps: r.reps, kg: num(r.weightKg, 1) }) : t('workouts.targetBw', { sets: r.sets, reps: r.reps }));
  return {
    result,
    target: (e: SessionExercise) => result(e.target),
    /** Why the target changed since last time: "+1 rep", "+2.5 kg", "Same as last time"… */
    reason: (e: SessionExercise) => t(`workouts.reason.${e.target.reason}`, { kg: num(e.weightStepKg ?? 0, 1) }),
  };
}

function useExerciseMap() {
  const q = useQuery(() => api.getExercises());
  return useMemo(() => new Map((q.data ?? []).map((e) => [e.id, e])), [q.data]);
}

const isDesktop = () => typeof window !== 'undefined' && window.matchMedia?.('(min-width: 1024px)').matches;

/** Week overview of the training program. Tapping a day opens that day's session (side panel on desktop). */
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
                  const cls = cn('flex min-h-[72px] w-full items-center gap-3.5 rounded-card px-4 py-3 text-start no-underline lg:min-h-[88px] lg:flex-col lg:items-start lg:gap-0.5 lg:rounded-lg',
                    !s ? 'hidden bg-neutral-100 text-neutral-700 lg:flex' : s.status === 'done' ? 'bg-sage-100 text-ink hover:text-ink' : s.status === 'today' ? 'bg-accent text-on-accent hover:text-on-accent' : 'bg-surface text-ink hover:bg-neutral-300 hover:text-ink',
                    s && s.id === current.id && s.status !== 'today' && 'lg:ring-2 lg:ring-inset lg:ring-accent-700');
                  const inner = (
                    <>
                      {s && <span className={cn('grid h-tap w-tap place-items-center rounded-full lg:hidden', s.status === 'done' ? 'bg-sage-600 text-bg' : s.status === 'today' ? 'bg-bg text-ink' : 'bg-bg')}><Icon as={s.status === 'done' ? Check : s.name.en.includes('Lower') ? Footprints : Dumbbell} /></span>}
                      <span className="flex flex-1 flex-col">
                        <span className="text-xs">{t(`enums.weekdayShort.${day}`)} {s && date(s.date, { day: 'numeric' })}</span>
                        <strong className="text-[15.5px]">{s ? l(s.name) : t('planReady.rest')}</strong>
                        {s && <span className="text-xs">{s.status === 'done' && s.summary ? t('workouts.doneMeta', { min: s.summary.minutes, done: s.summary.setsDone, total: s.summary.setsTotal }) : s.status === 'today' ? t('workouts.todayMeta', { min: s.estMinutes }) : t('units.minutesShort', { n: s.estMinutes })}</span>}
                      </span>
                      {s && <Icon as={ChevronRight} flip size={18} className="lg:hidden" />}
                    </>
                  );
                  return (
                    <li key={day}>
                      {s ? (
                        // A real link on phones (opens the day's page); on desktop it selects the day for the side panel.
                        <Link to={`/workouts/${s.id}`} aria-current={s.id === current.id ? 'true' : undefined} className={cls}
                          onClick={(ev) => { if (isDesktop()) { ev.preventDefault(); setSelected(s.id); } }}>{inner}</Link>
                      ) : <div className={cls}>{inner}</div>}
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

function ExerciseRow({ e, i, ex, result }: { e: SessionExercise; i: number; ex?: Exercise; result?: ExerciseResult | null }) {
  const { t, l, num } = useI18n();
  const fmt = useFormat();
  return (
    <li className="flex flex-col gap-2 rounded-lg bg-surface px-4 pb-3.5 pt-4">
      <div className="flex items-start gap-3">
        <Link to={`/exercises/${e.exerciseId}`} className="flex min-w-0 flex-1 items-start gap-3 text-ink no-underline hover:text-ink">
          <ExerciseThumb ex={ex} n={i + 1} />
          <div className="min-w-0 flex-1">
            <strong className="block text-[15.5px] leading-snug">{l(ex?.name)}</strong>
            <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-[12.5px] text-neutral-800">
              <span><strong>{e.target.sets}</strong> × <strong>{e.target.reps}</strong>{e.target.weightKg ? <> @ <strong>{num(e.target.weightKg, 1)}</strong> {t('units.kg')}</> : null}</span>
              <span>{t('workouts.range', { reps: e.reps })}</span>
              <span>{t('workouts.rest', { t: fmtRest(e.restSec, t) })}</span><span>{t('workouts.rpe', { n: e.rpe })}</span>
            </div>
            {result === undefined && <span className="mt-1.5 inline-block rounded-pill bg-accent-100 px-2.5 py-0.5 text-xs font-semibold text-accent-800">{fmt.reason(e)}</span>}
          </div>
        </Link>
        <InfoLink id={e.exerciseId} name={l(ex?.name)} />
      </div>
      {e.swap && <div className="ps-[68px]"><SwapBadge label={t(e.swap.kind === 'added' ? 'workouts.addedFor' : 'workouts.swappedFor', { area: t('body.shoulderL') })} /></div>}
      {result !== undefined && (
        <div data-testid="logged-result" className={cn('ms-[68px] flex items-center gap-2 rounded-pill px-3 py-1.5 text-[12.5px]', result ? 'bg-sage-100 text-sage-900' : 'bg-neutral-100 text-neutral-800')}>
          {result ? <><Icon as={Check} size={15} className="text-sage-700" /><span>{t('logger.result', { result: fmt.result(result) })}{result.struggled && <> · {t('logger.struggledShort')}</>}</span></> : t('workouts.skipped')}
        </div>
      )}
    </li>
  );
}

function InfoLink({ id, name }: { id: string; name: string }) {
  const { t } = useI18n();
  return <Link to={`/exercises/${id}`} aria-label={t('workouts.howTo', { name })} className="grid h-tap w-tap shrink-0 place-items-center rounded-full text-neutral-700 hover:bg-neutral-300 hover:text-ink"><Icon as={Info} size={18} /></Link>;
}

/** The exercise list plus, once it's done, what was logged. Shared by the desktop panel and the day page. */
function SessionBody({ s, exMap, injuries, twoCols }: { s: Workout; exMap: Map<string, Exercise>; injuries?: Injury[]; twoCols?: boolean }) {
  const { t } = useI18n();
  if (!s.exercises.length) return <p className="m-0 text-neutral-800">{t('workouts.detailsSoon')}</p>;
  const log = s.status === 'done' ? s.log : undefined;
  return (
    <>
      {log && (
        <Card tone="sage" className="gap-2 p-4">
          <strong className="text-base">{t('workouts.whatYouDid')}</strong>
          <div className="flex flex-wrap gap-2 text-[12.5px]">
            <span className="rounded-pill bg-bg px-3 py-1 font-bold">{t('workouts.effortLogged', { n: log.effort })}</span>
            {s.summary && <span className="rounded-pill bg-bg px-3 py-1">{t('workouts.doneMeta', { min: s.summary.minutes, done: s.summary.setsDone, total: s.summary.setsTotal })}</span>}
            {s.summary && Object.entries(s.summary.painByInjury).map(([id, n]) => {
              const inj = injuries?.find((i) => i.id === id);
              return inj ? <span key={id} className="rounded-pill bg-bg px-3 py-1">{t('workouts.painAfter', { area: t(`body.${inj.region}`), n })}</span> : null;
            })}
          </div>
        </Card>
      )}
      <ol className={cn('m-0 grid list-none gap-2.5 p-0', twoCols ? 'grid-cols-2' : 'lg:grid-cols-2')}>
        {s.exercises.map((e, i) => <ExerciseRow key={e.exerciseId} e={e} i={i} ex={exMap.get(e.exerciseId)} result={log ? log.results[e.exerciseId] ?? null : undefined} />)}
      </ol>
      <p className="m-0 text-[12.5px] text-neutral-700">{t('workouts.rpeHelp')}</p>
    </>
  );
}

function SessionPanel({ s, exMap }: { s: Workout; exMap: Map<string, Exercise> }) {
  const { t, l } = useI18n();
  return (
    <Card className="p-6">
      <div className="flex items-start justify-between gap-3">
        <h2 className="m-0 text-3xl">{l(s.name)}</h2>
        <div className="flex gap-2">
          <LinkButton to={`/workouts/${s.id}`} variant="secondary">{t('common.details')}</LinkButton>
          {s.status === 'today' && s.exercises.length > 0 && <LinkButton to={`/workouts/${s.id}/log`}>{t('workouts.start')}</LinkButton>}
        </div>
      </div>
      <SessionBody s={s} exMap={exMap} twoCols />
    </Card>
  );
}

/** One day's session: every exercise with sets × reps, weight, rest and target effort; what was logged once it's done.
 *  Previous / next arrows walk through the week's workouts. Only today's session can be started. */
export function Session() {
  const { id = '' } = useParams();
  const { t, l, date } = useI18n();
  const q = useQuery(() => Promise.all([api.getWorkout(id), api.getWorkoutWeek(), api.getInjuries()]), [id]);
  const exMap = useExerciseMap();
  const s = q.data?.[0];
  return (
    <AppShell back title={s ? l(s.name) : t('nav.workouts')} sub={s ? `${t(`enums.weekday.${s.day}`)} ${date(s.date)} · ${t('workouts.about', { min: s.estMinutes })}` : undefined}>
      <QueryView query={q}>
        {([s, week, injuries]) => (
          <>
            <DayNav s={s} week={week} />
            <div className="flex flex-wrap gap-2">
              <span className="rounded-pill bg-neutral-100 px-3 py-1 text-xs">{t('workouts.nExercises', { n: s.exercises.length })}</span>
              <span className="rounded-pill bg-neutral-100 px-3 py-1 text-xs">{t('workouts.nSets', { n: s.exercises.reduce((a, e) => a + e.sets, 0) })}</span>
              <span className="rounded-pill bg-neutral-100 px-3 py-1 text-xs">{t('workouts.warmup', { n: s.warmupMinutes })}</span>
            </div>
            <SessionBody s={s} exMap={exMap} injuries={injuries} />
            {s.status === 'today' && s.exercises.length > 0 && <LinkButton to={`/workouts/${s.id}/log`} size="lg" block className="lg:w-auto lg:self-start">{t('workouts.start')}</LinkButton>}
            {s.status === 'planned' && <p className="m-0 text-[13px] text-neutral-800">{t('workouts.startOnDay', { day: t(`enums.weekday.${s.day}`) })}</p>}
            {s.status === 'missed' && <p className="m-0 text-[13px] text-neutral-800">{t('workouts.missed')}</p>}
          </>
        )}
      </QueryView>
    </AppShell>
  );
}

function DayNav({ s, week }: { s: Workout; week: WorkoutWeek }) {
  const { t } = useI18n();
  const i = week.sessions.findIndex((x) => x.id === s.id);
  const prev = week.sessions[i - 1];
  const next = week.sessions[i + 1];
  const arrow = (to: Workout | undefined, icon: typeof ChevronLeft, label: string) => (to
    ? <LinkButton to={`/workouts/${to.id}`} replace variant="secondary" size="icon" icon={icon} iconFlip aria-label={label} />
    : <Button variant="secondary" size="icon" icon={icon} iconFlip aria-label={label} disabled />);
  return (
    <nav aria-label={t('nav.workouts')} className="flex items-center justify-between gap-3 lg:justify-start">
      {arrow(prev, ChevronLeft, t('workouts.prevDay'))}
      <span className="text-center text-[13px] text-neutral-800 lg:min-w-48">{t('workouts.dayOf', { n: i + 1, total: week.sessions.length })}</span>
      {arrow(next, ChevronRight, t('workouts.nextDay'))}
    </nav>
  );
}

/** How-to page: demo media, video link, one-line description, steps, cues, mistakes, muscles, alternatives. */
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
                <ExerciseMedia ex={ex} className="h-56 lg:h-80" />
                <p className="m-0 text-[15px] text-neutral-800">{l(ex.description)}</p>
                {ex.videoUrl && (
                  <a href={ex.videoUrl} target="_blank" rel="noopener noreferrer" className={cn(buttonClass('secondary', 'md'), 'self-start')}>
                    <Icon as={ExternalLink} size={18} />{t('exercise.watchVideo')}<span className="sr-only"> {t('common.newTab')}</span>
                  </a>
                )}
                {swap && <SwapBadge label={t('workouts.swappedFor', { area: t('body.shoulderL') })} />}
                <section><h2 className="m-0 mb-2 text-xl">{t('exercise.howTo')}</h2>
                  <ol className="m-0 flex flex-col gap-1.5 ps-5 text-[14.5px]">{ex.instructions.map((s, i) => <li key={i}>{l(s)}</li>)}</ol></section>
                {ex.mediaSource && (
                  <p className="m-0 text-xs text-neutral-700">
                    {t('exercise.credit')} <a href={ex.mediaSource.url} target="_blank" rel="noopener noreferrer">{ex.mediaSource.name}</a> · {ex.mediaSource.license}
                    {ex.mediaSource.note && <> · {l(ex.mediaSource.note)}</>}
                  </p>
                )}
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
                      <span className={cn('grid h-tap w-tap place-items-center rounded-full', a.kind === 'easier' ? 'bg-sage-200 text-sage-800' : a.kind === 'equipment' ? 'bg-neutral-200 text-neutral-800' : 'bg-warn-100 text-warn-800')}><Icon as={a.kind === 'easier' ? ArrowDown : a.kind === 'equipment' ? Dumbbell : Shield} size={18} /></span>
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

/**
 * The whole session on one page. Each exercise is logged in one tap ("Done as planned"), or one row when something
 * was different. "Finish workout" logs everything untouched as planned, then asks one effort question and the pain check.
 */
export function WorkoutLogger() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const { t, l, num } = useI18n();
  const q = useQuery(() => Promise.all([api.getWorkout(id), api.getExercises(), api.getInjuries()]), [id]);
  const key = `rafeqi.logger.${id}.`;
  const [results, setResults] = useSessionState<Record<string, ExerciseResult>>(`${key}results`, {});
  const [finished, setFinished] = useSessionState(`${key}finished`, false);
  const [effort, setEffort] = useSessionState<number | null>(`${key}effort`, null);
  const [editing, setEditing] = useState<string | null>(null);
  const [pain, setPain] = useState<Record<string, number>>({});
  const [flags, setFlags] = useState<string[]>(['none']);
  useEffect(() => { if (finished) window.scrollTo?.(0, 0); }, [finished]);

  return (
    <AppShell back hideTabs title={q.data ? l(q.data[0].name) : ''}>
      <QueryView query={q}>
        {([w, exs, injuries]) => {
          const active = injuries.filter((i) => i.status !== 'resolved');
          const main = active[0];
          const exMap = new Map(exs.map((e) => [e.id, e]));
          const log = (exerciseId: string, r: ExerciseResult | null) => {
            const next = { ...results };
            if (r) next[exerciseId] = r; else delete next[exerciseId];
            setResults(next);
            void api.logExercise(w.id, exerciseId, r);
          };

          if (finished) {
            const redFlag = flags.some((f) => f !== 'none');
            const prevPain = main?.painLog.at(-2)?.pain;
            const done = Object.values(results).filter((r) => r.sets > 0);
            const beat = w.exercises.filter((e) => {
              const r = results[e.exerciseId]; const last = e.lastTime;
              return r && last && r.sets > 0 && (r.weightKg > last.weightKg || (r.weightKg === last.weightKg && r.reps > last.reps));
            }).length;
            return (
              <div className="mx-auto flex w-full max-w-xl flex-col gap-4">
                <h2 className="m-0 text-2xl">{t('logger.doneTitle')}</h2>
                <div className="grid grid-cols-3 gap-2 text-center">
                  {[[num(done.reduce((a, r) => a + r.sets, 0)), t('logger.setsLogged')], [`${done.length}/${w.exercises.length}`, t('logger.exercises')], [num(beat), t('logger.beatLastTime')]].map(([v, k]) => (
                    <div key={k} className="rounded-lg bg-sage-100 px-1.5 py-3.5"><span className="block font-heading text-2xl">{v}</span><span className="text-xs">{k}</span></div>
                  ))}
                </div>
                <Card>
                  <strong className="flex items-center gap-2.5"><Icon as={Dumbbell} className="text-accent-700" />{t('logger.effortQ')}</strong>
                  <ScalePicker label={t('logger.effortLabel')} values={[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]} value={effort ?? undefined} onChange={setEffort} />
                  <div className="flex justify-between text-[11.5px] text-neutral-700"><span>{t('logger.effort1')}</span><span>{t('logger.effort10')}</span></div>
                </Card>
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
                {effort === null && <p className="m-0 text-[13px] text-neutral-800">{t('logger.pickEffort')}</p>}
                <Button size="lg" disabled={effort === null} onClick={async () => {
                  if (effort === null) return;
                  await api.finishWorkout(w.id, { effort, results: Object.fromEntries(Object.entries(results).filter(([, r]) => r.sets > 0)) }, pain, flags.filter((f) => f !== 'none'));
                  clearSessionState(key);
                  const warn = main && (redFlag || Object.values(pain).some((p) => p >= 6));
                  nav(warn ? `/injuries/${main.id}/warning` : `/workouts/${w.id}`, { replace: true });
                }}>{t('logger.saveFinish')}</Button>
              </div>
            );
          }

          if (!w.exercises.length) return <p>{t('workouts.detailsSoon')}</p>;
          const loggedCount = w.exercises.filter((e) => results[e.exerciseId]).length;
          return (
            <div className="mx-auto flex w-full max-w-xl flex-col gap-3.5">
              <div className="flex items-center gap-2.5 text-[13px]">
                <ProgressBar value={loggedCount} max={w.exercises.length} label={t('logger.progress', { done: loggedCount, total: w.exercises.length })} />
                <span className="whitespace-nowrap font-semibold">{t('logger.progress', { done: loggedCount, total: w.exercises.length })}</span>
              </div>
              <ol className="m-0 flex list-none flex-col gap-3 p-0">
                {w.exercises.map((e) => (
                  <LogCard key={e.exerciseId} e={e} ex={exMap.get(e.exerciseId)} result={results[e.exerciseId]} editing={editing === e.exerciseId}
                    onEdit={() => setEditing(e.exerciseId)} onCancel={() => setEditing(null)}
                    onLog={(r) => { log(e.exerciseId, r); setEditing(null); }} />
                ))}
              </ol>
              <p className="m-0 text-[12.5px] text-neutral-700">{t('logger.finishHint')}</p>
              <div className="flex gap-2.5">
                <Button variant="danger" size="lg" icon={Zap} onClick={() => setFinished(true)}>{t('logger.pain')}</Button>
                <Button size="lg" icon={Check} className="flex-1" onClick={() => {
                  const all = { ...results };
                  for (const e of w.exercises) {
                    if (!all[e.exerciseId]) { all[e.exerciseId] = asPlanned(e); void api.logExercise(w.id, e.exerciseId, all[e.exerciseId]); }
                  }
                  setResults(all); setEditing(null); setFinished(true);
                }}>{t('logger.finish')}</Button>
              </div>
            </div>
          );
        }}
      </QueryView>
    </AppShell>
  );
}

function LogCard({ e, ex, result, editing, onEdit, onCancel, onLog }: {
  e: SessionExercise; ex?: Exercise; result?: ExerciseResult; editing: boolean;
  onEdit: () => void; onCancel: () => void; onLog: (r: ExerciseResult | null) => void;
}) {
  const { t, l } = useI18n();
  const fmt = useFormat();
  const name = l(ex?.name);
  return (
    <li data-testid="log-card" className={cn('flex flex-col gap-3 rounded-card p-4', result && !editing ? 'bg-sage-100' : 'bg-surface')}>
      <div className="flex items-center gap-3">
        <Link to={`/exercises/${e.exerciseId}`} className="flex min-w-0 flex-1 items-center gap-3 text-ink no-underline hover:text-ink">
          <ExerciseThumb ex={ex} size={56} />
          <span className="flex min-w-0 flex-col gap-0.5 leading-tight">
            <strong className="text-[15.5px]">{name}</strong>
            <span className="text-[13px] text-neutral-800">{t('logger.targetLine', { target: fmt.target(e) })} <span className="text-neutral-700">· {fmt.reason(e)}</span></span>
            {e.lastTime && <span className="text-xs text-neutral-700">{t('logger.lastTime', { result: fmt.result(e.lastTime) })}{e.lastTime.struggled && <> · {t('logger.struggledShort')}</>}</span>}
          </span>
        </Link>
        <InfoLink id={e.exerciseId} name={name} />
      </div>
      {editing ? (
        <ResultEditor initial={result ?? asPlanned(e)} name={name} onSave={onLog} onCancel={onCancel} />
      ) : result ? (
        <div className="flex items-center gap-2">
          <span className="flex min-w-0 flex-1 items-center gap-2 text-[14px] font-semibold text-sage-900">
            <Icon as={Check} size={18} className="text-sage-700" />
            <span>{result.sets > 0 ? t('logger.result', { result: fmt.result(result) }) : t('workouts.skipped')}{result.struggled && <span className="font-normal"> · {t('logger.struggledShort')}</span>}</span>
          </span>
          <Button variant="ghost" size="icon" icon={Pencil} aria-label={t('logger.editResult', { name })} onClick={onEdit} />
          <Button variant="ghost" size="icon" icon={Undo2} aria-label={`${t('logger.undo')}: ${name}`} onClick={() => onLog(null)} />
        </div>
      ) : (
        <div className="flex gap-2">
          <Button size="lg" icon={Check} className="flex-1" aria-label={`${t('logger.doneAsPlanned')}: ${name}`} onClick={() => onLog(asPlanned(e))}>{t('logger.doneAsPlanned')}</Button>
          <Button variant="secondary" size="lg" icon={Pencil} aria-label={t('logger.editResult', { name })} onClick={onEdit}>{t('common.edit')}</Button>
        </div>
      )}
    </li>
  );
}

/** One row: sets done, reps (one number), weight, and "struggled on the last set". */
function ResultEditor({ initial, name, onSave, onCancel }: { initial: ExerciseResult; name: string; onSave: (r: ExerciseResult) => void; onCancel: () => void }) {
  const { t } = useI18n();
  const [v, setV] = useState({ sets: String(initial.sets), reps: String(initial.reps), weightKg: String(initial.weightKg) });
  const [struggled, setStruggled] = useState(initial.struggled);
  const parse = (s: string) => Number(s.trim().replace(',', '.').replace(/[٠-٩]/g, (d) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(d))));
  const sets = parse(v.sets), reps = parse(v.reps), weightKg = parse(v.weightKg);
  const bad = {
    sets: !(Number.isInteger(sets) && sets >= 0 && sets <= 20),
    reps: !(Number.isInteger(reps) && reps >= 0 && reps <= 100),
    weightKg: !(v.weightKg.trim() !== '' && weightKg >= 0 && weightKg <= 500),
  };
  const fields = [['sets', t('logger.sets'), 'numeric'], ['reps', t('logger.reps'), 'numeric'], ['weightKg', t('logger.weightKg'), 'decimal']] as const;
  return (
    <form className="flex flex-col gap-3" aria-label={t('logger.editResult', { name })}
      onSubmit={(ev) => { ev.preventDefault(); if (!Object.values(bad).some(Boolean)) onSave({ sets, reps: sets ? reps : 0, weightKg: sets ? Math.round(weightKg * 4) / 4 : 0, struggled: sets > 0 && struggled }); }}>
      <div className="grid grid-cols-3 gap-2">
        {fields.map(([k, label, mode]) => (
          <label key={k} className="flex min-w-0 flex-col gap-1 text-xs text-neutral-800">{label}
            <TextInput inputMode={mode} enterKeyHint="done" value={v[k]} invalid={bad[k]} className="px-3 text-center text-lg font-semibold tabular"
              onFocus={(ev) => ev.target.select()} onChange={(ev) => setV({ ...v, [k]: ev.target.value })} />
          </label>
        ))}
      </div>
      <Toggle checked={struggled} onChange={setStruggled} label={<span className="text-[13px]">{t('logger.struggled')}</span>} />
      <div className="flex gap-2">
        <Button type="submit" className="flex-1" disabled={Object.values(bad).some(Boolean)}>{t('logger.saveResult')}</Button>
        <Button variant="secondary" onClick={onCancel}>{t('common.cancel')}</Button>
      </div>
    </form>
  );
}

/** useState that survives leaving the page (e.g. opening an exercise's how-to mid-workout). */
function useSessionState<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>(() => {
    try { const raw = sessionStorage.getItem(key); return raw ? (JSON.parse(raw) as T) : initial; } catch { return initial; }
  });
  useEffect(() => { try { sessionStorage.setItem(key, JSON.stringify(value)); } catch { /* not persisted */ } }, [key, value]);
  return [value, setValue] as const;
}

function clearSessionState(prefix: string) {
  try { Object.keys(sessionStorage).filter((k) => k.startsWith(prefix)).forEach((k) => sessionStorage.removeItem(k)); } catch { /* ignore */ }
}
