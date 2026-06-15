"""
Construccion segura de db/huella_catalog.db.
"""

from __future__ import annotations

import json
import os
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.catalog_normalization import (
    canonical_json_hash,
    clean_text,
    composite_balance_key,
    composite_tree_key,
)
from scripts.catalog_parsers import (
    build_species_aliases,
    collect_source_inventory,
    file_sha256,
    parse_balance_pdf,
    parse_census_workbook,
    parse_operations_workbook,
    parse_supervision_workbook,
    resolve_real_sources,
    resolve_repo_root,
)


REQUIRED_CHECKS = [
    "census_present",
    "felling_present",
    "logs_present",
    "dispatch_present",
    "gtf_present",
    "dispatched_logs_registered",
    "supervision_species_match",
    "operation_species_match",
    "census_volume_vs_felling",
    "felling_volume_vs_logs",
    "species_balance_available",
    "species_balance_non_negative",
    "gtf_scope_consistent",
    "source_r_interpreted",
]

EXPECTED_INDEXES = {
    "idx_search_identifiers_type_value",
    "idx_dispatches_numero_gtf",
    "idx_logs_codigo_troza",
    "idx_trace_catalog_tree",
    "idx_trace_catalog_tree_simple",
    "idx_species_balances_scope",
    "idx_trace_catalog_status",
}


def decimal_or_none(value: str | None) -> Decimal | None:
    return Decimal(value) if value is not None else None


def row_score(record: dict[str, Any]) -> int:
    fields = [
        "especie_original",
        "especie_norm",
        "volumen_text",
        "diametro_mayor_text",
        "diametro_menor_text",
        "longitud_text",
        "observaciones_private",
        "volumen_censo_text",
    ]
    return sum(1 for field in fields if clean_text(record.get(field)))


def dedupe_records(
    records: list[dict[str, Any]],
    key_field: str,
    source_label: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    chosen: dict[str, dict[str, Any]] = {}
    rejected: list[dict[str, Any]] = []

    for record in records:
        key = record.get(key_field)
        if not key:
            rejected.append(
                {
                    "reason": "missing_dedupe_key",
                    "source": source_label,
                    "record": record,
                }
            )
            continue

        previous = chosen.get(key)
        if previous is None or row_score(record) > row_score(previous):
            if previous is not None:
                rejected.append(
                    {
                        "reason": "duplicate_lower_completeness",
                        "source": source_label,
                        "record": previous,
                    }
                )
            chosen[key] = record
        else:
            rejected.append(
                {
                    "reason": "duplicate_lower_completeness",
                    "source": source_label,
                    "record": record,
                }
            )

    return list(chosen.values()), rejected


def build_title_registry(
    census_rows: list[dict[str, Any]],
    felling_rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}

    for row in census_rows:
        key = row["titulo_habilitante_norm"]
        registry.setdefault(
            key,
            {
                "titulo_habilitante_original": row["titulo_habilitante_original"],
                "titulo_habilitante_norm": key,
                "titular_original": row.get("titular_original"),
                "titular_norm": row.get("titular_norm"),
                "modalidad_original": None,
                "plan_operativo_original": row.get("plan_operativo_original"),
                "plan_operativo_norm": row.get("plan_operativo_norm"),
                "resolucion_original": row.get("resolucion_original"),
                "resolucion_norm": row.get("resolucion_norm"),
            },
        )

    for row in felling_rows:
        key = row["titulo_habilitante_norm"]
        registry.setdefault(
            key,
            {
                "titulo_habilitante_original": row["titulo_habilitante_original"],
                "titulo_habilitante_norm": key,
                "titular_original": None,
                "titular_norm": None,
                "modalidad_original": None,
                "plan_operativo_original": None,
                "plan_operativo_norm": None,
                "resolucion_original": None,
                "resolucion_norm": None,
            },
        )

    return registry


def build_public_payload(
    trace: dict[str, Any],
    checks: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    public_checks = [
        {"name": name, "status": value["status"]}
        for name, value in checks.items()
    ]
    public_checks.sort(key=lambda item: item["name"])

    return {
        "titulo_habilitante": trace["titulo_habilitante_norm"],
        "parcela_corta": trace["parcela_corta_norm"],
        "codigo_arbol": trace["codigo_arbol_norm"],
        "especie_censo": trace.get("especie_censo_norm"),
        "especie_supervision": trace.get("especie_supervision_norm"),
        "especie_operacion": trace.get("especie_operacion_norm"),
        "volumen_censo_m3": trace.get("volumen_censo_text"),
        "volumen_tala_m3": trace.get("volumen_tala_text"),
        "volumen_trozado_m3": trace.get("volumen_trozado_text"),
        "trozas": sorted(trace.get("trozas", [])),
        "gtf": sorted(trace.get("gtf", [])),
        "verification_status": trace["verification_status"],
        "lineage": trace["lineage"],
        "checks": public_checks,
    }


def compute_checks_and_status(
    trace: dict[str, Any],
    gtf_scope_map: dict[str, set[tuple[str, str]]],
    balance_entry: dict[str, Any] | None,
) -> tuple[dict[str, dict[str, Any]], str]:
    checks: dict[str, dict[str, Any]] = {}

    def set_check(name: str, status: str, value: Any) -> None:
        checks[name] = {"status": status, "value": value}

    census_present = trace.get("tree") is not None
    felling_present = trace.get("felling") is not None
    logs_present = bool(trace.get("logs"))
    dispatch_present = bool(trace.get("dispatches"))
    gtf_present = bool(trace.get("gtf"))

    set_check("census_present", "PASS" if census_present else "NOT_EVALUATED", census_present)
    set_check("felling_present", "PASS" if felling_present else "NOT_EVALUATED", felling_present)
    set_check("logs_present", "PASS" if logs_present else "NOT_EVALUATED", logs_present)
    set_check("dispatch_present", "PASS" if dispatch_present else "NOT_EVALUATED", dispatch_present)
    set_check("gtf_present", "PASS" if gtf_present else "NOT_EVALUATED", gtf_present)

    if dispatch_present:
        registered = all(dispatch.get("codigo_troza_norm") in trace.get("troza_set", set()) for dispatch in trace["dispatches"])
        set_check("dispatched_logs_registered", "PASS" if registered else "FAIL", registered)
    else:
        set_check("dispatched_logs_registered", "NOT_EVALUATED", None)

    tree_species = trace.get("especie_censo_norm")
    supervision_species = trace.get("especie_supervision_norm")
    operation_species = trace.get("especie_operacion_norm")

    if supervision_species is None:
        set_check("supervision_species_match", "NOT_EVALUATED", None)
    elif tree_species and supervision_species == tree_species:
        set_check("supervision_species_match", "PASS", True)
    elif tree_species and supervision_species != tree_species:
        set_check("supervision_species_match", "FAIL", False)
    else:
        set_check("supervision_species_match", "NOT_EVALUATED", None)

    if operation_species is None:
        set_check("operation_species_match", "NOT_EVALUATED", None)
    elif tree_species and operation_species == tree_species:
        set_check("operation_species_match", "PASS", True)
    elif tree_species and operation_species != tree_species:
        set_check("operation_species_match", "FAIL", False)
    else:
        set_check("operation_species_match", "NOT_EVALUATED", None)

    census_volume = decimal_or_none(trace.get("volumen_censo_text"))
    felling_volume = decimal_or_none(trace.get("volumen_tala_text"))
    logs_volume = decimal_or_none(trace.get("volumen_trozado_text"))

    if census_volume is not None and felling_volume is not None:
        set_check(
            "census_volume_vs_felling",
            "PASS" if census_volume >= felling_volume else "FAIL",
            str(census_volume - felling_volume),
        )
    else:
        set_check("census_volume_vs_felling", "NOT_EVALUATED", None)

    if felling_volume is not None and logs_volume is not None:
        set_check(
            "felling_volume_vs_logs",
            "PASS" if felling_volume >= logs_volume else "FAIL",
            str(felling_volume - logs_volume),
        )
    else:
        set_check("felling_volume_vs_logs", "NOT_EVALUATED", None)

    if balance_entry is None:
        set_check("species_balance_available", "NOT_EVALUATED", None)
        set_check("species_balance_non_negative", "NOT_EVALUATED", None)
    else:
        set_check("species_balance_available", "PASS", True)
        balance_value = decimal_or_none(balance_entry.get("saldo_reportado_text"))
        set_check(
            "species_balance_non_negative",
            "PASS" if balance_value is not None and balance_value >= 0 else "FAIL",
            balance_entry.get("saldo_reportado_text"),
        )

    if gtf_present:
        consistent = all(
            len(gtf_scope_map.get(gtf, set())) == 1
            for gtf in trace["gtf"]
        )
        set_check("gtf_scope_consistent", "PASS" if consistent else "FAIL", consistent)
    else:
        set_check("gtf_scope_consistent", "NOT_EVALUATED", None)

    set_check("source_r_interpreted", "NOT_EVALUATED", None)

    fail_exists = any(value["status"] == "FAIL" for value in checks.values())
    if fail_exists:
        return checks, "POR_REVISAR"

    missing_chain = not (felling_present and logs_present and dispatch_present and gtf_present)
    if missing_chain:
        return checks, "INCOMPLETO"

    central_checks = {
        "supervision_species_match",
        "operation_species_match",
        "census_volume_vs_felling",
        "felling_volume_vs_logs",
    }
    if any(checks[name]["status"] == "NOT_EVALUATED" for name in central_checks):
        return checks, "NO_EVALUADO"

    return checks, "CONSISTENTE"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_schema(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def ensure_expected_sources(paths: list[Path], repo_root: Path) -> None:
    if len(paths) != 8:
        raise RuntimeError(f"Se esperaban 8 fuentes; se encontraron {len(paths)}")
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Fuente no encontrada: {path.relative_to(repo_root).as_posix()}")


def build() -> dict[str, Any]:
    repo_root = resolve_repo_root()
    db_dir = repo_root / "db"
    staging_dir = repo_root / "staging" / "catalog"
    schema_path = db_dir / "catalog_schema.sql"
    final_db = db_dir / "huella_catalog.db"
    temp_db = db_dir / "huella_catalog.db.tmp"

    source_paths = resolve_real_sources(repo_root)
    ensure_expected_sources(source_paths, repo_root)
    inventory = collect_source_inventory(repo_root)
    write_json(staging_dir / "source_inventory.json", inventory)

    census_result = parse_census_workbook(repo_root / "raw/censo/censo_forestal.xlsx", repo_root)
    supervision_result = parse_supervision_workbook(
        repo_root / "raw/muestra/muestra_supervisada.xlsx",
        repo_root=repo_root,
    )
    aliases = build_species_aliases(census_result["loaded"], supervision_result["loaded"])
    supervision_result = parse_supervision_workbook(
        repo_root / "raw/muestra/muestra_supervisada.xlsx",
        aliases,
        repo_root,
    )

    operations_results = [
        parse_operations_workbook(repo_root / "raw/libro/pc01/libro_operaciones_pc01.xlsx", aliases, repo_root),
        parse_operations_workbook(repo_root / "raw/libro/pc01/libro_operaciones_pc02.xlsx", aliases, repo_root),
        parse_operations_workbook(repo_root / "raw/libro/pc01/libro_operaciones_pc03.xlsx", aliases, repo_root),
    ]

    balance_results = [
        parse_balance_pdf(repo_root / "raw/balance/pc01/balance_extraccion_pc01.pdf", aliases, repo_root),
        parse_balance_pdf(repo_root / "raw/balance/pc01/balance_extraccion_pc02.pdf", aliases, repo_root),
        parse_balance_pdf(repo_root / "raw/balance/pc01/balance_extraccion_pc03.pdf", aliases, repo_root),
    ]

    write_json(
        staging_dir / "balance_extraction_text.json",
        [
            {
                "source": source_path.relative_to(repo_root).as_posix(),
                "pages": result["extracted_text"],
            }
            for source_path, result in zip(source_paths[-3:], balance_results)
        ],
    )

    trees, rejected_tree_dupes = dedupe_records(census_result["loaded"], "composite_tree_key", "census")
    supervisions, rejected_supervision_dupes = dedupe_records(supervision_result["loaded"], "composite_tree_key", "supervision")
    fellings_raw = [item for result in operations_results for item in result["fellings"]]
    logs_raw = [item for result in operations_results for item in result["logs"]]
    dispatches_raw = [item for result in operations_results for item in result["dispatches"]]
    balances_raw = [item for result in balance_results for item in result["loaded"]]

    fellings, rejected_felling_dupes = dedupe_records(fellings_raw, "composite_tree_key", "fellings")
    logs, rejected_log_dupes = dedupe_records(logs_raw, "composite_log_key", "logs")
    for item in dispatches_raw:
        item["dispatch_dedupe_key"] = "||".join(
            [
                item["composite_log_key"],
                item.get("numero_gtf_norm") or "",
                item.get("codigo_despacho_norm") or "",
            ]
        )
    dispatches, rejected_dispatch_dupes = dedupe_records(dispatches_raw, "dispatch_dedupe_key", "dispatches")
    for item in balances_raw:
        item["balance_dedupe_key"] = "||".join(
            [item["composite_balance_key"], item["product_type"]]
        )
    balances, rejected_balance_dupes = dedupe_records(balances_raw, "balance_dedupe_key", "balances")

    title_registry = build_title_registry(trees, fellings)
    trees_by_key = {item["composite_tree_key"]: item for item in trees}
    supervisions_by_key = {item["composite_tree_key"]: item for item in supervisions}
    fellings_by_key = {item["composite_tree_key"]: item for item in fellings}

    logs_by_tree: dict[str, list[dict[str, Any]]] = defaultdict(list)
    logs_by_log_key: dict[str, dict[str, Any]] = {}
    for item in logs:
        logs_by_tree[item["composite_tree_key"]].append(item)
        logs_by_log_key[item["composite_log_key"]] = item

    dispatches_by_tree: dict[str, list[dict[str, Any]]] = defaultdict(list)
    gtf_scope_map: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for item in dispatches:
        dispatches_by_tree[item["composite_tree_key"]].append(item)
        if item.get("numero_gtf_norm"):
            gtf_scope_map[item["numero_gtf_norm"]].add(
                (item["titulo_habilitante_norm"], item["parcela_corta_norm"])
            )

    balances_by_preferred_key: dict[str, dict[str, Any]] = {}
    for item in balances:
        if item.get("product_type") != "MADERA EN ROLLO":
            continue
        balances_by_preferred_key[item["composite_balance_key"]] = item

    trace_keys = sorted(
        set(trees_by_key)
        | set(fellings_by_key)
        | set(logs_by_tree)
        | set(dispatches_by_tree)
    )
    traces: list[dict[str, Any]] = []
    trace_checks_payload: list[tuple[str, dict[str, dict[str, Any]]]] = []

    for key in trace_keys:
        tree = trees_by_key.get(key)
        felling = fellings_by_key.get(key)
        supervision = supervisions_by_key.get(key)
        tree_logs = sorted(logs_by_tree.get(key, []), key=lambda row: row["codigo_troza_norm"])
        tree_dispatches = sorted(dispatches_by_tree.get(key, []), key=lambda row: (row.get("numero_gtf_norm") or "", row["codigo_troza_norm"]))
        troza_set = {item["codigo_troza_norm"] for item in tree_logs}
        gtf_numbers = sorted({item["numero_gtf_norm"] for item in tree_dispatches if item.get("numero_gtf_norm")})

        exemplar = tree or felling or (tree_logs[0] if tree_logs else tree_dispatches[0])
        assert exemplar is not None

        operation_species_candidates = {
            item["especie_norm"]
            for item in ([felling] if felling else []) + tree_logs
            if item.get("especie_norm")
        }
        operation_species = None
        if len(operation_species_candidates) == 1:
            operation_species = next(iter(operation_species_candidates))
        elif tree and tree.get("especie_norm") in operation_species_candidates:
            operation_species = tree["especie_norm"]

        balance_key = composite_balance_key(
            exemplar["titulo_habilitante_norm"],
            exemplar["parcela_corta_norm"],
            tree.get("especie_norm") if tree else operation_species,
        )
        balance_entry = balances_by_preferred_key.get(balance_key) if balance_key else None

        volumen_trozado = None
        if tree_logs:
            total = sum(decimal_or_none(item["volumen_text"]) or Decimal("0") for item in tree_logs)
            volumen_trozado = format(total.normalize(), "f").rstrip("0").rstrip(".")

        lineage = []
        for stage, record in (
            ("censo", tree),
            ("muestra_supervisada", supervision),
            ("tala", felling),
        ):
            if record:
                lineage.append(
                    {
                        "stage": stage,
                        "source_relative_path": record["source_relative_path"],
                        "source_sheet": record.get("source_sheet"),
                        "source_row_number": record.get("source_row_number"),
                    }
                )
        for item in tree_logs:
            lineage.append(
                {
                    "stage": "trozado",
                    "source_relative_path": item["source_relative_path"],
                    "source_sheet": item.get("source_sheet"),
                    "source_row_number": item.get("source_row_number"),
                }
            )
        for item in tree_dispatches:
            lineage.append(
                {
                    "stage": "despacho",
                    "source_relative_path": item["source_relative_path"],
                    "source_sheet": item.get("source_sheet"),
                    "source_row_number": item.get("source_row_number"),
                }
            )
        if balance_entry:
            lineage.append(
                {
                    "stage": "balance",
                    "source_relative_path": balance_entry["source_relative_path"],
                    "source_sheet": balance_entry.get("source_sheet"),
                    "source_row_number": balance_entry.get("source_row_number"),
                }
            )

        trace = {
            "tree": tree,
            "felling": felling,
            "logs": tree_logs,
            "dispatches": tree_dispatches,
            "troza_set": troza_set,
            "gtf": gtf_numbers,
            "title_id": None,
            "titulo_habilitante_norm": exemplar["titulo_habilitante_norm"],
            "parcela_corta_norm": exemplar["parcela_corta_norm"],
            "codigo_arbol_norm": exemplar["codigo_arbol_norm"],
            "composite_tree_key": key,
            "especie_censo_norm": tree.get("especie_norm") if tree else None,
            "especie_supervision_norm": supervision.get("especie_supervision_norm") if supervision else None,
            "especie_operacion_norm": operation_species,
            "volumen_censo_text": tree.get("volumen_censo_text") if tree else None,
            "volumen_tala_text": felling.get("volumen_text") if felling else None,
            "volumen_trozado_text": volumen_trozado,
            "trozas": [item["codigo_troza_norm"] for item in tree_logs],
            "lineage": lineage,
        }
        checks, status = compute_checks_and_status(trace, gtf_scope_map, balance_entry)
        trace["verification_status"] = status
        public_payload = build_public_payload(trace, checks)
        trace["public_payload_json"] = json.dumps(public_payload, ensure_ascii=False, sort_keys=True)
        trace["evidence_hash_sha256"] = canonical_json_hash(public_payload)
        traces.append(trace)
        trace_checks_payload.append((key, checks))

    source_stats = {
        "raw/censo/censo_forestal.xlsx": {
            "processed_rows": len(census_result["loaded"]) + len(census_result["rejected"]),
            "loaded_rows": len(trees),
            "rejected_rows": len(census_result["rejected"]) + len(rejected_tree_dupes),
        },
        "raw/muestra/muestra_supervisada.xlsx": {
            "processed_rows": len(supervision_result["loaded"]) + len(supervision_result["rejected"]),
            "loaded_rows": len(supervisions),
            "rejected_rows": len(supervision_result["rejected"]) + len(rejected_supervision_dupes),
        },
    }

    for result, rel in zip(
        operations_results,
        [
            "raw/libro/pc01/libro_operaciones_pc01.xlsx",
            "raw/libro/pc01/libro_operaciones_pc02.xlsx",
            "raw/libro/pc01/libro_operaciones_pc03.xlsx",
        ],
    ):
        source_stats[rel] = {
            "processed_rows": len(result["fellings"]) + len(result["logs"]) + len(result["dispatches"]) + len(result["rejected"]),
            "loaded_rows": 0,
            "rejected_rows": len(result["rejected"]),
        }
    source_stats["raw/libro/pc01/libro_operaciones_pc01.xlsx"]["loaded_rows"] += sum(
        1 for row in fellings if row["source_relative_path"] == "raw/libro/pc01/libro_operaciones_pc01.xlsx"
    ) + sum(
        1 for row in logs if row["source_relative_path"] == "raw/libro/pc01/libro_operaciones_pc01.xlsx"
    ) + sum(
        1 for row in dispatches if row["source_relative_path"] == "raw/libro/pc01/libro_operaciones_pc01.xlsx"
    )
    source_stats["raw/libro/pc01/libro_operaciones_pc02.xlsx"]["loaded_rows"] += sum(
        1 for row in fellings if row["source_relative_path"] == "raw/libro/pc01/libro_operaciones_pc02.xlsx"
    ) + sum(
        1 for row in logs if row["source_relative_path"] == "raw/libro/pc01/libro_operaciones_pc02.xlsx"
    ) + sum(
        1 for row in dispatches if row["source_relative_path"] == "raw/libro/pc01/libro_operaciones_pc02.xlsx"
    )
    source_stats["raw/libro/pc01/libro_operaciones_pc03.xlsx"]["loaded_rows"] += sum(
        1 for row in fellings if row["source_relative_path"] == "raw/libro/pc01/libro_operaciones_pc03.xlsx"
    ) + sum(
        1 for row in logs if row["source_relative_path"] == "raw/libro/pc01/libro_operaciones_pc03.xlsx"
    ) + sum(
        1 for row in dispatches if row["source_relative_path"] == "raw/libro/pc01/libro_operaciones_pc03.xlsx"
    )

    for result, rel in zip(
        balance_results,
        [
            "raw/balance/pc01/balance_extraccion_pc01.pdf",
            "raw/balance/pc01/balance_extraccion_pc02.pdf",
            "raw/balance/pc01/balance_extraccion_pc03.pdf",
        ],
    ):
        source_stats[rel] = {
            "processed_rows": len(result["loaded"]) + len(result["rejected"]),
            "loaded_rows": sum(1 for row in balances if row["source_relative_path"] == rel),
            "rejected_rows": len(result["rejected"]) + sum(1 for row in rejected_balance_dupes if row["record"]["source_relative_path"] == rel),
        }

    if temp_db.exists():
        temp_db.unlink()

    schema_sql = load_schema(schema_path)
    connection = sqlite3.connect(temp_db)
    connection.row_factory = sqlite3.Row

    try:
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            connection.executescript(schema_sql)
            connection.executemany(
                """
                INSERT INTO build_metadata (metadata_key, metadata_value)
                VALUES (?, ?)
                """,
                [
                    ("schema_version", "1.0"),
                    ("source_count", str(len(source_paths))),
                    ("build_target", "db/huella_catalog.db"),
                ],
            )

            source_id_by_path: dict[str, int] = {}
            for source in inventory["sources"]:
                stats = source_stats[source["relative_path"]]
                cursor = connection.execute(
                    """
                    INSERT INTO data_sources (
                        source_kind,
                        source_name,
                        relative_path,
                        sha256,
                        size_bytes,
                        workbook_sheets_json,
                        pdf_pages,
                        processed_rows,
                        loaded_rows,
                        rejected_rows
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        Path(source["relative_path"]).suffix.lower().lstrip("."),
                        Path(source["relative_path"]).name,
                        source["relative_path"],
                        source["sha256"],
                        source["size_bytes"],
                        json.dumps(source["sheets"], ensure_ascii=False) if source["sheets"] else None,
                        source["pages"],
                        stats["processed_rows"],
                        stats["loaded_rows"],
                        stats["rejected_rows"],
                    ),
                )
                source_id_by_path[source["relative_path"]] = int(cursor.lastrowid)

            title_id_by_norm: dict[str, int] = {}
            for title in title_registry.values():
                cursor = connection.execute(
                    """
                    INSERT INTO titles (
                        titulo_habilitante_original,
                        titulo_habilitante_norm,
                        titular_original,
                        titular_norm,
                        modalidad_original,
                        plan_operativo_original,
                        plan_operativo_norm,
                        resolucion_original,
                        resolucion_norm
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        title["titulo_habilitante_original"],
                        title["titulo_habilitante_norm"],
                        title["titular_original"],
                        title["titular_norm"],
                        title["modalidad_original"],
                        title["plan_operativo_original"],
                        title["plan_operativo_norm"],
                        title["resolucion_original"],
                        title["resolucion_norm"],
                    ),
                )
                title_id_by_norm[title["titulo_habilitante_norm"]] = int(cursor.lastrowid)

            tree_id_by_key: dict[str, int] = {}
            for row in trees:
                cursor = connection.execute(
                    """
                    INSERT INTO trees (
                        title_id,
                        titulo_habilitante_norm,
                        parcela_corta_original,
                        parcela_corta_norm,
                        codigo_arbol_original,
                        codigo_arbol_norm,
                        composite_tree_key,
                        especie_original,
                        especie_norm,
                        volumen_censo_text,
                        dap_text,
                        ac_text,
                        dmc_text,
                        source_relative_path,
                        source_sheet,
                        source_row_number,
                        raw_payload_json,
                        normalized_payload_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        title_id_by_norm[row["titulo_habilitante_norm"]],
                        row["titulo_habilitante_norm"],
                        row["parcela_corta_original"],
                        row["parcela_corta_norm"],
                        row["codigo_arbol_original"],
                        row["codigo_arbol_norm"],
                        row["composite_tree_key"],
                        row["especie_original"],
                        row["especie_norm"],
                        row["volumen_censo_text"],
                        row["dap_text"],
                        row["ac_text"],
                        row["dmc_text"],
                        row["source_relative_path"],
                        row["source_sheet"],
                        row["source_row_number"],
                        row["raw_payload_json"],
                        row["normalized_payload_json"],
                    ),
                )
                tree_id_by_key[row["composite_tree_key"]] = int(cursor.lastrowid)

            supervision_id_by_key: dict[str, int] = {}
            for row in supervisions:
                cursor = connection.execute(
                    """
                    INSERT INTO supervisions (
                        tree_id,
                        title_id,
                        titulo_habilitante_norm,
                        parcela_corta_original,
                        parcela_corta_norm,
                        codigo_arbol_original,
                        codigo_arbol_norm,
                        composite_tree_key,
                        especie_original,
                        especie_norm,
                        especie_censo_referida_original,
                        especie_censo_referida_norm,
                        coincide_especies_norm,
                        source_relative_path,
                        source_sheet,
                        source_row_number,
                        raw_payload_json,
                        normalized_payload_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tree_id_by_key.get(row["composite_tree_key"]),
                        title_id_by_norm[row["titulo_habilitante_norm"]],
                        row["titulo_habilitante_norm"],
                        row["parcela_corta_original"],
                        row["parcela_corta_norm"],
                        row["codigo_arbol_original"],
                        row["codigo_arbol_norm"],
                        row["composite_tree_key"],
                        row["especie_supervision_original"],
                        row["especie_supervision_norm"],
                        row["especie_censo_referida_original"],
                        row["especie_censo_referida_norm"],
                        row["coincide_especies_norm"],
                        row["source_relative_path"],
                        row["source_sheet"],
                        row["source_row_number"],
                        row["raw_payload_json"],
                        row["normalized_payload_json"],
                    ),
                )
                supervision_id_by_key[row["composite_tree_key"]] = int(cursor.lastrowid)

            felling_id_by_key: dict[str, int] = {}
            for row in fellings:
                cursor = connection.execute(
                    """
                    INSERT INTO fellings (
                        tree_id,
                        title_id,
                        titulo_habilitante_norm,
                        parcela_corta_original,
                        parcela_corta_norm,
                        codigo_arbol_original,
                        codigo_arbol_norm,
                        composite_tree_key,
                        especie_original,
                        especie_norm,
                        fecha_operacion,
                        volumen_text,
                        diametro_mayor_text,
                        diametro_menor_text,
                        longitud_text,
                        r_private_value,
                        observaciones_private,
                        source_relative_path,
                        source_sheet,
                        source_row_number,
                        raw_payload_json,
                        normalized_payload_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tree_id_by_key.get(row["composite_tree_key"]),
                        title_id_by_norm[row["titulo_habilitante_norm"]],
                        row["titulo_habilitante_norm"],
                        row["parcela_corta_original"],
                        row["parcela_corta_norm"],
                        row["codigo_arbol_original"],
                        row["codigo_arbol_norm"],
                        row["composite_tree_key"],
                        row["especie_original"],
                        row["especie_norm"],
                        row["fecha_operacion"],
                        row["volumen_text"],
                        row["diametro_mayor_text"],
                        row["diametro_menor_text"],
                        row["longitud_text"],
                        row["r_private_value"],
                        row["observaciones_private"],
                        row["source_relative_path"],
                        row["source_sheet"],
                        row["source_row_number"],
                        row["raw_payload_json"],
                        row["normalized_payload_json"],
                    ),
                )
                felling_id_by_key[row["composite_tree_key"]] = int(cursor.lastrowid)

            log_id_by_key: dict[str, int] = {}
            for row in logs:
                cursor = connection.execute(
                    """
                    INSERT INTO logs (
                        tree_id,
                        felling_id,
                        title_id,
                        titulo_habilitante_norm,
                        parcela_corta_original,
                        parcela_corta_norm,
                        codigo_troza_original,
                        codigo_troza_norm,
                        codigo_arbol_padre_norm,
                        composite_tree_key,
                        composite_log_key,
                        especie_original,
                        especie_norm,
                        fecha_operacion,
                        volumen_text,
                        diametro_mayor_text,
                        diametro_menor_text,
                        longitud_text,
                        r_private_value,
                        observaciones_private,
                        source_relative_path,
                        source_sheet,
                        source_row_number,
                        raw_payload_json,
                        normalized_payload_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tree_id_by_key.get(row["composite_tree_key"]),
                        felling_id_by_key.get(row["composite_tree_key"]),
                        title_id_by_norm[row["titulo_habilitante_norm"]],
                        row["titulo_habilitante_norm"],
                        row["parcela_corta_original"],
                        row["parcela_corta_norm"],
                        row["codigo_troza_original"],
                        row["codigo_troza_norm"],
                        row["codigo_arbol_padre_norm"],
                        row["composite_tree_key"],
                        row["composite_log_key"],
                        row["especie_original"],
                        row["especie_norm"],
                        row["fecha_operacion"],
                        row["volumen_text"],
                        row["diametro_mayor_text"],
                        row["diametro_menor_text"],
                        row["longitud_text"],
                        row["r_private_value"],
                        row["observaciones_private"],
                        row["source_relative_path"],
                        row["source_sheet"],
                        row["source_row_number"],
                        row["raw_payload_json"],
                        row["normalized_payload_json"],
                    ),
                )
                log_id_by_key[row["composite_log_key"]] = int(cursor.lastrowid)

            for row in dispatches:
                connection.execute(
                    """
                    INSERT INTO dispatches (
                        log_id,
                        tree_id,
                        title_id,
                        titulo_habilitante_norm,
                        parcela_corta_original,
                        parcela_corta_norm,
                        codigo_troza_original,
                        codigo_troza_norm,
                        codigo_arbol_padre_norm,
                        composite_tree_key,
                        composite_log_key,
                        codigo_despacho_original,
                        codigo_despacho_norm,
                        numero_gtf_original,
                        numero_gtf_norm,
                        fecha_operacion,
                        observaciones_private,
                        source_relative_path,
                        source_sheet,
                        source_row_number,
                        raw_payload_json,
                        normalized_payload_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        log_id_by_key.get(row["composite_log_key"]),
                        tree_id_by_key.get(row["composite_tree_key"]),
                        title_id_by_norm[row["titulo_habilitante_norm"]],
                        row["titulo_habilitante_norm"],
                        row["parcela_corta_original"],
                        row["parcela_corta_norm"],
                        row["codigo_troza_original"],
                        row["codigo_troza_norm"],
                        row["codigo_arbol_padre_norm"],
                        row["composite_tree_key"],
                        row["composite_log_key"],
                        row["codigo_despacho_original"],
                        row["codigo_despacho_norm"],
                        row["numero_gtf_original"],
                        row["numero_gtf_norm"],
                        row["fecha_operacion"],
                        row["observaciones_private"],
                        row["source_relative_path"],
                        row["source_sheet"],
                        row["source_row_number"],
                        row["raw_payload_json"],
                        row["normalized_payload_json"],
                    ),
                )

            for row in balances:
                connection.execute(
                    """
                    INSERT INTO species_balances (
                        title_id,
                        titulo_habilitante_norm,
                        parcela_corta_original,
                        parcela_corta_norm,
                        product_type,
                        especie_original,
                        especie_norm,
                        composite_balance_key,
                        volumen_autorizado_text,
                        volumen_extraido_text,
                        saldo_reportado_text,
                        source_fragment,
                        source_relative_path,
                        source_sheet,
                        source_row_number,
                        raw_payload_json,
                        normalized_payload_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        title_id_by_norm[row["titulo_habilitante_norm"]],
                        row["titulo_habilitante_norm"],
                        row["parcela_corta_original"],
                        row["parcela_corta_norm"],
                        row["product_type"],
                        row["especie_original"],
                        row["especie_norm"],
                        row["composite_balance_key"],
                        row["volumen_autorizado_text"],
                        row["volumen_extraido_text"],
                        row["saldo_reportado_text"],
                        row["source_fragment"],
                        row["source_relative_path"],
                        row["source_sheet"],
                        row["source_row_number"],
                        row["raw_payload_json"],
                        row["normalized_payload_json"],
                    ),
                )

            trace_id_by_key: dict[str, int] = {}
            checks_by_trace_key = dict(trace_checks_payload)
            for row in traces:
                cursor = connection.execute(
                    """
                    INSERT INTO trace_catalog (
                        tree_id,
                        title_id,
                        titulo_habilitante_norm,
                        parcela_corta_norm,
                        codigo_arbol_norm,
                        composite_tree_key,
                        especie_censo_norm,
                        especie_supervision_norm,
                        especie_operacion_norm,
                        volumen_censo_text,
                        volumen_tala_text,
                        volumen_trozado_text,
                        verification_status,
                        troza_count,
                        dispatch_count,
                        gtf_count,
                        evidence_hash_sha256,
                        public_payload_json,
                        lineage_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        tree_id_by_key.get(row["composite_tree_key"]),
                        title_id_by_norm[row["titulo_habilitante_norm"]],
                        row["titulo_habilitante_norm"],
                        row["parcela_corta_norm"],
                        row["codigo_arbol_norm"],
                        row["composite_tree_key"],
                        row["especie_censo_norm"],
                        row["especie_supervision_norm"],
                        row["especie_operacion_norm"],
                        row["volumen_censo_text"],
                        row["volumen_tala_text"],
                        row["volumen_trozado_text"],
                        row["verification_status"],
                        len(row["trozas"]),
                        len(row["dispatches"]),
                        len(row["gtf"]),
                        row["evidence_hash_sha256"],
                        row["public_payload_json"],
                        json.dumps(row["lineage"], ensure_ascii=False, sort_keys=True),
                    ),
                )
                trace_id = int(cursor.lastrowid)
                trace_id_by_key[row["composite_tree_key"]] = trace_id

                for name in REQUIRED_CHECKS:
                    check = checks_by_trace_key[row["composite_tree_key"]][name]
                    connection.execute(
                        """
                        INSERT INTO trace_checks (
                            trace_id,
                            check_name,
                            check_status,
                            value_json
                        )
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            trace_id,
                            name,
                            check["status"],
                            json.dumps(check["value"], ensure_ascii=False, sort_keys=True),
                        ),
                    )

                connection.execute(
                    """
                    INSERT INTO search_identifiers (
                        trace_id,
                        identifier_type,
                        identifier_value_norm,
                        display_value,
                        composite_tree_key,
                        titulo_habilitante_norm,
                        parcela_corta_norm,
                        verification_status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trace_id,
                        "ARBOL",
                        row["codigo_arbol_norm"],
                        row["codigo_arbol_norm"],
                        row["composite_tree_key"],
                        row["titulo_habilitante_norm"],
                        row["parcela_corta_norm"],
                        row["verification_status"],
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO search_identifiers (
                        trace_id,
                        identifier_type,
                        identifier_value_norm,
                        display_value,
                        composite_tree_key,
                        titulo_habilitante_norm,
                        parcela_corta_norm,
                        verification_status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        trace_id,
                        "TITULO",
                        row["titulo_habilitante_norm"],
                        row["titulo_habilitante_norm"],
                        row["composite_tree_key"],
                        row["titulo_habilitante_norm"],
                        row["parcela_corta_norm"],
                        row["verification_status"],
                    ),
                )
                for troza in row["trozas"]:
                    connection.execute(
                        """
                        INSERT INTO search_identifiers (
                            trace_id,
                            identifier_type,
                            identifier_value_norm,
                            display_value,
                            composite_tree_key,
                            titulo_habilitante_norm,
                            parcela_corta_norm,
                            verification_status
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            trace_id,
                            "TROZA",
                            troza,
                            troza,
                            row["composite_tree_key"],
                            row["titulo_habilitante_norm"],
                            row["parcela_corta_norm"],
                            row["verification_status"],
                        ),
                    )
                for gtf in row["gtf"]:
                    connection.execute(
                        """
                        INSERT INTO search_identifiers (
                            trace_id,
                            identifier_type,
                            identifier_value_norm,
                            display_value,
                            composite_tree_key,
                            titulo_habilitante_norm,
                            parcela_corta_norm,
                            verification_status
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            trace_id,
                            "GTF",
                            gtf,
                            gtf,
                            row["composite_tree_key"],
                            row["titulo_habilitante_norm"],
                            row["parcela_corta_norm"],
                            row["verification_status"],
                        ),
                    )

        foreign_key_errors = [tuple(row) for row in connection.execute("PRAGMA foreign_key_check").fetchall()]
        if foreign_key_errors:
            raise RuntimeError(f"Errores de claves foraneas: {foreign_key_errors}")

        indexes = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
        }
        missing_indexes = EXPECTED_INDEXES - indexes
        if missing_indexes:
            raise RuntimeError(f"Indices faltantes: {sorted(missing_indexes)}")

        row_501 = connection.execute(
            """
            SELECT especie_censo_norm, volumen_censo_text, volumen_tala_text,
                   volumen_trozado_text, verification_status, evidence_hash_sha256
            FROM trace_catalog
            WHERE parcela_corta_norm = 'PC 01' AND codigo_arbol_norm = '501'
            """
        ).fetchone()
        if row_501 is None or row_501["verification_status"] != "CONSISTENTE":
            raise RuntimeError("Validacion 501 fallo")

        row_1170 = connection.execute(
            """
            SELECT especie_censo_norm, especie_supervision_norm, volumen_censo_text,
                   volumen_tala_text, volumen_trozado_text, verification_status
            FROM trace_catalog
            WHERE parcela_corta_norm = 'PC 01' AND codigo_arbol_norm = '1170'
            """
        ).fetchone()
        if row_1170 is None or row_1170["verification_status"] != "POR_REVISAR":
            raise RuntimeError("Validacion 1170 fallo")
    finally:
        connection.close()

    os.replace(temp_db, final_db)

    final_connection = sqlite3.connect(final_db)
    final_connection.row_factory = sqlite3.Row
    try:
        table_counts = {
            row["name"]: row["count"]
            for row in final_connection.execute(
                """
                SELECT 'titles' AS name, COUNT(*) AS count FROM titles
                UNION ALL SELECT 'trees', COUNT(*) FROM trees
                UNION ALL SELECT 'supervisions', COUNT(*) FROM supervisions
                UNION ALL SELECT 'fellings', COUNT(*) FROM fellings
                UNION ALL SELECT 'logs', COUNT(*) FROM logs
                UNION ALL SELECT 'dispatches', COUNT(*) FROM dispatches
                UNION ALL SELECT 'species_balances', COUNT(*) FROM species_balances
                UNION ALL SELECT 'trace_catalog', COUNT(*) FROM trace_catalog
                UNION ALL SELECT 'trace_checks', COUNT(*) FROM trace_checks
                UNION ALL SELECT 'search_identifiers', COUNT(*) FROM search_identifiers
                """
            ).fetchall()
        }
    finally:
        final_connection.close()

    status_distribution = Counter(row["verification_status"] for row in traces)
    identifier_distribution = Counter()
    for row in traces:
        identifier_distribution["ARBOL"] += 1
        identifier_distribution["TITULO"] += 1
        identifier_distribution["TROZA"] += len(row["trozas"])
        identifier_distribution["GTF"] += len(row["gtf"])

    balances_loaded = len(balances)
    balances_rejected = sum(len(result["rejected"]) for result in balance_results) + len(rejected_balance_dupes)
    balances_without_association = sum(
        1
        for row in balances
        if row.get("product_type") == "MADERA EN ROLLO"
        and row["composite_balance_key"] not in {
            composite_balance_key(trace["titulo_habilitante_norm"], trace["parcela_corta_norm"], trace.get("especie_censo_norm"))
            for trace in traces
            if trace.get("especie_censo_norm")
        }
    )

    report = {
        "fuentes_procesadas": [item["relative_path"] for item in inventory["sources"]],
        "filas_por_fuente": source_stats,
        "duplicados": {
            "census": len(rejected_tree_dupes),
            "supervision": len(rejected_supervision_dupes),
            "fellings": len(rejected_felling_dupes),
            "logs": len(rejected_log_dupes),
            "dispatches": len(rejected_dispatch_dupes),
            "balances": len(rejected_balance_dupes),
        },
        "trees_without_felling": sum(1 for trace in traces if trace.get("tree") and not trace.get("felling")),
        "fellings_without_tree": sum(1 for row in fellings if row["composite_tree_key"] not in trees_by_key),
        "felling_without_logs": sum(1 for trace in traces if trace.get("felling") and not trace.get("logs")),
        "logs_without_tree": sum(1 for row in logs if row["composite_tree_key"] not in trees_by_key),
        "logs_without_dispatch": sum(1 for row in logs if row["composite_tree_key"] not in dispatches_by_tree),
        "dispatches_without_logs": sum(1 for row in dispatches if row["composite_log_key"] not in logs_by_log_key),
        "gtf_with_multiple_logs": sum(1 for scope, items in Counter(item["numero_gtf_norm"] for item in dispatches if item.get("numero_gtf_norm")).items() if items > 1),
        "gtf_crossing_titles_or_parcels": {
            gtf: sorted(f"{title}::{parcel}" for title, parcel in scopes)
            for gtf, scopes in gtf_scope_map.items()
            if len(scopes) > 1
        },
        "trees_without_supervision": sum(1 for trace in traces if trace.get("tree") and trace.get("especie_supervision_norm") is None),
        "species_differences": sum(1 for trace in traces if trace.get("especie_censo_norm") and trace.get("especie_supervision_norm") and trace["especie_censo_norm"] != trace["especie_supervision_norm"]),
        "volume_increases": sum(1 for trace in traces if trace.get("volumen_tala_text") and trace.get("volumen_trozado_text") and Decimal(trace["volumen_trozado_text"]) > Decimal(trace["volumen_tala_text"])),
        "balances_loaded": balances_loaded,
        "balances_rejected": balances_rejected,
        "balances_without_association": balances_without_association,
        "invalid_volume_values": 0,
        "records_with_r": {
            "fellings": sum(1 for row in fellings_raw if clean_text(row.get("r_private_value")) is not None),
            "logs": sum(1 for row in logs_raw if clean_text(row.get("r_private_value")) is not None),
        },
        "source_r_interpreted": False,
        "state_distribution": dict(status_distribution),
        "identifiers_by_type": dict(identifier_distribution),
        "table_counts": table_counts,
    }
    write_json(staging_dir / "catalog_quality_report.json", report)

    manifest = {
        "build_target": "db/huella_catalog.db",
        "database_sha256": file_sha256(final_db),
        "database_size_bytes": final_db.stat().st_size,
        "source_inventory_path": "staging/catalog/source_inventory.json",
        "quality_report_path": "staging/catalog/catalog_quality_report.json",
        "balance_extraction_text_path": "staging/catalog/balance_extraction_text.json",
        "source_sha256": {
            item["relative_path"]: item["sha256"] for item in inventory["sources"]
        },
        "table_counts": table_counts,
        "foreign_key_check": [],
        "status_distribution": dict(status_distribution),
    }
    write_json(staging_dir / "catalog_build_manifest.json", manifest)

    return {
        "inventory": inventory,
        "report": report,
        "manifest": manifest,
        "db_path": final_db,
    }


def main() -> None:
    repo_root = resolve_repo_root()
    temp_db = repo_root / "db" / "huella_catalog.db.tmp"
    try:
        result = build()
    except Exception:
        if temp_db.exists():
            temp_db.unlink()
        raise

    print(f"CATALOG_DB={result['db_path'].relative_to(repo_root).as_posix()}")
    print(json.dumps(result["manifest"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
