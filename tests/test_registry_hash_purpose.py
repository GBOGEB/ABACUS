"""Legacy registry identities must work when security-mode MD5 is disabled."""

import hashlib
from pathlib import Path
from unittest.mock import patch

from DMAIC_V3.canonical_refactoring import CanonicalDocumentRefactorer
from DMAIC_V3.phases.phase7_action_tracking import ActionTracker
from DMAIC_V3.phases.phase8_todo_management import TODOTracker


def test_registry_ids_preserve_legacy_bytes_under_fips_policy(tmp_path):
    original = hashlib.md5
    calls = []

    def nonsecurity_only(data, *, usedforsecurity=True):
        if usedforsecurity:
            raise ValueError("MD5 is disabled for security uses")
        calls.append(data)
        return original(data, usedforsecurity=False)

    document = CanonicalDocumentRefactorer(tmp_path)
    action = ActionTracker(tmp_path)
    todo = TODOTracker(tmp_path)
    action_input = {"phase": "p7", "agent": "worker", "timestamp": "2026-10-19"}
    todo_input = {"phase": "p8", "description": "review", "timestamp": "2026-10-19"}
    payloads = [
        str(Path("review.md")).encode(),
        b"p7_worker_2026-10-19",
        b"p8_review_2026-10-19",
    ]
    expected = [
        original(data, usedforsecurity=False).hexdigest()[:12] for data in payloads
    ]

    with patch("hashlib.md5", nonsecurity_only):
        actual = [
            document._generate_doc_id(tmp_path / "review.md"),
            action.register_action(action_input),
            todo.register_todo(todo_input),
        ]

    assert actual == expected
    assert calls == payloads
    assert action.local_actions[0]["action_id"] == expected[1]
    assert todo.local_todos[0]["todo_id"] == expected[2]
