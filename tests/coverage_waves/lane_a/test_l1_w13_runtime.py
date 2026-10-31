"""Lane A wave 13: models.qps_line_s.runtime verdict logic (paths redirected)."""

import json

import pytest

from models.qps_line_s import runtime as rt


def _unknown():
    return "unknown"


@pytest.fixture
def gen(tmp_path, monkeypatch):
    gen_dir = tmp_path / "gen"
    monkeypatch.setattr(rt, "ROOT", tmp_path)
    monkeypatch.setattr(rt, "GEN", gen_dir)
    monkeypatch.setattr(rt, "MATRIX", gen_dir / "scenario_matrix.csv")
    monkeypatch.setattr(rt, "STATUS_OUT", gen_dir / "runtime_status.json")
    # energy_provenance binds MATRIX as a default at import; keep it off repo files.
    monkeypatch.setattr(rt, "energy_provenance", _unknown)
    monkeypatch.setattr(rt, "REQUIRED_ARTEFACTS", [gen_dir / "a.csv", gen_dir / "b.md"])
    return gen_dir


def _make_artefacts(gen_dir):
    gen_dir.mkdir(parents=True, exist_ok=True)
    (gen_dir / "a.csv").write_text("x", encoding="utf-8")
    (gen_dir / "b.md").write_text("x", encoding="utf-8")


def test_run_generators_calls_all(monkeypatch):
    calls = []
    monkeypatch.setattr(rt.run_scenarios, "main", lambda: calls.append("s"))
    monkeypatch.setattr(rt.rfi_package, "main", lambda: calls.append("r"))
    monkeypatch.setattr(rt.recovery_model, "default_rows", lambda: ["row"])
    monkeypatch.setattr(rt.recovery_model, "write_outputs", calls.append)
    rt.run_generators()
    assert calls == ["s", "r", ["row"]]


def test_missing_artefacts_relative(gen):
    got = sorted(name.replace("\\", "/") for name in rt.missing_artefacts())
    assert got == ["gen/a.csv", "gen/b.md"]
    _make_artefacts(gen)
    assert rt.missing_artefacts() == []


def test_read_register(tmp_path):
    good = tmp_path / "r.yaml"
    good.write_text("blockers: []\n", encoding="utf-8")
    assert rt.read_register(good) == {"blockers": []}
    bad = tmp_path / "bad.yaml"
    bad.write_text("just text\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        rt.read_register(bad)


def test_open_gates_filters_and_default_reader(monkeypatch):
    data = {
        "blockers": [
            {"id": "B1", "gate": True, "status": "open", "severity": "hi"},
            {"id": "B2", "gate": True, "status": "accepted"},
            "junk",
        ],
        "assumptions": "not-a-list",
    }
    assert rt.open_gates(data) == [{"id": "B1", "status": "open", "severity": "hi"}]
    monkeypatch.setattr(rt, "read_register", lambda: {"assumptions": [{"gate": 1}]})
    assert rt.open_gates() == [{"id": None, "status": None, "severity": None}]


@pytest.mark.parametrize(
    "body,expected",
    [
        ("energy_source,x\nGamma fit,1\n", "bound"),
        ("energy_source,x\nIntegrated,1\n", "integrated"),
        ("energy_source,x\n,1\n", "unknown"),
        ("other\n1\n", "unknown"),
    ],
)
def test_energy_provenance(tmp_path, body, expected):
    matrix = tmp_path / "m.csv"
    matrix.write_text(body, encoding="utf-8")
    assert rt.energy_provenance(matrix) == expected


def test_energy_provenance_missing_file(tmp_path):
    assert rt.energy_provenance(tmp_path / "none.csv") == "unknown"


def test_decide():
    assert rt.decide(["x"], []) == "PIPELINE_FAIL"
    assert rt.decide([], []) == "PROCEED_MDA"
    assert rt.decide([], [{"id": 1}]) == "ISSUE_RFI"


def test_runtime_pipeline_fail_exits_two(gen, capsys):
    with pytest.raises(SystemExit) as exc:
        rt.runtime(regenerate=False)
    assert exc.value.code == 2
    status = json.loads((gen / "runtime_status.json").read_text())
    assert status["verdict"] == "PIPELINE_FAIL"
    assert status["energy_model"] == "unknown"


def test_runtime_proceed_with_regenerate(gen, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(rt, "run_generators", lambda: calls.append(1))
    monkeypatch.setattr(rt, "open_gates", list)
    _make_artefacts(gen)
    status = rt.runtime(regenerate=True, enforce=True)
    assert calls == [1]
    assert status["verdict"] == "PROCEED_MDA"
    assert json.loads(capsys.readouterr().out)["n_open_gates"] == 0


def test_runtime_issue_rfi_enforce_and_lenient(gen, monkeypatch, capsys):
    monkeypatch.setattr(rt, "open_gates", lambda: [{"id": "G"}])
    _make_artefacts(gen)
    assert rt.runtime(regenerate=False)["verdict"] == "ISSUE_RFI"
    with pytest.raises(SystemExit) as exc:
        rt.runtime(regenerate=False, enforce=True)
    assert exc.value.code == 1
