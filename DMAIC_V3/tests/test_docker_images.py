import os
import shutil
import subprocess
import pytest

pytestmark = [pytest.mark.docker, pytest.mark.integration]


def docker_enabled():
    """Check if Docker tests are enabled via environment variable."""
    return os.environ.get("DMAIC_DOCKER_TESTS", "0") == "1"


@pytest.mark.skipif(
    not docker_enabled(), reason="DMAIC_DOCKER_TESTS != 1; docker tests disabled"
)
def test_docker_binary_available():
    """Verify docker CLI is available in PATH."""
    assert shutil.which("docker") is not None, "'docker' must be in PATH"


@pytest.mark.skipif(
    not docker_enabled(), reason="DMAIC_DOCKER_TESTS != 1; docker tests disabled"
)
def test_docker_version_runs():
    """Verify docker --version command executes successfully."""
    result = subprocess.run(
        ["docker", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"docker --version failed: {result.stderr}"
    assert "version" in result.stdout.lower()


@pytest.mark.skipif(
    not docker_enabled(), reason="DMAIC_DOCKER_TESTS != 1; docker tests disabled"
)
def test_docker_info_accessible():
    """Verify docker info command works (daemon is running)."""
    result = subprocess.run(
        ["docker", "info"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"Docker daemon not running: {result.stderr}")
    assert "Server Version" in result.stdout or "server version" in result.stdout.lower()


@pytest.mark.skipif(
    not docker_enabled(), reason="DMAIC_DOCKER_TESTS != 1; docker tests disabled"
)
def test_docker_hello_world_image():
    """Test pulling and running hello-world image (if enabled)."""
    if os.environ.get("DMAIC_DOCKER_PULL_TESTS", "0") != "1":
        pytest.skip("DMAIC_DOCKER_PULL_TESTS != 1; skipping image pull test")
    
    result = subprocess.run(
        ["docker", "run", "--rm", "hello-world"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"docker run hello-world failed: {result.stderr}"
    assert "Hello from Docker" in result.stdout
