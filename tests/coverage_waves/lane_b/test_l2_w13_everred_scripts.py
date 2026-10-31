"""Lane-B wave 13: everred_v3 operator scripts (dashboards, reports, collectors).

Sibling ``src`` modules are replaced with recording fakes via loader ``deps``;
GitHub access is never constructed for real and every write goes to tmp_path.
"""

import hashlib
import json
import pathlib
import sys
import types

import pytest

from ._l2_loader import load
from ._l2_markup import parse

SHA = "a" * 40
REPO = "GBOGEB/ABACUS"
SCRIPTS = "tools/everred_v3/scripts/"


def _load_keep_path(rel, deps):
    """Load a script that inserts into sys.path, then restore sys.path."""
    saved = list(sys.path)
    try:
        return load(rel, deps=deps)
    finally:
        sys.path[:] = saved


def _argv(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["prog", *map(str, args)])


# --------------------------------------------------------------------------
# upgrade_dashboard.py (module-level script)
# --------------------------------------------------------------------------


class _UPath:
    """UTF-8 pathlib stand-in so the script's default-encoding I/O is portable."""

    def __init__(self, path):
        self.path = pathlib.Path(path)

    def resolve(self):
        return self

    @property
    def parents(self):
        return [_UPath(p) for p in self.path.parents]

    def __truediv__(self, other):
        return _UPath(self.path / other)

    def read_text(self):
        return self.path.read_text(encoding="utf-8")

    def write_text(self, text):
        self.path.write_text(text, encoding="utf-8")


TEMPLATE = (
    "<nav>"
    '<button data-scroll="data"><span>\u2934</span> Data exchange</button>'
    "</nav>\n"
    '<section id="data" class="section">DATA</section>\n'
    '<script id="svg-data" type="application/json">@@SVGJSON@@</script>\n'
    "<script>\n"
    "const visuals=JSON.parse(document.getElementById('svg-data').textContent);\n"
    "function renderRoots(){}\n"
    "function boot(){\n renderRoots();\n}\n"
    "</script>\n"
)


def _run_upgrade(tmp_path, text):
    target = tmp_path / "dashboard" / "template.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    fake = types.SimpleNamespace(
        Path=lambda _f: _UPath(tmp_path / "scripts" / "upgrade_dashboard.py")
    )
    load(SCRIPTS + "upgrade_dashboard.py", deps={"pathlib": fake})
    return target.read_text(encoding="utf-8")


def test_upgrade_dashboard_inserts_control_panel(tmp_path):
    out = _run_upgrade(tmp_path, TEMPLATE)
    assert out.count('id="control"') == 1
    assert out.index('<section id="control"') < out.index('<section id="data"')
    assert '<button data-scroll="control">' in out
    assert out.index('data-scroll="control"') < out.index('data-scroll="data"')
    assert "@@PULSES@@" in out and "@@ALERTS@@" in out
    assert "const pulses=JSON.parse" in out
    assert "const nativeAlerts=JSON.parse" in out
    assert out.index("function renderControl(){") < out.index("function renderRoots(){")
    assert " renderRoots();renderControl();\n}" in out


def test_upgrade_dashboard_is_idempotent(tmp_path):
    first = _run_upgrade(tmp_path, TEMPLATE)
    second = _run_upgrade(tmp_path, first)
    assert second == first
    assert second.count("function renderControl(){") == 1


def test_upgrade_dashboard_leaves_already_upgraded_text_untouched(tmp_path):
    text = '<section id="control">already</section> renderRoots();\n}'
    assert _run_upgrade(tmp_path, text) == text


# --------------------------------------------------------------------------
# coverage_obligation_report.py
# --------------------------------------------------------------------------


def _obligation_fake(calls):
    def parse_artifact(raw, manifest):
        calls.append((raw, manifest))
        return {"sha": manifest["sha"], "bytes": len(raw)}

    def compare(before, after):
        return {
            "before_sha": before["sha"],
            "after_sha": after["sha"],
            "status": "NO_REGRESSION" if after["bytes"] >= before["bytes"] else "DROP",
            "merge_admission": "HOLD",
            "detail": [before, after],
        }

    return types.SimpleNamespace(parse_artifact=parse_artifact, compare=compare)


def _obligation_inputs(tmp_path, before=b"{}", after=b'{"x":1}'):
    files = {}
    for label, raw, sha in (("before", before, "1" * 40), ("after", after, "2" * 40)):
        js = tmp_path / (label + ".json")
        js.write_bytes(raw)
        mf = tmp_path / (label + "_manifest.json")
        mf.write_text(json.dumps({"sha": sha}), encoding="utf-8")
        files[label] = (js, mf)
    return files


def test_coverage_obligation_report_writes_and_prints(tmp_path, monkeypatch, capsys):
    calls = []
    mod = _load_keep_path(
        SCRIPTS + "coverage_obligation_report.py",
        {"obligation_lineage": _obligation_fake(calls)},
    )
    f = _obligation_inputs(tmp_path)
    out = tmp_path / "nested" / "report.json"
    _argv(
        monkeypatch,
        "--before-json",
        f["before"][0],
        "--before-manifest",
        f["before"][1],
        "--after-json",
        f["after"][0],
        "--after-manifest",
        f["after"][1],
        "--out",
        out,
    )
    mod.main()
    assert [c[1]["sha"] for c in calls] == ["1" * 40, "2" * 40]
    assert calls[0][0] == b"{}" and calls[1][0] == b'{"x":1}'
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["status"] == "NO_REGRESSION"
    assert out.read_text(encoding="utf-8").endswith("}\n")
    printed = json.loads(capsys.readouterr().out)
    assert printed == {
        "before_sha": "1" * 40,
        "after_sha": "2" * 40,
        "status": "NO_REGRESSION",
        "merge_admission": "HOLD",
    }


def test_coverage_obligation_report_requires_all_inputs(tmp_path, monkeypatch):
    mod = _load_keep_path(
        SCRIPTS + "coverage_obligation_report.py",
        {"obligation_lineage": _obligation_fake([])},
    )
    _argv(monkeypatch, "--out", tmp_path / "r.json")
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 2
    assert not (tmp_path / "r.json").exists()


# --------------------------------------------------------------------------
# ci_latency_report.py
# --------------------------------------------------------------------------


class FakeReader:
    instances = []

    def __init__(self):
        self.calls = []
        FakeReader.instances.append(self)

    def run_and_jobs(self, repo, run_id, sha):
        self.calls.append((repo, run_id, sha))
        return {"id": run_id}, [{"id": run_id * 10}]


def _ci_mods():
    FakeReader.instances = []

    def measure_run(run, jobs, repo, sha):
        return {"run_id": run["id"], "jobs": len(jobs), "repo": repo, "sha": sha}

    def cohort(evidence):
        return {"status": "MEASURED", "n": len(evidence)}

    def digest_receipt(payload):
        raw = json.dumps(payload, sort_keys=True).encode()
        return hashlib.sha256(raw).hexdigest()

    ci = types.SimpleNamespace(
        SCHEMA="abacus.everred.ci-latency.v1",
        cohort=cohort,
        digest_receipt=digest_receipt,
        measure_run=measure_run,
    )
    ni = types.SimpleNamespace(GitHubReadOnly=FakeReader)
    return _load_keep_path(
        SCRIPTS + "ci_latency_report.py", {"ci_latency": ci, "native_ingest": ni}
    )


def test_ci_latency_report_main_builds_batch_receipt(tmp_path, monkeypatch, capsys):
    mod = _ci_mods()
    out = tmp_path / "deep" / "lat.json"
    _argv(
        monkeypatch,
        "--repo",
        REPO,
        "--sha",
        SHA,
        "--run-id",
        5,
        "--run-id",
        6,
        "--output",
        out,
    )
    mod.main()
    (reader,) = FakeReader.instances
    assert reader.calls == [(REPO, 5, SHA), (REPO, 6, SHA)]
    body = json.loads(out.read_text(encoding="utf-8"))
    assert body["schema"] == "abacus.everred.ci-latency.v1.batch"
    assert [r["run_id"] for r in body["run_receipts"]] == [5, 6]
    assert body["cohort"] == {"status": "MEASURED", "n": 2}
    assert body["merge_admission"] == "HOLD"
    assert body["security_waiver"] is False and body["authority_transfer"] is False
    digest = body.pop("sha256")
    expected = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    assert digest == expected
    printed = json.loads(capsys.readouterr().out)
    assert printed == {
        "runs": 2,
        "state": "MEASURED",
        "source_sha": SHA,
        "batch_digest": digest,
    }


@pytest.mark.parametrize(
    "ids, message",
    [
        ([], "between one and 30"),
        (list(range(1, 32)), "between one and 30"),
        ([4, 4], "duplicate native run IDs"),
    ],
)
def test_ci_latency_report_rejects_bad_run_id_sets(tmp_path, ids, message):
    mod = _ci_mods()
    args = types.SimpleNamespace(
        run_id=ids, repo=REPO, sha=SHA, output=tmp_path / "x.json"
    )
    with pytest.raises(ValueError, match=message):
        mod.run(args)
    assert FakeReader.instances == []
    assert not (tmp_path / "x.json").exists()


def test_ci_latency_report_accepts_thirty_runs(tmp_path, capsys):
    mod = _ci_mods()
    args = types.SimpleNamespace(
        run_id=list(range(1, 31)), repo=REPO, sha=SHA, output=tmp_path / "x.json"
    )
    mod.run(args)
    assert json.loads(capsys.readouterr().out)["runs"] == 30


# --------------------------------------------------------------------------
# collect_native.py
# --------------------------------------------------------------------------


def _collect_mod():
    calls = {"collect": [], "ledger": []}

    class Reader:
        pass

    def collect_native(repo, sha, run_id, plan, *, reader):
        calls["collect"].append((repo, sha, run_id, plan, type(reader).__name__))
        return [{"event_id": "e1"}, {"event_id": "e2"}]

    def append_events_batch(path, events):
        calls["ledger"].append((path, events))
        return len(events)

    ev = types.SimpleNamespace(append_events_batch=append_events_batch)
    ni = types.SimpleNamespace(GitHubReadOnly=Reader, collect_native=collect_native)
    mod = _load_keep_path(
        SCRIPTS + "collect_native.py", {"everred": ev, "native_ingest": ni}
    )
    return mod, calls


def test_collect_native_dry_run_without_plan(tmp_path, monkeypatch, capsys):
    mod, calls = _collect_mod()
    out = tmp_path / "o" / "batch.json"
    _argv(monkeypatch, "--repo", REPO, "--sha", SHA, "--run-id", 9, "--output", out)
    mod.main()
    assert calls["collect"] == [(REPO, SHA, 9, [], "Reader")]
    assert calls["ledger"] == []
    body = json.loads(out.read_text())
    assert body["schema"] == "abacus.everred.native.batch.v1"
    assert len(body["events"]) == 2
    assert capsys.readouterr().out.strip() == (
        "Collected 2 events at " + SHA + ": DRY_RUN_ONLY"
    )


def test_collect_native_with_plan_applies_ledger(tmp_path, monkeypatch, capsys):
    mod, calls = _collect_mod()
    plan = [{"artifact_id": 3, "kind": "bandit"}]
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(plan))
    ledger = tmp_path / "ledger.jsonl"
    _argv(
        monkeypatch,
        "--repo",
        REPO,
        "--sha",
        SHA,
        "--run-id",
        9,
        "--artifact-plan",
        plan_file,
        "--output",
        tmp_path / "b.json",
        "--apply-ledger",
        "--ledger",
        ledger,
    )
    mod.main()
    assert calls["collect"][0][3] == plan
    ((path, events),) = calls["ledger"]
    assert path == ledger and [e["event_id"] for e in events] == ["e1", "e2"]
    assert capsys.readouterr().out.strip().endswith(": LEDGER_APPLIED")


def test_collect_native_default_ledger_under_base():
    mod, _ = _collect_mod()
    assert mod.BASE.name == "everred_v3"
    assert (mod.BASE / "src").is_dir()


# --------------------------------------------------------------------------
# build_four_plane_dashboard.py
# --------------------------------------------------------------------------


def _bfd(tmp_path, monkeypatch):
    mod = load(SCRIPTS + "build_four_plane_dashboard.py")
    diagrams = tmp_path / "base" / "diagrams"
    diagrams.mkdir(parents=True)
    for name, label in (
        ("06_four_plane_execution.svg", "dag"),
        ("07_four_plane_sipoc.svg", "sipoc"),
    ):
        (diagrams / name).write_text(
            '<?xml version="1.0"?>\n<!-- prolog -->\n<svg id="' + label + '"></svg>',
            encoding="utf-8",
        )
    monkeypatch.setattr(mod, "BASE", tmp_path / "base")
    return mod


def _snapshot(**over):
    snap = {
        "schema": "abacus.everred.four_plane.preflight.v1",
        "source_binding": {"source_sha": SHA},
        "joined_census": {"observation_count": 2},
        "receipts": [{"id": 1}, {"id": 2, "note": "</script><b>x</b>"}],
        "dispatch_preview": {"tasks": [{"id": "t1"}, {"id": "t2"}, {"id": "t3"}]},
        "plan": {"task_count": 3},
        "claims": {"admission": "HOLD"},
    }
    snap.update(over)
    return snap


def _write(tmp_path, obj, name="snap.json"):
    path = tmp_path / name
    path.write_text(json.dumps(obj), encoding="utf-8")
    return path


def test_build_four_plane_dashboard_renders_page(tmp_path, monkeypatch):
    mod = _bfd(tmp_path, monkeypatch)
    snap = _write(tmp_path, _snapshot())
    target = tmp_path / "out" / "page.html"
    result = mod.build(snap, target)
    page = target.read_text(encoding="utf-8")
    digest = hashlib.sha256(snap.read_bytes()).hexdigest()
    assert result == {
        "html": target.as_posix(),
        "html_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "snapshot_sha256": digest,
        "observations": 2,
        "tasks": 3,
    }
    assert page.count(digest) == 2
    assert "DIGEST" not in page and "HEAD_PLACEHOLDER" not in page
    assert '<strong id="metricObservations">2</strong>' in page
    assert '<strong id="metricTasks">3</strong>' in page
    assert '<code id="sha">' + SHA + "</code>" in page
    assert "<?xml" not in page and "prolog" not in page
    grid = page[page.index('<div class="diagram-grid">') :]
    grid = grid[: grid.index("</section>")]
    top = parse(grid)
    arts = top.find_all("article")
    assert [a.find("h3").text for a in arts] == [
        "Execution DAG",
        "SIPOC ownership and evidence flow",
    ]
    assert [a.find("svg").get("id") for a in arts] == ["dag", "sipoc"]
    start = page.index('id="embeddedSnapshot">') + len('id="embeddedSnapshot">')
    embedded = page[start : page.index("</script>", start)]
    assert "<" not in embedded
    assert json.loads(embedded)["receipts"][1]["note"] == "</script><b>x</b>"


def test_build_four_plane_dashboard_escapes_sha(tmp_path, monkeypatch):
    mod = _bfd(tmp_path, monkeypatch)
    odd = "<" * 40
    snap = _write(tmp_path, _snapshot(source_binding={"source_sha": odd}))
    mod.build(snap, tmp_path / "p.html")
    page = (tmp_path / "p.html").read_text(encoding="utf-8")
    assert '<code id="sha">' + "&lt;" * 40 + "</code>" in page


@pytest.mark.parametrize(
    "over, message",
    [
        ({"schema": "other"}, "unknown preflight schema"),
        ({"source_binding": {"source_sha": "abc"}}, "missing source pin"),
        ({"joined_census": {"observation_count": 9}}, "count mismatch"),
        ({"plan": {"task_count": 1}}, "count mismatch"),
    ],
)
def test_build_four_plane_dashboard_rejects_bad_snapshots(
    tmp_path, monkeypatch, over, message
):
    mod = _bfd(tmp_path, monkeypatch)
    snap = _write(tmp_path, _snapshot(**over))
    with pytest.raises(ValueError, match=message):
        mod.build(snap, tmp_path / "p.html")
    assert not (tmp_path / "p.html").exists()


def test_build_four_plane_dashboard_main_prints_summary(tmp_path, monkeypatch, capsys):
    mod = _bfd(tmp_path, monkeypatch)
    snap = _write(tmp_path, _snapshot())
    out = tmp_path / "d" / "status.html"
    _argv(monkeypatch, "--snapshot", snap, "--output", out)
    mod.main()
    printed = json.loads(capsys.readouterr().out)
    assert printed["tasks"] == 3 and printed["observations"] == 2
    assert printed["html"] == out.as_posix()
    assert out.is_file()


# --------------------------------------------------------------------------
# qa_four_plane_release.py
# --------------------------------------------------------------------------


def _qa(tmp_path, monkeypatch, snap):
    mod = load(SCRIPTS + "qa_four_plane_release.py")
    base = tmp_path / "base"
    for rel in mod.FILES:
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(("content of " + rel).encode())
    (base / "data").mkdir()
    (base / "data" / "four_plane_preflight.json").write_text(json.dumps(snap))
    monkeypatch.setattr(mod, "BASE", base)
    return mod


def test_qa_four_plane_release_make_hashes_every_file(tmp_path, monkeypatch):
    snap = _snapshot()
    mod = _qa(tmp_path, monkeypatch, snap)
    receipt = mod.make()
    source = receipt["source_file_hashes"]
    assert sorted(source) == sorted(mod.FILES)
    for rel, value in source.items():
        assert value == hashlib.sha256(("content of " + rel).encode()).hexdigest()
    semantic = hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()
    assert receipt["source"]["semantic_sha256"] == semantic
    assert receipt["source"]["git_sha"] is None
    html = receipt["artifacts"]["html"]
    assert html["sha256"] == source["dashboard/four_plane_status.html"]
    assert (
        receipt["artifacts"]["svg_sipoc"]["sha256"]
        == source["diagrams/07_four_plane_sipoc.svg"]
    )
    assert receipt["evidence_level"] == "LOCAL_REPRODUCIBILITY"
    assert mod.sha(tmp_path / "base" / mod.FILES[0]) == source[mod.FILES[0]]


@pytest.mark.parametrize(
    "over",
    [
        {"claims": {"admission": "ADMIT"}},
        {"joined_census": {"observation_count": 5}},
    ],
)
def test_qa_four_plane_release_rejects_integrity_mismatch(tmp_path, monkeypatch, over):
    mod = _qa(tmp_path, monkeypatch, _snapshot(**over))
    with pytest.raises(ValueError, match="integrity mismatch"):
        mod.make()


def test_qa_four_plane_release_missing_artifact_raises(tmp_path, monkeypatch):
    mod = _qa(tmp_path, monkeypatch, _snapshot())
    (tmp_path / "base" / "diagrams" / "06_four_plane_execution.svg").unlink()
    with pytest.raises(FileNotFoundError):
        mod.make()
