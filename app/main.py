"""
app/main.py

API REST pública de solo lectura — Micro-fase 5B.

Endpoints:
  GET /                                   → estado del servicio
  GET /health                             → salud + acceso real a SQLite
  GET /api/v1/cases                       → lista de expedientes públicos
  GET /api/v1/verifications/{case_id}     → comprobante público completo

No se implementan POST, PUT, PATCH ni DELETE.
No se incluyen coordenadas, RUC, DNI, rutas internas ni registros crudos.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.catalog_service import (
    get_catalog_health,
    get_catalog_verification,
    search_catalog,
)
from app.service import get_public_verification, list_public_cases

# ── Aplicación ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Tree Blueprint - Huella Digital del Árbol",
    description=(
        "API prototípica para consultar consistencia y trazabilidad "
        "del origen de productos forestales."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── Middleware de seguridad ────────────────────────────────────────────────────

_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}


@app.middleware("http")
async def add_security_headers(request: Request, call_next: Any) -> Any:
    """Añade encabezados de seguridad mínimos a todas las respuestas."""
    response = await call_next(request)
    for header, value in _SECURITY_HEADERS.items():
        response.headers[header] = value
    return response


# ── Endpoints ─────────────────────────────────────────────────────────────────


@app.get("/", summary="Información del servicio")
def root() -> dict:
    """Estado general del servicio."""
    return {
        "service": "Huella Digital del Árbol",
        "version": "1.0.0",
        "status": "operational",
        "documentation": "/docs",
    }


@app.get("/health", summary="Salud del servicio")
def health() -> dict:
    """
    Comprueba el acceso real a SQLite.

    Responde HTTP 503 si la base de datos no puede consultarse.
    """
    try:
        cases = list_public_cases()
        payload = {
            "status": "ok",
            "database_mode": "read-only",
            "case_count": len(cases),
        }
        try:
            payload.update(get_catalog_health())
        except (FileNotFoundError, OSError, Exception):
            payload.update(
                {
                    "catalog_available": False,
                    "catalog_trace_count": 0,
                }
            )
        return payload
    except (FileNotFoundError, OSError, Exception) as exc:
        # No se exponen rutas locales ni trazas internas
        raise HTTPException(
            status_code=503,
            detail="Base de datos no disponible",
        ) from exc


@app.get("/api/v1/search", summary="Búsqueda de catálogo")
def search(query: str = Query(..., max_length=100)) -> dict:
    """
    Busca por GTF, troza, árbol o título habilitante.

    La búsqueda usa coincidencia exacta sobre search_identifiers.
    """
    normalized_query = query.strip()
    if not normalized_query:
        raise HTTPException(
            status_code=422,
            detail="La consulta no puede estar vacía",
        )
    return search_catalog(normalized_query)


@app.get("/api/v1/cases", summary="Lista de expedientes")
def get_cases() -> list[dict]:
    """
    Devuelve la lista pública de todos los expedientes.

    No incluye registros crudos ni rutas internas.
    """
    return list_public_cases()


@app.get(
    "/api/v1/verifications/{case_id}",
    summary="Comprobante de trazabilidad",
)
def get_verification(case_id: str) -> dict:
    """
    Devuelve el comprobante público completo de un expediente.

    - HTTP 200 si el caso existe.
    - HTTP 404 si el case_id no existe.

    El case_id nunca se interpola directamente en SQL;
    la capa repository usa placeholders.
    """
    result = get_public_verification(case_id)
    if result is None:
        result = get_catalog_verification(case_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Comprobante no encontrado",
        )
    return result
