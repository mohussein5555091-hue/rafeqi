import { useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { Repeat, ChefHat, Image, Timer, Flame, Refrigerator, Zap, X, RefreshCw, Copy, Plus, ShoppingBasket, ChevronLeft, ChevronRight } from 'lucide-react';
import {
  AppShell, Button, Card, Checkbox, Disclaimer, EmptyState, Icon, LinkButton, QueryView, Segmented, Tabs, Toggle, cn, useToast,
} from '@/components';
import { useI18n } from '@/i18n';
import { api } from '@/data/api';
import { useQuery } from '@/data/useQuery';
import { mealIcon } from '@/screens/home/Dashboard';
import type { GroceryCategory, GroceryItem, GroceryList, Meal, MealDay, MealWeekDay, Plan } from '@/types';

/** Today's Egyptian meals, or the week; each day of the week opens its own page. */
export function NutritionPlan() {
  const { t, l, num, date } = useI18n();
  const [params, setParams] = useSearchParams();
  const view = (params.get('view') as 'day' | 'week') ?? 'day';
  const dayQ = useQuery(() => Promise.all([api.getMealDay(), api.getPlan()]));
  const weekQ = useQuery(() => api.getMealWeek());

  return (
    <AppShell title={t('nav.nutrition')} sub={dayQ.data ? t('nutrition.sub', { date: date(dayQ.data[0].date, { weekday: 'long', day: 'numeric', month: 'short' }), kind: t(dayQ.data[0].isTrainingDay ? 'nutrition.trainingDay' : 'nutrition.restDay') }) : undefined}>
      <div className="lg:max-w-sm"><Tabs label={t('nutrition.view')} value={view} onChange={(v) => setParams({ view: v })} tabs={[{ id: 'day', label: t('nutrition.day') }, { id: 'week', label: t('nutrition.week') }]} /></div>
      {view === 'day' ? (
        <QueryView query={dayQ}>
          {([day, plan]) => <MealDayView day={day} plan={plan} onChange={(d) => dayQ.setData([d, plan])} />}
        </QueryView>
      ) : (
        <QueryView query={weekQ}>
          {(week) => (
            <ol className="m-0 flex list-none flex-col gap-2.5 p-0">
              {week.map((d) => (
                <li key={d.date}>
                  <Link to={`/nutrition/day/${d.date}`} aria-label={t('nutrition.openDay', { date: date(d.date, { weekday: 'long', day: 'numeric', month: 'long' }) })}
                    className={cn('flex min-h-16 items-center gap-3 rounded-lg py-2 pe-3 ps-2 text-ink no-underline hover:bg-neutral-300 hover:text-ink',
                      d.date === dayQ.data?.[0].date ? 'bg-accent-100 ring-2 ring-inset ring-accent' : 'bg-surface')}>
                    <div className="flex w-11 shrink-0 flex-col items-center leading-tight"><span className="text-[11px]">{t(`enums.weekdayShort.${d.day}`)}</span><strong className="text-[17px]">{date(d.date, { day: 'numeric' })}</strong></div>
                    <div className="flex min-w-0 flex-1 flex-col text-[12.5px]"><strong className="truncate text-[13.5px]">{l(d.main)}</strong><span className="truncate text-neutral-800">{l(d.others)}</span></div>
                    <span className="whitespace-nowrap text-xs font-bold">{t('units.kcalN', { n: num(d.kcal) })}</span>
                    <Icon as={ChevronRight} flip size={18} className="text-neutral-700" />
                  </Link>
                </li>
              ))}
            </ol>
          )}
        </QueryView>
      )}
    </AppShell>
  );
}

/** /nutrition/day/2026-10-02: that exact date's meal plan, with previous / next day arrows. */
export function NutritionDay() {
  const { date: iso = '' } = useParams();
  const { t, date } = useI18n();
  const q = useQuery(() => Promise.all([api.getMealDay(iso), api.getPlan(), api.getMealWeek(), api.getMealDay()]), [iso]);
  const d = q.data?.[0];
  const isToday = !!d && d.date === q.data?.[3].date;
  return (
    <AppShell back title={d ? date(d.date, { weekday: 'long', day: 'numeric', month: 'long' }) : t('nav.nutrition')}
      sub={d ? `${t(d.isTrainingDay ? 'nutrition.trainingDay' : 'nutrition.restDay')}${isToday ? ` · ${t('nutrition.today')}` : ''}` : undefined}>
      <QueryView query={q}>
        {([day, plan, week, today]) => (
          <>
            <MealDayNav date={day.date} week={week} />
            <MealDayView key={day.date} day={day} plan={plan} onChange={(nd) => q.setData([nd, plan, week, today])} />
          </>
        )}
      </QueryView>
    </AppShell>
  );
}

function MealDayNav({ date: iso, week }: { date: string; week: MealWeekDay[] }) {
  const { t, date } = useI18n();
  const i = week.findIndex((d) => d.date === iso);
  const arrow = (to: MealWeekDay | undefined, icon: typeof ChevronLeft, label: string) => (to
    ? <LinkButton to={`/nutrition/day/${to.date}`} replace variant="secondary" size="icon" icon={icon} iconFlip aria-label={label} />
    : <Button variant="secondary" size="icon" icon={icon} iconFlip aria-label={label} disabled />);
  return (
    <nav aria-label={t('nutrition.week')} className="flex items-center justify-between gap-3 lg:justify-start">
      {arrow(i > 0 ? week[i - 1] : undefined, ChevronLeft, t('nutrition.prevDay'))}
      <strong className="text-center lg:min-w-48">{date(iso, { weekday: 'short', day: 'numeric', month: 'short' })}</strong>
      {arrow(i >= 0 ? week[i + 1] : undefined, ChevronRight, t('nutrition.nextDay'))}
    </nav>
  );
}

/** One day's meals: portions, macros, swap and recipe per meal, and the daily totals against the plan. */
function MealDayView({ day, plan, onChange }: { day: MealDay; plan: Plan; onChange: (d: MealDay) => void }) {
  const { t, l, num } = useI18n();
  const [swapFor, setSwapFor] = useState<Meal | null>(null);
  const total = (k: 'kcal' | 'proteinG' | 'carbsG' | 'fatG') => day.meals.reduce((a, m) => a + m[k], 0);
  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
      <div className="order-2 grid gap-4 lg:order-1 lg:grid-cols-2">
        {day.meals.map((m) => (
          <Card key={m.id} className="p-3.5" data-testid="meal-card">
            <div className="flex gap-3.5">
              <div className="washed grid h-[84px] w-[84px] shrink-0 place-items-center rounded-lg bg-accent-200 text-neutral-800"><Icon as={mealIcon[m.slot]} size={26} /></div>
              <div className="flex min-w-0 flex-1 flex-col gap-0.5"><span className="text-xs text-neutral-700">{t(`enums.mealSlot.${m.slot}`)} · {m.time}</span><strong className="text-base leading-snug">{l(m.name)}</strong><span className="text-[12.5px] text-neutral-800">{l(m.portions)}</span></div>
            </div>
            <div className="flex flex-wrap gap-1.5 text-xs">
              <span className="rounded-pill bg-bg px-2.5 py-1 font-bold">{t('units.kcalN', { n: num(m.kcal) })}</span>
              {([['p', m.proteinG], ['c', m.carbsG], ['f', m.fatG]] as const).map(([k, v]) => <span key={k} className="rounded-pill bg-neutral-100 px-2.5 py-1">{t(`macros.${k}Short`, { n: v })}</span>)}
            </div>
            <div className="mt-auto flex gap-2">
              <Button variant="secondary" size="sm" icon={Repeat} className="flex-1" onClick={() => setSwapFor(m)}>{t('nutrition.swap')}</Button>
              {m.recipeId
                ? <LinkButton to={`/nutrition/recipes/${m.recipeId}`} variant="secondary" size="sm" icon={ChefHat} className="flex-1">{t('nutrition.recipe')}</LinkButton>
                : <Button variant="secondary" size="sm" icon={ChefHat} className="flex-1" disabled>{t('nutrition.recipe')}</Button>}
            </div>
          </Card>
        ))}
      </div>
      <Card className="order-1 lg:order-2 lg:self-start" data-testid="daily-total">
        <div className="flex items-baseline justify-between"><span className="text-[13px] text-neutral-700">{t('nutrition.dailyTotal')}</span><span><span className="font-heading text-3xl">{num(total('kcal'))}</span> {t('units.kcal')}</span></div>
        <div className="grid grid-cols-3 gap-2 text-center">
          {([['protein', total('proteinG'), plan.proteinG, 'bg-sage-600'], ['carbs', total('carbsG'), plan.carbsG, 'bg-accent-500'], ['fat', total('fatG'), plan.fatG, 'bg-neutral-600']] as const).map(([k, v, target, dot]) => (
            <div key={k} className="rounded-md bg-bg px-1 py-2.5">
              <span className="block text-base font-bold">{t('units.grams', { n: v })}</span>
              <span className="inline-flex items-center gap-1 text-[11.5px]"><span className={`h-2 w-2 rounded-full ${dot}`} />{t(`macros.${k}`)}</span>
              <span className="block text-[10.5px] text-neutral-700">{t('nutrition.target', { n: target })}</span>
            </div>
          ))}
        </div>
        <LinkButton to="/groceries" variant="secondary" icon={ShoppingBasket}>{t('nav.groceries')}</LinkButton>
      </Card>
      <Disclaimer className="order-3 lg:col-span-2" />
      {swapFor && <SwapSheet date={day.date} meal={swapFor} onClose={() => setSwapFor(null)} onSwapped={(d) => { onChange(d); setSwapFor(null); }} />}
    </div>
  );
}

function SwapSheet({ date, meal, onClose, onSwapped }: { date: string; meal: Meal; onClose: () => void; onSwapped: (d: Awaited<ReturnType<typeof api.swapMeal>>) => void }) {
  const { t, l, num } = useI18n();
  const q = useQuery(() => api.getSwapOptions(meal.id), [meal.id]);
  const [pick, setPick] = useState<string>();
  const chosen = q.data?.find((m) => m.id === pick) ?? q.data?.[0];
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-neutral-900/50 lg:items-center" role="dialog" aria-modal="true" aria-label={t('nutrition.swapTitle', { slot: t(`enums.mealSlot.${meal.slot}`) })} onClick={onClose}>
      <div className="flex max-h-[90vh] w-full max-w-lg flex-col gap-3 overflow-auto rounded-t-[36px] bg-bg px-4 pb-7 pt-3 shadow-lg lg:rounded-card" onClick={(e) => e.stopPropagation()}>
        <span className="h-1.5 w-11 self-center rounded-pill bg-neutral-400 lg:hidden" />
        <div className="flex items-center justify-between"><h2 className="m-0 text-2xl">{t('nutrition.swapTitle', { slot: t(`enums.mealSlot.${meal.slot}`) })}</h2><Button variant="secondary" size="icon" icon={X} aria-label={t('common.close')} onClick={onClose} /></div>
        <div className="flex items-center gap-3 rounded-lg bg-surface px-4 py-3 text-[13px]"><span className="text-neutral-700">{t('nutrition.now')}</span><strong className="flex-1">{l(meal.name)}</strong><span>{t('units.kcalN', { n: num(meal.kcal) })}</span></div>
        <span className="text-[13px] text-neutral-700">{t('nutrition.swapHint')}</span>
        <QueryView query={q} isEmpty={(d) => d.length === 0} empty={<p className="m-0 text-sm">{t('nutrition.noSwaps')}</p>}>
          {(opts) => (
            <div role="radiogroup" className="flex flex-col gap-2">
              {opts.map((o) => {
                const on = o.id === chosen?.id;
                return (
                  <button key={o.id} type="button" role="radio" aria-checked={on} onClick={() => setPick(o.id)}
                    className={cn('flex items-center gap-3 rounded-lg px-4 py-3.5 text-start', on ? 'bg-accent-100 ring-2 ring-inset ring-accent' : 'bg-surface')}>
                    <div className="flex flex-1 flex-col gap-0.5">
                      <strong>{l(o.name)}</strong>
                      <span className="text-[12.5px] text-neutral-800">{l(o.portions)} · {t('nutrition.macroLine', { kcal: o.kcal, p: o.proteinG, c: o.carbsG, f: o.fatG })}</span>
                      <span className="text-xs font-semibold text-sage-800">{t('nutrition.delta', { kcal: (o.kcal - meal.kcal > 0 ? '+' : '') + (o.kcal - meal.kcal), p: (o.proteinG - meal.proteinG > 0 ? '+' : '') + (o.proteinG - meal.proteinG) })}</span>
                    </div>
                    <span className={cn('h-6 w-6 shrink-0 rounded-full', on ? 'border-[7px] border-accent' : 'border-2 border-neutral-500')} />
                  </button>
                );
              })}
            </div>
          )}
        </QueryView>
        <Button size="lg" disabled={!chosen} onClick={async () => chosen && onSwapped(await api.swapMeal(date, meal.id, chosen))}>{chosen ? t('nutrition.swapTo', { name: l(chosen.name) }) : t('nutrition.swap')}</Button>
        <span className="text-center text-xs text-neutral-700">{t('nutrition.groceryUpdates')}</span>
      </div>
    </div>
  );
}

/** Recipe: photo area, ingredients scaled to the user's portion, steps with timers, storage & reheating. */
export function RecipeDetail() {
  const { id = '' } = useParams();
  const { t, l, num } = useI18n();
  const q = useQuery(() => api.getRecipe(id), [id]);
  const [batch, setBatch] = useState<1 | 3>(1);
  const [running, setRunning] = useState<number | null>(null);
  return (
    <AppShell back title={q.data ? l(q.data.name) : t('nutrition.recipe')} sub={t('nutrition.recipeSub')}>
      <QueryView query={q}>
        {(r) => (
          <div className="grid gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
            <div className="flex flex-col gap-4">
              <div className="washed grid h-56 place-items-center overflow-hidden rounded-card bg-sage-300">
                {r.photoUrl ? <img src={r.photoUrl} alt={l(r.name)} className="h-full w-full object-cover" /> : <span className="flex items-center gap-2 text-[12.5px] font-semibold text-sage-900"><Icon as={Image} size={18} />{t('nutrition.photo')}</span>}
              </div>
              <div className="grid grid-cols-4 gap-2 text-center">
                {([[Timer, t('units.minutesShort', { n: r.prepMin }), t('nutrition.prep')], [Flame, t('units.minutesShort', { n: r.cookMin }), t('nutrition.cook')], [Refrigerator, t('nutrition.days', { n: r.fridgeDays }), t('nutrition.fridge')], [Zap, num(r.kcal * batch), t('units.kcal')]] as const).map(([ic, v, k]) => (
                  <div key={k} className="flex flex-col items-center rounded-md bg-surface px-0.5 py-2.5"><Icon as={ic} size={18} /><span className="text-sm font-bold">{v}</span><span className="text-[11px]">{k}</span></div>
                ))}
              </div>
              <Card tone="sage" className="text-sm">
                <strong className="flex items-center gap-2"><Icon as={Refrigerator} size={18} />{t('nutrition.storing')}</strong>
                <span>{l(r.storage)}</span><span>{l(r.reheating)}</span>
              </Card>
            </div>
            <div className="flex flex-col gap-5">
              <section className="flex flex-col gap-2">
                <div className="flex items-center justify-between gap-3"><h2 className="m-0 text-xl">{t('nutrition.ingredients')}</h2>
                  <Segmented className="min-h-tap" label={t('nutrition.portions')} value={batch} onChange={setBatch} options={[{ id: 1, label: t('nutrition.onePortion') }, { id: 3, label: t('nutrition.prepThree') }]} /></div>
                <span className="text-xs text-neutral-700">{t('nutrition.scaledTo', { kcal: num(r.kcal) })}</span>
                <ul className="m-0 grid list-none rounded-lg bg-surface px-5 py-1.5 lg:grid-cols-2 lg:gap-x-7">
                  {r.ingredients.map((i) => (
                    <li key={i.name.en} className="flex min-h-tap items-center justify-between gap-2.5 border-b border-divider text-sm">
                      <span className="min-w-0 flex-1 truncate">{l(i.name)}</span>
                      <strong className="whitespace-nowrap">{batch === 1 || !i.grams ? l(i.amount) : t('units.grams', { n: i.grams * batch })}</strong>
                    </li>
                  ))}
                </ul>
              </section>
              <section className="flex flex-col gap-3"><h2 className="m-0 text-xl">{t('nutrition.steps')}</h2>
                <ol className="m-0 flex list-none flex-col gap-3 p-0">
                  {r.steps.map((s, i) => (
                    <li key={i} className="flex items-start gap-3">
                      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-accent text-sm font-bold text-bg">{i + 1}</span>
                      <div className="flex min-w-0 flex-1 flex-col gap-1.5 pt-1 lg:flex-row lg:items-center lg:gap-3.5">
                        <span className="flex-1 text-[14.5px]">{l(s.text)}</span>
                        {s.timerSec && (
                          <Button variant="secondary" size="sm" icon={Timer} className="self-start font-body font-bold" onClick={() => setRunning(running === i ? null : i)} aria-pressed={running === i}>
                            {running === i ? t('nutrition.timerRunning') : t('nutrition.startTimer', { t: `${Math.floor(s.timerSec / 60)}:${String(s.timerSec % 60).padStart(2, '0')}` })}
                          </Button>
                        )}
                      </div>
                    </li>
                  ))}
                </ol>
              </section>
            </div>
          </div>
        )}
      </QueryView>
    </AppShell>
  );
}

const CATEGORY_ORDER: GroceryCategory[] = ['produce', 'meat', 'dairy', 'bakery', 'pantry', 'spices'];

/** Plain-text list for WhatsApp. */
export function groceryText(list: GroceryList, period: 'week' | 'month', t: (k: string, v?: Record<string, string | number>) => string, l: (x: GroceryItem['name']) => string, num: (n: number, d?: number) => string) {
  const lines = [t('groceries.copyHeader', { period: t(`groceries.${period}`) })];
  for (const c of CATEGORY_ORDER) {
    const rows = list.items.filter((i) => i.period === period && i.category === c && !i.haveIt);
    if (!rows.length) continue;
    lines.push('', t(`enums.groceryCategory.${c}`));
    rows.forEach((i) => lines.push(`- ${l(i.name)} · ${num(i.qty, 2)} ${t(`units.${i.unit}`)}`));
  }
  return lines.join('\n');
}

/** Auto-generated list: this week (fresh) / this month (staples), grouped by category. */
export function Groceries() {
  const { t, l, num, date } = useI18n();
  const toast = useToast();
  const q = useQuery(() => api.getGroceryList());
  const [period, setPeriod] = useState<'week' | 'month'>('week');
  const update = async (id: string, patch: Partial<Pick<GroceryItem, 'checked' | 'haveIt'>>) => q.setData(await api.updateGroceryItem(id, patch));

  return (
    <AppShell title={t('nav.groceries')} sub={q.data ? t('groceries.sub', { week: q.data.weekNumber, start: date(q.data.start), end: date(q.data.end) }) : undefined}
      actions={<LinkButton to="/groceries/pantry" variant="secondary" size="sm" className="hidden lg:inline-flex">{t('groceries.pantry')}</LinkButton>}>
      <div className="lg:max-w-sm"><Tabs label={t('groceries.period')} value={period} onChange={setPeriod} tabs={[{ id: 'week', label: t('groceries.week') }, { id: 'month', label: t('groceries.month') }]} /></div>
      <QueryView query={q} isEmpty={(d) => d.items.filter((i) => i.period === period && !i.haveIt).length === 0}
        empty={<EmptyState icon={ShoppingBasket} title={t('groceries.emptyTitle')} body={t('groceries.emptyBody')} action={<LinkButton to="/groceries/pantry" variant="secondary">{t('groceries.pantry')}</LinkButton>} />}>
        {(list) => {
          const items = list.items.filter((i) => i.period === period);
          const toBuy = items.filter((i) => !i.haveIt);
          return (
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
              <div className="flex flex-col gap-4">
                {period === 'week' && list.changeNote && (
                  <div className="flex items-start gap-3 rounded-lg bg-accent-100 px-4 py-3.5 text-[13.5px] text-accent-900"><Icon as={RefreshCw} size={18} className="mt-0.5 text-accent-700" /><span>{l(list.changeNote)}</span></div>
                )}
                <div className="grid gap-4 lg:grid-cols-2">
                  {CATEGORY_ORDER.map((c) => {
                    const rows = items.filter((i) => i.category === c);
                    if (!rows.length) return null;
                    return (
                      <section key={c} className="flex flex-col gap-1.5">
                        <div className="flex items-baseline justify-between px-1.5"><h2 className="m-0 text-base">{t(`enums.groceryCategory.${c}`)}</h2><span className="text-xs text-neutral-700">{t('groceries.catCount', { n: rows.filter((i) => !i.haveIt).length })}</span></div>
                        <ul className="m-0 flex list-none flex-col overflow-hidden rounded-lg bg-surface p-0">
                          {rows.map((i) => (
                            <li key={i.id} className={cn('flex items-center gap-1.5 border-b border-divider py-1.5 pe-4 ps-1', i.haveIt && 'opacity-55')}>
                              <Checkbox checked={i.checked} onChange={(checked) => update(i.id, { checked })} label={l(i.name)} />
                              <div className="flex min-w-0 flex-1 flex-col">
                                <span className={cn('text-[14.5px]', i.checked && 'text-neutral-700 line-through')}>{l(i.name)} · <strong>{num(i.qty, 2)} {t(`units.${i.unit}`)}</strong></span>
                                <Toggle checked={i.haveIt} onChange={(haveIt) => update(i.id, { haveIt })} label={t('groceries.haveIt')} />
                              </div>
                            </li>
                          ))}
                        </ul>
                      </section>
                    );
                  })}
                </div>
              </div>
              <div className="flex flex-col gap-3 lg:sticky lg:top-6 lg:self-start">
                <Card tone="ink">
                  <div className="flex items-baseline justify-between"><span className="text-[13px] opacity-80">{t(`groceries.toBuy.${period}`)}</span><span className="font-heading text-[26px]">{num(toBuy.length)}</span></div>
                  <span className="text-[12.5px] opacity-80">{t('groceries.haveCount', { have: items.length - toBuy.length })}</span>
                  <Button variant="inverse" icon={Copy} onClick={async () => {
                    await navigator.clipboard?.writeText(groceryText(list, period, t, l, num)).catch(() => undefined);
                    toast({ message: t('groceries.copied'), tone: 'success' });
                  }}>{t('groceries.copy')}</Button>
                </Card>
                <LinkButton to="/groceries/pantry" variant="secondary" className="lg:hidden">{t('groceries.pantry')}</LinkButton>
                <p className="m-0 text-xs text-neutral-700">{t('groceries.packNote')}</p>
              </div>
            </div>
          );
        }}
      </QueryView>
    </AppShell>
  );
}

/** Staples the user already has at home. */
export function Pantry() {
  const { t, l } = useI18n();
  const q = useQuery(() => api.getPantry());
  const tone = { plenty: 'bg-sage-100 text-sage-800', low: 'bg-accent-100 text-accent-800', untracked: 'bg-neutral-200 text-neutral-800' } as const;
  return (
    <AppShell back title={t('groceries.pantry')}>
      <p className="m-0 text-sm text-neutral-800">{t('groceries.pantryIntro')}</p>
      <QueryView query={q} isEmpty={(d) => d.length === 0} empty={<EmptyState title={t('groceries.pantryEmpty')} />}>
        {(items) => (
          <ul className="m-0 flex max-w-2xl list-none flex-col rounded-lg bg-surface py-1 pe-2 ps-4">
            {items.map((p) => (
              <li key={p.id} className="flex min-h-14 items-center gap-2.5 border-b border-divider">
                <span className="flex-1 text-[14.5px] font-semibold">{l(p.name)}</span>
                <span className={cn('whitespace-nowrap rounded-pill px-2.5 py-1 text-[11.5px] font-bold', tone[p.level])}>{t(`groceries.level.${p.level}`)}</span>
                <Button variant="ghost" size="sm">{t('groceries.markLow')}</Button>
              </li>
            ))}
          </ul>
        )}
      </QueryView>
      <Button variant="secondary" icon={Plus} className="self-start">{t('groceries.addStaple')}</Button>
    </AppShell>
  );
}
