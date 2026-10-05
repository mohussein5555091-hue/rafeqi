import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import { Flame, Dumbbell, Utensils, Hourglass, ShoppingBasket, ChevronRight, Lock, Trophy, ChevronsLeftRight, Image, Sparkles, User as UserIcon, Target, Bandage, HeartPulse, KeyRound, LogOut, MessageSquare, Trash2, Wrench } from 'lucide-react';
import {
  AppShell, Breathing, Button, Card, Checkbox, CitationChip, Disclaimer, EmptyState, ErrorState, Icon, LineChart, LinkButton, QueryView, Segmented, StatusBadge, StepList, rollingAverage, cn, useToast,
} from '@/components';
import { useI18n } from '@/i18n';
import { useTheme } from '@/theme';
import { ApiError, api } from '@/data/api';
import { useQuery } from '@/data/useQuery';
import { useSession } from '@/data/session';
import type { WeeklyReview as Review } from '@/types';
import { WhyPlanLink } from '@/screens/plan/WhyPlan';
import { useNavigate } from 'react-router-dom';

const MEASURES = ['waist', 'hips', 'chest', 'arm', 'thigh'] as const;
type MeasureKey = (typeof MEASURES)[number];

const changeIcon: Record<Review['changes'][number]['kind'], LucideIcon> = { calories: Flame, exercise: Dumbbell, injury: Bandage, meals: Utensils };

function ReviewWriting({ onDone }: { onDone: () => void }) {
  const { t } = useI18n();
  const steps = ['read', 'compare', 'adjust', 'write'] as const;
  const [n, setN] = useState(0);
  useEffect(() => {
    if (n >= steps.length) { onDone(); return; }
    const id = setTimeout(() => setN(n + 1), 900);
    return () => clearTimeout(id);
  }, [n, onDone, steps.length]);
  return (
    <div className="mx-auto flex w-full max-w-xl flex-col gap-6 py-4">
      <div className="grid h-52 place-items-center"><Breathing size={180} mark={t('brand.mark')} /></div>
      <div><h2 className="m-0 mb-2 text-3xl">{t('review.writingTitle')}</h2><p className="m-0 text-neutral-800">{t('review.writingBody')}</p></div>
      <StepList steps={steps.map((s, i) => ({ label: t(`review.writingSteps.${s}`), state: i < n ? 'done' : i === n ? 'active' : 'todo' }))} />
    </div>
  );
}

/** Weekly review. `?writing=1` shows the 30–90 s wait state after a check-in. */
export function WeeklyReview() {
  const { id = '' } = useParams();
  const [params, setParams] = useSearchParams();
  const { t, l, num, date } = useI18n();
  const q = useQuery(() => api.getReview(id), [id]);
  const writing = params.get('writing') === '1' || q.data?.state === 'pending';
  const title = q.data ? t('review.title', { week: q.data.weekNumber }) : t('nav.reviews');

  return (
    <AppShell back title={title} sub={q.data ? `${date(q.data.start)} – ${date(q.data.end)}` : undefined} actions={q.data && !writing ? <span className="hidden lg:block"><StatusBadge status={q.data.status} /></span> : undefined}>
      {writing ? <ReviewWriting onDone={() => setParams({})} /> : (
        <QueryView query={q}>
          {(r) => r.state === 'failed' ? (
            <ErrorState icon={Hourglass} title={t('review.slowTitle')} body={t('review.slowBody')} onRetry={q.reload} />
          ) : (
            <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
              <div className="flex flex-col gap-4">
                <Card tone="sage" className="p-6 lg:flex-row lg:items-center lg:gap-5">
                  <div className="flex flex-1 flex-col gap-2.5"><span className="lg:hidden"><StatusBadge status={r.status} /></span><p className="m-0 text-base leading-relaxed">{l(r.summary)}</p></div>
                  <div className="grid grid-cols-3 gap-2 text-center lg:flex">
                    <div className="rounded-lg bg-bg px-4 py-3"><span className="block font-heading text-2xl" dir="ltr">{r.stats.weightChangeKg > 0 ? '+' : ''}{num(r.stats.weightChangeKg, 1)}</span><span className="text-xs">{t('review.kgWeek')}</span></div>
                    <div className={cn('rounded-lg px-4 py-3', r.stats.sessionsDone < r.stats.sessionsPlanned ? 'bg-accent-100' : 'bg-bg')}><span className="block font-heading text-2xl">{r.stats.sessionsDone}/{r.stats.sessionsPlanned}</span><span className="text-xs">{t('review.sessions')}</span></div>
                    {r.stats.pain !== undefined && <div className="rounded-lg bg-bg px-4 py-3"><span className="block font-heading text-2xl">{r.stats.pain}/10</span><span className="text-xs">{t('review.pain')}</span></div>}
                  </div>
                </Card>
                {r.changes.length > 0 && <h2 className="m-0 mt-1 text-xl">{t('review.changed')}</h2>}
                <div className="grid gap-3 lg:grid-cols-2">
                  {r.changes.map((c, i) => (
                    <Card key={i} className="gap-2">
                      <div className="flex items-center gap-2.5"><span className="grid h-9 w-9 place-items-center rounded-full bg-bg"><Icon as={changeIcon[c.kind]} size={18} /></span><span className="text-xs font-bold uppercase tracking-[.06em] text-accent-700 rtl:normal-case">{t(`review.kind.${c.kind}`)}</span></div>
                      <strong className="text-[15.5px] leading-snug">{l(c.what)}</strong>
                      <span className="text-[13.5px] text-neutral-800">{l(c.why)}</span>
                      <div className="mt-auto"><CitationChip source={l(c.citation)} /></div>
                    </Card>
                  ))}
                </div>
              </div>
              <div className="flex flex-col gap-4">
                {r.focus.length > 0 && (
                  <Card tone="accent"><h2 className="m-0 text-xl">{t('review.focus')}</h2>
                    <ol className="m-0 flex list-none flex-col gap-2.5 p-0">{r.focus.map((f, i) => (
                      <li key={i} className="flex gap-3 text-[14.5px]"><span className="grid h-[26px] w-[26px] shrink-0 place-items-center rounded-full bg-accent text-[13px] font-bold text-on-accent">{i + 1}</span>{l(f)}</li>
                    ))}</ol>
                  </Card>
                )}
                {r.groceryUpdate && (
                  <Link to="/groceries" className="flex min-h-[60px] items-center gap-3 rounded-pill bg-surface py-2 pe-4 ps-2 text-ink no-underline hover:bg-neutral-300 hover:text-ink">
                    <span className="grid h-tap w-tap place-items-center rounded-full bg-sage-600 text-bg"><Icon as={ShoppingBasket} /></span>
                    <span className="flex-1 leading-tight"><strong className="block">{t('review.grocery')}</strong><span className="text-[12.5px] text-neutral-700">{l(r.groceryUpdate.note)}</span></span>
                    <Icon as={ChevronRight} flip />
                  </Link>
                )}
                <LinkButton to="/reviews" variant="secondary">{t('review.past')}</LinkButton>
                <p className="m-0 text-xs text-neutral-700">{t('review.citeNote')}</p>
                <Disclaimer />
              </div>
            </div>
          )}
        </QueryView>
      )}
    </AppShell>
  );
}

export function ReviewHistory() {
  const { t, l, date } = useI18n();
  const q = useQuery(() => api.getReviews());
  return (
    <AppShell back title={t('nav.reviews')}>
      <QueryView query={q} isEmpty={(d) => d.length === 0} empty={<EmptyState title={t('review.emptyTitle')} body={t('review.emptyBody')} />}>
        {(list) => (
          <ol className="m-0 flex max-w-3xl list-none flex-col gap-2.5 p-0">
            {list.map((r) => (
              <li key={r.id}>
                <Link to={`/reviews/${r.id}`} className="flex items-start gap-3.5 rounded-lg bg-surface p-4 text-ink no-underline hover:bg-neutral-300 hover:text-ink">
                  <div className="flex w-[52px] shrink-0 flex-col items-center rounded-md bg-bg py-1.5 leading-tight"><span className="text-[10.5px]">{t('review.week')}</span><strong className="font-heading text-[22px] font-normal">{r.weekNumber}</strong></div>
                  <div className="flex flex-1 flex-col gap-1"><div className="flex items-center justify-between gap-2"><span className="text-xs text-neutral-700">{date(r.start)} – {date(r.end)}</span><StatusBadge status={r.status} /></div><span className="text-[13.5px]">{l(r.shortSummary)}</span></div>
                </Link>
              </li>
            ))}
          </ol>
        )}
      </QueryView>
    </AppShell>
  );
}

/** Weight (entries + 7-day average), measurements, strength per lift, records, photo compare. */
export function Progress() {
  const { t, l, num, date } = useI18n();
  const q = useQuery(() => api.getProgress());
  const [lift, setLift] = useState(0);
  const [view, setView] = useState<'front' | 'side' | 'back'>('front');
  return (
    <AppShell title={t('nav.progress')} sub={q.data ? t('progress.since', { date: date(q.data.since, { day: 'numeric', month: 'long' }) }) : undefined}>
      <QueryView query={q}>
        {(p) => {
          const w = p.weights.map((x) => x.kg);
          const pick = (arr: { date: string }[], n = 4) => arr.filter((_, i) => i % Math.ceil(arr.length / n) === 0 || i === arr.length - 1).map((x) => date(x.date));
          // Each measurement compares the first week it was taken with the latest one.
          const firstOf = (k: MeasureKey) => p.measurements.find((m) => m[k] !== undefined)?.[k];
          const lastOf = (k: MeasureKey) => [...p.measurements].reverse().find((m) => m[k] !== undefined)?.[k];
          const waist = p.measurements.filter((m) => m.waist !== undefined);
          const L = p.lifts[Math.min(lift, p.lifts.length - 1)];
          const noData = <p className="m-0 text-sm text-neutral-800">{t('progress.noData')}</p>;
          const photos = p.photos.filter((x) => x.view === view);
          return (
            <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
              <Card>
                <div className="flex items-baseline justify-between"><h2 className="m-0 text-xl">{t('progress.weight')}</h2>{w.length > 0 && <span className="text-[13px] font-bold text-sage-800">{num(w[0], 1)} → {num(w.at(-1)!, 1)} {t('units.kg')}</span>}</div>
                {w.length < 2 ? noData : <LineChart ariaLabel={t('progress.weight')} labels={pick(p.weights)} height={180} axisWidth={34}
                  series={[{ values: w, tone: 'muted', dots: true, line: false, label: t('progress.weighIns') }, { values: rollingAverage(w), tone: 'ok', area: true, label: t('progress.avg7') }]} />}
              </Card>
              <Card>
                <h2 className="m-0 text-xl">{t('progress.measurements')}</h2>
                {waist.length >= 2 && <LineChart ariaLabel={t('progress.measurements')} labels={pick(waist)} height={110} axisWidth={30} series={[{ values: waist.map((m) => m.waist!), tone: 'ok', dots: true, label: t('progress.waistCm') }]} />}
                {p.measurements.length === 0 ? noData : (
                  <table className="w-full text-sm">
                    <tbody>{MEASURES.filter((k) => firstOf(k) !== undefined).map((k) => {
                      const a = firstOf(k)!, b = lastOf(k)!, d = b - a;
                      return <tr key={k} className="h-tap border-b border-divider"><td>{t(`checkIn.body.m.${k}`)}</td><td className="text-neutral-700">{num(a, 1)} → {num(b, 1)}</td><td className={cn('text-end font-bold', d < 0 ? 'text-sage-800' : 'text-neutral-700')} dir="ltr">{d > 0 ? '+' : ''}{num(d, 1)}</td></tr>;
                    })}</tbody>
                  </table>
                )}
              </Card>
              <Card>
                <h2 className="m-0 text-xl">{t('progress.strength')}</h2>
                {L ? <>
                  <Segmented className="min-h-tap" label={t('progress.strength')} value={lift} onChange={setLift} options={p.lifts.map((x, i) => ({ id: i, label: l(x.name) }))} />
                  {L.points.length < 2 ? noData : <LineChart ariaLabel={l(L.name)} labels={pick(L.points, 3)} height={130} axisWidth={34} series={[{ values: L.points.map((x) => x.kg), tone: 'accent', dots: true, label: t('progress.topSet', { unit: l(L.unit) }) }]} />}
                </> : <p className="m-0 text-sm text-neutral-800">{t('progress.noLifts')}</p>}
              </Card>
              <div className="grid gap-4 lg:grid-cols-2">
                <section className="flex flex-col gap-2"><h2 className="m-0 text-xl">{t('progress.records')}</h2>
                  {p.records.length === 0 && <p className="m-0 text-sm text-neutral-800">{t('progress.noLifts')}</p>}
                  {p.records.map((r) => (
                    <div key={r.exerciseId} className="flex min-h-[60px] items-center gap-3 rounded-pill bg-surface py-2 pe-4 ps-2">
                      <span className="grid h-tap w-tap shrink-0 place-items-center rounded-full bg-accent-200 text-accent-800"><Icon as={Trophy} size={19} /></span>
                      <div className="flex-1 leading-tight"><strong className="block text-[14.5px]">{l(r.name)}</strong><span className="text-xs text-neutral-700">{date(r.date)}</span></div>
                      <strong className="whitespace-nowrap">{l(r.value)}</strong>
                    </div>
                  ))}
                </section>
                <Card>
                  <div className="flex items-center justify-between"><h2 className="m-0 text-xl">{t('progress.photos')}</h2><span className="flex items-center gap-1 text-xs text-neutral-700"><Icon as={Lock} size={13} />{t('progress.private')}</span></div>
                  {photos.length >= 2 ? (
                    <div dir="ltr" className="relative grid h-64 grid-cols-2 overflow-hidden rounded-lg">
                      {[photos[0], photos.at(-1)!].map((ph, i) => (
                        <div key={i} className={cn('washed flex flex-col items-center justify-center gap-1.5 text-[12.5px]', i ? 'bg-sage-300' : 'bg-neutral-300')}>
                          {ph.url ? <img src={ph.url} alt="" className="h-full w-full object-cover" /> : <><Icon as={Image} size={22} />{date(ph.date)}</>}
                        </div>
                      ))}
                      <span className="absolute inset-y-0 left-1/2 w-[3px] -translate-x-1/2 bg-bg" />
                      <span className="absolute left-1/2 top-1/2 grid h-tap w-tap -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full bg-bg shadow-md" aria-label={t('progress.drag')}><Icon as={ChevronsLeftRight} /></span>
                    </div>
                  ) : <p className="m-0 text-sm text-neutral-800">{t('progress.noPhotos')}</p>}
                  <Segmented className="min-h-tap" label={t('progress.photos')} value={view} onChange={setView} options={(['front', 'side', 'back'] as const).map((v) => ({ id: v, label: t(`checkIn.body.view.${v}`) }))} />
                </Card>
              </div>
            </div>
          );
        }}
      </QueryView>
    </AppShell>
  );
}

/** Edit answers & regenerate, language, theme, password, delete data, log out. */
export function Profile() {
  const { t, l, lang, setLang } = useI18n();
  const { theme, setTheme } = useTheme();
  const { logout } = useSession();
  const nav = useNavigate();
  const q = useQuery(() => Promise.all([api.getUser(), api.getInjuries(), api.getEquipment()]));
  const [confirmDelete, setConfirmDelete] = useState(false);
  return (
    <AppShell back hideTabs title={t('nav.profile')}>
      <QueryView query={q}>
        {([u, injuries, equipment]) => (
          <div className="grid max-w-5xl gap-5 lg:grid-cols-2">
            <div className="flex flex-col gap-4">
              <Card className="flex-row items-center gap-3.5">
                <span className="grid h-[60px] w-[60px] place-items-center rounded-full bg-sage-200 font-heading text-2xl text-sage-800">{l(u.firstName).charAt(0)}</span>
                <div className="leading-snug"><strong className="block text-[17px]">{l(u.firstName)} {l(u.lastName)}</strong><span className="text-[13px] text-neutral-700" dir="ltr">{u.email}</span></div>
              </Card>
              <section className="flex flex-col gap-1.5">
                <h2 className="m-0 px-1.5 text-xs font-bold uppercase tracking-[.08em] rtl:normal-case">{t('profile.plan')}</h2>
                <ul className="m-0 flex list-none flex-col overflow-hidden rounded-lg bg-surface p-0">
                  {([
                    ['about', UserIcon, t('profile.aboutValue', { age: u.age, h: u.heightCm })], ['goal', Target, `${t(`enums.goal.${u.goal}`)} · ${t(`enums.pace.${u.pace}`)}`],
                    ['training', Dumbbell, `${t('common.daysPerWeek', { n: u.daysPerWeek })} · ${t(`enums.location.${u.location}`)}`], ['injuries', Bandage, t('profile.injuriesValue', { n: injuries.filter((i) => i.status !== 'resolved').length })],
                    ['health', HeartPulse, t('onboarding.review.healthClear')], ['food', Utensils, t('profile.foodValue', { n: u.food.mealsPerDay })],
                  ] as const).map(([step, ic, v]) => (
                    <li key={step}><Link to={`/onboarding/${step}`} className="flex min-h-14 items-center gap-3 border-b border-divider px-4 text-ink no-underline hover:bg-neutral-300 hover:text-ink">
                      <Icon as={ic} size={19} /><span className="flex-1 text-[14.5px]">{t(`onboarding.${step}.title`)}</span><span className="text-[12.5px] text-neutral-700">{v}</span><Icon as={ChevronRight} size={18} flip />
                    </Link></li>
                  ))}
                  <li><Link to="/profile/equipment" className="flex min-h-14 items-center gap-3 border-b border-divider px-4 text-ink no-underline hover:bg-neutral-300 hover:text-ink">
                    <Icon as={Wrench} size={19} /><span className="flex-1 text-[14.5px]">{t('profile.equipment')}</span>
                    <span className="text-[12.5px] text-neutral-700">{equipment.items.some((i) => !i.available) ? t('profile.equipmentMissing', { n: equipment.items.filter((i) => !i.available).length }) : t('profile.equipmentAll')}</span><Icon as={ChevronRight} size={18} flip />
                  </Link></li>
                </ul>
                <WhyPlanLink className="mt-1.5" />
                <Button size="lg" icon={Sparkles} className="mt-1.5" onClick={() => nav('/onboarding/generating')}>{t('profile.regenerate')}</Button>
                <span className="px-1.5 text-xs text-neutral-700">{t('profile.regenerateNote')}</span>
              </section>
            </div>
            <div className="flex flex-col gap-4">
              <section className="flex flex-col gap-2.5">
                <h2 className="m-0 px-1.5 text-xs font-bold uppercase tracking-[.08em] rtl:normal-case">{t('profile.preferences')}</h2>
                {([
                  [t('profile.language'), <Segmented key="l" className="min-h-tap" label={t('profile.language')} value={lang} onChange={setLang} options={[{ id: 'en', label: 'English' }, { id: 'ar', label: 'العربية' }]} />],
                  [t('profile.theme'), <Segmented key="t" className="min-h-tap" label={t('profile.theme')} value={theme} onChange={setTheme} options={(['light', 'dark', 'system'] as const).map((x) => ({ id: x, label: t(`profile.themes.${x}`) }))} />],
                ] as const).map(([label, control]) => (
                  <div key={label} className="flex items-center justify-between gap-2.5 rounded-pill bg-surface py-2 pe-2 ps-4"><span className="text-[14.5px]">{label}</span>{control}</div>
                ))}
              </section>
              <section className="flex flex-col gap-1.5">
                <h2 className="m-0 px-1.5 text-xs font-bold uppercase tracking-[.08em] rtl:normal-case">{t('profile.account')}</h2>
                <ul className="m-0 flex list-none flex-col overflow-hidden rounded-lg bg-surface p-0">
                  <li><Link to="/profile/password" className="flex min-h-14 items-center gap-3 border-b border-divider px-4 text-ink no-underline hover:bg-neutral-300 hover:text-ink"><Icon as={KeyRound} size={19} /><span className="flex-1">{t('profile.changePassword')}</span><Icon as={ChevronRight} size={18} flip /></Link></li>
                  <li><Link to="/profile/feedback" className="flex min-h-14 items-center gap-3 border-b border-divider px-4 text-ink no-underline hover:bg-neutral-300 hover:text-ink"><Icon as={MessageSquare} size={19} /><span className="flex-1">{t('profile.feedback')}</span><Icon as={ChevronRight} size={18} flip /></Link></li>
                  <li><button type="button" onClick={async () => { await logout(); nav('/login', { replace: true }); }} className="flex min-h-14 w-full items-center gap-3 px-4 text-start hover:bg-neutral-300"><Icon as={LogOut} size={19} flip /><span>{t('profile.logout')}</span></button></li>
                </ul>
                <Button variant="danger" size="lg" icon={Trash2} className="mt-1.5" onClick={() => setConfirmDelete(true)}>{t('profile.delete')}</Button>
                <span className="px-1.5 text-xs text-neutral-700">{t('profile.deleteNote')}</span>
              </section>
              <Disclaimer />
            </div>
            {confirmDelete && (
              <div className="fixed inset-0 z-50 grid place-items-center bg-neutral-900/50 p-4" role="dialog" aria-modal="true" aria-labelledby="del-title">
                <div className="flex w-full max-w-md flex-col gap-3 rounded-card bg-surface p-6 shadow-lg">
                  <h2 id="del-title" className="m-0 text-xl">{t('profile.deleteConfirmTitle')}</h2>
                  <p className="m-0 text-sm text-neutral-800">{t('profile.deleteConfirmBody')}</p>
                  <div className="mt-2 flex justify-end gap-2">
                    <Button variant="secondary" onClick={() => setConfirmDelete(false)}>{t('common.cancel')}</Button>
                    <Button variant="danger" onClick={async () => { await api.deleteMyData(); await logout(); nav('/login', { replace: true }); }}>{t('profile.deleteConfirm')}</Button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </QueryView>
    </AppShell>
  );
}

/** What the training place has: untick what's missing, and the plan is rebuilt around it. */
export function ProfileEquipment() {
  const { t, l } = useI18n();
  const nav = useNavigate();
  const toast = useToast();
  const q = useQuery(() => api.getEquipment());
  const [missing, setMissing] = useState<string[]>();
  const [saving, setSaving] = useState(false);
  return (
    <AppShell back hideTabs title={t('profile.equipment')}>
      <QueryView query={q}>
        {(eq) => {
          const gone = missing ?? eq.items.filter((i) => !i.available).map((i) => i.id);
          return (
            <div className="flex max-w-md flex-col gap-4">
              <p className="m-0 text-[14.5px] text-neutral-800">{t('profile.equipmentIntro')}</p>
              <span className="text-[13px] text-neutral-700">{t('profile.equipmentWhere', { place: t(`enums.location.${eq.location}`) })}</span>
              <ul className="m-0 flex list-none flex-col overflow-hidden rounded-lg bg-surface p-0" data-testid="equipment-list">
                {eq.items.map((i) => (
                  <li key={i.id} className="flex min-h-14 items-center gap-2 border-b border-divider pe-4 ps-1">
                    <Checkbox checked={!gone.includes(i.id)} label={l(i.name)} onChange={(have) => setMissing(have ? gone.filter((x) => x !== i.id) : [...gone, i.id])} />
                    <span className="flex-1 text-[14.5px]">{l(i.name)}</span>
                  </li>
                ))}
              </ul>
              <Button size="lg" disabled={saving || missing === undefined} onClick={async () => {
                setSaving(true);
                try { await api.saveEquipment(gone); toast({ message: t('profile.equipmentSaved'), tone: 'success' }); nav('/profile'); }
                catch { toast({ message: t('common.saveFailed'), tone: 'error' }); }
                finally { setSaving(false); }
              }}>{t('common.save')}</Button>
            </div>
          );
        }}
      </QueryView>
    </AppShell>
  );
}

const FEEDBACK_MAX = 1000;

/** "Send feedback": a few lines to the people running the app (saved in the database; never sent to the AI). */
export function SendFeedback() {
  const { t, num } = useI18n();
  const nav = useNavigate();
  const toast = useToast();
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  return (
    <AppShell back hideTabs title={t('profile.feedback')}>
      <form className="flex max-w-md flex-col gap-4" onSubmit={async (e) => {
        e.preventDefault();
        if (!text.trim()) return;
        setBusy(true);
        try { await api.sendFeedback(text.trim(), document.referrer ? new URL(document.referrer).pathname : '/profile'); toast({ message: t('profile.feedbackSent'), tone: 'success' }); nav('/profile'); }
        catch { toast({ message: t('common.saveFailed'), tone: 'error' }); }
        finally { setBusy(false); }
      }}>
        <p className="m-0 text-[14.5px] text-neutral-800">{t('profile.feedbackIntro')}</p>
        <label htmlFor="fb" className="flex flex-col gap-1.5 text-[13px]">{t('profile.feedbackLabel')}
          <textarea id="fb" maxLength={FEEDBACK_MAX} value={text} onChange={(e) => setText(e.target.value.slice(0, FEEDBACK_MAX))}
            className="min-h-[168px] resize-none rounded-lg border border-divider bg-surface px-4 py-4 text-[15.5px] focus-visible:border-accent-700" />
        </label>
        <span className="text-end text-xs text-neutral-700" aria-live="polite">{t('checkIn.note.count', { n: num(text.length), max: num(FEEDBACK_MAX) })}</span>
        <Button type="submit" size="lg" disabled={busy || !text.trim()}>{t('profile.feedbackSend')}</Button>
      </form>
    </AppShell>
  );
}

export function ChangePassword() {
  const { t } = useI18n();
  const nav = useNavigate();
  const [cur, setCur] = useState(''); const [next, setNext] = useState('');
  const [err, setErr] = useState<string>();
  return (
    <AppShell back hideTabs title={t('profile.changePassword')}>
      <form className="flex max-w-md flex-col gap-4" onSubmit={async (e) => {
        e.preventDefault();
        if (next.length < 8 || !/\d/.test(next)) return setErr(t('auth.errors.passwordRules'));
        try { await api.changePassword(cur, next); nav('/profile'); }
        catch (e) { setErr(t(e instanceof ApiError && e.message === 'wrong_current_password' ? 'profile.wrongPassword' : 'common.saveFailed')); }
      }}>
        <label className="flex flex-col gap-1.5 text-[13px]">{t('profile.currentPassword')}<input type="password" className="h-[52px] rounded-pill border border-divider bg-surface px-4 text-base" value={cur} onChange={(e) => setCur(e.target.value)} /></label>
        <label className="flex flex-col gap-1.5 text-[13px]">{t('profile.newPassword')}<input type="password" className="h-[52px] rounded-pill border border-divider bg-surface px-4 text-base" value={next} onChange={(e) => setNext(e.target.value)} aria-invalid={!!err} /></label>
        {err && <span role="alert" className="text-[13px] text-warn-700">{err}</span>}
        <Button type="submit" size="lg">{t('common.save')}</Button>
      </form>
    </AppShell>
  );
}
