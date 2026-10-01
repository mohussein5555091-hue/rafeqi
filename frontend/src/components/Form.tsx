import { useId, useState, type InputHTMLAttributes, type ReactNode } from 'react';
import { Eye, EyeOff, Minus, Plus, CircleAlert } from 'lucide-react';
import { cn, Icon } from './Button';
import { useI18n } from '@/i18n';

export function Field({ label, hint, error, children, htmlFor }: { label: ReactNode; hint?: ReactNode; error?: string; children: ReactNode; htmlFor?: string }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={htmlFor} className="text-[13px] text-neutral-800">{label}</label>
      {children}
      {error ? (
        <span role="alert" className="flex items-center gap-1.5 text-[13px] text-warn-700"><Icon as={CircleAlert} size={14} />{error}</span>
      ) : hint ? <span className="text-xs text-neutral-700">{hint}</span> : null}
    </div>
  );
}

const inputCls = (invalid?: boolean) => cn(
  'h-[52px] w-full rounded-pill border bg-surface px-4 text-base text-ink caret-accent placeholder:text-neutral-600',
  'hover:border-neutral-600 focus-visible:border-accent-700 focus-visible:outline-offset-0',
  invalid ? 'border-warn-600 ring-1 ring-warn-600' : 'border-divider',
);

export function TextInput({ invalid, className, ...rest }: { invalid?: boolean } & InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(inputCls(invalid), className)} aria-invalid={invalid || undefined} {...rest} />;
}

export function PasswordInput({ invalid, ...rest }: { invalid?: boolean } & InputHTMLAttributes<HTMLInputElement>) {
  const { t } = useI18n();
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <input type={show ? 'text' : 'password'} className={cn(inputCls(invalid), 'pe-14')} aria-invalid={invalid || undefined} {...rest} />
      <button type="button" onClick={() => setShow((s) => !s)} aria-label={t(show ? 'auth.hidePassword' : 'auth.showPassword')}
        className="absolute end-1 top-1 grid h-tap w-tap place-items-center rounded-pill text-ink hover:bg-neutral-200">
        <Icon as={show ? EyeOff : Eye} />
      </button>
    </div>
  );
}

/** Native radio group styled as the Organic segmented control. */
export function Segmented<T extends string | number>({ options, value, onChange, label, className }: {
  options: { id: T; label: ReactNode }[]; value: T; onChange: (v: T) => void; label: string; className?: string;
}) {
  const name = useId();
  return (
    <div role="radiogroup" aria-label={label} className={cn('flex min-h-12 overflow-hidden rounded-pill border border-divider', className)}>
      {options.map((o, i) => (
        <label key={String(o.id)} className={cn('flex flex-1 cursor-pointer items-center justify-center whitespace-nowrap px-3 text-sm has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:-outline-offset-2 has-[:focus-visible]:outline-accent-700',
          i > 0 && 'border-s border-divider', value === o.id ? 'bg-accent font-semibold text-on-accent' : 'hover:bg-neutral-200')}>
          <input type="radio" className="sr-only" name={name} checked={value === o.id} onChange={() => onChange(o.id)} />
          {o.label}
        </label>
      ))}
    </div>
  );
}

/** Pick one number from a small range (1–5 scales, 0–10 pain, days per week). */
export function ScalePicker({ values, value, onChange, label, dangerFrom, size = 'md' }: {
  values: number[]; value: number | undefined; onChange: (v: number) => void; label: string; dangerFrom?: number; size?: 'md' | 'lg';
}) {
  const cols = values.length > 6 ? 6 : values.length;
  return (
    <div role="radiogroup" aria-label={label} className="grid gap-2" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0,1fr))` }}>
      {values.map((v) => (
        <button key={v} type="button" role="radio" aria-checked={value === v} onClick={() => onChange(v)}
          className={cn('grid place-items-center rounded-pill text-[15px] font-semibold tabular transition-colors', size === 'lg' ? 'h-14' : 'h-12',
            value === v ? 'bg-accent font-bold text-on-accent' : cn('bg-surface hover:bg-neutral-300', dangerFrom !== undefined && v >= dangerFrom ? 'text-warn-700' : 'text-ink'))}>
          {v}
        </button>
      ))}
    </div>
  );
}

export function NumberStepper({ value, onChange, step = 1, min, max, unit, label, digits = 0, size = 'md' }: {
  value: number; onChange: (v: number) => void; step?: number; min?: number; max?: number; unit?: string; label: string; digits?: number; size?: 'md' | 'lg';
}) {
  const { t, num } = useI18n();
  const clamp = (v: number) => Math.max(min ?? -Infinity, Math.min(max ?? Infinity, Math.round(v * 100) / 100));
  const btn = cn('grid place-items-center rounded-pill text-ink hover:bg-neutral-200', size === 'lg' ? 'h-14 w-14 bg-bg' : 'h-12 w-12');
  return (
    <div className={cn('flex items-center rounded-pill border border-divider bg-surface', size === 'lg' && 'border-0 bg-transparent')} aria-label={label} role="group">
      <button type="button" className={btn} aria-label={t('common.decrease', { label })} onClick={() => onChange(clamp(value - step))}><Icon as={Minus} /></button>
      <output className={cn('flex-1 text-center font-bold tabular', size === 'lg' ? 'font-heading text-[34px] font-normal' : 'text-lg')} aria-live="polite">
        {num(value, digits)} {unit && <span className="text-[13px] font-normal text-neutral-700">{unit}</span>}
      </output>
      <button type="button" className={btn} aria-label={t('common.increase', { label })} onClick={() => onChange(clamp(value + step))}><Icon as={Plus} /></button>
    </div>
  );
}

export function Slider({ value, onChange, min, max, step = 1, label, tone = 'sage' }: {
  value: number; onChange: (v: number) => void; min: number; max: number; step?: number; label: string; tone?: 'sage' | 'accent';
}) {
  return (
    <input type="range" aria-label={label} min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))}
      className={cn('h-tap w-full cursor-pointer', tone === 'sage' ? 'accent-sage-600' : 'accent-accent')} />
  );
}

export function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: ReactNode }) {
  return (
    <button type="button" role="switch" aria-checked={checked} onClick={() => onChange(!checked)}
      className="inline-flex min-h-8 items-center gap-2 text-xs text-neutral-800">
      <span className={cn('relative h-[18px] w-[30px] shrink-0 rounded-pill transition-colors', checked ? 'bg-sage-600' : 'bg-neutral-400')}>
        <span className={cn('absolute top-0.5 h-3.5 w-3.5 rounded-full bg-bg transition-all', checked ? 'start-[14px]' : 'start-0.5')} />
      </span>
      {label}
    </button>
  );
}

export function Checkbox({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button type="button" role="checkbox" aria-checked={checked} aria-label={label} onClick={() => onChange(!checked)}
      className="grid h-tap w-tap shrink-0 place-items-center">
      <span className={cn('grid h-6 w-6 place-items-center rounded-sm', checked ? 'bg-sage-600 text-bg' : 'border-2 border-neutral-500')}>
        {checked && <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5" /></svg>}
      </span>
    </button>
  );
}

export function Tabs<T extends string>({ tabs, value, onChange, label }: { tabs: { id: T; label: string }[]; value: T; onChange: (v: T) => void; label: string }) {
  return (
    <div role="tablist" aria-label={label} className="flex rounded-pill bg-surface p-1">
      {tabs.map((tab) => (
        <button key={tab.id} role="tab" aria-selected={value === tab.id} type="button" onClick={() => onChange(tab.id)}
          className={cn('min-h-tap flex-1 whitespace-nowrap rounded-pill px-3', value === tab.id ? 'bg-bg font-bold shadow-sm' : 'font-semibold text-neutral-700 hover:text-ink')}>
          {tab.label}
        </button>
      ))}
    </div>
  );
}
