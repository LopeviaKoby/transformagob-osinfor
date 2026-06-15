"""
Pruebas API para búsqueda y detalle del catálogo.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.catalog_database import open_catalog_readonly_connection  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)

_CATALOG_TRACE_501 = "1503"
_RESTRICTED_STRINGS = [
    "source_relative_path",
    "source_sheet",
    "source_row_number",
    "raw/",
    "staging/",
    "db/",
    "ruc",
    "dni",
    "\"r\"",
]


def _assert_no_private_fields(test: unittest.TestCase, body: str) -> None:
    lower = body.lower()
    for field in _RESTRICTED_STRINGS:
        with test.subTest(field=field):
            test.assertNotIn(field.lower(), lower)


class TestCatalogSearch(unittest.TestCase):
    def test_search_gtf_017_0001426(self) -> None:
        resp = client.get("/api/v1/search", params={"query": "017-0001426"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["detected_type"], "GTF")
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["codigo_arbol"], "501")

    def test_search_log_501_a(self) -> None:
        resp = client.get("/api/v1/search", params={"query": "501/A"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["detected_type"], "TROZA")
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["codigo_arbol"], "501")

    def test_search_tree_501_returns_multiple_results(self) -> None:
        resp = client.get("/api/v1/search", params={"query": "501"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["detected_type"], "ARBOL")
        self.assertGreater(data["count"], 1)

    def test_search_inexistent_returns_empty_list(self) -> None:
        resp = client.get("/api/v1/search", params={"query": "NO-EXISTE-999"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["results"], [])

    def test_search_empty_query_returns_422(self) -> None:
        resp = client.get("/api/v1/search", params={"query": "   "})
        self.assertEqual(resp.status_code, 422)

    def test_post_search_returns_405(self) -> None:
        resp = client.post("/api/v1/search", json={})
        self.assertEqual(resp.status_code, 405)


class TestCatalogVerification(unittest.TestCase):
    def test_catalog_detail_by_trace_id(self) -> None:
        resp = client.get(f"/api/v1/verifications/{_CATALOG_TRACE_501}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["case_id"], _CATALOG_TRACE_501)
        self.assertEqual(data["verification_status"], "CONSISTENTE")
        self.assertEqual(data["codigo_arbol"], "501")

    def test_balance_associated(self) -> None:
        resp = client.get(f"/api/v1/verifications/{_CATALOG_TRACE_501}")
        data = resp.json()
        self.assertEqual(data["balance"]["available"], True)
        self.assertIn("authorized_m3", data["balance"])
        self.assertIn("remaining_reported_m3", data["balance"])

    def test_allowed_statuses(self) -> None:
        statuses = {
            client.get("/api/v1/verifications/1503").json()["verification_status"],
            client.get("/api/v1/verifications/164").json()["verification_status"],
            client.get("/api/v1/verifications/1").json()["verification_status"],
        }
        self.assertTrue(
            statuses.issubset(
                {"CONSISTENTE", "POR_REVISAR", "INCOMPLETO", "NO_EVALUADO", "INCONSISTENTE"}
            )
        )

    def test_private_fields_absent(self) -> None:
        resp = client.get(f"/api/v1/verifications/{_CATALOG_TRACE_501}")
        self.assertEqual(resp.status_code, 200)
        _assert_no_private_fields(self, resp.text)

    def test_old_cases_still_work(self) -> None:
        resp = client.get("/api/v1/verifications/clean-pc01-501")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["case_id"], "clean-pc01-501")

    def test_health_reports_catalog(self) -> None:
        resp = client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["catalog_available"], True)
        self.assertEqual(data["catalog_trace_count"], 10468)


class TestCatalogReadonlyConnection(unittest.TestCase):
    def test_catalog_database_rejects_writes(self) -> None:
        conn = open_catalog_readonly_connection()
        try:
            with self.assertRaises(Exception):
                conn.execute("CREATE TABLE _forbidden_catalog (x INTEGER)")
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
