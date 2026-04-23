const BACKEND = process.env.NEXT_PUBLIC_API_URL || 'https://calc-carbon-140293665526.me-west1.run.app';

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BACKEND}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) },
    ...options,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data as T;
}

export interface User {
  email: string;
  name: string;
  role: string;
  is_first_login: boolean;
}

export interface EmissionRow {
  id?: string;
  project_name: string;
  contractor: string;
  region: string;
  category: string;
  boq_code?: string;
  short_text?: string;
  material?: string;
  weight_kg: number;
  emission_co2e: number;
  reliability_score: number;
  matched_by?: string;
  assumed_uom?: string;
  review_required?: boolean;
  year?: number;
  measurement_year?: number;
  calculation_date?: string;
  scope?: string;
  conversion_assumption?: string;
  reliability_status?: string;
}

export interface ReviewRow {
  review_id: string;
  short_text: string;
  material?: string;
  project_name: string;
  boq_code?: string;
  suggested_category: string;
  suggested_uom: string;
  review_reason: string;
  reliability_score: number;
  factor_spread_pct?: number;
  climatiq_candidate_count?: number;
}

export interface ProcessingRun {
  run_id: string;
  status: string;
  current_stage?: string;
  rows_processed?: number;
  rows_total?: number;
  progress_pct?: number;
  source_file?: string;
  file_name?: string;
  created_at?: string;
  updated_at?: string;
}

// Auth
export const login = (email: string, password: string) =>
  req<User>('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });

export const changePassword = (email: string, new_password: string) =>
  req('/auth/change-password', { method: 'POST', body: JSON.stringify({ email, new_password }) });

// Data
export const fetchEmissions = () => req<{ items: EmissionRow[] }>('/emissions');
export const fetchReview = (status = 'pending') => req<{ items: ReviewRow[] }>(`/review-items?status=${status}`);
export const fetchProcessingStatus = () => req<{ run: ProcessingRun | null }>('/processing/status');
export const fetchProjects = () => req<{ projects: string[] }>('/projects');

// Review actions
export const approveReview = (review_id: string, reviewed_by = 'dashboard') =>
  req('/review/approve', { method: 'POST', body: JSON.stringify({ review_id, reviewed_by }) });

export const rejectReview = (review_id: string, reviewed_by = 'dashboard') =>
  req('/review/reject', { method: 'POST', body: JSON.stringify({ review_id, reviewed_by }) });

// AI chat
export const aiChat = (messages: { role: string; content: string }[], context: string) =>
  req<{ reply: string }>('/ai/chat', { method: 'POST', body: JSON.stringify({ messages, context }) });

// Manage DB
export const deleteProject = (project_name: string) =>
  req('/manage-db', { method: 'POST', body: JSON.stringify({ action: 'delete_project', project_name }) });

// Upload
export async function uploadFile(formData: FormData, projectName: string, contractor: string, region: string, sourceMode: string, settings: Record<string, unknown>) {
  const payload = {
    bucket: 'green_excal',
    file: (formData.get('file') as File)?.name,
    project_name: projectName,
    contractor,
    region,
    source_mode: sourceMode,
    measurement_basis: sourceMode === 'annual_paid_2025' ? 'paid_2025' : 'boq',
    ...settings,
  };

  // 1. Upload file to GCS via a signed-URL or direct (handled client-side via GCS)
  // 2. Trigger backend processing
  const res = await fetch(BACKEND, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'שגיאה בעיבוד הקובץ');
  return data;
}
