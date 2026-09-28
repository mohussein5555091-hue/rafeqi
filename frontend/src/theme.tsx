import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

type Theme = 'light' | 'dark' | 'system';
const KEY = 'rafeqi.theme';
const ThemeContext = createContext<{ theme: Theme; setTheme: (t: Theme) => void; isDark: boolean } | null>(null);

// Storage can throw (private windows, blocked site data), so the theme must work without it.
const read = (): Theme => {
  try { const v = localStorage.getItem(KEY); return v === 'light' || v === 'dark' ? v : 'system'; } catch { return 'system'; }
};
const write = (t: Theme) => { try { localStorage.setItem(KEY, t); } catch { /* not remembered, still applied */ } };

/** Defaults to the device setting ("system") until the person picks one; the choice is remembered. */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(read);
  const [systemDark, setSystemDark] = useState(() => window.matchMedia('(prefers-color-scheme: dark)').matches);
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => setSystemDark(mq.matches);
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, []);
  const isDark = theme === 'dark' || (theme === 'system' && systemDark);
  useEffect(() => { document.documentElement.classList.toggle('dark', isDark); }, [isDark]);
  useEffect(() => { write(theme); }, [theme]);
  return <ThemeContext.Provider value={{ theme, setTheme, isDark }}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used inside <ThemeProvider>');
  return ctx;
}
