"""Behaviour tests for qplant/config_service/client.py.

The HTTP client never touches the network: ``requests`` is replaced on each
client instance by a recording fake.
"""

import builtins
import sys

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

mod = load("qplant/config_service/client.py", name="abn_w5_config_client")


class _Resp:
    def __init__(self, payload, error=None):
        self.payload = payload
        self.error = error

    def raise_for_status(self):
        if self.error is not None:
            raise self.error

    def json(self):
        return self.payload


class _FakeRequests:
    def __init__(self, payload=None, error=None):
        self.payload = payload if payload is not None else {}
        self.error = error
        self.calls = []

    def get(self, url, timeout):
        self.calls.append(("GET", url, None, timeout))
        return _Resp(self.payload, self.error)

    def post(self, url, json, timeout):
        self.calls.append(("POST", url, json, timeout))
        return _Resp(self.payload, self.error)


def _client(payload=None, error=None, base="http://cfg.local:9000/"):
    client = mod.ConfigClient(base)
    fake = _FakeRequests(payload, error)
    client._requests = fake
    return client, fake


def test_base_url_trailing_slash_stripped_and_requests_bound():
    client = mod.ConfigClient("http://host:1/")
    assert client.base_url == "http://host:1"
    assert client._requests is not None
    assert mod.ConfigClient().base_url == "http://localhost:8200"


@pytest.mark.parametrize(
    "method,path",
    [
        ("health", "/api/v1/health"),
        ("get_all", "/api/v1/config"),
        ("validate", "/api/v1/config/validate"),
        ("get_schema", "/api/v1/config/schema"),
        ("get_history", "/api/v1/config/history"),
    ],
)
def test_simple_get_endpoints_return_json(method, path):
    payload = {"ok": True, "m": method}
    client, fake = _client(payload)
    assert getattr(client, method)() == payload
    assert fake.calls == [("GET", "http://cfg.local:9000" + path, None, 10)]


def test_get_section_builds_section_url():
    client, fake = _client({"count": 3})
    assert client.get_section("compressors") == {"count": 3}
    assert fake.calls[0][1] == "http://cfg.local:9000/api/v1/config/section/compressors"


def test_get_value_unwraps_value_key():
    client, fake = _client({"value": 42, "path": "a.b"})
    assert client.get_value("a.b") == 42
    assert fake.calls[0][1].endswith("/api/v1/config/value?path=a.b")


def test_get_value_missing_key_is_none():
    client, _ = _client({"other": 1})
    assert client.get_value("x") is None


def test_set_value_posts_payload_with_defaults():
    client, fake = _client({"status": "ok"})
    assert client.set_value("a.b", 7) == {"status": "ok"}
    method, url, body, timeout = fake.calls[0]
    assert method == "POST"
    assert url.endswith("/api/v1/config/set")
    assert body == {"path": "a.b", "value": 7, "user": "sdk", "reason": ""}
    assert timeout == 10


def test_set_value_custom_user_and_reason():
    client, fake = _client({})
    client.set_value("p", [1], user="ops", reason="tune")
    assert fake.calls[0][2] == {
        "path": "p",
        "value": [1],
        "user": "ops",
        "reason": "tune",
    }


def test_reload_posts_empty_body():
    client, fake = _client({"reloaded": True})
    assert client.reload() == {"reloaded": True}
    assert fake.calls == [
        ("POST", "http://cfg.local:9000/api/v1/config/reload", {}, 10)
    ]


def test_get_hash_returns_hash_or_empty():
    client, _ = _client({"hash": "abc123"})
    assert client.get_hash() == "abc123"
    client2, _ = _client({"nohash": 1})
    assert client2.get_hash() == ""


def test_http_error_propagates_from_raise_for_status():
    client, _ = _client({}, error=ValueError("HTTP 500"))
    with pytest.raises(ValueError, match="HTTP 500"):
        client.get_all()
    with pytest.raises(ValueError, match="HTTP 500"):
        client.reload()


def test_missing_requests_logs_warning_and_raises_on_use(monkeypatch, caplog):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "requests":
            raise ImportError("no requests")
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(sys.modules, "requests", raising=False)
    monkeypatch.setattr(builtins, "__import__", fake_import)
    with caplog.at_level("WARNING"):
        client = mod.ConfigClient()
    monkeypatch.setattr(builtins, "__import__", real_import)
    assert client._requests is None
    assert "requests library not available" in caplog.text
    with pytest.raises(RuntimeError, match="requests library required"):
        client.health()
    with pytest.raises(RuntimeError, match="requests library required"):
        client.set_value("a", 1)


CONFIG_YAML = b"""version: '4.4'
compressor_specifications:
  hp_compressors:
    count: 3
  names: [a, b]
financial:
  total: 600000
"""


@pytest.fixture
def cfg_file(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_bytes(CONFIG_YAML)
    return path


def test_direct_client_reads_yaml(cfg_file):
    client = mod.DirectConfigClient(str(cfg_file))
    data = client.get_all()
    assert data["version"] == "4.4"
    data["version"] = "mutated"
    assert client.get_all()["version"] == "4.4"


def test_direct_get_section_and_missing(cfg_file):
    client = mod.DirectConfigClient(str(cfg_file))
    assert client.get_section("financial") == {"total": 600000}
    with pytest.raises(KeyError, match="Section not found: nope"):
        client.get_section("nope")


def test_direct_get_value_nested_and_errors(cfg_file):
    client = mod.DirectConfigClient(str(cfg_file))
    assert client.get_value("compressor_specifications.hp_compressors.count") == 3
    assert client.get_value("version") == "4.4"
    with pytest.raises(KeyError, match="Path not found: financial.missing"):
        client.get_value("financial.missing")
    # descending into a non-dict (a list) fails cleanly
    with pytest.raises(KeyError, match="Path not found"):
        client.get_value("compressor_specifications.names.0")


def test_direct_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="Config not found"):
        mod.DirectConfigClient(str(tmp_path / "absent.yaml"))


def test_direct_empty_file_is_empty_dict_and_reload_picks_up_changes(cfg_file):
    cfg_file.write_bytes(b"")
    client = mod.DirectConfigClient(str(cfg_file))
    assert client.get_all() == {}
    cfg_file.write_bytes(b"a: 1\n")
    client.reload()
    assert client.get_all() == {"a": 1}
    assert client.get_value("a") == 1


def test_direct_default_path_relative_to_cwd(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "config.yaml").write_bytes(b"k: v\n")
    monkeypatch.chdir(tmp_path)
    client = mod.DirectConfigClient()
    assert client.get_section("k") == "v"
