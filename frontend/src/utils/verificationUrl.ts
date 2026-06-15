/**
 * src/utils/verificationUrl.ts
 *
 * Utilidades para construir y leer la URL verificable de un expediente.
 * La URL contiene únicamente: protocolo + host + ruta + ?case=<caseId>.
 * No incluye hash, titular, especie, GTF, coordenadas ni datos privados.
 */

/**
 * Devuelve la URL pública canónica para un case_id.
 *
 * Usa VITE_PUBLIC_BASE_URL cuando está definida y no vacía;
 * de lo contrario usa window.location limpiando search y hash.
 */
export function buildVerificationUrl(caseId: string): string {
  const rawBase = import.meta.env.VITE_PUBLIC_BASE_URL as string | undefined;

  let base: URL;
  if (rawBase && rawBase.trim().length > 0) {
    base = new URL(rawBase.trim());
  } else {
    // Tomar la URL actual eliminando search y hash previos
    base = new URL(window.location.href);
    base.search = '';
    base.hash = '';
  }

  // Construir params — URLSearchParams se encarga de la codificación
  const params = new URLSearchParams();
  params.set('case', caseId);
  base.search = params.toString();

  return base.toString();
}

/**
 * Lee el query param ?case= de la URL actual.
 * Devuelve null si no está presente.
 * No valida que el case_id exista en la base de datos.
 */
export function getRequestedCaseId(): string | null {
  const params = new URLSearchParams(window.location.search);
  return params.get('case');
}

export function getRequestedSearchQuery(): string | null {
  const params = new URLSearchParams(window.location.search);
  return params.get('query');
}

/**
 * Actualiza la barra del navegador con la URL del caso
 * sin recargar la página.
 */
export function updateVerificationUrl(caseId: string): void {
  const url = buildVerificationUrl(caseId);
  window.history.replaceState(null, '', url);
}

/**
 * Limpia el query param ?case= de la URL actual sin recargar.
 */
export function clearVerificationUrl(): void {
  const url = new URL(window.location.href);
  url.search = '';
  url.hash = '';
  window.history.replaceState(null, '', url.toString());
}
