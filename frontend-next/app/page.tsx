'use client';
import { useEffect, useState } from 'react';
import { AuthProvider, useAuth } from '../lib/auth';
import { LoginPage } from '../components/LoginPage';
import { Dashboard } from '../components/Dashboard';

function AppContent() {
  const { user, loading } = useAuth();
  const [isDemo, setIsDemo] = useState(false);
  const [demoChecked, setDemoChecked] = useState(false);

  useEffect(() => {
    setIsDemo(new URLSearchParams(window.location.search).has('demo'));
    setDemoChecked(true);
  }, []);

  if (!demoChecked || (loading && !isDemo)) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--grad-hero)' }}>
        <div className="text-white text-center">
          <div className="text-4xl mb-3">🌿</div>
          <div className="font-semibold">טוען...</div>
        </div>
      </div>
    );
  }

  if (isDemo) return <Dashboard demoMode />;
  if (!user || user.is_first_login) return <LoginPage />;
  return <Dashboard />;
}

export default function Home() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
