"""
app/repository.py

Capa de acceso a datos sobre db/huella_origen.db (solo lectura).

Funciones públicas:
- list_cases() -> list[dict]
- get_case_detail(case_id: str) -> dict | None
"""

from __future__ import annotations

import json
from contextlib import closing
from typing import Any

from app.database import open_readonly_connection


def _row_to_dict(row: Any) -> dict:
    """Convierte un sqlite3.Row en dict estándar."""
    return dict(row)


def list_cases() -> list[dict]:
    """
    Devuelve los dos expedientes con los campos de resumen.

    Campos incluidos
    ----------------
    case_id, case_type, codigo_arbol, parcela_corta,
    verification_status, attestation_eligible (bool),
    especie_censo, especie_supervision, evidence_hash_sha256
    """
    sql = """
        SELECT
            case_id,
            case_type,
            codigo_arbol,
            parcela_corta,
            verification_status,
            attestation_eligible,
            especie_censo,
            especie_supervision,
            evidence_hash_sha256
        FROM cases
        ORDER BY case_type, case_id
    """
    with closing(open_readonly_connection()) as conn:
        rows = conn.execute(sql).fetchall()

    result = []
    for row in rows:
        item = _row_to_dict(row)
        item["attestation_eligible"] = bool(item["attestation_eligible"])
        result.append(item)

    return result


def get_case_detail(case_id: str) -> dict | None:
    """
    Devuelve la estructura anidada completa de un expediente.

    Retorna None si el case_id no existe.

    Todas las consultas usan placeholders; nunca se interpola
    case_id directamente en el SQL.
    """
    with closing(open_readonly_connection()) as conn:
        # ── Fila principal ────────────────────────────────────────────
        case_row = conn.execute(
            """
            SELECT
                case_id,
                case_type,
                schema_version,
                verification_status,
                attestation_eligible,
                titular,
                titulo_habilitante,
                parcela_corta,
                codigo_arbol,
                plan_operativo,
                resolucion,
                especie_censo,
                especie_supervision,
                volumen_censo_m3,
                volumen_tala_m3,
                volumen_trozado_m3,
                diferencia_tala_trozado_m3,
                observations,
                evidence_hash_sha256
            FROM cases
            WHERE case_id = ?
            """,
            (case_id,),
        ).fetchone()

        if case_row is None:
            return None

        case = _row_to_dict(case_row)

        # ── Checks ───────────────────────────────────────────────────
        check_rows = conn.execute(
            """
            SELECT check_name, check_status, raw_value_json
            FROM case_checks
            WHERE case_id = ?
            ORDER BY check_name
            """,
            (case_id,),
        ).fetchall()

        checks = [
            {
                "name": r["check_name"],
                "status": r["check_status"],
                "value": json.loads(r["raw_value_json"]),
            }
            for r in check_rows
        ]

        # ── Lineage ──────────────────────────────────────────────────
        source_rows = conn.execute(
            """
            SELECT stage, source_path
            FROM case_sources
            WHERE case_id = ?
            ORDER BY stage
            """,
            (case_id,),
        ).fetchall()

        lineage = [
            {"stage": r["stage"], "source": r["source_path"]}
            for r in source_rows
        ]

        # ── Trozas ───────────────────────────────────────────────────
        log_rows = conn.execute(
            """
            SELECT codigo_troza
            FROM case_logs
            WHERE case_id = ?
            ORDER BY codigo_troza
            """,
            (case_id,),
        ).fetchall()

        logs = [r["codigo_troza"] for r in log_rows]

        # ── GTF ──────────────────────────────────────────────────────
        gtf_rows = conn.execute(
            """
            SELECT numero_gtf
            FROM case_gtf
            WHERE case_id = ?
            ORDER BY numero_gtf
            """,
            (case_id,),
        ).fetchall()

        gtf = [r["numero_gtf"] for r in gtf_rows]

        # ── Conteo de registros por stage ────────────────────────────
        record_count_rows = conn.execute(
            """
            SELECT stage, COUNT(*) AS cnt
            FROM case_records
            WHERE case_id = ?
            GROUP BY stage
            ORDER BY stage
            """,
            (case_id,),
        ).fetchall()

        record_counts = {r["stage"]: r["cnt"] for r in record_count_rows}

    # ── Estructura anidada ────────────────────────────────────────────
    return {
        "case_id": case["case_id"],
        "case_type": case["case_type"],
        "status": case["verification_status"],
        "attestation_eligible": bool(case["attestation_eligible"]),
        "origin": {
            "titular": case["titular"],
            "titulo_habilitante": case["titulo_habilitante"],
            "parcela_corta": case["parcela_corta"],
            "codigo_arbol": case["codigo_arbol"],
            "plan_operativo": case["plan_operativo"],
            "resolucion": case["resolucion"],
        },
        "species": {
            "census": case["especie_censo"],
            "supervision": case["especie_supervision"],
        },
        "volumes_m3": {
            "census": case["volumen_censo_m3"],
            "felling": case["volumen_tala_m3"],
            "bucking": case["volumen_trozado_m3"],
            "felling_minus_bucking": case["diferencia_tala_trozado_m3"],
        },
        "checks": checks,
        "lineage": lineage,
        "logs": logs,
        "gtf": gtf,
        "record_counts": record_counts,
        "evidence_hash_sha256": case["evidence_hash_sha256"],
    }
