import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import type { User } from '@/types';
import { useI18n } from '@/i18n';
import { useTheme } from '@/theme';
import { UNAUTHORIZED_EVENT, api } from './api';

interface Session {
  user: User | null;
  /** false until we know whether the cookie is still a valid login. */
  ready: boolean;
  checkInDue: boolean;
  login: (email: string, password: string) => Promise<User>;
  signup: (input: { firstName: string; email: string; password: string }) => Promise<User>;
  logout: () => Promise<void>;
  /** Reads the account again (after onboarding, a new plan or a check-in). */
  refresh: () => Promise<void>;
}

const SessionContext = createContext<Session | null>(null);
// The last known user, so pages render straight away; the httpOnly cookie is what really keeps you logged in.
const KEY = 'rafeqi.session';

const read = (): User | null => {
  try {
    const u = JSON.parse(localStorage.getItem(KEY) ?? 'null') as User | null;
    return u && typeof u.onboardingComplete === 'boolean' ? u : null; // ignore anything saved by an older version
  } catch { return null; }
};
const write = (u: User | null) => { try { u ? localStorage.setItem(KEY, JSON.stringify(u)) : localStorage.removeItem(KEY); } catch { /* not cached */ } };

export function SessionProvider({ children }: { children: ReactNode }) {
  const { lang, setLang } = useI18n();
  const { theme, setTheme } = useTheme();
  const [user, setUser] = useState<User | null>(read);
  const [ready, setReady] = useState(user !== null);
  const [checkInDue, setCheckInDue] = useState(false);
  const keep = useCallback((u: User | null) => { setUser(u); write(u); }, []);
  const userRef = useRef(user);
  userRef.current = user;

  const loadCheckIn = useCallback((u: User | null) => {
    if (!u?.hasPlan) { setCheckInDue(false); return; }
    api.getNextCheckIn().then((n) => setCheckInDue(n.due), () => setCheckInDue(false));
  }, []);

  const refresh = useCallback(async () => {
    const u = await api.getUser();
    keep(u);
    loadCheckIn(u);
  }, [keep, loadCheckIn]);

  // Check the cookie on every visit; a session that ended sends you back to Log in.
  useEffect(() => {
    refresh().catch(() => undefined).finally(() => setReady(true));
    const onExpired = () => keep(null);
    window.addEventListener(UNAUTHORIZED_EVENT, onExpired);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onExpired);
  }, [keep, refresh]);

  // Language and theme belong to the account: a change on this device is saved to it.
  useEffect(() => {
    if (user && (user.language !== lang || user.theme !== theme)) {
      api.updateUser({ language: lang, theme }).then(keep, () => undefined);
    }
  }, [lang, theme, user, keep]);

  const value: Session = {
    user,
    ready,
    checkInDue,
    login: async (e, p) => {
      const u = await api.login(e, p);
      // Logging in brings back the language and theme saved on the account.
      setLang(u.language);
      setTheme(u.theme);
      keep(u);
      loadCheckIn(u);
      return u;
    },
    signup: async (input) => {
      // A new account starts with the language and theme picked on this device.
      const u = await api.signup(input).then(() => api.updateUser({ language: lang, theme }));
      keep(u);
      return u;
    },
    logout: async () => { await api.logout(); keep(null); },
    refresh,
  };
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSession must be used inside <SessionProvider>');
  return ctx;
}

/** Pages that work before the plan exists. */
const BEFORE_PLAN = /^\/(onboarding|profile)(\/|$)/;

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, ready } = useSession();
  const loc = useLocation();
  if (!user && !ready) return null; // checking the cookie: a moment on the first visit only
  if (!user) return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  // First the questionnaire, then the plan; every other page needs both.
  if (!user.onboardingComplete && !loc.pathname.startsWith('/onboarding')) return <Navigate to="/onboarding" replace />;
  if (user.onboardingComplete && !user.hasPlan && !BEFORE_PLAN.test(loc.pathname)) return <Navigate to="/onboarding/generating" replace />;
  return <>{children}</>;
}
