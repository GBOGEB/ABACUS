"""Lane A wave 13: .github/scripts/security_dashboard.py (network mocked)."""

import sys

import pytest

from tests.coverage_waves.lane_a._load import load


@pytest.fixture(scope="module")
def sd():
    saved_path = list(sys.path)
    name = "l1_w13_security_dashboard"
    try:
        mod = load(".github/scripts/security_dashboard.py", name=name)
    finally:
        sys.path[:] = saved_path
        sys.modules.pop(name, None)
    return mod


class _Resp:
    def __init__(self, status, body=b"[]", link=""):
        self.status = status
        self._body = body
        self._link = link

    def read(self):
        return self._body

    def getheader(self, name, default=""):
        return self._link or default


class _Conn:
    def __init__(self, resp, log):
        self.resp = resp
        self.log = log

    def request(self, method, target, headers):
        self.log.append((method, target, headers["Accept"]))

    def getresponse(self):
        return self.resp

    def close(self):
        self.log.append("closed")


def _factory(responses, log):
    queue = list(responses)

    def make(host, timeout):
        log.append((host, timeout))
        return _Conn(queue.pop(0), log)

    return make


def _alert(tool, rule, sev, path, number):
    return {
        "tool": {"name": tool},
        "rule": {"id": rule, "severity": sev},
        "number": number,
        "html_url": "u",
        "most_recent_instance": {
            "location": {"path": path, "start_line": number},
            "message": {"text": "m" * 200},
        },
    }


def test_classify_rex_exact_prefix_other(sd):
    assert sd.classify_rex("B101") == "SEC_ASSERT"
    assert sd.classify_rex("B602x") == "SEC_SUBPROCESS"
    assert sd.classify_rex("python.lang.security.audit.pickle.load") == (
        "SEC_DESERIALIZATION"
    )
    assert sd.classify_rex("ZZZ999") == "OTHER"


def test_gh_get_rejects_non_https_before_connect(sd, monkeypatch):
    log = []
    monkeypatch.setattr(sd, "HTTPSConnection", _factory([], log))
    monkeypatch.setattr(sd, "API_BASE", "http://api.github.com")
    with pytest.raises(ValueError, match="Unsafe"):
        sd.gh_get("/repos/x/y/code-scanning/alerts")
    assert log == []


def test_gh_get_non_list_payload_rejected(sd, monkeypatch):
    log = []
    resp = _Resp(200, b'{"message": "x"}')
    monkeypatch.setattr(sd, "HTTPSConnection", _factory([resp], log))
    with pytest.raises(ValueError, match="Expected list"):
        sd.gh_get("/repos/GBOGEB/ABACUS/code-scanning/alerts")
    assert log[-1] == "closed"


def test_gh_get_other_repo_no_query_and_ignores_non_next_links(sd, monkeypatch):
    log = []
    resp = _Resp(200, b'[{"n": 1}]', link='<https://api.github.com/x>; rel="prev"')
    monkeypatch.setattr(sd, "REPO", "other/repo")
    monkeypatch.setattr(sd, "HTTPSConnection", _factory([resp], log))
    assert sd.gh_get("/repos/other/repo/code-scanning/alerts") == [{"n": 1}]
    assert log[1] == (
        "GET",
        "/repos/other/repo/code-scanning/alerts",
        ("application/vnd.github+json"),
    )


def test_fetch_alerts_builds_path(sd, monkeypatch):
    seen = []

    def fake_get(path):
        seen.append(path)
        return [1]

    monkeypatch.setattr(sd, "gh_get", fake_get)
    assert sd.fetch_alerts("fixed") == [1]
    assert seen[0].endswith("code-scanning/alerts?per_page=100&state=fixed")


def test_build_telemetry_groups_and_defaults(sd):
    alerts = [
        _alert("CodeQL", "py/path-injection", "High", "a.py", 1),
        _alert("Bandit", "B101", "note", "a.py", 2),
        _alert("Bandit", "B105", "critical", "b.py", 3),
        {},
    ]
    tel = sd.build_telemetry(alerts)
    assert tel["total_open"] == 4
    assert tel["by_tool"] == {"CodeQL": 1, "Bandit": 2, "unknown": 1}
    assert tel["by_severity"]["high"] == 1
    assert tel["by_severity"]["none"] == 1
    assert tel["hot_files"][0] == {"file": "a.py", "count": 2}
    assert tel["by_rex_group"]["OTHER"] == 1
    assert len(tel["groups"]["SEC_PATH_TRAVERSAL"][0]["message"]) == 120


def test_render_markdown_orders_and_unknown_group(sd):
    tel = {
        "generated_at": "T",
        "total_open": 3,
        "by_tool": {"B": 1, "A": 2},
        "by_severity": {"note": 1, "critical": 1, "weird": 1},
        "by_rex_group": {"NEW_GROUP": 1, "SEC_ASSERT": 2},
    }
    md = sd.render_markdown(tel)
    assert md.index("- critical: 1") < md.index("- note: 1") < md.index("- weird")
    assert md.index("- A: 2") < md.index("- B: 1")
    assert "- NEW_GROUP (INFO): 1" in md
    assert "- SEC_ASSERT (LOW): 2" in md


def test_render_yaml_all_value_shapes(sd):
    tel = {
        "generated_at": "2026-01-01T00:00:00Z",
        "repo": "o/r",
        "total_open": 2,
        "empty_map": {},
        "empty_list": [],
        "by_tool": {"Bandit": 2},
        "hot_files": [{"file": "a.py", "count": 2}],
        "tags": ["x", "y"],
        "groups": {
            "SEC_ASSERT": [
                {
                    "number": 7,
                    "tool": "Bandit",
                    "rule_id": "B101",
                    "severity": "low",
                    "file": "a.py",
                    "line": 3,
                }
            ]
        },
    }
    text = sd.render_yaml(tel)
    assert 'generated_at: "2026-01-01T00:00:00Z"' in text
    assert "repo: o/r" in text
    assert "total_open: 2" in text
    assert "empty_map: {}" in text
    assert "empty_list: []" in text
    assert "by_tool:\n  Bandit: 2" in text
    assert "hot_files:\n  - file: a.py\n    count: 2" in text
    assert "tags:\n  - x\n  - y" in text
    assert "groups:\n  SEC_ASSERT:\n    - number: 7" in text
    assert '      rule_id: "B101"' in text
    assert text.endswith("line: 3\n")


def test_main_without_token_exits_one(sd, monkeypatch, capsys):
    monkeypatch.setattr(sd, "TOKEN", "")
    with pytest.raises(SystemExit) as exc:
        sd.main()
    assert exc.value.code == 1
    assert "GITHUB_TOKEN not set" in capsys.readouterr().err


def test_main_writes_dashboard(sd, monkeypatch, tmp_path, capsys):
    credential = "-".join(["unit", "value"])
    monkeypatch.setattr(sd, "TOKEN", credential)
    alerts = [
        _alert("Bandit", "B101", "low", "a.py", 1),
        _alert("Mystery", "Q1", "low", "b.py", 2),
    ]
    monkeypatch.setattr(sd, "fetch_alerts", lambda state: alerts)
    monkeypatch.chdir(tmp_path)
    sd.main()
    md = (tmp_path / ".github" / "security" / "dashboard.md").read_text(
        encoding="utf-8"
    )
    assert "2 open alerts" in md
    out = capsys.readouterr().out
    assert "2 open alerts fetched" in out
    assert "SEC_ASSERT" in out and "[INFO]" in out
    assert credential not in out
