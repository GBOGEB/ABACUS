"""Lane-B wave 8: everred_v3 four_planes typed observations and federated join."""

import copy

import pytest

from ._l2_loader import load

fp = load("tools/everred_v3/src/four_planes.py")

A, B = "a" * 40, "b" * 40
REPO = "GBOGEB/ABACUS"
IMAGE = "sha256:" + "e" * 64


def _src(**overrides):
    values = {"repository": REPO, "source_sha": A, "run_id": 5, "job_id": 6}
    values.update(overrides)
    return fp.Source(**values)


# --- primitives and Source ------------------------------------------------------------------------


def test_canon_and_fingerprint():
    assert fp.canon({"b": 1, "a": "é"}) == '{"a":"\\u00e9","b":1}'
    assert fp.fingerprint({"a": 1}) == fp.fingerprint({"a": 1})
    with pytest.raises(fp.EvidenceError, match="nope"):
        fp.demand(False, "nope")


def test_source_binding_and_from_dict():
    src = _src(executed_sha=B)
    assert src.binding() == {
        "repository": REPO,
        "source_sha": A,
        "run_id": 5,
        "job_id": 6,
        "executed_sha": B,
    }
    assert (
        fp.source_from_dict({"repository": REPO, "source_sha": A, "run_id": 1}).job_id
        is None
    )
    with pytest.raises(fp.EvidenceError, match="source must be mapping"):
        fp.source_from_dict("x")


@pytest.mark.parametrize(
    "overrides,message",
    [
        ({"repository": "bad"}, "repository invalid"),
        ({"repository": "GBOGEB/.."}, "repository invalid"),
        ({"source_sha": "A" * 40}, "source SHA invalid"),
        ({"run_id": True}, "run ID invalid"),
        ({"job_id": 0}, "job ID invalid"),
        ({"executed_sha": "short"}, "executed SHA invalid"),
    ],
)
def test_source_rejections(overrides, message):
    with pytest.raises(fp.EvidenceError, match=message):
        _src(**overrides)


def test_time_normalization():
    assert fp._time("2026-10-27T12:00:00+02:00") == "2026-10-27T10:00:00Z"
    assert fp._time("2026-10-27T10:00:00Z") == "2026-10-27T10:00:00Z"
    for bad, message in [
        (None, "UTC or offset time required"),
        ("2026-10-27T10:00:00", "UTC or offset time required"),
        ("2026-13-45T10:00:00Z", "time invalid"),
    ]:
        with pytest.raises(fp.EvidenceError, match=message):
            fp._time(bad)


def test_clean_log_redacts_and_bounds():
    secret_line = "tok" + "en=abc123 and " + "pass" + "word: hunter2"
    text = "\x1b[31mred\x1b[0m\x07bell\t" + secret_line + "\n"
    result = fp.clean_log(text)
    assert result["excerpt"].startswith("red bell\t[REDACTED] and [REDACTED]")
    assert (
        result["raw_bytes"] == len(text.encode("utf-8"))
        and result["truncated"] is False
    )
    long = fp.clean_log("é" * (fp.MAX_LOG))
    assert (
        long["truncated"] is True and len(long["excerpt"].encode("utf-8")) <= fp.MAX_LOG
    )
    with pytest.raises(fp.EvidenceError, match="log must be text"):
        fp.clean_log(b"bytes")


# --- receipts ---------------------------------------------------------------------------------------


def _debugger(**overrides):
    data = {
        "tool": "LLDB",
        "session_id": "s-1",
        "verified_step_count": 3,
        "binary_build_id": "build-9",
        "frames": [{"fn": "main"}],
        "started_at": "2026-10-27T10:00:00Z",
        "ended_at": "2026-10-27T10:05:00Z",
    }
    data.update(overrides)
    return data


def test_diagnostic_receipt_trust_levels():
    declared = fp.diagnostic_receipt(_src(), _debugger())
    assert declared["data"]["observed_step_evidence"] is None
    assert (
        declared["receipt_id"].startswith("FP-") and len(declared["receipt_id"]) == 31
    )
    observed = fp.diagnostic_receipt(
        _src(), _debugger(), trust="LOCAL_OBSERVED", artifact_sha256="f" * 64
    )
    assert observed["data"]["observed_step_evidence"] is True
    assert (
        observed["artifact_sha256"] == "f" * 64 and observed["merge_authority"] is False
    )
    minimal = fp.diagnostic_receipt(
        _src(), _debugger(started_at=None, ended_at=None, frames=[])
    )
    assert minimal["data"]["frames"] == []


@pytest.mark.parametrize(
    "data,kwargs,message",
    [
        ("x", {}, "debugger observation must be mapping"),
        (_debugger(tool="WinDbg"), {}, "unsupported debugger"),
        (_debugger(session_id="x" * 129), {}, "session ID missing"),
        (_debugger(verified_step_count=-1), {}, "invalid step count"),
        (_debugger(binary_build_id=""), {}, "target build ID missing"),
        (_debugger(frames=["x"]), {}, "malformed backtrace"),
        (_debugger(started_at="yesterday"), {}, "UTC or offset time required"),
        (_debugger(crash_signature=5), {}, "bad crash signature"),
        (_debugger(), {"trust": "TRUST_ME"}, "invalid trust label"),
        (_debugger(), {"trust": "EXTERNAL_REVIEWED"}, "externally authenticated"),
        (_debugger(), {"artifact_sha256": "short"}, "invalid artifact digest"),
    ],
)
def test_diagnostic_receipt_rejections(data, kwargs, message):
    with pytest.raises(fp.EvidenceError, match=message):
        fp.diagnostic_receipt(_src(), data, **kwargs)


def test_receipt_rejects_unknown_plane():
    with pytest.raises(fp.EvidenceError, match="unrecognized plane"):
        fp._receipt(_src(), "astral", "x", {})


def _ldab(**overrides):
    data = {"root_id": "root:abc", "finding_fingerprint": "f" * 64}
    data.update(overrides)
    return data


def test_ldab_receipt():
    row = fp.ldab_receipt(_src(), _ldab(repair_commit=B, owner="lane-b"))
    assert row["domain"] == "ldab" and row["data"]["disposition"] == "HYPOTHESIS"
    assert row["data"]["scope"] == "same-head" and row["data"]["repair_commit"] == B


@pytest.mark.parametrize(
    "data,message",
    [
        ("x", "LDAB linkage must be mapping"),
        (_ldab(root_id="x"), "stable root ID required"),
        (_ldab(finding_fingerprint="short"), "exact finding fingerprint required"),
        (_ldab(disposition="CONFIRMED_ROOT"), "cannot self-certify"),
        (_ldab(repair_commit="nope"), "repair SHA invalid"),
    ],
)
def test_ldab_receipt_rejections(data, message):
    with pytest.raises(fp.EvidenceError, match=message):
        fp.ldab_receipt(_src(), data)


def _runtime(**overrides):
    data = {
        "os_family": "RHEL9",
        "container_runtime": "podman",
        "container_id": "c1",
        "image_digest": IMAGE,
        "ports": [
            {
                "port": 8080,
                "state": "OBSERVED_LISTENING",
                "tested_at": "t",
                "probe_id": "p",
            },
            {"port": 22, "state": "DECLARED"},
        ],
    }
    data.update(overrides)
    return data


def test_runtime_receipt():
    row = fp.runtime_receipt(_src(), _runtime())
    assert (
        row["plane"] == "runtime"
        and row["data"]["evidence_status"] == "OBSERVED_NO_DEPLOYMENT_PROOF"
    )
    bare = fp.runtime_receipt(_src(), {"os_family": "macOS"})
    assert bare["data"]["container_runtime"] == "none" and bare["data"]["ports"] == []


@pytest.mark.parametrize(
    "data,message",
    [
        ("x", "runtime observation must be mapping"),
        (_runtime(os_family="BeOS"), "unrecognized OS"),
        (_runtime(container_runtime="lxc"), "unsupported container runtime"),
        (_runtime(container_runtime="none"), "unbound container identity"),
        (_runtime(image_digest="sha256:short"), "unbound container identity"),
        (_runtime(ports="x"), "invalid port census"),
        (_runtime(ports=[{"port": 1, "state": "OPEN"}]), "invalid port state"),
        (_runtime(ports=[{"port": 70000, "state": "DECLARED"}]), "invalid port"),
        (
            _runtime(ports=[{"port": 80, "state": "OBSERVED_LISTENING"}]),
            "missing probe",
        ),
    ],
)
def test_runtime_receipt_rejections(data, message):
    with pytest.raises(fp.EvidenceError, match=message):
        fp.runtime_receipt(_src(), data)


# --- federated_join -----------------------------------------------------------------------------------


def test_federated_join_groups_by_exact_source():
    rows = [
        fp.diagnostic_receipt(_src(), _debugger()),
        fp.runtime_receipt(_src(job_id=None), _runtime()),
        fp.ldab_receipt(_src(job_id=9), _ldab()),
        fp.runtime_receipt(_src(source_sha=B), {"os_family": "Ubuntu"}),
    ]
    census = fp.federated_join(rows)
    assert census["group_count"] == 2 and census["observation_count"] == 4
    first = census["groups"][0]
    assert first["source_sha"] == A and first["job_ids"] == [6, 9]
    assert (
        len(first["planes"]["diagnostic"]) == 2 and len(first["planes"]["runtime"]) == 1
    )
    assert first["observations"] == 3 and first["admission"] == "HOLD"
    assert census["global_admission"] == "HOLD" and census["unknown_is_zero"] is False


def _tampered(change):
    row = fp.diagnostic_receipt(_src(), _debugger())
    change(row)
    return [row]


@pytest.mark.parametrize(
    "receipts,message",
    [
        ("x", "receipts must be list"),
        (["x"], "invalid receipt"),
        (_tampered(lambda r: r.update(plane="astral")), "unknown receipt plane"),
        (
            _tampered(lambda r: r.update(merge_authority=True)),
            "cannot grant merge authority",
        ),
        (_tampered(lambda r: r["data"].update(tool="GDB")), "content hash mismatch"),
    ],
)
def test_federated_join_rejections(receipts, message):
    with pytest.raises(fp.EvidenceError, match=message):
        fp.federated_join(receipts)


def test_federated_join_rejects_duplicates():
    row = fp.diagnostic_receipt(_src(), _debugger())
    with pytest.raises(fp.EvidenceError, match="duplicate receipt"):
        fp.federated_join([row, copy.deepcopy(row)])
