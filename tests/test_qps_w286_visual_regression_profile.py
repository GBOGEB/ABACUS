import importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
V=ROOT/"qps/visual_regression/w286/validate_review_profile.py"
F=ROOT/"qps/visual_regression/w286/review_profile.json"
S=importlib.util.spec_from_file_location("w286profile",V); M=importlib.util.module_from_spec(S); S.loader.exec_module(M)
def load(): return json.loads(F.read_text(encoding="utf-8"))
def test_profile_passes(): assert M.validate(load())==[]
def test_authority_override_rejected():
    d=load(); d["authority"]="QPS_ENGINEERING_AUTHORITY"; assert "authority" in M.validate(d)
def test_required_dimensions_are_closed():
    d=load(); d["dimensions"]=d["dimensions"][:-1]; assert "dimensions" in M.validate(d)
