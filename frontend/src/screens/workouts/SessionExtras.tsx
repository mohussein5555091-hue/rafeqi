import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Bandage, Check, Flame, HeartPulse, Info, Repeat, Snowflake, X } from 'lucide-react';
import { Button, Card, ExerciseThumb, Icon, Kicker, NumberStepper, QueryView, Segmented, Toggle, cn, inRange, useToast } from '@/components';
import { useI18n } from '@/i18n';
import { api } from '@/data/api';
import { useQuery } from '@/data/useQuery';
import type { CardioSession, Exercise, ExerciseAlternative, ExerciseSwapInfo, Injury, SessionExercise, SwapReason, Target, Workout } from '@/types';

/** Today's date (yyyy-mm-dd) on this device. */
export const todayIso = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

/** Ticks are allowed on today's session (before or after finishing it). */
export const canTick = (w: Workout) => w.status === 'today' || (w.status === 'done' && w.date === todayIso());

export function InfoLink({ id, name }: { id: string; name: string }) {
  const { t } = useI18n();
  return <Link to={`/exercises/${id}`} aria-label={t('workouts.howTo', { name })} className="grid h-tap w-tap shrink-0 place-items-center rounded-full text-neutral-700 hover:bg-neutral-300 hover:text-ink"><Icon as={Info} size={18} /></Link>;
}

/** "Swapped for your left shoulder", "Swapped: no cable machine"… */
export function useSwapLabel() {
  const { t, l } = useI18n();
  return (s: ExerciseSwapInfo) => (s.kind === 'user' ? t('swap.badge', { why: l(s.why) })
    : t(s.kind === 'added' ? 'workouts.addedFor' : 'workouts.swappedFor', { area: t(`body.${s.region}`) }));
}

/** "3 × 9 @ 22.5 kg" (or "3 × 12" for bodyweight). */
export function useTargetText() {
  const { t, num } = useI18n();
  return (r: Pick<Target, 'sets' | 'reps' | 'weightKg'>) =>
    (r.weightKg ? t('workouts.target', { sets: r.sets, reps: r.reps, kg: num(r.weightKg, 1) }) : t('workouts.targetBw', { sets: r.sets, reps: r.reps }));
}

function MoveRow({ ex, id, detail }: { ex?: Exercise; id: string; detail: string }) {
  const { l } = useI18n();
  return (
    <li className="flex min-h-[56px] items-center gap-3">
      <Link to={`/exercises/${id}`} className="flex min-w-0 flex-1 items-center gap-3 text-ink no-underline hover:text-ink">
        <ExerciseThumb ex={ex} size={44} />
        <span className="flex min-w-0 flex-col leading-tight"><strong className="text-[14.5px]">{l(ex?.name)}</strong><span className="text-[12.5px] text-neutral-800">{detail}</span></span>
      </Link>
      <InfoLink id={id} name={l(ex?.name)} />
    </li>
  );
}

function SectionTick({ w, section, done, label }: { w: Workout; section: 'warmup' | 'cooldown'; done: boolean; label: string }) {
  const { t } = useI18n();
  const toast = useToast();
  const [on, setOn] = useState(done);
  if (!canTick(w)) return done ? <span className="flex items-center gap-1.5 text-[13px] font-semibold text-sage-800"><Icon as={Check} size={16} />{label}</span> : null;
  return (
    <Toggle checked={on} label={<span className="text-[13.5px] font-semibold">{label}</span>} onChange={(v) => {
      setOn(v);
      api.tickSection(w.id, section, v).catch(() => { setOn(!v); toast({ message: t('common.saveFailed'), tone: 'error' }); });
    }} />
  );
}

/** Before the exercises: easy movement, mobility moves for today's muscles, then lighter sets of the first exercise. */
export function WarmupSection({ w, exMap }: { w: Workout; exMap: Map<string, Exercise> }) {
  const { t, l, num } = useI18n();
  const wu = w.warmup;
  if (!wu) return null;
  const ramp = wu.rampUp;
  return (
    <Card data-testid="warmup" className="gap-3">
      <div className="flex items-center justify-between gap-3">
        <h2 className="m-0 flex items-center gap-2 text-xl"><Icon as={Flame} className="text-accent-700" />{t('warmup.title')}</h2>
        <span className="rounded-pill bg-neutral-100 px-3 py-1 text-xs">{t('warmup.about', { n: wu.minutes })}</span>
      </div>
      <ol className="m-0 flex list-none flex-col gap-1 p-0">
        {wu.general && <MoveRow id={wu.general.exerciseId} ex={exMap.get(wu.general.exerciseId)} detail={t('warmup.general', { min: wu.general.minutes })} />}
      </ol>
      <Kicker>{t('warmup.moves')}</Kicker>
      <ol className="m-0 flex list-none flex-col gap-1 p-0">
        {wu.moves.map((m) => <MoveRow key={m.exerciseId} id={m.exerciseId} ex={exMap.get(m.exerciseId)} detail={l(m.amount)} />)}
      </ol>
      {ramp && (
        <>
          <Kicker>{t('warmup.ramp', { name: l(exMap.get(ramp.exerciseId)?.name) })}</Kicker>
          <ol className="m-0 flex list-none flex-wrap gap-2 p-0">
            {ramp.sets.map((s, i) => (
              <li key={i} className="rounded-pill bg-accent-100 px-3 py-1.5 text-[13px] text-accent-900">
                <strong>{t('warmup.rampPct', { pct: s.pct })}</strong> · {t('warmup.rampSet', { reps: s.reps, kg: num(s.weightKg, 1) })}
              </li>
            ))}
          </ol>
        </>
      )}
      {wu.skipped.length > 0 && (
        <div className="flex flex-col gap-1 rounded-lg bg-warn-100 px-3.5 py-2.5 text-[12.5px] text-warn-800">
          <strong className="flex items-center gap-1.5"><Icon as={Bandage} size={15} />{t('warmup.skipped')}</strong>
          {wu.skipped.map((s) => <span key={s.exerciseId}>{l(s.why)}</span>)}
        </div>
      )}
      <SectionTick w={w} section="warmup" done={wu.done} label={t('warmup.done')} />
    </Card>
  );
}

/** After the exercises: stretches for the muscles trained, then slow breathing, with a "Done" tick. */
export function CooldownSection({ w, exMap }: { w: Workout; exMap: Map<string, Exercise> }) {
  const { t } = useI18n();
  const cd = w.cooldown;
  if (!cd) return null;
  return (
    <Card data-testid="cooldown" className="gap-3">
      <div className="flex items-center justify-between gap-3">
        <h2 className="m-0 flex items-center gap-2 text-xl"><Icon as={Snowflake} className="text-sage-700" />{t('cooldown.title')}</h2>
        <span className="rounded-pill bg-neutral-100 px-3 py-1 text-xs">{t('cooldown.about', { n: cd.minutes })}</span>
      </div>
      <ol className="m-0 flex list-none flex-col gap-1 p-0">
        {cd.stretches.map((s) => (
          <MoveRow key={s.exerciseId} id={s.exerciseId} ex={exMap.get(s.exerciseId)} detail={t(s.eachSide ? 'cooldown.eachSide' : 'cooldown.hold', { s: s.seconds })} />
        ))}
        {cd.breathing && <MoveRow id={cd.breathing.exerciseId} ex={exMap.get(cd.breathing.exerciseId)} detail={t('cooldown.breathing', { min: cd.breathing.minutes })} />}
      </ol>
      <SectionTick w={w} section="cooldown" done={cd.done} label={t('cooldown.done')} />
    </Card>
  );
}

/** Cardio: after lifting, or a rest day's whole session. Marked done with the minutes actually done. */
export function CardioCard({ w, c, exMap, onChange }: { w: Workout; c: CardioSession; exMap: Map<string, Exercise>; onChange?: () => void }) {
  const { t, l, num } = useI18n();
  const toast = useToast();
  const [minutes, setMinutes] = useState<number | undefined>(c.done?.minutes ?? c.minutes);
  const [done, setDone] = useState(c.done);
  const [busy, setBusy] = useState(false);
  const ex = exMap.get(c.exerciseId);
  const open = w.date <= todayIso();
  const save = async (m: number | null) => {
    setBusy(true);
    try {
      await api.logCardio(w.day, m);
      setDone(m === null ? undefined : { minutes: m });
      onChange?.();
    } catch {
      toast({ message: t('common.saveFailed'), tone: 'error' });
    } finally {
      setBusy(false);
    }
  };
  return (
    <Card data-testid="cardio" tone={done ? 'sage' : 'surface'} className="gap-3">
      <div className="flex items-center justify-between gap-3">
        <h2 className="m-0 flex items-center gap-2 text-xl"><Icon as={HeartPulse} className="text-warn-600" />{t('cardio.title')}</h2>
        <span className="rounded-pill bg-neutral-100 px-3 py-1 text-xs">{t(c.when === 'afterLifting' ? 'cardio.afterLifting' : 'cardio.restDay')}</span>
      </div>
      <ol className="m-0 list-none p-0">
        <MoveRow id={c.exerciseId} ex={ex} detail={`${t('cardio.minutes', { n: c.minutes })} · ${l(c.intensityName)}`} />
      </ol>
      {done ? (
        <div className="flex items-center gap-2">
          <span className="flex flex-1 items-center gap-2 text-[14px] font-semibold text-sage-900"><Icon as={Check} size={18} className="text-sage-700" />{t('cardio.done', { n: num(done.minutes) })}</span>
          <Button variant="ghost" size="sm" disabled={busy} onClick={() => save(null)}>{t('cardio.undo')}</Button>
        </div>
      ) : open ? (
        <div className="flex flex-col gap-2">
          <span className="text-[13px] text-neutral-800">{t('cardio.minutesDone')}</span>
          <div className="flex items-start gap-2">
            <div className="flex-1"><NumberStepper label={t('cardio.minutesDone')} value={minutes} onChange={setMinutes} min={1} max={300} step={5} unit={t('units.minutesUnit')} /></div>
            <Button size="lg" icon={Check} disabled={busy || !inRange(minutes, 1, 300)} onClick={() => inRange(minutes, 1, 300) && save(Math.round(minutes))}>{t('cardio.markDone')}</Button>
          </div>
        </div>
      ) : <p className="m-0 text-[13px] text-neutral-800">{t('cardio.notYet', { day: t(`enums.weekday.${w.day}`) })}</p>}
    </Card>
  );
}

const REASONS: SwapReason[] = ['equipment', 'busy', 'cantDo', 'pain'];

/**
 * Swap an exercise: why (one tap) → 2–4 alternatives (same movement and muscles, fit the equipment and injuries)
 * → just today or from now on. "It causes pain" then offers to add or update an injury.
 */
export function SwapSheet({ w, e, exMap, injuries, onClose, onSwapped }: {
  w: Workout; e: SessionExercise; exMap: Map<string, Exercise>; injuries: Injury[]; onClose: () => void; onSwapped: (workoutId: string) => void;
}) {
  const { t, l } = useI18n();
  const toast = useToast();
  const nav = useNavigate();
  const target = useTargetText();
  const [reason, setReason] = useState<SwapReason>();
  const [pick, setPick] = useState<ExerciseAlternative>();
  const [scope, setScope] = useState<'today' | 'always'>('today');
  const [busy, setBusy] = useState(false);
  const [painFor, setPainFor] = useState<string>(); // after a "pain" swap: the new workout id
  const name = l(exMap.get(e.exerciseId)?.name);
  const active = injuries.filter((i) => i.status !== 'resolved');

  const confirm = async () => {
    if (!reason || !pick) return;
    setBusy(true);
    try {
      const out = await api.swapExercise(w.id, e.exerciseId, pick.exerciseId, reason, scope);
      toast({ message: t('swap.done', { name: l(pick.name) }), tone: 'success' });
      if (reason === 'pain') setPainFor(out.workoutId);
      else onSwapped(out.workoutId);
    } catch {
      toast({ message: t('common.saveFailed'), tone: 'error' });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-neutral-900/50 lg:items-center" role="dialog" aria-modal="true" aria-label={t('swap.title', { name })} onClick={onClose}>
      <div className="flex max-h-[90vh] w-full max-w-lg flex-col gap-3 overflow-auto rounded-t-[36px] bg-bg px-4 pb-7 pt-3 shadow-lg lg:rounded-card" onClick={(ev) => ev.stopPropagation()}>
        <span className="h-1.5 w-11 self-center rounded-pill bg-neutral-400 lg:hidden" />
        <div className="flex items-center justify-between gap-3"><h2 className="m-0 text-2xl">{t('swap.title', { name })}</h2><Button variant="secondary" size="icon" icon={X} aria-label={t('common.close')} onClick={onClose} /></div>
        {painFor ? (
          <div className="flex flex-col gap-3">
            <div className="flex items-start gap-3 rounded-lg bg-warn-100 px-4 py-4 text-warn-800"><Icon as={Bandage} /><div className="text-sm"><strong className="mb-0.5 block text-[15px]">{t('swap.painTitle')}</strong>{t('swap.painBody')}</div></div>
            {active.map((i) => <Button key={i.id} variant="secondary" size="lg" onClick={() => nav(`/injuries/${i.id}/edit`)}>{t('swap.updateInjury', { area: t(`body.${i.region}`) })}</Button>)}
            <Button size="lg" icon={Bandage} onClick={() => nav('/injuries/new')}>{t('swap.addInjury')}</Button>
            <Button variant="ghost" onClick={() => onSwapped(painFor)}>{t('swap.notNow')}</Button>
          </div>
        ) : !reason ? (
          <>
            <span className="text-[13.5px] text-neutral-800">{t('swap.why')}</span>
            <div role="radiogroup" aria-label={t('swap.why')} className="flex flex-col gap-2">
              {REASONS.map((r) => (
                <button key={r} type="button" role="radio" aria-checked={false} onClick={() => setReason(r)}
                  className="flex min-h-[60px] flex-col justify-center rounded-lg bg-surface px-4 py-2.5 text-start hover:bg-neutral-300">
                  <strong className="text-[15px]">{t(`swap.reason.${r}`)}</strong><span className="text-[12.5px] text-neutral-700">{t(`swap.reasonHint.${r}`)}</span>
                </button>
              ))}
            </div>
          </>
        ) : (
          <Alternatives w={w} e={e} reason={reason} pick={pick} setPick={setPick} target={target} />
        )}
        {reason && !painFor && (
          <>
            <span className="text-[13.5px] font-semibold">{t('swap.scope')}</span>
            <Segmented className="min-h-tap" label={t('swap.scope')} value={scope} onChange={setScope}
              options={[{ id: 'today', label: t('swap.today') }, { id: 'always', label: t('swap.always') }]} />
            <span className="text-xs text-neutral-700">{t(scope === 'today' ? 'swap.todayHint' : 'swap.alwaysHint')}</span>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={() => { setReason(undefined); setPick(undefined); }}>{t('swap.back')}</Button>
              <Button size="lg" icon={Repeat} className="flex-1" disabled={!pick || busy} onClick={confirm}>{pick ? t('swap.confirm', { name: l(pick.name) }) : t('swap.button')}</Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function Alternatives({ w, e, reason, pick, setPick, target }: {
  w: Workout; e: SessionExercise; reason: SwapReason; pick?: ExerciseAlternative; setPick: (a: ExerciseAlternative) => void; target: ReturnType<typeof useTargetText>;
}) {
  const { t, l } = useI18n();
  const q = useQuery(() => api.getAlternatives(w.id, e.exerciseId, reason), [reason]);
  return (
    <>
      <span className="text-[13.5px] text-neutral-800">{t('swap.pick')}</span>
      <QueryView query={q} isEmpty={(d) => d.length === 0} empty={<p className="m-0 text-sm">{t('swap.none')}</p>}>
        {(alts) => (
          <div role="radiogroup" aria-label={t('swap.pick')} className="flex flex-col gap-2">
            {alts.map((a) => {
              const on = a.exerciseId === pick?.exerciseId;
              return (
                <div key={a.exerciseId} className={cn('flex items-center gap-2 rounded-lg pe-1 ps-3', on ? 'bg-accent-100 ring-2 ring-inset ring-accent-700' : 'bg-surface')}>
                  <button type="button" role="radio" aria-checked={on} onClick={() => setPick(a)} className="flex min-h-[68px] min-w-0 flex-1 items-center gap-3 py-2 text-start">
                    <ExerciseThumb ex={a} size={48} />
                    <span className="flex min-w-0 flex-col leading-tight">
                      <strong className="text-[14.5px]">{l(a.name)}</strong>
                      <span className="text-[12.5px] text-neutral-800">{target(a.target)} · {t(`workouts.reason.${a.target.reason}`, { kg: '' })}</span>
                      <span className="text-xs text-neutral-700">{l(a.muscleNames)}</span>
                    </span>
                  </button>
                  <InfoLink id={a.exerciseId} name={l(a.name)} />
                </div>
              );
            })}
          </div>
        )}
      </QueryView>
    </>
  );
}

