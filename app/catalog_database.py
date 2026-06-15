"""
Conexión SQLite de solo lectura para db/huella_catalog.db.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "db" / "huella_catalog.db"


def open_catalog_readonly_connection() -> sqlite3.Connection:
    """
    Abre una conexión SQLite de solo lectura sobre el catálogo.
    """
    db_path = DATABASE_PATH.resolve()
    if not db_path.exists():
        raise FileNotFoundError(
            f"No existe la base de datos del catálogo: {db_path}\n"
            "Ejecuta primero: python scripts/build_catalog.py"
        )

    connection = sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA query_only = ON")
    return connection
