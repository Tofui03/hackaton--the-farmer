import type { AuditRecord, ErrorResponse, ReviewUpdate, SubmissionRecord } from '../types/api';

const API_BASE = (import.meta.env.VITE_API_BASE ?? (import.meta.env.DEV ? '/api' : '')).replace(/\/$/, '');

export class ApiError extends Error {
  status: number;
  payload: ErrorResponse | null;

  constructor(status: number, message: string, payload: ErrorResponse | null = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let payload: ErrorResponse | null = null;
    try {
      payload = (await response.json()) as ErrorResponse;
    } catch {
      payload = null;
    }
    throw new ApiError(response.status, payload?.message ?? `Request failed (${response.status})`, payload);
  }

  return (await response.json()) as T;
}

export function listAudits(): Promise<AuditRecord[]> {
  return request<AuditRecord[]>('/audit');
}

export function getAudit(emailId: string): Promise<AuditRecord> {
  return request<AuditRecord>(`/audit/${encodeURIComponent(emailId)}`);
}

export function submitReview(emailId: string, update: ReviewUpdate): Promise<AuditRecord> {
  return request<AuditRecord>(`/audit/${encodeURIComponent(emailId)}/review`, {
    method: 'POST',
    body: JSON.stringify(update),
  });
}

export type SubmissionPayload = Record<string, SubmissionRecord>;

export function getSubmission(): Promise<SubmissionPayload> {
  return request<SubmissionPayload>('/submission');
}
