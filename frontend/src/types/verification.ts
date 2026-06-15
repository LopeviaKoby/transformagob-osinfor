/**
 * Tipos derivados exactamente de la respuesta real del backend.
 * Fuentes: app/service.py · app/repository.py
 */

// ── GET /api/v1/cases ─────────────────────────────────────────────────────────

/** Resumen de un expediente devuelto por GET /api/v1/cases */
export interface CaseSummary {
  case_id: string;
  case_type: 'clean' | 'inconsistent';
  codigo_arbol: string;
  parcela_corta: string;
  verification_status: VerificationStatus;
  attestation_eligible: boolean;
  especie_censo: string | null;
  especie_supervision: string | null;
  evidence_hash_sha256: string;
}

export type VerificationStatus =
  | 'CONSISTENTE'
  | 'POR_REVISAR'
  | 'INCOMPLETO'
  | 'NO_EVALUADO'
  | 'INCONSISTENTE';

// ── GET /api/v1/verifications/{case_id} ───────────────────────────────────────

/** Una validación individual devuelta en el array `validaciones` */
export interface Validacion {
  name: string;
  status: 'PASS' | 'FAIL' | 'NOT_EVALUATED';
}

export interface VerificationBalance {
  available: boolean;
  species?: string;
  authorized_m3?: number | null;
  extracted_reported_m3?: number | null;
  remaining_reported_m3?: number | null;
}

/** Detalle público completo — proyección de service.get_public_verification() */
export interface VerificationDetail {
  schema_version: string;
  case_id: string;
  verification_status: VerificationStatus;
  attestation_eligible: boolean;

  // Identificación de origen
  titular: string | null;
  titulo_habilitante: string | null;
  parcela_corta: string | null;
  codigo_arbol: string | null;
  plan_operativo: string | null;
  resolucion: string | null;

  // Especie
  especie_censo: string | null;
  especie_supervision: string | null;

  // Volúmenes (m³)
  volumen_censo_m3: number | null;
  volumen_tala_m3: number | null;
  volumen_trozado_m3: number | null;

  // Movilización
  trozas: string[];
  gtf: string[];

  // Validaciones
  validaciones: Validacion[];

  // Linaje: solo nombres de etapa, sin rutas
  lineage_stages: string[];

  evidence_hash_sha256: string;
  disclaimer: string;
  balance?: VerificationBalance;
}
