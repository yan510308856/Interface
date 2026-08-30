"""Deterministic unit tests for Stage D0 validation boundaries."""

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import freeze_d0  # noqa: E402
import validate_d0  # noqa: E402


class D0ValidationTests(unittest.TestCase):
    def test_frozen_files_match_digest_manifest(self):
        recorded = json.loads(freeze_d0.DIGEST_PATH.read_text(encoding="utf-8"))
        self.assertEqual(recorded, freeze_d0.compute_manifest())

    def test_digest_is_sensitive_without_mutating_file(self):
        data = (ROOT / freeze_d0.FROZEN_PATHS[0]).read_bytes()
        self.assertNotEqual(
            freeze_d0.sha256_bytes(data),
            freeze_d0.sha256_bytes(data + b"probe"),
        )

    def test_four_cells_only_differ_in_allowed_fields(self):
        self.assertEqual("PASS", validate_d0.check_four_cells().status)

    def test_declared_digests_and_operation_permissions_match(self):
        self.assertEqual("PASS", validate_d0.check_internal_consistency().status)

    def test_atomic_rejects_unknown_operation_and_audits_it(self):
        boundary = validate_d0.InterfaceBoundary({"read_file"})
        with self.assertRaises(ValueError):
            boundary.atomic('{"operation":"open_socket","arguments":{}}')
        self.assertEqual("invalid_request", boundary.audit[-1]["error"])

    def test_restricted_python_rejects_import_and_audits_it(self):
        boundary = validate_d0.InterfaceBoundary({"read_file"})
        with self.assertRaises(ValueError):
            boundary.restricted_python("import os")
        self.assertEqual("permission_denied", boundary.audit[-1]["error"])


if __name__ == "__main__":
    unittest.main()
