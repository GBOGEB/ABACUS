"""Behaviour tests for scripts/pytest_test_state_plugin.py.

The hook functions are called directly with fake parser/config/item/report
objects; the plugin is never registered into the running pytest session.
"""

from types import SimpleNamespace

import pytest

from tests.coverage_waves.lane_b._l2_loader import load

plugin = load("scripts/pytest_test_state_plugin.py", name="abn_test_state_plugin")


class _Parser:
    def __init__(self):
        self.options = []

    def addoption(self, *args, **kwargs):
        self.options.append((args, kwargs))


class _Config:
    def __init__(self, govern=False):
        self.govern = govern
        self.lines = []

    def addinivalue_line(self, name, line):
        self.lines.append((name, line))

    def getoption(self, name):
        assert name == "--govern-test-states"
        return self.govern


class _Item:
    def __init__(self, markers=(), govern=False, props=None):
        self.markers = set(markers)
        self.config = _Config(govern)
        self.user_properties = list(props or [])

    def get_closest_marker(self, name):
        return SimpleNamespace(name=name) if name in self.markers else None


def _report(when, outcome="passed", wasxfail=None):
    rep = SimpleNamespace(when=when, outcome=outcome, longrepr=None, user_properties=[])
    if wasxfail is not None:
        rep.wasxfail = wasxfail
    return rep


class _ReportProxy:
    """Expose passed/skipped/failed derived from ``outcome`` like TestReport."""

    def __init__(self, rep):
        self.__dict__["_rep"] = rep

    def __getattr__(self, name):
        if name in ("passed", "skipped", "failed"):
            return self._rep.outcome == name
        return getattr(self._rep, name)

    def __setattr__(self, name, value):
        setattr(self._rep, name, value)


def _drive(item, rep):
    proxy = _ReportProxy(rep)
    gen = plugin.pytest_runtest_makereport(item, None)
    next(gen)
    with pytest.raises(StopIteration):
        gen.send(SimpleNamespace(get_result=lambda: proxy))
    return dict(item.user_properties)


def test_state_constants():
    assert len(plugin.TEST_STATES) == 8
    assert plugin.BLOCKING_STATES < set(plugin.TEST_STATES)
    assert "TEST_GREEN" not in plugin.BLOCKING_STATES


def test_addoption_registers_govern_flag():
    parser = _Parser()
    plugin.pytest_addoption(parser)
    args, kwargs = parser.options[0]
    assert args == ("--govern-test-states",)
    assert kwargs["action"] == "store_true"
    assert kwargs["default"] is False


def test_configure_registers_one_marker_per_state():
    config = _Config()
    plugin.pytest_configure(config)
    assert [n for n, _ in config.lines] == ["markers"] * len(plugin.TEST_STATES)
    assert config.lines[0][1].startswith("NO_TEST:")


def test_marker_states_and_set_property_replace_existing():
    item = _Item(markers={"TEST_GREEN", "NO_TEST", "unrelated"})
    assert plugin._marker_states(item) == ["NO_TEST", "TEST_GREEN"]
    item.user_properties[:] = [("a", "1"), ("k", "old"), ("b", "2")]
    plugin._set_property(item, "k", "new")
    assert item.user_properties == [("a", "1"), ("b", "2"), ("k", "new")]


def test_setup_pass_records_nothing():
    item = _Item()
    assert _drive(item, _report("setup")) == {}


def test_teardown_records_nothing():
    item = _Item()
    assert _drive(item, _report("teardown", "failed")) == {}


def test_call_pass_records_green_and_copies_properties():
    item = _Item(props=[("other", "x")])
    rep = _report("call")
    props = _drive(item, rep)
    assert props["test_state"] == "TEST_GREEN"
    assert props["test_state_source"] == "outcome"
    assert rep.user_properties == item.user_properties
    assert rep.user_properties is not item.user_properties


def test_call_failure_records_failing():
    props = _drive(_Item(), _report("call", "failed"))
    assert props["test_state"] == "TEST_FAILING"
    assert props["test_state_source"] == "outcome"


def test_setup_failure_records_failing():
    props = _drive(_Item(), _report("setup", "failed"))
    assert props["test_state"] == "TEST_FAILING"


def test_xfail_records_failing_with_flag():
    props = _drive(_Item(), _report("call", "skipped", wasxfail="reason"))
    assert props["test_state"] == "TEST_FAILING"
    assert props["test_state_source"] == "xfail"
    assert props["xfail"] == "true"


def test_skip_with_one_blocking_marker_uses_marker_state():
    item = _Item(markers={"TEST_BLOCKED_DEPENDENCY", "NO_TEST"})
    props = _drive(item, _report("setup", "skipped"))
    assert props["test_state"] == "TEST_BLOCKED_DEPENDENCY"
    assert props["test_state_source"] == "marker"


def test_ungoverned_skip_is_report_only():
    rep = _report("call", "skipped")
    props = _drive(_Item(govern=False), rep)
    assert props["test_state"] == "TEST_EXISTS_UNCOLLECTED"
    assert props["test_state_source"] == "ungoverned_report_only"
    assert rep.outcome == "skipped"


def test_governed_skip_without_marker_is_turned_into_failure():
    rep = _report("call", "skipped")
    props = _drive(_Item(govern=True), rep)
    assert rep.outcome == "failed"
    assert rep.longrepr.startswith("Skipped test must carry exactly one")
    assert "TEST_BLOCKED_CONFIG" in rep.longrepr
    assert props["test_state"] == "TEST_FAILING"
    assert props["test_state_source"] == "skip_enforcement"


def test_governed_skip_with_two_blocking_markers_fails():
    markers = {"TEST_BLOCKED_CONFIG", "TEST_NOT_IMPLEMENTED"}
    rep = _report("setup", "skipped")
    props = _drive(_Item(markers=markers, govern=True), rep)
    assert rep.outcome == "failed"
    assert props["test_state_source"] == "skip_enforcement"
