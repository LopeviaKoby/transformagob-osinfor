"""
tests/test_api.py

Suite de pruebas unitarias para la Micro-fase 5B.

Ejecutar con:
    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import sys
import unittest
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


def _assert_security_headers(test: unittest.TestCase, response: object) -> None:
    for header, value in _SECURITY_HEADERS.items():
        with test.subTest(header=header):
            test.assertEqual(response.headers.get(header), value)


def _assert_no_restricted_fields(
    test: unittest.TestCase, body: str, label: str
) -> None:
    lower = body.lower()
    for field in _RESTRICTED_STRINGS:
        with test.subTest(field=field, label=label):
            test.assertNotIn(field.lower(), lower)


class TestRoot(unittest.TestCase):
    def setUp(self) -> None:
        self.resp = client.get("/")

    def test_status_200(self) -> None:
        self.assertEqual(self.resp.status_code, 200)

    def test_body_fields(self) -> None:
        data = self.resp.json()
        self.assertEqual(data["service"], "Huella Digital del Árbol")
        self.assertEqual(data["version"], "1.0.0")
        self.assertEqual(data["status"], "operational")
        self.assertEqual(data["documentation"], "/docs")

    def test_security_headers(self) -> None:
        _assert_security_headers(self, self.resp)


class TestHealth(unittest.TestCase):
    def setUp(self) -> None:
        self.resp = client.get("/health")
        self.data = self.resp.json()

    def test_status_200(self) -> None:
        self.assertEqual(self.resp.status_code, 200)

    def test_status_ok(self) -> None:
        self.assertEqual(self.data["status"], "ok")

    def test_database_mode(self) -> None:
        self.assertEqual(self.data["database_mode"], "read-only")

    def test_case_count(self) -> None:
        self.assertEqual(self.data["case_count"], 2)

    def test_security_headers(self) -> None:
        _assert_security_headers(self, self.resp)


class TestListCases(unittest.TestCase):
    def setUp(self) -> None:
        self.resp = client.get("/api/v1/cases")
        self.data = self.resp.json()

    def test_status_200(self) -> None:
        self.assertEqual(self.resp.status_code, 200)

    def test_returns_two_cases(self) -> None:
        self.assertEqual(len(self.data), 2)

    def test_both_ids_present(self) -> None:
        ids = {c["case_id"] for c in self.data}
        self.assertIn(_CLEAN_ID, ids)
        self.assertIn(_INCONSISTENT_ID, ids)

    def test_security_headers(self) -> None:
        _assert_security_headers(self, self.resp)

    def test_no_restricted_fields(self) -> None:
        _assert_no_restricted_fields(self, self.resp.text, "GET /api/v1/cases")


class TestCleanCaseVerification(unittest.TestCase):
    def setUp(self) -> None:
        self.resp = client.get(f"/api/v1/verifications/{_CLEAN_ID}")
        self.data = self.resp.json()

    def test_status_200(self) -> None:
        self.assertEqual(self.resp.status_code, 200)

    def test_case_id(self) -> None:
        self.assertEqual(self.data["case_id"], _CLEAN_ID)

    def test_attestation_eligible_true(self) -> None:
        self.assertIs(self.data["attestation_eligible"], True)

    def test_verification_status(self) -> None:
        self.assertEqual(self.data["verification_status"], "CONSISTENTE")

    def test_one_troza(self) -> None:
        self.assertEqual(len(self.data["trozas"]), 1)

    def test_one_gtf(self) -> None:
        self.assertEqual(len(self.data["gtf"]), 1)

    def test_hash_intact(self) -> None:
        self.assertEqual(self.data["evidence_hash_sha256"], _CLEAN_HASH)

    def test_security_headers(self) -> None:
        _assert_security_headers(self, self.resp)

    def test_no_restricted_fields(self) -> None:
        _assert_no_restricted_fields(
            self, self.resp.text, f"GET /api/v1/verifications/{_CLEAN_ID}"
        )

    def test_schema_version(self) -> None:
        self.assertEqual(self.data.get("schema_version"), "1.0")

    def test_disclaimer_present(self) -> None:
        self.assertIn("disclaimer", self.data)


class TestInconsistentCaseVerification(unittest.TestCase):
    def setUp(self) -> None:
        self.resp = client.get(f"/api/v1/verifications/{_INCONSISTENT_ID}")
        self.data = self.resp.json()

    def test_status_200(self) -> None:
        self.assertEqual(self.resp.status_code, 200)

    def test_case_id(self) -> None:
        self.assertEqual(self.data["case_id"], _INCONSISTENT_ID)

    def test_attestation_eligible_false(self) -> None:
        self.assertIs(self.data["attestation_eligible"], False)

    def test_verification_status(self) -> None:
        self.assertEqual(self.data["verification_status"], "INCONSISTENTE")

    def test_three_trozas(self) -> None:
        self.assertEqual(len(self.data["trozas"]), 3)

    def test_three_gtf(self) -> None:
        self.assertEqual(len(self.data["gtf"]), 3)

    def test_hash_intact(self) -> None:
        self.assertEqual(self.data["evidence_hash_sha256"], _INCONSISTENT_HASH)

    def test_security_headers(self) -> None:
        _assert_security_headers(self, self.resp)

    def test_no_restricted_fields(self) -> None:
        _assert_no_restricted_fields(
            self, self.resp.text, f"GET /api/v1/verifications/{_INCONSISTENT_ID}"
        )


class TestNotFound(unittest.TestCase):
    def setUp(self) -> None:
        self.resp = client.get("/api/v1/verifications/no-existe-este-id")

    def test_status_404(self) -> None:
        self.assertEqual(self.resp.status_code, 404)

    def test_detail_message(self) -> None:
        self.assertEqual(self.resp.json()["detail"], "Comprobante no encontrado")

    def test_security_headers(self) -> None:
        _assert_security_headers(self, self.resp)


class TestMethodNotAllowed(unittest.TestCase):
    def test_post_cases_returns_405(self) -> None:
        resp = client.post("/api/v1/cases", json={})
        self.assertEqual(resp.status_code, 405)

    def test_put_verification_returns_405(self) -> None:
        resp = client.put(f"/api/v1/verifications/{_CLEAN_ID}", json={})
        self.assertEqual(resp.status_code, 405)

    def test_delete_verification_returns_405(self) -> None:
        resp = client.delete(f"/api/v1/verifications/{_CLEAN_ID}")
        self.assertEqual(resp.status_code, 405)


class TestOpenAPI(unittest.TestCase):
    def test_openapi_json_200(self) -> None:
        resp = client.get("/openapi.json")
        self.assertEqual(resp.status_code, 200)

    def test_docs_200(self) -> None:
        resp = client.get("/docs")
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
