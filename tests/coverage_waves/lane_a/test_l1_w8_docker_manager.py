"""Behaviour tests for DMAIC_V3/infrastructure/docker_manager.py.

The real ``docker`` SDK is not installed in CI, so a fake ``docker`` module is
inserted into ``sys.modules`` (via monkeypatch, undone after each test) before
the production module is loaded. No docker daemon is contacted.
"""

import sys
import types

import pytest

from tests.coverage_waves.lane_a._load import load

MOD_NAME = "l1_w8_docker_manager_under_test"


class FakeContainer:
    def __init__(self, name="c", status="running", attrs=None, logs=b"hello"):
        self.name = name
        self.status = status
        self.attrs = attrs or {}
        self._logs = logs
        self.calls = []
        self.fail = set()
        self.reload_statuses = []

    def _maybe_fail(self, op):
        self.calls.append(op)
        if op in self.fail:
            raise RuntimeError(op + " failed")

    def start(self):
        self._maybe_fail("start")
        self.status = "running"

    def stop(self):
        self._maybe_fail("stop")

    def remove(self):
        self._maybe_fail("remove")

    def reload(self):
        self._maybe_fail("reload")
        if self.reload_statuses:
            self.status = self.reload_statuses.pop(0)

    def logs(self, tail):
        self._maybe_fail("logs")
        self.calls.append(("tail", tail))
        return self._logs


class FakeContainers:
    def __init__(self):
        self.existing = []
        self.run_result = FakeContainer(name="new")
        self.run_kwargs = None
        self.list_kwargs = None
        self.raise_on_list = None

    def list(self, **kwargs):
        self.list_kwargs = kwargs
        if self.raise_on_list:
            raise self.raise_on_list
        return self.existing

    def run(self, image, **kwargs):
        self.run_kwargs = dict(kwargs, image=image)
        return self.run_result


class FakeClient:
    def __init__(self):
        self.containers = FakeContainers()


def make_fake_docker(client=None, error=None):
    fake = types.ModuleType("docker")

    def from_env():
        if error is not None:
            raise error
        return client

    fake.from_env = from_env
    fake.models = types.SimpleNamespace(
        containers=types.SimpleNamespace(Container=FakeContainer)
    )
    return fake


@pytest.fixture
def client():
    return FakeClient()


@pytest.fixture
def dm(monkeypatch, client):
    monkeypatch.setitem(sys.modules, "docker", make_fake_docker(client))
    module = load("DMAIC_V3/infrastructure/docker_manager.py", name=MOD_NAME)
    yield module
    sys.modules.pop(MOD_NAME, None)


@pytest.fixture
def mgr(dm):
    return dm.DockerInfrastructureManager()


def svc(dm, name="svc", ports=None, health=None, stype=None):
    return dm.ServiceConfig(
        name=name,
        service_type=stype or dm.ServiceType.LISTENING,
        image="img:1",
        ports={"80": 0} if ports is None else ports,
        environment={"E": "1"},
        volumes={},
        always_running=True,
        health_check=health,
    )


def test_service_config_defaults(dm):
    c = svc(dm)
    assert c.restart_policy == "unless-stopped"
    assert c.health_check is None
    assert dm.ServiceType.QUALITY_ASSURANCE.value == "qa"


def test_port_manager_allocate_reuse_release(dm):
    pm = dm.PortManager()
    p1 = pm.allocate_port("a", dm.ServiceType.MONITORING)
    p2 = pm.allocate_port("b", dm.ServiceType.MONITORING)
    assert (p1, p2) == (8100, 8101)
    assert pm.allocate_port("a", dm.ServiceType.MONITORING) == 8100
    assert pm.get_port("b") == 8101
    pm.release_port("a")
    pm.release_port("unknown")
    assert pm.get_port("a") is None
    assert pm.allocate_port("c", dm.ServiceType.MONITORING) == 8100


def test_port_manager_exhausted(dm):
    pm = dm.PortManager()
    for i in range(100):
        pm.allocate_port("s" + str(i), dm.ServiceType.TURN_BASED)
    with pytest.raises(RuntimeError, match="No available ports"):
        pm.allocate_port("overflow", dm.ServiceType.TURN_BASED)


def test_init_docker_available(mgr, client):
    assert mgr.docker_available is True
    assert mgr.client is client
    assert mgr.services == {}
    assert mgr.containers == {}


def test_init_docker_unavailable(monkeypatch):
    fake = make_fake_docker(error=ConnectionError("no daemon"))
    monkeypatch.setitem(sys.modules, "docker", fake)
    module = load("DMAIC_V3/infrastructure/docker_manager.py", name=MOD_NAME)
    try:
        m = module.DockerInfrastructureManager()
        assert m.docker_available is False
        assert m.client is None
        m.register_service(svc(module))
        assert m.start_service("svc") is False
    finally:
        sys.modules.pop(MOD_NAME, None)


def test_register_service_auto_and_fixed_ports(dm, mgr):
    c = svc(dm, ports={"80": 0, "443": 9443})
    mgr.register_service(c)
    assert mgr.services["svc"] is c
    assert c.ports == {"80": 8000, "443": 9443}
    assert mgr.port_manager.get_port("svc:80") == 8000


def test_start_unregistered(mgr):
    assert mgr.start_service("ghost") is False


def test_start_existing_stopped_container(dm, mgr, client):
    existing = FakeContainer(status="exited")
    client.containers.existing = [existing]
    mgr.register_service(svc(dm))
    assert mgr.start_service("svc") is True
    assert existing.calls == ["start"]
    assert mgr.containers["svc"] is existing
    assert client.containers.list_kwargs == {"all": True, "filters": {"name": "svc"}}


def test_start_existing_running_container(dm, mgr, client):
    existing = FakeContainer(status="running")
    client.containers.existing = [existing]
    mgr.register_service(svc(dm))
    assert mgr.start_service("svc") is True
    assert existing.calls == []


def test_start_new_container_without_health(dm, mgr, client):
    mgr.register_service(svc(dm, ports={"80": 1234}))
    assert mgr.start_service("svc") is True
    kw = client.containers.run_kwargs
    assert kw["image"] == "img:1"
    assert kw["ports"] == {"80/tcp": 1234}
    assert kw["detach"] is True
    assert kw["restart_policy"] == {"Name": "unless-stopped"}
    assert mgr.containers["svc"] is client.containers.run_result


def test_start_new_container_with_health(dm, mgr, client, monkeypatch):
    seen = []
    monkeypatch.setattr(
        mgr, "_wait_for_health", lambda c, hc: seen.append((c, hc)) or True
    )
    mgr.register_service(svc(dm, health={"interval": 1}))
    assert mgr.start_service("svc") is True
    assert seen == [(client.containers.run_result, {"interval": 1})]


def test_start_service_error(dm, mgr, client):
    client.containers.raise_on_list = RuntimeError("api down")
    mgr.register_service(svc(dm))
    assert mgr.start_service("svc") is False


def test_stop_unknown_is_noop(mgr):
    mgr.stop_service("ghost")


def test_stop_without_remove_keeps_container(mgr):
    c = FakeContainer()
    mgr.containers["svc"] = c
    mgr.stop_service("svc")
    assert c.calls == ["stop"]
    assert "svc" in mgr.containers


def test_stop_with_remove(mgr):
    c = FakeContainer()
    mgr.containers["svc"] = c
    mgr.stop_service("svc", remove=True)
    assert c.calls == ["stop", "remove"]
    assert "svc" not in mgr.containers


def test_stop_error_is_logged(mgr, caplog):
    c = FakeContainer()
    c.fail.add("stop")
    mgr.containers["svc"] = c
    mgr.stop_service("svc", remove=True)
    assert "svc" in mgr.containers
    assert "Failed to stop service svc" in caplog.text


def test_status(mgr):
    assert mgr.get_service_status("ghost") is None
    c = FakeContainer(status="created")
    c.reload_statuses = ["running"]
    mgr.containers["svc"] = c
    assert mgr.get_service_status("svc") == "running"
    c.fail.add("reload")
    assert mgr.get_service_status("svc") is None


def test_logs(mgr):
    assert mgr.get_service_logs("ghost") == ""
    c = FakeContainer(logs="héllo".encode("utf-8"))
    mgr.containers["svc"] = c
    assert mgr.get_service_logs("svc", tail=5) == "héllo"
    assert ("tail", 5) in c.calls
    c.fail.add("logs")
    assert mgr.get_service_logs("svc") == ""


def test_cleanup_all(mgr):
    a = FakeContainer()
    b = FakeContainer()
    b.fail.add("stop")
    mgr.containers.update(a=a, b=b)
    mgr.cleanup_all()
    assert mgr.containers == {}
    assert a.calls == ["stop", "remove"]


def fake_clock(monkeypatch, dm, times):
    seq = list(times)
    monkeypatch.setattr(dm.time, "time", lambda: seq.pop(0) if seq else 10**6)
    sleeps = []
    monkeypatch.setattr(dm.time, "sleep", sleeps.append)
    return sleeps


def test_wait_for_health_running_no_test(dm, mgr, monkeypatch):
    sleeps = fake_clock(monkeypatch, dm, [0, 0, 1])
    c = FakeContainer(status="created")
    c.reload_statuses = ["created", "running"]
    assert mgr._wait_for_health(c, {}) is True
    assert sleeps == [1]


def test_wait_for_health_healthy(dm, mgr, monkeypatch):
    sleeps = fake_clock(monkeypatch, dm, [0, 0, 1, 2])
    c = FakeContainer(status="running")
    c.attrs = {"State": {"Health": {"Status": "starting"}}}

    def reload():
        c.calls.append("reload")
        if c.calls.count("reload") == 2:
            c.attrs = {"State": {"Health": {"Status": "healthy"}}}

    c.reload = reload
    assert mgr._wait_for_health(c, {"test": ["CMD", "true"]}) is True
    assert sleeps == [1]


def test_wait_for_health_timeout(dm, mgr, monkeypatch):
    sleeps = fake_clock(monkeypatch, dm, [0, 0, 31])
    c = FakeContainer(name="slow", status="exited")
    with pytest.raises(TimeoutError, match="slow did not become healthy"):
        mgr._wait_for_health(c, {"test": []})
    assert sleeps == [1]


def test_create_infrastructure_manager(dm):
    m = dm.create_infrastructure_manager()
    assert set(m.services) == set(dm.DMAIC_SERVICES)
    assert dm.DMAIC_SERVICES["dmaic_api"].ports == {"8000": 8000}
    assert dm.DMAIC_SERVICES["dmaic_reconciler"].ports == {"8800": 8800}
    assert dm.DMAIC_SERVICES["dmaic_debugger"].always_running is False
