function normalizeText(value: string): string {
  return value.trim().toLowerCase();
}

export function getPublicApiError(
  detail: unknown,
  status: number,
  fallbackMessage: string,
): string {
  if (typeof detail !== 'string' || detail.trim() === '') {
    return fallbackMessage;
  }

  const normalized = normalizeText(detail);

  if (
    normalized.includes('unprocessable entity') ||
    normalized.includes('field required') ||
    normalized.includes('string should have at most') ||
    normalized.includes('input should be') ||
    normalized.includes('query must not be empty')
  ) {
    return 'Revisa el código ingresado.';
  }

  if (
    normalized.includes('not found') ||
    normalized.includes('no verification found')
  ) {
    return 'No encontramos el expediente solicitado.';
  }

  if (normalized.startsWith('error ')) {
    if (status >= 500) {
      return 'No pudimos completar la solicitud.';
    }
    return fallbackMessage;
  }

  return detail;
}
