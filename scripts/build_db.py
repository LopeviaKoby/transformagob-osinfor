"""
Construye db/huella_origen.db desde los expedientes JSON definitivos.

Entradas:
- staging/cases/case_clean.json
- staging/cases/case_inconsistent.json

Salida:
- db/huella_origen.db

La construcción es reproducible:
1. valida los hashes;
2. elimina una base anterior;
3. crea el esquema;
4. inserta ambos casos dentro de una transacción;
5. verifica conteos y relaciones.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CASES_DIR = PROJECT_ROOT / "staging" / "cases"
SCHEMA_PATH = PROJECT_ROOT / "db" / "schema.sql"
DATABASE_PATH = PROJECT_ROOT / "db" / "huella_origen.db"

CASE_FILES = (
    CASES_DIR / "case_clean.json",
    CASES_DIR / "case_inconsistent.json",
)

EXPECTED_CASE_IDS = {
    "clean-pc01-501",
    "inconsistent-pc01-1170",
}

EVIDENCE_KEYS = (
    "join_key",
    "verification",
    "summary",
    "lineage",
    "records",
)


def load_json(path: Path) -> dict[str, Any]:
    """Carga y valida estructuralmente un expediente JSON."""
    if not path.exists():
        raise FileNotFoundError(f"No existe el expediente: {path}")

    content = path.read_text(encoding="utf-8")

    if content.lstrip().lower().startswith(
        ("<!doctype", "<html")
    ):
        raise RuntimeError(
            f"{path.name} contiene HTML en lugar de JSON."
        )

    payload = json.loads(content)

    if not isinstance(payload, dict):
        raise TypeError(
            f"{path.name} debe contener un objeto JSON."
        )

    return payload


def calculate_evidence_hash(
    payload: dict[str, Any],
) -> str:
    """Reproduce el hash generado en Colab."""
    evidence = {
        key: payload[key]
        for key in EVIDENCE_KEYS
    }

    canonical = json.dumps(
        evidence,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")

    return hashlib.sha256(canonical).hexdigest()


def validate_payload(
    payload: dict[str, Any],
    source_path: Path,
) -> None:
    """Valida identidad, versión e integridad."""
    required_keys = {
        "schema_version",
        "case_id",
        "case_type",
        "join_key",
        "verification",
        "summary",
        "lineage",
        "records",
        "evidence_hash_sha256",
    }

    missing = required_keys - payload.keys()

    if missing:
        raise ValueError(
            f"{source_path.name}: faltan campos {sorted(missing)}"
        )

    if payload["schema_version"] != "2.0":
        raise ValueError(
            f"{source_path.name}: versión distinta de 2.0."
        )

    if payload["case_id"] not in EXPECTED_CASE_IDS:
        raise ValueError(
            f"{source_path.name}: case_id inesperado: "
            f"{payload['case_id']}"
        )

    stored_hash = payload["evidence_hash_sha256"]
    calculated_hash = calculate_evidence_hash(payload)

    if stored_hash != calculated_hash:
        raise ValueError(
            f"{source_path.name}: hash de evidencia inválido.\n"
            f"Almacenado: {stored_hash}\n"
            f"Calculado:  {calculated_hash}"
        )


def check_status(
    check_name: str,
    raw_value: Any,
    verification: dict[str, Any],
) -> str:
    """
    Convierte las validaciones a estados explícitos.

    El campo R no se clasifica como error:
    queda como NOT_EVALUATED porque su significado
    no está confirmado.
    """
    excluded_rule = verification.get("excluded_rule") or {}

    if (
        check_name == "campo_r_validado"
        or excluded_rule.get("field") == "R"
        and check_name == "campo_r_validado"
    ):
        return "NOT_EVALUATED"

    return "PASS" if raw_value is True else "FAIL"


def insert_case(
    connection: sqlite3.Connection,
    payload: dict[str, Any],
    source_path: Path,
    loaded_at: str,
) -> None:
    """Inserta un expediente completo y su linaje."""
    case_id = payload["case_id"]
    join_key = payload["join_key"]
    verification = payload["verification"]
    summary = payload["summary"]

    connection.execute(
        """
        INSERT INTO cases (
            case_id,
            schema_version,
            case_type,
            titulo_habilitante,
            parcela_corta,
            codigo_arbol,
            verification_status,
            attestation_eligible,
            titular,
            plan_operativo,
            resolucion,
            especie_censo,
            especie_supervision,
            volumen_censo_m3,
            volumen_tala_m3,
            volumen_trozado_m3,
            diferencia_tala_trozado_m3,
            observations,
            evidence_hash_sha256,
            source_json_path,
            loaded_at_utc
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        (
            case_id,
            payload["schema_version"],
            payload["case_type"],
            join_key["titulo_habilitante"],
            join_key["parcela_corta"],
            join_key["codigo_arbol"],
            verification["status"],
            int(
                verification[
                    "prototype_attestation_eligible"
                ]
            ),
            summary.get("titular"),
            summary.get("plan_operativo"),
            summary.get("resolucion"),
            summary.get("especie_censo"),
            summary.get("especie_supervision"),
            summary.get("volumen_censo_m3"),
            summary.get("volumen_tala_m3"),
            summary.get("volumen_trozado_m3"),
            summary.get(
                "diferencia_tala_trozado_m3"
            ),
            verification.get("observations"),
            payload["evidence_hash_sha256"],
            source_path.relative_to(
                PROJECT_ROOT
            ).as_posix(),
            loaded_at,
        ),
    )

    for name, value in verification[
        "checks"
    ].items():
        connection.execute(
            """
            INSERT INTO case_checks (
                case_id,
                check_name,
                check_status,
                raw_value_json
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                case_id,
                name,
                check_status(
                    name,
                    value,
                    verification,
                ),
                json.dumps(
                    value,
                    ensure_ascii=False,
                ),
            ),
        )

    for stage, source in payload[
        "lineage"
    ].items():
        connection.execute(
            """
            INSERT INTO case_sources (
                case_id,
                stage,
                source_path
            )
            VALUES (?, ?, ?)
            """,
            (
                case_id,
                stage,
                source,
            ),
        )

    for stage, stage_records in payload[
        "records"
    ].items():
        for index, record in enumerate(stage_records):
            connection.execute(
                """
                INSERT INTO case_records (
                    case_id,
                    stage,
                    record_index,
                    record_json
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    case_id,
                    stage,
                    index,
                    json.dumps(
                        record,
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                ),
            )

    for codigo_troza in summary.get(
        "trozas",
        [],
    ):
        connection.execute(
            """
            INSERT INTO case_logs (
                case_id,
                codigo_troza
            )
            VALUES (?, ?)
            """,
            (
                case_id,
                str(codigo_troza),
            ),
        )

    for numero_gtf in summary.get(
        "gtf",
        [],
    ):
        connection.execute(
            """
            INSERT INTO case_gtf (
                case_id,
                numero_gtf
            )
            VALUES (?, ?)
            """,
            (
                case_id,
                str(numero_gtf),
            ),
        )


def verify_database(
    connection: sqlite3.Connection,
) -> None:
    """Comprueba los datos esenciales del MVP."""
    case_count = connection.execute(
        "SELECT COUNT(*) FROM cases"
    ).fetchone()[0]

    if case_count != 2:
        raise RuntimeError(
            f"Se esperaban 2 casos; existen {case_count}."
        )

    loaded_ids = {
        row[0]
        for row in connection.execute(
            "SELECT case_id FROM cases"
        ).fetchall()
    }

    if loaded_ids != EXPECTED_CASE_IDS:
        raise RuntimeError(
            f"Casos inesperados: {loaded_ids}"
        )

    clean_logs = connection.execute(
        """
        SELECT COUNT(*)
        FROM case_logs
        WHERE case_id = 'clean-pc01-501'
        """
    ).fetchone()[0]

    inconsistent_logs = connection.execute(
        """
        SELECT COUNT(*)
        FROM case_logs
        WHERE case_id = 'inconsistent-pc01-1170'
        """
    ).fetchone()[0]

    clean_gtf = connection.execute(
        """
        SELECT COUNT(*)
        FROM case_gtf
        WHERE case_id = 'clean-pc01-501'
        """
    ).fetchone()[0]

    inconsistent_gtf = connection.execute(
        """
        SELECT COUNT(*)
        FROM case_gtf
        WHERE case_id = 'inconsistent-pc01-1170'
        """
    ).fetchone()[0]

    if (clean_logs, clean_gtf) != (1, 1):
        raise RuntimeError(
            "El caso limpio debe tener 1 troza y 1 GTF."
        )

    if (
        inconsistent_logs,
        inconsistent_gtf,
    ) != (3, 3):
        raise RuntimeError(
            "El caso inconsistente debe tener "
            "3 trozas y 3 GTF."
        )

    foreign_key_errors = connection.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    if foreign_key_errors:
        raise RuntimeError(
            f"Errores de integridad referencial: "
            f"{foreign_key_errors}"
        )


def print_summary(
    connection: sqlite3.Connection,
) -> None:
    """Presenta el resultado de forma verificable."""
    rows = connection.execute(
        """
        SELECT
            case_id,
            codigo_arbol,
            verification_status,
            attestation_eligible,
            volumen_censo_m3,
            volumen_tala_m3,
            volumen_trozado_m3
        FROM cases
        ORDER BY case_type
        """
    ).fetchall()

    print("=" * 76)
    print("BASE SQLITE CONSTRUIDA")
    print("=" * 76)

    for row in rows:
        (
            case_id,
            tree_code,
            status,
            eligible,
            census_volume,
            felling_volume,
            log_volume,
        ) = row

        print(f"\nCaso:       {case_id}")
        print(f"Árbol:      {tree_code}")
        print(f"Estado:     {status}")
        print(f"Elegible:   {bool(eligible)}")
        print(f"Censo m³:   {census_volume}")
        print(f"Tala m³:    {felling_volume}")
        print(f"Trozado m³: {log_volume}")

    table_counts = connection.execute(
        """
        SELECT 'cases', COUNT(*) FROM cases
        UNION ALL
        SELECT 'case_checks', COUNT(*) FROM case_checks
        UNION ALL
        SELECT 'case_sources', COUNT(*) FROM case_sources
        UNION ALL
        SELECT 'case_records', COUNT(*) FROM case_records
        UNION ALL
        SELECT 'case_logs', COUNT(*) FROM case_logs
        UNION ALL
        SELECT 'case_gtf', COUNT(*) FROM case_gtf
        """
    ).fetchall()

    print("\nRegistros por tabla:")

    for table_name, count in table_counts:
        print(f"  {table_name:<20} {count}")

    print(f"\nBase: {DATABASE_PATH}")
    print("\nMICRO-FASE 4B COMPLETADA")


def main() -> None:
    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(
            f"No existe el esquema: {SCHEMA_PATH}"
        )

    payloads = []

    for path in CASE_FILES:
        payload = load_json(path)
        validate_payload(payload, path)
        payloads.append((path, payload))

    loaded_ids = {
        payload["case_id"]
        for _, payload in payloads
    }

    if loaded_ids != EXPECTED_CASE_IDS:
        raise RuntimeError(
            f"Expedientes incorrectos: {loaded_ids}"
        )

    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()

    schema_sql = SCHEMA_PATH.read_text(
        encoding="utf-8"
    )

    loaded_at = datetime.now(
        timezone.utc
    ).isoformat()

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        with connection:
            connection.executescript(schema_sql)

            connection.executemany(
                """
                INSERT INTO build_metadata (
                    metadata_key,
                    metadata_value
                )
                VALUES (?, ?)
                """,
                (
                    ("schema_version", "1.0"),
                    ("loaded_at_utc", loaded_at),
                    (
                        "source_case_count",
                        str(len(payloads)),
                    ),
                ),
            )

            for path, payload in payloads:
                insert_case(
                    connection,
                    payload,
                    path,
                    loaded_at,
                )

        verify_database(connection)
        print_summary(connection)

    finally:
        connection.close()


if __name__ == "__main__":
    main()