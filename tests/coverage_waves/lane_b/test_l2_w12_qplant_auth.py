"""Lane-B wave 12: qplant API key manager and its CLI (storage under tmp_path)."""

import json
import sys
import types
from datetime import datetime, timedelta

import pytest

from ._l2_loader import load

akm = load("qplant/authentication/api_key_manager.py")
_saved_path = list(sys.path)
try:
    cli = load("qplant/authentication/key_cli.py", deps={"api_key_manager": akm})
finally:
    sys.path[:] = _saved_path

FAKE_PREFIX = "qplant" + "_"


@pytest.fixture(autouse=True)
def _fast_hash(monkeypatch):
    monkeypatch.setattr(akm, "_PBKDF2_ITERATIONS", 1000)


@pytest.fixture
def mgr(tmp_path):
    return akm.APIKeyManager(str(tmp_path / "db" / "keys.json"))


def _db(manager):
    return json.loads(manager.keys_db.read_text(encoding="utf-8"))


def _write_db(manager, db):
    manager.keys_db.write_text(json.dumps(db), encoding="utf-8")


# --------------------------------------------------------------------------
# APIKeyManager
# --------------------------------------------------------------------------


def test_default_db_path_under_home(monkeypatch, tmp_path):
    monkeypatch.setattr(akm.Path, "home", lambda: tmp_path)
    expected = tmp_path / ".qplant" / "authentication" / "api_keys.json"
    assert akm.default_keys_db_path() == str(expected)
    manager = akm.APIKeyManager()
    assert manager.keys_db == expected
    assert json.loads(expected.read_text(encoding="utf-8")) == {}


def test_ensure_db_keeps_existing(tmp_path):
    path = tmp_path / "keys.json"
    path.write_text('{"k": {"name": "x"}}', encoding="utf-8")
    manager = akm.APIKeyManager(str(path))
    assert manager.list_keys() == {"k": {"name": "x"}}


def test_generate_and_validate_round_trip(mgr):
    key_id, api_key = mgr.generate_key("svc", expiry_days=10, rate_limit=7)
    assert api_key.startswith(FAKE_PREFIX)
    assert key_id.startswith("key_")
    stored = _db(mgr)[key_id]
    assert api_key not in json.dumps(stored)
    assert stored["key_prefix"] == api_key[:15]
    assert stored["status"] == "active"
    assert stored["usage_count"] == 0

    result = mgr.validate_key(api_key)
    assert result == {"valid": True, "key_id": key_id, "name": "svc", "rate_limit": 7}
    stored = _db(mgr)[key_id]
    assert stored["usage_count"] == 1
    assert stored["last_used"] is not None


@pytest.mark.parametrize("candidate", ["", None, "bogus", "QPLANT_x"])
def test_validate_rejects_bad_format(mgr, candidate):
    assert mgr.validate_key(candidate) == {"valid": False, "reason": "invalid_format"}


def test_validate_skips_mismatched_and_legacy_entries(mgr):
    key_id, api_key = mgr.generate_key("real")
    db = _db(mgr)
    db["legacy"] = {"key_prefix": api_key[:15], "key_hash": "00"}
    db["other"] = {"key_prefix": "different", "key_salt": "00", "key_hash": "00"}
    db["collision"] = {
        "key_prefix": api_key[:15],
        "key_salt": "ab" * 32,
        "key_hash": "00",
    }
    # place decoys before the real entry so every skip branch runs
    _write_db(mgr, {k: db[k] for k in ["legacy", "other", "collision", key_id]})
    assert mgr.validate_key(api_key)["key_id"] == key_id
    unknown = FAKE_PREFIX + "z" * 40
    assert mgr.validate_key(unknown) == {"valid": False, "reason": "invalid_key"}


def test_validate_expired_and_revoked(mgr):
    key_id, api_key = mgr.generate_key("exp")
    db = _db(mgr)
    db[key_id]["expires_at"] = (datetime.now() - timedelta(days=1)).isoformat()
    _write_db(mgr, db)
    assert mgr.validate_key(api_key) == {"valid": False, "reason": "expired"}

    key2, api_key2 = mgr.generate_key("rev")
    assert mgr.revoke_key(key2) is True
    assert _db(mgr)[key2]["status"] == "revoked"
    assert "revoked_at" in _db(mgr)[key2]
    assert mgr.validate_key(api_key2) == {"valid": False, "reason": "revoked"}


def test_revoke_and_rotate_unknown(mgr):
    assert mgr.revoke_key("key_missing") is False
    assert mgr.rotate_key("key_missing") is None
    assert mgr.get_key_info("key_missing") is None


def test_rotate_replaces_key(mgr):
    old_id, old_key = mgr.generate_key("svc", rate_limit=42)
    new_id, new_key = mgr.rotate_key(old_id)
    assert new_id != old_id
    assert mgr.validate_key(old_key)["reason"] == "revoked"
    assert mgr.validate_key(new_key)["rate_limit"] == 42
    assert mgr.get_key_info(new_id)["name"] == "svc"


def test_listings_exclude_internal_fields(mgr):
    key_id, _ = mgr.generate_key("svc")
    listed = mgr.list_keys()[key_id]
    info = mgr.get_key_info(key_id)
    for fields in (listed, info):
        assert not set(fields) & {"key_hash", "key_salt", "key_prefix"}
        assert fields["name"] == "svc"


def test_load_db_tolerates_corrupt_or_missing(mgr):
    mgr.keys_db.write_text("{not json", encoding="utf-8")
    assert mgr.list_keys() == {}
    mgr.keys_db.unlink()
    assert mgr.list_keys() == {}


# --------------------------------------------------------------------------
# key_cli
# --------------------------------------------------------------------------


def _run_cli(monkeypatch, db, *args):
    monkeypatch.setattr(sys, "argv", ["key_cli", "--db", str(db), *args])
    cli.main()


def test_cli_no_command_prints_help(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, "argv", ["key_cli"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 1
    assert "QPLANT API Key Management CLI" in capsys.readouterr().out


def test_cli_full_lifecycle(monkeypatch, capsys, tmp_path):
    db = tmp_path / "keys.json"
    _run_cli(monkeypatch, db, "list")
    assert "No API keys found." in capsys.readouterr().out

    env_file = tmp_path / "out.env"
    _run_cli(
        monkeypatch,
        db,
        "generate",
        "--name",
        "Prod",
        "--days",
        "5",
        "--rate-limit",
        "9",
        "--output",
        str(env_file),
    )
    out = capsys.readouterr().out
    assert "Rate:     9 req/hour" in out
    assert "Written to" in out
    lines = env_file.read_text(encoding="utf-8").splitlines()
    api_key = lines[0].split("=", 1)[1]
    key_id = lines[1].split("=", 1)[1]
    assert api_key.startswith(FAKE_PREFIX)

    _run_cli(monkeypatch, db, "validate", "--key", api_key)
    out = capsys.readouterr().out
    assert "Valid API key" in out
    assert key_id in out

    _run_cli(monkeypatch, db, "list")
    out = capsys.readouterr().out
    assert key_id in out
    assert "Prod" in out

    _run_cli(monkeypatch, db, "info", "--key-id", key_id)
    info = json.loads(capsys.readouterr().out)
    assert info["usage_count"] == 1

    _run_cli(monkeypatch, db, "rotate", "--key-id", key_id)
    out = capsys.readouterr().out
    assert "Key rotated" in out
    assert key_id + " (revoked)" in out

    new_id = [k for k in json.loads(db.read_text(encoding="utf-8")) if k != key_id][0]
    _run_cli(monkeypatch, db, "revoke", "--key-id", new_id)
    assert "Revoked key: " + new_id in capsys.readouterr().out


def test_cli_generate_without_output(monkeypatch, capsys, tmp_path):
    _run_cli(monkeypatch, tmp_path / "k.json", "generate", "--name", "Dev")
    out = capsys.readouterr().out
    assert "Rate:     1000 req/hour" in out
    assert "Written to" not in out


@pytest.mark.parametrize(
    "args,message",
    [
        (["validate", "--key", "bogus"], "Invalid: invalid_format"),
        (["revoke", "--key-id", "key_x"], "Key not found: key_x"),
        (["rotate", "--key-id", "key_x"], "Key not found: key_x"),
        (["info", "--key-id", "key_x"], "Key not found: key_x"),
    ],
)
def test_cli_failures_exit_1(monkeypatch, capsys, tmp_path, args, message):
    with pytest.raises(SystemExit) as exc:
        _run_cli(monkeypatch, tmp_path / "k.json", *args)
    assert exc.value.code == 1
    assert message in capsys.readouterr().out


def test_cli_list_without_expiry(capsys):
    fake = types.SimpleNamespace(
        list_keys=lambda: {"key_1": {"name": "n", "status": "active", "usage_count": 3}}
    )
    cli.cmd_list(types.SimpleNamespace(), fake)
    out = capsys.readouterr().out
    assert "key_1" in out
    assert out.rstrip().endswith("N/A")
