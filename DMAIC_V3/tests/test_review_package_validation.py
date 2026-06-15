import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_review_package.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location(
        "validate_review_package",
        VALIDATOR_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_w000_review_package_validates_cleanly():
    validator = _load_validator()

    assert validator.validate_review_package() == []


def test_w000_validator_tracks_required_bootstrap_domains():
    validator = _load_validator()

    assert validator.REQUIRED_DOMAINS == {
        "ssot_registry",
        "contractual_gap_register",
        "governance_controls",
        "ci_cd_scaffolding",
        "tender_review_package",
    }
