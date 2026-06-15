"""
scripts/smoke_api.py

Prueba de humo de la Micro-fase 5B.

Ejecutable desde cualquier directorio:
    python scripts/smoke_api.py

Usa TestClient de FastAPI (sin levantar un servidor real).
Termina con: MICRO-FASE 5B COMPLETADA
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ── Garantizar que el paquete app sea importable ──────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)

_CLEAN_ID = "clean-pc01-501"
_INCONSISTENT_ID = "inconsistent-pc01-1170"
_CLEAN_HASH = "4c96a56231688b3723a64a724808cfdd6345f8c5469c3213c8b21f249a9fada6"
_INCONSISTENT_HASH = "a7252bfc45f98497d058bea506d225913db9b4929f5bf706e48df424a580bf32"

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}

_RESTRICTED_STRINGS = [
    "source_path",
    "source_json_path",
    "observations",
    "coordenada",
    "ruc",
    "dni",
    "raw/",
    "staging/",
    "db/",
]

_passed = 0
_failed = 0


def _ok(msg: str) -> None:
    global _passed
    _passed += 1
    print(f"  [OK]   {msg}")


def _fail(msg: str) -> None:
    global _failed
    _failed += 1
    print(f"  [FAIL] {msg}", file=sys.stderr)


def _assert(condition: bool, msg: str) -> None:
    if condition:
        _ok(msg)
    else:
        _fail(msg)


def _check_security_headers(resp: object, endpoint: str) -> None:
    for header, value in _SECURITY_HEADERS.items():
        _assert(
            resp.headers.get(header) == value,
            f"{endpoint} — encabezado {header}: {value}",
        )


def _check_no_restricted_fields(body: str, label: str) -> None:
    lower = body.lower()
    for field in _RESTRICTED_STRINGS:
        _assert(
            field.lower() not in lower,
            f"'{field}' ausente en {label}",
        )


def main() -> None:
    print("=" * 70)
    print("SMOKE TEST — Micro-fase 5B")
    print("=" * 70)

    # ── 1. GET / ──────────────────────────────────────────────────────────────
    print("\n[1] GET /")
    r = client.get("/")
    _assert(r.status_code == 200, "GET / -> 200")
    _check_security_headers(r, "GET /")

    # ── 2. GET /health ────────────────────────────────────────────────────────
    print("\n[2] GET /health")
    r = client.get("/health")
    _assert(r.status_code == 200, "GET /health -> 200")
    data = r.json()
    _assert(data.get("status") == "ok", "health.status == 'ok'")
    _assert(
        data.get("database_mode") == "read-only",
        "health.database_mode == 'read-only'",
    )
    _assert(data.get("case_count") == 2, "health.case_count == 2")
    _check_security_headers(r, "GET /health")

    # ── 3. GET /api/v1/cases ──────────────────────────────────────────────────
    print("\n[3] GET /api/v1/cases")
    r = client.get("/api/v1/cases")
    _assert(r.status_code == 200, "GET /api/v1/cases -> 200")
    cases = r.json()
    _assert(len(cases) == 2, "Lista contiene exactamente 2 casos")
    _check_security_headers(r, "GET /api/v1/cases")
    _check_no_restricted_fields(r.text, "GET /api/v1/cases")

    # ── 4. GET /api/v1/verifications/clean-pc01-501 ───────────────────────────
    print(f"\n[4] GET /api/v1/verifications/{_CLEAN_ID}")
    r = client.get(f"/api/v1/verifications/{_CLEAN_ID}")
    _assert(r.status_code == 200, f"GET verifications/{_CLEAN_ID} -> 200")
    clean = r.json()
    _assert(
        clean.get("attestation_eligible") is True,
        "Caso limpio es elegible",
    )
    _assert(len(clean.get("trozas", [])) == 1, "Caso limpio tiene 1 troza")
    _assert(len(clean.get("gtf", [])) == 1, "Caso limpio tiene 1 GTF")
    _check_security_headers(r, f"GET verifications/{_CLEAN_ID}")
    _check_no_restricted_fields(r.text, f"GET verifications/{_CLEAN_ID}")

    # ── 5. GET /api/v1/verifications/inconsistent-pc01-1170 ──────────────────
    print(f"\n[5] GET /api/v1/verifications/{_INCONSISTENT_ID}")
    r = client.get(f"/api/v1/verifications/{_INCONSISTENT_ID}")
    _assert(r.status_code == 200, f"GET verifications/{_INCONSISTENT_ID} -> 200")
    inconsistent = r.json()
    _assert(
        inconsistent.get("attestation_eligible") is False,
        "Caso inconsistente no es elegible",
    )
    _assert(
        len(inconsistent.get("trozas", [])) == 3,
        "Caso inconsistente tiene 3 trozas",
    )
    _assert(
        len(inconsistent.get("gtf", [])) == 3,
        "Caso inconsistente tiene 3 GTF",
    )
    _check_security_headers(r, f"GET verifications/{_INCONSISTENT_ID}")
    _check_no_restricted_fields(r.text, f"GET verifications/{_INCONSISTENT_ID}")

    # ── 6. GET case_id inexistente -> 404 ─────────────────────────────────────
    print("\n[6] GET /api/v1/verifications/no-existe -> 404")
    r = client.get("/api/v1/verifications/no-existe")
    _assert(r.status_code == 404, "case_id inexistente -> 404")
    detail = r.json().get("detail", "")
    _assert(detail == "Comprobante no encontrado", "Mensaje 404 correcto")

    # ── 7. POST /api/v1/cases -> 405 ──────────────────────────────────────────
    print("\n[7] POST /api/v1/cases -> 405")
    r = client.post("/api/v1/cases", json={})
    _assert(r.status_code == 405, "POST /api/v1/cases -> 405")

    # ── 8. GET /openapi.json -> 200 ────────────────────────────────────────────
    print("\n[8] GET /openapi.json")
    r = client.get("/openapi.json")
    _assert(r.status_code == 200, "GET /openapi.json -> 200")

    # ── 9. GET /docs -> 200 ────────────────────────────────────────────────────
    print("\n[9] GET /docs")
    r = client.get("/docs")
    _assert(r.status_code == 200, "GET /docs -> 200")

    # ── 10. Hashes intactos ───────────────────────────────────────────────────
    print("\n[10] Integridad de hashes")
    _assert(
        clean.get("evidence_hash_sha256") == _CLEAN_HASH,
        "Hash del caso limpio intacto",
    )
    _assert(
        inconsistent.get("evidence_hash_sha256") == _INCONSISTENT_HASH,
        "Hash del caso inconsistente intacto",
    )

    # ── Resumen ───────────────────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print(f"Resultados: {_passed} OK — {_failed} FAIL")
    print("=" * 70)

    if _failed > 0:
        sys.exit(1)

    print("\nMICRO-FASE 5B COMPLETADA")


if __name__ == "__main__":
    main()

