'use client';
import { useState } from 'react';
import { useAuth } from '../lib/auth';

const LOGO = 'https://storage.googleapis.com/green_excal/carbontrack-logo.png';

export function LoginPage() {
  const { user, login, changePassword } = useAuth();
  const [showForm, setShowForm] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [newPass, setNewPass] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const isFirstLogin = user?.is_first_login;

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) { setError('יש להזין אימייל וסיסמה'); return; }
    setLoading(true); setError('');
    try { await login(email, password); }
    catch (err) { setError(String(err)); }
    setLoading(false);
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPass.length < 4 || newPass === '1234') { setError('סיסמה חייבת להיות לפחות 4 תווים ושונה מ-1234'); return; }
    setLoading(true); setError('');
    try { await changePassword(user!.email, newPass); }
    catch (err) { setError(String(err)); }
    setLoading(false);
  };

  if (isFirstLogin) {
    return (
      <Screen>
        <Card>
          <img src={LOGO} className="w-20 h-20 mx-auto mb-4 object-contain" alt="CarbonTrack" />
          <h2 className="text-xl font-bold text-center text-slate-800 mb-1">הגדרת סיסמה ראשונית</h2>
          <p className="text-sm text-slate-500 text-center mb-6">בחרי סיסמה חדשה לחשבונך</p>
          <form onSubmit={handleChangePassword} className="space-y-4">
            <Field label="סיסמה חדשה">
              <input type="password" value={newPass} onChange={e => setNewPass(e.target.value)}
                className={INPUT} placeholder="לפחות 4 תווים" />
            </Field>
            {error && <ErrorBox>{error}</ErrorBox>}
            <Btn loading={loading}>{loading ? 'מעדכן...' : 'עדכן סיסמה וכנס'}</Btn>
          </form>
        </Card>
      </Screen>
    );
  }

  /* ── Landing ── */
  return (
    <div className="min-h-screen flex flex-col" style={{ background: 'linear-gradient(160deg, #f0fdf4 0%, #ecfdf5 40%, #f8fafc 100%)' }}>

      {/* Top bar */}
      <header className="flex items-center justify-between px-8 py-4">
        <div className="flex items-center gap-2.5">
          <img src={LOGO} className="w-8 h-8 object-contain" alt="CarbonTrack" />
          <span className="font-bold text-slate-800 text-sm">Carbon₂Track</span>
        </div>
        <span className="text-xs text-slate-400">נתיבי ישראל</span>
      </header>

      {/* Hero */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-12 text-center">

        {/* Logo */}
        <div className="relative mb-8">
          <div className="absolute inset-0 rounded-full blur-3xl opacity-30" style={{ background: 'radial-gradient(circle, #10b981, #059669)' }} />
          <img src={LOGO} className="relative w-36 h-36 object-contain drop-shadow-xl" alt="CarbonTrack Logo" />
        </div>

        <h1 className="text-5xl font-black text-slate-900 mb-3 leading-tight">
          Carbon<span style={{ color: '#059669' }}>₂</span>Track
        </h1>
        <p className="text-xl text-slate-600 mb-2 font-medium">מערכת מעקב פליטות פחמן</p>
        <p className="text-slate-400 text-sm mb-10 max-w-md leading-relaxed">
          ניטור, ניתוח וצמצום פליטות CO₂ בפרויקטי תשתית — בזמן אמת, מבוסס BigQuery ו-AI
        </p>

        {/* Feature chips */}
        <div className="flex flex-wrap gap-2 justify-center mb-10">
          {['📊 דאשבורד KPI', '🤖 ניתוח Gemini AI', '⚡ סימולטור What-If', '🗺️ מפת ישראל', '✅ תור סקירה'].map(f => (
            <span key={f} className="text-xs font-medium px-3 py-1.5 rounded-full bg-white border border-slate-200 text-slate-600 shadow-sm">{f}</span>
          ))}
        </div>

        {/* CTA / Login form */}
        {!showForm ? (
          <button onClick={() => setShowForm(true)}
            className="px-10 py-4 rounded-2xl text-white font-bold text-base shadow-lg hover:shadow-xl hover:scale-105 active:scale-100 transition-all"
            style={{ background: 'linear-gradient(135deg, #059669, #10b981)' }}>
            כניסה למערכת ←
          </button>
        ) : (
          <div className="w-full max-w-sm bg-white rounded-3xl shadow-xl border border-slate-100 p-8 text-right mt-2 animate-in"
            style={{ animation: 'fadeSlide 0.2s ease' }}>
            <h2 className="text-lg font-bold text-slate-800 mb-5">כניסה למערכת</h2>
            <form onSubmit={handleLogin} className="space-y-4">
              <Field label="אימייל">
                <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                  className={INPUT} placeholder="your@email.com" autoComplete="email" dir="ltr" autoFocus />
              </Field>
              <Field label="סיסמה">
                <input type="password" value={password} onChange={e => setPassword(e.target.value)}
                  className={INPUT} placeholder="••••••••" autoComplete="current-password" dir="ltr" />
              </Field>
              {error && <ErrorBox>{error}</ErrorBox>}
              <Btn loading={loading}>{loading ? 'מתחבר...' : 'כניסה →'}</Btn>
              <button type="button" onClick={() => setShowForm(false)}
                className="w-full text-xs text-slate-400 hover:text-slate-600 transition-colors py-1">
                חזרה
              </button>
            </form>
          </div>
        )}
      </main>

      <footer className="text-center text-xs text-slate-300 pb-6">
        Carbon₂Track · נתיבי ישראל · {new Date().getFullYear()}
      </footer>
    </div>
  );
}

/* ── Shared sub-components ── */

function Screen({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center p-4"
      style={{ background: 'linear-gradient(160deg, #f0fdf4 0%, #ecfdf5 40%, #f8fafc 100%)' }}>
      {children}
    </div>
  );
}
function Card({ children }: { children: React.ReactNode }) {
  return <div className="bg-white rounded-3xl shadow-xl border border-slate-100 p-8 w-full max-w-sm">{children}</div>;
}
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-xs font-medium text-slate-500 mb-1.5 block">{label}</label>
      {children}
    </div>
  );
}
function ErrorBox({ children }: { children: React.ReactNode }) {
  return <div className="text-red-500 text-xs bg-red-50 border border-red-100 rounded-xl px-3 py-2">{children}</div>;
}
function Btn({ children, loading }: { children: React.ReactNode; loading: boolean }) {
  return (
    <button type="submit" disabled={loading}
      className="w-full py-3.5 rounded-xl text-white font-semibold text-sm disabled:opacity-60 transition-all hover:opacity-90 active:scale-[0.99]"
      style={{ background: 'linear-gradient(135deg, #059669, #10b981)' }}>
      {children}
    </button>
  );
}

const INPUT = 'w-full text-sm border border-slate-200 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-emerald-400/40 focus:border-emerald-400 bg-slate-50 transition-all';
