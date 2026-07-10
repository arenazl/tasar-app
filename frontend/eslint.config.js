// ESLint 9 flat config (WO F3-06 -- gate de calidad).
//
// rules-of-hooks: error  -> bug de runtime real (React #310 en prod si se
//   viola: hook llamado condicionalmente / despues de un return / en un
//   loop). Nunca se afloja.
// exhaustive-deps: warn  -> se anota, NO se fuerza a arreglar todo de una
//   (hay warns preexistentes que dependen de un analisis caso por caso,
//   ver el listado en el reporte del WO).
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import reactHooks from 'eslint-plugin-react-hooks';
import globals from 'globals';

export default tseslint.config(
  { ignores: ['dist/**', 'node_modules/**', 'src/assets copy/**'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['src/**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2020,
      sourceType: 'module',
      globals: { ...globals.browser },
    },
    plugins: {
      'react-hooks': reactHooks,
    },
    rules: {
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      // TypeScript ya cubre variables/params sin uso (y tsconfig las deja
      // pasar a proposito, noUnusedLocals/noUnusedParameters: false) --
      // no duplicar el chequeo con una regla mas estricta en ESLint.
      '@typescript-eslint/no-unused-vars': 'off',
      '@typescript-eslint/no-explicit-any': 'off',
    },
  },
);
