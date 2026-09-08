from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_parallel_pilot_executes_two_arms_with_stable_root_ids(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "alpha").mkdir()
    (root / "beta").mkdir()
    (root / "alpha" / "contract.yaml").write_text("authority: canonical\n", encoding="utf-8")
    (root / "beta" / "contract.yaml").write_text("authority: candidate\n", encoding="utf-8")
    (root / "consumer.py").write_text("PATH = 'contract.yaml'\n", encoding="utf-8")

    p2 = tmp_path / "p2.json"
    p2.write_text(
        json.dumps(
            {
                "findings": [
                    {
                        "severity": "blocker",
                        "type": "duplicate_or_competing_authority",
                        "family": "contract",
                        "paths": ["alpha/contract.yaml", "beta/contract.yaml"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "pilot.json"
    script = Path(__file__).parents[1] / "tools" / "w64_3p_parallel_pilot.py"
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--p2",
            str(p2),
            "--root",
            str(root),
            "--out",
            str(out),
            "--sample",
            "1",
            "--discovery-workers",
            "2",
            "--discrimination-workers",
            "2",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["sample_root_items"] == 1
    assert len(payload["stable_root_ids"]) == 1
    assert [arm["arm"] for arm in payload["arms"]] == [
        "ARM_DISCOVERY",
        "ARM_DISCRIMINATION",
    ]
    assert payload["arms"][0]["chain"] == ["3PE", "3PL"]
    assert payload["arms"][1]["chain"] == ["3PC", "3PV"]
    assert payload["DoD"]["same_frozen_root_ids"] is True
    assert payload["DoD"]["all_workers_read_only"] is True
    assert payload["DoD"]["single_writer_not_invoked"] is True
    assert payload["DoD"]["no_release_or_engineering_credit"] is True
    assert payload["comparison"]["discovery_wall_time_ms"] >= 0
    assert payload["comparison"]["discrimination_wall_time_ms"] >= 0
