export interface User {
  id: number;
  email: string;
  full_name: string;
  // Roles unificados de la suite (WO F1-01) + legacy TasAR.
  role: 'admin' | 'supervisor' | 'vendedor' | 'tasador' | 'cliente';
  workspace_id: number;
  license_number?: string;
  avatar_url?: string;
  daily_conversations_goal?: number;
}

// ==================== DMO (WO F2-01) ====================

export type MetricType = 'checkbox' | 'quantity';

export interface Coach {
  id: number;
  name: string;
  description?: string | null;
  photo_url?: string | null;
  source_url?: string | null;
  is_official: boolean;
  templates_count?: number;
  created_at: string;
}

export interface DmoBlock {
  id: number;
  template_id: number;
  name: string;
  description?: string | null;
  start_time: string; // "HH:MM:SS"
  end_time: string;
  color: string;
  sort_order: number;
  is_money_block: boolean;
  metric_type: MetricType;
  metric_label?: string | null;
  metric_goal: number;
}

export interface DmoTemplate {
  id: number;
  workspace_id?: number | null; // NULL = catalogo oficial global
  coach_id: number;
  coach_name?: string | null;
  name: string;
  description?: string | null;
  market?: string | null;
  is_active: boolean;
  is_office_default: boolean;
  is_official: boolean; // true si es del catalogo global
  blocks: DmoBlock[];
  assignments_count?: number;
  created_at: string;
}

export interface VendorOut {
  id: number;
  full_name: string;
  email: string;
  role: string;
  daily_conversations_goal: number;
}

export interface DmoAssignment {
  id: number;
  vendor_id: number;
  vendor_name?: string | null;
  template_id: number;
  template_name?: string | null;
  coach_name?: string | null;
  assigned_at: string;
}

export interface DmoLog {
  id: number;
  vendor_id: number;
  block_id: number;
  date: string;
  completed: boolean;
  metric_value: number;
  notes?: string | null;
  created_at: string;
}

export interface DmoDay {
  date: string;
  template: DmoTemplate | null;
  blocks: DmoBlock[];
  logs: DmoLog[];
  conversations_goal: number;
  conversations_done: number;
  completion_pct: number;
}

export interface PropertyPhoto {
  id: number;
  url: string;
  caption?: string;
  order: number;
}

export interface Property {
  id: number;
  workspace_id: number;
  created_by: number;
  title: string;
  property_type: string;
  operation: string;
  province: string;
  city: string;
  neighborhood?: string;
  address: string;
  latitude?: number;
  longitude?: number;
  total_area_m2?: number;
  covered_area_m2?: number;
  rooms?: number;
  bedrooms?: number;
  bathrooms?: number;
  parking_spots?: number;
  age_years?: number;
  condition?: string;
  orientation?: string;
  floor?: number;
  asking_price?: number;
  currency: string;
  description?: string;
  ai_analysis?: string;
  photos: PropertyPhoto[];
  created_at: string;
  updated_at: string;
}

export interface Adjustment {
  id?: number;
  factor: string;
  description?: string;
  coefficient: number;
  amount?: number;
}

export interface Comparable {
  id: number;
  source: string;
  source_url?: string;
  title: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  total_area_m2?: number;
  covered_area_m2?: number;
  rooms?: number;
  bedrooms?: number;
  bathrooms?: number;
  age_years?: number;
  condition?: string;
  price: number;
  currency: string;
  price_per_m2?: number;
  adjusted_price?: number;
  adjusted_price_per_m2?: number;
  weight: number;
  notes?: string;
  adjustments: Adjustment[];
}

export interface MarketStudy {
  id: number;
  workspace_id: number;
  property_id: number;
  created_by: number;
  status: string;
  method: string;
  suggested_value_min?: number;
  suggested_value_max?: number;
  suggested_value_mode?: number;
  confidence_score?: number;
  ai_summary?: string;
  ai_recommendations?: string;
  notes?: string;
  comparables: Comparable[];
  created_at: string;
  updated_at: string;
}

export interface Appraisal {
  id: number;
  workspace_id: number;
  property_id: number;
  market_study_id?: number;
  created_by: number;
  purpose: string;
  status: string;
  final_value: number;
  currency: string;
  methodology?: string;
  observations?: string;
  legal_remarks?: string;
  pdf_url?: string;
  delivered_at?: string;
  signatures: { id: number; user_id: number; signed_at: string }[];
  created_at: string;
}

export interface DashboardData {
  kpis: { label: string; value: number; delta_pct?: number; unit?: string }[];
  properties_by_type: { type: string; count: number }[];
  studies_by_status: { status: string; count: number }[];
  recent_appraisals: any[];
}

export interface HeatPoint {
  lat: number;
  lng: number;
  intensity: number;
  label?: string;
  price_per_m2?: number;
}
