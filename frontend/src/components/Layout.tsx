import type { ReactNode } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import {
  ArrowLeft, Bandage, ChartLine, ClipboardCheck, Dumbbell, House, Moon, NotebookPen, Salad, Settings, ShoppingBasket, Sun,
} from 'lucide-react';
import { Button, cn, Icon } from './Button';
import { StepProgress } from './Card';
import { Disclaimer } from './Feedback';
import { useI18n } from '@/i18n';
import { useTheme } from '@/theme';
import { useSession } from '@/data/session';

export function LanguageSwitch({ className }: { className?: string }) {
  const { lang, setLang, t } = useI18n();
  return (
    <button type="button" onClick={() => setLang(lang === 'en' ? 'ar' : 'en')} aria-label={t('common.switchLanguage')}
      className={cn('min-h-tap min-w-tap shrink-0 rounded-pill border border-divider px-3 text-[13px] font-semibold hover:bg-neutral-200', className)}>
      {t('common.otherLanguage')}
    </button>
  );
}

/** Light/dark toggle. aria-pressed tells screen readers whether dark mode is on. */
export function ThemeSwitch({ className }: { className?: string }) {
  const { isDark, setTheme } = useTheme();
  const { t } = useI18n();
  return <Button variant="secondary" size="icon" className={className} aria-label={t('common.toggleTheme')} aria-pressed={isDark} data-testid="theme-toggle"
    icon={isDark ? Sun : Moon} onClick={() => setTheme(isDark ? 'light' : 'dark')} />;
}

/** Language + theme controls shown in every page header. */
export function PageControls({ className }: { className?: string }) {
  return <div className={cn('flex shrink-0 items-center gap-2', className)}><LanguageSwitch /><ThemeSwitch /></div>;
}

const MAIN_TABS: { to: string; key: string; icon: LucideIcon }[] = [
  { to: '/', key: 'home', icon: House },
  { to: '/workouts', key: 'workouts', icon: Dumbbell },
  { to: '/nutrition', key: 'nutrition', icon: Salad },
  { to: '/groceries', key: 'groceries', icon: ShoppingBasket },
  { to: '/progress', key: 'progress', icon: ChartLine },
];
const EXTRA: { to: string; key: string; icon: LucideIcon }[] = [
  { to: '/check-in', key: 'checkIn', icon: ClipboardCheck },
  { to: '/reviews', key: 'reviews', icon: NotebookPen },
  { to: '/injuries', key: 'injuries', icon: Bandage },
  { to: '/profile', key: 'profile', icon: Settings },
];

/** Mobile bottom navigation. No chat, no "Ask" tab. */
export function TabBar() {
  const { t } = useI18n();
  const { checkInDue } = useSession();
  return (
    <nav aria-label={t('nav.main')} className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t border-divider bg-surface px-2 pb-[max(env(safe-area-inset-bottom),14px)] pt-2 lg:hidden">
      {MAIN_TABS.map((tab) => (
        <NavLink key={tab.to} to={tab.to} end={tab.to === '/'}
          className={({ isActive }) => cn('flex min-h-[52px] flex-col items-center gap-0.5 text-[11.5px] no-underline', isActive ? 'font-bold text-accent-700' : 'font-medium text-neutral-700 hover:text-ink')}>
          {({ isActive }) => (
            <>
              <span className={cn('relative grid h-[30px] w-[58px] place-items-center rounded-pill', isActive && 'bg-accent-200')}>
                <Icon as={tab.icon} size={21} />
                {tab.key === 'home' && checkInDue && <span aria-label={t('nav.checkInDue')} className="absolute end-2.5 top-0.5 h-2.5 w-2.5 rounded-full border-2 border-surface bg-accent" />}
              </span>
              {t(`nav.${tab.key}`)}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}

/** Desktop left sidebar (logical "start" edge, so it moves right in Arabic). */
export function Sidebar() {
  const { t, l } = useI18n();
  const { user, checkInDue } = useSession();
  return (
    <aside className="sticky top-0 hidden h-screen w-[248px] shrink-0 flex-col gap-6 bg-surface px-4 py-6 lg:flex">
      <Link to="/" className="flex items-center gap-2.5 px-2 text-ink no-underline">
        <span className="grid h-10 w-10 place-items-center rounded-full bg-accent font-heading text-xl text-on-accent">{t('brand.mark')}</span>
        <span className="font-heading text-[22px]">{t('brand.name')}</span>
      </Link>
      <nav aria-label={t('nav.main')} className="flex flex-col gap-1">
        {[...MAIN_TABS, ...EXTRA].map((item) => (
          <NavLink key={item.to} to={item.to} end={item.to === '/'}
            className={({ isActive }) => cn('flex min-h-tap items-center gap-3 rounded-pill px-3.5 text-[14.5px] no-underline', isActive ? 'bg-accent-200 font-bold text-accent-800' : 'font-medium text-ink hover:bg-neutral-200 hover:text-ink')}>
            <Icon as={item.icon} />
            <span className="flex-1 whitespace-nowrap">{t(`nav.${item.key}`)}</span>
            {item.key === 'checkIn' && checkInDue && <span className="rounded-pill bg-accent px-2.5 py-0.5 text-[11px] font-bold text-on-accent">{t('nav.due')}</span>}
          </NavLink>
        ))}
      </nav>
      <div className="mt-auto flex flex-col gap-3">
        <div className="flex gap-2"><LanguageSwitch className="flex-1" /><ThemeSwitch /></div>
        {user && (
          <Link to="/profile" className="flex items-center gap-2.5 rounded-pill bg-bg p-2 text-ink no-underline">
            <span className="grid h-10 w-10 place-items-center rounded-full bg-sage-200 font-heading text-lg text-sage-800">{l(user.firstName).charAt(0)}</span>
            <span className="flex flex-col leading-tight"><strong className="text-sm">{l(user.firstName)} {l(user.lastName)}</strong><span className="text-xs text-neutral-700">{t(`enums.experience.${user.experience}`)} · {t('common.daysPerWeek', { n: user.daysPerWeek })}</span></span>
          </Link>
        )}
        <Disclaimer className="px-2" />
      </div>
    </aside>
  );
}

export function AppBar({ title, sub, back, actions }: { title: string; sub?: string; back?: boolean; actions?: ReactNode }) {
  const { t, l } = useI18n();
  const { user } = useSession();
  const nav = useNavigate();
  return (
    <header className="flex min-h-[64px] items-center gap-2.5 px-4 pb-2.5 pt-3 lg:px-10 lg:pb-4 lg:pt-8">
      {back && <Button variant="secondary" size="icon" icon={ArrowLeft} iconFlip aria-label={t('common.back')} onClick={() => nav(-1)} />}
      <div className="flex min-w-0 flex-1 flex-col">
        {sub && <span className="order-2 text-xs text-neutral-700 lg:order-1 lg:text-sm">{sub}</span>}
        <h1 className="order-1 m-0 line-clamp-2 break-words text-[21px] leading-tight lg:order-2 lg:line-clamp-1 lg:text-[40px]">{title}</h1>
      </div>
      {actions}
      <PageControls className="lg:hidden" />
      {user && (
        <Link to="/profile" aria-label={t('nav.profile')} className="grid h-tap w-tap shrink-0 place-items-center rounded-full bg-sage-200 font-heading text-[17px] text-sage-800 no-underline lg:hidden">
          {l(user.firstName).charAt(0)}
        </Link>
      )}
    </header>
  );
}

/** Signed-in layout: sidebar on desktop, bottom tabs on mobile. */
export function AppShell({ title, sub, back, actions, children, hideTabs }: {
  title: string; sub?: string; back?: boolean; actions?: ReactNode; children: ReactNode; hideTabs?: boolean;
}) {
  return (
    <div className="min-h-screen lg:flex">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <AppBar title={title} sub={sub} back={back} actions={actions} />
        <main className={cn('flex flex-1 flex-col gap-4 px-4 lg:gap-5 lg:px-10 lg:pb-10', hideTabs ? 'pb-8' : 'pb-32')}>{children}</main>
        {!hideTabs && <TabBar />}
      </div>
    </div>
  );
}

/** Multi-step flow layout (onboarding, weekly check-in): progress bar, back/next footer. */
export function FlowShell({ title, step, total, onBack, onNext, nextLabel, nextDisabled, backLabel, children, footerNote, intro }: {
  title: string; step: number; total: number; onBack?: () => void; onNext: () => void; nextLabel?: string; nextDisabled?: boolean;
  backLabel?: string; children: ReactNode; footerNote?: string; intro?: string;
}) {
  const { t } = useI18n();
  const stepLabel = t('common.stepOf', { step, total });
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-xl flex-col">
      <header className="flex items-center gap-2.5 px-5 pb-3 pt-4">
        {onBack && <Button variant="secondary" size="icon" icon={ArrowLeft} iconFlip aria-label={t('common.back')} onClick={onBack} />}
        <div className="flex min-w-0 flex-1 flex-col"><h1 className="m-0 truncate text-[21px]">{title}</h1><span className="text-xs text-neutral-700">{stepLabel}</span></div>
        <PageControls />
      </header>
      <div className="px-5 pb-4"><StepProgress step={step} total={total} label={stepLabel} /></div>
      <main className="flex flex-1 flex-col gap-4 px-5 pb-6">
        {intro && <p className="m-0 text-[15px] text-neutral-800">{intro}</p>}
        {children}
      </main>
      <footer className="sticky bottom-0 flex flex-col gap-1.5 border-t border-divider bg-bg px-5 pb-7 pt-3.5">
        <div className="flex gap-2.5">
          {onBack && <Button variant="secondary" size="md" onClick={onBack}>{backLabel ?? t('common.back')}</Button>}
          <Button className="flex-1" size="md" onClick={onNext} disabled={nextDisabled}>{nextLabel ?? t('common.next')}</Button>
        </div>
        {footerNote && <span className="text-center text-xs text-neutral-700">{footerNote}</span>}
      </footer>
    </div>
  );
}
