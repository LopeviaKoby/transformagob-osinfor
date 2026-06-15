import type { SearchResponse } from '../types/search';
import { getPublicApiError } from './publicApiErrors';

const BASE = '/api/v1';

async function fetchJson<T>(
  url: string,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(url, { signal });
  const fallbackMessage = response.status === 422
    ? 'Revisa el código ingresado.'
    : 'No pudimos completar la búsqueda.';

  if (!response.ok) {
    let detail = fallbackMessage;
    try {
      const body = await response.json() as { detail?: string };
      detail = getPublicApiError(body.detail, response.status, fallbackMessage);
    } catch {
      // ignorar si no es JSON
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

export async function searchCatalog(
  query: string,
  signal?: AbortSignal,
): Promise<SearchResponse> {
  const params = new URLSearchParams({ query });
  return fetchJson<SearchResponse>(`${BASE}/search?${params.toString()}`, signal);
}
