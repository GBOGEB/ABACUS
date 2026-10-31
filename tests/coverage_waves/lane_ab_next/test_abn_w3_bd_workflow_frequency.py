"""Behaviour tests for tools/bd_workflow_frequency.py."""

import argparse
import io
import json
import runpy

import pytest

from tests.coverage_waves.lane_b._l2_loader import REPO_ROOT, load

mod = load("tools/bd_workflow_frequency.py", name="abn_w3_bd_workflow_frequency")


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def _run(path, sha, conclusion="success", event="push", branch="main", number=1):
    return {
        "path": path,
        "head_sha": sha,
        "conclusion": conclusion,
        "event": event,
        "head_branch": branch,
        "run_number": number,
    }


def test_api_json_sets_headers_and_decodes(monkeypatch):
    seen = {}

    def fake_urlopen(req, timeout):
        seen["url"] = req.full_url
        seen["timeout"] = timeout
        seen["accept"] = req.get_header("Accept")
        seen["auth"] = req.get_header("Authorization")
        seen["ver"] = req.get_header("X-github-api-version")
        return _Resp(json.dumps({"ok": 1}).encode("utf-8"))

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    cred = "abc"
    out = mod.api_json("https://example.invalid/x", cred)
    assert out == {"ok": 1}
    assert seen["url"] == "https://example.invalid/x"
    assert seen["timeout"] == 45
    assert seen["accept"] == "application/vnd.github+json"
    assert seen["auth"] == "Bearer abc"
    assert seen["ver"] == "2022-11-28"


def test_fetch_runs_stops_on_short_page(monkeypatch):
    calls = []

    def fake_api(url, cred):
        calls.append(url)
        return {"workflow_runs": [{"id": i} for i in range(5)]}

    monkeypatch.setattr(mod, "api_json", fake_api)
    runs = mod.fetch_runs("o/r", "t", 250)
    assert len(runs) == 5
    assert calls == [mod.API + "/repos/o/r/actions/runs?per_page=100&page=1"]


def test_fetch_runs_paginates_and_truncates(monkeypatch):
    calls = []

    def fake_api(url, cred):
        calls.append(url)
        return {"workflow_runs": [{"id": len(calls)}] * 100}

    monkeypatch.setattr(mod, "api_json", fake_api)
    runs = mod.fetch_runs("o/r", "t", 150)
    assert len(runs) == 150
    assert len(calls) == 2
    assert calls[1].endswith("page=2")


def test_fetch_runs_reaches_limit_on_full_pages(monkeypatch):
    monkeypatch.setattr(mod, "api_json", lambda u, t: {"workflow_runs": [{}] * 100})
    assert len(mod.fetch_runs("o/r", "t", 100)) == 100


def test_fetch_runs_missing_key_and_min_one_page(monkeypatch):
    monkeypatch.setattr(mod, "api_json", lambda u, t: {})
    assert mod.fetch_runs("o/r", "t", 0) == []


def test_parse_family_ok_and_errors():
    assert mod.parse_family(" ci = a.yml, b.yml ,,") == ("ci", ["a.yml", "b.yml"])
    with pytest.raises(argparse.ArgumentTypeError, match="NAME=path1"):
        mod.parse_family("nopaths")
    with pytest.raises(argparse.ArgumentTypeError, match="requires a name"):
        mod.parse_family(" =a.yml")
    with pytest.raises(argparse.ArgumentTypeError, match="requires a name"):
        mod.parse_family("ci= , ")


def test_ratio():
    assert mod.ratio(1, 3) == 0.333333
    assert mod.ratio(5, 0) == 0.0


def test_metrics_for_family_counts():
    runs = [
        _run("a.yml", "s1", number=3),
        _run("a.yml", "s1", conclusion="skipped", number=7),
        _run("a.yml", "s2", conclusion=None, number=None),
        _run("b.yml", "s1", event="pull_request"),
        _run("b.yml", None),
        _run("other.yml", "s9"),
    ]
    m = mod.metrics_for_family("fam", ["a.yml", "b.yml", "c.yml"], runs)
    assert m["family"] == "fam"
    assert m["total_invocations"] == 5
    # tuples: (a,push,s1,main) x2 dedup -> 1, (a,push,s2), (b,pr,s1), (b,push,"")
    assert m["unique_input_tuples"] == 4
    assert m["unique_input_tuple_ratio"] == 0.8
    assert m["invocations_per_unique_input"] == 1.25
    assert m["observable_noop_invocations"] == 1
    assert m["observable_noop_rate"] == 0.2
    # workflow_sha set: (a,s1),(a,s2),(b,s1) -> 3
    assert m["same_sha_repeat_invocations"] == 2
    # family shas: s1, s2 -> 2
    assert m["family_sha_fanout_invocations"] == 3
    assert m["family_sha_fanout_rate"] == 0.6
    per = {p["path"]: p for p in m["per_workflow"]}
    assert per["a.yml"]["invocations"] == 3
    assert per["a.yml"]["unique_head_shas"] == 2
    assert per["a.yml"]["same_sha_repeat_invocations"] == 1
    assert per["a.yml"]["conclusions"] == {
        "skipped": 1,
        "success": 1,
        "unknown": 1,
    }
    assert per["a.yml"]["latest_run_number"] == 7
    assert per["b.yml"]["unique_head_shas"] == 1
    assert per["c.yml"]["invocations"] == 0
    assert per["c.yml"]["same_sha_repeat_rate"] == 0.0
    assert per["c.yml"]["latest_run_number"] == 0


def test_metrics_for_family_empty():
    m = mod.metrics_for_family("none", ["x.yml"], [])
    assert m["total_invocations"] == 0
    assert m["invocations_per_unique_input"] == 0.0
    assert m["unique_input_tuple_ratio"] == 0.0


def test_render_markdown_table_rows():
    fam = mod.metrics_for_family("fam", ["a.yml"], [_run("a.yml", "s1")] * 2)
    payload = {
        "repository": "o/r",
        "sampled_runs": 2,
        "generated_at": "2026-01-01T00:00:00+00:00",
        "families": [fam],
    }
    md = mod.render_markdown(payload)
    assert md.startswith("# BD Workflow Frequency Telemetry")
    assert "- Repository: `o/r`" in md
    assert "- Sampled runs: **2**" in md
    assert "| fam | 2 | 50.0% | 0.0% | 50.0% | 50.0% |" in md
    assert "## Measurement contract" in md


def _argv(monkeypatch, tmp_path, *extra):
    argv = [
        "bd",
        "--family",
        "ci=a.yml",
        "--out-json",
        str(tmp_path / "o" / "m.json"),
        "--out-md",
        str(tmp_path / "md" / "m.md"),
        *extra,
    ]
    monkeypatch.setattr("sys.argv", argv)


def test_main_writes_outputs(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")
    _argv(monkeypatch, tmp_path, "--limit", "10")
    seen = {}

    def fake_fetch(repo, cred, limit):
        seen["args"] = (repo, limit)
        return [_run("a.yml", "s1"), _run("a.yml", "s1", conclusion="skipped")]

    monkeypatch.setattr(mod, "fetch_runs", fake_fetch)
    assert mod.main() == 0
    assert seen["args"] == ("o/r", 10)
    data = json.loads((tmp_path / "o" / "m.json").read_text(encoding="utf-8"))
    assert data["schema_version"] == "1.0"
    assert data["repository"] == "o/r"
    assert data["sampled_runs"] == 2
    assert data["measurement_contract"]["authority"] == "operational_bd_only"
    assert data["families"][0]["observable_noop_invocations"] == 1
    md = (tmp_path / "md" / "m.md").read_text(encoding="utf-8")
    assert "| ci | 2 |" in md
    assert "| ci | 2 |" in capsys.readouterr().out


def test_main_requires_token(monkeypatch, tmp_path):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    _argv(monkeypatch, tmp_path, "--repo", "o/r")
    with pytest.raises(SystemExit, match="GITHUB_TOKEN is required"):
        mod.main()


def test_main_rejects_bad_repo(monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    _argv(monkeypatch, tmp_path)
    with pytest.raises(SystemExit, match="owner/name"):
        mod.main()
    _argv(monkeypatch, tmp_path, "--repo", "noslash")
    with pytest.raises(SystemExit, match="owner/name"):
        mod.main()


def test_main_rejects_limit(monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    for limit in ("0", "1001"):
        _argv(monkeypatch, tmp_path, "--repo", "o/r", "--limit", limit)
        with pytest.raises(SystemExit, match="between 1 and 1000"):
            mod.main()


def test_script_entrypoint_requires_family(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["bd"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(
            str(REPO_ROOT / "tools" / "bd_workflow_frequency.py"),
            run_name="__main__",
        )
    assert exc.value.code == 2
    assert "--family" in capsys.readouterr().err
