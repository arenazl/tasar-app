import { Navigate } from 'react-router-dom';
import { ReactNode } from 'react';
import { useAuth } from '../contexts/AuthContext';
import BrandLoading from './BrandLoading';

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <BrandLoading fullscreen message="Iniciando TasAR…" size="md" />;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
