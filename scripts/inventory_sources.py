"""
Inventario verificable de las ocho fuentes del catalogo.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.catalog_parsers import collect_source_inventory, resolve_repo_root


def main() -> None:
    repo_root = resolve_repo_root()
    inventory = collect_source_inventory(repo_root)

    staging_dir = repo_root / "staging" / "catalog"
    staging_dir.mkdir(parents=True, exist_ok=True)
    output_path = staging_dir / "source_inventory.json"
    output_path.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"REPO_ROOT={repo_root}")
    for source in inventory["sources"]:
        print(
            json.dumps(
                source,
                ensure_ascii=False,
            )
        )
    print(f"INVENTORY_JSON={output_path.relative_to(repo_root).as_posix()}")


if __name__ == "__main__":
    main()
