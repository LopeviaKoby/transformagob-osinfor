"""
Prueba de humo para búsqueda y detalle del catálogo.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        print(f"[FAIL] {message}", file=sys.stderr)
        sys.exit(1)
    print(f"[OK]   {message}")


def main() -> None:
    print("=" * 70)
    print("SMOKE TEST — Catálogo API")
    print("=" * 70)

    search_gtf = client.get("/api/v1/search", params={"query": "017-0001426"})
    _assert(search_gtf.status_code == 200, "GET /api/v1/search GTF -> 200")
    _assert(search_gtf.json()["count"] == 1, "GTF 017-0001426 devuelve 1 resultado")

    search_log = client.get("/api/v1/search", params={"query": "501/A"})
    _assert(search_log.status_code == 200, "GET /api/v1/search troza -> 200")
    _assert(search_log.json()["results"][0]["codigo_arbol"] == "501", "501/A abre el árbol 501")

    detail = client.get("/api/v1/verifications/1503")
    _assert(detail.status_code == 200, "GET /api/v1/verifications/1503 -> 200")
    _assert(detail.json()["balance"]["available"] is True, "El detalle del catálogo expone balance")

    health = client.get("/health")
    _assert(health.status_code == 200, "GET /health -> 200")
    _assert(health.json()["catalog_trace_count"] == 10468, "/health informa 10468 expedientes")

    print("\nSMOKE CATALOG API OK")


if __name__ == "__main__":
    main()
