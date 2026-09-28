import type { KeyboardEvent, ReactElement } from 'react';
import { useI18n } from '@/i18n';
import type { BodyRegion } from '@/types';

export type RegionState = 'none' | 'select' | 'attn' | 'warn' | 'ok' | 'muscle' | 'muscle2';

const fills: Record<RegionState, [string, string]> = {
  none: ['var(--color-neutral-300)', 'var(--color-neutral-500)'],
  select: ['var(--color-accent-300)', 'var(--color-accent-600)'],
  attn: ['var(--color-accent-200)', 'var(--color-accent-500)'],
  warn: ['var(--color-warn-200)', 'var(--color-warn-600)'],
  ok: ['var(--color-accent-2-200)', 'var(--color-accent-2-600)'],
  muscle: ['var(--color-accent-2-400)', 'var(--color-accent-2-700)'],
  muscle2: ['var(--color-accent-2-200)', 'var(--color-accent-2-500)'],
};

type Shape = { k: string; paired?: boolean; c?: { cx: number; cy: number; r: number }; r?: { x: number; y: number; w: number; h: number } };
// Geometry drawn for the viewer's left half; paired regions are mirrored.
const shapes = (front: boolean): Shape[] => [
  { k: 'head', c: { cx: 100, cy: 34, r: 22 } },
  { k: 'neck', r: { x: 91, y: 58, w: 18, h: 14 } },
  { k: front ? 'chest' : 'upperBack', r: { x: 72, y: 76, w: 56, h: 58 } },
  { k: front ? 'abdomen' : 'lowerBack', r: { x: 74, y: 138, w: 52, h: 50 } },
  { k: 'shoulder', paired: true, c: { cx: 60, cy: 90, r: 15 } },
  { k: 'arm', paired: true, r: { x: 40, y: 106, w: 20, h: 58 } },
  { k: 'forearm', paired: true, r: { x: 32, y: 168, w: 18, h: 62 } },
  { k: 'hip', paired: true, r: { x: 73, y: 192, w: 26, h: 34 } },
  { k: 'thigh', paired: true, r: { x: 73, y: 230, w: 26, h: 72 } },
  { k: 'knee', paired: true, c: { cx: 86, cy: 314, r: 12 } },
  { k: 'shin', paired: true, r: { x: 75, y: 330, w: 22, h: 58 } },
  { k: 'ankle', paired: true, r: { x: 75, y: 392, w: 22, h: 16 } },
];

/**
 * Tappable front/back body map. Front view shows the user's right side on the
 * viewer's left (like a mirror facing you). Pair with a list of chips so every
 * region is also reachable with a 44px target.
 */
export function BodyMap({ view, marks = {}, onToggle, width = 150, showLabels = true }: {
  view: 'front' | 'back'; marks?: Partial<Record<BodyRegion, RegionState>>; onToggle?: (r: BodyRegion) => void; width?: number; showLabels?: boolean;
}) {
  const { t } = useI18n();
  const front = view === 'front';
  const items: { id: BodyRegion; el: ReactElement }[] = [];
  for (const s of shapes(front)) {
    for (const mirror of s.paired ? [false, true] : [false]) {
      const viewerLeft = !mirror;
      const id = (s.paired ? s.k + ((front ? viewerLeft : !viewerLeft) ? 'R' : 'L') : s.k) as BodyRegion;
      const [fill, stroke] = fills[marks[id] ?? 'none'];
      const common = {
        fill, stroke, strokeWidth: marks[id] && marks[id] !== 'none' ? 2.5 : 1.5,
        className: onToggle ? 'cursor-pointer transition-[fill] focus-visible:outline-none' : undefined,
        role: onToggle ? 'button' : undefined, tabIndex: onToggle ? 0 : undefined,
        'aria-label': t(`body.${id}`), 'aria-pressed': onToggle ? marks[id] === 'select' : undefined,
        onClick: onToggle ? () => onToggle(id) : undefined,
        onKeyDown: onToggle ? (e: KeyboardEvent) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onToggle(id); } } : undefined,
      };
      const el = s.c
        ? <circle cx={mirror ? 200 - s.c.cx : s.c.cx} cy={s.c.cy} r={s.c.r} {...common}><title>{t(`body.${id}`)}</title></circle>
        : <rect x={mirror ? 200 - s.r!.x - s.r!.w : s.r!.x} y={s.r!.y} width={s.r!.w} height={s.r!.h} rx={Math.min(s.r!.w, s.r!.h) / 2} {...common}><title>{t(`body.${id}`)}</title></rect>;
      items.push({ id, el });
    }
  }
  return (
    <figure className="m-0 shrink-0" style={{ width }}>
      <svg viewBox="0 0 200 420" className="block h-auto w-full overflow-visible" aria-label={t(front ? 'body.frontView' : 'body.backView')}>
        {items.map((i) => <g key={i.id}>{i.el}</g>)}
      </svg>
      {showLabels && (
        <figcaption dir="ltr" className="mt-1 flex items-center justify-between px-1.5 text-[11px] font-bold text-neutral-700">
          <span>{t(front ? 'body.rightShort' : 'body.leftShort')}</span>
          <span className="font-semibold">{t(front ? 'body.front' : 'body.back')}</span>
          <span>{t(front ? 'body.leftShort' : 'body.rightShort')}</span>
        </figcaption>
      )}
    </figure>
  );
}
