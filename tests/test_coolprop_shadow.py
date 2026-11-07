"""Contract for tools/coolprop_shadow (CoolProp record/replay differential).

Uses a stand-in `CoolProp` package so the harness is proven without CoolProp
installed, on every interpreter in the main matrix.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "tools" / "coolprop_shadow" / "hook"
sys.path.insert(0, str(HOOK))
sys.path.insert(0, str(ROOT / "tools" / "coolprop_shadow"))
import coolprop_shadow_codec as codec  # noqa: E402
import replay  # noqa: E402

FAKE_V7 = '''
def PropsSI(*args):
    if len(args) == 2:
        return {"GAS_CONSTANT": 8.314462618, "MOLAR_MASS": 0.004002602}[args[0]]
    out, n1, v1, n2, v2, fluid = args
    if n1 == "T" and v1 < 2.1768:
        raise ValueError(f"Temperature to QT_flash [{v1} K] must be in range")
    if out == "BAD":
        raise ValueError("unknown output BAD")
    if isinstance(v2, list):
        return [float(v1) * x for x in v2]
    base = float(v1) * 1000.0 + float(v2)
    return base + (0.5 if type(v2) is int else 0.0)  # int and float args differ
'''


def make_fake(root: Path, version: str, body: str) -> Path:
    pkg = root / "CoolProp"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text(f'__version__ = "{version}"\n', encoding="utf-8")
    (pkg / "CoolProp.py").write_text(textwrap.dedent(body), encoding="utf-8")
    return root


CALLER = '''
import subprocess, sys
from CoolProp.CoolProp import PropsSI
PropsSI("D", "T", 4.5, "P", 1.3e5, "Helium")
PropsSI("D", "T", 4.5, "P", 1.3e5, "Helium")          # repeat: counted, not duplicated
PropsSI("P", "T", 4.2, "Q", 0, "Helium")              # int literal kept as int
PropsSI("P", "T", 4.2, "Q", 0.0, "Helium")            # float literal is a different call
PropsSI("GAS_CONSTANT", "Helium")
PropsSI("D", "T", 3.0, "P", [1.0, 2.0], "Helium")
for bad in (("D", "T", 2.0, "P", 1e5, "Helium"), ("BAD", "T", 5.0, "P", 1e5, "Helium")):
    try:
        PropsSI(*bad)
    except ValueError:
        pass
# a model CLI launched by a test: the hook must follow it into the child
subprocess.run([sys.executable, "-c",
                "from CoolProp.CoolProp import PropsSI; PropsSI('H', 'T', 300.0, 'P', 1e5, 'Helium')"],
               check=True)
'''


@pytest.fixture()
def recorded(tmp_path):
    fake = make_fake(tmp_path / "v7", "7.2.0", FAKE_V7)
    records = tmp_path / "records"
    env = {**os.environ,
           "PYTHONPATH": os.pathsep.join([str(HOOK), str(fake)]),
           "COOLPROP_SHADOW_RECORD_DIR": str(records)}
    subprocess.run([sys.executable, "-c", CALLER], env=env, check=True, cwd=tmp_path)
    calls, headers = replay.load_records(records)
    return calls, headers, records, fake


def load_fake(directory: Path):
    namespace: dict = {}
    exec((directory / "CoolProp" / "CoolProp.py").read_text(encoding="utf-8"), namespace)
    return namespace["PropsSI"]


# --------------------------------------------------------------------------- recorder


def test_hook_records_every_distinct_call_including_subprocesses(recorded):
    calls, headers, records, _ = recorded
    assert {h["coolprop"] for h in headers} == {"7.2.0"}
    assert len(list(records.glob("calls-*.jsonl"))) == 2  # parent + child process
    decoded = {repr(codec.decode_call(c["key"])[0]): c for c in calls.values()}
    assert len(decoded) == 8
    assert decoded[repr(("D", "T", 4.5, "P", 1.3e5, "Helium"))]["count"] == 2
    assert repr(("H", "T", 300.0, "P", 1e5, "Helium")) in decoded  # from the child process
    int_call = decoded[repr(("P", "T", 4.2, "Q", 0, "Helium"))]
    float_call = decoded[repr(("P", "T", 4.2, "Q", 0.0, "Helium"))]
    assert int_call is not float_call  # type-distinct calls stay distinct
    assert json.loads(int_call["key"])["args"][4] == ["int", 0]
    assert decoded[repr(("D", "T", 2.0, "P", 1e5, "Helium"))]["outcome"][0] == "error"
    assert all(site.startswith("__main__:") for c in calls.values() for site in c["sites"])


def test_hook_is_inert_without_the_environment_switch(tmp_path):
    fake = make_fake(tmp_path / "v7", "7.2.0", FAKE_V7)
    env = {k: v for k, v in os.environ.items() if k != "COOLPROP_SHADOW_RECORD_DIR"}
    env["PYTHONPATH"] = os.pathsep.join([str(HOOK), str(fake)])
    out = subprocess.run(
        [sys.executable, "-c",
         "from CoolProp.CoolProp import PropsSI; print(hasattr(PropsSI, '__coolprop_shadow__'))"],
        env=env, check=True, capture_output=True, text=True, cwd=tmp_path)
    assert out.stdout.strip() == "False"


def test_wrapper_is_transparent(tmp_path):
    fake = make_fake(tmp_path / "v7", "7.2.0", FAKE_V7)
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(HOOK), str(fake)]),
           "COOLPROP_SHADOW_RECORD_DIR": str(tmp_path / "r")}
    script = textwrap.dedent('''
        import CoolProp.CoolProp as cp
        assert cp.PropsSI.__coolprop_shadow__ and cp.PropsSI.__name__ == "PropsSI"
        assert cp.PropsSI("D", "T", 5.0, "P", 2.0, "Helium") == 5002.0
        try:
            cp.PropsSI("D", "T", 1.0, "P", 2.0, "Helium")
        except ValueError as exc:
            assert "QT_flash" in str(exc)
        else:
            raise AssertionError("error was swallowed")
        print("ok")
    ''')
    out = subprocess.run([sys.executable, "-c", script], env=env, check=True,
                         capture_output=True, text=True, cwd=tmp_path)
    assert out.stdout.strip() == "ok"


# --------------------------------------------------------------------------- replay


def test_control_replay_is_identical(recorded):
    calls, *_ , fake = recorded
    rows = replay.replay(calls, load_fake(fake))
    assert {r["class"] for r in rows} == {"IDENTICAL"}


DRIFTED = FAKE_V7.replace(
    '    base = float(v1) * 1000.0 + float(v2)\n',
    '    base = float(v1) * 1000.0 + float(v2)\n'
    '    if out == "D": base *= 1 + 1e-9\n'
    '    if out == "P": base *= 1 + 1e-3\n'
    '    if out == "H": raise ValueError("new limit check")\n'
).replace('    if n1 == "T" and v1 < 2.1768:\n'
          '        raise ValueError(f"Temperature to QT_flash [{v1} K] must be in range")\n',
          '    if n1 == "T" and v1 < 2.1768:\n'
          '        return 0.125\n'
).replace('raise ValueError("unknown output BAD")', 'raise ValueError("Output BAD is not valid")')


def test_replay_classifies_each_kind_of_change(recorded, tmp_path):
    calls, *_ = recorded
    new = make_fake(tmp_path / "v8", "8.0.0", DRIFTED)
    rows = {r["call"]: r for r in replay.replay(calls, load_fake(new))}
    klass = {call: r["class"] for call, r in rows.items()}
    assert klass["PropsSI('D', 'T', 4.5, 'P', 130000.0, 'Helium')"] == "DRIFT"
    assert klass["PropsSI('P', 'T', 4.2, 'Q', 0, 'Helium')"] == "SIGNIFICANT"
    assert klass["PropsSI('H', 'T', 300.0, 'P', 100000.0, 'Helium')"] == "NEW_ERROR"
    assert klass["PropsSI('D', 'T', 2.0, 'P', 100000.0, 'Helium')"] == "FIXED_ERROR"
    assert klass["PropsSI('BAD', 'T', 5.0, 'P', 100000.0, 'Helium')"] == "ERROR_REWORDED"
    assert klass["PropsSI('GAS_CONSTANT', 'Helium')"] == "IDENTICAL"
    assert rows["PropsSI('D', 'T', 2.0, 'P', 100000.0, 'Helium')"]["band"].startswith("below lambda")


def test_cli_require_identical_gates_the_control(recorded, tmp_path):
    _, _, records, fake = recorded
    new = make_fake(tmp_path / "v8", "8.0.0", DRIFTED)

    def cli(coolprop_dir: Path) -> subprocess.CompletedProcess:
        env = {**os.environ, "PYTHONPATH": str(coolprop_dir)}
        env.pop("COOLPROP_SHADOW_RECORD_DIR", None)
        return subprocess.run(
            [sys.executable, str(ROOT / "tools/coolprop_shadow/replay.py"), "--records", str(records),
             "--out", str(tmp_path / f"{coolprop_dir.name}.json"),
             "--summary", str(tmp_path / f"{coolprop_dir.name}.md"), "--require-identical"],
            env=env, capture_output=True, text=True, cwd=tmp_path)

    assert cli(fake).returncode == 0
    drifted = cli(new)
    assert drifted.returncode == 1
    report = json.loads((tmp_path / "v8.json").read_text(encoding="utf-8"))
    assert report["meta"]["replay"]["coolprop"] == "8.0.0"
    assert report["meta"]["recorded_coolprop"] == ["7.2.0"]
    assert "NEW_ERROR" in (tmp_path / "v8.md").read_text(encoding="utf-8")


def test_cli_fails_closed_without_records(tmp_path):
    out = subprocess.run([sys.executable, str(ROOT / "tools/coolprop_shadow/replay.py"),
                          "--records", str(tmp_path), "--out", str(tmp_path / "r.json")],
                         capture_output=True, text=True)
    assert out.returncode == 2


# --------------------------------------------------------------------------- codec


@pytest.mark.parametrize("value", [0, 1, True, 4.2, -0.0, 1e-300, math.inf, "Helium",
                                   [1, 2.5], (3.0, "x")])
def test_codec_round_trip_preserves_value_and_type(value):
    back = codec.decode(json.loads(json.dumps(codec.encode(value))))
    assert type(back) is type(value)
    assert back == value or (isinstance(value, float) and math.copysign(1, back) == math.copysign(1, value))


def test_codec_round_trip_nan_and_numpy():
    assert math.isnan(codec.decode(codec.encode(math.nan)))
    np = pytest.importorskip("numpy")
    for value in (np.float64(4.2), np.float32(1.5), np.int64(7)):
        back = codec.decode(json.loads(json.dumps(codec.encode(value))))
        assert type(back) is type(value) and back == value
    arr = np.array([[1.0, 2.0], [3.0, 4.0]])
    back = codec.decode(json.loads(json.dumps(codec.encode(arr))))
    assert back.dtype == arr.dtype and back.shape == arr.shape and (back == arr).all()


def test_codec_marks_unknown_types_unreplayable():
    with pytest.raises(codec.Unreplayable):
        codec.decode(codec.encode(object()))


def test_bands_follow_the_helium_policy():
    assert replay.band(("D", "T", 2.0, "P", 1e5, "Helium")).startswith("below lambda")
    assert "HEPAK governs" in replay.band(("D", "T", 4.5, "P", 1e5, "Helium"))
    assert "CoolProp governs" in replay.band(("D", "P", 1e5, "T", 4.6, "HEOS::Helium"))
    assert replay.band(("T", "P", 1e5, "Q", 0, "Helium")) == "no-T input"
    assert replay.band(("GAS_CONSTANT", "Helium")) == "constant"
    assert replay.band(("D", "T", 300.0, "P", 1e5, "Nitrogen")) == "non-helium"
