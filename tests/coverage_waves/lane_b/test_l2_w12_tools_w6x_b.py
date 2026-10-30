"""Lane-B wave 12: PCA gate, W72/W74/W75 row builders, W83 diversity, MC-2 PCA."""

import copy
import json
import sys
import types

import pytest

from ._l2_loader import load

pga = load("tools/w67_pca_promotion_gate.py")
sem = load("tools/w72_build_semantic_rows.py")
rt74 = load("tools/w74_build_runtime_rows.py")
dec = load("tools/w75_build_deconfounded_rows.py")
hist = load("tools/w75_build_historical_panel.py")
div = load("tools/w83_semantic_basis_diversity.py")

_PCA_RESULT = {}


def _fake_pca_block(rows, features):
    _PCA_RESULT["seen"] = (len(rows), list(features))
    return copy.deepcopy(_PCA_RESULT["value"])


topo = load(
    "tools/mc2_semantic_topology_pca.py",
    deps={"mc2_federated_telemetry": types.SimpleNamespace(pca_block=_fake_pca_block)},
)


def _sha(i):
    return "{0:040x}".format(i + 1)


def _write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")
    return path


def _argv(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["prog", *[str(a) for a in args]])


# --------------------------------------------------------------------------
# w67_pca_promotion_gate
# --------------------------------------------------------------------------


def _pca_row(i, sha=None, **over):
    row = {k: 0.1 * (i + 1) * (j + 1) % 1 for j, k in enumerate(pga.FEATURES)}
    row["registry_gap_rate"] = float(i)
    row["source_sha"] = sha if sha is not None else _sha(i)
    row.update(over)
    return row


def test_numeric():
    assert pga.numeric(_pca_row(0))
    assert not pga.numeric(_pca_row(0, graph_drop_rate="x"))
    assert not pga.numeric(_pca_row(0, graph_drop_rate=float("nan")))


def test_standardize_constant_column():
    rows = [_pca_row(i, lineage_gap_rate=0.5) for i in range(3)]
    z = pga.standardize(rows)
    assert [r[4] for r in z] == [0.0, 0.0, 0.0]
    assert z[0][0] == pytest.approx(-1.0)


def test_power_on_zero_matrix():
    eig, v = pga.power([[0.0] * 5 for _ in range(5)], iters=2)
    assert eig == 0.0 and v == [0.0] * 5


def test_pca_gate_pass(tmp_path, monkeypatch, capsys):
    paths = [
        _write_json(tmp_path / "r{0}.json".format(i), _pca_row(i)) for i in range(3)
    ]
    paths.append(_write_json(tmp_path / "bad.json", _pca_row(9, graph_drop_rate=None)))
    out = tmp_path / "rcpt.json"
    _argv(monkeypatch, *paths, "--out", out)
    pga.main()
    data = json.loads(out.read_text())
    assert data["promotion"] == "PASS"
    assert data["rows_seen"] == 4 and data["numeric_comparable_rows"] == 3
    assert data["worker_allocation_mode"] == "PCA_REVERSE_LOADING"
    assert set(data["reverse_loading_rank"]) == set(pga.FEATURES)
    assert 0 < data["pc1_explained_variance_ratio"] <= 1
    assert json.loads(capsys.readouterr().out)["promotion"] == "PASS"


def test_pca_gate_zero_variance(tmp_path, monkeypatch):
    rows = [{k: 0.5 for k in pga.FEATURES} | {"source_sha": _sha(i)} for i in range(3)]
    paths = [
        _write_json(tmp_path / "r{0}.json".format(i), r) for i, r in enumerate(rows)
    ]
    out = tmp_path / "rcpt.json"
    _argv(monkeypatch, *paths, "--out", out)
    pga.main()
    data = json.loads(out.read_text())
    assert data["promotion"] == "PASS"
    assert data["pc1_explained_variance_ratio"] == 0.0


def test_pca_gate_withheld(tmp_path, monkeypatch):
    rows = [_pca_row(0), _pca_row(1, sha=_sha(0)), _pca_row(2, sha="")]
    paths = [
        _write_json(tmp_path / "r{0}.json".format(i), r) for i, r in enumerate(rows)
    ]
    out = tmp_path / "rcpt.json"
    _argv(monkeypatch, *paths, "--out", out)
    pga.main()
    data = json.loads(out.read_text())
    assert data["promotion"] == "WITHHELD"
    assert data["distinct_source_shas"] == 1
    assert "pc1_loadings" not in data


# --------------------------------------------------------------------------
# w72_build_semantic_rows
# --------------------------------------------------------------------------


def _sem_feature(i, **over):
    row = {k: 0.25 for k in sem.FEATURES}
    row["measurement_schema"] = sem.EXPECTED_SCHEMA
    row["source_sha"] = _sha(i)
    row.update(over)
    return row


def test_finite():
    assert sem.finite(1) and sem.finite(0.5)
    assert not sem.finite(True)
    assert not sem.finite(float("inf"))
    assert not sem.finite("1")


def test_semantic_rows_main(tmp_path, monkeypatch, capsys):
    paths = [
        _write_json(tmp_path / "f{0}.json".format(i), _sem_feature(i)) for i in (2, 0)
    ]
    out = tmp_path / "rows.json"
    _argv(monkeypatch, *paths, "--out", out)
    sem.main()
    rows = json.loads(out.read_text())
    assert [r["source_sha"] for r in rows] == [_sha(0), _sha(2)]
    assert rows[0]["row_id"] == "SEM-W72-" + _sha(0)[:12]
    assert rows[0]["graph_drop_rate"] == 0.25
    assert json.loads(capsys.readouterr().out) == {"distinct_source_shas": 2, "rows": 2}


@pytest.mark.parametrize(
    "rows, match",
    [
        (
            [_sem_feature(0, measurement_schema="OTHER")],
            "incompatible measurement schema",
        ),
        ([_sem_feature(0, source_sha="ABC")], "exact 40-char lowercase hex"),
        ([_sem_feature(0), _sem_feature(0)], "duplicate source_sha"),
        ([_sem_feature(0, lineage_gap_rate=1.5)], "invalid lineage_gap_rate"),
        ([_sem_feature(0, registry_gap_rate=None)], "invalid registry_gap_rate"),
    ],
)
def test_semantic_rows_rejections(tmp_path, monkeypatch, rows, match):
    paths = [
        _write_json(tmp_path / "f{0}.json".format(i), r) for i, r in enumerate(rows)
    ]
    _argv(monkeypatch, *paths, "--out", tmp_path / "o.json")
    with pytest.raises(ValueError, match=match):
        sem.main()


# --------------------------------------------------------------------------
# w74_build_runtime_rows
# --------------------------------------------------------------------------

CREATED = "2026-01-01T00:00:00Z"


def _job(name, job_id, **over):
    job = {
        "name": name,
        "id": job_id,
        "started_at": "2026-01-01T00:00:10Z",
        "completed_at": "2026-01-01T00:01:10Z",
        "runner_id": 7,
        "conclusion": "success",
        "steps": [
            {"conclusion": "success"},
            {"conclusion": "skipped"},
            {"conclusion": None},
        ],
    }
    job.update(over)
    return job


def _w74_setup(tmp_path, count=5, job_over=None, dup_sha=False):
    probes = tmp_path / "probes"
    jobs = []
    for i in range(count):
        label = "h{0}".format(i + 1)
        sha = _sha(0 if dup_sha else i)
        _write_json(
            probes / label / "PROBE_RECEIPT.json",
            {"source_sha": sha, "matrix_label": label},
        )
        over = (job_over or {}).get(i, {})
        job = _job("w74-runtime-" + label, 100 + i)
        job.update(over)
        jobs.append(job)
    jobs_json = _write_json(tmp_path / "jobs.json", {"jobs": jobs})
    return jobs_json, probes


def _w74_argv(monkeypatch, tmp_path, jobs_json, probes):
    out = tmp_path / "rows.json"
    _argv(
        monkeypatch,
        "--jobs-json",
        jobs_json,
        "--probe-root",
        probes,
        "--run-created-at",
        CREATED,
        "--run-id",
        "42",
        "--repo",
        "o/r",
        "--out",
        out,
    )
    return out


def test_w74_parse_time():
    assert rt74.parse_time("2026-01-01T00:00:00Z").utcoffset().total_seconds() == 0


def test_w74_main(tmp_path, monkeypatch, capsys):
    jobs_json, probes = _w74_setup(
        tmp_path, job_over={0: {"started_at": "2025-12-31T23:59:00Z"}}
    )
    out = _w74_argv(monkeypatch, tmp_path, jobs_json, probes)
    rt74.main()
    rows = json.loads(out.read_text())
    assert len(rows) == 5
    first = rows[0]
    assert first["source_sha"] == _sha(0)
    assert first["queue_seconds_mean"] == 0.0
    assert first["execute_seconds_total"] == 130.0
    assert first["steps_executed_total"] == 1
    assert first["evidence_reference"].endswith("/repos/o/r/actions/runs/42/jobs")
    assert rows[1]["queue_seconds_mean"] == 10.0
    assert json.loads(capsys.readouterr().out)["rows"] == 5


@pytest.mark.parametrize(
    "kwargs, match",
    [
        ({"count": 0}, "no W74 probe receipts found"),
        (
            {"job_over": {1: {"name": "other"}}},
            "missing job metadata for w74-runtime-h2",
        ),
        ({"job_over": {0: {"runner_id": None}}}, "NOT_EXECUTED"),
        ({"job_over": {0: {"steps": None}}}, "NOT_EXECUTED"),
        ({"count": 4}, ">=5 unique exact-SHA"),
        ({"dup_sha": True}, ">=5 unique exact-SHA"),
        ({"job_over": {2: {"conclusion": "FAILURE"}}}, "contains a failed execution"),
        ({"job_over": {2: {"conclusion": None}}}, "contains a failed execution"),
    ],
)
def test_w74_rejections(tmp_path, monkeypatch, kwargs, match):
    jobs_json, probes = _w74_setup(tmp_path, **kwargs)
    probes.mkdir(exist_ok=True)
    _w74_argv(monkeypatch, tmp_path, jobs_json, probes)
    with pytest.raises(ValueError, match=match):
        rt74.main()


# --------------------------------------------------------------------------
# w75_build_deconfounded_rows
# --------------------------------------------------------------------------


def _w75_setup(tmp_path, mutate=None):
    """Write 15 receipts (5 SHAs x 3 repeats) and the matching jobs payload."""
    receipts = []
    for repeat in (1, 2, 3):
        for i in range(5):
            receipts.append(
                {
                    "source_sha": _sha(i),
                    "matrix_label": "h{0}".format(i + 1),
                    "repeat": repeat,
                    "probe_execute_seconds": 20.0,
                }
            )
    jobs = {}
    for idx, rc in enumerate(receipts):
        name = "w75-r{0}-{1}".format(rc["repeat"], rc["matrix_label"])
        jobs[name] = _job(name, 500 + idx)
    if mutate:
        mutate(receipts, jobs)
    probes = tmp_path / "probes"
    for idx, rc in enumerate(receipts):
        _write_json(probes / "p{0:02d}".format(idx) / "PROBE_RECEIPT.json", rc)
    probes.mkdir(exist_ok=True)
    jobs_json = _write_json(tmp_path / "jobs.json", {"jobs": list(jobs.values())})
    return jobs_json, probes


def test_w75_deconfounded_main(tmp_path, monkeypatch, capsys):
    def mutate(receipts, jobs):
        receipts[0]["probe_execute_seconds"] = 500.0

    jobs_json, probes = _w75_setup(tmp_path, mutate)
    out = _w74_argv(monkeypatch, tmp_path, jobs_json, probes)
    dec.main()
    rows = json.loads(out.read_text())
    assert len(rows) == 15
    assert [(r["repeat"], r["source_sha"]) for r in rows[:2]] == [
        (1, _sha(0)),
        (1, _sha(1)),
    ]
    assert rows[0]["orchestration_overhead_seconds"] == 0.0
    assert rows[1]["orchestration_overhead_seconds"] == 40.0
    assert rows[1]["row_id"] == "RUN-W75-R1-" + _sha(1)[:12]
    assert json.loads(capsys.readouterr().out)["repeats"] == {"1": 5, "2": 5, "3": 5}


def _set(index, key, value):
    def mutate(receipts, jobs):
        receipts[index][key] = value

    return mutate


def _job_set(name, key, value):
    def mutate(receipts, jobs):
        jobs[name][key] = value

    return mutate


def _drop_receipt(receipts, jobs):
    receipts.pop()


def _dup_key(receipts, jobs):
    # Same SHA/repeat as receipt 0 but a different label -> 15 rows, 14 keys.
    receipts[1]["source_sha"] = receipts[0]["source_sha"]


def _sixth_sha(receipts, jobs):
    receipts[14]["source_sha"] = _sha(9)


@pytest.mark.parametrize(
    "mutate, match",
    [
        (lambda r, j: r.clear(), "no W75 probe receipts found"),
        (_set(0, "source_sha", "XYZ"), "invalid source SHA"),
        (_set(0, "matrix_label", "h9"), "invalid W75 job identity"),
        (lambda r, j: j.pop("w75-r1-h1"), "missing job metadata for w75-r1-h1"),
        (_job_set("w75-r1-h1", "runner_id", 0), "NOT_EXECUTED"),
        (_job_set("w75-r1-h1", "steps", []), "NOT_EXECUTED"),
        (_job_set("w75-r1-h1", "conclusion", "failure"), "did not succeed"),
        (_job_set("w75-r1-h1", "conclusion", None), "did not succeed"),
        (_set(0, "probe_execute_seconds", -1), "negative intrinsic probe time"),
        (_drop_receipt, "exactly 15 rows, observed 14"),
        (_dup_key, "unique SHA x repeat observations"),
        (_sixth_sha, "five exact SHAs with three repeats each"),
    ],
)
def test_w75_deconfounded_rejections(tmp_path, monkeypatch, mutate, match):
    jobs_json, probes = _w75_setup(tmp_path, mutate)
    _w74_argv(monkeypatch, tmp_path, jobs_json, probes)
    with pytest.raises(ValueError, match=match):
        dec.main()


# --------------------------------------------------------------------------
# w75_build_historical_panel
# --------------------------------------------------------------------------


def _hist_setup(tmp_path, mutate=None):
    """Build manifest + artifact members for 3 runs x 5 SHAs."""
    root = tmp_path / "evidence"
    runs = []
    members = {}
    art = 1000
    for repeat in (3, 1, 2):
        run_id = 9000 + repeat
        paired_id = art
        art += 1
        paired_rows = []
        probes = []
        for i in range(5):
            sha = _sha(i)
            paired_rows.append(
                {
                    "source_sha": sha,
                    "execution_state": "PASS",
                    "runner_id": 3,
                    "steps_executed_total": 4,
                    "execute_seconds_total": 30.0,
                    "evidence_reference": "https://x/actions/runs/{0}/jobs".format(
                        run_id
                    ),
                }
            )
            probe_id = art
            art += 1
            label = "h{0}".format(i + 1)
            probes.append(
                {
                    "source_sha": sha,
                    "artifact_id": probe_id,
                    "expected_member": "PROBE_RECEIPT.json",
                    "label": label,
                    "digest": "sha256:p{0}".format(probe_id),
                }
            )
            members[(probe_id, "PROBE_RECEIPT.json")] = {
                "source_sha": sha,
                "matrix_label": label,
                "probe_execute_seconds": 10.0 if i else 45.0,
            }
        members[(paired_id, "rows.json")] = paired_rows
        runs.append(
            {
                "repeat": repeat,
                "run_id": run_id,
                "control_head_sha": "c" * 40,
                "paired_artifact": {
                    "artifact_id": paired_id,
                    "expected_member": "rows.json",
                    "digest": "sha256:r{0}".format(paired_id),
                },
                "probes": probes,
            }
        )
    manifest = {"runs": runs}
    if mutate:
        mutate(manifest, members)
    for (aid, member), payload in members.items():
        _write_json(root / "artifact-{0}".format(aid) / member, payload)
    root.mkdir(exist_ok=True)
    mpath = _write_json(tmp_path / "manifest.json", manifest)
    out = tmp_path / "panel.json"
    return ["--manifest", mpath, "--evidence-root", root, "--out", out], out


def _run_of(manifest, repeat):
    return next(r for r in manifest["runs"] if r["repeat"] == repeat)


def _paired(manifest, members, repeat):
    pa = _run_of(manifest, repeat)["paired_artifact"]
    return members[(pa["artifact_id"], pa["expected_member"])]


def _probe_payload(manifest, members, repeat, index):
    pm = _run_of(manifest, repeat)["probes"][index]
    return members[(pm["artifact_id"], pm["expected_member"])]


def test_artifact_member_missing(tmp_path):
    with pytest.raises(ValueError, match="missing artifact member"):
        hist.artifact_member(tmp_path, 1, "x.json")


def test_historical_panel_main(tmp_path, monkeypatch, capsys):
    args, out = _hist_setup(tmp_path)
    _argv(monkeypatch, *args)
    hist.main()
    rows = json.loads(out.read_text())
    assert len(rows) == 15
    assert [r["repeat"] for r in rows] == [1] * 5 + [2] * 5 + [3] * 5
    first = rows[0]
    assert first["source_sha"] == _sha(0)
    assert first["source_run_id"] == 9001
    assert first["orchestration_overhead_seconds"] == 0.0
    assert rows[1]["orchestration_overhead_seconds"] == 20.0
    assert first["paired_artifact_digest"].startswith("sha256:r")
    assert json.loads(capsys.readouterr().out)["repeats"] == {"1": 5, "2": 5, "3": 5}


def _m_runs(n):
    def mutate(manifest, members):
        manifest["runs"] = manifest["runs"][:n]

    return mutate


def _m_no_runs(manifest, members):
    manifest.pop("runs")


def _m_missing_paired(manifest, members):
    _run_of(manifest, 1)["paired_artifact"]["expected_member"] = "nope.json"


def _m_short_paired(manifest, members):
    _paired(manifest, members, 1).pop()


def _m_dup_paired(manifest, members):
    rows = _paired(manifest, members, 1)
    rows[1] = dict(rows[0])


def _m_no_probe(manifest, members):
    _paired(manifest, members, 1)[0]["source_sha"] = _sha(20)


def _m_probe_sha(manifest, members):
    _probe_payload(manifest, members, 1, 0)["source_sha"] = _sha(30)


def _m_probe_label(manifest, members):
    _probe_payload(manifest, members, 1, 0)["matrix_label"] = "h9"


def _m_row(key, value):
    def mutate(manifest, members):
        _paired(manifest, members, 1)[0][key] = value

    return mutate


def _m_repeat_twice(manifest, members):
    # Two runs claim repeat 1 with disjoint SHAs -> 15 rows, unbalanced repeats.
    run = _run_of(manifest, 2)
    for i, row in enumerate(_paired(manifest, members, 2)):
        row["source_sha"] = _sha(40 + i)
        run["probes"][i]["source_sha"] = _sha(40 + i)
        _probe_payload(manifest, members, 2, i)["source_sha"] = _sha(40 + i)
    run["repeat"] = 1


def _m_other_shas(manifest, members):
    for i, row in enumerate(_paired(manifest, members, 3)):
        row["source_sha"] = _sha(50 + i)
        _run_of(manifest, 3)["probes"][i]["source_sha"] = _sha(50 + i)
        _probe_payload(manifest, members, 3, i)["source_sha"] = _sha(50 + i)


@pytest.mark.parametrize(
    "mutate, match",
    [
        (_m_runs(2), "exactly three runs"),
        (_m_no_runs, "exactly three runs"),
        (_m_missing_paired, "missing artifact member"),
        (_m_short_paired, "expected five paired rows and probes"),
        (_m_dup_paired, "duplicate repeat/source state"),
        (_m_no_probe, "no probe for"),
        (_m_probe_sha, "probe/source SHA mismatch"),
        (_m_probe_label, "probe label mismatch"),
        (_m_row("execution_state", "FAIL"), "historical row is not PASS"),
        (_m_row("runner_id", None), "no real runner"),
        (_m_row("steps_executed_total", 0), "executed zero steps"),
        (_m_row("evidence_reference", None), "does not bind declared run"),
        (_m_repeat_twice, "3 repeats x 5 exact SHAs"),
        (_m_other_shas, "3 repeats x 5 exact SHAs"),
    ],
)
def test_historical_panel_rejections(tmp_path, monkeypatch, mutate, match):
    args, _ = _hist_setup(tmp_path, mutate)
    _argv(monkeypatch, *args)
    with pytest.raises(ValueError, match=match):
        hist.main()


# --------------------------------------------------------------------------
# w83_semantic_basis_diversity
# --------------------------------------------------------------------------


def _div_receipt(label, vec, blocks=("a", "b", "c")):
    return {
        "matrix_label": label,
        "feature_vector": vec,
        "feature_vector_sha256": json.dumps(vec, sort_keys=True),
        "block_sha256": {
            "semantic_composition": blocks[0],
            "consumer_graph_distribution": blocks[1],
            "workflow_governance_composition": blocks[2],
        },
    }


def _div_paths(tmp_path, recent_vec=None, drop=0, bad_schema=False, extra=None):
    labels = sorted(div.EXPECTED_W79) + sorted(div.EXPECTED_RECENT)
    paths = []
    for idx, label in enumerate(labels[drop:]):
        if label in div.EXPECTED_RECENT and recent_vec is not None:
            vec = recent_vec(idx)
        else:
            vec = {"x": idx % 3, "y": 1}
        if bad_schema and idx == 5:
            vec = {"x": 1}
        receipt = _div_receipt(label, vec, blocks=("s{0}".format(idx % 2), "g", "w"))
        paths.append(_write_json(tmp_path / "r{0:02d}.json".format(idx), receipt))
    if extra:
        paths.append(_write_json(tmp_path / "extra.json", extra))
    return paths


def test_diversity_signal_present(tmp_path, monkeypatch, capsys):
    paths = _div_paths(tmp_path, recent_vec=lambda i: {"x": i, "y": 1})
    out = tmp_path / "div.json"
    _argv(monkeypatch, *paths, "--out", out)
    div.main()
    data = json.loads(out.read_text())
    assert data["status"] == "DIVERSITY_SIGNAL_PRESENT"
    assert data["recent_variable_features"] == ["x"]
    assert data["groups"]["all_states"]["state_count"] == 21
    assert data["groups"]["w79_historical"]["unique_semantic_composition"] == 2
    assert data["feature_ranges_all_states"]["y"] == {"min": 1, "max": 1, "distinct": 1}
    assert json.loads(capsys.readouterr().out)["pca_fit_performed"] is False


def test_diversity_saturated(tmp_path, monkeypatch):
    paths = _div_paths(tmp_path, recent_vec=lambda i: {"x": 7, "y": 7})
    out = tmp_path / "div.json"
    _argv(monkeypatch, *paths, "--out", out)
    div.main()
    data = json.loads(out.read_text())
    assert data["status"] == "RECENT_BASIS_STILL_SATURATED"
    assert data["recent_variable_feature_count"] == 0


@pytest.mark.parametrize(
    "kwargs, match",
    [
        ({"drop": 1}, "exactly 21 unique predeclared states"),
        (
            {"extra": _div_receipt("s01", {"x": 0, "y": 1})},
            "exactly 21 unique predeclared states",
        ),
        ({"bad_schema": True}, "feature schema drift"),
    ],
)
def test_diversity_rejections(tmp_path, monkeypatch, kwargs, match):
    paths = _div_paths(tmp_path, **kwargs)
    _argv(monkeypatch, *paths, "--out", tmp_path / "o.json")
    with pytest.raises(SystemExit, match=match):
        div.main()


# --------------------------------------------------------------------------
# mc2_semantic_topology_pca
# --------------------------------------------------------------------------


def _topo_row(**over):
    row = {"observation_class": "semantic_topology"}
    row.update({k: 0.5 for k in topo.FEATURES})
    row.update(over)
    return row


def _measured(sign):
    return {
        "status": "MEASURED_PCA_DIAGNOSTIC",
        "components": [
            {"pc": 2, "loadings": {"consumer_edge_density": 0.25}},
            {"pc": 1, "loadings": {"consumer_penetration_rate": sign * 0.8}},
        ],
    }


def test_topology_finite():
    assert topo.finite(0) and not topo.finite(False) and not topo.finite(float("nan"))


@pytest.mark.parametrize(
    "pca, expected_pc1",
    [
        (_measured(-1), 0.8),
        (_measured(1), 0.8),
        (
            {
                "status": "MEASURED_PCA_DIAGNOSTIC",
                "components": [{"pc": 1, "loadings": {}}],
            },
            None,
        ),
        ({"status": "WITHHELD", "reason": "INSUFFICIENT_COMPARABLE_ROWS"}, None),
    ],
)
def test_topology_main(tmp_path, monkeypatch, capsys, pca, expected_pc1):
    _PCA_RESULT["value"] = pca
    rows = _write_json(tmp_path / "rows.json", [_topo_row(), _topo_row()])
    out = tmp_path / "pca.json"
    _argv(monkeypatch, rows, "--out", out)
    topo.main()
    data = json.loads(out.read_text())
    assert _PCA_RESULT["seen"] == (2, topo.FEATURES)
    assert data["rows_total"] == 2
    assert len(data["receipt_sha256"]) == 64
    semantic = data["semantic_pca"]
    if expected_pc1 is not None:
        pc1 = next(c for c in semantic["components"] if c["pc"] == 1)
        assert pc1["loadings"]["consumer_penetration_rate"] == expected_pc1
        pc2 = next(c for c in semantic["components"] if c["pc"] == 2)
        assert abs(pc2["loadings"]["consumer_edge_density"]) == 0.25
    else:
        assert semantic == pca
    assert json.loads(capsys.readouterr().out)["bt_status"].startswith("WITHHELD")


def test_topology_flip_negates_all_components(tmp_path, monkeypatch):
    _PCA_RESULT["value"] = _measured(-1)
    rows = _write_json(tmp_path / "rows.json", [_topo_row()])
    out = tmp_path / "pca.json"
    _argv(monkeypatch, rows, "--out", out)
    topo.main()
    comps = json.loads(out.read_text())["semantic_pca"]["components"]
    assert comps[0]["loadings"] == {"consumer_edge_density": -0.25}


@pytest.mark.parametrize(
    "payload, match",
    [
        ({"not": "list"}, "rows root must be a list"),
        ([_topo_row(observation_class="runtime")], "row 0: wrong observation_class"),
        (
            [_topo_row(), _topo_row(consumer_edge_density=2)],
            "row 1: invalid consumer_edge",
        ),
        ([_topo_row(consumer_degree_concentration=True)], "invalid consumer_degree"),
    ],
)
def test_topology_rejections(tmp_path, monkeypatch, payload, match):
    rows = _write_json(tmp_path / "rows.json", payload)
    _argv(monkeypatch, rows, "--out", tmp_path / "o.json")
    with pytest.raises(ValueError, match=match):
        topo.main()
