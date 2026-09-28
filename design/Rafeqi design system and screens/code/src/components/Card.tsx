import type { HTMLAttributes, ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';
import { Check, CircleAlert, TriangleAlert, Shield, BookOpen } from 'lucide-react';
import { cn, Icon } from './Button';
import { useI18n } from '@/i18n';
import type { Status } from '@/types';

// ── Card ─────────────────────────────────────────────────────────────
type Tone = 'surface' | 'sage' | 'accent' | 'warn' | 'plain' | 'ink';
const tones: Record<Tone, string> = {
  surface: 'bg-surface',
  sage: 'bg-sage-100 text-sage-900',
  accent: 'bg-accent-100 text-accent-900',
  warn: 'bg-warn-100 text-warn-800',
  plain: 'bg-bg',
  ink: 'bg-ink text-bg',
};
export function Card({ tone = 'surface', className, ...rest }: { tone?: Tone } & HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('flex flex-col gap-o-3 rounded-card p-5', tones[tone], className)} {...rest} />;
}
export function Kicker({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cn('text-xs font-bold uppercase tracking-[.08em] text-accent-700 rtl:normal-case rtl:tracking-normal', className)}>{children}</span>;
}

// ── Chips ────────────────────────────────────────────────────────────
export function Chip({ selected, onToggle, children, icon }: { selected: boolean; onToggle?: () => void; children: ReactNode; icon?: LucideIcon }) {
  return (
    <button type="button" aria-pressed={selected} onClick={onToggle}
      className={cn('inline-flex min-h-tap items-center gap-1.5 whitespace-nowrap rounded-pill border-[1.5px] px-4 text-sm transition-colors',
        selected ? 'border-accent bg-accent-100 font-bold text-accent-800' : 'border-divider text-ink hover:bg-neutral-200')}>
      {selected ? <Icon as={Check} size={15} /> : icon && <Icon as={icon} size={15} />}
      {children}
    </button>
  );
}

export function ChipGroup<T extends string>({ options, value, onChange, label }: {
  options: { id: T; label: string }[]; value: T[]; onChange: (v: T[]) => void; label?: string;
}) {
  return (
    <div role="group" aria-label={label} className="flex flex-wrap gap-2">
      {options.map((o) => (
        <Chip key={o.id} selected={value.includes(o.id)} onToggle={() => onChange(value.includes(o.id) ? value.filter((v) => v !== o.id) : [...value, o.id])}>
          {o.label}
        </Chip>
      ))}
    </div>
  );
}

// ── Badges ───────────────────────────────────────────────────────────
const statusStyle: Record<Status, { cls: string; icon: LucideIcon }> = {
  onTrack: { cls: 'bg-sage-100 text-sage-800', icon: Check },
  attention: { cls: 'bg-accent-100 text-accent-800', icon: CircleAlert },
  warning: { cls: 'bg-warn-100 text-warn-800', icon: TriangleAlert },
};

export function Badge({ className, children, icon }: { className?: string; children: ReactNode; icon?: LucideIcon }) {
  return (
    <span className={cn('inline-flex items-center gap-1.5 self-start whitespace-nowrap rounded-pill px-3 py-1 text-xs font-bold', className)}>
      {icon && <Icon as={icon} size={13} />}{children}
    </span>
  );
}

/** One status language everywhere: on track · needs attention · warning. */
export function StatusBadge({ status, label }: { status: Status; label?: string }) {
  const { t } = useI18n();
  const s = statusStyle[status];
  return <Badge className={s.cls} icon={s.icon}>{label ?? t(`status.${status}`)}</Badge>;
}

export function SwapBadge({ label }: { label: string }) {
  return <Badge className="bg-warn-100 text-warn-800" icon={Shield}>{label}</Badge>;
}

export function CitationChip({ source }: { source: string }) {
  return <Badge className="bg-bg font-normal text-neutral-800" icon={BookOpen}>{source}</Badge>;
}

// ── Progress ─────────────────────────────────────────────────────────
export function ProgressBar({ value, max = 100, tone = 'sage', label }: { value: number; max?: number; tone?: 'sage' | 'accent' | 'neutral'; label?: string }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  const fill = { sage: 'bg-sage-600', accent: 'bg-accent-500', neutral: 'bg-neutral-600' }[tone];
  return (
    <div role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={max} aria-label={label} className="h-2 w-full rounded-pill bg-neutral-300">
      <div className={cn('h-2 rounded-pill', fill)} style={{ width: `${pct}%` }} />
    </div>
  );
}

/** Segmented step indicator for multi-step flows. */
export function StepProgress({ step, total, label }: { step: number; total: number; label: string }) {
  return (
    <div role="progressbar" aria-valuenow={step} aria-valuemin={1} aria-valuemax={total} aria-label={label}
      className="grid gap-1.5" style={{ gridTemplateColumns: `repeat(${total}, 1fr)` }}>
      {Array.from({ length: total }, (_, i) => <span key={i} className={cn('h-2 rounded-pill', i < step ? 'bg-accent' : 'bg-neutral-300')} />)}
    </div>
  );
}
