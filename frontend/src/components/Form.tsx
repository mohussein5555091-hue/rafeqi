import { useCallback, useEffect, useId, useRef, useState, type InputHTMLAttributes, type MouseEvent as ReactMouseEvent, type PointerEvent as ReactPointerEvent, type ReactNode } from 'react';
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

/** Reads a typed number: "." or "," (or the Arabic ٫) as the decimal point, and Arabic or Persian digits. NaN if it isn't one. */
export function parseNumber(text: string): number {
  const s = text.trim().replace(/[٠-٩]/g, (d) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(d))).replace(/[۰-۹]/g, (d) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(d)))
    .replace(/[,٫]/g, '.');
  return /^\d+(\.\d+)?$|^\d+\.$/.test(s) ? Number(s.replace(/\.$/, '')) : NaN;
}

/** Repeats `fn` while a button is held: once at once, then faster and faster. */
function useHoldRepeat(fn: () => void) {
  const timer = useRef<number>();
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const stop = useCallback(() => { window.clearTimeout(timer.current); timer.current = undefined; }, []);
  const start = useCallback(() => {
    stop();
    fnRef.current();
    let delay = 400;
    const tick = () => { fnRef.current(); delay = Math.max(50, delay * 0.8); timer.current = window.setTimeout(tick, delay); };
    timer.current = window.setTimeout(tick, delay);
  }, [stop]);
  useEffect(() => stop, [stop]);
  return { start, stop };
}

/**
 * A number you can type (tap it: the phone's number keyboard opens, with a decimal point when `digits` > 0), or nudge
 * with − and + (hold to repeat, faster and faster). It can start empty with a placeholder ("e.g. 80").
 * `onChange` gets the typed number (even out of range) or undefined when the field is empty or not a number;
 * the range message shows when the field is left with a value outside `min`–`max`.
 */
export function NumberStepper({ value, onChange, step = 1, min, max, unit, label, digits = 0, size = 'md', placeholder, start, rangeError, id }: {
  value: number | undefined; onChange: (v: number | undefined) => void; step?: number; min?: number; max?: number; unit?: string; label: string;
  digits?: number; size?: 'md' | 'lg'; placeholder?: number; start?: number; rangeError?: (v: number) => string | undefined; id?: string;
}) {
  const { t, num } = useI18n();
  const fmt = (v: number | undefined) => (v === undefined ? '' : num(v, digits).replace(/,/g, ''));
  const [text, setText] = useState(fmt(value));
  const [focused, setFocused] = useState(false);
  const [touched, setTouched] = useState(false);
  const pointer = useRef(false);
  const ownId = useId();
  const inputId = id ?? ownId;
  useEffect(() => { if (!focused) setText(fmt(value)); }, [value, focused]); // eslint-disable-line react-hooks/exhaustive-deps

  const clamp = (v: number) => Math.max(min ?? -Infinity, Math.min(max ?? Infinity, Math.round(v * 100) / 100));
  const valueRef = useRef(value);
  valueRef.current = value;
  const nudge = (dir: 1 | -1) => {
    const cur = valueRef.current;
    const next = cur === undefined ? clamp(start ?? placeholder ?? min ?? 0) : clamp(cur + dir * step);
    valueRef.current = next;
    setTouched(true);
    onChange(next);
  };
  const minus = useHoldRepeat(() => nudge(-1));
  const plus = useHoldRepeat(() => nudge(1));

  const typed = parseNumber(text);
  const outOfRange = !Number.isNaN(typed) && ((min !== undefined && typed < min) || (max !== undefined && typed > max));
  const message = text.trim() === '' || !touched || focused ? undefined
    : Number.isNaN(typed) ? t('common.notANumber', { label })
      : (rangeError?.(typed) ?? (outOfRange ? t('common.range', { label, min: num(min ?? 0, digits), max: num(max ?? 0, digits), unit: unit ?? '' }).trim() : undefined));

  const btn = cn('grid shrink-0 touch-none select-none place-items-center rounded-pill text-ink hover:bg-neutral-200', size === 'lg' ? 'h-14 w-14 bg-bg' : 'h-12 w-12');
  const hold = (h: ReturnType<typeof useHoldRepeat>) => ({
    onPointerDown: (e: ReactPointerEvent) => { if (e.button !== 0) return; pointer.current = true; h.start(); },
    onPointerUp: h.stop, onPointerLeave: h.stop, onPointerCancel: h.stop,
    onClick: () => { if (!pointer.current) h.start(); h.stop(); pointer.current = false; }, // keyboard: one step
    onContextMenu: (e: ReactMouseEvent) => e.preventDefault(),
  });
  return (
    <div className="flex flex-col gap-1.5">
      <div className={cn('flex items-center rounded-pill border bg-surface', message ? 'border-warn-600' : 'border-divider', size === 'lg' && 'border-0 bg-transparent')} aria-label={label} role="group">
        <button type="button" className={btn} aria-label={t('common.decrease', { label })} {...hold(minus)}><Icon as={Minus} /></button>
        <label className="flex min-w-0 flex-1 items-baseline justify-center gap-1" htmlFor={inputId}>
          <input id={inputId} type="text" inputMode={digits > 0 ? 'decimal' : 'numeric'} enterKeyHint="done" autoComplete="off" dir="ltr"
            aria-label={label} aria-invalid={!!message} placeholder={placeholder !== undefined ? t('common.eg', { n: num(placeholder, digits) }) : undefined}
            className={cn('w-full min-w-0 bg-transparent text-center font-bold tabular placeholder:text-[15px] placeholder:font-normal placeholder:text-neutral-600 focus:outline-none',
              size === 'lg' ? 'font-heading text-[34px] font-normal' : 'text-lg')}
            value={text}
            onFocus={(e) => { setFocused(true); e.target.select(); }}
            onBlur={() => { setFocused(false); setTouched(true); }}
            onChange={(e) => {
              setText(e.target.value);
              const v = parseNumber(e.target.value);
              onChange(Number.isNaN(v) ? undefined : v);
            }} />
          {unit && <span className="shrink-0 text-[13px] font-normal text-neutral-700">{unit}</span>}
        </label>
        <button type="button" className={btn} aria-label={t('common.increase', { label })} {...hold(plus)}><Icon as={Plus} /></button>
      </div>
      {message && <span role="alert" className="flex items-center gap-1.5 text-[13px] text-warn-700"><Icon as={CircleAlert} size={14} />{message}</span>}
    </div>
  );
}

/** True when `v` is a number inside min–max (what a NumberStepper accepts). */
export const inRange = (v: number | undefined, min: number, max: number): v is number => v !== undefined && v >= min && v <= max;

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
