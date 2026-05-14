import { Users } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export default function Equipo() {
  const { user } = useAuth();
  return (
    <div className="p-8 max-w-5xl mx-auto animate-fade-in">
      <header className="mb-6">
        <h1 className="text-3xl font-bold text-text-primary flex items-center gap-2">
          <Users className="h-7 w-7 text-brand" /> Equipo
        </h1>
        <p className="text-text-secondary mt-1">Tasadores y colaboradores del workspace</p>
      </header>

      <div className="p-6 rounded-xl bg-bg-card border border-border-base">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-brand text-white flex items-center justify-center font-bold text-lg">
            {user?.full_name?.charAt(0)}
          </div>
          <div>
            <div className="font-semibold text-text-primary">{user?.full_name}</div>
            <div className="text-sm text-text-secondary">{user?.email}</div>
            <div className="text-xs text-text-secondary mt-1 capitalize">{user?.role} {user?.license_number && `· Mat. ${user.license_number}`}</div>
          </div>
        </div>
      </div>

      <div className="mt-6 p-6 rounded-xl bg-bg-card border border-dashed border-border-base text-center text-text-secondary">
        Próximamente: invitar tasadores, asignar permisos por estudio, gestionar firmas múltiples.
      </div>
    </div>
  );
}
