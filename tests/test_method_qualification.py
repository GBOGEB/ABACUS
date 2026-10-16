import importlib.util
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"scripts"/"method_qualification.py"
spec=importlib.util.spec_from_file_location("method_qualification",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
def sample():
    return dict(repository="ABACUS",source_sha="a"*40,method_id="security-sast",
        tool_version="1",config_digest="b"*64,corpus_digest="c"*64,
        run_id=1,job_id=2,attempt=1,tp=1,fp=0,fn=0,tn=1,
        runtime_seconds=0.1,repair_receipt=None,negative_controls_pass=False,
        federation_receipts=[],adaptive_receipt=None)
def test_unknown_fails_closed():
    e=sample();del e["job_id"]
    assert m.qualify(e)["state"]=="UNKNOWN"
def test_m2_not_repair():
    assert m.qualify(sample())["level"]=="M2"
def test_m4_negative_and_repair():
    e=sample();e.update(repair_receipt="root",negative_controls_pass=True)
    assert m.qualify(e)["level"]=="M4"
def test_false_negative_blocks_m4():
    e=sample();e.update(fn=1,repair_receipt="root",negative_controls_pass=True)
    assert m.qualify(e)["level"]=="M3"
def test_m6_not_admission():
    e=sample();e.update(repair_receipt="root",negative_controls_pass=True,
        federation_receipts=["CODEX","QPS"],adaptive_receipt="trial")
    assert m.qualify(e)["level"]=="M6"
    assert m.qualify(e)["merge_authorized"] is False
def test_negative_count_invalid():
    e=sample();e["tp"]=-1
    assert m.qualify(e)["state"]=="INVALID"
