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
    <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--grad-hero)' }}>
      <div className="bg-white rounded-2xl shadow-elevated p-8 w-full max-w-sm mx-4">
        <div className="text-center mb-6">
          <img src="https://storage.googleapis.com/green_excal/carbontrack-logo.png"
            className="w-24 h-24 mx-auto mb-3 object-contain"
            onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
            alt="CarbonTrack" />
          <h1 className="font-bold text-xl text-gray-900">Carbon₂Track</h1>
          <p className="text-muted-fg text-sm mt-1">נתיבי ישראל — מעקב פליטות פחמן</p>
        </div>

        {isFirstLogin ? (
          <form onSubmit={handleChangePassword} className="space-y-4">
            <h2 className="font-semibold text-center">החלפת סיסמה ראשונית</h2>
            <div>
              <label className="text-xs text-muted-fg uppercase tracking-wide mb-1 block">סיסמה חדשה</label>
              <input type="password" value={newPass} onChange={e => setNewPass(e.target.value)}
                className="w-full text-sm border border-border rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary/40 bg-muted"
                placeholder="לפחות 4 תווים" />
            </div>
            {error && <p className="text-destructive text-xs">{error}</p>}
            <button type="submit" disabled={loading}
              className="w-full py-3 rounded-xl text-white font-semibold disabled:opacity-50 text-sm"
              style={{ background: 'var(--grad-primary)' }}>
              {loading ? 'מעדכן...' : 'עדכן סיסמה וכנס'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="text-xs text-muted-fg uppercase tracking-wide mb-1 block">אימייל</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                className="w-full text-sm border border-border rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary/40 bg-muted"
                placeholder="your@email.com" autoComplete="email" />
            </div>
            <div>
              <label className="text-xs text-muted-fg uppercase tracking-wide mb-1 block">סיסמה</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)}
                className="w-full text-sm border border-border rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary/40 bg-muted"
                placeholder="••••••••" autoComplete="current-password" />
            </div>
            {error && <p className="text-destructive text-xs">{error}</p>}
            <button type="submit" disabled={loading}
              className="w-full py-3 rounded-xl text-white font-semibold disabled:opacity-50 text-sm"
              style={{ background: 'var(--grad-primary)' }}>
              {loading ? 'מתחבר...' : 'היכנס למערכת'}
            </button>
          </form>
        )}

        <p className="text-center text-muted-fg text-[11px] mt-5">🛣️ מערכת ניהול פליטות פחמן — נתיבי ישראל</p>
      </div>
    </div>
  );
}
