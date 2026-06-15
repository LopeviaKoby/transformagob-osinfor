const VALIDATION_LABELS: Record<string, string> = {
  census_present: 'Árbol registrado en el censo',
  felling_present: 'Tala registrada',
  logs_present: 'Trozas registradas',
  dispatch_present: 'Despacho registrado',
  gtf_present: 'GTF registrada',
  dispatched_logs_registered: 'Trozas despachadas registradas',
  supervision_species_match: 'Especie verificada en supervisión',
  operation_species_match: 'Especie registrada en la operación',
  census_volume_vs_felling: 'Volumen de censo y tala',
  felling_volume_vs_logs: 'Volumen de tala y trozado',
  species_balance_available: 'Balance de la especie disponible',
  species_balance_non_negative: 'Saldo reportado de la especie',
  gtf_scope_consistent: 'GTF asociada al mismo origen',
  source_r_interpreted: 'Dato no evaluado',
};

const VALIDATION_STATUS_LABELS = {
  PASS: 'Cumple',
  FAIL: 'Por revisar',
  NOT_EVALUATED: 'No evaluado',
} as const;

export function getValidationLabel(code: string): string {
  return VALIDATION_LABELS[code] ?? 'Control adicional';
}

export function getValidationStatusLabel(
  status: keyof typeof VALIDATION_STATUS_LABELS,
): string {
  return VALIDATION_STATUS_LABELS[status];
}
