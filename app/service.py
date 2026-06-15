"""
app/service.py

Capa de servicio: proyecciones públicas sobre los datos del repositorio.

Funciones públicas:
- list_public_cases() -> list[dict]
- get_public_verification(case_id: str) -> dict | None

La proyección pública EXCLUYE:
- registros crudos (case_records)
- observations
- source_json_path / source_path
- rutas raw/, staging/, db/
- coordenadas, RUC, DNI, placas, inspectores
- el valor interno del campo R
"""

from __future__ import annotations

from app.repository import get_case_detail, list_cases

_DISCLAIMER = (
    "Comprobante prototípico de consistencia y trazabilidad. "
    "No sustituye la GTF ni una certificación oficial."
)

_SCHEMA_VERSION = "1.0"

# Checks que no deben exponerse en la proyección pública
_PRIVATE_CHECKS = {"campo_r_validado"}


def list_public_cases() -> list[dict]:
    """
    Devuelve una lista resumida de todos los expedientes.

    Cada elemento contiene:
    case_id, case_type, codigo_arbol, parcela_corta,
    verification_status, attestation_eligible, especie_censo,
    especie_supervision, evidence_hash_sha256
    """
    return list_cases()


def get_public_verification(case_id: str) -> dict | None:
    """
    Devuelve la proyección pública de un expediente.

    Apta para comprador o funcionario externo.
    Retorna None si el case_id no existe.
    """
    detail = get_case_detail(case_id)

    if detail is None:
        return None

    # Filtrar checks privados y omitir el valor interno del campo R
    public_checks = [
        {"name": chk["name"], "status": chk["status"]}
        for chk in detail["checks"]
        if chk["name"] not in _PRIVATE_CHECKS
    ]

    # Para el lineaje, exponer solo los nombres de etapa (sin rutas)
    lineage_stages = sorted(
        entry["stage"] for entry in detail["lineage"]
    )

    return {
        "schema_version": _SCHEMA_VERSION,
        "case_id": detail["case_id"],
        "verification_status": detail["status"],
        "attestation_eligible": detail["attestation_eligible"],
        "titular": detail["origin"]["titular"],
        "titulo_habilitante": detail["origin"]["titulo_habilitante"],
        "parcela_corta": detail["origin"]["parcela_corta"],
        "codigo_arbol": detail["origin"]["codigo_arbol"],
        "plan_operativo": detail["origin"]["plan_operativo"],
        "resolucion": detail["origin"]["resolucion"],
        "especie_censo": detail["species"]["census"],
        "especie_supervision": detail["species"]["supervision"],
        "volumen_censo_m3": detail["volumes_m3"]["census"],
        "volumen_tala_m3": detail["volumes_m3"]["felling"],
        "volumen_trozado_m3": detail["volumes_m3"]["bucking"],
        "trozas": detail["logs"],
        "gtf": detail["gtf"],
        "validaciones": public_checks,
        "lineage_stages": lineage_stages,
        "evidence_hash_sha256": detail["evidence_hash_sha256"],
        "disclaimer": _DISCLAIMER,
    }
