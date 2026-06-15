"""
Normalizacion y utilidades puras para el catalogo SQLite.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Any


_NULL_LITERALS = {"", "[NULL]", "NULL", "NAN", "NONE"}


def clean_text(value: Any) -> str | None:
    """Normaliza texto vacio y espacios sin interpretar significado."""
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    if text.upper() in _NULL_LITERALS:
        return None

    return re.sub(r"\s+", " ", text)


def normalize_header(value: Any) -> str:
    """Convierte encabezados a una forma comparable."""
    text = clean_text(value) or ""
    text = text.lower()
    replacements = {
        "°": " ",
        "º": " ",
        "n°": "n ",
        "#": "num",
        "(": " ",
        ")": " ",
        "/": " ",
        "-": " ",
        ".": " ",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def simplify_for_matching(value: Any) -> str:
    text = clean_text(value) or ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9|/]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_title(value: Any) -> str | None:
    text = clean_text(value)
    if text is None:
        return None
    upper = text.upper()
    upper = re.sub(r"\s*/\s*", "/", upper)
    upper = re.sub(r"\s*-\s*", "-", upper)
    upper = re.sub(r"\s+", " ", upper).strip()
    return upper


def normalize_parcela(value: Any) -> str | None:
    text = clean_text(value)
    if text is None:
        return None

    upper = unicodedata.normalize("NFKD", text.upper())
    upper = "".join(ch for ch in upper if not unicodedata.combining(ch))
    upper = re.sub(r"[^A-Z0-9]+", " ", upper).strip()

    match = re.search(r"\bPCA?\s*0*([0-9]+)\b", upper)
    if not match:
        match = re.search(r"\bPC\s*0*([0-9]+)\b", upper)
    if match:
        return f"PC {int(match.group(1)):02d}"

    return upper


def normalize_tree_code(value: Any) -> str | None:
    text = clean_text(value)
    if text is None:
        return None

    numeric = text.replace(",", "")
    if re.fullmatch(r"[0-9]+(?:\.0+)?", numeric):
        return str(int(Decimal(numeric)))

    return text.upper()


def normalize_log_code(value: Any) -> str | None:
    text = clean_text(value)
    if text is None:
        return None

    upper = text.upper().replace("\\", "/")
    upper = re.sub(r"\s*[-/]\s*", "/", upper)
    upper = re.sub(r"\s+", " ", upper).strip()
    upper = upper.replace(" ", "/")
    match = re.fullmatch(r"(.+?)/([A-Z0-9]+)", upper)
    if not match:
        return upper

    tree_code = normalize_tree_code(match.group(1))
    suffix = match.group(2).upper()
    if tree_code is None:
        return None
    return f"{tree_code}/{suffix}"


def parent_tree_from_log_code(value: Any) -> str | None:
    normalized = normalize_log_code(value)
    if normalized is None or "/" not in normalized:
        return None
    return normalized.split("/", 1)[0]


def normalize_gtf(value: Any) -> str | None:
    text = clean_text(value)
    if text is None:
        return None

    upper = text.upper()
    upper = re.sub(r"\s+", "", upper)
    upper = re.sub(r"-{2,}", "-", upper)
    return upper


def normalize_species(value: Any) -> str | None:
    text = clean_text(value)
    if text is None:
        return None

    if "|" in text:
        left, right = [clean_text(part) or "" for part in text.split("|", 1)]
        return f"{left} | {right}".strip()

    return text


def species_signature(value: Any) -> str | None:
    normalized = normalize_species(value)
    if normalized is None:
        return None

    if "|" in normalized:
        scientific, common = [part.strip() for part in normalized.split("|", 1)]
        scientific_tokens = simplify_for_matching(scientific).split()
        common_tokens = simplify_for_matching(common).split()
        lead = " ".join(scientific_tokens[:2])
        return f"{lead}|{' '.join(common_tokens)}".strip("|")

    tokens = simplify_for_matching(normalized).split()
    if len(tokens) >= 2:
        return " ".join(tokens[:2])
    return " ".join(tokens)


def canonicalize_species(
    raw_value: Any,
    canonical_by_signature: dict[str, str],
) -> str | None:
    """Mapea una especie textual a una forma canonica cuando es reconocible."""
    normalized = normalize_species(raw_value)
    if normalized is None:
        return None

    if normalized in canonical_by_signature.values():
        return normalized

    signature = species_signature(normalized)
    if signature and signature in canonical_by_signature:
        return canonical_by_signature[signature]

    simplified = simplify_for_matching(normalized)
    tokens = simplified.split()
    if len(tokens) >= 2:
        lead = " ".join(tokens[:2])
        if lead in canonical_by_signature:
            return canonical_by_signature[lead]
        for key, candidate in canonical_by_signature.items():
            if key.startswith(lead):
                return candidate

    return normalized


def normalize_decimal(value: Any) -> str | None:
    text = clean_text(value)
    if text is None:
        return None

    compact = text.replace(",", "")
    try:
        decimal = Decimal(compact)
    except InvalidOperation as exc:
        raise ValueError(f"Valor decimal invalido: {value!r}") from exc

    normalized = format(decimal.normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")

    return normalized or "0"


def normalize_date(value: Any) -> str | None:
    text = clean_text(value)
    if text is None:
        return None

    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")

    for fmt in ("%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return text


def composite_tree_key(
    titulo_habilitante: str | None,
    parcela_corta: str | None,
    codigo_arbol: str | None,
) -> str | None:
    if not (titulo_habilitante and parcela_corta and codigo_arbol):
        return None
    return "||".join([titulo_habilitante, parcela_corta, codigo_arbol])


def composite_log_key(
    titulo_habilitante: str | None,
    parcela_corta: str | None,
    codigo_troza: str | None,
) -> str | None:
    if not (titulo_habilitante and parcela_corta and codigo_troza):
        return None
    return "||".join([titulo_habilitante, parcela_corta, codigo_troza])


def composite_balance_key(
    titulo_habilitante: str | None,
    parcela_corta: str | None,
    especie: str | None,
) -> str | None:
    if not (titulo_habilitante and parcela_corta and especie):
        return None
    return "||".join([titulo_habilitante, parcela_corta, especie])


def canonical_json_hash(payload: Any) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
