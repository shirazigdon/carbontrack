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
    try { await login(email, password); } catch (err) { setError(String(err)); }
    setLoading(false);
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPass.length < 4 || newPass === '1234') { setError('סיסמה חייבת להיות לפחות 4 תווים ושונה מ-1234'); return; }
    setLoading(true); setError('');
    try { await changePassword(user!.email, newPass); } catch (err) { setError(String(err)); }
    setLoading(false);
  };

  if (isFirstLogin) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(160deg, #eef8f2 0%, #d8f3e3 50%, #f7fbf7 100%)' }}>
        <div style={cardStyle}>
          <img src={LOGO} style={{ width: 72, height: 72, objectFit: 'contain', display: 'block', margin: '0 auto 16px' }} alt="logo" />
          <h2 style={{ fontSize: 20, fontWeight: 700, textAlign: 'center', color: '#1b4332', marginBottom: 6 }}>הגדרת סיסמה ראשונית</h2>
          <p style={{ fontSize: 13, color: '#52b788', textAlign: 'center', marginBottom: 24 }}>בחרי סיסמה חדשה לחשבונך</p>
          <form onSubmit={handleChangePassword} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <label style={labelStyle}>סיסמה חדשה</label>
            <input type="password" value={newPass} onChange={e => setNewPass(e.target.value)} style={inputStyle} placeholder="לפחות 4 תווים" />
            {error && <div style={errorStyle}>{error}</div>}
            <button type="submit" disabled={loading} style={btnStyle}>{loading ? 'מעדכן...' : 'עדכן וכנס'}</button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(160deg, #eef8f2 0%, #d8f3e3 40%, #b7e4c7 100%)', display: 'flex', flexDirection: 'column' }}>

      {/* Decorative blobs */}
      <div style={{ position: 'fixed', top: -100, right: -100, width: 400, height: 400, borderRadius: '50%', background: 'radial-gradient(circle, rgba(82,183,136,0.25), transparent)', pointerEvents: 'none' }} />
      <div style={{ position: 'fixed', bottom: -80, left: -80, width: 350, height: 350, borderRadius: '50%', background: 'radial-gradient(circle, rgba(149,213,178,0.3), transparent)', pointerEvents: 'none' }} />
      <div style={{ position: 'fixed', top: '40%', left: '30%', width: 200, height: 200, borderRadius: '50%', background: 'radial-gradient(circle, rgba(183,228,199,0.2), transparent)', pointerEvents: 'none' }} />

      {/* Top bar */}
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 32px', position: 'relative', zIndex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <img src={LOGO} style={{ width: 36, height: 36, objectFit: 'contain' }} alt="logo" />
          <span style={{ fontWeight: 700, fontSize: 15, color: '#1b4332' }}>Carbon₂Track</span>
        </div>
        <span style={{ fontSize: 12, color: '#52b788', fontWeight: 500 }}>🌿 נתיבי ישראל</span>
      </header>

      {/* Hero */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '32px 16px', textAlign: 'center', position: 'relative', zIndex: 1 }}>

        {/* Logo with glow */}
        <div style={{ position: 'relative', marginBottom: 28 }}>
          <div style={{ position: 'absolute', inset: -20, borderRadius: '50%', background: 'radial-gradient(circle, rgba(82,183,136,0.35), transparent)', filter: 'blur(20px)' }} />
          <img src={LOGO} style={{ position: 'relative', width: 140, height: 140, objectFit: 'contain', filter: 'drop-shadow(0 8px 24px rgba(27,67,50,0.2))' }} alt="CarbonTrack" />
        </div>

        <h1 style={{ fontSize: 48, fontWeight: 900, color: '#1b4332', marginBottom: 8, lineHeight: 1.1 }}>
          Carbon<span style={{ color: '#52b788' }}>₂</span>Track
        </h1>
        <p style={{ fontSize: 18, color: '#2d6a4f', fontWeight: 600, marginBottom: 8 }}>מעקב פליטות פחמן לסביבה בריאה יותר</p>
        <p style={{ fontSize: 13, color: '#74c69d', marginBottom: 36, maxWidth: 360, lineHeight: 1.7 }}>
          ניטור, ניתוח וצמצום פליטות CO₂ בפרויקטי תשתית — בזמן אמת, מבוסס BigQuery ו-AI
        </p>

        {/* Feature chips */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center', marginBottom: 36 }}>
          {['🌱 דאשבורד KPI', '🤖 ניתוח Gemini AI', '⚡ סימולטור What-If', '🗺️ מפת ישראל', '✅ תור סקירה'].map(f => (
            <span key={f} style={{ fontSize: 12, fontWeight: 500, padding: '6px 14px', borderRadius: 99, background: 'rgba(255,255,255,0.7)', border: '1.5px solid #b7e4c7', color: '#2d6a4f', backdropFilter: 'blur(8px)' }}>{f}</span>
          ))}
        </div>

        {/* CTA */}
        {!showForm ? (
          <button onClick={() => setShowForm(true)} style={{ ...btnStyle, fontSize: 16, padding: '14px 40px', borderRadius: 16, boxShadow: '0 8px 28px rgba(64,145,108,0.35)' }}>
            כניסה למערכת 🌿
          </button>
        ) : (
          <div style={{ ...cardStyle, width: '100%', maxWidth: 360, marginTop: 8, animation: 'fadeSlide 0.2s ease' }}>
            <h2 style={{ fontSize: 17, fontWeight: 700, color: '#1b4332', marginBottom: 20 }}>כניסה למערכת</h2>
            <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={labelStyle}>אימייל</label>
                <input type="email" value={email} onChange={e => setEmail(e.target.value)} style={inputStyle} placeholder="your@email.com" autoComplete="email" dir="ltr" autoFocus />
              </div>
              <div>
                <label style={labelStyle}>סיסמה</label>
                <input type="password" value={password} onChange={e => setPassword(e.target.value)} style={inputStyle} placeholder="••••••••" autoComplete="current-password" dir="ltr" />
              </div>
              {error && <div style={errorStyle}>{error}</div>}
              <button type="submit" disabled={loading} style={btnStyle}>{loading ? 'מתחבר...' : 'כניסה ←'}</button>
              <button type="button" onClick={() => setShowForm(false)} style={{ fontSize: 12, color: '#74c69d', background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}>חזרה</button>
            </form>
          </div>
        )}
      </main>

      <footer style={{ textAlign: 'center', fontSize: 11, color: '#95d5b2', padding: '16px', position: 'relative', zIndex: 1 }}>
        Carbon₂Track · נתיבי ישראל · {new Date().getFullYear()} 🌿
      </footer>
    </div>
  );
}

const cardStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.85)',
  border: '1.5px solid #b7e4c7',
  borderRadius: 24,
  padding: 32,
  backdropFilter: 'blur(16px)',
  boxShadow: '0 8px 32px rgba(27,67,50,0.10)',
};

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: 12,
  fontWeight: 600,
  color: '#4a7c59',
  marginBottom: 6,
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  fontSize: 14,
  border: '1.5px solid #b7e4c7',
  borderRadius: 12,
  padding: '10px 14px',
  outline: 'none',
  background: '#f7fbf7',
  color: '#1b4332',
  transition: 'border-color 0.2s',
};

const btnStyle: React.CSSProperties = {
  width: '100%',
  padding: '12px 20px',
  borderRadius: 12,
  background: 'linear-gradient(135deg, #40916c, #52b788)',
  color: '#ffffff',
  fontWeight: 700,
  fontSize: 14,
  border: 'none',
  cursor: 'pointer',
  transition: 'opacity 0.2s',
};

const errorStyle: React.CSSProperties = {
  fontSize: 12,
  color: '#e63946',
  background: '#fde8e8',
  border: '1px solid #fca5a5',
  borderRadius: 10,
  padding: '8px 12px',
};
