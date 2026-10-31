"""Lane-B wave 15: qplant materials DB, API-key middleware and load-test grader.

``fastapi`` is replaced by a minimal fake injected through the loader so the
middleware logic runs in CI jobs without it. The key database lives under
tmp_path (``QPLANT_API_KEYS_DB``) and every report path is a tmp_path file.
"""

import asyncio
import csv
import json
import sys
import types

import pytest

from ._l2_loader import load

# --------------------------------------------------------------------------
# handover_dashboard/src/materials_db.py
# --------------------------------------------------------------------------

mdb = load("qplant/handover_dashboard/src/materials_db.py")


def test_materials_have_unique_ids_and_property_tables():
    ids = [m["id"] for m in mdb.MATERIALS.values()]
    assert len(ids) == len(set(ids)) and all(i.startswith("MAT-") for i in ids)
    for mat in mdb.MATERIALS.values():
        assert isinstance(mat["name"], str) and mat["name"]
        assert isinstance(mat["properties"], dict) and mat["properties"]


def test_seal_suppliers_match_supplier_comparison():
    seals = {m["supplier"].split()[0] for k, m in mdb.MATERIALS.items() if "SEAL" in k}
    compared = {row["supplier"].split()[0] for row in mdb.SUPPLIER_COMPARISON}
    assert seals <= compared
    for row in mdb.SUPPLIER_COMPARISON:
        assert isinstance(row["cost_eur"], int) and row["cost_relative"] > 0
        assert isinstance(row["advantages"], list) and row["disadvantages"]


def test_codes_standards_and_welding_shape():
    codes = [c["code"] for c in mdb.CODES_STANDARDS]
    assert len(codes) == len(set(codes))
    assert all(set(c) == {"code", "title", "scope"} for c in mdb.CODES_STANDARDS)
    weld = mdb.WELDING_SPECS["orbital_tig"]
    assert weld["id"].startswith("WELD-") and isinstance(weld["standards"], list)


def test_valve_classes_and_reliability_ranges():
    for valve in mdb.VALVE_CLASSES:
        assert valve["class"] == "CV"
        assert valve["max_leak_restriction"] > valve["max_leak_ambient"] > 0
    for row in mdb.RELIABILITY_DATA.values():
        assert row["mtbf_hours"] > row["mttr_hours"] > 0
        assert 0 < row["availability_pct"] <= 100


# --------------------------------------------------------------------------
# authentication/fastapi_middleware.py
# --------------------------------------------------------------------------


class FakeHTTPException(Exception):
    def __init__(self, status_code, detail=None, headers=None):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.headers = headers


def _fake_fastapi():
    fastapi = types.ModuleType("fastapi")
    fastapi.Security = lambda dep: dep
    fastapi.HTTPException = FakeHTTPException
    fastapi.Request = object
    fastapi.status = types.SimpleNamespace(
        HTTP_401_UNAUTHORIZED=401, HTTP_429_TOO_MANY_REQUESTS=429
    )
    security = types.ModuleType("fastapi.security")

    class APIKeyHeader:
        def __init__(self, name, auto_error=True):
            self.name = name
            self.auto_error = auto_error

    security.APIKeyHeader = APIKeyHeader
    fastapi.security = security
    return {"fastapi": fastapi, "fastapi.security": security}


@pytest.fixture
def mw(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setenv("QPLANT_API_KEYS_DB", str(tmp_path / "keys" / "db.json"))
    akm = load("qplant/authentication/api_key_manager.py")
    rl = load("qplant/authentication/rate_limiter.py")
    deps = _fake_fastapi()
    deps.update(api_key_manager=akm, rate_limiter=rl)
    return load("qplant/authentication/fastapi_middleware.py", deps=deps)


def _call(mod, key):
    return asyncio.run(mod.verify_api_key(key))


def test_globals_wire_header_and_tmp_key_db(mw, tmp_path):
    assert mw.api_key_header.name == "X-API-Key"
    assert mw.api_key_header.auto_error is False
    assert mw.key_manager.keys_db == tmp_path / "keys" / "db.json"
    assert json.loads(mw.key_manager.keys_db.read_text()) == {}


@pytest.mark.parametrize("key", [None, ""])
def test_missing_key_is_401(mw, key):
    with pytest.raises(FakeHTTPException) as exc:
        _call(mw, key)
    assert exc.value.status_code == 401
    assert "Missing API key" in exc.value.detail
    assert exc.value.headers == {"WWW-Authenticate": "ApiKey"}


def test_invalid_key_reports_reason(mw):
    with pytest.raises(FakeHTTPException) as exc:
        _call(mw, "not" + "_a_key")
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid API key: invalid_format"


def test_valid_key_returns_metadata_then_rate_limits(mw):
    key_id, api_key = mw.key_manager.generate_key("svc", rate_limit=1)
    info = _call(mw, api_key)
    assert info == {"valid": True, "key_id": key_id, "name": "svc", "rate_limit": 1}
    with pytest.raises(FakeHTTPException) as exc:
        _call(mw, api_key)
    assert exc.value.status_code == 429
    assert exc.value.headers == {"Retry-After": "60"}


# --------------------------------------------------------------------------
# load_testing/analyze_results.py
# --------------------------------------------------------------------------

ar = load("qplant/load_testing/analyze_results.py")

FIELDS = ["Name", "50%", "95%", "99%", "Failure Count", "Request Count"]
BASELINES = {
    "api_endpoints": {
        "/health": {"p95_ms": 100, "p99_ms": 200, "error_rate_pct": "1%"},
        "/slow": {"p95_ms": 100, "p99_ms": 200, "error_rate_pct": 1},
    }
}


def _row(name, p95=10, p99=20, fail=0, req=100):
    return {
        "Name": name,
        "50%": "5",
        "95%": str(p95),
        "99%": str(p99),
        "Failure Count": str(fail),
        "Request Count": str(req),
    }


def _write_csv(path, rows):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def test_load_baselines_and_parse_csv(tmp_path):
    bl = tmp_path / "bl.json"
    bl.write_text(json.dumps(BASELINES))
    assert ar.load_baselines(str(bl)) == BASELINES
    path = tmp_path / "x_stats.csv"
    _write_csv(path, [_row("/health")])
    rows = ar.parse_locust_stats(str(path))
    assert rows == [_row("/health")]
    assert ar.parse_locust_stats(str(tmp_path / "missing.csv")) == []


def test_grade_all_within_baseline_is_a():
    stats = [_row("/health"), _row("Aggregated"), _row(""), _row("/unknown")]
    result = ar.grade_performance(stats, BASELINES)
    assert result["grade"] == "A" and result["score"] == 100.0
    assert [e["name"] for e in result["endpoints"]] == ["/health", "/unknown"]
    assert result["regressions"] == [] and result["recommendations"] == []


def test_grade_regressions_and_floor_at_zero():
    stats = [_row("/slow", p95=150, p99=300, fail=50, req=100)]
    result = ar.grade_performance(stats, BASELINES)
    ep = result["endpoints"][0]
    assert ep["score"] == 40.0 and ep["error_rate_pct"] == 50.0
    assert result["grade"] == "F"
    assert result["regressions"] == [
        "/slow: p95=150.0ms exceeds baseline 100ms",
        "/slow: error_rate=50.00% exceeds baseline",
    ]
    assert len(result["recommendations"]) == 2


@pytest.mark.parametrize(
    "rows,grade",
    [
        ([_row("/slow", p95=150), _row("/health")], "B"),
        ([_row("/slow", p95=150)], "C"),
        ([_row("/slow", p95=150, p99=300)], "C"),
        ([_row("/slow", fail=5)], "C"),
        ([_row("/slow", p95=150, fail=5)], "D"),
    ],
)
def test_grade_boundaries(rows, grade):
    assert ar.grade_performance(rows, BASELINES)["grade"] == grade


def test_grade_empty_stats_and_missing_baselines():
    assert ar.grade_performance([], {})["score"] == 0.0
    assert ar.grade_performance([], {})["grade"] == "F"
    result = ar.grade_performance([_row("/x", fail=0, req=0)], {})
    assert result["endpoints"][0]["requests"] == 0
    assert result["grade"] == "A"


def _run_main(monkeypatch, tmp_path, argv):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["analyze_results.py", *argv])
    (tmp_path / "performance_baselines.json").write_text(json.dumps(BASELINES))
    return ar.main()


def test_main_with_prefix_writes_report(monkeypatch, tmp_path, capsys):
    rows = [_row("/health"), _row("/slow", p95=150, p99=300, fail=3)]
    _write_csv(tmp_path / "run_stats.csv", rows)
    out = tmp_path / "report.json"
    _run_main(monkeypatch, tmp_path, ["--csv-prefix", "run", "--output", str(out)])
    text = capsys.readouterr().out
    assert "Performance Grade: C (70.0/100)" in text
    assert "/health" in text and "Regressions" in text and "Recommendations" in text
    assert "Report saved to" in text
    saved = json.loads(out.read_text())
    assert saved["grade"] == "C" and len(saved["endpoints"]) == 2


def test_main_status_icons(monkeypatch, tmp_path, capsys):
    rows = [
        _row("/health"),
        _row("/slow", fail=5),
        _row("/slow2", p95=150, p99=300, fail=5),
    ]
    _write_csv(tmp_path / "run_stats.csv", rows)
    _run_main(monkeypatch, tmp_path, ["--csv-prefix", "run"])
    text = capsys.readouterr().out
    assert "\u2705 /health\n" in text
    assert "\u26a0\ufe0f /slow\n" in text
    assert "\u274c /slow2\n" in text


def test_main_clean_run_omits_sections(monkeypatch, tmp_path, capsys):
    _write_csv(tmp_path / "run_stats.csv", [_row("/health")])
    _run_main(monkeypatch, tmp_path, ["--csv-prefix", "run"])
    text = capsys.readouterr().out
    assert "Grade: A" in text
    assert "Regressions" not in text and "Recommendations" not in text
    assert "Report saved" not in text


def test_main_picks_most_recent_report(monkeypatch, tmp_path, capsys):
    reports = tmp_path / "reports"
    reports.mkdir()
    _write_csv(reports / "a_stats.csv", [_row("/slow", p95=999, fail=90)])
    _write_csv(reports / "b_stats.csv", [_row("/health")])
    _run_main(monkeypatch, tmp_path, [])
    text = capsys.readouterr().out
    assert "Using most recent:" in text and "b_stats.csv" in text
    assert "Grade: A" in text


def test_main_no_reports_exits(monkeypatch, tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, tmp_path, [])
    assert exc.value.code == 1
    assert "No load test results" in capsys.readouterr().out


def test_main_empty_stats_exits(monkeypatch, tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, tmp_path, ["--csv-prefix", "missing"])
    assert exc.value.code == 1
    assert "No stats found in missing_stats.csv" in capsys.readouterr().out
