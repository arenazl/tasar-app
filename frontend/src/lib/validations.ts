export interface ValidationResult {
  isValid: boolean;
  error?: string;
}

export const validators = {
  required: (value: string, fieldName = 'Este campo'): ValidationResult => {
    if (!value || !String(value).trim()) {
      return { isValid: false, error: `${fieldName} es obligatorio` };
    }
    return { isValid: true };
  },
  minLength: (value: string, min: number, fieldName = 'Este campo'): ValidationResult => {
    if (value && value.length < min) {
      return { isValid: false, error: `${fieldName} debe tener al menos ${min} caracteres` };
    }
    return { isValid: true };
  },
  maxLength: (value: string, max: number, fieldName = 'Este campo'): ValidationResult => {
    if (value && value.length > max) {
      return { isValid: false, error: `${fieldName} no puede exceder ${max} caracteres` };
    }
    return { isValid: true };
  },
  email: (value: string): ValidationResult => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (value && !re.test(value)) {
      return { isValid: false, error: 'Email inválido' };
    }
    return { isValid: true };
  },
  number: (value: string, fieldName = 'Este campo'): ValidationResult => {
    if (value === '' || value == null) return { isValid: true };
    if (isNaN(Number(value))) {
      return { isValid: false, error: `${fieldName} debe ser un número` };
    }
    return { isValid: true };
  },
  positive: (value: string, fieldName = 'Este campo'): ValidationResult => {
    if (value === '' || value == null) return { isValid: true };
    const n = Number(value);
    if (isNaN(n) || n <= 0) {
      return { isValid: false, error: `${fieldName} debe ser mayor a 0` };
    }
    return { isValid: true };
  },
};
