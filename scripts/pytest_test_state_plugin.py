"""Governed pytest test-state taxonomy and skip enforcement for ABACUS."""

from __future__ import annotations

import pytest


TEST_STATES = (
    "NO_TEST",
    "TEST_EXISTS_UNCOLLECTED",
    "TEST_BLOCKED_DEPENDENCY",
    "TEST_BLOCKED_CONFIG",
    "TEST_BLOCKED_SOURCE_MISSING",
    "TEST_NOT_IMPLEMENTED",
    "TEST_FAILING",
    "TEST_GREEN",
)

BLOCKING_STATES = frozenset(
    {
        "TEST_BLOCKED_DEPENDENCY",
        "TEST_BLOCKED_CONFIG",
        "TEST_BLOCKED_SOURCE_MISSING",
        "TEST_NOT_IMPLEMENTED",
    }
)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--govern-test-states",
        action="store_true",
        default=False,
        help="Fail canonical execution on uncategorized skips.",
    )


def pytest_configure(config: pytest.Config) -> None:
    for state in TEST_STATES:
        config.addinivalue_line(
            "markers",
            f"{state}: governed ABACUS test-evidence state",
        )


def _marker_states(item: pytest.Item) -> list[str]:
    return [state for state in TEST_STATES if item.get_closest_marker(state)]


def _set_property(item: pytest.Item, name: str, value: str) -> None:
    item.user_properties[:] = [
        (key, current)
        for key, current in item.user_properties
        if key != name
    ]
    item.user_properties.append((name, value))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[object]):
    """Record one governed state per executed item and reject unclassified skips."""

    outcome = yield
    report = outcome.get_result()

    if report.when == "setup" and report.passed:
        return
    if report.when not in {"setup", "call"}:
        return

    was_xfail = bool(getattr(report, "wasxfail", False))
    marker_states = _marker_states(item)

    if was_xfail:
        state = "TEST_FAILING"
        source = "xfail"
        _set_property(item, "xfail", "true")
    elif report.skipped:
        blocking = [state for state in marker_states if state in BLOCKING_STATES]
        if len(blocking) != 1:
            if item.config.getoption("--govern-test-states"):
                message = (
                    "Skipped test must carry exactly one governed blocking marker: "
                    + ", ".join(sorted(BLOCKING_STATES))
                )
                report.outcome = "failed"
                report.longrepr = message
                state = "TEST_FAILING"
                source = "skip_enforcement"
            else:
                state = "TEST_EXISTS_UNCOLLECTED"
                source = "ungoverned_report_only"
        else:
            state = blocking[0]
            source = "marker"
    elif report.failed:
        state = "TEST_FAILING"
        source = "outcome"
    elif report.when == "call":
        state = "TEST_GREEN"
        source = "outcome"
    else:
        return

    _set_property(item, "test_state", state)
    _set_property(item, "test_state_source", source)
    report.user_properties = list(item.user_properties)
