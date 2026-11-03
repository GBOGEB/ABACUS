"""Gap tests for scripts/validate_ssot_style.py: probe depth kinds and CLI."""

import json

from tests.coverage_waves.lane_b._l2_loader import load

vss = load("scripts/validate_ssot_style.py", name="abn_w7_validate_ssot_style")


def test_repair_pr_set_rejects_non_integer_lists():
    errors = []
    assert vss._repair_pr_set(["754"], "field", errors) == set()
    assert errors == ["field must be an integer or list of integers"]
    assert vss._repair_pr_set(7, "field", errors) == {7}


def test_probe_without_weight_skips_weight_check():
    errors = vss.validate_manifest({"awake_probes": [{"id": "a"}]})
    assert "awake probe missing weight: {'id': 'a'}" in errors
    assert not any(e.startswith("probe weight") for e in errors)


def test_read_text_falls_back_on_bad_utf8(tmp_path):
    path = tmp_path / "bad.txt"
    path.write_bytes(b"ok\xff text")
    assert vss._read_text(path) == "ok text"


def test_probe_depth_missing_path(tmp_path):
    assert vss._probe_depth("graph", tmp_path / "nope") == (0, 3, ["missing"])


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_probe_depth_graph_and_playwright_partial(tmp_path):
    graph = _write(tmp_path, "g.yaml", "nodes: a\n")
    assert vss._probe_depth("graph", graph) == (2, 4, ["exists", "topology"])
    pw = _write(tmp_path, "p.py", "chromium only")
    assert vss._probe_depth("playwright", pw) == (2, 4, ["exists", "browser"])


def test_probe_depth_dow_json_full_and_invalid(tmp_path):
    good = _write(
        tmp_path,
        "dow.json",
        json.dumps(
            {
                "status": "ok",
                "components": {"dow_agents": 2},
                "pipeline": {"orchestrator": "x"},
            }
        ),
    )
    depth, max_depth, signals = vss._probe_depth("dow", good)
    assert (depth, max_depth) == (4, 4)
    assert signals == ["exists", "status_ok", "agents", "orchestrator"]
    bad = _write(tmp_path, "bad.json", "{not json")
    assert vss._probe_depth("dow", bad) == (1, 4, ["exists"])


def test_probe_depth_dow_keb_text(tmp_path):
    src = _write(
        tmp_path,
        "keb.py",
        "def test_x(): pass\nbidirectional\nasync def run(): queue_size\n",
    )
    depth, _, signals = vss._probe_depth("keb", src)
    assert depth == 4
    assert signals == ["exists", "tests", "bidirectional", "runtime", "queue_feedback"]
    plain = _write(tmp_path, "dow.py", "nothing here")
    assert vss._probe_depth("dow", plain) == (1, 4, ["exists"])


def test_probe_depth_html_and_style(tmp_path):
    html = _write(tmp_path, "a.html", "<HTML><script>PCA</script>")
    assert vss._probe_depth("html", html)[2] == [
        "exists",
        "document",
        "pca_bt",
        "scripted",
    ]
    empty_html = _write(tmp_path, "b.html", "plain")
    assert vss._probe_depth("html", empty_html) == (1, 4, ["exists"])
    style = _write(tmp_path, "s.yaml", "palette\nAptos\nrender_qa\n")
    assert vss._probe_depth("style", style)[2] == [
        "exists",
        "palette",
        "typography",
        "validation",
    ]
    empty_style = _write(tmp_path, "t.yaml", "nothing")
    assert vss._probe_depth("style", empty_style) == (1, 4, ["exists"])
    other = _write(tmp_path, "o.txt", "x")
    assert vss._probe_depth("unknown", other) == (1, 4, ["exists"])


def test_score_artifact_contract_counts_gates():
    result = vss.score_artifact_contract(
        {"artifact_contract": {"excel": ["a", "b"], "pdf": ["c"], "extra": []}}
    )
    assert result["artifact_count"] == 3
    assert result["total_gate_count"] == 3
    assert result["gate_counts"] == {"excel": 2, "pdf": 1, "extra": 0}
    assert result["contract_score"] == round(2 / 6 * 100, 1)


def _manifest(tmp_path):
    manifest = {
        "awake_probes": [{"id": "s", "path": "s.yaml", "kind": "style", "weight": 1}],
        "scoring": {"pca_focus_axes": ["x"], "bt_priority_rule": "rule"},
    }
    (tmp_path / "s.yaml").write_text("palette", encoding="utf-8")
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_build_report_relative_and_absolute_manifest(tmp_path):
    path = _manifest(tmp_path)
    report = vss.build_report(path, root=tmp_path)
    assert report["manifest"] == "manifest.json"
    assert report["valid"] is False
    assert report["pca_focus_axes"] == ["x"]
    assert report["bt_priority_rule"] == "rule"
    assert report["penetration"]["by_kind"]["style"] == {"depth": 2, "max_depth": 4}
    other_root = tmp_path / "elsewhere"
    other_root.mkdir()
    report2 = vss.build_report(path, root=other_root)
    assert report2["manifest"] == str(path)


def test_main_writes_output_and_returns_one(tmp_path, monkeypatch, capsys):
    path = _manifest(tmp_path)
    monkeypatch.setattr(vss, "ROOT", tmp_path)
    monkeypatch.setattr(
        vss,
        "build_report",
        lambda manifest_path: dict(valid=False, manifest=str(manifest_path)),
    )
    out = tmp_path / "nested" / "report.json"
    rc = vss.main(["--manifest", str(path), "--output", str(out)])
    assert rc == 1
    assert json.loads(out.read_text(encoding="utf-8"))["valid"] is False
    assert '"valid": false' in capsys.readouterr().out


def test_main_valid_without_output(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(vss, "build_report", lambda manifest_path: dict(valid=True))
    assert vss.main(["--manifest", str(tmp_path / "m.json")]) == 0
    assert '"valid": true' in capsys.readouterr().out
