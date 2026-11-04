"""Behaviour tests for tools/gloob_dispatch_responder.py."""

import io
import json
import runpy

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

mod = load("tools/gloob_dispatch_responder.py", name="abn_w3_gloob_dispatch_responder")

REPO = "GBOGEB/ABACUS"
SHA = "0123456789abcdef0123456789abcdef01234567"
CAPS = {
    "capabilities": {
        "FEDERATION_AMBASSADOR": {"eligible": True, "authority": "DOW_POINTER_ONLY"},
        "IDLE": {"eligible": False, "authority": "OTHER"},
    }
}
KEYS = ("dispatch_id", "route_id", "assignment_digest", "target_repo", "crew")


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def _pair(crew="FEDERATION_AMBASSADOR", dispatch_id="D1"):
    env = {
        "schema": "gloob-dispatch-envelope/0.1",
        "dispatch_id": dispatch_id,
        "route_id": "R1",
        "assignment_digest": "A1",
        "target_repo": REPO,
        "crew": crew,
    }
    env["envelope_digest"] = mod.digest(env)
    ticket = {"schema": "gloob-dispatch-ticket/0.1"}
    for key in KEYS:
        ticket["expected_" + key] = env[key]
    ticket["expected_envelope_digest"] = env["envelope_digest"]
    ticket["dispatch_url"] = "https://example.invalid/env.json"
    return ticket, env


def _setup(monkeypatch, tmp_path, env, ticket):
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    caps_path = tmp_path / "caps.json"
    caps_path.write_bytes(json.dumps(CAPS).encode("utf-8"))
    monkeypatch.setattr(mod, "CAPS", caps_path)
    monkeypatch.setattr(mod, "fetch_json", lambda url: dict(env))
    ticket_path = tmp_path / "ticket.json"
    ticket_path.write_bytes(json.dumps(ticket).encode("utf-8"))
    return ticket_path


def test_load_and_dump_roundtrip(tmp_path):
    target = tmp_path / "a" / "b" / "x.json"
    mod.dump(target, {"b": 1, "a": [1, 2]})
    assert target.read_text(encoding="utf-8").startswith('{\n  "a"')
    assert mod.load(target) == {"a": [1, 2], "b": 1}


def test_digest_is_key_order_independent():
    assert mod.digest({"a": 1, "b": "é"}) == mod.digest({"b": "é", "a": 1})
    assert mod.digest({"a": 1}) != mod.digest({"a": 2})
    assert len(mod.digest({})) == 64


def test_fetch_json_uses_urlopen(monkeypatch):
    seen = {}

    def fake_urlopen(url, timeout):
        seen["args"] = (url, timeout)
        return _Resp(b'{"k": "v"}')

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    assert mod.fetch_json("https://example.invalid/e") == {"k": "v"}
    assert seen["args"] == ("https://example.invalid/e", 30)


def test_validate_accepts_matching_pair():
    ticket, env = _pair()
    assert mod.validate(ticket, env, CAPS, REPO) == []


def test_validate_reports_every_mismatch():
    ticket, env = _pair(crew="IDLE")
    ticket["schema"] = "bad"
    ticket["expected_route_id"] = "OTHER"
    ticket["expected_envelope_digest"] = "nope"
    env["schema"] = "bad"
    errors = mod.validate(ticket, env, CAPS, "other/repo")
    assert errors == [
        "TICKET_SCHEMA_MISMATCH",
        "ENVELOPE_SCHEMA_MISMATCH",
        "ENVELOPE_DIGEST_MISMATCH",
        "EXPECTED_ROUTE_ID_MISMATCH",
        "EXPECTED_ENVELOPE_DIGEST_MISMATCH",
        "TARGET_REPO_MISMATCH",
        "CREW_NOT_ELIGIBLE",
        "AUTHORITY_BOUNDARY_MISMATCH",
    ]


def test_validate_missing_digest_and_unknown_crew():
    ticket, env = _pair(crew="GHOST")
    env.pop("envelope_digest")
    errors = mod.validate(ticket, env, {}, REPO)
    assert "ENVELOPE_DIGEST_MISMATCH" in errors
    assert "EXPECTED_ENVELOPE_DIGEST_MISMATCH" in errors
    assert "CREW_NOT_ELIGIBLE" in errors
    assert "AUTHORITY_BOUNDARY_MISMATCH" in errors


def test_process_emits_ack_return_and_ledger(monkeypatch, tmp_path, capsys):
    ticket, env = _pair()
    ticket_path = _setup(monkeypatch, tmp_path, env, ticket)
    mod.process(ticket_path, SHA, 42, REPO)
    out = json.loads(capsys.readouterr().out)
    assert out == {
        "dispatch_id": "D1",
        "route_id": "R1",
        "run_id": "42",
        "source_commit": SHA,
        "state": "RETURN_EMITTED",
    }
    base = tmp_path / "gloob_dispatch"
    ack = mod.load(base / "outbox" / "D1" / "delivery-ack.json")
    assert ack["state"] == "ACCEPTED"
    assert ack["receiver_disposition"] == "ACCEPT_POINTER_ONLY"
    assert ack["control_credit"] is False
    ret = mod.load(base / "outbox" / "D1" / "gloob-causal-return.json")
    assert ret["outcome"] == "RESOLVED"
    assert ret["dispatch"]["envelope_digest"] == env["envelope_digest"]
    assert ret["evidence"]["run_id"] == "42"
    ledger = mod.load(base / "accepted" / "D1.json")
    assert ledger["authority"] == "DOW_POINTER_ONLY"
    assert ledger["source_commit"] == SHA
    # a second delivery of the same dispatch is a replay
    with pytest.raises(SystemExit, match="REPLAY_REJECTED"):
        mod.process(ticket_path, SHA, 43, REPO)


def test_process_rejects_invalid_dispatch(monkeypatch, tmp_path):
    ticket, env = _pair()
    ticket_path = _setup(monkeypatch, tmp_path, env, ticket)
    with pytest.raises(SystemExit, match="DISPATCH_REJECTED: TARGET_REPO_MISMATCH"):
        mod.process(ticket_path, SHA, 1, "other/repo")
    assert not (tmp_path / "gloob_dispatch").exists()


def test_process_rejects_bad_source_sha(monkeypatch, tmp_path):
    ticket, env = _pair()
    ticket_path = _setup(monkeypatch, tmp_path, env, ticket)
    for bad in ("abc", SHA.upper(), ""):
        with pytest.raises(SystemExit, match="INVALID_SOURCE_SHA"):
            mod.process(ticket_path, bad, 1, REPO)


def test_process_falls_back_to_ticket_dispatch_id(monkeypatch, tmp_path):
    ticket, env = _pair()
    env.pop("dispatch_id")
    ticket_path = _setup(monkeypatch, tmp_path, env, ticket)
    # replay check uses the ticket's expected id before validation
    accepted = tmp_path / "gloob_dispatch" / "accepted"
    accepted.mkdir(parents=True)
    (accepted / "D1.json").write_bytes(b"{}")
    with pytest.raises(SystemExit, match="REPLAY_REJECTED"):
        mod.process(ticket_path, SHA, 1, REPO)


def test_self_test_passes_with_repo_capabilities(capsys):
    assert mod.self_test() is None
    assert "self-test PASS" in capsys.readouterr().out


def test_main_self_test(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["gdr", "--self-test"])
    assert mod.main() is None
    assert "self-test PASS" in capsys.readouterr().out


def test_main_requires_ticket(monkeypatch):
    monkeypatch.setattr("sys.argv", ["gdr"])
    with pytest.raises(SystemExit, match="ticket required"):
        mod.main()


def test_main_passes_environment(monkeypatch):
    seen = {}
    monkeypatch.setattr(mod, "process", lambda *a: seen.setdefault("a", a))
    monkeypatch.setattr("sys.argv", ["gdr", "t.json"])
    monkeypatch.setenv("GITHUB_SHA", SHA)
    monkeypatch.setenv("GITHUB_RUN_ID", "9")
    monkeypatch.setenv("GITHUB_REPOSITORY", REPO)
    mod.main()
    assert seen["a"] == ("t.json", SHA, "9", REPO)
    for name in ("GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_REPOSITORY"):
        monkeypatch.delenv(name)
    seen.clear()
    mod.main()
    assert seen["a"] == ("t.json", "", "", "")


def test_script_entrypoint_self_test(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["gdr", "--self-test"])
    runpy.run_path(
        str(REPO_ROOT / "tools" / "gloob_dispatch_responder.py"),
        run_name="__main__",
    )
    assert "self-test PASS" in capsys.readouterr().out
