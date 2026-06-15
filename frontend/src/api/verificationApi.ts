/**
 * Cliente API — rutas relativas hacia el backend FastAPI.
 * El proxy Vite reenvía /api → http://127.0.0.1:8000
 */

import type { CaseSummary, VerificationDetail } from '../types/verification';
import { getPublicApiError } from './publicApiErrors';

const BASE = '/api/v1';

/** Lanzador genérico con comprobación de response.ok */
async function fetchJson<T>(
  url: string,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(url, { signal });
  const fallbackMessage = response.status === 404
    ? 'No encontramos el expediente solicitado.'
    : 'No pudimos cargar el expediente.';

  if (!response.ok) {
    let detail = fallbackMessage;
    try {
      const body = await response.json() as { detail?: string };
      detail = getPublicApiError(body.detail, response.status, fallbackMessage);
    } catch {
      // cuerpo no es JSON — ignorar
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

/** GET /api/v1/cases */
export async function getCases(signal?: AbortSignal): Promise<CaseSummary[]> {
  return fetchJson<CaseSummary[]>(`${BASE}/cases`, signal);
}

/** GET /api/v1/verifications/{case_id} */
export async function getVerification(
  caseId: string,
  signal?: AbortSignal,
): Promise<VerificationDetail> {
  return fetchJson<VerificationDetail>(
    `${BASE}/verifications/${encodeURIComponent(caseId)}`,
    signal,
  );
}
