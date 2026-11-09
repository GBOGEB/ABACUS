"""Lane-B wave 9: everred_v3 yaml_control strict YAML, plan DAG and federation."""

import copy
import hashlib

import pytest

from ._l2_loader import load

fp = load("tools/everred_v3/src/four_planes.py")
yc = load("tools/everred_v3/src/yaml_control.py", deps={"four_planes": fp})
Err = fp.EvidenceError

PLAN_SCHEMA = "abacus.everred.execution-plan.v1"
FED_SCHEMA = "abacus.everred.federation-policy.v1"


def _task(tid, needs=None, mode="READ_ONLY", write_paths=None, **overrides):
    task = {
        "id": tid,
        "plane": "diagnostic",
        "mode": mode,
        "owner": "bot",
        "needs": list(needs or []),
        "write_paths": list(write_paths or []),
    }
    task.update(overrides)
    return task


def _raw(tid, **raw):
    task = _task(tid)
    task.update(raw)
    return task


def _plan(*tasks):
    return {"schema": PLAN_SCHEMA, "tasks": list(tasks)}


def _binding(producer="GBOGEB/ABACUS", consumer="GBOGEB/CODEX", **overrides):
    b = {
        "producer": producer,
        "consumer": consumer,
        "action": "OBSERVATION_ONLY",
        "domain": "ci",
    }
    b.update(overrides)
    return b


# --- module import without PyYAML -------------------------------------------------------------


def test_module_without_pyyaml_refuses_configuration():
    bare = load(
        "tools/everred_v3/src/yaml_control.py",
        name="l2_w9_yaml_control_no_pyyaml",
        deps={"four_planes": fp, "yaml": None},
    )
    assert bare.yaml is None
    assert bare.StrictLoader.__mro__[1] is object
    with pytest.raises(fp.EvidenceError, match="PyYAML required"):
        bare.load_yaml("a: 1\n")


# --- load_yaml --------------------------------------------------------------------------------


def test_load_yaml_yaml12_booleans_and_bytes():
    out = yc.load_yaml(b"a: yes\nb: True\nc: off\nd: FALSE\n7: seven\n")
    assert out == {"a": "yes", "b": True, "c": "off", "d": False, 7: "seven"}


@pytest.mark.parametrize(
    "raw,message",
    [
        (b"\xff\xfe: 1\n", "YAML not UTF-8"),
        ("a: " + "x" * 200 + "\n", "YAML too large"),
        (123, "YAML too large"),
        ("a: &x 1\nb: *x\n", "YAML aliases prohibited"),
        ("a: [\n", "invalid YAML: ParserError"),
        ("<<: {a: 1}\n", "invalid YAML: ConstructorError"),
        ('"<<": 1\n', "YAML merge keys prohibited"),
        ("1.5: x\n", "invalid YAML map key"),
        ("? [a]\n: 1\n", "invalid YAML map key"),
        ("a: 1\na: 2\n", "duplicate YAML key: a"),
        ("- 1\n- 2\n", "YAML must be mapping"),
        ("", "YAML must be mapping"),
    ],
)
def test_load_yaml_rejections(raw, message):
    with pytest.raises(Err, match=message):
        yc.load_yaml(raw, max_bytes=100)


def test_load_yaml_nested_mapping_is_also_strict():
    with pytest.raises(Err, match="duplicate YAML key: k"):
        yc.load_yaml("outer:\n  k: 1\n  k: 2\n")


# --- normalize_yaml / semantic_diff -----------------------------------------------------------


def test_normalize_yaml_is_deterministic_projection():
    text, digest = yc.normalize_yaml("b: 2\na: [1, 2]\n")
    assert text == "a:\n- 1\n- 2\nb: 2\n"
    assert digest == hashlib.sha256(b'{"a":[1,2],"b":2}').hexdigest()
    assert yc.normalize_yaml("a: [1, 2]\nb: 2\n") == (text, digest)


def test_normalize_yaml_detects_meaning_change(monkeypatch):
    monkeypatch.setattr(yc.yaml, "safe_dump", lambda *a, **k: "other: 1\n")
    with pytest.raises(Err, match="YAML formatter changed meaning"):
        yc.normalize_yaml("a: 1\n")


def test_normalize_yaml_timestamp_leaks_type_error():
    """production_defect: load_yaml accepts YAML timestamps (date objects), but
    canon() cannot serialise them, so normalize_yaml raises a raw TypeError
    instead of EvidenceError; this test fails once fixed."""
    with pytest.raises(TypeError, match="not JSON serializable"):
        yc.normalize_yaml("d: 2020-01-01\n")


def test_semantic_diff_changed_and_unchanged():
    out = yc.semantic_diff("a: 1\nb: 2\n", "b: 3\nc: 4\na: 1\n")
    assert out["changed"] is True
    assert out["top_level_changes"] == ["b", "c"]
    assert out["before_digest"] != out["after_digest"]
    same = yc.semantic_diff("a: 1\n", "a:   1\n")
    assert same["changed"] is False
    assert same["top_level_changes"] == []
    assert same["before_digest"] == same["after_digest"]


# --- safe_path / overlaps ---------------------------------------------------------------------


def test_safe_path_accepts_relative_posix():
    assert yc.safe_path("src/pkg/mod.py") == "src/pkg/mod.py"


@pytest.mark.parametrize(
    "path,message",
    [
        (None, "path must be relative POSIX"),
        ("", "path must be relative POSIX"),
        ("a\\b", "path must be relative POSIX"),
        ("/etc/x", "absolute path rejected"),
        ("C:x", "absolute path rejected"),
        ("a/../b", "traversal or empty path"),
        ("./a", "traversal or empty path"),
        ("a//b", "traversal or empty path"),
        ("a/", "traversal or empty path"),
    ],
)
def test_safe_path_rejections(path, message):
    with pytest.raises(Err, match=message):
        yc.safe_path(path)


@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("src", "src", True),
        ("src/a", "src", True),
        ("src", "src/a", True),
        ("src", "srcx", False),
        ("a", "b", False),
    ],
)
def test_overlaps(a, b, expected):
    assert yc.overlaps(a, b) is expected


# --- validate_plan ----------------------------------------------------------------------------


def test_validate_plan_topological_order():
    plan = _plan(
        _task("TASK_C", needs=["TASK_A", "TASK_B"]),
        _task("TASK_B", needs=["TASK_A"]),
        _task("TASK_A"),
        _task("TASK_D"),
        _task(
            "TASK_W",
            needs=["TASK_C"],
            mode="REVIEW_REQUIRED",
            write_paths=["src/a", "docs"],
            plane="evidence",
        ),
    )
    out = yc.validate_plan(copy.deepcopy(plan))
    assert out["schema"] == PLAN_SCHEMA
    assert out["task_count"] == 5
    assert out["topological_order"] == [
        "TASK_A",
        "TASK_B",
        "TASK_C",
        "TASK_D",
        "TASK_W",
    ]
    assert out["mutating_tasks"] == ["TASK_W"]
    assert out["source_leases_required"] is True
    assert out["dispatch_authority"] is False
    assert out["plan_digest"] == fp.fingerprint(plan)


def test_validate_plan_read_only_needs_no_leases():
    out = yc.validate_plan(_plan(_task("TASK_A")))
    assert out["mutating_tasks"] == []
    assert out["source_leases_required"] is False


def test_validate_plan_task_without_write_paths_key_raises_key_error():
    """production_defect: validate_plan defaults a missing ``write_paths`` to []
    during validation, but the ``mutating_tasks`` summary indexes
    ``x["write_paths"]`` directly, so a plan whose task omits the key raises a
    raw KeyError instead of succeeding; this test fails once fixed."""
    task = _task("TASK_A")
    del task["write_paths"]
    del task["needs"]
    with pytest.raises(KeyError, match="write_paths"):
        yc.validate_plan(_plan(task))


def _many(n):
    return [_task(f"TASK_{i:03d}") for i in range(n)]


@pytest.mark.parametrize(
    "plan,message",
    [
        ("plan", "plan schema invalid"),
        ({"schema": "other", "tasks": [_task("TASK_A")]}, "plan schema invalid"),
        ({"schema": PLAN_SCHEMA}, "task count invalid"),
        (_plan(), "task count invalid"),
        (_plan(*_many(101)), "task count invalid"),
        (_plan("TASK_A"), "task malformed"),
        (_plan(_task(None)), "task ID invalid"),
        (_plan(_task("ab")), "task ID invalid"),
        (_plan(_task("TA")), "task ID invalid"),
        (_plan(_task("TASK_A"), _task("TASK_A")), "duplicate task ID"),
        (_plan(_task("TASK_A", plane="cloud")), "task plane invalid"),
        (_plan(_task("TASK_A", mode="EXECUTE")), "task execution mode invalid"),
        (_plan(_task("TASK_A", owner="")), "owner missing"),
        (_plan(_task("TASK_A", owner=None)), "owner missing"),
        (_plan(_raw("TASK_A", needs="TASK_B")), "dependencies malformed"),
        (_plan(_task("TASK_A", needs=[1])), "dependencies malformed"),
        (_plan(_raw("TASK_A", write_paths="src")), "path list invalid"),
        (
            _plan(
                _task(
                    "TASK_A",
                    mode="REVIEW_REQUIRED",
                    write_paths=[f"p{i}" for i in range(33)],
                )
            ),
            "path list invalid",
        ),
        (
            _plan(_task("TASK_A", mode="REVIEW_REQUIRED", write_paths=["../x"])),
            "traversal or empty path",
        ),
        (
            _plan(_task("TASK_A", mode="REVIEW_REQUIRED", write_paths=["a", "a"])),
            "duplicate write path",
        ),
        (
            _plan(_task("TASK_A", write_paths=["src"])),
            "unapproved worker cannot write source",
        ),
        (
            _plan(
                _task("TASK_A", mode="REVIEW_REQUIRED", write_paths=["src"]),
                _task("TASK_B", mode="REVIEW_REQUIRED", write_paths=["src/x"]),
            ),
            "worker write conflict: TASK_B vs TASK_A",
        ),
        (_plan(_task("TASK_A", needs=["TASK_A"])), "unknown or self dependency"),
        (_plan(_task("TASK_A", needs=["TASK_Z"])), "unknown or self dependency"),
        (
            _plan(_task("TASK_A", needs=["TASK_B"]), _task("TASK_B", needs=["TASK_A"])),
            "cyclic workflow dependency",
        ),
        (
            _plan(
                _task("TASK_A"),
                _task("TASK_B", needs=["TASK_A", "TASK_C"]),
                _task("TASK_C", needs=["TASK_B"]),
            ),
            "cyclic workflow dependency",
        ),
    ],
)
def test_validate_plan_rejections(plan, message):
    with pytest.raises(Err, match=message):
        yc.validate_plan(plan)


# --- evaluate_dispatch ------------------------------------------------------------------------


def _dispatch_plan():
    return _plan(
        _task("TASK_A"),
        _task("TASK_B"),
        _task("TASK_C", needs=["TASK_A"], plane="runtime"),
        _task("TASK_D", needs=["TASK_A", "TASK_B"]),
        _task("TASK_E", needs=["TASK_B"]),
        _task("TASK_W", mode="REVIEW_REQUIRED", write_paths=["src"]),
    )


def test_evaluate_dispatch_states():
    plan = _dispatch_plan()
    out = yc.evaluate_dispatch(plan, {"TASK_A": "PASS", "TASK_B": "FAIL"})
    states = {row["id"]: row["state"] for row in out["tasks"]}
    assert states == {
        "TASK_A": "READY_TO_REQUEST",
        "TASK_B": "READY_TO_REQUEST",
        "TASK_C": "READY_TO_REQUEST",
        "TASK_D": "BLOCKED_UPSTREAM_RED",
        "TASK_E": "BLOCKED_UPSTREAM_RED",
        "TASK_W": "HOLD_REVIEW",
    }
    row_c = next(r for r in out["tasks"] if r["id"] == "TASK_C")
    assert row_c == {
        "id": "TASK_C",
        "plane": "runtime",
        "state": "READY_TO_REQUEST",
        "needs": ["TASK_A"],
        "actor": "bot",
    }
    assert out["schema"] == "abacus.everred.dispatch-preview.v1"
    assert out["executed"] is False
    assert out["mutations"] is False
    assert out["admission"] == "HOLD"
    assert out["plan_digest"] == yc.validate_plan(plan)["plan_digest"]


def test_evaluate_dispatch_waits_for_missing_or_pending_evidence():
    out = yc.evaluate_dispatch(_dispatch_plan(), {"TASK_A": "PENDING"})
    states = {row["id"]: row["state"] for row in out["tasks"]}
    assert states["TASK_C"] == "WAITING_FOR_EVIDENCE"
    assert states["TASK_D"] == "WAITING_FOR_EVIDENCE"
    assert states["TASK_E"] == "WAITING_FOR_EVIDENCE"


@pytest.mark.parametrize(
    "observed",
    [{"TASK_Z": "PASS"}, {"TASK_A": "GREEN"}],
)
def test_evaluate_dispatch_status_map_invalid(observed):
    with pytest.raises(Err, match="status map invalid"):
        yc.evaluate_dispatch(_dispatch_plan(), observed)


# --- validate_federation_policy ---------------------------------------------------------------


def test_validate_federation_policy_ok():
    policy = {
        "schema": FED_SCHEMA,
        "bindings": [
            _binding(),
            _binding(domain="security"),
            _binding("GBOGEB/CODEX", "GBOGEB/ABACUS"),
        ],
    }
    out = yc.validate_federation_policy(policy)
    assert out["binding_count"] == 3
    assert out["authority_transfer"] is False
    assert out["policy_digest"] == fp.fingerprint(policy)


@pytest.mark.parametrize(
    "policy,message",
    [
        ([], "federation schema invalid"),
        ({"schema": "x", "bindings": [_binding()]}, "federation schema invalid"),
        ({"schema": FED_SCHEMA}, "federation mappings missing"),
        ({"schema": FED_SCHEMA, "bindings": []}, "federation mappings missing"),
        ({"schema": FED_SCHEMA, "bindings": ["x"]}, "invalid binding"),
        ({"schema": FED_SCHEMA, "bindings": [_binding(1)]}, "federation repo invalid"),
        (
            {"schema": FED_SCHEMA, "bindings": [_binding("noslash")]},
            "federation repo invalid",
        ),
        (
            {"schema": FED_SCHEMA, "bindings": [_binding(consumer="GBOGEB/..")]},
            "federation repo invalid",
        ),
        (
            {"schema": FED_SCHEMA, "bindings": [_binding("./ABACUS")]},
            "federation repo invalid",
        ),
        (
            {"schema": FED_SCHEMA, "bindings": [_binding(consumer="GBOGEB/ABACUS")]},
            "federation requires distinct producer",
        ),
        (
            {"schema": FED_SCHEMA, "bindings": [_binding(action="MERGE")]},
            "federation cannot delegate authority",
        ),
        (
            {"schema": FED_SCHEMA, "bindings": [_binding(), _binding()]},
            "duplicate federation binding",
        ),
    ],
)
def test_validate_federation_policy_rejections(policy, message):
    with pytest.raises(Err, match=message):
        yc.validate_federation_policy(policy)
