from pathlib import Path
import importlib.util, json
HERE=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location("profile",HERE/"validate_review_profile.py"); M=importlib.util.module_from_spec(SPEC); assert SPEC.loader is not None; SPEC.loader.exec_module(M)

def test_profile_contract():
    data=json.loads((HERE/"review_profile.json").read_text(encoding="utf-8"))
    assert M.validate(data)==[]
