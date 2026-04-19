'use client';
import { useState } from 'react';
import { useAuth } from '../lib/auth';

export function LoginPage() {
  const { user, login, changePassword } = useAuth();
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

  return (
    <div className="min-h-screen flex" style={{ background: '#0f1729' }}>
      {/* Left decorative panel */}
      <div className="hidden lg:flex flex-col justify-between w-1/2 p-12 relative overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #0f1729 0%, #1a2744 50%, #0d2b1a 100%)' }}>
        <div className="absolute inset-0 opacity-20"
          style={{ backgroundImage: 'radial-gradient(circle at 30% 60%, #10b981 0%, transparent 50%), radial-gradient(circle at 70% 20%, #059669 0%, transparent 40%)' }} />
        <div className="relative">
          <div className="flex items-center gap-3 mb-12">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg,#059669,#10b981)' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 22V12M12 12C12 7 7 4 3 6M12 12C12 7 17 4 21 6" />
              </svg>
            </div>
            <div>
              <div className="text-white font-bold text-lg">Carbon₂Track</div>
              <div className="text-white/40 text-xs">נתיבי ישראל</div>
            </div>
          </div>
          <h2 className="text-white text-3xl font-bold leading-tight mb-4">
            מעקב פליטות פחמן<br />בתשתיות לאומיות
          </h2>
          <p className="text-white/50 text-sm leading-relaxed">
            מערכת BI לניטור, ניתוח וצמצום פליטות CO₂ בפרויקטי תשתית — מבוסס על נתוני BigQuery בזמן אמת.
          </p>
        </div>
        <div className="relative space-y-3">
          {[
            { icon: '📊', text: 'דאשבורד KPI בזמן אמת' },
            { icon: '🤖', text: 'ניתוח AI מבוסס Gemini' },
            { icon: '⚡', text: 'סימולטור What-If' },
          ].map(({ icon, text }) => (
            <div key={text} className="flex items-center gap-3 text-sm text-white/60">
              <span className="w-8 h-8 rounded-lg flex items-center justify-center text-base flex-shrink-0"
                style={{ background: 'rgba(255,255,255,0.06)' }}>{icon}</span>
              {text}
            </div>
          ))}
        </div>
      </div>

      {/* Login form */}
      <div className="flex-1 flex items-center justify-center p-8" style={{ background: '#f8fafc' }}>
        <div className="w-full max-w-sm">
          <div className="mb-8 text-center lg:text-right">
            <h1 className="text-2xl font-bold text-slate-900 mb-1">
              {isFirstLogin ? 'הגדרת סיסמה' : 'כניסה למערכת'}
            </h1>
            <p className="text-slate-500 text-sm">
              {isFirstLogin ? 'בחרי סיסמה חדשה לחשבונך' : 'הכנסי את פרטי ההתחברות'}
            </p>
          </div>

          {isFirstLogin ? (
            <form onSubmit={handleChangePassword} className="space-y-4">
              <div>
                <label className="text-xs font-medium text-slate-600 mb-1.5 block">סיסמה חדשה</label>
                <input type="password" value={newPass} onChange={e => setNewPass(e.target.value)}
                  className="w-full text-sm border border-slate-200 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-emerald-400/50 focus:border-emerald-400 bg-white transition-all"
                  placeholder="לפחות 4 תווים" />
              </div>
              {error && (
                <div className="text-red-500 text-xs bg-red-50 border border-red-100 rounded-lg px-3 py-2">{error}</div>
              )}
              <button type="submit" disabled={loading}
                className="w-full py-3 rounded-xl text-white font-semibold text-sm disabled:opacity-60 transition-all hover:opacity-90 active:scale-[0.99]"
                style={{ background: 'linear-gradient(135deg,#059669,#10b981)' }}>
                {loading ? 'מעדכן...' : 'עדכן סיסמה וכנס'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="text-xs font-medium text-slate-600 mb-1.5 block">אימייל</label>
                <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                  className="w-full text-sm border border-slate-200 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-emerald-400/50 focus:border-emerald-400 bg-white transition-all"
                  placeholder="your@email.com" autoComplete="email" dir="ltr" />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600 mb-1.5 block">סיסמה</label>
                <input type="password" value={password} onChange={e => setPassword(e.target.value)}
                  className="w-full text-sm border border-slate-200 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-emerald-400/50 focus:border-emerald-400 bg-white transition-all"
                  placeholder="••••••••" autoComplete="current-password" dir="ltr" />
              </div>
              {error && (
                <div className="text-red-500 text-xs bg-red-50 border border-red-100 rounded-lg px-3 py-2">{error}</div>
              )}
              <button type="submit" disabled={loading}
                className="w-full py-3.5 rounded-xl text-white font-semibold text-sm disabled:opacity-60 transition-all hover:opacity-90 active:scale-[0.99] mt-2"
                style={{ background: 'linear-gradient(135deg,#059669,#10b981)' }}>
                {loading ? 'מתחבר...' : 'כניסה →'}
              </button>
            </form>
          )}

          <p className="text-center text-slate-400 text-[11px] mt-8">Carbon₂Track · נתיבי ישראל · {new Date().getFullYear()}</p>
        </div>
      </div>
    </div>
  );
}
