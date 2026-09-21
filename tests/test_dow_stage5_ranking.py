from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
STAGE5 = (
    ROOT
    / "DMAIC_V3"
    / "local_mcp"
    / "agents"
    / "recursive_self_ranking_v2.3_OPTIMIZED.py"
)


def test_stage5_executes_parent_ranking_mechanic(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    fixture = target / "fixture.json"
    fixture.write_text(
        json.dumps(
            {
                "metadata": {"phase": "test"},
                "payload": "x" * 256,
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "ranking.json"

    result = subprocess.run(
        [
            sys.executable,
            str(STAGE5),
            "--target",
            str(target),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == "abacus-dow-self-ranking/v1"
    assert payload["engine_version"] == "3.3.0"
    assert payload["total_artifacts"] == 1
    assert payload["ranked_artifacts"][0]["path"] == str(fixture)
    assert "rank_score" in payload["ranked_artifacts"][0]


def test_stage5_fails_closed_without_json_artifacts(tmp_path: Path) -> None:
    target = tmp_path / "empty"
    target.mkdir()

    result = subprocess.run(
        [
            sys.executable,
            str(STAGE5),
            "--target",
            str(target),
            "--output",
            str(tmp_path / "ranking.json"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode != 0
    assert "No JSON artifacts found" in result.stdout
