import { cn } from './Button';
import { useI18n } from '@/i18n';

// One chart style for the whole app: 3 dashed gridlines, raw entries as hollow
// dots, trend as a 3px line with a 14% area wash, limits as dashed clay-red rules.
// Time always runs left → right, also in Arabic.

export type ChartTone = 'ok' | 'accent' | 'warn' | 'muted';
const toneVar: Record<ChartTone, string> = {
  ok: 'var(--color-accent-2-600)',
  accent: 'var(--color-accent)',
  warn: 'var(--color-warn-600)',
  muted: 'var(--color-neutral-500)',
};

export interface Series {
  values: (number | null)[];
  tone?: ChartTone;
  label?: string;
  dots?: boolean;
  line?: boolean; // false = dots only (raw entries)
  area?: boolean;
  dashed?: boolean;
}

export function LineChart({ series, labels, min, max, height = 160, ticks = 3, unit = '', threshold, legend = true, axisWidth = 36, ariaLabel }: {
  series: Series[]; labels: string[]; min?: number; max?: number; height?: number; ticks?: number; unit?: string;
  threshold?: { value: number; label: string }; legend?: boolean; axisWidth?: number; ariaLabel: string;
}) {
  const { num } = useI18n();
  const all = series.flatMap((s) => s.values.filter((v): v is number => v != null));
  let lo = min ?? Math.floor(Math.min(...all));
  let hi = max ?? Math.ceil(Math.max(...all));
  if (hi <= lo) hi = lo + 1;
  const n = Math.max(...series.map((s) => s.values.length));
  const X = (i: number) => (n < 2 ? 50 : (i / (n - 1)) * 100);
  const Y = (v: number) => 100 - ((v - lo) / (hi - lo)) * 100;
  const tickVals = Array.from({ length: ticks }, (_, i) => hi - ((hi - lo) * i) / (ticks - 1));

  return (
    <figure dir="ltr" className="m-0 flex w-full min-w-0 flex-col gap-2" aria-label={ariaLabel} role="img">
      {legend && series.some((s) => s.label) && (
        <figcaption className="flex flex-wrap gap-3.5 text-xs text-neutral-700">
          {series.filter((s) => s.label).map((s) => (
            <span key={s.label} className="inline-flex items-center gap-1.5">
              <span className="rounded-pill" style={s.line === false
                ? { width: 10, height: 10, border: `2px solid ${toneVar[s.tone ?? 'ok']}` }
                : { width: 16, height: s.dashed ? 2 : 4, background: toneVar[s.tone ?? 'ok'] }} />
              {s.label}
            </span>
          ))}
        </figcaption>
      )}
      <div className="flex min-w-0 gap-2">
        <div className="relative shrink-0 text-[11px] text-neutral-700 tabular" style={{ width: axisWidth, height }}>
          {tickVals.map((v) => (
            <span key={v} className="absolute right-0 -translate-y-1/2 whitespace-nowrap" style={{ top: `${Y(v)}%` }}>{num(v, 1)}{unit}</span>
          ))}
        </div>
        <div className="relative min-w-0 flex-1" style={{ height }}>
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 h-full w-full overflow-visible">
            {tickVals.map((v) => <line key={v} x1="0" x2="100" y1={Y(v)} y2={Y(v)} stroke="var(--color-divider)" strokeDasharray="3 4" vectorEffect="non-scaling-stroke" />)}
            {threshold && <line x1="0" x2="100" y1={Y(threshold.value)} y2={Y(threshold.value)} stroke="var(--color-warn-600)" strokeWidth={1.5} strokeDasharray="6 4" vectorEffect="non-scaling-stroke" />}
            {series.map((s, si) => {
              if (s.line === false) return null;
              const pts = s.values.map((v, i) => (v == null ? null : [X(i), Y(v)] as const)).filter((p): p is readonly [number, number] => !!p);
              if (pts.length < 2) return null;
              const d = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(2)} ${p[1].toFixed(2)}`).join(' ');
              const c = toneVar[s.tone ?? 'ok'];
              return (
                <g key={si}>
                  {s.area && <path d={`${d} L${pts[pts.length - 1][0]} 100 L${pts[0][0]} 100 Z`} fill={`color-mix(in srgb, ${c} 14%, transparent)`} />}
                  <path d={d} fill="none" stroke={c} strokeWidth={s.dashed ? 2 : 3} strokeDasharray={s.dashed ? '5 5' : undefined} strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
                </g>
              );
            })}
          </svg>
          {threshold && (
            <span className="absolute right-0 -translate-y-[120%] whitespace-nowrap text-[10.5px] font-bold text-warn-700" style={{ top: `${Y(threshold.value)}%` }}>{threshold.label}</span>
          )}
          {series.flatMap((s, si) => !s.dots ? [] : s.values.map((v, i) => v == null ? null : (
            <span key={`${si}-${i}`} className="absolute -ms-1 -mt-1 h-2 w-2 rounded-full border-2"
              style={{ left: `${X(i)}%`, top: `${Y(v)}%`, borderColor: toneVar[s.tone ?? 'ok'], background: s.line === false ? 'var(--color-bg)' : toneVar[s.tone ?? 'ok'] }} />
          )))}
        </div>
      </div>
      <div className="flex justify-between gap-1.5 whitespace-nowrap text-[11px] text-neutral-700" style={{ paddingLeft: axisWidth + 8 }}>
        {labels.map((l) => <span key={l}>{l}</span>)}
      </div>
    </figure>
  );
}

/** 7-day rolling average, null until 7 entries exist. */
export const rollingAverage = (vals: number[], window = 7) =>
  vals.map((_, i) => (i < window - 1 ? null : Math.round((vals.slice(i - window + 1, i + 1).reduce((a, b) => a + b, 0) / window) * 100) / 100));

export function MacroRing({ eaten, target, size = 104, label }: { eaten: number; target: number; size?: number; label: string }) {
  const { num } = useI18n();
  const pct = Math.min(100, (eaten / target) * 100);
  return (
    <div className="grid shrink-0 place-items-center rounded-full" style={{ width: size, height: size, background: `conic-gradient(var(--color-accent-2-600) 0 ${pct}%, var(--color-neutral-300) ${pct}% 100%)` }}>
      <div className="flex flex-col items-center justify-center rounded-full bg-surface leading-tight" style={{ width: size - 22, height: size - 22 }}>
        <span className="font-heading text-[22px] tabular">{num(Math.max(0, target - eaten))}</span>
        <span className="text-[11px] text-neutral-700">{label}</span>
      </div>
    </div>
  );
}

export function MacroBars({ rows }: { rows: { label: string; value: string; pct: number; tone: 'sage' | 'accent' | 'neutral' }[] }) {
  const fill = { sage: 'bg-sage-600', accent: 'bg-accent-500', neutral: 'bg-neutral-600' };
  return (
    <div className="flex flex-1 flex-col gap-2.5 text-[12.5px]">
      {rows.map((r) => (
        <div key={r.label}>
          <div className="flex justify-between"><span>{r.label}</span><strong>{r.value}</strong></div>
          <div className="mt-1 h-2 rounded-pill bg-neutral-300"><div className={cn('h-2 rounded-pill', fill[r.tone])} style={{ width: `${Math.min(100, r.pct)}%` }} /></div>
        </div>
      ))}
    </div>
  );
}
