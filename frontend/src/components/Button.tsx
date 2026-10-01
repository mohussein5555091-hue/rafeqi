import type { LucideIcon } from 'lucide-react';
import { Link, type LinkProps } from 'react-router-dom';
import type { ButtonHTMLAttributes, ReactNode } from 'react';

export const cn = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(' ');

/** Lucide at the system's heavier 2.75 stroke. `flip` mirrors directional icons in RTL. */
export function Icon({ as: C, size = 20, flip, className }: { as: LucideIcon; size?: number; flip?: boolean; className?: string }) {
  return <C size={size} strokeWidth={2.75} aria-hidden className={cn('shrink-0', flip && 'rtl:-scale-x-100', className)} />;
}

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'inverse';
type Size = 'sm' | 'md' | 'lg' | 'icon';

const variants: Record<Variant, string> = {
  primary: 'bg-accent text-on-accent hover:bg-accent-600 active:bg-accent-600 hover:text-on-accent',
  secondary: 'border border-divider text-ink hover:bg-neutral-200 active:bg-neutral-300 hover:text-ink',
  ghost: 'text-accent-700 hover:bg-accent-100 active:bg-accent-200',
  danger: 'border border-warn-300 text-warn-700 hover:bg-warn-100 hover:text-warn-700',
  inverse: 'bg-bg text-ink hover:bg-neutral-100 hover:text-ink',
};
const sizes: Record<Size, string> = {
  sm: 'min-h-tap px-4 text-sm',
  md: 'h-12 px-5 text-[15px]',
  lg: 'h-[54px] px-6 text-[17px]',
  icon: 'h-tap w-tap p-0',
};

export const buttonClass = (variant: Variant = 'primary', size: Size = 'md', block = false) =>
  cn('inline-flex items-center justify-center gap-2 rounded-pill font-heading whitespace-nowrap no-underline transition-colors',
    'disabled:cursor-not-allowed disabled:opacity-45', variants[variant], sizes[size], block && 'w-full');

interface Common { variant?: Variant; size?: Size; block?: boolean; icon?: LucideIcon; iconFlip?: boolean; children?: ReactNode }

export function Button({ variant, size, block, icon, iconFlip, children, className, type = 'button', ...rest }: Common & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button type={type} className={cn(buttonClass(variant, size, block), className)} {...rest}>
      {icon && <Icon as={icon} size={size === 'lg' ? 20 : 18} flip={iconFlip} />}
      {children}
    </button>
  );
}

export function LinkButton({ variant, size, block, icon, iconFlip, children, className, ...rest }: Common & LinkProps) {
  return (
    <Link className={cn(buttonClass(variant, size, block), className)} {...rest}>
      {icon && <Icon as={icon} size={size === 'lg' ? 20 : 18} flip={iconFlip} />}
      {children}
    </Link>
  );
}
