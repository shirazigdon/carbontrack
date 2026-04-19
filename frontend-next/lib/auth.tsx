'use client';
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User, login as apiLogin, changePassword as apiChangePassword } from './api';

interface AuthCtx {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  changePassword: (email: string, newPass: string) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx>(null!);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    try {
      const stored = localStorage.getItem('ct_user');
      if (stored) setUser(JSON.parse(stored));
    } catch {}
    setLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    const u = await apiLogin(email, password);
    if (!u.is_first_login) {
      localStorage.setItem('ct_user', JSON.stringify(u));
      setUser(u);
    } else {
      // return user with first_login flag — page handles password change
      setUser({ ...u });
    }
  };

  const changePassword = async (email: string, newPass: string) => {
    await apiChangePassword(email, newPass);
    const updated = { ...user!, is_first_login: false };
    localStorage.setItem('ct_user', JSON.stringify(updated));
    setUser(updated);
  };

  const logout = () => {
    localStorage.removeItem('ct_user');
    setUser(null);
  };

  return <Ctx.Provider value={{ user, loading, login, changePassword, logout }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
