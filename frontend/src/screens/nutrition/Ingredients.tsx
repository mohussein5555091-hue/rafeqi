import { useState } from 'react';
import { Lightbulb, MinusCircle, Repeat, Undo2, X } from 'lucide-react';
import { Badge, Button, Card, Icon, QueryView, Segmented, cn, useToast } from '@/components';
import { useI18n } from '@/i18n';
import { api } from '@/data/api';
import { useQuery } from '@/data/useQuery';
import type { DayNote, IngredientReplacement, MealDay, MealIngredient, RemoveReason, RemoveScope } from '@/types';

type Row = Pick<MealIngredient, 'name' | 'amount'> & Partial<MealIngredient>;
const REASONS: RemoveReason[] = ['dislike', 'unavailable'];

/**
 * A meal's ingredients, each with Remove (or, once removed or replaced, struck through with Undo).
 * Used on the meal cards and the recipe page. `onChanged` gets the meal's day back from the API.
 */
export function IngredientList({ mealId, mealName, ingredients, onChanged, onSwapMeal, className }: {
  mealId: string; mealName: string; ingredients: Row[]; onChanged: (d: MealDay) => void; onSwapMeal: () => void; className?: string;
}) {
  const { t, l } = useI18n();
  const toast = useToast();
  const [removing, setRemoving] = useState<Row>();
  const [busy, setBusy] = useState<string>();
  const undo = async (i: Row) => {
    setBusy(i.foodId);
    try {
      onChanged(await api.undoIngredient(mealId, i.foodId!));
      toast({ message: t('ingredients.undone', { name: l(i.name) }), tone: 'success' });
    } catch {
      toast({ message: t('common.saveFailed'), tone: 'error' });
    } finally {
      setBusy(undefined);
    }
  };
  return (
    <>
      <ul className={cn('m-0 flex list-none flex-col p-0', className)} data-testid="ingredients">
        {ingredients.map((i) => {
          const changed = i.status === 'removed' || i.status === 'replaced';
          return (
            <li key={i.foodId ?? l(i.name)} data-testid="ingredient" data-food={i.foodId} data-status={i.status ?? 'kept'}
              className="flex min-h-tap items-center gap-2.5 border-b border-divider py-1.5 text-sm last:border-b-0">
              <span className="flex min-w-0 flex-1 flex-col leading-tight">
                <span className={cn('flex flex-wrap items-center gap-x-2', changed && 'text-neutral-700 line-through')}>
                  {l(i.name)}
                  {i.essential && !changed && <span className="text-[11px] font-semibold text-sage-800 no-underline">{t('ingredients.essential')}</span>}
                </span>
                {i.status === 'replaced' && i.replacement && (
                  <strong className="text-[13px]">{t('ingredients.replacedBy', { name: l(i.replacement.name), amount: l(i.replacement.amount) })}</strong>
                )}
                {i.status === 'removed' && i.change && <span className="text-xs text-neutral-700">{t(`ingredients.removedBecause.${i.change.reason}`)}</span>}
              </span>
              <strong className={cn('whitespace-nowrap', changed && 'font-normal text-neutral-700 line-through')}>{l(i.amount)}</strong>
              {i.foodId && (changed ? (
                <Button variant="secondary" size="sm" icon={Undo2} disabled={busy === i.foodId} aria-label={t('ingredients.undoLabel', { name: l(i.name) })} onClick={() => undo(i)}>{t('ingredients.undo')}</Button>
              ) : (
                <Button variant="ghost" size="sm" icon={MinusCircle} aria-label={t('ingredients.removeLabel', { name: l(i.name) })} onClick={() => setRemoving(i)}>{t('ingredients.remove')}</Button>
              ))}
            </li>
          );
        })}
      </ul>
      {removing && (
        <RemoveSheet mealId={mealId} mealName={mealName} ingredient={removing} onClose={() => setRemoving(undefined)}
          onSwapMeal={() => { setRemoving(undefined); onSwapMeal(); }}
          onDone={(d) => { setRemoving(undefined); onChanged(d); }} />
      )}
    </>
  );
}

/** Why (one tap) → something similar instead, or nothing → just this meal, or always → Remove. */
function RemoveSheet({ mealId, mealName, ingredient, onClose, onDone, onSwapMeal }: {
  mealId: string; mealName: string; ingredient: Row; onClose: () => void; onDone: (d: MealDay) => void; onSwapMeal: () => void;
}) {
  const { t, l, num } = useI18n();
  const toast = useToast();
  const q = useQuery(() => api.getReplacements(mealId, ingredient.foodId!), [mealId, ingredient.foodId]);
  const [reason, setReason] = useState<RemoveReason>();
  const [pick, setPick] = useState<IngredientReplacement | null>(null);
  const [scope, setScope] = useState<RemoveScope>('meal');
  const [busy, setBusy] = useState(false);
  const name = l(ingredient.name);
  const confirm = async () => {
    if (!reason) return;
    setBusy(true);
    try {
      const d = await api.removeIngredient(mealId, ingredient.foodId!, { reason, scope, replacementFoodId: pick?.foodId ?? null });
      toast({ message: t(pick ? 'ingredients.replacedDone' : 'ingredients.done', { name }), tone: 'success' });
      onDone(d);
    } catch {
      toast({ message: t('common.saveFailed'), tone: 'error' });
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-neutral-900/50 lg:items-center" role="dialog" aria-modal="true" aria-label={t('ingredients.sheetTitle', { name })} onClick={onClose}>
      <div className="flex max-h-[90vh] w-full max-w-lg flex-col gap-3 overflow-auto rounded-t-[36px] bg-bg px-4 pb-7 pt-3 shadow-lg lg:rounded-card" onClick={(e) => e.stopPropagation()}>
        <span className="h-1.5 w-11 self-center rounded-pill bg-neutral-400 lg:hidden" />
        <div className="flex items-center justify-between gap-3"><h2 className="m-0 text-2xl">{t('ingredients.sheetTitle', { name })}</h2><Button variant="secondary" size="icon" icon={X} aria-label={t('common.close')} onClick={onClose} /></div>
        <QueryView query={q}>
          {(opts) => opts.essential ? (
            <div className="flex flex-col gap-3" data-testid="essential">
              <div className="rounded-lg bg-attn-100 px-4 py-4 text-attn-800"><strong className="mb-0.5 block text-[15px]">{t('ingredients.essentialTitle', { name })}</strong>
                <span className="text-sm">{t('ingredients.essentialBody', { meal: mealName })}</span></div>
              <Button size="lg" icon={Repeat} onClick={onSwapMeal}>{t('ingredients.swapMeal')}</Button>
              <Button variant="ghost" onClick={onClose}>{t('ingredients.keep')}</Button>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              <span className="text-[13.5px] font-semibold">{t('ingredients.why')}</span>
              <div role="radiogroup" aria-label={t('ingredients.why')} className="flex flex-col gap-2">
                {REASONS.map((r) => (
                  <button key={r} type="button" role="radio" aria-checked={reason === r} onClick={() => { setReason(r); if (r === 'dislike') setScope('always'); }}
                    className={cn('flex min-h-[56px] flex-col justify-center rounded-lg px-4 py-2 text-start', reason === r ? 'bg-accent-100 ring-2 ring-inset ring-accent-700' : 'bg-surface hover:bg-neutral-300')}>
                    <strong className="text-[15px]">{t(`ingredients.reason.${r}`)}</strong><span className="text-[12.5px] text-neutral-700">{t(`ingredients.reasonHint.${r}`)}</span>
                  </button>
                ))}
              </div>
              {reason && (
                <>
                  <span className="text-[13.5px] font-semibold">{t('ingredients.replace')}</span>
                  <div role="radiogroup" aria-label={t('ingredients.replace')} className="flex flex-col gap-2">
                    {opts.options.map((o) => (
                      <button key={o.foodId} type="button" role="radio" aria-checked={pick?.foodId === o.foodId} onClick={() => setPick(o)}
                        className={cn('flex flex-col rounded-lg px-4 py-2.5 text-start', pick?.foodId === o.foodId ? 'bg-accent-100 ring-2 ring-inset ring-accent-700' : 'bg-surface')}>
                        <strong>{l(o.name)}</strong>
                        <span className="text-[12.5px] text-neutral-800">{t('ingredients.option', { g: num(o.grams), kcal: num(o.kcal), p: num(o.proteinG) })}</span>
                      </button>
                    ))}
                    <button type="button" role="radio" aria-checked={pick === null} onClick={() => setPick(null)}
                      className={cn('flex min-h-tap items-center rounded-lg px-4 py-2.5 text-start', pick === null ? 'bg-accent-100 ring-2 ring-inset ring-accent-700' : 'bg-surface')}>
                      <strong>{t('ingredients.none')}</strong>
                    </button>
                  </div>
                  {opts.options.length === 0 && <span className="text-xs text-neutral-700">{t('ingredients.noReplacements')}</span>}
                  <span className="text-[13.5px] font-semibold">{t('ingredients.scope')}</span>
                  <Segmented className="min-h-tap" label={t('ingredients.scope')} value={scope} onChange={setScope}
                    options={[{ id: 'meal', label: t('ingredients.meal') }, { id: 'always', label: t('ingredients.always') }]} />
                  <span className="text-xs text-neutral-700">{t(scope === 'always' ? 'ingredients.alwaysHint' : reason === 'dislike' ? 'ingredients.dislikeHint' : 'ingredients.mealHint')}</span>
                  <Button size="lg" icon={MinusCircle} disabled={busy} onClick={confirm}>
                    {pick ? t('ingredients.confirmReplace', { name: l(pick.name) }) : t('ingredients.confirmRemove', { name })}
                  </Button>
                  <span className="text-center text-xs text-neutral-700">{t('ingredients.updates')}</span>
                </>
              )}
            </div>
          )}
        </QueryView>
      </div>
    </div>
  );
}

/** What the engine did to keep the day on target after an ingredient change (and a snack, if portions couldn't). */
export function DayNoteCard({ note }: { note: DayNote }) {
  const { t, l, num } = useI18n();
  return (
    <Card tone={note.onTarget ? 'sage' : 'attn'} className="gap-2" data-testid="day-note">
      <strong className="flex items-center gap-2"><Icon as={Lightbulb} size={18} />{t('ingredients.noteTitle')}</strong>
      <ul className="m-0 flex list-disc flex-col gap-1 ps-5 text-[13.5px]">
        {note.lines.map((line, i) => <li key={i}>{l(line)}</li>)}
      </ul>
      {note.snack && (
        <Badge className="bg-bg font-semibold">{t('ingredients.snack', { name: l(note.snack.name), kcal: num(note.snack.kcal), p: num(note.snack.protein) })}</Badge>
      )}
    </Card>
  );
}
