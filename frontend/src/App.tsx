import { useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Toaster } from 'sonner';
import { AuthProvider } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';

// Cleanup de hints viejos (pre-v2) para que vuelvan a aparecer despues de
// la reescritura completa de contenido en pageHints.ts. Sucede una sola vez
// por sesion por dispositivo.
function cleanupOldHintFlags() {
  if (typeof window === 'undefined') return;
  if (localStorage.getItem('tasar_hints_v2_migrated') === 'true') return;
  const keysToRemove: string[] = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key && key.startsWith('hint_dismissed_') && !key.includes('_v2_')) {
      keysToRemove.push(key);
    }
  }
  keysToRemove.forEach(k => localStorage.removeItem(k));
  localStorage.setItem('tasar_hints_v2_migrated', 'true');
}
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';

import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Bandeja from './pages/Bandeja';
import Propiedades from './pages/Propiedades';
import Estudios from './pages/Estudios';
import EstudioDetail from './pages/EstudioDetail';
import Tasaciones from './pages/Tasaciones';
import TasacionDetail from './pages/TasacionDetail';
import TasacionExpress from './pages/TasacionExpress';
import MapaCalor from './pages/MapaCalor';
import TasadorAI from './pages/TasadorAI';
import Configuracion from './pages/Configuracion';
import Mercado from './pages/Mercado';
import Comparables from './pages/Comparables';
import Reportes from './pages/Reportes';
import EstudioEditorial from './pages/EstudioEditorial';
import Pipeline from './pages/Pipeline';
import Clientes from './pages/Clientes';

export default function App() {
  useEffect(() => { cleanupOldHintFlags(); }, []);
  return (
    <ThemeProvider>
      <AuthProvider>
        <Toaster position="top-right" richColors />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/*" element={
            <ProtectedRoute>
              <Layout>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/bandeja" element={<Bandeja />} />
                  <Route path="/propiedades" element={<Propiedades />} />
                  <Route path="/estudios" element={<Estudios />} />
                  <Route path="/estudios/:id" element={<EstudioDetail />} />
                  <Route path="/tasaciones" element={<Tasaciones />} />
                  <Route path="/tasacion-express" element={<TasacionExpress />} />
                  <Route path="/tasaciones/:id" element={<TasacionDetail />} />
                  <Route path="/pipeline" element={<Pipeline />} />
                  <Route path="/clientes" element={<Clientes />} />
                  <Route path="/mercado" element={<Mercado />} />
                  <Route path="/comparables" element={<Comparables />} />
                  <Route path="/reportes" element={<Reportes />} />
                  <Route path="/reportes/:id" element={<EstudioEditorial />} />
                  <Route path="/mapa" element={<MapaCalor />} />
                  <Route path="/tasador-ai" element={<TasadorAI />} />
                  <Route path="/configuracion" element={<Configuracion />} />
                </Routes>
              </Layout>
            </ProtectedRoute>
          } />
        </Routes>
      </AuthProvider>
    </ThemeProvider>
  );
}
