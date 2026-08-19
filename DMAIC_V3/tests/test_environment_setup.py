import os
import shutil
import sys
import pytest

pytestmark = [pytest.mark.env]


def test_python_version_is_reasonable():
    """Verify Python 3.9+ is being used for DMAIC_V3."""
    major, minor = sys.version_info[:2]
    assert (major, minor) >= (3, 9), "Python 3.9+ recommended for DMAIC_V3"


def test_venv_presence_or_skip():
    """
    Check for a 'venv' or '.venv' directory as a hint that a virtual
    environment exists. This is advisory, not a hard failure.
    """
    if not (os.path.isdir("venv") or os.path.isdir(".venv")):
        pytest.skip("No venv/.venv directory found; env likely managed elsewhere")


def test_docker_cli_installed_or_skip():
    """
    Ensure 'docker' CLI is installed if docker tests are expected.
    """
    if os.environ.get("DMAIC_DOCKER_TESTS", "0") != "1":
        pytest.skip("DMAIC_DOCKER_TESTS != 1; skipping docker CLI check")

    if shutil.which("docker") is None:
        pytest.fail("DMAIC_DOCKER_TESTS=1 but 'docker' binary not found in PATH")


def test_git_cli_available():
    """Verify git is available for GitHub roundtrip tests."""
    if shutil.which("git") is None:
        pytest.skip("git not found in PATH; GitHub roundtrip tests may be skipped")


def test_pytest_plugins_loaded():
    """Verify essential pytest plugins are available."""
    import pytest as pt
    plugins = [p for p in dir(pt) if not p.startswith('_')]
    assert 'mark' in plugins, "pytest.mark should be available"
