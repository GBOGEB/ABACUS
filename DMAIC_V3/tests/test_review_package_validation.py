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



def test_w000_externalized_alat_intent_is_provenance_bound():
    validator = _load_validator()

    assert (
        "docs/Q3_Q4_Q5/WHAT_ALAT_IS_REALLY_ASKING.md"
        not in validator.REQUIRED_DOCS
    )
    assert validator.REQUIRED_EXTERNALIZED_ARTIFACTS[
        "tender-alat-intent"
    ] == {
        "state": "externalized_private",
        "external_repo": "GBOGEB/cryoplant-project",
        "original_path": (
            "docs/Q3_Q4_Q5/WHAT_ALAT_IS_REALLY_ASKING.md"
        ),
        "provenance_path": "tender_library/PROVENANCE.csv",
        "sha256": (
            "03a0d496913d642102358492a2000363"
            "e61fde352159dfc67fa43559584c3a45"
        ),
    }


def test_w000_rejects_unregistered_externalized_artifact(monkeypatch):
    validator = _load_validator()
    approved = {
        "id": "tender-alat-intent",
        "domain": "tender_review_package",
        **validator.REQUIRED_EXTERNALIZED_ARTIFACTS["tender-alat-intent"],
    }
    unregistered = {
        "id": "unregistered-artifact",
        "domain": "tender_review_package",
        "state": "externalized_private",
        "external_repo": "example/private-repo",
        "original_path": "docs/private.md",
        "provenance_path": "PROVENANCE.csv",
        "sha256": "0" * 64,
    }
    monkeypatch.setattr(
        validator,
        "_read_yaml",
        lambda _path: {"artifacts": [approved, unregistered]},
    )
    errors = []

    validator._validate_manifest(errors)

    assert (
        "unregistered-artifact is not an approved externalized artifact"
        in errors
    )
