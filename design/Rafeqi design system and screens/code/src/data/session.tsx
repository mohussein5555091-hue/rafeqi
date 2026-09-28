import { createContext, useContext, useState, type ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import type { User } from '@/types';
import { api } from './api';

interface Session {
  user: User | null;
  checkInDue: boolean;
  login: (email: string, password: string) => Promise<User>;
  signup: (input: { firstName: string; email: string; password: string }) => Promise<User>;
  logout: () => Promise<void>;
}

const SessionContext = createContext<Session | null>(null);
const KEY = 'rafeqi.session';

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as User) : null;
  });
  const keep = (u: User | null) => { setUser(u); u ? localStorage.setItem(KEY, JSON.stringify(u)) : localStorage.removeItem(KEY); };

  const value: Session = {
    user,
    checkInDue: true, // backend: derive from next check-in date
    login: async (e, p) => { const u = await api.login(e, p); keep(u); return u; },
    signup: async (input) => { const u = await api.signup(input); keep(u); return u; },
    logout: async () => { await api.logout(); keep(null); },
  };
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSession must be used inside <SessionProvider>');
  return ctx;
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user } = useSession();
  const loc = useLocation();
  if (!user) return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  return <>{children}</>;
}
