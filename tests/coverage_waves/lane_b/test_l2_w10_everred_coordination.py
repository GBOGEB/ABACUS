"""Lane-B wave 10: everred_v3 lease coordination (registry ops, Git CAS store, CLI)."""

import copy
import json
import sys
import types

import pytest

from ._l2_loader import load

fake_fcntl = types.SimpleNamespace(
    LOCK_EX=2, LOCK_UN=8, LOCK_SH=1, flock=lambda fd, op: None
)
mt = load("tools/everred_v3/src/metrics.py")
ev = load("tools/everred_v3/src/everred.py", deps={"fcntl": fake_fcntl, "metrics": mt})
co = load("tools/everred_v3/src/coordination.py", deps={"everred": ev})

A, B = "a" * 40, "b" * 40
REPO = "GBOGEB/ABACUS"
AUTH = "https://github.com/GBOGEB/ABACUS/issues/1"


def _claim(root="root-0001", key="idem-key-0001", paths=("src/a",), **overrides):
    op = {
        "type": "claim",
        "root_id": root,
        "idempotency_key": key,
        "expected_source_sha": A,
        "paths": list(paths),
        "principal": "worker-1",
        "authority_reference": AUTH,
    }
    op.update(overrides)
    return op


def _release(root="root-0001", key="idem-key-0002", claim_id="idem-key-0001", **kw):
    op = {
        "type": "release",
        "root_id": root,
        "idempotency_key": key,
        "claim_id": claim_id,
        "release_evidence_url": "https://github.com/GBOGEB/ABACUS/pull/2",
    }
    op.update(kw)
    return op


def _claimed():
    return co.apply_operation(co.registry(REPO), _claim())


# ---------------------------------------------------------------- sane_path


@pytest.mark.parametrize("path", ["src/a.py", "a", "dir/sub/file"])
def test_sane_path_accepts_relative_posix(path):
    assert co.sane_path(path) == path


@pytest.mark.parametrize(
    "path, msg",
    [
        (None, "normalized repository-relative"),
        ("", "normalized repository-relative"),
        ("/abs", "normalized repository-relative"),
        ("a\\b", "normalized repository-relative"),
        ("C:foo", "normalized repository-relative"),
        ("a//b", "unsafe lease path segment"),
        ("a/./b", "unsafe lease path segment"),
        ("a/../b", "unsafe lease path segment"),
        ("a/", "unsafe lease path segment"),
    ],
)
def test_sane_path_rejects(path, msg):
    with pytest.raises(ev.InvalidEvidence, match=msg):
        co.sane_path(path)


def test_registry_shape():
    reg = co.registry(REPO)
    assert reg == {
        "schema": "abacus.everred.leases.v1",
        "repository": REPO,
        "generation": 0,
        "active": {},
        "released": [],
        "used_idempotency_keys": [],
    }


# ---------------------------------------------------------- apply_operation


def test_claim_records_lease_and_does_not_mutate_input():
    state = co.registry(REPO)
    before = copy.deepcopy(state)
    out = co.apply_operation(state, _claim(paths=["src/b", "src/a", "src/a"]))
    assert state == before
    assert out["generation"] == 1
    assert out["used_idempotency_keys"] == ["idem-key-0001"]
    lease = out["active"]["root-0001"]
    assert lease["paths"] == ["src/a", "src/b"]
    assert lease["claim_id"] == "idem-key-0001"
    assert lease["authority_status"] == "EXTERNALLY_REFERENCED_NOT_VALIDATED"
    assert lease["expected_source_sha"] == A


def test_second_disjoint_claim_coexists():
    state = _claimed()
    out = co.apply_operation(
        state, _claim(root="root-0002", key="idem-key-0003", paths=["docs/x"])
    )
    assert sorted(out["active"]) == ["root-0001", "root-0002"]
    assert out["generation"] == 2


def test_release_moves_lease_to_released():
    out = co.apply_operation(_claimed(), _release())
    assert out["active"] == {}
    assert out["released"] == [
        {
            "root_id": "root-0001",
            "claim_id": "idem-key-0001",
            "evidence_url": "https://github.com/GBOGEB/ABACUS/pull/2",
        }
    ]
    assert out["generation"] == 2
    assert out["used_idempotency_keys"] == ["idem-key-0001", "idem-key-0002"]


def _state_with(**changes):
    s = co.registry(REPO)
    s.update(changes)
    return s


@pytest.mark.parametrize(
    "state, op, msg",
    [
        ("nope", _claim(), "wrong lease registry schema"),
        (_state_with(schema="x"), _claim(), "wrong lease registry schema"),
        (co.registry(REPO), "nope", "invalid operation"),
        (co.registry(REPO), {"type": "steal"}, "invalid operation"),
        (_state_with(repository=5), _claim(), "missing repository"),
        (_state_with(repository="noslash"), _claim(), "missing repository"),
        (_state_with(active=[]), _claim(), "corrupt active registry"),
        (_state_with(generation=-1), _claim(), "invalid generation"),
        (_state_with(generation=True), _claim(), "invalid generation"),
        (co.registry(REPO), _claim(root="short"), "root identity required"),
        (co.registry(REPO), _claim(root=7), "root identity required"),
        (co.registry(REPO), _claim(key="short"), "idempotency required"),
        (
            _state_with(used_idempotency_keys=["idem-key-0001"]),
            _claim(),
            "duplicate idempotency key",
        ),
        (
            co.registry(REPO),
            _claim(expected_source_sha="abc"),
            "invalid source head SHA",
        ),
        (co.registry(REPO), _claim(paths=[]), "paths required"),
        (co.registry(REPO), dict(_claim(), paths="src/a"), "paths required"),
        (co.registry(REPO), _claim(paths=["/etc"]), "normalized"),
        (co.registry(REPO), _claim(principal="  "), "principal required"),
        (co.registry(REPO), _claim(principal=None), "principal required"),
        (
            co.registry(REPO),
            _claim(authority_reference="https://evil.example/x"),
            "external authority reference required",
        ),
        (
            co.registry(REPO),
            _claim(authority_reference=None),
            "external authority reference required",
        ),
        (_claimed(), _claim(key="idem-key-0009"), "root already owned"),
        (
            _claimed(),
            _claim(root="root-0002", key="idem-key-0009", paths=["src/a/deep"]),
            "overlapping mutation scope",
        ),
        (co.registry(REPO), _release(), "no active lease"),
        (_claimed(), _release(claim_id="other-claim"), "does not own active claim"),
        (
            _claimed(),
            _release(release_evidence_url="http://x"),
            "auditable evidence reference",
        ),
        (
            _claimed(),
            _release(release_evidence_url=None),
            "auditable evidence reference",
        ),
    ],
)
def test_apply_operation_rejections(state, op, msg):
    with pytest.raises(ev.InvalidEvidence, match=msg):
        co.apply_operation(copy.deepcopy(state), copy.deepcopy(op))


def test_cross_repo_contamination_rejected():
    state = _claimed()
    state["active"]["root-0001"]["repository"] = "Other/Repo"
    op = _claim(root="root-0002", key="idem-key-0009", paths=["zzz"])
    with pytest.raises(ev.InvalidEvidence, match="cross-repo registry contamination"):
        co.apply_operation(state, op)


# ------------------------------------------------------------- GitCASStore


class FakeGit:
    """Scripted stand-in for subprocess.run keyed on the git sub-command."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        code, out, err = self.responses.get(argv[3], (0, "", ""))
        return types.SimpleNamespace(returncode=code, stdout=out, stderr=err)

    def subs(self):
        return [c[0][3] for c in self.calls]


def _store(monkeypatch, tmp_path, responses):
    fake = FakeGit(responses)
    monkeypatch.setattr(co.subprocess, "run", fake)
    return co.GitCASStore(tmp_path), fake


def test_store_rejects_non_dedicated_ref(tmp_path):
    with pytest.raises(ev.InvalidEvidence, match="dedicated lease registry"):
        co.GitCASStore(tmp_path, ref="refs/heads/main")


def test_store_rejects_unsafe_remote(tmp_path):
    with pytest.raises(ev.InvalidEvidence, match="unsafe remote name"):
        co.GitCASStore(tmp_path, remote="origin;rm")


def test_store_init_resolves_root(tmp_path):
    store = co.GitCASStore(tmp_path, remote="upstream")
    assert store.root == tmp_path.resolve()
    assert store.remote == "upstream"
    assert store.ref == co.REF


def test_git_passes_args_and_raises_on_failure(monkeypatch, tmp_path):
    store, fake = _store(monkeypatch, tmp_path, {"status": (1, "", "boom" * 200)})
    with pytest.raises(ev.InvalidEvidence, match="git status failed: boom"):
        store.git("status")
    argv, kwargs = fake.calls[0]
    assert argv[:3] == ["git", "-C", str(tmp_path.resolve())]
    assert kwargs["timeout"] == 45 and kwargs["text"] is True
    res = store.git("status", ok=False)
    assert res.returncode == 1


def test_read_without_ref_returns_genesis(monkeypatch, tmp_path):
    store, fake = _store(monkeypatch, tmp_path, {"ls-remote": (0, "", "")})
    old, state = store.read(REPO)
    assert old == co.ZERO
    assert state == co.registry(REPO)
    assert fake.subs() == ["ls-remote"]


def _remote_state(state=None, sha=A):
    blob = json.dumps(state if state is not None else co.registry(REPO))
    return {
        "ls-remote": (0, sha + "\t" + co.REF + "\n", ""),
        "fetch": (0, "", ""),
        "show": (0, blob, ""),
    }


def test_read_existing_registry(monkeypatch, tmp_path):
    state = _claimed()
    store, fake = _store(monkeypatch, tmp_path, _remote_state(state))
    old, got = store.read(REPO)
    assert old == A and got == state
    assert fake.subs() == ["ls-remote", "fetch", "show"]
    assert fake.calls[2][0][-1] == A + ":registry.json"


@pytest.mark.parametrize(
    "responses, msg",
    [
        ({"ls-remote": (0, A + " r\n" + B + " r\n", "")}, "ambiguous lease ref"),
        ({"ls-remote": (0, "zzz r\n", "")}, "invalid current lease ref"),
        (dict(_remote_state(), show=(0, "{not json", "")), "invalid lease registry"),
        (
            _remote_state(co.registry("Other/Repo")),
            "unexpected registry identity",
        ),
        (
            _remote_state(dict(co.registry(REPO), schema="v0")),
            "unexpected registry identity",
        ),
    ],
)
def test_read_rejections(monkeypatch, tmp_path, responses, msg):
    store, _ = _store(monkeypatch, tmp_path, responses)
    with pytest.raises(ev.InvalidEvidence, match=msg):
        store.read(REPO)


def test_commit_without_parent(monkeypatch, tmp_path):
    store, fake = _store(
        monkeypatch,
        tmp_path,
        {
            "hash-object": (0, "blob1\n", ""),
            "mktree": (0, "tree1\n", ""),
            "commit-tree": (0, "commit1\n", ""),
        },
    )
    state = _claimed()
    assert store.commit(co.ZERO, state) == "commit1"
    assert fake.calls[0][1]["input"] == ev.stable_json(state) + "\n"
    assert fake.calls[1][1]["input"] == "100644 blob blob1\tregistry.json\n"
    commit_argv = fake.calls[2][0]
    assert "-p" not in commit_argv
    assert commit_argv[-1] == "everred: lease generation 1"


def test_commit_with_parent(monkeypatch, tmp_path):
    store, fake = _store(monkeypatch, tmp_path, {"commit-tree": (0, "c2\n", "")})
    assert store.commit(A, co.registry(REPO)) == "c2"
    argv = fake.calls[2][0]
    assert argv[argv.index("-p") + 1] == A


def test_transact_dry_run(monkeypatch, tmp_path):
    store, fake = _store(monkeypatch, tmp_path, {"ls-remote": (0, "", "")})
    out = store.transact(REPO, _claim())
    assert out["status"] == "PROPOSED_NOT_WRITTEN"
    assert out["previous_ref"] == co.ZERO
    assert out["registry"]["generation"] == 1
    assert fake.subs() == ["ls-remote"]


def test_transact_apply_from_genesis(monkeypatch, tmp_path):
    responses = {"ls-remote": (0, "", ""), "commit-tree": (0, B + "\n", "")}
    store, fake = _store(monkeypatch, tmp_path, responses)
    out = store.transact(REPO, _claim(), apply=True)
    assert out == {
        "status": "COORDINATION_COMMITTED_NOT_SOURCE_AUTHORIZATION",
        "old_ref": co.ZERO,
        "new_ref": B,
        "generation": 1,
    }
    push = fake.calls[-1][0]
    assert push[3] == "push"
    assert push[4] == "--force-with-lease=" + co.REF + ":"
    assert push[-1] == B + ":" + co.REF


def test_transact_apply_existing_ref_lease(monkeypatch, tmp_path):
    responses = _remote_state(_claimed())
    responses["commit-tree"] = (0, B + "\n", "")
    store, fake = _store(monkeypatch, tmp_path, responses)
    out = store.transact(REPO, _release(), apply=True)
    assert out["old_ref"] == A and out["generation"] == 2
    assert fake.calls[-1][0][4] == "--force-with-lease=" + co.REF + ":" + A


def test_transact_cas_rejected(monkeypatch, tmp_path):
    responses = {"ls-remote": (0, "", ""), "push": (1, "", "stale")}
    store, _ = _store(monkeypatch, tmp_path, responses)
    with pytest.raises(ev.InvalidEvidence, match="atomic lease CAS rejected"):
        store.transact(REPO, _claim(), apply=True)


# --------------------------------------------------------------------- CLI


@pytest.mark.parametrize("apply_flag", [False, True])
def test_main_cli(monkeypatch, tmp_path, capsys, apply_flag):
    op_file = tmp_path / "op.json"
    op_file.write_text(json.dumps(_claim()))
    responses = {"ls-remote": (0, "", ""), "commit-tree": (0, B + "\n", "")}
    _, fake = _store(monkeypatch, tmp_path, responses)
    argv = [
        "coordination",
        "--repo",
        REPO,
        "--checkout",
        str(tmp_path),
        "--operation",
        str(op_file),
    ]
    if apply_flag:
        argv.append("--apply")
    monkeypatch.setattr(sys, "argv", argv)
    co.main()
    out = json.loads(capsys.readouterr().out)
    if apply_flag:
        assert out["status"] == "COORDINATION_COMMITTED_NOT_SOURCE_AUTHORIZATION"
        assert "push" in fake.subs()
    else:
        assert out["status"] == "PROPOSED_NOT_WRITTEN"
        assert "push" not in fake.subs()
