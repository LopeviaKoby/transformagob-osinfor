"""
Proyecciones públicas para db/huella_catalog.db.
"""

from __future__ import annotations

from typing import Any

from app.catalog_repository import (
    ALLOWED_STATUSES,
    get_catalog_trace,
    get_catalog_trace_count,
    search_identifiers,
)

_DISCLAIMER = (
    "Comprobante prototípico de consistencia y trazabilidad. "
    "No sustituye la GTF ni una certificación oficial."
)

_SCHEMA_VERSION = "1.0"


def _status_to_attestation_eligible(status: str) -> bool:
    return status == "CONSISTENTE"


def _public_status(status: str) -> str:
    if status not in ALLOWED_STATUSES:
        return "POR_REVISAR"
    return status


def _as_number(value: str | None) -> float | None:
    if value is None:
        return None
    return float(value)


def search_catalog(query: str) -> dict[str, Any]:
    detected_type, results = search_identifiers(query)
    return {
        "query": query,
        "detected_type": detected_type,
        "count": len(results),
        "results": [
            {
                "trace_id": str(item["trace_id"]),
                "identifier_type": item["identifier_type"],
                "identifier": item["identifier"],
                "codigo_arbol": item["codigo_arbol"],
                "parcela_corta": item["parcela_corta"],
                "titulo_habilitante": item["titulo_habilitante"],
                "especie": item["especie"],
                "status": _public_status(item["status"]),
            }
            for item in results
        ],
    }


def get_catalog_verification(trace_id: str) -> dict[str, Any] | None:
    detail = get_catalog_trace(trace_id)
    if detail is None:
        return None

    lineage_stages = sorted({entry["stage"] for entry in detail["lineage"]})
    status = _public_status(detail["status"])
    payload = {
        "schema_version": _SCHEMA_VERSION,
        "case_id": detail["trace_id"],
        "verification_status": status,
        "attestation_eligible": _status_to_attestation_eligible(status),
        "titular": detail["origin"]["titular"],
        "titulo_habilitante": detail["origin"]["titulo_habilitante"],
        "parcela_corta": detail["origin"]["parcela_corta"],
        "codigo_arbol": detail["origin"]["codigo_arbol"],
        "plan_operativo": detail["origin"]["plan_operativo"],
        "resolucion": detail["origin"]["resolucion"],
        "especie_censo": detail["species"]["census"],
        "especie_supervision": detail["species"]["supervision"],
        "volumen_censo_m3": _as_number(detail["volumes_m3"]["census"]),
        "volumen_tala_m3": _as_number(detail["volumes_m3"]["felling"]),
        "volumen_trozado_m3": _as_number(detail["volumes_m3"]["bucking"]),
        "trozas": detail["logs"],
        "gtf": detail["gtf"],
        "validaciones": [
            {"name": check["name"], "status": check["status"]}
            for check in detail["checks"]
        ],
        "lineage_stages": lineage_stages,
        "evidence_hash_sha256": detail["evidence_hash_sha256"],
        "disclaimer": _DISCLAIMER,
        "balance": (
            {
                "available": True,
                "species": detail["balance"]["species"],
                "authorized_m3": _as_number(detail["balance"]["authorized_m3"]),
                "extracted_reported_m3": _as_number(detail["balance"]["extracted_reported_m3"]),
                "remaining_reported_m3": _as_number(detail["balance"]["remaining_reported_m3"]),
            }
            if detail["balance"] is not None
            else {"available": False}
        ),
    }
    return payload


def get_catalog_health() -> dict[str, Any]:
    count = get_catalog_trace_count()
    return {
        "catalog_available": True,
        "catalog_trace_count": count,
    }
