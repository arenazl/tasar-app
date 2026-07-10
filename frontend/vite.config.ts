import { execSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Version auto-incremental: nº de commits + short SHA. Sube en cada push/deploy.
// base-compartida/6-GUIA-PWA.md — Nivel 1 (version.json + versionCheck).
function gitVersion(): string {
  try {
    const count = execSync('git rev-list --count HEAD').toString().trim();
    const sha = execSync('git rev-parse --short HEAD').toString().trim();
    return `${count}.${sha}`;
  } catch {
    return 'dev';
  }
}
const APP_VERSION = gitVersion();

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'emit-version-json',
      closeBundle() {
        try {
          writeFileSync('dist/version.json', JSON.stringify({ version: APP_VERSION }));
        } catch {
          /* dev / sin dist: ignorar */
        }
      },
    },
  ],
  define: { __APP_VERSION__: JSON.stringify(APP_VERSION) },
  server: {
    port: 5600,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8600',
        changeOrigin: true,
      },
    },
  },
});
