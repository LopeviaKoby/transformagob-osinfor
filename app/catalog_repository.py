"""
Acceso de solo lectura a db/huella_catalog.db.
"""

from __future__ import annotations

import json
from contextlib import closing
from typing import Any

from app.catalog_database import open_catalog_readonly_connection
from scripts.catalog_normalization import (
    normalize_gtf,
    normalize_log_code,
    normalize_title,
    normalize_tree_code,
)

ALLOWED_STATUSES = {
    "CONSISTENTE",
    "POR_REVISAR",
    "INCOMPLETO",
    "NO_EVALUADO",
    "INCONSISTENTE",
}

SEARCH_TYPES = ("GTF", "TROZA", "ARBOL", "TITULO")

_TYPE_PRIORITY = {
    "ARBOL": 1,
    "GTF": 2,
    "TITULO": 3,
    "TROZA": 4,
}

_STATUS_PRIORITY = {
    "CONSISTENTE": 1,
    "POR_REVISAR": 2,
    "INCONSISTENTE": 2,
    "NO_EVALUADO": 3,
    "INCOMPLETO": 4,
}


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row)


def get_catalog_trace_count() -> int:
    with closing(open_catalog_readonly_connection()) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM trace_catalog"
        ).fetchone()
    return int(row["cnt"])


def _normalize_search_value(identifier_type: str, query: str) -> str:
    if identifier_type == "GTF":
        normalized = normalize_gtf(query)
    elif identifier_type == "TROZA":
        normalized = normalize_log_code(query)
    elif identifier_type == "ARBOL":
        normalized = normalize_tree_code(query)
    else:
        normalized = normalize_title(query)

    if normalized is None:
        raise ValueError("Consulta inválida")
    return normalized


def detect_identifier_type(query: str) -> str:
    stripped = query.strip()
    upper = stripped.upper()
    if any(prefix in upper for prefix in ("GOREMAD", "OSINFOR", "DRFFS", "P-MAD", "TAH")):
        return "TITULO"
    if stripped.isdigit():
        return "ARBOL"
    if stripped.count("-") >= 1 and any(ch.isdigit() for ch in stripped):
        if stripped.startswith("0") or stripped.count("-") >= 2:
            return "GTF"
    if (
        "/" in stripped
        or any(separator in upper for separator in ("-A", "-B", "-C", "-D"))
        or any(f" {letter}" in upper for letter in ("A", "B", "C", "D"))
    ):
        return "TROZA"
    return "TITULO"


def search_identifiers(query: str, limit: int = 20) -> tuple[str, list[dict[str, Any]]]:
    detected_type = detect_identifier_type(query)
    ordered_types = [detected_type] + [item for item in SEARCH_TYPES if item != detected_type]
    rows: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()

    with closing(open_catalog_readonly_connection()) as conn:
        for identifier_type in ordered_types:
            normalized = _normalize_search_value(identifier_type, query)
            result_rows = conn.execute(
                """
                SELECT
                    si.trace_id,
                    si.identifier_type,
                    COALESCE(si.display_value, si.identifier_value_norm) AS identifier,
                    tc.codigo_arbol_norm AS codigo_arbol,
                    tc.parcela_corta_norm AS parcela_corta,
                    tc.titulo_habilitante_norm AS titulo_habilitante,
                    COALESCE(
                        tc.especie_censo_norm,
                        tc.especie_operacion_norm,
                        tc.especie_supervision_norm
                    ) AS especie,
                    tc.verification_status AS status
                FROM search_identifiers AS si
                INNER JOIN trace_catalog AS tc
                    ON tc.trace_id = si.trace_id
                WHERE si.identifier_type = ?
                  AND si.identifier_value_norm = ?
                ORDER BY
                    si.identifier_type,
                    tc.parcela_corta_norm,
                    tc.codigo_arbol_norm
                LIMIT ?
                """,
                (identifier_type, normalized, limit),
            ).fetchall()

            raw_items = [_row_to_dict(row) for row in result_rows]
            if identifier_type == "GTF":
                grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
                for item in raw_items:
                    group_key = (
                        item["identifier"],
                        item["titulo_habilitante"],
                        item["parcela_corta"],
                    )
                    current = grouped.get(group_key)
                    if current is None:
                        grouped[group_key] = item
                        continue
                    current_rank = _STATUS_PRIORITY.get(current["status"], 99)
                    candidate_rank = _STATUS_PRIORITY.get(item["status"], 99)
                    if candidate_rank < current_rank:
                        grouped[group_key] = item
                        continue
                    if candidate_rank == current_rank and (item["codigo_arbol"] or "") < (current["codigo_arbol"] or ""):
                        grouped[group_key] = item
                raw_items = list(grouped.values())

            for item in raw_items:
                key = (
                    item["trace_id"],
                    item["identifier_type"],
                    item["identifier"],
                )
                if key in seen:
                    continue
                seen.add(key)
                rows.append(item)

            if rows:
                break

    rows.sort(
        key=lambda item: (
            _TYPE_PRIORITY.get(item["identifier_type"], 99),
            item["parcela_corta"] or "",
            item["codigo_arbol"] or "",
        )
    )
    return detected_type, rows[:limit]


def get_catalog_trace(trace_id: str) -> dict[str, Any] | None:
    if not trace_id.isdigit():
        return None

    with closing(open_catalog_readonly_connection()) as conn:
        trace_row = conn.execute(
            """
            SELECT
                tc.trace_id,
                tc.title_id,
                tc.titulo_habilitante_norm,
                tc.parcela_corta_norm,
                tc.codigo_arbol_norm,
                tc.especie_censo_norm,
                tc.especie_supervision_norm,
                tc.especie_operacion_norm,
                tc.volumen_censo_text,
                tc.volumen_tala_text,
                tc.volumen_trozado_text,
                tc.verification_status,
                tc.gtf_count,
                tc.evidence_hash_sha256,
                tc.public_payload_json,
                tc.lineage_json,
                t.titular_norm,
                t.plan_operativo_norm,
                t.resolucion_norm
            FROM trace_catalog AS tc
            INNER JOIN titles AS t
                ON t.title_id = tc.title_id
            WHERE tc.trace_id = ?
            """,
            (trace_id,),
        ).fetchone()

        if trace_row is None:
            return None

        payload = json.loads(trace_row["public_payload_json"])
        lineage = json.loads(trace_row["lineage_json"])
        checks_rows = conn.execute(
            """
            SELECT check_name, check_status, value_json
            FROM trace_checks
            WHERE trace_id = ?
            ORDER BY check_name
            """,
            (trace_id,),
        ).fetchall()
        checks = [
            {
                "name": row["check_name"],
                "status": row["check_status"],
                "value": json.loads(row["value_json"]),
            }
            for row in checks_rows
        ]

        balance_row = conn.execute(
            """
            SELECT
                especie_norm,
                volumen_autorizado_text,
                volumen_extraido_text,
                saldo_reportado_text
            FROM species_balances
            WHERE titulo_habilitante_norm = ?
              AND parcela_corta_norm = ?
              AND especie_norm = ?
              AND product_type = 'MADERA EN ROLLO'
            LIMIT 1
            """,
            (
                trace_row["titulo_habilitante_norm"],
                trace_row["parcela_corta_norm"],
                trace_row["especie_censo_norm"],
            ),
        ).fetchone()

    return {
        "trace_id": str(trace_row["trace_id"]),
        "title_id": trace_row["title_id"],
        "status": trace_row["verification_status"],
        "origin": {
            "titular": trace_row["titular_norm"],
            "titulo_habilitante": trace_row["titulo_habilitante_norm"],
            "parcela_corta": trace_row["parcela_corta_norm"],
            "codigo_arbol": trace_row["codigo_arbol_norm"],
            "plan_operativo": trace_row["plan_operativo_norm"],
            "resolucion": trace_row["resolucion_norm"],
        },
        "species": {
            "census": trace_row["especie_censo_norm"],
            "supervision": trace_row["especie_supervision_norm"],
            "operation": trace_row["especie_operacion_norm"],
        },
        "volumes_m3": {
            "census": trace_row["volumen_censo_text"],
            "felling": trace_row["volumen_tala_text"],
            "bucking": trace_row["volumen_trozado_text"],
        },
        "checks": checks,
        "lineage": lineage,
        "logs": payload.get("trozas", []),
        "gtf": payload.get("gtf", []),
        "evidence_hash_sha256": trace_row["evidence_hash_sha256"],
        "balance": (
            {
                "species": balance_row["especie_norm"],
                "authorized_m3": balance_row["volumen_autorizado_text"],
                "extracted_reported_m3": balance_row["volumen_extraido_text"],
                "remaining_reported_m3": balance_row["saldo_reportado_text"],
            }
            if balance_row is not None
            else None
        ),
    }
