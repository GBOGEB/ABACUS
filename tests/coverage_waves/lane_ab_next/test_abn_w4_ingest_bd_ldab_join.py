"""Behaviour tests for tools/everred_v3/scripts/ingest_bd_ldab_join.py.

The real ``everred`` ledger module imports ``fcntl`` (Unix-only), so a stub
providing exactly SCHEMA, InvalidEvidence, append_event and valid_sha is used.
"""

import copy
import hashlib
import json
import re
import runpy
import sys
import types

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

REL = "tools/everred_v3/scripts/ingest_bd_ldab_join.py"
SCRIPT = REPO_ROOT / REL
SHA = "a" * 40
URL = "https://github.com/GBOGEB/ABACUS/actions/runs/5"


class _Invalid(ValueError):
    pass


def _make_stub():
    stub = types.ModuleType("everred")
    stub.SCHEMA = "abacus.everred.event.v3"
    stub.InvalidEvidence = _Invalid
    stub.appended = []

    def valid_sha(value):
        return isinstance(value, str) and bool(re.fullmatch("[0-9a-f]{40}", value))

    def append_event(path, event):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
        stub.appended.append((path, event))
        return event

    stub.valid_sha = valid_sha
    stub.append_event = append_event
    return stub


STUB = _make_stub()
_saved_path = list(sys.path)
mod = load(REL, name="abn_ingest_bd_ldab_join", deps={"everred": STUB})
sys.path[:] = _saved_path


def _doc():
    return dict(
        schema="bd.ldab.joined.census.v1",
        scope=dict(
            repository="GBOGEB/ABACUS",
            head_sha=SHA,
            evidence_url=URL,
            run_id=5,
            job_id=9,
        ),
        merge_admission="HOLD",
        authority_transfer=False,
        security_waiver=False,
        roots=[dict(root_id="BD-1"), dict(root_id="CI-2")],
        metrics=dict(full_bandit_unique=4, debug_receipts=3, comparable_delta=-1),
        unlinked_debug_receipts=[dict(x=1)],
    )


def test_to_event_maps_observation_only():
    doc = _doc()
    event = mod.to_event(doc)
    digest = hashlib.sha256(
        json.dumps(
            doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()
    assert event["id"] == "BDLDAB-" + digest[:24]
    assert event["schema"] == STUB.SCHEMA
    assert event["kind"] == "note" and event["provenance"] == "manual"
    assert event["repo"] == "GBOGEB/ABACUS" and event["sha"] == SHA
    ev = event["evidence"]
    assert ev["producer_sha256"] == digest
    assert ev["source_binding"]["run_url"] == URL
    assert ev["bandit_fingerprint_observations"] == 4
    assert ev["join_groups"] == 2
    assert ev["debug_receipts"] == 3
    assert ev["unlinked_debug_receipts"] == 1
    assert ev["compare"] == -1
    assert ev["root_causality"] == "UNCONFIRMED"
    assert ev["admission"] == "HOLD"
    assert ev["evidence_trust"] == "MANUAL_UNVERIFIED"
    assert ev["ingested_at"] == event["occurred_at"]


def _mutate(path, value):
    doc = _doc()
    target = doc
    for key in path[:-1]:
        target = target[key]
    if value is _DROP:
        del target[path[-1]]
    else:
        target[path[-1]] = value
    return doc


_DROP = object()


@pytest.mark.parametrize(
    "path, value, message",
    [
        (("schema",), "other", "expected bd.ldab"),
        (("scope",), "x", "missing source scope"),
        (("scope", "repository"), "noslash", "repository/SHA"),
        (("scope", "repository"), 5, "repository/SHA"),
        (("scope", "head_sha"), "A" * 40, "repository/SHA"),
        (("scope", "evidence_url"), "http://x/y", "unbound"),
        (("scope", "evidence_url"), None, "unbound"),
        (("scope", "run_id"), True, "unbound"),
        (("scope", "run_id"), 0, "unbound"),
        (("scope", "job_id"), "9", "unbound"),
        (("scope", "job_id"), -1, "unbound"),
        (("merge_admission",), "GO", "admission/authority"),
        (("authority_transfer",), None, "admission/authority"),
        (("security_waiver",), True, "admission/authority"),
        (("roots",), {}, "arrays required"),
        (("metrics",), [], "arrays required"),
        (("unlinked_debug_receipts",), _DROP, "arrays required"),
        (("roots",), [dict(root_id="BD-1"), dict(root_id="BD-1")], "duplicate"),
        (("roots",), ["BD-1"], "duplicate"),
        (("roots",), [dict(root_id="XX-1")], "unsupported"),
        (("roots",), [dict(root_id=3)], "unsupported"),
        (("metrics", "full_bandit_unique"), -1, "bandit denominator"),
        (("metrics", "full_bandit_unique"), 1.0, "bandit denominator"),
    ],
)
def test_to_event_rejects(path, value, message):
    with pytest.raises(_Invalid, match=message):
        mod.to_event(_mutate(path, value))


def test_to_event_rejects_non_dict():
    with pytest.raises(_Invalid, match="expected"):
        mod.to_event([1])


def test_to_event_does_not_mutate_input():
    doc = _doc()
    snapshot = copy.deepcopy(doc)
    mod.to_event(doc)
    assert doc == snapshot


def _write(path, doc):
    path.write_bytes(json.dumps(doc).encode("utf-8"))
    return path


def test_main_appends_to_default_ledger(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    src = _write(tmp_path / "joined.json", _doc())
    monkeypatch.setattr(sys, "argv", ["prog", "--input", str(src)])
    mod.main()
    out = capsys.readouterr().out
    assert "Appended observation-only BD/LDAB join receipt BDLDAB-" in out
    line = (tmp_path / "data" / "ledger.jsonl").read_text(encoding="utf-8")
    assert json.loads(line)["kind"] == "note"


def test_main_invalid_input_raises(tmp_path, monkeypatch):
    src = _write(tmp_path / "bad.json", dict(schema="nope"))
    ledger = tmp_path / "l.jsonl"
    argv = ["prog", "--input", str(src), "--ledger", str(ledger)]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(_Invalid):
        mod.main()
    assert not ledger.exists()


def test_run_as_script(tmp_path, capsys, monkeypatch):
    src = _write(tmp_path / "joined.json", _doc())
    ledger = tmp_path / "led" / "ger.jsonl"
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setitem(sys.modules, "everred", _make_stub())
    argv = [str(SCRIPT), "--input", str(src), "--ledger", str(ledger)]
    monkeypatch.setattr(sys, "argv", argv)
    runpy.run_path(str(SCRIPT), run_name="__main__")
    assert "BDLDAB-" in capsys.readouterr().out
    assert ledger.is_file()
