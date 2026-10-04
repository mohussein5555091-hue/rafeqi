import { useState, type FormEvent, type ReactNode } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { CircleAlert, Check, Info } from 'lucide-react';
import { Button, Field, Icon, PageControls, PasswordInput, TextInput, cn } from '@/components';
import { useI18n } from '@/i18n';
import { useSession } from '@/data/session';
import { ApiError } from '@/data/api';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

/** Split layout: brand panel on desktop, single column on mobile. */
export function AuthLayout({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <section className="relative hidden flex-col justify-between overflow-hidden bg-surface px-16 py-14 lg:flex">
        <div className="flex items-center gap-3">
          <span className="grid h-12 w-12 place-items-center rounded-full bg-accent font-heading text-2xl text-on-accent">{t('brand.mark')}</span>
          <span className="font-heading text-[28px]">{t('brand.name')}</span>
        </div>
        <span aria-hidden className="absolute -end-40 top-44 h-[520px] w-[520px] rounded-full bg-sage-300" />
        <span aria-hidden className="absolute end-56 top-[420px] h-[300px] w-[300px] rounded-full bg-accent-200" />
        <div className="relative max-w-[480px]"><h2 className="m-0 mb-4 text-[56px]">{t('auth.heroTitle')}</h2><p className="m-0 text-lg text-neutral-800">{t('auth.tagline')}</p></div>
        <p className="relative m-0 flex gap-1.5 text-[13px] text-neutral-700"><Icon as={Info} size={15} />{t('common.disclaimerShort')}</p>
      </section>
      <section className="flex flex-col px-6 pb-8 pt-4 lg:px-16 lg:py-10">
        <div className="flex justify-end"><PageControls /></div>
        <div className="mx-auto flex w-full max-w-[420px] flex-1 flex-col justify-center gap-5 py-6">{children}</div>
      </section>
    </div>
  );
}

function BrandIntro() {
  const { t } = useI18n();
  return (
    <div className="flex flex-col gap-4 lg:hidden">
      <div aria-hidden className="relative h-32">
        <span className="absolute start-0 top-0 h-28 w-28 rounded-full bg-accent-200" />
        <span className="absolute start-20 top-10 h-20 w-20 rounded-full bg-sage-300" />
        <span className="absolute start-7 top-7 grid h-16 w-16 place-items-center rounded-full bg-accent font-heading text-[34px] text-on-accent">{t('brand.mark')}</span>
      </div>
      <div><h1 className="m-0 mb-2 text-[38px]">{t('brand.name')}</h1><p className="m-0 text-base text-neutral-800">{t('auth.tagline')}</p></div>
    </div>
  );
}

export function Login() {
  const { t } = useI18n();
  const { login } = useSession();
  const nav = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from ?? '/';
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<{ email?: string; password?: string; form?: string }>({});
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const next = {
      email: !EMAIL_RE.test(email) ? t('auth.errors.email') : undefined,
      password: !password ? t('auth.errors.passwordRequired') : undefined,
    };
    setErrors(next);
    if (next.email || next.password) return;
    setBusy(true);
    try { await login(email, password); nav(from, { replace: true }); }
    catch { setErrors({ form: t('auth.errors.invalid') }); }
    finally { setBusy(false); }
  };

  return (
    <AuthLayout>
      <BrandIntro />
      <h2 className="m-0 hidden text-[38px] lg:block">{t('auth.login')}</h2>
      {errors.form && <div role="alert" className="flex items-start gap-3 rounded-lg bg-warn-100 px-4 py-3.5 text-sm text-warn-800"><Icon as={CircleAlert} />{errors.form}</div>}
      <form onSubmit={submit} noValidate className="flex flex-col gap-4">
        <Field label={t('auth.email')} htmlFor="email" error={errors.email}>
          <TextInput id="email" type="email" autoComplete="email" dir="ltr" className="text-start" value={email} invalid={!!errors.email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label={t('auth.password')} htmlFor="password" error={errors.password}>
          <PasswordInput id="password" autoComplete="current-password" value={password} invalid={!!errors.password} onChange={(e) => setPassword(e.target.value)} placeholder={t('auth.passwordPlaceholder')} />
        </Field>
        <Link to="/forgot-password" className="flex min-h-tap items-center self-end text-sm font-semibold">{t('auth.forgot')}</Link>
        <Button type="submit" size="lg" disabled={busy}>{t('auth.login')}</Button>
        <Link to="/signup" className={cn('inline-flex h-[54px] items-center justify-center rounded-pill border border-divider font-heading text-base text-ink no-underline hover:bg-neutral-200 hover:text-ink')}>{t('auth.createAccount')}</Link>
      </form>
      <p className="m-0 flex gap-1.5 text-xs text-neutral-700 lg:hidden"><Icon as={Info} size={14} />{t('common.disclaimerShort')}</p>
    </AuthLayout>
  );
}

export function SignUp() {
  const { t } = useI18n();
  const { signup } = useSession();
  const nav = useNavigate();
  const [form, setForm] = useState({ firstName: '', email: '', password: '' });
  const [consent, setConsent] = useState(false);
  const [errors, setErrors] = useState<Record<string, string | undefined>>({});
  const [busy, setBusy] = useState(false);
  const rules = { len: form.password.length >= 8, num: /\d/.test(form.password) };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const next = {
      firstName: !form.firstName.trim() ? t('auth.errors.firstName') : undefined,
      email: !EMAIL_RE.test(form.email) ? t('auth.errors.email') : undefined,
      password: !(rules.len && rules.num) ? t('auth.errors.passwordRules') : undefined,
      consent: !consent ? t('auth.errors.consent') : undefined,
    };
    setErrors(next);
    if (Object.values(next).some(Boolean)) return;
    setBusy(true);
    try {
      await signup(form);
      nav('/onboarding/about');
    } catch (err) {
      const taken = err instanceof ApiError && err.message === 'email_taken';
      setErrors(taken ? { email: t('auth.errors.emailTaken') } : { form: t('auth.errors.failed') });
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout>
      <div><h1 className="m-0 mb-2 text-[34px]">{t('auth.signupTitle')}</h1><p className="m-0 text-neutral-800">{t('auth.signupSub')}</p></div>
      <form onSubmit={submit} noValidate className="flex flex-col gap-4">
        <Field label={t('auth.firstName')} htmlFor="fn" error={errors.firstName}><TextInput id="fn" autoComplete="given-name" value={form.firstName} invalid={!!errors.firstName} onChange={(e) => setForm({ ...form, firstName: e.target.value })} /></Field>
        <Field label={t('auth.email')} htmlFor="em" error={errors.email}><TextInput id="em" type="email" dir="ltr" className="text-start" autoComplete="email" value={form.email} invalid={!!errors.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
        <Field label={t('auth.password')} htmlFor="pw" error={errors.password}>
          <PasswordInput id="pw" autoComplete="new-password" value={form.password} invalid={!!errors.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          <div className="flex gap-3.5 text-[12.5px]">
            {([['len', 'auth.rule8'], ['num', 'auth.ruleNumber']] as const).map(([k, key]) => (
              <span key={k} className={cn('flex items-center gap-1', rules[k] ? 'text-sage-800' : 'text-neutral-700')}><Icon as={Check} size={14} />{t(key)}</span>
            ))}
          </div>
        </Field>
        <label className="flex min-h-tap cursor-pointer items-start gap-3 text-sm">
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-0.5 h-6 w-6 shrink-0 accent-accent" />
          <span>{t('auth.consent')}</span>
        </label>
        {errors.consent && <span role="alert" className="text-[13px] text-warn-700">{errors.consent}</span>}
        {errors.form && <span role="alert" className="text-[13px] text-warn-700">{errors.form}</span>}
        <Button type="submit" size="lg" disabled={busy}>{t('auth.createAccountCta')}</Button>
        <Link to="/login" className="self-center text-sm font-semibold">{t('auth.haveAccount')}</Link>
      </form>
    </AuthLayout>
  );
}

/** Email reset isn't built yet: explains how to get a new password for now (admin: npm run reset-password). */
export function ForgotPassword() {
  const { t } = useI18n();
  return (
    <AuthLayout>
      <h1 className="m-0 text-[34px]">{t('auth.forgotTitle')}</h1>
      <div role="note" className="flex items-start gap-3 rounded-lg bg-accent-100 px-4 py-3.5 text-[14.5px] text-accent-900">
        <Icon as={Info} className="mt-0.5 text-accent-700" />
        <span className="flex flex-col gap-1"><strong>{t('auth.resetLaterTitle')}</strong><span>{t('auth.resetLaterBody')}</span></span>
      </div>
      <Link to="/login" className="self-center text-sm font-semibold">{t('auth.backToLogin')}</Link>
    </AuthLayout>
  );
}
