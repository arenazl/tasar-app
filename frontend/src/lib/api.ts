/**
 * Shim de compatibilidad para WizardForm que viene de sugerenciasMun.
 * En su origen `chatApi.askDynamic()` llama a Gemini con un payload contextual.
 * Acá lo redirigimos a nuestro Tasador AI (Claude headless) — devuelve la misma forma.
 */
import { api } from '../services/api';

export const chatApi: any = {
  askDynamic: async (question: string, datos: any, tipo: string): Promise<any> => {
    const prompt = [
      `Contexto: ${tipo}`,
      `Datos: ${JSON.stringify(datos, null, 2)}`,
      question || 'Sugerí cómo completar los campos faltantes.',
    ].join('\n\n');
    try {
      const r = await api.post('/ai/chat', { message: prompt });
      const text = r.data.response;
      return { data: { response: text, respuesta: text, sugerencias: [] } };
    } catch {
      return { data: { response: '', respuesta: '', sugerencias: [] } };
    }
  },
};
