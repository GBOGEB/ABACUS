"""Behaviour tests for handover/cbd_20261016/binder.py (network fully stubbed)."""

import copy
import io
import json
import sys

import pytest

from tests.coverage_waves.lane_a._load import load

bd = load("handover/cbd_20261016/binder.py")

SHA1 = "1" * 40
SHA2 = "2" * 40


def make_binder():
    repos = [
        {"repo": "GBOGEB/R" + str(i), "branch": "main", "sha": SHA1, "protected": True}
        for i in range(5)
    ]
    return {
        "schema": bd.SCHEMA,
        "control": dict(bd.CONTROL),
        "observed_date": "2026-10-16",
        "repositories": repos,
        "prs": [
            {"repo": "GBOGEB/ABACUS", "number": 7, "sha": SHA2, "action": "reread"}
        ],
        "receipts": [
            {"repo": "GBOGEB/ABACUS", "run_id": 5, "head_sha": SHA1},
            {"repo": "GBOGEB/ABACUS", "run_id": 6, "head_sha": None},
        ],
        "metrics": {"matched_security_delta": None, "REX_formal_root_closures": None},
        "roots": [{"id": "ROOT1", "canonical_owner": "#1", "status": "HOLD"}],
        "references": {"owner": "https://example.invalid/x"},
    }


def write(tmp_path, obj, name="BINDER.json"):
    path = tmp_path / name
    path.write_bytes(json.dumps(obj).encode("utf-8"))
    return path


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(bd.request, "urlopen", refuse)


def test_load_accepts_valid(tmp_path):
    obj = bd.load(write(tmp_path, make_binder()))
    assert obj["schema"] == bd.SCHEMA
    assert len(obj["repositories"]) == 5


CASES = [
    (lambda b: b.update(schema="x"), "schema/authority tamper"),
    (lambda b: b["control"].update(security_waiver=True), "schema/authority tamper"),
    (lambda b: b["repositories"].pop(), "population mismatch"),
    (lambda b: b["repositories"][0].update(repo="evil/x"), "bad repo or exact SHA"),
    (lambda b: b["repositories"][0].update(sha="abc"), "bad repo or exact SHA"),
    (lambda b: b["prs"][0].update(repo="GBOGEB/a b"), "bad PR repo or head"),
    (lambda b: b["prs"][0].update(sha="Z" * 40), "bad PR repo or head"),
    (lambda b: b["receipts"][0].update(repo="other/x"), "bad run receipt"),
    (lambda b: b["receipts"][0].update(run_id="5"), "bad run receipt"),
    (lambda b: b["receipts"][0].update(head_sha="short"), "bad receipt source"),
    (lambda b: b["metrics"].update(matched_security_delta=1), "scanner credit"),
    (lambda b: b["metrics"].update(REX_formal_root_closures=0), "closure credit"),
]


@pytest.mark.parametrize("mutator,message", CASES)
def test_load_rejections(tmp_path, mutator, message):
    obj = make_binder()
    mutator(obj)
    with pytest.raises(ValueError, match=message):
        bd.load(write(tmp_path, obj))


def test_load_rejects_missing_repositories(tmp_path):
    obj = make_binder()
    del obj["repositories"]
    with pytest.raises(ValueError, match="population mismatch"):
        bd.load(write(tmp_path, obj))


def test_api_get_restricts_path():
    with pytest.raises(ValueError, match="restricted API path"):
        bd.api_get("/repos/other/x", "")


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


@pytest.mark.parametrize("token", ["", "tkn"])
def test_api_get_builds_readonly_request(monkeypatch, token):
    seen = {}

    def fake_urlopen(req, timeout):
        seen["url"] = req.full_url
        seen["headers"] = dict(req.header_items())
        seen["method"] = req.get_method()
        seen["timeout"] = timeout
        return FakeResponse(b'{"ok": true}')

    monkeypatch.setattr(bd.request, "urlopen", fake_urlopen)
    assert bd.api_get("/repos/GBOGEB/ABACUS/pulls/1", token) == {"ok": True}
    assert seen["url"] == "https://api.github.com/repos/GBOGEB/ABACUS/pulls/1"
    assert seen["method"] == "GET"
    assert seen["timeout"] == 15
    assert ("Authorization" in seen["headers"]) is bool(token)
    if token:
        assert seen["headers"]["Authorization"] == "Bearer " + token


def fake_api_factory(calls):
    def fake_api(path, token):
        calls.append((path, token))
        if path.endswith("/branches/main") and "/R0/" in path:
            return {"commit": {"sha": SHA1}}
        if "/R1/" in path:
            return {"commit": {"sha": SHA2}}
        if "/R2/" in path:
            raise bd.error.URLError("offline")
        if "/R3/" in path:
            return {}
        if "/R4/" in path:
            raise TimeoutError()
        return {"head": {"sha": SHA2}, "state": "open", "merged_at": None}

    return fake_api


def test_recensus_classifies_rows(monkeypatch):
    calls = []
    monkeypatch.setattr(bd, "api_get", fake_api_factory(calls))
    out = bd.recensus(make_binder(), "t")
    assert out["schema"] == "code_purple.binder.recensus.v1"
    assert out["authority"] == "READ_ONLY"
    rows = out["rows"]
    assert len(rows) == 6
    assert [r["match"] for r in rows] == [True, False, None, None, None, True]
    assert rows[2]["error_type"] == "URLError"
    assert rows[3]["error_type"] == "KeyError"
    assert rows[4]["error_type"] == "TimeoutError"
    pr = rows[5]
    assert pr["type"] == "pr"
    assert pr["state"] == "open"
    assert pr["merged"] is False
    assert calls[5] == ("/repos/GBOGEB/ABACUS/pulls/7", "t")
    assert out["sha_drift"] == 1
    assert out["unknown"] == 3


def test_markdown_offline_and_live():
    binder = make_binder()
    text = bd.markdown(binder)
    assert text.endswith("\n")
    assert "Historic observation: 2026-10-16" in text
    assert "| GBOGEB/R0 | main | " + SHA1 + " | True |" in text
    assert "| ROOT1 | #1 | HOLD |" in text
    assert "[#7](https://github.com/GBOGEB/ABACUS/pull/7)" in text
    assert "- owner: https://example.invalid/x" in text
    assert "Fresh read-only SHA recensus" not in text
    live = {"rows": [{"source": "GBOGEB/R0", "ref": "main", "match": True}]}
    live["rows"][0]["observed_sha"] = SHA1
    text2 = bd.markdown(binder, live)
    assert "Fresh read-only SHA recensus" in text2
    assert "| GBOGEB/R0:main | True | " + SHA1 + " |" in text2


def run_main(monkeypatch, args):
    monkeypatch.setattr(sys, "argv", ["binder.py", *args])
    return bd.main()


def test_main_offline(tmp_path, monkeypatch, capsys):
    path = write(tmp_path, make_binder())
    out = tmp_path / "out"
    rc = run_main(monkeypatch, ["--binder", str(path), "--out", str(out)])
    assert rc == 0
    assert (out / "BINDER_READBACK.md").exists()
    assert not (out / "LIVE_RECENSUS.json").exists()
    printed = json.loads(capsys.readouterr().out)
    assert printed["sha_drift"] is None
    assert printed["unknown"] is None
    assert len(printed["binder_sha256"]) == 64


def test_main_live_strict_with_drift(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("GH_TOKEN", "envtok")
    calls = []
    monkeypatch.setattr(bd, "api_get", fake_api_factory(calls))
    path = write(tmp_path, make_binder())
    args = ["--binder", str(path), "--out", str(tmp_path), "--live", "--strict"]
    assert run_main(monkeypatch, args) == 2
    assert calls[0][1] == "envtok"
    live = json.loads((tmp_path / "LIVE_RECENSUS.json").read_text())
    assert live["sha_drift"] == 1
    printed = json.loads(capsys.readouterr().out)
    assert printed["unknown"] == 3


def test_main_live_clean_strict_and_nonstrict(tmp_path, monkeypatch):
    def all_match(path, token):
        if "/pulls/" in path:
            return {"head": {"sha": SHA2}, "state": "closed", "merged_at": "x"}
        return {"commit": {"sha": SHA1}}

    monkeypatch.setattr(bd, "api_get", all_match)
    path = write(tmp_path, make_binder())
    base = ["--binder", str(path), "--out", str(tmp_path), "--live"]
    assert run_main(monkeypatch, base + ["--strict"]) == 0
    bad = copy.deepcopy(make_binder())
    bad["repositories"][0]["sha"] = SHA2
    path2 = write(tmp_path, bad, "B2.json")
    args = ["--binder", str(path2), "--out", str(tmp_path), "--live"]
    assert run_main(monkeypatch, args) == 0
