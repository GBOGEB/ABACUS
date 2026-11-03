"""Contract for tools/ci/python_versions.py (Python version SSOT sync and guard).

Synthetic version numbers (3.20-3.24) keep these tests independent of the real
ssot/python_versions.yaml, so they never need editing when Python is bumped.
"""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "ci"))
import python_versions as pv  # noqa: E402

SSOT = """\
supported: ["3.20", "3.21", "3.22", "3.23", "3.24"]
default: "3.23"
experimental: ["3.25"]
canary_workflows: [.github/workflows/canary.yml]
end_of_life: ["3.18", "3.19"]
caps:
  oracle:
    max: "3.23"
    reason: oracle wheels stop at cp323
    patterns: ['(?i)oraclepkg']
  old-numpy:
    max: "3.21"
    reason: pinned numpy stops at cp321
    patterns: ['numpy==1\\.']
derived_files:
  - {path: .python-version, pattern: '^(3\\.\\d+)\\s*$', value: default, format: dotted, create: true}
  - {path: pyproject.toml, pattern: 'requires-python = ">=(3\\.\\d+)"', value: oldest, format: dotted}
"""

CANARY = """\
name: canary
on: workflow_dispatch
jobs:
  c:
    runs-on: ubuntu-latest
    continue-on-error: true
    strategy:
      matrix:
        python-version: ['3.25']
    steps:
      - uses: actions/setup-python@v7
        with:
          python-version: ${{ matrix.python-version }}
          allow-prereleases: true
"""


def make_repo(tmp_path: Path, workflows: dict[str, str]) -> Path:
    (tmp_path / "ssot").mkdir()
    (tmp_path / "ssot/python_versions.yaml").write_text(SSOT, encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('requires-python = ">=3.19"\n', encoding="utf-8")
    wf = tmp_path / ".github/workflows"
    wf.mkdir(parents=True)
    (wf / "canary.yml").write_text(CANARY, encoding="utf-8")
    for name, text in workflows.items():
        (wf / name).write_text(textwrap.dedent(text), encoding="utf-8")
    return tmp_path


def run(root: Path, command: str) -> int:
    return pv.main([command, "--root", str(root)])


def wf(root: Path, name: str) -> str:
    return (root / ".github/workflows" / name).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- lane rules


@pytest.fixture()
def lane():
    return pv.Lane(["3.20", "3.21", "3.22", "3.23", "3.24"], "3.23")


def test_list_rules(lane):
    assert lane.for_list(4) == lane.versions          # >= 3 -> full lane
    assert lane.for_list(3) == lane.versions
    assert lane.for_list(2) == ["3.20", "3.24"]       # edges
    assert lane.for_list(1) == ["3.23"]               # default pin


def test_role_rules_preserve_lowest_middle_highest(lane):
    assert lane.for_roles(["3.18"]) == {"3.18": "3.23"}
    assert lane.for_roles(["3.18", "3.19"]) == {"3.18": "3.20", "3.19": "3.24"}
    assert lane.for_roles(["3.18", "3.19", "3.20", "3.19"]) == {
        "3.18": "3.20", "3.19": "3.22", "3.20": "3.24"}
    with pytest.raises(pv.SyncError):
        lane.for_roles(["3.16", "3.17", "3.18", "3.19"])


def test_narrow_lane_folds_middle_role_into_oldest():
    narrow = pv.Lane(["3.20", "3.21"], "3.21")
    assert narrow.for_roles(["3.17", "3.18", "3.19"]) == {"3.17": "3.20", "3.18": "3.20", "3.19": "3.21"}


def test_condition_role_map_tracks_matrix_position(lane):
    assert lane.role_map(["3.18", "3.19"]) == {"3.18": "3.20", "3.19": "3.24"}
    assert lane.role_map(["3.17", "3.18", "3.19"]) == {"3.17": "3.20", "3.18": "3.22", "3.19": "3.24"}


# --------------------------------------------------------------------------- sync


SAMPLE = """\
name: sample
on:
  pull_request:
    paths: ['requirements-oraclepkg.txt']
env:
  PYTHON_VERSION: '3.19'
jobs:
  unit:
    name: Unit
    strategy:
      matrix:
        python-version: ["3.18", "3.19"]
    steps:
      - uses: actions/setup-python@abc123
        with:
          python-version: ${{ matrix.python-version }}
      - name: Upload coverage
        if: matrix.python-version == '3.19'
        run: echo ok
  pinned:
    name: Lint - Python 3.19
    steps:
      - name: Set up Python 3.19
        uses: actions/setup-python@v7
        with:
          python-version: ${{ env.PYTHON_VERSION }}
  oracle:
    strategy:
      matrix:
        include:
          - {os: ubuntu, py: '3.17'}
          - {os: ubuntu, py: '3.18'}
          - {os: ubuntu, py: '3.19'}
          - {os: windows, py: '3.18'}
    steps:
      - run: pip install oraclepkg==7.2.0
      - uses: actions/setup-python@v7
        with:
          python-version: ${{ matrix.py }}
  narrow:
    strategy:
      matrix:
        include:
          - os: ubuntu
            python: '3.17'
          - os: ubuntu
            python: '3.18'
          - os: ubuntu
            python: '3.19'
    steps:
      - run: pip install numpy==1.26.4
      - uses: actions/setup-python@v7
        with:
          python-version: ${{ matrix.python }}
  dynamic:
    strategy:
      matrix:
        python-version: >-
          ${{ fromJSON(github.event_name == 'push' && '["3.19"]' || '["3.18","3.19"]') }}
    steps:
      - uses: actions/setup-python@v7
        with:
          python-version: ${{ matrix.python-version }}
"""


def test_sync_rewrites_every_site_kind_and_is_idempotent(tmp_path):
    root = make_repo(tmp_path, {"sample.yml": SAMPLE})
    assert run(root, "check") == 1
    assert run(root, "sync") == 0
    text = wf(root, "sample.yml")

    # 2-entry list -> lane edges (the oracle cap is per job and on.paths is ignored)
    assert 'python-version: ["3.20", "3.24"]' in text
    # condition follows the cell it used to select (old newest -> new newest)
    assert "if: matrix.python-version == '3.24'" in text
    # env-routed pin and its labels follow the default
    assert "PYTHON_VERSION: '3.23'" in text
    assert "name: Set up Python 3.23" in text and "name: Lint - Python 3.23" in text
    # include roles under the oracle cap (lane 3.20-3.23): lowest/middle/highest
    assert "{os: ubuntu, py: '3.20'}" in text
    assert "{os: ubuntu, py: '3.22'}" in text
    assert "{os: ubuntu, py: '3.23'}" in text
    assert "{os: windows, py: '3.22'}" in text
    # narrow lane (3.20-3.21): middle folds into oldest, duplicate entry removed
    assert text.count("python: '3.20'") == 1 and text.count("python: '3.21'") == 1
    assert "python: '3.17'" not in text and "python: '3.18'" not in text
    # JSON lists inside expressions
    assert '\'["3.23"]\' || \'["3.20","3.24"]\'' in text

    # derived files
    assert (root / ".python-version").read_text(encoding="utf-8") == "3.23\n"
    assert 'requires-python = ">=3.20"' in (root / "pyproject.toml").read_text(encoding="utf-8")
    view = json.loads((root / pv.LANES_VIEW_PATH).read_text(encoding="utf-8"))
    assert view["lanes"]["oracle"]["versions"] == ["3.20", "3.21", "3.22", "3.23"]
    assert view["lanes"]["old-numpy"]["pin"] == "3.21"

    before = text
    assert run(root, "sync") == 0
    assert wf(root, "sample.yml") == before
    assert run(root, "check") == 0


def test_sync_only_touches_version_spans(tmp_path):
    root = make_repo(tmp_path, {"sample.yml": SAMPLE})
    run(root, "sync")
    old_lines, new_lines = SAMPLE.splitlines(), wf(root, "sample.yml").splitlines()
    dropped = [line for line in old_lines if line not in new_lines]
    for line in dropped:  # every changed or removed line carried a version
        assert pv.LITERAL_RE.search(line) or line.strip() == "- os: ubuntu", line


def test_canary_keeps_experimental_versions(tmp_path):
    root = make_repo(tmp_path, {})
    assert run(root, "sync") == 0
    assert "python-version: ['3.25']" in wf(root, "canary.yml")
    assert run(root, "check") == 0


# --------------------------------------------------------------------------- guard failures


@pytest.mark.parametrize(
    "workflow, message",
    [
        (  # condition against an expression matrix cannot be rewritten safely
            """\
            jobs:
              j:
                strategy:
                  matrix: ${{ fromJSON(needs.plan.outputs.matrix) }}
                steps:
                  - uses: actions/setup-python@v7
                    with: {python-version: '${{ matrix.python-version }}'}
                  - if: matrix.python-version == '3.23'
                    run: echo
            """,
            "compare to a job output",
        ),
        (  # versions hidden in a hand-built JSON matrix
            """\
            jobs:
              j:
                steps:
                  - run: echo 'matrix={"python-version":"3.22"}' >> "$GITHUB_OUTPUT"
            """,
            "hard-coded python-version",
        ),
        (  # end-of-life interpreter in a script
            """\
            jobs:
              j:
                steps:
                  - run: uv python install 3.19
            """,
            "end-of-life",
        ),
        (  # reads the lanes view without declaring its lane
            """\
            jobs:
              j:
                steps:
                  - run: jq '.lanes.default.pin' ssot/python_versions.lanes.json
            """,
            "must declare PYTHON_LANE: default",
        ),
    ],
)
def test_check_fails_closed(tmp_path, capsys, workflow, message):
    root = make_repo(tmp_path, {"w.yml": workflow})
    run(root, "sync")  # derived files in place; the workflow problem must remain
    capsys.readouterr()
    assert run(root, "check") == 1
    assert message in capsys.readouterr().out


def test_declared_lane_must_match_ssot(tmp_path):
    good = """\
    env:
      PYTHON_LANE: oracle
    jobs:
      j:
        steps:
          - run: pip install oraclepkg && jq '.lanes[env.PYTHON_LANE]' ssot/python_versions.lanes.json
    """
    root = make_repo(tmp_path, {"w.yml": good})
    run(root, "sync")
    assert run(root, "check") == 0
    path = root / ".github/workflows/w.yml"
    path.write_text(path.read_text().replace("PYTHON_LANE: oracle", "PYTHON_LANE: default"))
    assert run(root, "check") == 1


def test_sync_refuses_while_unhandled_sites_exist(tmp_path):
    root = make_repo(tmp_path, {"w.yml": "jobs:\n  j:\n    steps:\n      - run: uv python install 3.19\n"})
    assert run(root, "sync") == 2


# --------------------------------------------------------------------------- the real repository


def test_repository_matches_its_ssot():
    assert pv.main(["check", "--root", str(ROOT)]) == 0


def test_real_policy_is_coherent():
    policy = pv.Policy.load(ROOT)
    assert policy.default in policy.supported
    assert not set(policy.end_of_life) & set(policy.supported)
    assert all(pv.vkey(v) > pv.vkey(policy.supported[-1]) for v in policy.experimental)
    for name, cap in policy.caps.items():
        assert cap["max"] in policy.supported, name
        assert cap["reason"].strip(), name
