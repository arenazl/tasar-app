// Jerarquia de roles del rubro inmobiliario (WO F6-06) — fuente UNICA del
// vocabulario en el frontend. Espeja core.security.ROLE_HIERARCHY del backend.
//
//   broker (4)        titular con matricula: acceso TOTAL.
//   administrador (3) gestion plena (config + equipo + borrados). En permisos == broker.
//   coordinador (2)   ve TODO el workspace + gestiona lo comercial (DMO, ranking),
//                     pero NO config del workspace, NI equipo, NI borrados sensibles.
//   asesor (1)        opera lo suyo + lo sin asignar (el "vendedor" de antes).
export type StaffRole = 'broker' | 'administrador' | 'coordinador' | 'asesor';

export const ROLE_HIERARCHY: Record<StaffRole, number> = {
  asesor: 1,
  coordinador: 2,
  administrador: 3,
  broker: 4,
};

// Labels y descripciones en castellano rioplatense (para selectores/badges).
export const ROLE_META: Record<StaffRole, { label: string; desc: string; color: string }> = {
  broker: { label: 'Broker', desc: 'Titular · acceso total', color: '#ef4444' },
  administrador: { label: 'Administrador', desc: 'Gestión plena + equipo', color: '#f59e0b' },
  coordinador: { label: 'Coordinador', desc: 'Ve todo + comercial', color: '#8b5cf6' },
  asesor: { label: 'Asesor', desc: 'Opera lo suyo', color: '#10b981' },
};

// Orden de mayor a menor jerarquia (para selectores).
export const STAFF_ROLES: StaffRole[] = ['broker', 'administrador', 'coordinador', 'asesor'];

export function roleLevel(role?: string | null): number {
  return role ? (ROLE_HIERARCHY[role as StaffRole] ?? 0) : 0;
}

/** True si `role` alcanza (>=) el nivel de `min`. */
export function hasMinRole(role: string | undefined | null, min: StaffRole): boolean {
  return roleLevel(role) >= ROLE_HIERARCHY[min];
}

/** Manager: ve todo el workspace + herramientas comerciales (coordinador+). */
export function isManager(role?: string | null): boolean {
  return hasMinRole(role, 'coordinador');
}

/** Gestión del workspace: config, equipo, borrados sensibles (administrador+). */
export function canManageWorkspace(role?: string | null): boolean {
  return hasMinRole(role, 'administrador');
}

export function roleLabel(role?: string | null): string {
  return role ? (ROLE_META[role as StaffRole]?.label ?? role) : '';
}
