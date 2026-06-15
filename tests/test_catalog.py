"""
Pruebas del catalogo SQLite.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.build_catalog import EXPECTED_INDEXES, build, compute_checks_and_status  # noqa: E402
from scripts.catalog_normalization import (  # noqa: E402
    canonical_json_hash,
    composite_balance_key,
    composite_log_key,
    composite_tree_key,
    normalize_decimal,
    normalize_gtf,
    normalize_log_code,
    normalize_parcela,
    normalize_tree_code,
    parent_tree_from_log_code,
)
from scripts.catalog_parsers import detect_header_row  # noqa: E402


CATALOG_DB = _REPO_ROOT / "db" / "huella_catalog.db"
TRACE_501 = "GOREMAD-GRRNYGA-DRFFS/DFFS-TAH/P-MAD-D-008-15||PC 01||501"
TRACE_1170 = "GOREMAD-GRRNYGA-DRFFS/DFFS-TAH/P-MAD-D-008-15||PC 01||1170"


class TestCatalogNormalization(unittest.TestCase):
    def test_normalize_parcela_variants(self) -> None:
        for raw in ["PC1", "PC 1", "PC01", "PC 01", "PCA 1"]:
            self.assertEqual(normalize_parcela(raw), "PC 01")

    def test_normalize_tree_code_variants(self) -> None:
        for raw in ["501", "501.0", 501]:
            self.assertEqual(normalize_tree_code(raw), "501")

    def test_normalize_log_code_variants(self) -> None:
        for raw in ["501-A", "501 A", "501/A"]:
            self.assertEqual(normalize_log_code(raw), "501/A")

    def test_parent_tree_from_log_code(self) -> None:
        self.assertEqual(parent_tree_from_log_code("501-A"), "501")

    def test_normalize_gtf_preserves_zeros(self) -> None:
        self.assertEqual(normalize_gtf("017-0001426"), "017-0001426")

    def test_normalize_decimal_uses_canonical_text(self) -> None:
        self.assertEqual(normalize_decimal("5.8810"), "5.881")

    def test_composite_keys(self) -> None:
        self.assertEqual(
            composite_tree_key("T", "PC 01", "501"),
            "T||PC 01||501",
        )
        self.assertEqual(
            composite_log_key("T", "PC 01", "501/A"),
            "T||PC 01||501/A",
        )
        self.assertEqual(
            composite_balance_key("T", "PC 01", "Brosimum guianense | Manchinga"),
            "T||PC 01||Brosimum guianense | Manchinga",
        )

    def test_header_detection(self) -> None:
        rows = [
            ["Titular", None, None, "X"],
            ["Titulo Habilitante", None, None, "Y"],
            ["N° Resolucion", None, None, "Z"],
            ["Vigencia", None, None, "A"],
            ["N°", "Fecha", "Codigo del Arbol", "R", "Especie", "Volumen(m3)"],
        ]
        index = detect_header_row(rows, {"codigo_del_arbol", "fecha", "especie", "volumen"})
        self.assertEqual(index, 4)


class TestCatalogChecks(unittest.TestCase):
    def _base_trace(self) -> dict:
        return {
            "tree": {"dummy": True},
            "felling": {"dummy": True},
            "logs": [{"codigo_troza_norm": "501/A"}],
            "dispatches": [{"codigo_troza_norm": "501/A"}],
            "troza_set": {"501/A"},
            "gtf": ["017-0001426"],
            "titulo_habilitante_norm": "T",
            "parcela_corta_norm": "PC 01",
            "codigo_arbol_norm": "501",
            "especie_censo_norm": "Brosimum guianense | Manchinga",
            "especie_supervision_norm": "Brosimum guianense | Manchinga",
            "especie_operacion_norm": "Brosimum guianense | Manchinga",
            "volumen_censo_text": "5.881",
            "volumen_tala_text": "5.643",
            "volumen_trozado_text": "5.192",
            "trozas": ["501/A"],
            "lineage": [],
        }

    def test_gtf_with_multiple_logs_is_allowed_in_same_scope(self) -> None:
        trace = self._base_trace()
        trace["logs"] = [{"codigo_troza_norm": "501/A"}, {"codigo_troza_norm": "501/B"}]
        trace["dispatches"] = [{"codigo_troza_norm": "501/A"}, {"codigo_troza_norm": "501/B"}]
        trace["troza_set"] = {"501/A", "501/B"}
        trace["trozas"] = ["501/A", "501/B"]
        trace["gtf"] = ["017-0001426"]
        checks, status = compute_checks_and_status(
            trace,
            {"017-0001426": {("T", "PC 01")}},
            {"saldo_reportado_text": "10", "dummy": True},
        )
        self.assertEqual(checks["gtf_scope_consistent"]["status"], "PASS")
        self.assertEqual(status, "CONSISTENTE")

    def test_gtf_crossing_titles_fails(self) -> None:
        checks, status = compute_checks_and_status(
            self._base_trace(),
            {"017-0001426": {("T", "PC 01"), ("T2", "PC 02")}},
            {"saldo_reportado_text": "10", "dummy": True},
        )
        self.assertEqual(checks["gtf_scope_consistent"]["status"], "FAIL")
        self.assertEqual(status, "POR_REVISAR")

    def test_supervision_absent_is_not_evaluated(self) -> None:
        trace = self._base_trace()
        trace["especie_supervision_norm"] = None
        checks, status = compute_checks_and_status(
            trace,
            {"017-0001426": {("T", "PC 01")}},
            {"saldo_reportado_text": "10", "dummy": True},
        )
        self.assertEqual(checks["supervision_species_match"]["status"], "NOT_EVALUATED")
        self.assertEqual(status, "NO_EVALUADO")

    def test_missing_stage_becomes_incomplete(self) -> None:
        trace = self._base_trace()
        trace["logs"] = []
        trace["dispatches"] = []
        trace["troza_set"] = set()
        trace["trozas"] = []
        trace["gtf"] = []
        trace["volumen_trozado_text"] = None
        checks, status = compute_checks_and_status(trace, {}, {"saldo_reportado_text": "10"})
        self.assertEqual(checks["logs_present"]["status"], "NOT_EVALUATED")
        self.assertEqual(status, "INCOMPLETO")

    def test_volume_increase_becomes_fail(self) -> None:
        trace = self._base_trace()
        trace["volumen_trozado_text"] = "6"
        checks, status = compute_checks_and_status(
            trace,
            {"017-0001426": {("T", "PC 01")}},
            {"saldo_reportado_text": "10"},
        )
        self.assertEqual(checks["felling_volume_vs_logs"]["status"], "FAIL")
        self.assertEqual(status, "POR_REVISAR")

    def test_negative_balance_fails(self) -> None:
        checks, status = compute_checks_and_status(
            self._base_trace(),
            {"017-0001426": {("T", "PC 01")}},
            {"saldo_reportado_text": "-0.1"},
        )
        self.assertEqual(checks["species_balance_non_negative"]["status"], "FAIL")
        self.assertEqual(status, "POR_REVISAR")

    def test_r_field_never_interpreted(self) -> None:
        checks, _ = compute_checks_and_status(
            self._base_trace(),
            {"017-0001426": {("T", "PC 01")}},
            {"saldo_reportado_text": "10"},
        )
        self.assertEqual(checks["source_r_interpreted"]["status"], "NOT_EVALUATED")

    def test_hash_is_deterministic(self) -> None:
        left = {"b": 2, "a": [3, 1]}
        right = {"a": [3, 1], "b": 2}
        self.assertEqual(canonical_json_hash(left), canonical_json_hash(right))


class TestCatalogDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not CATALOG_DB.exists():
            build()
        cls.connection = sqlite3.connect(CATALOG_DB)
        cls.connection.row_factory = sqlite3.Row

    @classmethod
    def tearDownClass(cls) -> None:
        cls.connection.close()

    def test_foreign_keys(self) -> None:
        rows = self.connection.execute("PRAGMA foreign_key_check").fetchall()
        self.assertEqual(rows, [])

    def test_indices_exist(self) -> None:
        names = {
            row["name"]
            for row in self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
        }
        self.assertTrue(EXPECTED_INDEXES.issubset(names))

    def test_balance_association_for_501(self) -> None:
        row = self.connection.execute(
            """
            SELECT check_status
            FROM trace_checks
            WHERE trace_id = (
                SELECT trace_id FROM trace_catalog
                WHERE composite_tree_key = ?
            )
            AND check_name = 'species_balance_available'
            """,
            (TRACE_501,),
        ).fetchone()
        self.assertEqual(row["check_status"], "PASS")

    def test_case_501(self) -> None:
        row = self.connection.execute(
            """
            SELECT especie_censo_norm, volumen_censo_text, volumen_tala_text,
                   volumen_trozado_text, verification_status
            FROM trace_catalog
            WHERE composite_tree_key = ?
            """,
            (TRACE_501,),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["especie_censo_norm"], "Brosimum guianense | Manchinga")
        self.assertEqual(row["volumen_censo_text"], "5.881")
        self.assertEqual(row["volumen_tala_text"], "5.643")
        self.assertEqual(row["volumen_trozado_text"], "5.192")
        self.assertEqual(row["verification_status"], "CONSISTENTE")

    def test_case_1170(self) -> None:
        row = self.connection.execute(
            """
            SELECT especie_censo_norm, especie_supervision_norm, volumen_censo_text,
                   volumen_tala_text, volumen_trozado_text, verification_status
            FROM trace_catalog
            WHERE composite_tree_key = ?
            """,
            (TRACE_1170,),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["especie_censo_norm"], "Myroxylon balsamum | Estoraque")
        self.assertEqual(row["especie_supervision_norm"], "Hymenaea oblongifolia | Azúcar huayo")
        self.assertEqual(row["volumen_censo_text"], "10.065")
        self.assertEqual(row["volumen_tala_text"], "9.975")
        self.assertEqual(row["volumen_trozado_text"], "10.819")
        self.assertEqual(row["verification_status"], "POR_REVISAR")

    def test_search_identifiers_allow_ambiguous_tree_codes(self) -> None:
        count = self.connection.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM search_identifiers
            WHERE identifier_type = 'ARBOL' AND identifier_value_norm = '501'
            """,
        ).fetchone()["cnt"]
        self.assertGreaterEqual(count, 3)

    def test_gtf_has_multiple_logs(self) -> None:
        row = self.connection.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM dispatches
            WHERE numero_gtf_norm = '017-0001271'
            """,
        ).fetchone()
        self.assertGreater(row["cnt"], 1)

    def test_repeated_reconstruction_is_reproducible(self) -> None:
        before = hashlib.sha256(CATALOG_DB.read_bytes()).hexdigest()
        self.__class__.connection.close()
        build()
        self.__class__.connection = sqlite3.connect(CATALOG_DB)
        self.__class__.connection.row_factory = sqlite3.Row
        after = hashlib.sha256(CATALOG_DB.read_bytes()).hexdigest()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
