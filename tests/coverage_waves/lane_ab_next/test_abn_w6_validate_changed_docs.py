"""Behaviour tests for scripts/validate_changed_docs.py (git/linters mocked)."""

from types import SimpleNamespace

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("scripts/validate_changed_docs.py", name="abn_w6_validate_changed_docs")

GH_VARS = (
    "GITHUB_EVENT_NAME",
    "GITHUB_BASE_REF",
    "GITHUB_BASE_SHA",
    "GITHUB_EVENT_BEFORE",
    "GITHUB_SHA_BEFORE",
    "GITHUB_SHA",
)
SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_M = "c" * 40


def _cp(returncode=0, stdout=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout)


class FakeGit:
    """Scriptable replacement for ``mod._run``."""

    def __init__(self, commits=(), fetchable=(), merge_base=None, handlers=None):
        self.commits = set(commits)
        self.fetchable = set(fetchable)
        self.merge_base = merge_base
        self.handlers = handlers or {}
        self.calls = []

    def __call__(self, args, check=True):
        args = list(args)
        self.calls.append(args)
        if args[:3] == ["git", "cat-file", "-e"]:
            ref = args[3][: -len("^{commit}")]
            return _cp(0 if ref in self.commits else 1)
        if args[:2] == ["git", "fetch"]:
            self.commits |= {args[-1]} & self.fetchable
            if args[-1] in self.fetchable:
                self.commits.add("origin/" + args[-1])
            return _cp(0)
        if args[:2] == ["git", "merge-base"]:
            if self.merge_base is None:
                return _cp(1)
            return _cp(0, self.merge_base + "\n")
        for key, handler in self.handlers.items():
            if tuple(args[: len(key)]) == key:
                return handler(args)
        return _cp(0, "")


@pytest.fixture
def env(monkeypatch, tmp_path):
    for name in GH_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    return monkeypatch


def _install(env, fake):
    env.setattr(mod, "_run", fake)
    return fake


def test_run_passes_repo_root_and_flags(env, tmp_path):
    seen = {}

    def fake_run(args, **kw):
        seen.update(kw)
        seen["args"] = args
        return _cp(0, "ok")

    env.setattr(mod.subprocess, "run", fake_run)
    assert mod._run(["echo", "x"], check=False).stdout == "ok"
    assert seen["cwd"] == tmp_path
    assert seen["check"] is False
    assert seen["text"] is True


def test_is_real_sha():
    assert mod._is_real_sha(SHA_A)
    assert not mod._is_real_sha("0" * 40)
    assert not mod._is_real_sha("")


def test_commit_exists_and_fetch_ref(env):
    fake = _install(env, FakeGit(commits={SHA_A}))
    assert mod._commit_exists(SHA_A)
    assert not mod._commit_exists(SHA_B)
    mod._fetch_ref("main")
    assert fake.calls[-1] == [
        "git",
        "fetch",
        "--no-tags",
        "--depth=1",
        "origin",
        "main",
    ]


def test_pr_requires_valid_base_sha(env):
    env.setenv("GITHUB_EVENT_NAME", "pull_request")
    _install(env, FakeGit())
    with pytest.raises(RuntimeError, match="valid base SHA"):
        mod._github_diff_ranges()


def test_pr_base_unresolvable_after_fetch(env):
    env.setenv("GITHUB_EVENT_NAME", "pull_request")
    env.setenv("GITHUB_BASE_SHA", SHA_A)
    fake = _install(env, FakeGit())
    with pytest.raises(RuntimeError, match="Cannot resolve PR base SHA"):
        mod._github_diff_ranges()
    assert any(call[:2] == ["git", "fetch"] for call in fake.calls)


def test_pr_merge_base_failure(env):
    env.setenv("GITHUB_EVENT_NAME", "pull_request")
    env.setenv("GITHUB_BASE_SHA", SHA_A)
    _install(env, FakeGit(fetchable={SHA_A}))
    with pytest.raises(RuntimeError, match="Cannot resolve PR merge base"):
        mod._github_diff_ranges()


def test_pr_invalid_merge_base(env):
    env.setenv("GITHUB_EVENT_NAME", "pull_request")
    env.setenv("GITHUB_BASE_SHA", SHA_A)
    _install(env, FakeGit(commits={SHA_A}, merge_base=""))
    with pytest.raises(RuntimeError, match="Invalid PR merge base"):
        mod._github_diff_ranges()
    _install(env, FakeGit(commits={SHA_A}, merge_base=SHA_M))
    with pytest.raises(RuntimeError, match="Invalid PR merge base"):
        mod._github_diff_ranges()


def test_pr_synthetic_merge_uses_first_parent(env):
    env.setenv("GITHUB_EVENT_NAME", "pull_request")
    env.setenv("GITHUB_BASE_SHA", SHA_A)
    _install(env, FakeGit(commits={SHA_A, SHA_M, "HEAD^2"}, merge_base=SHA_M))
    assert mod._github_diff_ranges() == [["HEAD^1..HEAD"]]


def test_pr_without_merge_commit_uses_merge_base(env):
    env.setenv("GITHUB_EVENT_NAME", "pull_request")
    env.setenv("GITHUB_BASE_SHA", SHA_A)
    _install(env, FakeGit(commits={SHA_A, SHA_M}, merge_base=SHA_M))
    assert mod._github_diff_ranges() == [[SHA_M + "..HEAD"]]


def test_push_ranges_from_base_and_before(env):
    env.setenv("GITHUB_EVENT_NAME", "push")
    env.setenv("GITHUB_BASE_SHA", SHA_A)
    env.setenv("GITHUB_SHA_BEFORE", SHA_B)
    env.setenv("GITHUB_SHA", "deadbeef")
    _install(env, FakeGit(commits={SHA_A, "HEAD~1"}, fetchable={SHA_B}))
    assert mod._github_diff_ranges() == [
        [SHA_A + "..deadbeef"],
        [SHA_B + "..deadbeef"],
        ["HEAD~1..HEAD"],
    ]


def test_push_skips_zero_and_unfetchable(env):
    env.setenv("GITHUB_EVENT_BEFORE", "0" * 40)
    env.setenv("GITHUB_BASE_SHA", SHA_A)
    _install(env, FakeGit())
    assert mod._github_diff_ranges() == [["HEAD~1..HEAD"]]


def test_changed_files_filters(env, tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_bytes(b"# a\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.md").write_bytes(b"x\n")
    out = "docs/a.md\nnode_modules/x.md\ndeleted.md\n"
    _install(
        env,
        FakeGit(
            commits={"HEAD~1"},
            handlers={("git", "diff", "--name-only"): lambda a: _cp(0, out)},
        ),
    )
    assert [p.as_posix() for p in mod.changed_files()] == ["docs/a.md"]


def test_changed_files_falls_through_ranges_then_raises(env):
    env.setenv("GITHUB_BASE_SHA", SHA_A)
    _install(
        env,
        FakeGit(
            commits={SHA_A, "HEAD~1"},
            handlers={("git", "diff", "--name-only"): lambda a: _cp(128)},
        ),
    )
    with pytest.raises(RuntimeError, match="Unable to determine changed files"):
        mod.changed_files()


def test_rename_origins_classifies(env):
    out = "\n".join(
        [
            "R100\told/a.md\tnew/a.md",
            "R087\told/b.md\tnew/b.md",
            "M\tdocs/c.md",
            "X\tweird",
        ]
    )

    def handler(args):
        if args[-1].startswith(SHA_A):
            return _cp(1)
        return _cp(0, out)

    env.setenv("GITHUB_BASE_SHA", SHA_A)
    _install(
        env,
        FakeGit(
            commits={SHA_A, "HEAD~1"},
            handlers={("git", "diff", "--name-status"): handler},
        ),
    )
    unchanged, origins = mod.rename_origins()
    assert unchanged == {"new/a.md"}
    assert origins == {
        "new/b.md": ("HEAD~1", "old/b.md"),
        "docs/c.md": ("HEAD~1", "docs/c.md"),
    }


def test_rename_origins_triple_dot_base_and_none(env):
    env.setattr(mod, "_github_diff_ranges", lambda: [["origin/main...HEAD"]])
    _install(
        env,
        FakeGit(handlers={("git", "diff"): lambda a: _cp(0, "M\tx.md")}),
    )
    assert mod.rename_origins() == (set(), {"x.md": ("origin/main", "x.md")})
    _install(env, FakeGit(handlers={("git", "diff"): lambda a: _cp(1)}))
    assert mod.rename_origins() == (set(), {})


def test_git_blob_encodes(env):
    _install(env, FakeGit(handlers={("git", "show"): lambda a: _cp(0, "é")}))
    assert mod._git_blob("HEAD", "a.md") == (0, "é".encode("utf-8"))


def test_markdown_rule_counts():
    out = "\n".join(
        [
            "docs\\a.md:3 MD013/line-length Line too long",
            "docs/a.md:4:2 error MD013 again",
            "docs/b.md:1 warning MD041 first line",
            "summary: 3 errors",
        ]
    )
    counts = mod.markdown_rule_counts(out)
    assert counts["docs/a.md"]["MD013"] == 2
    assert counts["docs/b.md"]["MD041"] == 1
    assert len(counts) == 2


def test_ratchet_markdown_empty(capsys):
    assert mod.ratchet_markdown([], {}) == 0
    assert "No edited pre-existing Markdown files." in capsys.readouterr().out


def test_ratchet_markdown_compares_rule_counts(env, tmp_path, capsys):
    head_out = "\n".join(
        [
            "a.md:1 MD013 long",
            "a.md:2 MD013 long",
            "b.md:1 MD009 trailing",
        ]
    )

    def lint(args):
        files = args[1:]
        if files and files[0].startswith("changed-docs-base-"):
            prefix = files[0].split("/")[0]
            assert (tmp_path / prefix / "a.md").read_bytes() == b"base a"
            return _cp(1, prefix + "/a.md:1 MD013 long\nother.md:1 MD001 x\n")
        if files == ["u.md"]:
            return _cp(1, "u.md:1 MD001 strict\n")
        return _cp(1, head_out)

    def show(args):
        if args[-1].endswith(":u.md"):
            return _cp(128, "")
        return _cp(0, "base " + args[-1].split(":")[-1].split(".")[0])

    fake = _install(
        env,
        FakeGit(handlers={("markdownlint-cli2",): lint, ("git", "show"): show}),
    )
    origins = {
        "a.md": ("HEAD~1", "a.md"),
        "b.md": ("HEAD~1", "b.md"),
        "u.md": ("HEAD~1", "u.md"),
    }
    failures = mod.ratchet_markdown(["a.md", "b.md", "u.md"], origins)
    out = capsys.readouterr().out
    assert failures == 3
    assert "New Markdown lint findings: a.md: MD013 1 -> 2" in out
    assert "New Markdown lint findings: b.md: MD009 0 -> 1" in out
    assert "Validating 1 changed Markdown (base unreadable) file(s)." in out
    assert not list(tmp_path.glob("changed-docs-base-*"))
    assert any(call[:2] == ["markdownlint-cli2", "u.md"] for call in fake.calls)


def test_ratchet_markdown_all_strict(env, tmp_path):
    _install(
        env,
        FakeGit(
            handlers={
                ("git", "show"): lambda a: _cp(1),
                ("markdownlint-cli2",): lambda a: _cp(0, ""),
            }
        ),
    )
    assert mod.ratchet_markdown(["a.md"], {"a.md": ("HEAD", "a.md")}) == 0
    assert not list(tmp_path.glob("changed-docs-base-*"))


def test_by_kind():
    paths = [
        mod.Path("a.MD"),
        mod.Path("b.yml"),
        mod.Path("c.json"),
        mod.Path("d.txt"),
    ]
    assert mod._by_kind(paths, "markdown") == ["a.MD"]
    assert mod._by_kind(paths, "yaml") == ["b.yml"]
    assert mod._by_kind(paths, "json") == ["c.json"]


def _yaml(tmp_path, name, body):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body.encode("utf-8"))
    return name


def test_validate_yaml_structure_ok_and_alias(env, tmp_path, capsys):
    good = _yaml(tmp_path, "good.yml", "a: &x\n  - 1\n  - {b: 2}\nc: *x\n")
    wf = _yaml(tmp_path, ".github/workflows/ci.yml", "on: push\njobs: {}\n")
    assert mod.validate_yaml_structure([good, wf]) == 0
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    ("name", "body", "needle"),
    [
        ("empty.yml", "", "empty YAML document"),
        ("dup.yml", "a: 1\nb: 2\na: 3\n", "duplicate YAML key 'a' at line 3"),
        ("cx.yml", "? [a, b]\n: 1\n", "complex YAML mapping key"),
        (".github/workflows/m.yml", "a: 1\n---\nb: 2\n", "one YAML document"),
        ("bad.yml", "a: [1, 2\n", "Invalid YAML structure"),
    ],
)
def test_validate_yaml_structure_failures(env, tmp_path, capsys, name, body, needle):
    _yaml(tmp_path, name, body)
    assert mod.validate_yaml_structure([name]) == 1
    assert needle in capsys.readouterr().out


def test_validate_yaml_missing_and_oversize(env, tmp_path, capsys):
    assert mod.validate_yaml_structure(["nope.yml"]) == 1
    big = _yaml(tmp_path, "big.yml", "a: 1\n")
    real_stat = mod.Path.stat

    def fake_stat(self, *a, **kw):
        result = real_stat(self, *a, **kw)
        if self.name == "big.yml":
            return SimpleNamespace(st_size=9_000_000, st_mode=result.st_mode)
        return result

    env.setattr(mod.Path, "stat", fake_stat)
    assert mod.validate_yaml_structure([big]) == 1
    assert "exceeds 8 MB" in capsys.readouterr().out


def test_validate_json(env, tmp_path, capsys):
    (tmp_path / "ok.json").write_bytes(b'{"a": 1}')
    (tmp_path / "bad.json").write_bytes(b"{")
    assert mod.validate_json(["ok.json", "bad.json"]) == 1
    assert "Invalid JSON: bad.json" in capsys.readouterr().out


def test_run_optional(env, capsys):
    assert mod.run_optional("YAML", ["yamllint"], []) == 0
    assert "No changed YAML files." in capsys.readouterr().out
    _install(env, FakeGit(handlers={("yamllint",): lambda a: _cp(1, "x.yml bad\n")}))
    assert mod.run_optional("YAML", ["yamllint"], ["x.yml"]) == 1
    out = capsys.readouterr().out
    assert "Validating 1 changed YAML file(s)." in out
    assert "x.yml bad" in out
    _install(env, FakeGit(handlers={("yamllint",): lambda a: _cp(0, "")}))
    assert mod.run_optional("YAML", ["yamllint"], ["x.yml"]) == 0


def test_main_selection_error(env, capsys):
    def boom():
        raise RuntimeError("no diff")

    env.setattr(mod, "changed_files", boom)
    assert mod.main() == 1
    assert "Changed-doc selection error: no diff" in capsys.readouterr().err


def test_main_full_flow(env, tmp_path, capsys):
    _yaml(tmp_path, "c.yml", "a: 1\n")
    (tmp_path / "d.json").write_bytes(b"[]")
    paths = [mod.Path(p) for p in ("new.md", "old.md", "moved.md", "c.yml", "d.json")]
    env.setattr(mod, "changed_files", lambda: paths)
    env.setattr(
        mod,
        "rename_origins",
        lambda: ({"moved.md"}, {"old.md": ("HEAD~1", "old.md")}),
    )
    ratchet_calls = []
    env.setattr(
        mod,
        "ratchet_markdown",
        lambda p, o: ratchet_calls.append(p) or 0,
    )
    _install(env, FakeGit())
    assert mod.main() == 0
    out = capsys.readouterr().out
    assert "Skipping 1 pure rename(s)" in out
    assert "Validating 1 changed Markdown file(s)." in out
    assert "Validating 1 changed YAML file(s)." in out
    assert "No changed JSON files." not in out
    assert ratchet_calls == [["old.md"]]


def test_main_no_docs_and_failure(env, tmp_path, capsys):
    env.setattr(mod, "changed_files", lambda: [mod.Path("x.md")])
    env.setattr(mod, "rename_origins", lambda: (set(), {}))
    _install(
        env,
        FakeGit(handlers={("markdownlint-cli2",): lambda a: _cp(1, "x.md:1 MD001\n")}),
    )
    assert mod.main() == 1
    out = capsys.readouterr().out
    assert "No changed JSON files." in out
    assert "Skipping" not in out
