"""Lane-B wave 7: everred_v3 mass_signal_join scanner census."""

import json
import sys

import pytest

from ._l2_loader import load

ms = load("tools/everred_v3/src/mass_signal_join.py")

REPO, HEAD = "GBOGEB/ABACUS", "a" * 40
SEP = chr(92)


def _source(scanner="bandit", run=1, artifact="1", mode="detailed", **overrides):
    source = {
        "scanner": scanner,
        "repository": REPO,
        "head_sha": HEAD,
        "run_id": run,
        "attempt": 1,
        "job_id": 2,
        "artifact_sha256": artifact * 64,
        "config_sha256": "c" * 64,
        "mode": mode,
        "enforcement": {
            "continue_on_error": False,
            "workflow_conclusion": "failure",
            "required_check": None,
        },
    }
    if mode == "detailed":
        source["findings"] = []
    else:
        source.update(counts={"B101": 2}, total=2)
    source.update(overrides)
    return source


def _payload(*sources, **overrides):
    payload = {
        "schema": ms.SCHEMA,
        "repository": REPO,
        "head_sha": HEAD,
        "sources": list(sources),
    }
    payload.update(overrides)
    return payload


def _finding(rule, path="src/a.py", line=10):
    return {"rule_id": rule, "path": path, "line": line}


@pytest.mark.parametrize(
    "scanner,rule,expected",
    [
        ("ruff", "S602", "COMMAND_EXECUTION"),
        ("ruff", "S110", "ERROR_OBSERVABILITY"),
        ("ruff", "S314", "UNSAFE_XML"),
        ("ruff", "S324", "CRYPTOGRAPHIC_INTENT"),
        ("ruff", "E501", "SCANNER_SPECIFIC:ruff:E501"),
        ("bandit", "B603", "COMMAND_EXECUTION"),
        ("bandit", "B324", "CRYPTOGRAPHIC_INTENT"),
        ("semgrep", "python.lang.subprocess-shell", "COMMAND_EXECUTION"),
        ("codeql", "py/unsafe-xml-parse", "UNSAFE_XML"),
        ("semgrep", "weak-hash-md5", "CRYPTOGRAPHIC_INTENT"),
        ("codeql", "py/clear-text", "SCANNER_SPECIFIC:codeql:py/clear-text"),
        ("flake8", "E722", "ERROR_OBSERVABILITY"),
        ("black", "fmt", "SCANNER_SPECIFIC:black:fmt"),
    ],
)
def test_family(scanner, rule, expected):
    assert ms.family(scanner, rule) == expected


@pytest.mark.parametrize(
    "path,ok",
    [
        ("src/a.py", True),
        ("", False),
        ("/abs", False),
        ("a" + SEP + "b", False),
        ("c:x", False),
        ("a" + chr(0), False),
        ("a//b", False),
        ("a/../b", False),
        ("x" * 1025, False),
        (None, False),
    ],
)
def test_path_ok(path, ok):
    assert ms.path_ok(path) is ok


def test_digest_is_canonical():
    assert ms.digest({"b": 1, "a": [1, 2]}) == ms.digest({"a": [1, 2], "b": 1})
    with pytest.raises(ValueError):
        ms.digest({"x": float("nan")})


def test_normalize_cross_scanner_candidates_and_aggregates():
    bandit = _source(findings=[_finding("B603"), _finding("B101", line=11)])
    semgrep = _source(
        "semgrep", run=2, artifact="2", findings=[_finding("cmd-subprocess-call")]
    )
    ruff = _source("ruff", run=3, artifact="3", findings=[_finding("S602", line=99)])
    flake8 = _source(
        "flake8",
        run=4,
        artifact="4",
        mode="aggregate",
        counts={"E722": 3, "F401": 1},
        total=4,
    )
    result = ms.normalize(_payload(bandit, semgrep, ruff, flake8))
    assert result["scanner_totals"] == {
        "bandit": 2,
        "flake8": 4,
        "ruff": 1,
        "semgrep": 1,
    }
    assert result["per_rule_counts"]["flake8"] == {"E722": 3, "F401": 1}
    assert result["detailed_fingerprint_counts"] == {
        "bandit": 2,
        "ruff": 1,
        "semgrep": 1,
    }
    assert result["cross_scanner_candidates"] == [
        {
            "path": "src/a.py",
            "line": 10,
            "family": "COMMAND_EXECUTION",
            "scanners": ["bandit", "semgrep"],
            "state": "UNCONFIRMED_CAUSAL_CANDIDATE",
        }
    ]
    assert result["candidate_count"] == 1 and result["source_observations"] == 4
    assert [e["scanner"] for e in result["enforcement"]] == [
        "bandit",
        "flake8",
        "ruff",
        "semgrep",
    ]
    assert (
        result["merge_admission"] == "HOLD" and result["verified_causal_roots"] is None
    )


def _bad(**overrides):
    return _payload(_source(**overrides))


@pytest.mark.parametrize(
    "payload,message",
    [
        ("x", "invalid signal schema"),
        (
            _payload(_source(), repository="other/ABACUS"),
            "invalid exact repository identity",
        ),
        (
            _payload(_source(), repository="GBOGEB/.."),
            "invalid exact repository identity",
        ),
        (_payload(_source(), head_sha="A" * 40), "invalid exact repository identity"),
        (_payload(), "missing scanner sources"),
        (_payload("x"), "malformed scanner source"),
        (_bad(scanner="pylint"), "unsupported scanner"),
        (_bad(head_sha="b" * 40), "cross-head scanner join"),
        (_bad(attempt=0), "missing native run/job/attempt"),
        (_payload(_source(), _source()), "duplicate scanner source"),
        (_bad(config_sha256="short"), "invalid source/config byte identity"),
        (_payload(_source(), _source(run=9)), "duplicate scanner artifact"),
        (_bad(mode="sampled"), "invalid scanner evidence granularity"),
        (_bad(enforcement={"continue_on_error": "no"}), "enforcement semantics absent"),
        (
            _bad(
                enforcement={
                    "continue_on_error": True,
                    "workflow_conclusion": "maybe",
                    "required_check": None,
                }
            ),
            "enforcement semantics absent",
        ),
        (_bad(mode="aggregate", counts={}), "missing aggregate counts"),
        (_bad(mode="aggregate", counts={"!bad": 1}), "invalid aggregate finding"),
        (_bad(mode="aggregate", counts={"B1": -1}), "invalid aggregate finding"),
        (_bad(mode="aggregate", total=3), "aggregate denominator"),
        (_bad(mode="aggregate", findings=[]), "aggregate cannot infer locations"),
        (_bad(findings=None), "missing detailed findings"),
        (_bad(total=0), "details cannot silently mix"),
        (_bad(findings=["x"]), "invalid finding"),
        (
            _bad(findings=[_finding("B1", path="/etc/x")]),
            "invalid finding rule/location",
        ),
        (_bad(findings=[_finding("B1", line=0)]), "invalid finding rule/location"),
    ],
)
def test_normalize_rejections(payload, message):
    with pytest.raises(ms.InvalidCensus, match=message):
        ms.normalize(payload)


def test_main_writes_projection_atomically(tmp_path, monkeypatch):
    source = tmp_path / "in.json"
    raw = json.dumps(_payload(_source(findings=[_finding("B603")]))).encode("utf-8")
    source.write_bytes(raw)
    out = tmp_path / "nested" / "out.json"
    monkeypatch.setattr(
        sys, "argv", ["prog", "--input", str(source), "--output", str(out)]
    )
    ms.main()
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["scanner_totals"] == {"bandit": 1}
    assert len(result["input_sha256"]) == 64
    assert [p.name for p in out.parent.iterdir()] == ["out.json"]
    # Re-running over an existing, distinct output replaces it.
    ms.main()
    assert (
        json.loads(out.read_text(encoding="utf-8"))["input_sha256"]
        == result["input_sha256"]
    )


def test_main_refuses_aliasing_and_cleans_up(tmp_path, monkeypatch):
    source = tmp_path / "in.json"
    source.write_text(json.dumps(_payload(_source())), encoding="utf-8")
    monkeypatch.setattr(
        sys, "argv", ["prog", "--input", str(source), "--output", str(source)]
    )
    with pytest.raises(ms.InvalidCensus, match="output aliases input evidence"):
        ms.main()

    out = tmp_path / "out.json"
    monkeypatch.setattr(
        sys, "argv", ["prog", "--input", str(source), "--output", str(out)]
    )

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(ms.os, "replace", boom)
    with pytest.raises(OSError, match="disk full"):
        ms.main()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["in.json"]
