import { useEffect, useState } from 'react';
import { Dumbbell, Pause, Play } from 'lucide-react';
import { cn, Icon } from './Button';
import { useI18n } from '@/i18n';
import type { Exercise } from '@/types';

const framesOf = (ex: Pick<Exercise, 'imageUrl' | 'imageFrames'>) => (ex.imageUrl ? [ex.imageUrl, ...(ex.imageFrames ?? [])] : []);
const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/**
 * Demonstration at the top of the exercise page. Start/end photos crossfade in a loop like a GIF.
 * Stays still when the device asks for reduced motion; the pause button covers everyone else.
 */
export function ExerciseMedia({ ex, className }: { ex: Exercise; className?: string }) {
  const { t, l } = useI18n();
  const frames = framesOf(ex);
  const [playing, setPlaying] = useState(() => frames.length > 1 && !reducedMotion());
  const [frame, setFrame] = useState(0);
  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(() => setFrame((f) => (f + 1) % frames.length), 1200);
    return () => clearInterval(timer);
  }, [playing, frames.length]);

  if (!frames.length) {
    return (
      <div className={cn('washed relative grid place-items-center overflow-hidden rounded-card bg-sage-200', className)} aria-label={t('exercise.media')}>
        <span className="relative flex flex-col items-center gap-2 text-sage-900"><span className="grid h-16 w-16 place-items-center rounded-full bg-bg"><Icon as={Dumbbell} size={26} /></span><span className="text-[12.5px] font-semibold">{t('exercise.noMedia')}</span></span>
      </div>
    );
  }
  return (
    <figure className={cn('relative m-0 overflow-hidden rounded-card bg-neutral-100', className)}>
      {frames.map((src, i) => (
        <img key={src} src={src} alt={i === 0 ? t('exercise.mediaAlt', { name: l(ex.name) }) : ''} aria-hidden={i !== 0}
          className={cn('absolute inset-0 h-full w-full object-cover transition-opacity duration-500', i === frame ? 'opacity-100' : 'opacity-0')} />
      ))}
      {frames.length > 1 && (
        <button type="button" onClick={() => setPlaying(!playing)} aria-label={t(playing ? 'exercise.pause' : 'exercise.play')}
          className="absolute bottom-3 end-3 grid h-tap w-tap place-items-center rounded-full bg-bg/90 text-ink shadow-sm hover:bg-bg">
          <Icon as={playing ? Pause : Play} size={18} />
        </button>
      )}
    </figure>
  );
}

/** Small square thumbnail for exercise rows. Shows the exercise's number when given. */
export function ExerciseThumb({ ex, n, size = 56 }: { ex?: Pick<Exercise, 'imageUrl'>; n?: number; size?: number }) {
  return (
    <span className="relative shrink-0" style={{ width: size, height: size }}>
      {ex?.imageUrl
        ? <img src={ex.imageUrl} alt="" loading="lazy" className="h-full w-full rounded-lg bg-neutral-100 object-cover" />
        : <span className="grid h-full w-full place-items-center rounded-lg bg-sage-200 text-sage-800"><Icon as={Dumbbell} size={size / 2.6} /></span>}
      {n !== undefined && <span className="absolute -start-1.5 -top-1.5 grid h-6 w-6 place-items-center rounded-full border-2 border-surface bg-bg text-[11.5px] font-bold">{n}</span>}
    </span>
  );
}
