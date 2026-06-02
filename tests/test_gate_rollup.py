import json
from pathlib import Path

from tools.gate_rollup import build_gate_rollup, write_gate_rollup


def test_build_gate_rollup_handles_missing_log_file(tmp_path: Path) -> None:
    payload = build_gate_rollup(log_path=tmp_path / "missing.jsonl")

    assert payload["schema_version"] == 1
    assert payload["prs"] == []
    assert payload["generated_at"].endswith("Z")
    assert payload["source"]["records_read"] == 0
    assert payload["source"]["records_used"] == 0
    assert payload["source"]["malformed_lines"] == 0


def test_build_gate_rollup_parses_failures_and_first_failed_gate(tmp_path: Path) -> None:
    log_path = tmp_path / "ci-runs.jsonl"
    log_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "pr_id": 12,
                        "timestamp": "2026-06-01T10:00:00Z",
                        "gate_name": "lint",
                        "exit_code": 0,
                    }
                ),
                "not-json",
                json.dumps(
                    {
                        "pr_id": 12,
                        "timestamp": "2026-06-01T10:05:00Z",
                        "gate_name": "test",
                        "exit_code": 1,
                    }
                ),
                json.dumps(
                    {
                        "pr_id": 12,
                        "timestamp": "2026-06-01T10:02:00Z",
                        "gate_name": "build",
                        "exit_code": 2,
                    }
                ),
                json.dumps({"pr_id": 12, "gate_name": "security", "exit_code": 9}),
                json.dumps({"pr_id": 12, "timestamp": "2026-06-01T10:03:00Z", "exit_code": 1}),
                json.dumps(
                    {
                        "pr_id": 13,
                        "timestamp": "2026-06-01T09:00:00Z",
                        "gate_name": "lint",
                        "exit_code": 0,
                    }
                ),
                json.dumps(
                    {
                        "pr_id": 13,
                        "timestamp": "2026-06-01T10:00:00+01:00",
                        "gate_name": "deploy",
                        "exit_code": "2",
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    payload = build_gate_rollup(log_path=log_path)

    assert payload["source"]["records_read"] == 8
    assert payload["source"]["records_used"] == 7
    assert payload["source"]["malformed_lines"] == 1

    assert [row["pr_id"] for row in payload["prs"]] == ["12", "13"]
    pr12 = payload["prs"][0]
    assert pr12["status"] == "FAIL"
    assert pr12["first_failed_gate"] == "build"
    assert pr12["failed_gates"] == ["build", "test", "security"]
    assert pr12["total_gates_run"] == 4
    assert pr12["last_updated"] == "2026-06-01T10:05:00Z"

    pr13 = payload["prs"][1]
    assert pr13["status"] == "FAIL"
    assert pr13["first_failed_gate"] == "deploy"
    assert pr13["failed_gates"] == ["deploy"]
    assert pr13["total_gates_run"] == 2
    assert pr13["last_updated"] == "2026-06-01T09:00:00Z"


def test_write_gate_rollup_creates_output_directory(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "ci-runs.jsonl"
    output_path = tmp_path / "docs" / "dashboard-gates.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("", encoding="utf-8")

    written = write_gate_rollup(output_path=output_path, log_path=log_path)

    assert written == output_path
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["prs"] == []
