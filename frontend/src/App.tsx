import { Routes, Route } from 'react-router-dom';
import { Toaster } from 'sonner';
import { AuthProvider } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';

import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Bandeja from './pages/Bandeja';
import Propiedades from './pages/Propiedades';
import Estudios from './pages/Estudios';
import EstudioDetail from './pages/EstudioDetail';
import Tasaciones from './pages/Tasaciones';
import MapaCalor from './pages/MapaCalor';
import TasadorAI from './pages/TasadorAI';
import Configuracion from './pages/Configuracion';
import Mercado from './pages/Mercado';
import Comparables from './pages/Comparables';
import Reportes from './pages/Reportes';
import Pipeline from './pages/Pipeline';
import Clientes from './pages/Clientes';

export default function App() {
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
                  <Route path="/pipeline" element={<Pipeline />} />
                  <Route path="/clientes" element={<Clientes />} />
                  <Route path="/mercado" element={<Mercado />} />
                  <Route path="/comparables" element={<Comparables />} />
                  <Route path="/reportes" element={<Reportes />} />
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
