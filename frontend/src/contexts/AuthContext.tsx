import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api } from '../services/api';
import type { User } from '../types';

interface AuthCtx {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: { email: string; password: string; full_name: string; workspace_name: string; license_number?: string }) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('tasar_token');
    if (!token) { setLoading(false); return; }
    api.get<User>('/auth/me')
      .then(r => setUser(r.data))
      .catch(() => localStorage.removeItem('tasar_token'))
      .finally(() => setLoading(false));
  }, []);

  const login = async (email: string, password: string) => {
    const r = await api.post('/auth/login', { email, password });
    localStorage.setItem('tasar_token', r.data.access_token);
    setUser(r.data.user);
  };

  const register = async (data: any) => {
    const r = await api.post('/auth/register', data);
    localStorage.setItem('tasar_token', r.data.access_token);
    setUser(r.data.user);
  };

  const logout = () => {
    localStorage.removeItem('tasar_token');
    setUser(null);
  };

  return <Ctx.Provider value={{ user, loading, login, register, logout }}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useAuth fuera de AuthProvider');
  return ctx;
}
