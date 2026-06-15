"""
tests/test_public_query.py

Suite de pruebas unitarias para la Micro-fase 5A.

Ejecutar con:
    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import sqlite3
import sys
import unittest
from pathlib import Path

# ── Garantizar que el paquete app sea importable ──────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.database import open_readonly_connection  # noqa: E402
from app.service import get_public_verification, list_public_cases  # noqa: E402

_CLEAN_ID = "clean-pc01-501"
_INCONSISTENT_ID = "inconsistent-pc01-1170"

_PRIVATE_STRINGS = (
    "source_path",
    "source_json_path",
    "observations",
    "coordenada",
    "ruc",
    "dni",
)


class TestListPublicCases(unittest.TestCase):
    """Pruebas sobre list_public_cases()."""

    def setUp(self) -> None:
        self.cases = list_public_cases()

    def test_returns_exactly_two_cases(self) -> None:
        self.assertEqual(len(self.cases), 2)

    def test_clean_case_present(self) -> None:
        ids = {c["case_id"] for c in self.cases}
        self.assertIn(_CLEAN_ID, ids)

    def test_inconsistent_case_present(self) -> None:
        ids = {c["case_id"] for c in self.cases}
        self.assertIn(_INCONSISTENT_ID, ids)

    def test_attestation_eligible_is_bool(self) -> None:
        for case in self.cases:
            self.assertIsInstance(case["attestation_eligible"], bool)


class TestCleanCaseDetail(unittest.TestCase):
    """Pruebas sobre el detalle del caso limpio."""

    def setUp(self) -> None:
        self.detail = get_public_verification(_CLEAN_ID)

    def test_detail_not_none(self) -> None:
        self.assertIsNotNone(self.detail)

    def test_case_id(self) -> None:
        self.assertEqual(self.detail["case_id"], _CLEAN_ID)

    def test_attestation_eligible_true(self) -> None:
        self.assertIs(self.detail["attestation_eligible"], True)

    def test_verification_status_consistent(self) -> None:
        self.assertEqual(self.detail["verification_status"], "CONSISTENTE")

    def test_has_one_troza(self) -> None:
        self.assertEqual(len(self.detail["trozas"]), 1)

    def test_has_one_gtf(self) -> None:
        self.assertEqual(len(self.detail["gtf"]), 1)

    def test_schema_version(self) -> None:
        self.assertEqual(self.detail["schema_version"], "1.0")

    def test_disclaimer_present(self) -> None:
        self.assertIn("disclaimer", self.detail)
        self.assertTrue(len(self.detail["disclaimer"]) > 0)

    def test_lineage_stages_is_list(self) -> None:
        self.assertIsInstance(self.detail["lineage_stages"], list)
        self.assertGreater(len(self.detail["lineage_stages"]), 0)

    def test_validaciones_is_list(self) -> None:
        self.assertIsInstance(self.detail["validaciones"], list)

    def test_validaciones_have_name_and_status(self) -> None:
        for v in self.detail["validaciones"]:
            self.assertIn("name", v)
            self.assertIn("status", v)
            self.assertIn(v["status"], {"PASS", "FAIL", "NOT_EVALUATED"})

    def test_evidence_hash_present(self) -> None:
        self.assertIn("evidence_hash_sha256", self.detail)
        self.assertEqual(len(self.detail["evidence_hash_sha256"]), 64)


class TestInconsistentCaseDetail(unittest.TestCase):
    """Pruebas sobre el detalle del caso inconsistente."""

    def setUp(self) -> None:
        self.detail = get_public_verification(_INCONSISTENT_ID)

    def test_detail_not_none(self) -> None:
        self.assertIsNotNone(self.detail)

    def test_case_id(self) -> None:
        self.assertEqual(self.detail["case_id"], _INCONSISTENT_ID)

    def test_attestation_eligible_false(self) -> None:
        self.assertIs(self.detail["attestation_eligible"], False)

    def test_verification_status_inconsistent(self) -> None:
        self.assertEqual(self.detail["verification_status"], "INCONSISTENTE")

    def test_has_three_trozas(self) -> None:
        self.assertEqual(len(self.detail["trozas"]), 3)

    def test_has_three_gtf(self) -> None:
        self.assertEqual(len(self.detail["gtf"]), 3)

    def test_evidence_hash_present(self) -> None:
        self.assertIn("evidence_hash_sha256", self.detail)
        self.assertEqual(len(self.detail["evidence_hash_sha256"]), 64)


class TestNonExistentCase(unittest.TestCase):
    """Pruebas cuando el case_id no existe."""

    def test_returns_none_for_unknown_id(self) -> None:
        result = get_public_verification("no-existe-este-id")
        self.assertIsNone(result)

    def test_returns_none_for_empty_string(self) -> None:
        result = get_public_verification("")
        self.assertIsNone(result)


class TestPrivateFieldsAbsent(unittest.TestCase):
    """Verifica que los campos privados no aparezcan en el JSON público."""

    def _serialized(self, case_id: str) -> str:
        detail = get_public_verification(case_id)
        self.assertIsNotNone(detail)
        return json.dumps(detail, ensure_ascii=False)

    def _check_private_fields(self, serialized: str, label: str) -> None:
        for field in _PRIVATE_STRINGS:
            with self.subTest(field=field, case=label):
                self.assertNotIn(field, serialized)

    def test_clean_case_no_private_fields(self) -> None:
        self._check_private_fields(self._serialized(_CLEAN_ID), _CLEAN_ID)

    def test_inconsistent_case_no_private_fields(self) -> None:
        self._check_private_fields(
            self._serialized(_INCONSISTENT_ID), _INCONSISTENT_ID
        )

    def test_campo_r_value_absent_in_clean(self) -> None:
        """El campo R no debe estar en validaciones públicas."""
        detail = get_public_verification(_CLEAN_ID)
        names = [v["name"] for v in detail["validaciones"]]
        self.assertNotIn("campo_r_validado", names)

    def test_campo_r_value_absent_in_inconsistent(self) -> None:
        detail = get_public_verification(_INCONSISTENT_ID)
        names = [v["name"] for v in detail["validaciones"]]
        self.assertNotIn("campo_r_validado", names)


class TestReadonlyConnection(unittest.TestCase):
    """Verifica que la conexión rechaza operaciones de escritura."""

    def test_create_table_raises_operational_error(self) -> None:
        conn = open_readonly_connection()
        try:
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("CREATE TABLE _test_forbidden (x INTEGER)")
        finally:
            conn.close()

    def test_insert_raises_operational_error(self) -> None:
        conn = open_readonly_connection()
        try:
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute(
                    "INSERT INTO build_metadata (metadata_key, metadata_value) "
                    "VALUES (?, ?)",
                    ("_test", "_value"),
                )
        finally:
            conn.close()

    def test_drop_table_raises_operational_error(self) -> None:
        conn = open_readonly_connection()
        try:
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("DROP TABLE cases")
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
