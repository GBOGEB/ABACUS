"""Unit tests for integration/cryoplant_project/scripts/reciprocal_smoke.py.

The probe itself needs a token for the private member repository, so these
tests replace the GitHub API with a fake and check what the script decides
and records.
"""

import base64
import io
import json

import pytest
import yaml

from integration.cryoplant_project.scripts import reciprocal_smoke

SHA = "a" * 40

ACTIVE_MANIFEST = {
    "federation": {
        "moniker": "DELTA_1",
        "status": "active",
        "self": {"repository": "GBOGEB/cryoplant-project", "plane": "auxiliary"},
        "hub": {"runtime_plane": {"repository": "GBOGEB/ABACUS"}},
    }
}


def fake_api(manifest):
    calls = []

    def api(path, token):
        calls.append((path, token))
        if path.endswith("/commits/main"):
            return {"sha": SHA}
        encoded = base64.b64encode(yaml.safe_dump(manifest).encode()).decode()
        return {"content": encoded}

    return api, calls


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    path = tmp_path / "federation" / "reciprocal_smoke.json"
    monkeypatch.setattr(reciprocal_smoke, "EVIDENCE", path)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    return path


def test_main_requires_a_token(evidence, capsys):
    assert reciprocal_smoke.main() == 2
    assert "GH_TOKEN" in capsys.readouterr().err
    assert not evidence.exists()


def test_main_records_ok_for_an_active_member(evidence, monkeypatch):
    api, calls = fake_api(ACTIVE_MANIFEST)
    monkeypatch.setattr(reciprocal_smoke, "api", api)
    monkeypatch.setenv("GH_TOKEN", "t")

    assert reciprocal_smoke.main() == 0

    receipt = json.loads(evidence.read_text(encoding="utf-8"))
    assert receipt["status"] == "ok"
    assert receipt["direction"] == "GBOGEB/ABACUS -> GBOGEB/cryoplant-project"
    assert receipt["member_main_sha"] == SHA
    assert all(receipt["checks"].values())
    # The manifest is read at the resolved head, not at a moving branch.
    assert calls[1][0].endswith(f"manifest.yaml?ref={SHA}")
    assert {token for _, token in calls} == {"t"}


def test_main_fails_for_a_proposed_member(evidence, monkeypatch):
    proposed = json.loads(json.dumps(ACTIVE_MANIFEST))
    proposed["federation"]["status"] = "proposed"
    api, _ = fake_api(proposed)
    monkeypatch.setattr(reciprocal_smoke, "api", api)
    monkeypatch.setenv("GITHUB_TOKEN", "t")

    assert reciprocal_smoke.main() == 1

    receipt = json.loads(evidence.read_text(encoding="utf-8"))
    assert receipt["status"] == "failed"
    assert receipt["checks"]["member_status_active"] is False


def test_api_sends_the_token_to_the_fixed_github_host(monkeypatch):
    seen = {}

    def urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["auth"] = request.get_header("Authorization")
        seen["timeout"] = timeout
        return io.BytesIO(b'{"sha": "x"}')

    monkeypatch.setattr(reciprocal_smoke.urllib.request, "urlopen", urlopen)

    assert reciprocal_smoke.api("/repos/o/r/commits/main", "t") == {"sha": "x"}
    assert seen == {
        "url": "https://api.github.com/repos/o/r/commits/main",
        "auth": "Bearer t",
        "timeout": 30,
    }
