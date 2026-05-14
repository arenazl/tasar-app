export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'admin' | 'tasador' | 'cliente';
  workspace_id: number;
  license_number?: string;
  avatar_url?: string;
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
