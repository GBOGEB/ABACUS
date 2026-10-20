"""Adversarial proof that pytest marker checks cannot return false green."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sync_pytest_config as sync
import verify_pytest_sync as legacy


CANONICAL = (
    "[pytest]\n"
    "markers =\n"
    "    smoke: Smoke tests\n"
    "    integration: Integration tests\n"
)


class PytestMarkerSyncFailClosedTests(unittest.TestCase):
    def _files(self, root, *, ini=CANONICAL, toml=None):
        (root / "pytest.ini").write_text(ini, encoding="utf-8")
        if toml is not None:
            (root / "pyproject.toml").write_text(toml, encoding="utf-8")

    def test_canonical_only_is_not_falsely_called_synchronized(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            self._files(root)
            receipt = sync.validate(root)
            self.assertEqual(receipt["marker_count"], 2)
            self.assertEqual(receipt["status"], "SINGLE_CANONICAL_SOURCE_VALIDATED")
            self.assertEqual(receipt["secondary_config"], "NOT_DECLARED")
            self.assertFalse(receipt["source_mutation"])

    def test_exact_secondary_contract_is_synchronized(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            self._files(
                root,
                toml='[tool.pytest.ini_options]\n'
                     'markers = ["smoke: Smoke tests", '
                     '"integration: Integration tests"]\n',
            )
            self.assertEqual(sync.validate(root)["status"], "SYNCHRONIZED")

    def test_missing_secondary_marker_fails_closed(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            self._files(root, toml='[tool.pytest.ini_options]\n'
                                   'markers = ["smoke: Smoke tests"]\n')
            with self.assertRaisesRegex(ValueError, "missing="):
                sync.validate(root)

    def test_changed_secondary_description_fails_closed(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            self._files(
                root,
                toml='[tool.pytest.ini_options]\n'
                     'markers = ["smoke: Changed description", '
                     '"integration: Integration tests"]\n',
            )
            with self.assertRaisesRegex(ValueError, "changed="):
                sync.validate(root)

    def test_duplicate_canonical_marker_fails_closed(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            self._files(root, ini=CANONICAL + "    smoke: Another meaning\n")
            with self.assertRaisesRegex(ValueError, "duplicate marker"):
                sync.validate(root)

    def test_missing_canonical_or_empty_markers_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            with self.assertRaisesRegex(ValueError, "Missing canonical"):
                sync.validate(root)
            self._files(root, ini="[pytest]\nmarkers =\n")
            with self.assertRaisesRegex(ValueError, "empty marker"):
                sync.validate(root)

    def test_legacy_shim_propagates_denial(self):
        with mock.patch.object(legacy, "sync_main", return_value=1) as invoke:
            self.assertEqual(legacy.main(), 1)
            invoke.assert_called_once_with(["--dry-run"])


if __name__ == "__main__":
    unittest.main()
