import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import en from './en.json';
import ar from './ar.json';
import type { Lang, LocalizedText } from '@/types';

type Dict = Record<string, unknown>;
const dicts: Record<Lang, Dict> = { en, ar };

function lookup(dict: Dict, key: string): unknown {
  return key.split('.').reduce<unknown>((o, k) => (o && typeof o === 'object' ? (o as Dict)[k] : undefined), dict);
}

export interface I18n {
  lang: Lang;
  dir: 'ltr' | 'rtl';
  setLang: (l: Lang) => void;
  /** Translate a key from en.json / ar.json. `{name}` placeholders are replaced from vars. */
  t: (key: string, vars?: Record<string, string | number>) => string;
  /** Pick the current language from backend LocalizedText. */
  l: (text: LocalizedText | undefined) => string;
  num: (n: number, digits?: number) => string;
  egp: (n: number) => string;
  date: (iso: string, opts?: Intl.DateTimeFormatOptions) => string;
}

const I18nContext = createContext<I18n | null>(null);
const STORAGE_KEY = 'rafeqi.lang';

export function I18nProvider({ children, initial }: { children: ReactNode; initial?: Lang }) {
  const [lang, setLangState] = useState<Lang>(() => (localStorage.getItem(STORAGE_KEY) as Lang) || initial || 'en');
  const dir = lang === 'ar' ? 'rtl' : 'ltr';

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = dir;
    localStorage.setItem(STORAGE_KEY, lang);
  }, [lang, dir]);

  const setLang = useCallback((l: Lang) => setLangState(l), []);

  const value = useMemo<I18n>(() => {
    // Western digits in both languages (plans, weights and prices read best that way).
    const locale = lang === 'ar' ? 'ar-EG-u-nu-latn' : 'en-GB';
    const t: I18n['t'] = (key, vars) => {
      const raw = lookup(dicts[lang], key) ?? lookup(dicts.en, key);
      let s = typeof raw === 'string' ? raw : key;
      if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(String(v));
      return s;
    };
    const num: I18n['num'] = (n, digits = 0) =>
      new Intl.NumberFormat(locale, { maximumFractionDigits: digits, minimumFractionDigits: 0 }).format(n);
    return {
      lang, dir, setLang, t,
      l: (text) => (text ? text[lang] || text.en : ''),
      num,
      egp: (n) => t('common.egp', { amount: num(n) }),
      date: (iso, opts = { day: 'numeric', month: 'short' }) =>
        new Intl.DateTimeFormat(locale, { timeZone: 'UTC', ...opts }).format(new Date(iso + 'T00:00:00Z')),
    };
  }, [lang, dir, setLang]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18n {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error('useI18n must be used inside <I18nProvider>');
  return ctx;
}
