import { BookOpen, Calculator, ChevronRight, CircleHelp, ClipboardList, ShieldCheck, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import { AppShell, Badge, Card, Icon, Kicker, ProgressBar, QueryView, cn } from '@/components';
import { useI18n } from '@/i18n';
import { api } from '@/data/api';
import { useQuery } from '@/data/useQuery';
import type { LocalizedText, WhyAnswer, WhyDecision } from '@/types';

type Injury = { region: string; status: string; severity: number; painful_movements?: string[]; restrictions?: string[] };
const ENUM_KEYS: Record<string, string> = { sex: 'sex', goal: 'goal', pace: 'pace', experience: 'experience', location: 'location', daily_activity: 'dailyActivity' };
const HEALTH: Record<string, string> = {
  heart_condition: 'heartCondition', diabetes: 'diabetes', pregnancy: 'pregnancy', recent_surgery: 'recentSurgery', exercise_medication: 'exerciseMedication',
};

/** One answer, in the words the questionnaire used. */
function useAnswerText() {
  const { t, l, num } = useI18n();
  const list = (xs: string[], label: (x: string) => string) => (xs.length ? xs.map(label).join(', ') : t('why.value.none'));
  return ({ key, value }: WhyAnswer): string => {
    if (key === 'daily_activity' && value == null) return t('why.value.notAnswered');
    if (key in ENUM_KEYS) return t(`enums.${ENUM_KEYS[key]}.${value}`);
    switch (key) {
      case 'age': return t('why.value.years', { n: value as number });
      case 'height_cm': return `${num(value as number)} ${t('units.cm')}`;
      case 'waist_cm': return value == null ? t('why.value.notGiven') : `${num(value as number)} ${t('units.cm')}`;
      case 'weight_kg': return `${num(value as number, 1)} ${t('units.kg')}`;
      case 'days_per_week': return t('common.daysPerWeek', { n: value as number });
      case 'session_minutes': case 'cooking_minutes': return t('units.minutesShort', { n: value as number });
      case 'meals_per_day': return t('why.value.perDay', { n: value as number });
      case 'dislikes': return list(value as string[], (x) => t(`enums.food.${x}`));
      case 'allergies': return list((value as string[]).filter((x) => x !== 'none'), (x) => t(`enums.allergy.${x}`));
      case 'fasting': return list(value as string[], (x) => t(`enums.fasting.${x}`));
      case 'health': return (value as string[]).length ? (value as string[]).map((h) => t(`onboarding.health.q.${HEALTH[h] ?? h}`)).join(', ') : t('onboarding.review.healthClear');
      case 'injuries': return list((value as Injury[]).map((i) => [
        t(`body.${i.region}`), t(`enums.injuryStatus.${i.status}`), `${i.severity}/5`,
        ...(i.painful_movements ?? []).map((m) => t(`enums.movement.${m}`)), ...(i.restrictions ?? []).map((r) => t(`enums.restriction.${r}`)),
      ].join(' · ')), (x) => x);
      case 'missing_equipment': return list((value as LocalizedText[]).map((x) => l(x)), (x) => x);
      case 'checkin': case 'swaps': return t(`why.value.${key}`);
      default: return String(value);
    }
  };
}

function Answers({ d }: { d: WhyDecision }) {
  const { t } = useI18n();
  const answerText = useAnswerText();
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-xs font-bold text-neutral-800">{t('why.answers')}</span>
      {d.answers.length ? (
        <ul className="m-0 flex list-none flex-wrap gap-1.5 p-0">
          {d.answers.map((a) => (
            <li key={a.key} className="rounded-pill bg-bg px-3 py-1 text-[12.5px]"><span className="text-neutral-700">{t(`why.answer.${a.key}`)}:</span> <strong>{answerText(a)}</strong></li>
          ))}
        </ul>
      ) : <span className="text-[12.5px] text-neutral-700">{t('why.noAnswers')}</span>}
    </div>
  );
}

/** Where the rule comes from: "From your books" (book, page, quote), "Standard formula" (its original source),
 *  "Rafeqi safety rule" (conservative on purpose, not from a book) or "Not yet from a book". */
function Source({ d }: { d: WhyDecision }) {
  const { t, l } = useI18n();
  const s = d.source;
  return (
    <div className="flex flex-col gap-1.5 border-t border-divider pt-3" data-testid="source" data-kind={s.kind}>
      <span className="text-xs font-bold text-neutral-800">{t('why.source')}</span>
      {s.kind === 'placeholder' ? (
        <>
          <Badge className="bg-attn-100 text-attn-800" icon={CircleHelp}><span data-testid="placeholder-badge">{t('why.placeholder')}</span></Badge>
          <span className="text-xs text-neutral-700">{t('why.placeholderSource', { text: s.text.replace(/^PLACEHOLDER:\s*/, '') })}</span>
        </>
      ) : s.kind === 'safety' ? (
        <>
          <Badge className="bg-accent-100 text-accent-800" icon={ShieldCheck}><span data-testid="safety-badge">{t('why.safety')}</span></Badge>
          <span className="text-xs text-neutral-700" data-testid="safety-note">{t('why.safetyNote')}</span>
        </>
      ) : (
        <>
          {s.kind === 'book'
            ? <Badge className="bg-sage-100 text-sage-900" icon={BookOpen}><span data-testid="book-badge">{t('why.fromBooks')}</span></Badge>
            : <Badge className="bg-neutral-100 text-neutral-900" icon={Calculator}><span data-testid="formula-badge">{t('why.formula')}</span></Badge>}
          <span className="flex items-start gap-1.5 text-[13px]" data-testid="book">
            <Icon as={s.kind === 'book' ? BookOpen : Calculator} size={16} className="mt-0.5 text-sage-700" />
            <span>{s.kind === 'formula' && <>{t('why.originalSource')}: </>}<strong>{s.book}</strong>{s.chapter ? ` · ${s.chapter}` : ''} · {t('why.page', { page: s.page ?? '' })}</span>
          </span>
          {s.quote && <blockquote className="m-0 border-s-4 border-sage-300 ps-3 text-[13px] italic text-neutral-800">{l(s.quote)}</blockquote>}
        </>
      )}
    </div>
  );
}

function Decision({ d }: { d: WhyDecision }) {
  const { t, l } = useI18n();
  return (
    <li data-testid="decision" data-rule={d.rule} className="flex flex-col gap-3 rounded-card bg-surface p-4 lg:p-5">
      {d.context && <span className="text-[12.5px] font-semibold text-neutral-700">{l(d.context)}</span>}
      <div className="flex flex-col gap-0.5">
        <Kicker>{t('why.result')}</Kicker>
        <p className="m-0 text-[15px] font-semibold leading-snug" data-testid="result">{l(d.result)}</p>
      </div>
      <Answers d={d} />
      <div className="flex flex-col gap-0.5">
        <span className="text-xs font-bold text-neutral-800">{t('why.rule')}</span>
        <p className="m-0 text-[13.5px] text-neutral-800">{l(d.summary)}</p>
      </div>
      <Source d={d} />
    </li>
  );
}

/** Several decisions from the same rule (a starting weight per exercise…): the rule once, the decisions folded away. */
function RuleGroup({ ds }: { ds: WhyDecision[] }) {
  const { t, l, num } = useI18n();
  const d = ds[0];
  return (
    <li data-testid="rule-group" data-rule={d.ruleKey} className="flex flex-col gap-3 rounded-card bg-surface p-4 lg:p-5">
      <div className="flex flex-col gap-0.5">
        <span className="text-xs font-bold text-neutral-800">{t('why.rule')}</span>
        <p className="m-0 text-[15px] font-semibold leading-snug">{l(d.summary)}</p>
      </div>
      <details className="group rounded-lg bg-bg px-3 py-2">
        <summary className="flex min-h-tap cursor-pointer list-none items-center gap-2 text-[13.5px] font-semibold">
          <Icon as={ChevronRight} size={18} flip className="transition-transform group-open:rotate-90" />
          {t('why.fromRule', { n: num(ds.length) })}
        </summary>
        <ul className="m-0 mt-2 flex list-none flex-col gap-2.5 p-0">
          {ds.map((x, i) => (
            <li key={i} data-testid="decision" data-rule={x.rule} className="flex flex-col gap-1.5 border-t border-divider pt-2.5 first:border-0 first:pt-0">
              {x.context && <span className="text-[12.5px] font-semibold text-neutral-700">{l(x.context)}</span>}
              <p className="m-0 text-[14px] leading-snug" data-testid="result">{l(x.result)}</p>
              {JSON.stringify(x.answers) !== JSON.stringify(d.answers) && <Answers d={x} />}
            </li>
          ))}
        </ul>
      </details>
      <Answers d={d} />
      <Source d={d} />
    </li>
  );
}

/** A group's decisions, those sharing a rule folded together (in the order they first appear). */
function byRule(ds: WhyDecision[]): WhyDecision[][] {
  const out = new Map<string, WhyDecision[]>();
  for (const d of ds) out.set(d.ruleKey, [...(out.get(d.ruleKey) ?? []), d]);
  return [...out.values()];
}

export function WhyPlan() {
  const { t, l, num } = useI18n();
  const q = useQuery(() => api.getWhy());
  return (
    <AppShell back hideTabs title={t('why.title')}>
      <QueryView query={q}>
        {(why) => (
          <div className="flex max-w-3xl flex-col gap-5">
            <p className="m-0 text-[15px] text-neutral-800">{t('why.intro')}</p>
            <Card tone="sage" className="gap-2.5" data-testid="backed">
              <strong className="text-lg">{t('why.backed', { x: num(why.rules.fromBooks), y: num(why.rules.total), a: num(why.backed), b: num(why.total) })}</strong>
              <ProgressBar value={why.rules.fromBooks} max={why.rules.total || 1} label={t('why.backed', { x: num(why.rules.fromBooks), y: num(why.rules.total), a: num(why.backed), b: num(why.total) })} />
              {why.formulas > 0 && <span className="text-[13px]" data-testid="formulas-note">{t('why.formulasNote', { n: num(why.formulas) })}</span>}
              {why.safety > 0 && <span className="text-[13px]" data-testid="safety-count">{t('why.safetyCount', { n: num(why.safety) })}</span>}
              <span className="text-[13px]">{t('why.backedNote')}</span>
            </Card>
            {/* The AI summary slot: filled by the local LLM in the AI phase (never a number, only words). */}
            <section data-testid="ai-summary" aria-label={t('why.aiSlot')}
              className={cn('flex items-start gap-2.5 rounded-card p-4 text-[13.5px]', why.aiSummary ? 'bg-surface' : 'border-2 border-dashed border-divider text-neutral-700')}>
              <Icon as={Sparkles} size={18} className="mt-0.5" />
              <p className="m-0">{why.aiSummary ? l(why.aiSummary) : t('why.aiSlot')}</p>
            </section>
            <nav aria-label={t('why.jump')} className="flex flex-wrap gap-2">
              {why.groups.map((g) => (
                <a key={g.id} href={`#why-${g.id}`} className="inline-flex min-h-tap items-center rounded-pill border-[1.5px] border-divider px-4 text-sm text-ink no-underline hover:bg-neutral-200 hover:text-ink">
                  {t(`why.group.${g.id}`)} <span className="ms-1.5 text-neutral-700">{num(g.decisions.length)}</span>
                </a>
              ))}
            </nav>
            {why.groups.map((g) => (
              <section key={g.id} id={`why-${g.id}`} className="flex scroll-mt-20 flex-col gap-2.5" aria-labelledby={`why-${g.id}-h`}>
                <h2 id={`why-${g.id}-h`} className="m-0 text-xl">{t(`why.group.${g.id}`)}</h2>
                <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
                  {byRule(g.decisions).map((ds) => (ds.length > 1 ? <RuleGroup key={ds[0].ruleKey} ds={ds} /> : <Decision key={ds[0].ruleKey} d={ds[0]} />))}
                </ul>
              </section>
            ))}
          </div>
        )}
      </QueryView>
    </AppShell>
  );
}

/** The link to this page, used on "Your plan is ready", the dashboard and Profile. */
export function WhyPlanLink({ className }: { className?: string }) {
  const { t } = useI18n();
  return (
    <Link to="/plan/why" data-testid="why-link" className={cn('flex min-h-14 items-center gap-3 rounded-lg bg-surface px-4 py-2 text-ink no-underline hover:bg-neutral-300 hover:text-ink', className)}>
      <Icon as={ClipboardList} size={19} />
      <span className="flex flex-1 flex-col leading-tight"><strong className="text-[14.5px]">{t('why.link')}</strong><span className="text-[12.5px] text-neutral-700">{t('why.linkSub')}</span></span>
      <Icon as={ChevronRight} size={18} flip />
    </Link>
  );
}
