"""Lane-B wave 13: Gloob dispatch responder and W286 pandoc P1 receiver check.

HTTP is faked on the loaded module (``urlopen``); ROOT/CAPS are redirected to
tmp_path so no ack, return or ledger file is written into the repository.
"""

import io
import json
import sys
import types
from pathlib import Path

import pytest

from ._l2_loader import load

REPO = "GBOGEB/ABACUS"
SHA = "c" * 40
URL = "https://example.invalid/dispatch.json"

gd = load("tools/gloob_dispatch_responder.py")


# --------------------------------------------------------------------------
# validate_w286_gloob_pandoc_p1.py (module-level assertions)
# --------------------------------------------------------------------------

W286_REL = "architecture/w286/W286_GLOOB_PANDOC_P1_RECEIVER_HOLD_v0.1.json"


def _w286_record():
    return {
        "repo": REPO,
        "authority_role": "DOW_DERIVED_ANALYSIS_CONSUMPTION",
        "producer": {
            "merge_sha": "3ce6078a12b2fd139f7a674db5d5cf99df6e90da",
            "proof_head_sha": "446d1b4520fe991bd18482bcc21939a8c5538170",
            "proof_run_id": 35372225076,
            "status": "PROVEN_MERGED",
        },
        "authority_transfer": False,
        "must_not": ["promote_QPS_engineering_truth"],
        "formal_credit_delta": 0,
    }


def _run_w286(tmp_path, record):
    target = tmp_path / W286_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record), encoding="utf-8")
    fake = types.SimpleNamespace(Path=lambda _f: tmp_path / "tools" / "v.py")
    return load("tools/validate_w286_gloob_pandoc_p1.py", deps={"pathlib": fake})


def test_w286_real_record_passes(capsys):
    mod = load("tools/validate_w286_gloob_pandoc_p1.py")
    assert capsys.readouterr().out.strip() == "PASS W286 ABACUS independent P1 parity"
    assert isinstance(mod.D, dict) and isinstance(mod.D["producer"], dict)
    assert mod.P.name == Path(W286_REL).name


def test_w286_synthetic_record_passes(tmp_path, capsys):
    mod = _run_w286(tmp_path, _w286_record())
    assert mod.P == tmp_path / W286_REL
    assert "PASS W286" in capsys.readouterr().out


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(repo="other/repo"),
        lambda d: d.update(authority_transfer=True),
        lambda d: d["producer"].update(status="PENDING"),
        lambda d: d["producer"].update(proof_run_id=1),
        lambda d: d.update(must_not=[]),
        lambda d: d.update(formal_credit_delta=1),
    ],
)
def test_w286_rejects_drifted_record(tmp_path, capsys, mutate):
    record = _w286_record()
    mutate(record)
    with pytest.raises(AssertionError):
        _run_w286(tmp_path, record)
    assert "PASS" not in capsys.readouterr().out


# --------------------------------------------------------------------------
# gloob_dispatch_responder.py
# --------------------------------------------------------------------------


def _envelope(**over):
    env = {
        "schema": "gloob-dispatch-envelope/0.1",
        "dispatch_id": "D-1",
        "route_id": "R-1",
        "assignment_digest": "A-1",
        "target_repo": REPO,
        "crew": "FEDERATION_AMBASSADOR",
        "transport": {"mode": "IMMUTABLE_GLOOB_POINTER"},
    }
    env.update(over)
    env["envelope_digest"] = gd.digest(env)
    return env


def _ticket(env, **over):
    keys = ("dispatch_id", "route_id", "assignment_digest", "target_repo", "crew")
    ticket = {"schema": "gloob-dispatch-ticket/0.1", "dispatch_url": URL}
    ticket.update({"expected_" + k: env[k] for k in keys})
    ticket["expected_envelope_digest"] = env["envelope_digest"]
    ticket.update(over)
    return ticket


CAPS = {
    "capabilities": {
        "FEDERATION_AMBASSADOR": {"eligible": True, "authority": "DOW_POINTER_ONLY"},
        "LURKER": {"eligible": False, "authority": "FULL"},
    }
}


def test_digest_is_canonical_and_unicode_safe():
    assert gd.digest({"b": 1, "a": "\u00e9"}) == gd.digest({"a": "\u00e9", "b": 1})
    assert gd.digest({"a": 1}) != gd.digest({"a": 2})
    assert len(gd.digest({})) == 64


def test_load_and_dump_round_trip(tmp_path):
    target = tmp_path / "a" / "b" / "v.json"
    gd.dump(target, {"z": 1, "a": [1, 2]})
    text = target.read_text(encoding="utf-8")
    assert text.endswith("\n") and text.index('"a"') < text.index('"z"')
    assert gd.load(target) == {"z": 1, "a": [1, 2]}


def test_fetch_json_uses_urlopen(monkeypatch):
    seen = {}

    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(url, timeout):
        seen["args"] = (url, timeout)
        return Resp(json.dumps({"ok": "\u2713"}).encode("utf-8"))

    monkeypatch.setattr(gd.urllib.request, "urlopen", fake_urlopen)
    assert gd.fetch_json(URL) == {"ok": "\u2713"}
    assert seen["args"] == (URL, 30)


def test_validate_accepts_matching_dispatch():
    env = _envelope()
    assert gd.validate(_ticket(env), env, CAPS, REPO) == []


def test_validate_reports_every_mismatch():
    env = _envelope(crew="LURKER", target_repo="x/y")
    env["schema"] = "bad"
    ticket = _ticket(
        env,
        schema="bad",
        expected_route_id="R-other",
        expected_envelope_digest="nope",
    )
    errors = gd.validate(ticket, env, CAPS, REPO)
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
    env = _envelope(crew="GHOST")
    env.pop("envelope_digest")
    errors = gd.validate(_ticket(dict(env, envelope_digest="x")), env, {}, REPO)
    assert "ENVELOPE_DIGEST_MISMATCH" in errors
    assert "CREW_NOT_ELIGIBLE" in errors
    assert "AUTHORITY_BOUNDARY_MISMATCH" in errors


@pytest.fixture
def responder(tmp_path, monkeypatch):
    caps = tmp_path / "gloob_dispatch" / "capabilities.json"
    caps.parent.mkdir(parents=True)
    caps.write_text(json.dumps(CAPS), encoding="utf-8")
    monkeypatch.setattr(gd, "ROOT", tmp_path)
    monkeypatch.setattr(gd, "CAPS", caps)
    state = {"envelope": _envelope(), "urls": []}

    def fake_fetch(url):
        state["urls"].append(url)
        return state["envelope"]

    monkeypatch.setattr(gd, "fetch_json", fake_fetch)
    return state


def _write_ticket(tmp_path, ticket):
    path = tmp_path / "ticket.json"
    path.write_text(json.dumps(ticket), encoding="utf-8")
    return path


def test_process_emits_ack_return_and_ledger(tmp_path, responder, capsys):
    env = responder["envelope"]
    ticket = _write_ticket(tmp_path, _ticket(env))
    gd.process(ticket, SHA, 77, REPO)
    assert responder["urls"] == [URL]
    outbox = tmp_path / "gloob_dispatch" / "outbox" / "D-1"
    ack = json.loads((outbox / "delivery-ack.json").read_text(encoding="utf-8"))
    assert ack["state"] == "ACCEPTED" and ack["run_id"] == "77"
    assert ack["source_commit"] == SHA and ack["control_credit"] is False
    ret = json.loads((outbox / "gloob-causal-return.json").read_text("utf-8"))
    assert ret["outcome"] == "RESOLVED"
    assert ret["dispatch"]["envelope_digest"] == env["envelope_digest"]
    ledger_path = tmp_path / "gloob_dispatch" / "accepted" / "D-1.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert ledger["state"] == "RETURN_EMITTED"
    assert ledger["authority"] == "DOW_POINTER_ONLY"
    printed = json.loads(capsys.readouterr().out)
    assert printed == {
        "dispatch_id": "D-1",
        "route_id": "R-1",
        "state": "RETURN_EMITTED",
        "source_commit": SHA,
        "run_id": "77",
    }
    with pytest.raises(SystemExit, match="REPLAY_REJECTED"):
        gd.process(ticket, SHA, 78, REPO)


def test_process_rejects_invalid_dispatch(tmp_path, responder):
    env = responder["envelope"]
    ticket = _write_ticket(tmp_path, _ticket(env, schema="bad"))
    with pytest.raises(SystemExit) as exc:
        gd.process(ticket, SHA, 1, REPO)
    assert str(exc.value) == "DISPATCH_REJECTED: TICKET_SCHEMA_MISMATCH"
    assert not (tmp_path / "gloob_dispatch" / "outbox").exists()


@pytest.mark.parametrize("bad_sha", ["", "C" * 40, "g" * 40, "a" * 39])
def test_process_rejects_invalid_source_sha(tmp_path, responder, bad_sha):
    ticket = _write_ticket(tmp_path, _ticket(responder["envelope"]))
    with pytest.raises(SystemExit, match="INVALID_SOURCE_SHA"):
        gd.process(ticket, bad_sha, 1, REPO)
    assert not (tmp_path / "gloob_dispatch" / "accepted").exists()


def test_process_falls_back_to_ticket_dispatch_id(tmp_path, responder):
    env = responder["envelope"]
    ticket = _write_ticket(tmp_path, _ticket(env))
    responder["envelope"] = {k: v for k, v in env.items() if k != "dispatch_id"}
    with pytest.raises(SystemExit, match="DISPATCH_REJECTED"):
        gd.process(ticket, SHA, 1, REPO)
    accepted = tmp_path / "gloob_dispatch" / "accepted" / "D-1.json"
    accepted.parent.mkdir(parents=True)
    accepted.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit, match="REPLAY_REJECTED"):
        gd.process(ticket, SHA, 1, REPO)


def test_self_test_against_real_capabilities(capsys):
    assert gd.self_test() is None
    assert "self-test PASS" in capsys.readouterr().out


def test_main_self_test_flag(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["prog", "--self-test"])
    gd.main()
    assert "self-test PASS" in capsys.readouterr().out


def test_main_requires_ticket(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog"])
    with pytest.raises(SystemExit, match="ticket required"):
        gd.main()


def test_main_passes_github_env(monkeypatch):
    seen = []
    monkeypatch.setattr(gd, "process", lambda *a: seen.append(a))
    monkeypatch.setattr(sys, "argv", ["prog", "t.json"])
    monkeypatch.setenv("GITHUB_SHA", SHA)
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    monkeypatch.setenv("GITHUB_REPOSITORY", REPO)
    gd.main()
    assert seen == [("t.json", SHA, "42", REPO)]


def test_main_defaults_missing_env_to_empty(monkeypatch):
    seen = []
    monkeypatch.setattr(gd, "process", lambda *a: seen.append(a))
    monkeypatch.setattr(sys, "argv", ["prog", "t.json"])
    for key in ("GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_REPOSITORY"):
        monkeypatch.delenv(key, raising=False)
    gd.main()
    assert seen == [("t.json", "", "", "")]
