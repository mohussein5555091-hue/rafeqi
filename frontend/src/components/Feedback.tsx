import { createContext, useCallback, useContext, useState, type ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';
import { Check, CloudOff, Info, Sprout, CircleCheck, TriangleAlert } from 'lucide-react';
import { Button, cn, Icon } from './Button';
import { useI18n } from '@/i18n';
import type { Query } from '@/data/useQuery';
import { NotFoundError } from '@/data/api';

// ── Loading / empty / error ──────────────────────────────────────────
export function Skeleton({ className }: { className?: string }) {
  return <span aria-hidden className={cn('block animate-pulse-soft rounded-pill bg-neutral-300', className)} />;
}

export function LoadingState({ rows = 3 }: { rows?: number }) {
  const { t } = useI18n();
  return (
    <div aria-busy="true" aria-label={t('common.loading')} className="flex flex-col gap-4">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex flex-col gap-3 rounded-card bg-surface p-6">
          <Skeleton className="h-3 w-1/3" /><Skeleton className="h-6 w-2/3" /><Skeleton className="h-3 w-1/2" />
        </div>
      ))}
    </div>
  );
}

export function EmptyState({ icon = Sprout, title, body, action }: { icon?: LucideIcon; title: string; body?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-card bg-neutral-100 p-6 ring-[1.5px] ring-inset ring-divider">
      <span className="grid h-16 w-16 place-items-center rounded-full bg-sage-200 text-sage-700"><Icon as={icon} size={28} /></span>
      <h3 className="m-0 text-2xl">{title}</h3>
      {body && <p className="m-0 text-neutral-800">{body}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ title, body, onRetry, icon = CloudOff }: { title?: string; body?: string; onRetry?: () => void; icon?: LucideIcon }) {
  const { t } = useI18n();
  return (
    <div role="alert" className="flex flex-col items-start gap-3 rounded-card bg-surface p-6">
      <span className="grid h-16 w-16 place-items-center rounded-full bg-warn-100 text-warn-600"><Icon as={icon} size={28} /></span>
      <h3 className="m-0 text-2xl">{title ?? t('common.errorTitle')}</h3>
      <p className="m-0 text-neutral-800">{body ?? t('common.errorBody')}</p>
      {onRetry && <Button onClick={onRetry}>{t('common.retry')}</Button>}
    </div>
  );
}

/** Renders loading / error / (optional) empty states around a query. */
export function QueryView<T>({ query, children, isEmpty, empty, loading }: {
  query: Query<T>; children: (data: T) => ReactNode; isEmpty?: (d: T) => boolean; empty?: ReactNode; loading?: ReactNode;
}) {
  const { t } = useI18n();
  if (query.loading && query.data === undefined) return <>{loading ?? <LoadingState />}</>;
  if (query.error) return query.error instanceof NotFoundError
    ? <ErrorState title={t('common.notFoundTitle')} body={t('common.notFoundBody')} />
    : <ErrorState onRetry={query.reload} />;
  if (query.data === undefined) return null;
  if (isEmpty?.(query.data) && empty) return <>{empty}</>;
  return <>{children(query.data)}</>;
}

// ── Wait screen (plan generation, weekly review) ─────────────────────
export function Breathing({ size = 200, mark }: { size?: number; mark: string }) {
  return (
    <div className="relative" style={{ width: size, height: size }} aria-hidden>
      <span className="absolute inset-0 animate-breathe rounded-full bg-sage-200 motion-reduce:animate-none" />
      <span className="absolute animate-breathe rounded-full bg-sage-400 [animation-delay:.6s] motion-reduce:animate-none" style={{ inset: size * 0.17 }} />
      <span className="absolute grid place-items-center rounded-full bg-accent font-heading text-on-accent" style={{ inset: size * 0.35, fontSize: size * 0.15 }}>{mark}</span>
    </div>
  );
}

export function StepList({ steps }: { steps: { label: string; state: 'done' | 'active' | 'todo'; detail?: string }[] }) {
  return (
    <ol className="m-0 flex list-none flex-col gap-3.5 p-0" aria-live="polite">
      {steps.map((s) => (
        <li key={s.label} className={cn('flex items-center gap-3.5 text-[15px]', s.state === 'active' && 'font-bold', s.state === 'todo' && 'text-neutral-700')}>
          {s.state === 'done' && <span className="grid h-8 w-8 place-items-center rounded-full bg-sage-600 text-bg"><Icon as={Check} size={17} /></span>}
          {s.state === 'active' && <span className="h-8 w-8 animate-spin rounded-full border-[3px] border-accent-300 border-t-accent motion-reduce:animate-none" />}
          {s.state === 'todo' && <span className="h-8 w-8 rounded-full border-2 border-dashed border-neutral-400" />}
          <span className="flex-1">{s.label}</span>
          {s.detail && <span className="text-[12.5px] font-normal text-neutral-700">{s.detail}</span>}
        </li>
      ))}
    </ol>
  );
}

// ── Disclaimer ───────────────────────────────────────────────────────
export function Disclaimer({ className }: { className?: string }) {
  const { t } = useI18n();
  return <p className={cn('m-0 flex items-start gap-1.5 text-xs text-neutral-700', className)}><Icon as={Info} size={14} className="mt-0.5" />{t('common.disclaimer')}</p>;
}

// ── Toasts ───────────────────────────────────────────────────────────
type ToastTone = 'default' | 'success' | 'error';
interface ToastMsg { id: number; message: string; tone: ToastTone; action?: { label: string; onClick: () => void } }
const ToastCtx = createContext<(m: Omit<ToastMsg, 'id' | 'tone'> & { tone?: ToastTone }) => void>(() => {});

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastMsg[]>([]);
  const show = useCallback((m: Omit<ToastMsg, 'id' | 'tone'> & { tone?: ToastTone }) => {
    const id = Date.now();
    setItems((x) => [...x, { ...m, id, tone: m.tone ?? 'default' }]);
    setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), 3200);
  }, []);
  const style: Record<ToastTone, [string, LucideIcon]> = {
    default: ['bg-ink text-bg', CircleCheck], success: ['bg-sage-200 text-sage-900', CircleCheck], error: ['bg-warn-100 text-warn-800', TriangleAlert],
  };
  return (
    <ToastCtx.Provider value={show}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed inset-x-4 bottom-28 z-50 flex flex-col items-center gap-2 lg:bottom-8">
        {items.map((i) => (
          <div key={i.id} className={cn('pointer-events-auto flex max-w-md items-center gap-3 rounded-pill py-3 pe-3 ps-5 shadow-lg', style[i.tone][0])}>
            <Icon as={style[i.tone][1]} /><span className="flex-1 text-sm">{i.message}</span>
            {i.action && <button className="min-h-9 px-2 font-bold underline" onClick={i.action.onClick}>{i.action.label}</button>}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
export const useToast = () => useContext(ToastCtx);
