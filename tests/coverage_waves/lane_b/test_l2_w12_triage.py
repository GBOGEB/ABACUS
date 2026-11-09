"""Lane-B wave 12: triage census, floating-anchor census and CReq federation."""

import hashlib
import json
import sys
from pathlib import Path, PurePosixPath

import pytest
import yaml

from ._l2_loader import REPO_ROOT, load

fac = load("tools/triage/floating_anchor_census.py")
gate = load("triage/requirements/creq_ci_gate.py")
resolver = load("triage/requirements/creq_resolver.py")
census = load("triage/run_repo_census.py")

REGISTRY = REPO_ROOT / "triage/requirements/GLOBAL_CREQ_REGISTRY.json"
OVERLAY = REPO_ROOT / "triage/requirements/ABACUS_CREQ_OVERLAY.json"
ROLES = (
    "local_repo_owner",
    "parent_cADR_or_cOCD_authority",
    "global_CReq_authority",
)


def _json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(data).encode("utf-8"))
    return path


def _chain(state="APPROVED", roles=ROLES):
    return [{"role": role, "state": state} for role in roles]


# ---------------------------------------------------------------------------
# floating_anchor_census
# ---------------------------------------------------------------------------


def test_fac_iter_files_skips_excluded_dirs(tmp_path):
    for rel in ("a/engine.py", ".git/HEAD", "x/node_modules/y.js", "top.md"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x", encoding="utf-8")
    assert sorted(fac.iter_files(tmp_path)) == [Path("a/engine.py"), Path("top.md")]


@pytest.mark.parametrize(
    "path, anchor, expected",
    [
        ("src/keb/engine.py", "KEB", True),
        ("src/keb_engine.py", "keb", True),
        ("src/kebab_engine.py", "keb", False),
        ("src/dowry.py", "DOW", False),
    ],
)
def test_fac_linked_by_path(path, anchor, expected):
    assert fac.linked_by_path(path, anchor) is expected


@pytest.mark.parametrize(
    "path, bucket",
    [
        ("x/workflows-pending/deploy.yml", "staged_workflow"),
        ("workflows-to-install/ci.yml", "staged_workflow"),
        ("tools_v2.3/pipeline.py", "embedded_version_or_subrepo"),
        ("a/repo_snapshot/runner.py", "embedded_version_or_subrepo"),
        ("local_mcp/engine.py", "runtime_agent_surface"),
        ("src/keb/x.py", "runtime_agent_surface"),
        ("docs/pipeline_handover.md", "status_or_handover_needs_review"),
        ("lib/engine.py", "engine_like_unlinked"),
    ],
)
def test_fac_classify_path(path, bucket):
    assert fac.classify_path(path) == bucket


FAC_PATHS = [
    "keb/engine.py",
    "keb/notes.txt",
    "lib/engine.py",
    "lib/plain.txt",
    "local_mcp/runner.py",
    "docs/deploy_report.md",
]


def test_fac_build_report(tmp_path, monkeypatch):
    monkeypatch.setattr(
        fac, "iter_files", lambda root: [PurePosixPath(p) for p in FAC_PATHS]
    )
    report = fac.build_report(tmp_path, "GBOGEB/ABACUS", "keb")
    assert report["anchor"] == "KEB"
    assert report["totals"] == {
        "files": 6,
        "anchor_named_files": 2,
        "engine_like_files": 4,
        "anchor_named_engine_like_files": 1,
        "verified_linked_engine_like_files": None,
        "floating_engine_like_files": 3,
    }
    assert report["top_roots"] == [
        ("keb", 2),
        ("lib", 2),
        ("docs", 1),
        ("local_mcp", 1),
    ]
    assert report["floating_buckets"] == {
        "engine_like_unlinked": {"count": 1, "paths": ["lib/engine.py"]},
        "runtime_agent_surface": {"count": 1, "paths": ["local_mcp/runner.py"]},
        "status_or_handover_needs_review": {
            "count": 1,
            "paths": ["docs/deploy_report.md"],
        },
    }
    assert report["anchor_named_engine_paths"] == ["keb/engine.py"]
    assert report["control"]["engineering_credit"] is False


def _fac_tree(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "keb_engine.py").write_text("x", encoding="utf-8")
    (root / "runner.py").write_text("x", encoding="utf-8")
    return root


def test_fac_main_stdout(tmp_path, monkeypatch, capsys):
    root = _fac_tree(tmp_path)
    argv = ["fac", "--root", str(root), "--repo", "r", "--anchor", "keb"]
    monkeypatch.setattr(sys, "argv", argv)
    assert fac.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["totals"]["floating_engine_like_files"] == 1
    assert report["floating_buckets"]["engine_like_unlinked"]["paths"] == ["runner.py"]


def test_fac_main_writes_out(tmp_path, monkeypatch, capsys):
    root = _fac_tree(tmp_path)
    out = tmp_path / "o" / "census.json"
    argv = ["fac", "--root", str(root), "--repo", "r", "--anchor", "DOW"]
    monkeypatch.setattr(sys, "argv", argv + ["--out", str(out)])
    assert fac.main() == 0
    assert capsys.readouterr().out == ""
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["anchor"] == "DOW"
    assert report["totals"]["floating_engine_like_files"] == 2


# ---------------------------------------------------------------------------
# creq_resolver
# ---------------------------------------------------------------------------


def _registry(*ids):
    return {"requirements": [{"id": i, "title": "T" + i} for i in ids]}


def _overlay(*items):
    return {"repo": "GBOGEB/ABACUS", "requirements": list(items)}


def test_resolver_committed_inputs():
    receipt = resolver.resolve(resolver.load(REGISTRY), resolver.load(OVERLAY))
    rows = {row["effective_id"]: row for row in receipt["effective_requirements"]}
    assert rows["CReq_004"]["source"] == "global_fallback"
    assert rows["CReq_004"]["blocked_override"] == "CReq_ABACUS_001"
    assert "CReq_ABACUS_001" not in rows
    assert receipt["warnings"] == [
        "CReq_ABACUS_001 override blocked: approval chain incomplete"
    ]
    body = {k: v for k, v in receipt.items() if k != "sha256"}
    assert (
        receipt["sha256"]
        == hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )


def test_resolver_override_addition_and_globals():
    overlay = _overlay(
        {
            "id": "CReq_ABACUS_001",
            "mode": "override",
            "overrides": "CReq_001",
            "title": "local",
            "approval_state": "APPROVED",
            "approval_chain": _chain(),
        },
        {
            "id": "CReq_ABACUS_002",
            "parent_global_requirement": "CReq_002",
            "title": "add",
        },
        {"id": "CReq_ABACUS_003", "title": "orphan add"},
    )
    receipt = resolver.resolve(_registry("CReq_001", "CReq_002", "CReq_003"), overlay)
    got = [
        (row["effective_id"], row["source"])
        for row in receipt["effective_requirements"]
    ]
    assert got == [
        ("CReq_003", "global"),
        ("CReq_ABACUS_001", "approved_local_override"),
        ("CReq_ABACUS_002", "local_addition"),
        ("CReq_ABACUS_003", "local_addition"),
    ]
    assert receipt["warnings"] == []


@pytest.mark.parametrize(
    "item",
    [
        {"approval_state": "PROPOSED", "approval_chain": _chain()},
        {"approval_state": "APPROVED", "approval_chain": _chain(roles=ROLES[:2])},
        {"approval_state": "APPROVED"},
    ],
)
def test_resolver_approval_incomplete(item):
    assert resolver.approval_complete(item) is False


@pytest.mark.parametrize(
    "registry, overlay, match",
    [
        (_registry("CReq_1"), _overlay(), "invalid global id CReq_1"),
        (_registry("CReq_001", "CReq_001"), _overlay(), "duplicate global id"),
        (_registry("CReq_001"), _overlay({"id": "X_001"}), "invalid local id"),
        (
            _registry("CReq_001"),
            _overlay({"id": "CReq_A_001", "title": "t"}, {"id": "CReq_A_001"}),
            "duplicate local id",
        ),
        (
            _registry("CReq_001"),
            _overlay({"id": "CReq_A_001", "overrides": "CReq_009"}),
            "unknown global parent CReq_009",
        ),
    ],
)
def test_resolver_rejections(registry, overlay, match):
    with pytest.raises(ValueError, match=match):
        resolver.resolve(registry, overlay)


def test_resolver_main(tmp_path, monkeypatch, capsys):
    out = tmp_path / "res.json"
    argv = ["r", "--global-registry", str(REGISTRY), "--overlay", str(OVERLAY)]
    monkeypatch.setattr(sys, "argv", argv + ["--out", str(out)])
    resolver.main()
    printed = capsys.readouterr().out
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert "CReq resolution: PASS" in printed
    assert "WARN: CReq_ABACUS_001 override blocked" in printed
    assert "sha256=" + receipt["sha256"] in printed


# ---------------------------------------------------------------------------
# creq_ci_gate
# ---------------------------------------------------------------------------


def test_gate_repo_ns_and_load(tmp_path):
    assert gate.repo_ns("GBOGEB/pipeline-automation-hub") == "PIPELINE"
    assert gate.load(_json(tmp_path / "a.json", {"k": 1})) == {"k": 1}


def test_gate_committed_registry_digest_pinned():
    assert hashlib.sha256(REGISTRY.read_bytes()).hexdigest() == (
        gate.EXPECTED_REGISTRY_SHA256
    )


def _receipt_file(tmp_path, **kw):
    data = {"approval_state": "APPROVED", "approval_chain": _chain()}
    data.update(kw)
    return _json(tmp_path / "approval.json", data)


def _item(**kw):
    item = {"id": "CReq_ABACUS_001", "approval_state": "APPROVED"}
    item["approval_receipt"] = "approval.json"
    item.update(kw)
    return item


def test_gate_check_approval_passes(tmp_path):
    assert gate.check_approval({"id": "x", "approval_state": "PROPOSED"}, tmp_path) is (
        False
    )
    _receipt_file(tmp_path, expires_at="2999-01-01T00:00:00Z")
    assert gate.check_approval(_item(), tmp_path) is True
    (tmp_path / "approval.json").write_bytes(
        json.dumps({"status": "APPROVED"}).encode()
    )
    assert gate.check_approval(_item(approval_chain=_chain()), tmp_path) is True


@pytest.mark.parametrize(
    "item, receipt, match",
    [
        (_item(approval_receipt=None), None, "missing approval_receipt"),
        (_item(), None, "approval receipt not found"),
        (_item(), {"approval_state": "NO"}, "approval receipt not approved"),
        (
            _item(),
            {"approval_state": "APPROVED", "approval_chain": _chain("PROPOSED")},
            "approval roles incomplete",
        ),
        (
            _item(expires_at="2000-01-01"),
            {"approval_state": "APPROVED", "approval_chain": _chain()},
            "approval expired",
        ),
    ],
)
def test_gate_check_approval_failures(tmp_path, capsys, item, receipt, match):
    if receipt is not None:
        _json(tmp_path / "approval.json", receipt)
    with pytest.raises(SystemExit) as exc:
        gate.check_approval(item, tmp_path)
    assert exc.value.code == 1
    assert match in capsys.readouterr().out


def _fake_resolver(monkeypatch, rows=None):
    calls = []

    def fake(cmd, check):
        calls.append(cmd)
        assert check is True
        if rows is None:
            monkeypatch.setattr(sys, "argv", ["resolver", *cmd[2:]])
            resolver.main()
        else:
            out = cmd[cmd.index("--out") + 1]
            _json(Path(out), {"effective_requirements": rows})

    monkeypatch.setattr(gate.subprocess, "run", fake)
    return calls


def _run_gate(tmp_path, monkeypatch, registry=REGISTRY, overlay=OVERLAY):
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "receipts" / "ABACUS_CREQ_RESOLUTION.json"
    argv = ["gate", "--registry", str(registry), "--overlay", str(overlay)]
    argv += ["--resolver", "creq_resolver.py", "--out", str(out)]
    monkeypatch.setattr(sys, "argv", argv)
    gate.main()
    return out


def test_gate_main_committed_inputs_pass(tmp_path, monkeypatch, capsys):
    calls = _fake_resolver(monkeypatch)
    out = _run_gate(tmp_path, monkeypatch)
    assert calls[0][0] == sys.executable
    assert calls[0][1] == "creq_resolver.py"
    printed = capsys.readouterr().out
    assert "CReq federation CI: PASS" in printed
    result = json.loads(
        (out.parent / "ABACUS_CREQ_GATE.json").read_text(encoding="utf-8")
    )
    assert result["status"] == "PASS"
    assert result["global_registry_sha256"] == gate.EXPECTED_REGISTRY_SHA256
    assert result["checked_local_count"] == 1
    assert result["effective_count"] == len(
        json.loads(out.read_text(encoding="utf-8"))["effective_requirements"]
    )


def _custom(tmp_path, monkeypatch, registry, *items):
    reg = _json(tmp_path / "in" / "reg.json", registry)
    ovl = _json(tmp_path / "in" / "ovl.json", _overlay(*items))
    digest = hashlib.sha256(reg.read_bytes()).hexdigest()
    monkeypatch.setattr(gate, "EXPECTED_REGISTRY_SHA256", digest)
    return reg, ovl


def test_gate_main_approved_override_and_addition(tmp_path, monkeypatch, capsys):
    _json(tmp_path / "approval.json", {"approval_state": "APPROVED"})
    reg, ovl = _custom(
        tmp_path,
        monkeypatch,
        _registry("CReq_001", "CReq_002"),
        {
            "id": "CReq_ABACUS_001",
            "mode": "override",
            "overrides": "CReq_001",
            "title": "o",
            "approval_state": "APPROVED",
            "approval_receipt": "approval.json",
            "approval_chain": _chain(),
        },
        {"id": "CReq_ABACUS_002", "parent_global_requirement": "CReq_002"},
    )
    _fake_resolver(
        monkeypatch,
        [
            {"effective_id": "CReq_ABACUS_001"},
            {"effective_id": "CReq_ABACUS_002"},
            {"effective_id": "CReq_002"},
        ],
    )
    _run_gate(tmp_path, monkeypatch, reg, ovl)
    assert "CReq federation CI: PASS" in capsys.readouterr().out


def _ovr(state="PROPOSED"):
    return {
        "id": "CReq_ABACUS_001",
        "mode": "override",
        "overrides": "CReq_001",
        "approval_state": state,
    }


@pytest.mark.parametrize(
    "registry, items, rows, match",
    [
        (
            _registry("CReq_001", "CReq_001"),
            [],
            None,
            "duplicate global IDs",
        ),
        (
            _registry("CReq_001"),
            [{"id": "CReq_OTHER_001"}],
            None,
            "local namespace shadowing/foreign prefix",
        ),
        (
            _registry("CReq_001"),
            [{"id": "CReq_ABACUS_001"}],
            None,
            "missing/unknown global parent",
        ),
        (
            _registry("CReq_001"),
            [{"id": "CReq_ABACUS_001", "overrides": "CReq_002"}],
            None,
            "missing/unknown global parent",
        ),
        (
            _registry("CReq_001"),
            [{"id": "CReq_ABACUS_001", "overrides": "CReq_001", "mode": "drop"}],
            None,
            "unknown mode",
        ),
        (
            _registry("CReq_001"),
            [{"id": "CReq_ABACUS_001", "parent_global_requirement": "CReq_001"}],
            [{"effective_id": "CReq_001"}],
            "addition precedence divergence",
        ),
        (
            _registry("CReq_001"),
            [_ovr()],
            [{"effective_id": "CReq_ABACUS_001"}],
            "fallback precedence divergence",
        ),
        (
            _registry("CReq_001"),
            [_ovr()],
            [{"effective_id": "CReq_001"}, {"effective_id": "CReq_ABACUS_001"}],
            "fallback precedence divergence",
        ),
    ],
)
def test_gate_main_failures(
    tmp_path, monkeypatch, capsys, registry, items, rows, match
):
    reg, ovl = _custom(tmp_path, monkeypatch, registry, *items)
    _fake_resolver(monkeypatch, rows or [])
    with pytest.raises(SystemExit) as exc:
        _run_gate(tmp_path, monkeypatch, reg, ovl)
    assert exc.value.code == 1
    assert match in capsys.readouterr().out


@pytest.mark.parametrize(
    "rows",
    [
        [{"effective_id": "CReq_001"}],
        [{"effective_id": "CReq_ABACUS_001"}, {"effective_id": "CReq_001"}],
    ],
)
def test_gate_main_approved_override_divergence(tmp_path, monkeypatch, capsys, rows):
    _json(tmp_path / "approval.json", {"approval_state": "APPROVED"})
    item = _ovr("APPROVED")
    item.update(approval_receipt="approval.json", approval_chain=_chain())
    reg, ovl = _custom(tmp_path, monkeypatch, _registry("CReq_001"), item)
    _fake_resolver(monkeypatch, rows)
    with pytest.raises(SystemExit):
        _run_gate(tmp_path, monkeypatch, reg, ovl)
    assert "approved override precedence divergence" in capsys.readouterr().out


def test_gate_main_registry_digest_drift(tmp_path, monkeypatch, capsys):
    reg = _json(tmp_path / "reg.json", _registry("CReq_001"))
    with pytest.raises(SystemExit):
        _run_gate(tmp_path, monkeypatch, reg, OVERLAY)
    digest = hashlib.sha256(reg.read_bytes()).hexdigest()
    assert "global registry digest drift: " + digest in capsys.readouterr().out


# ---------------------------------------------------------------------------
# run_repo_census
# ---------------------------------------------------------------------------

CENSUS_REG = {
    "repository": "GBOGEB/ABACUS",
    "role": "ANALYTICAL_RUNTIME",
    "canonical_roots": [
        {"path": "src/", "state": "CANONICAL_ACTIVE"},
        {"path": "src/deep", "state": "ACTIVE_COMPATIBILITY"},
        {"path": "ssot"},
        "not-a-dict",
        {"state": "CANONICAL_ACTIVE"},
    ],
    "generated_roots": None,
}


@pytest.mark.parametrize(
    "path, expected",
    [
        ("src/a.py", "CANONICAL_ACTIVE"),
        ("src", "CANONICAL_ACTIVE"),
        ("src/deep/b.py", "ACTIVE_COMPATIBILITY"),
        ("ssot/x.yaml", "UNKNOWN"),
        ("srcx/a.py", "UNKNOWN"),
        ("ABACUS-v031/a.py", "HISTORICAL"),
        ("legacy/a.py", "HISTORICAL"),
        ("x/archive/a.py", "HISTORICAL"),
        ("x/deprecated_a.py", "HISTORICAL"),
        ("x/generated/a.json", "GENERATED"),
        ("dist/a.js", "GENERATED"),
        ("docs/a.md", "DOCUMENTATION_ONLY"),
        ("docs/a.py", "UNKNOWN"),
    ],
)
def test_census_state(path, expected):
    assert census.state(path, CENSUS_REG) == expected


def test_census_pref_filters():
    assert census.pref(CENSUS_REG, "canonical_roots") == [
        ("src", "CANONICAL_ACTIVE"),
        ("src/deep", "ACTIVE_COMPATIBILITY"),
        ("ssot", "UNKNOWN"),
    ]
    assert census.pref(CENSUS_REG, "generated_roots") == []
    assert census.pref({}, "dormant_roots") == []


def test_census_rules_categories():
    rules = dict(census.RULES)
    assert rules["workflow"](".github/workflows/ci.yml")
    assert rules["test"]("tests/a.py") and rules["test"]("x/test_a.py")
    assert rules["zod"]("x/schema.ts") and not rules["zod"]("x/schema.py")
    assert rules["deployment"]("docker-compose.yml")
    assert rules["binary_output"]("a.pdf")
    assert not rules["agentic"]("plain.txt")


def test_census_git_uses_root(monkeypatch, tmp_path):
    calls = []

    def fake(cmd, cwd, text):
        calls.append((cmd, cwd, text))
        return " out \n"

    monkeypatch.setattr(census.subprocess, "check_output", fake)
    monkeypatch.setattr(census, "ROOT", tmp_path)
    assert census.git("rev-parse", "HEAD") == "out"
    assert calls == [(["git", "rev-parse", "HEAD"], tmp_path, True)]


CENSUS_FILES = [
    "src/a_ssot.py",
    "src/deep/a_ssot.py",
    "ssot/x.yaml",
    "docs/readme.md",
    "legacy/old.txt",
    "x/generated/blob.bin",
]


def _census_env(tmp_path, monkeypatch, files):
    triage = tmp_path / "triage"
    triage.mkdir()
    registry = triage / "REPO_CENSUS.yaml"
    registry.write_text(yaml.safe_dump(CENSUS_REG), encoding="utf-8")
    monkeypatch.setattr(census, "REGISTRY", registry)
    monkeypatch.setattr(census, "OUT", triage / "generated")

    def fake_git(*args):
        if args == ("ls-files",):
            return "\n".join(files)
        assert args == ("rev-parse", "HEAD")
        return "f" * 40

    monkeypatch.setattr(census, "git", fake_git)
    return triage / "generated"


def test_census_main_writes_receipt(tmp_path, monkeypatch, capsys):
    out = _census_env(tmp_path, monkeypatch, CENSUS_FILES)
    census.main()
    summary = json.loads(capsys.readouterr().out)
    assert summary["commit"] == "f" * 40
    rec = json.loads((out / "REPO_CENSUS_EXECUTED.json").read_text(encoding="utf-8"))
    assert rec["population"] == {"tracked_files": 6}
    assert rec["lifecycle"]["counts"] == {
        "ACTIVE_COMPATIBILITY": 1,
        "CANONICAL_ACTIVE": 1,
        "DOCUMENTATION_ONLY": 1,
        "GENERATED": 1,
        "HISTORICAL": 1,
        "UNKNOWN": 1,
    }
    assert rec["lifecycle"]["awake"] == 2
    assert rec["lifecycle"]["historical_dormant_docs"] == 2
    amb = rec["ambiguity"]
    assert amb["active_ssot_candidates"] == ["src/a_ssot.py", "src/deep/a_ssot.py"]
    assert amb["duplicate_active_runtime_stems"] == {
        "a_ssot": ["src/a_ssot.py", "src/deep/a_ssot.py"]
    }
    assert rec["files"][-1] == {
        "path": "x/generated/blob.bin",
        "state": "GENERATED",
        "categories": ["other"],
    }
    assert rec["category_penetration"]["runtime"]["awake_ratio"] == 1.0
    body = {k: v for k, v in rec.items() if k != "receipt_sha256"}
    assert (
        rec["receipt_sha256"]
        == hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )
    # The writer uses the platform default encoding, so read it back the same way.
    md = (out / "REPO_CENSUS_EXECUTED.md").read_text()
    assert "Tracked **6**" in md and "Duplicate active runtime stems: **1**" in md


def test_census_main_empty_repo(tmp_path, monkeypatch, capsys):
    out = _census_env(tmp_path, monkeypatch, [])
    census.main()
    rec = json.loads((out / "REPO_CENSUS_EXECUTED.json").read_text(encoding="utf-8"))
    assert rec["population"] == {"tracked_files": 0}
    assert rec["lifecycle"]["awake_ratio"] == 0
    assert rec["files"] == []
