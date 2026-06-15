"""
app/database.py

Provee open_readonly_connection(): una conexión SQLite de solo lectura
sobre db/huella_origen.db.

Reglas:
- No mantiene conexiones globales.
- El consumidor es responsable de cerrar la conexión
  (mediante contextlib.closing o try/finally).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "db" / "huella_origen.db"


def open_readonly_connection() -> sqlite3.Connection:
    """
    Abre y devuelve una conexión SQLite de solo lectura.

    Raises
    ------
    FileNotFoundError
        Si db/huella_origen.db no existe en disco.
    """
    db_path = DATABASE_PATH.resolve()

    if not db_path.exists():
        raise FileNotFoundError(
            f"No existe la base de datos: {db_path}\n"
            "Ejecuta primero: python scripts/build_db.py"
        )

    uri = db_path.as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA query_only = ON")

    return connection
