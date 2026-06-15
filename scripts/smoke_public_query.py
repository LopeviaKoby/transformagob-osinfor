"""
scripts/smoke_public_query.py

Prueba de humo de la Micro-fase 5A.

Ejecutable desde cualquier directorio:
    python scripts/smoke_public_query.py

Verifica:
- Que existan exactamente 2 casos.
- Que clean-pc01-501 sea elegible.
- Que inconsistent-pc01-1170 NO sea elegible.
- Que el caso limpio tenga 1 troza y 1 GTF.
- Que el inconsistente tenga 3 trozas y 3 GTF.
- Que ningún JSON público contenga campos privados.
- Que una operación CREATE TABLE sobre la conexión de solo lectura
  falle con sqlite3.OperationalError.
- Imprime ambos JSON públicos.
- Termina con: MICRO-FASE 5A COMPLETADA
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

# ── Garantizar que el paquete app sea importable ──────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.database import open_readonly_connection  # noqa: E402
from app.service import get_public_verification, list_public_cases  # noqa: E402

# Campos que no deben aparecer en la proyección pública
_PRIVATE_FIELDS = {
    "source_path",
    "source_json_path",
    "observations",
    "coordenada",
    "ruc",
    "dni",
}

_CLEAN_ID = "clean-pc01-501"
_INCONSISTENT_ID = "inconsistent-pc01-1170"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        print(f"  [FAIL] {message}", file=sys.stderr)
        sys.exit(1)
    print(f"  [OK]   {message}")


def main() -> None:
    print("=" * 70)
    print("SMOKE TEST — Micro-fase 5A")
    print("=" * 70)

    # ── 1. Lista de casos ─────────────────────────────────────────────────────
    print("\n[1] list_public_cases()")
    cases = list_public_cases()
    _assert(len(cases) == 2, "Existen exactamente 2 casos")

    case_ids = {c["case_id"] for c in cases}
    _assert(_CLEAN_ID in case_ids, f"Existe el caso {_CLEAN_ID}")
    _assert(_INCONSISTENT_ID in case_ids, f"Existe el caso {_INCONSISTENT_ID}")

    # ── 2. Elegibilidad ───────────────────────────────────────────────────────
    print("\n[2] Elegibilidad")
    clean_summary = next(c for c in cases if c["case_id"] == _CLEAN_ID)
    inconsistent_summary = next(c for c in cases if c["case_id"] == _INCONSISTENT_ID)

    _assert(
        clean_summary["attestation_eligible"] is True,
        f"{_CLEAN_ID} es elegible (True)",
    )
    _assert(
        inconsistent_summary["attestation_eligible"] is False,
        f"{_INCONSISTENT_ID} no es elegible (False)",
    )

    # ── 3. Detalle del caso limpio ────────────────────────────────────────────
    print(f"\n[3] get_public_verification('{_CLEAN_ID}')")
    clean = get_public_verification(_CLEAN_ID)
    _assert(clean is not None, "Detalle del caso limpio no es None")

    _assert(len(clean["trozas"]) == 1, "Caso limpio tiene 1 troza")
    _assert(len(clean["gtf"]) == 1, "Caso limpio tiene 1 GTF")

    # ── 4. Detalle del caso inconsistente ─────────────────────────────────────
    print(f"\n[4] get_public_verification('{_INCONSISTENT_ID}')")
    inconsistent = get_public_verification(_INCONSISTENT_ID)
    _assert(inconsistent is not None, "Detalle del caso inconsistente no es None")

    _assert(len(inconsistent["trozas"]) == 3, "Caso inconsistente tiene 3 trozas")
    _assert(len(inconsistent["gtf"]) == 3, "Caso inconsistente tiene 3 GTF")

    # ── 5. Campos privados ausentes ───────────────────────────────────────────
    print("\n[5] Ausencia de campos privados en JSON público")
    for label, obj in [(_CLEAN_ID, clean), (_INCONSISTENT_ID, inconsistent)]:
        serialized = json.dumps(obj, ensure_ascii=False)
        for field in _PRIVATE_FIELDS:
            _assert(
                field not in serialized,
                f"'{field}' ausente en {label}",
            )

    # ── 6. Conexión rechaza escrituras ────────────────────────────────────────
    print("\n[6] Conexión de solo lectura rechaza CREATE TABLE")
    conn = open_readonly_connection()
    try:
        try:
            conn.execute("CREATE TABLE _forbidden (x INTEGER)")
            _assert(False, "CREATE TABLE debió lanzar OperationalError")
        except sqlite3.OperationalError:
            _assert(True, "CREATE TABLE lanzó sqlite3.OperationalError correctamente")
    finally:
        conn.close()

    # ── 7. Impresión de JSON públicos ─────────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"JSON público — {_CLEAN_ID}")
    print("=" * 70)
    print(json.dumps(clean, ensure_ascii=False, indent=2))

    print("\n" + "=" * 70)
    print(f"JSON público — {_INCONSISTENT_ID}")
    print("=" * 70)
    print(json.dumps(inconsistent, ensure_ascii=False, indent=2))

    print("\nMICRO-FASE 5A COMPLETADA")


if __name__ == "__main__":
    main()
