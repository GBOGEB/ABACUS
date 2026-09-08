import json
from pathlib import Path

from models.qps_line_b.run_p05h_p05i_receipts import DEFAULT_SOURCE, emit


ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "docs/qps_line_b/generated"


def test_p05h_p05i_generator_matches_committed_semantics(tmp_path):
    written = emit(DEFAULT_SOURCE, tmp_path)
    assert {p.name for p in written} == {
        "P05H_DN150_VALIDATION_RECEIPT.json",
        "P05I_DISTRIBUTED_VLP_THERMO_LINES_CHECK.json",
    }
    for generated in written:
        expected = CURRENT / generated.name
        assert expected.is_file()
        assert json.loads(generated.read_text()) == json.loads(expected.read_text())
