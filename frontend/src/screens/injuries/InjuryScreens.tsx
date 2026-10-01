import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ChevronRight, Plus, Ban, Stethoscope, Check, OctagonAlert, Pause, Footprints, Bell, CircleAlert, TriangleAlert, CircleCheck } from 'lucide-react';
import { AppShell, BodyMap, Button, Card, Field, Icon, LineChart, PageControls, QueryView, StatusBadge, cn, type RegionState } from '@/components';
import { useI18n } from '@/i18n';
import { api } from '@/data/api';
import { useQuery } from '@/data/useQuery';
import { InjuryDetailsForm } from '@/screens/onboarding/Onboarding';
import { REGION_LIST, sideOf } from '@/constants';
import type { BodyRegion, Injury, InjuryInput, InjuryStatus, Status } from '@/types';

export const injuryStatus: Record<InjuryStatus, Status> = { active: 'warning', recovering: 'attention', resolved: 'onTrack' };
const regionState: Record<InjuryStatus, RegionState> = { active: 'warn', recovering: 'attn', resolved: 'ok' };

export function Injuries() {
  const { t } = useI18n();
  const q = useQuery(() => api.getInjuries());
  return (
    <AppShell back title={t('nav.injuries')}>
      <QueryView query={q}>
        {(list) => {
          const marks = Object.fromEntries(list.map((i) => [i.region, regionState[i.status]])) as Partial<Record<BodyRegion, RegionState>>;
          return (
            <div className="grid gap-4 lg:grid-cols-[300px_minmax(0,1fr)]">
              <div className="flex justify-center gap-2.5 rounded-card bg-surface p-4 lg:self-start">
                <BodyMap view="front" marks={marks} width={110} /><BodyMap view="back" marks={marks} width={110} />
              </div>
              <div className="flex flex-col gap-3">
                {list.map((i) => (
                  <Link key={i.id} to={`/injuries/${i.id}`} className="flex min-h-[76px] items-center gap-3.5 rounded-card bg-surface py-3 pe-4 ps-3 text-ink no-underline hover:bg-neutral-300 hover:text-ink">
                    <span className={cn('grid h-12 w-12 shrink-0 place-items-center rounded-full text-bg', { active: 'bg-warn-600', recovering: 'bg-attn-600', resolved: 'bg-sage-600' }[i.status])}>
                      <Icon as={{ active: TriangleAlert, recovering: CircleAlert, resolved: Check }[i.status]} />
                    </span>
                    <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                      <div className="flex flex-wrap items-center gap-2"><strong className="whitespace-nowrap">{t(`body.${i.region}`)}</strong><StatusBadge status={injuryStatus[i.status]} label={t(`enums.injuryStatus.${i.status}`)} /></div>
                      <span className="text-[12.5px] text-neutral-800">{i.status === 'resolved' ? t('injuries.noRestrictions') : t('injuries.meta', { pain: i.painLog.at(-1)?.pain ?? 0, n: i.avoided.length })}</span>
                    </div>
                    <Icon as={ChevronRight} flip />
                  </Link>
                ))}
                <Link to="/injuries/new" className="inline-flex h-12 items-center justify-center gap-2 rounded-pill border border-divider font-heading text-ink no-underline hover:bg-neutral-200 hover:text-ink"><Icon as={Plus} size={18} />{t('injuries.add')}</Link>
              </div>
            </div>
          );
        }}
      </QueryView>
    </AppShell>
  );
}

export function InjuryDetail() {
  const { id = '' } = useParams();
  const { t, l, date } = useI18n();
  const nav = useNavigate();
  const q = useQuery(() => api.getInjury(id), [id]);
  return (
    <AppShell back title={q.data ? t(`body.${q.data.region}`) : t('nav.injuries')} sub={q.data ? t('injuries.detailSub', { type: t(`enums.injuryType.${q.data.type}`), date: date(q.data.since) }) : undefined}>
      <QueryView query={q}>
        {(i) => (
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="flex flex-col gap-4">
              <div className="flex flex-wrap gap-2">
                <StatusBadge status={injuryStatus[i.status]} label={t(`enums.injuryStatus.${i.status}`)} />
                <span className="rounded-pill bg-neutral-100 px-3 py-1 text-xs">{t('injuries.severityNow', { n: i.severity })}</span>
                {i.restrictions.map((r) => <span key={r} className="rounded-pill bg-neutral-100 px-3 py-1 text-xs">{t(`enums.restriction.${r}`)}</span>)}
              </div>
              {i.painLog.length > 1 && (
                <Card>
                  <div className="flex items-baseline justify-between"><h2 className="m-0 text-lg">{t('injuries.painTrend')}</h2><span className="text-[13px] font-bold text-sage-800">{i.painLog[0].pain} → {i.painLog.at(-1)!.pain}</span></div>
                  <LineChart ariaLabel={t('injuries.painTrend')} series={[{ values: i.painLog.map((p) => p.pain), tone: 'warn', dots: true, label: t('injuries.painScale') }]}
                    labels={[i.painLog[0], i.painLog[Math.floor(i.painLog.length / 2)], i.painLog.at(-1)!].map((p) => date(p.date))} min={0} max={10} height={150} axisWidth={24}
                    threshold={{ value: 6, label: t('injuries.seeProfessional') }} />
                </Card>
              )}
            </div>
            <div className="flex flex-col gap-4">
              {i.avoided.length > 0 && (
                <section className="flex flex-col gap-2"><h2 className="m-0 text-lg">{t('injuries.avoided')}</h2>
                  {i.avoided.map((a) => (
                    <div key={a.from.en} className="flex min-h-[52px] items-center gap-3 rounded-pill bg-warn-100 px-4 text-warn-800">
                      <Icon as={Ban} size={18} /><span className="flex-1 text-sm font-semibold">{l(a.from)}</span><span className="text-xs">→ {l(a.to)}</span>
                    </div>
                  ))}
                </section>
              )}
              <div className="flex items-start gap-3 rounded-lg bg-surface px-4 py-4 text-[13.5px]"><Icon as={Stethoscope} className="text-warn-600" /><span>{t('injuries.stopRule')}</span></div>
              <div className="flex gap-2.5">
                <Button variant="secondary" className="flex-1" onClick={() => nav(`/injuries/${i.id}/edit`)}>{t('common.edit')}</Button>
                {i.status !== 'resolved' && <Button variant="secondary" icon={Check} className="flex-1" onClick={async () => { q.setData(await api.saveInjury({ ...i, status: 'resolved' })); }}>{t('injuries.markResolved')}</Button>}
              </div>
            </div>
          </div>
        )}
      </QueryView>
    </AppShell>
  );
}

/** Add (/injuries/new) or edit (/injuries/:id/edit). */
export function InjuryEdit() {
  const { id } = useParams();
  const { t } = useI18n();
  const nav = useNavigate();
  const q = useQuery(() => (id ? api.getInjury(id) : Promise.resolve(null)), [id]);
  const [draft, setDraft] = useState<(InjuryInput & { status: InjuryStatus }) | null>(null);
  return (
    <AppShell back hideTabs title={id ? t('injuries.editTitle') : t('injuries.add')}>
      <QueryView query={q}>
        {(existing: Injury | null) => {
          const v = draft ?? (existing ?? { region: 'shoulderL' as BodyRegion, side: 'left' as const, type: 'unsure' as const, severity: 2 as const, painfulMovements: [], restrictions: [], status: 'active' as InjuryStatus });
          const set = (patch: Partial<typeof v>) => setDraft({ ...v, ...patch });
          return (
            <div className="mx-auto flex w-full max-w-xl flex-col gap-4">
              {!existing && (
                <Field label={t('injuries.area')}>
                  <select className="h-[52px] rounded-pill border border-divider bg-surface px-4" value={v.region} onChange={(e) => { const r = e.target.value as BodyRegion; set({ region: r, side: sideOf(r) }); }}>
                    {REGION_LIST.map((r) => <option key={r} value={r}>{t(`body.${r}`)}</option>)}
                  </select>
                </Field>
              )}
              <Field label={t('injuries.status')}>
                <div role="radiogroup" className="grid grid-cols-3 gap-2">
                  {(['active', 'recovering', 'resolved'] as InjuryStatus[]).map((s) => (
                    <button key={s} type="button" role="radio" aria-checked={v.status === s} onClick={() => set({ status: s })}
                      className={cn('flex min-h-14 flex-col items-center justify-center gap-0.5 rounded-lg text-[13.5px]', v.status === s ? 'bg-accent-100 font-bold text-accent-800 ring-2 ring-inset ring-accent-700' : 'bg-surface font-semibold')}>
                      <Icon as={{ active: TriangleAlert, recovering: CircleAlert, resolved: CircleCheck }[s]} size={17} />{t(`enums.injuryStatus.${s}`)}
                    </button>
                  ))}
                </div>
              </Field>
              <InjuryDetailsForm value={v} onChange={(x) => set(x)} />
              <p className="m-0 text-[12.5px] text-neutral-700">{t('injuries.saveNote')}</p>
              <div className="flex gap-2.5">
                {existing && <Button variant="danger" onClick={async () => { await api.deleteInjury(existing.id); nav('/injuries', { replace: true }); }}>{t('common.delete')}</Button>}
                <Button className="flex-1" size="lg" onClick={async () => { const saved = await api.saveInjury({ ...v, id: existing?.id }); nav(`/injuries/${saved.id}`, { replace: true }); }}>{t('common.save')}</Button>
              </div>
            </div>
          );
        }}
      </QueryView>
    </AppShell>
  );
}

/** Shown after sharp pain, swelling, numbness, pain ≥ 6 or pain that keeps getting worse. */
export function InjuryWarning() {
  const { id = '' } = useParams();
  const { t } = useI18n();
  const nav = useNavigate();
  const q = useQuery(() => api.getInjury(id), [id]);
  return (
    <div role="alertdialog" aria-labelledby="warn-title" className="min-h-screen bg-warn-100 text-warn-800">
      <div className="mx-auto flex min-h-screen max-w-xl flex-col gap-5 px-6 pb-10 pt-4">
        <div className="flex justify-end"><PageControls /></div>
        <span className="grid h-[88px] w-[88px] place-items-center rounded-full bg-warn-600 text-white"><Icon as={OctagonAlert} size={40} /></span>
        <h1 id="warn-title" className="m-0 text-[32px]">{t('warning.title')}</h1>
        <p className="m-0 text-[15.5px]">{t('warning.body', { area: q.data ? t(`body.${q.data.region}`) : '' })}</p>
        <Card tone="plain" className="text-ink">
          <strong>{t('warning.whatWeDid')}</strong>
          <span className="flex gap-2.5 text-sm"><Icon as={Pause} size={18} className="text-warn-600" />{t('warning.paused')}</span>
          <span className="flex gap-2.5 text-sm"><Icon as={Footprints} size={18} className="text-sage-600" />{t('warning.kept')}</span>
          <span className="flex gap-2.5 text-sm"><Icon as={Bell} size={18} className="text-accent-600" />{t('warning.askAgain')}</span>
        </Card>
        <p className="m-0 text-[13.5px]">{t('warning.emergency')}</p>
        <div className="mt-auto flex flex-col gap-2.5">
          <button className="h-[54px] rounded-pill bg-warn-600 font-heading text-base text-white hover:opacity-90" onClick={() => nav('/', { replace: true })}>{t('warning.understand')}</button>
          <Button variant="danger" size="lg" onClick={() => nav(`/injuries/${id}/edit`)}>{t('warning.checked')}</Button>
        </div>
      </div>
    </div>
  );
}
