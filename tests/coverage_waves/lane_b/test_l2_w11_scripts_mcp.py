"""Lane-B wave 11: MCP operational scripts (capacity fit, health handler)."""

import io
import json
import sys

import pytest

from ._l2_loader import load

# ---------------------------------------------------------------------------
# mcp_capacity_fit: a stdin -> stdout script that runs at import time
# ---------------------------------------------------------------------------


def _fit(monkeypatch, capsys, rows, blank=True):
    lines = [json.dumps(r) for r in rows]
    text = ("\n   \n" if blank else "\n").join(lines) + "\n"
    monkeypatch.setattr(sys, "stdin", io.StringIO(text))
    load("scripts/mcp_capacity_fit.py", name="l2_w11_mcp_capacity_fit")
    return json.loads(capsys.readouterr().out)


def _obs(queued, completed=0, workers=2, **extra):
    row = {"queued": queued, "completed": completed, "workers": workers}
    row.update(extra)
    return row


@pytest.mark.parametrize(
    "rows",
    [[], [_obs(5)]],
)
def test_capacity_fit_needs_two_observations(monkeypatch, capsys, rows):
    with pytest.raises(SystemExit, match="need >=2 observations"):
        _fit(monkeypatch, capsys, rows)


@pytest.mark.parametrize(
    "completed, expected",
    [(60, 2), (4, 4), (1, 8)],
)
def test_capacity_fit_recommendation_with_timestamps(
    monkeypatch, capsys, completed, expected
):
    rows = [_obs(100, 0, t=0), _obs(70, 0, t=60), _obs(40, completed, t=120)]
    out = _fit(monkeypatch, capsys, rows)
    assert out["queue_delta"] == -60.0
    assert out["net_drain_per_min"] == 30.0
    assert out["jobs_per_worker_min"] == round(completed / 4.0, 4)
    assert out["recommended_workers"] == expected
    assert out["candidates"] == [2, 4, 8]


def test_capacity_fit_short_window_uses_elapsed_s(monkeypatch, capsys):
    rows = [_obs(10, 0), _obs(9, 3, elapsed_s=0.5)]
    out = _fit(monkeypatch, capsys, rows, blank=False)
    # elapsed collapses to 0.5 s -> 1 job drained in 1/120 min.
    assert out["net_drain_per_min"] == 120.0
    assert out["jobs_per_worker_min"] == 180.0
    assert out["recommended_workers"] == 2


def test_capacity_fit_short_window_without_elapsed_s(monkeypatch, capsys):
    rows = [_obs(10, 0, workers=0), _obs(8, 3, workers=0)]
    out = _fit(monkeypatch, capsys, rows)
    assert out["net_drain_per_min"] == 120.0
    assert out["jobs_per_worker_min"] == 0.0
    assert out["recommended_workers"] == 2


def test_capacity_fit_growing_queue_starts_at_two(monkeypatch, capsys):
    rows = [_obs(10, 0, elapsed_s=0), _obs(50, 100, elapsed_s=120)]
    out = _fit(monkeypatch, capsys, rows)
    assert out["queue_delta"] == 40.0
    assert out["net_drain_per_min"] == -20.0
    assert out["recommended_workers"] == 2


# ---------------------------------------------------------------------------
# mcp_health_server: state() and the request handler, never a real socket
# ---------------------------------------------------------------------------


def _health(monkeypatch, **env):
    for key in (
        "MCP_HEALTH_PORT",
        "MCP_HEALTH_HOST",
        "MCP_WORKER_ID",
        "MCP_STATE_FILE",
        "MCP_DEBUG",
    ):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return load("scripts/mcp_health_server.py", name="l2_w11_mcp_health_server")


def test_health_defaults(monkeypatch):
    mod = _health(monkeypatch)
    assert (mod.PORT, mod.HOST, mod.WORKER, mod.STATE) == (
        8766,
        "127.0.0.1",
        "abacus-mcp",
        "",
    )
    monkeypatch.setattr(mod, "START", 100.0)
    monkeypatch.setattr(mod.time, "time", lambda: 112.34)
    assert mod.state() == {
        "worker_id": "abacus-mcp",
        "uptime_s": 12.3,
        "ready": True,
        "port": 8766,
    }


def test_health_state_merges_file(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"ready": False, "queue": 3}), encoding="utf-8")
    mod = _health(
        monkeypatch,
        MCP_HEALTH_PORT="9001",
        MCP_WORKER_ID="w-7",
        MCP_STATE_FILE=str(state_file),
    )
    out = mod.state()
    assert out["ready"] is False and out["queue"] == 3
    assert out["worker_id"] == "w-7" and out["port"] == 9001


def test_health_state_missing_file_is_ignored(tmp_path, monkeypatch):
    mod = _health(monkeypatch, MCP_STATE_FILE=str(tmp_path / "absent.json"))
    out = mod.state()
    assert "state_error" not in out and out["ready"] is True


def test_health_state_reports_parse_error(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    state_file.write_text("{not json", encoding="utf-8")
    mod = _health(monkeypatch, MCP_STATE_FILE=str(state_file))
    assert mod.state()["state_error"] == "JSONDecodeError"


def _get(mod, path):
    """Drive H.do_GET on an in-memory handler without opening a socket."""
    handler = mod.H.__new__(mod.H)
    handler.path = path
    handler.command = "GET"
    handler.request_version = "HTTP/1.1"
    handler.requestline = "GET " + path + " HTTP/1.1"
    handler.client_address = ("127.0.0.1", 0)
    handler.wfile = io.BytesIO()
    handler.do_GET()
    raw = handler.wfile.getvalue()
    head, _, body = raw.partition(b"\r\n\r\n")
    lines = head.decode("latin-1").split("\r\n")
    status = int(lines[0].split(" ")[1])
    headers = dict(line.split(": ", 1) for line in lines[1:])
    return status, headers, json.loads(body)


@pytest.mark.parametrize("path", ["/health", "/ready", "/metrics"])
def test_handler_health_paths(monkeypatch, path):
    mod = _health(monkeypatch, MCP_WORKER_ID="w-1")
    status, headers, body = _get(mod, path)
    assert status == 200
    assert headers["Content-Type"] == "application/json"
    assert int(headers["Content-Length"]) == len(json.dumps(body, sort_keys=True))
    assert body["worker_id"] == "w-1" and body["ready"] is True


@pytest.mark.parametrize(
    "debug, path, expected",
    [
        ("1", "/debug/state", 200),
        ("0", "/debug/state", 404),
        (None, "/debug/state", 404),
        ("1", "/other", 404),
    ],
)
def test_handler_debug_and_not_found(monkeypatch, debug, path, expected):
    mod = _health(monkeypatch)
    if debug is not None:
        monkeypatch.setenv("MCP_DEBUG", debug)
    status, _, body = _get(mod, path)
    assert status == expected
    if expected == 404:
        assert body == {"error": "not_found"}
    else:
        assert body["worker_id"] == "abacus-mcp"


def test_handler_log_message_is_silent(monkeypatch):
    mod = _health(monkeypatch)
    handler = mod.H.__new__(mod.H)
    assert handler.log_message("%s", "x") is None
