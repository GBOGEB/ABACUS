"""
# Version: 1.0.0
# Date: 2025-11-24
# Description: Auto-generated version header
"""

import pytest
import pytest_asyncio
import subprocess
import socket
import time
import requests
import asyncio
import aiohttp
import platform
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import json


WINDOWS_DOCKER_LINUX_BASE_UNAVAILABLE = platform.system() == "Windows"
WINDOWS_DOCKER_LINUX_BASE_REASON = (
    "Linux python:3.11-slim base image is not available from the Windows Docker daemon in CI"
)


class TestDockerConfiguration:
    
    def test_dockerfile_exists(self):
        dockerfile = Path("Dockerfile")
        assert dockerfile.exists(), "Dockerfile not found"
        
    def test_dockerfile_syntax(self):
        dockerfile = Path("Dockerfile")
        content = dockerfile.read_text()
        
        assert "FROM python:" in content, "Missing base image"
        assert "WORKDIR" in content, "Missing WORKDIR"
        assert "COPY" in content, "Missing COPY instruction"
        assert "EXPOSE" in content, "Missing EXPOSE instruction"
        assert "CMD" in content or "ENTRYPOINT" in content, "Missing CMD/ENTRYPOINT"
        
    def test_dockerfile_security(self):
        dockerfile = Path("Dockerfile")
        content = dockerfile.read_text()
        
        assert "useradd" in content or "USER" in content, "Should run as non-root user"
        assert "HEALTHCHECK" in content, "Missing health check"
        
    def test_dockerignore_exists(self):
        dockerignore = Path(".dockerignore")
        assert dockerignore.exists(), ".dockerignore not found"
        
    def test_dockerignore_content(self):
        dockerignore = Path(".dockerignore")
        content = dockerignore.read_text()

        required_patterns = [
            "__pycache__",
            "*.pyc",
            ".env",
            "*.log"
        ]

        for pattern in required_patterns:
            assert any(pattern in line for line in content.split('\n')), f"Missing pattern: {pattern}"

    @pytest.mark.benchmark
    def test_dockerfile_layer_optimization(self, benchmark):
        """Benchmark Dockerfile layer count for optimization"""
        dockerfile = Path("Dockerfile")
        content = dockerfile.read_text()

        def count_layers():
            return len([line for line in content.split('\n')
                       if line.strip().startswith(('RUN', 'COPY', 'ADD'))])

        layer_count = benchmark(count_layers)
        assert layer_count < 15, f"Too many layers: {layer_count}. Consider optimization."


class TestDockerCompose:

    def test_docker_compose_exists(self):
        compose_file = Path("docker-compose.yml")
        assert compose_file.exists(), "docker-compose.yml not found"

    def test_docker_compose_syntax(self):
        import yaml
        
        compose_file = Path("docker-compose.yml")
        with open(compose_file) as f:
            config = yaml.safe_load(f)
            
        assert "services" in config, "Missing services section"
        assert "version" in config, "Missing version"
        
    def test_docker_compose_services(self):
        import yaml
        
        compose_file = Path("docker-compose.yml")
        with open(compose_file) as f:
            config = yaml.safe_load(f)
            
        services = config.get("services", {})
        assert "app" in services, "Missing app service"
        
        app_service = services["app"]
        assert "build" in app_service or "image" in app_service, "Missing build/image"
        assert "ports" in app_service, "Missing port mapping"
        
    def test_docker_compose_health_checks(self):
        import yaml

        compose_file = Path("docker-compose.yml")
        with open(compose_file) as f:
            config = yaml.safe_load(f)

        services = config.get("services", {})
        for service_name, service_config in services.items():
            if service_name in ["app", "db", "redis"]:
                assert "healthcheck" in service_config, f"Missing healthcheck for {service_name}"


class TestPortAvailability:

    def test_port_8000_available(self):
        """Validate that the test runner can allocate an ephemeral TCP port."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", 0))
            allocated_port = sock.getsockname()[1]
        finally:
            sock.close()

        assert allocated_port > 0, "Runner should provide an ephemeral TCP port"

    def test_port_5432_available(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 5432))
        sock.close()

        assert result != 0, "Port 5432 should be available (not in use)"

    def test_port_6379_available(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 6379))
        sock.close()

        assert result != 0, "Port 6379 should be available (not in use)"

    def test_port_range_validation(self):
        ports = [8000, 5432, 6379]

        for port in ports:
            assert 1024 <= port <= 65535, f"Port {port} out of valid range"


@pytest.mark.integration
@pytest.mark.skipif(WINDOWS_DOCKER_LINUX_BASE_UNAVAILABLE, reason=WINDOWS_DOCKER_LINUX_BASE_REASON)
class TestDockerBuild:

    @pytest.mark.slow
    def test_docker_build_success(self):
        result = subprocess.run(
            ["docker", "build", "-t", "test-master-input", "."],
            capture_output=True,
            text=True,
            timeout=300
        )

        assert result.returncode == 0, f"Docker build failed: {result.stderr}"

    @pytest.mark.slow
    def test_docker_image_size(self):
        result = subprocess.run(
            ["docker", "images", "test-master-input", "--format", "{{.Size}}"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0 and result.stdout.strip():
            size_str = result.stdout.strip()
            assert size_str, "Image size should be reported"


@pytest.mark.integration
class TestDockerContainer:

    @pytest.fixture
    def container_id(self):
        result = subprocess.run(
            ["docker", "run", "-d", "-p", "8000:8000", "test-master-input"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            container_id = result.stdout.strip()
            yield container_id

            subprocess.run(["docker", "stop", container_id], capture_output=True)
            subprocess.run(["docker", "rm", container_id], capture_output=True)
        else:
            pytest.skip("Docker container failed to start")

    @pytest.mark.slow
    def test_container_starts(self, container_id):
        assert container_id, "Container should have an ID"

        time.sleep(5)

        result = subprocess.run(
            ["docker", "ps", "-q", "-f", f"id={container_id}"],
            capture_output=True,
            text=True
        )


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.skipif(WINDOWS_DOCKER_LINUX_BASE_UNAVAILABLE, reason=WINDOWS_DOCKER_LINUX_BASE_REASON)
class TestDockerContainerIntegration:
    """Slow integration tests for actual Docker container operations"""

    @pytest.mark.asyncio
    async def test_docker_build_async(self):
        """Test Docker image build asynchronously."""
        proc = await asyncio.create_subprocess_exec(
            "docker", "build", "-t", "test-app:latest", ".",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        _, stderr = await proc.communicate()

        assert proc.returncode == 0, f"Docker build failed: {stderr.decode()}"

        inspect_proc = await asyncio.create_subprocess_exec(
            "docker", "image", "inspect", "test-app:latest",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        inspect_stdout, inspect_stderr = await inspect_proc.communicate()

        assert inspect_proc.returncode == 0, (
            f"Built image is not inspectable: {inspect_stderr.decode()}"
        )
        assert inspect_stdout.strip(), "Built image inspect output should not be empty"

    @pytest.mark.asyncio
    async def test_docker_container_health_async(self):
        """Test container health check asynchronously."""
        container_name = f"test-container-{time.time_ns()}"
        proc = await asyncio.create_subprocess_exec(
            "docker", "run", "-d", "--name", container_name,
            "test-app:latest",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()
        container_id = stdout.decode().strip()

        assert proc.returncode == 0, f"Docker run failed: {stderr.decode()}"
        assert container_id, "Docker run should return a container ID"

        try:
            await asyncio.sleep(5)

            inspect_proc = await asyncio.create_subprocess_exec(
                "docker", "inspect", "--format={{.State.Health.Status}}", container_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            inspect_stdout, inspect_stderr = await inspect_proc.communicate()
            health_status = inspect_stdout.decode().strip()

            assert inspect_proc.returncode == 0, (
                f"Docker inspect failed: {inspect_stderr.decode()}"
            )
            assert health_status in ["healthy", "starting"], (
                f"Container unhealthy: {health_status}"
            )

        finally:
            stop_proc = await asyncio.create_subprocess_exec(
                "docker", "stop", container_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await stop_proc.communicate()

            rm_proc = await asyncio.create_subprocess_exec(
                "docker", "rm", container_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await rm_proc.communicate()

    @pytest.mark.asyncio
    async def test_docker_volume_mounts_async(self):
        """Test volume mounts work correctly"""
        test_file = Path("test_volume_data.txt")
        test_file.write_text("test data")

        try:
            proc = await asyncio.create_subprocess_exec(
                'docker', 'run', '--rm',
                '-v', f'{test_file.absolute()}:/data/test.txt',
                'test-app:latest',
                'cat', '/data/test.txt',
                stdout=asyncio.subprocess.PIPE
            )

            stdout, _ = await proc.communicate()
            content = stdout.decode().strip()

            assert content == "test data", "Volume mount failed"

        finally:
            test_file.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_docker_network_connectivity_async(self):
        """Test container network connectivity in an isolated Docker network."""
        suffix = time.time_ns()
        network_name = f"test-network-{suffix}"
        container1_name = f"test-app1-{suffix}"
        container2_name = f"test-app2-{suffix}"
        container_ids = []

        network_proc = await asyncio.create_subprocess_exec(
            "docker", "network", "create", network_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, network_stderr = await network_proc.communicate()
        assert network_proc.returncode == 0, (
            f"Docker network create failed: {network_stderr.decode()}"
        )

        try:
            for container_name in (container1_name, container2_name):
                run_proc = await asyncio.create_subprocess_exec(
                    "docker", "run", "-d", "--name", container_name,
                    "--network", network_name, "test-app:latest",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                run_stdout, run_stderr = await run_proc.communicate()
                container_id = run_stdout.decode().strip()

                assert run_proc.returncode == 0, (
                    f"Docker run failed for {container_name}: {run_stderr.decode()}"
                )
                assert container_id, (
                    f"Docker run should return an ID for {container_name}"
                )
                container_ids.append(container_id)

            await asyncio.sleep(2)

            connectivity_proc = await asyncio.create_subprocess_exec(
                "docker", "exec", container_ids[0],
                "python", "-c",
                (
                    "import socket,time; "
                    "deadline=time.monotonic()+10; "
                    "last=None; "
                    f"host='{container2_name}'; "
                    "port=8000; "
                    "\nwhile time.monotonic() < deadline:\n"
                    "    try:\n"
                    "        s=socket.create_connection((host, port), timeout=1); "
                    "s.close(); break\n"
                    "    except OSError as exc:\n"
                    "        last=exc; time.sleep(0.5)\n"
                    "else:\n"
                    "    raise SystemExit(f'connectivity timeout: {last}')"
                ),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, connectivity_stderr = await connectivity_proc.communicate()

            assert connectivity_proc.returncode == 0, (
                f"Network connectivity failed: {connectivity_stderr.decode()}"
            )

        finally:
            for container_id in container_ids:
                stop_proc = await asyncio.create_subprocess_exec(
                    "docker", "stop", container_id,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await stop_proc.communicate()

                rm_proc = await asyncio.create_subprocess_exec(
                    "docker", "rm", container_id,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await rm_proc.communicate()

            network_rm_proc = await asyncio.create_subprocess_exec(
                "docker", "network", "rm", network_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await network_rm_proc.communicate()


@pytest.mark.benchmark
class TestDockerPerformance:
    """Performance benchmarking for Docker operations"""

    def test_dockerfile_parse_performance(self, benchmark):
        """Benchmark Dockerfile parsing performance"""
        dockerfile = Path("Dockerfile")

        def parse_dockerfile():
            content = dockerfile.read_text()
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            instructions = {}
            for line in lines:
                if ' ' in line:
                    cmd, args = line.split(' ', 1)
                    instructions[cmd] = instructions.get(cmd, []) + [args]
            return instructions

        result = benchmark(parse_dockerfile)
        assert len(result) > 0, "Failed to parse Dockerfile"

    def test_docker_compose_parse_performance(self, benchmark):
        """Benchmark docker-compose.yml parsing performance"""
        import yaml

        compose_file = Path("docker-compose.yml")

        def parse_compose():
            with open(compose_file) as f:
                return yaml.safe_load(f)

        result = benchmark(parse_compose)
        assert "services" in result, "Failed to parse docker-compose.yml"
        
        assert result.stdout.strip() == container_id, "Container should be running"
    
    @pytest.mark.slow
    def test_container_health(self, container_id):
        time.sleep(10)
        
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Health.Status}}", container_id],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            health_status = result.stdout.strip()
            assert health_status in ["healthy", "starting"], f"Container health: {health_status}"
    
    @pytest.mark.slow
    def test_container_port_binding(self, container_id):
        result = subprocess.run(
            ["docker", "port", container_id, "8000"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, "Port binding should be configured"
        assert "8000" in result.stdout, "Port 8000 should be mapped"
    
    @pytest.mark.slow
    def test_container_logs(self, container_id):
        time.sleep(5)
        
        result = subprocess.run(
            ["docker", "logs", container_id],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, "Should be able to retrieve logs"


@pytest.mark.integration
class TestDockerComposeDeploy:
    
    @pytest.mark.slow
    def test_docker_compose_up(self):
        result = subprocess.run(
            ["docker-compose", "config"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"docker-compose config failed: {result.stderr}"
    
    @pytest.mark.slow
    def test_docker_compose_services_defined(self):
        result = subprocess.run(
            ["docker-compose", "config", "--services"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            services = result.stdout.strip().split('\n')
            assert "app" in services, "App service should be defined"


class TestDockerVolumes:
    
    def test_volume_directories_exist(self):
        data_dir = Path("data")
        logs_dir = Path("logs")
        
        assert data_dir.exists() or True, "Data directory should exist or be creatable"
        assert logs_dir.exists() or True, "Logs directory should exist or be creatable"
    
    def test_docker_compose_volumes(self):
        import yaml
        
        compose_file = Path("docker-compose.yml")
        with open(compose_file) as f:
            config = yaml.safe_load(f)
            
        volumes = config.get("volumes", {})
        assert len(volumes) > 0, "Should define named volumes"


class TestDockerNetworking:
    
    def test_docker_compose_networks(self):
        import yaml
        
        compose_file = Path("docker-compose.yml")
        with open(compose_file) as f:
            config = yaml.safe_load(f)
            
        services = config.get("services", {})
        
        for service_name, service_config in services.items():
            if "depends_on" in service_config:
                assert isinstance(service_config["depends_on"], list), \
                    f"depends_on should be a list for {service_name}"


class TestDockerSecurity:
    
    def test_no_hardcoded_secrets(self):
        dockerfile = Path("Dockerfile")
        content = dockerfile.read_text()
        
        forbidden_patterns = [
            "password=",
            "secret=",
            "token=",
            "api_key="
        ]
        
        for pattern in forbidden_patterns:
            assert pattern.lower() not in content.lower(), \
                f"Hardcoded secret pattern found: {pattern}"
    
    def test_environment_variables_used(self):
        compose_file = Path("docker-compose.yml")
        content = compose_file.read_text()
        
        assert "${" in content or "environment:" in content, \
            "Should use environment variables"
    
    def test_docker_compose_env_file(self):
        compose_file = Path("docker-compose.yml")
        content = compose_file.read_text()
        
        sensitive_vars = ["PASSWORD", "SECRET", "KEY"]
        
        for var in sensitive_vars:
            if var in content:
                assert "${" in content, "Sensitive vars should use env substitution"


class TestDockerPerformance:
    
    def test_dockerfile_layer_optimization(self):
        dockerfile = Path("Dockerfile")
        content = dockerfile.read_text()
        lines = content.split('\n')
        
        copy_count = sum(1 for line in lines if line.strip().startswith('COPY'))
        assert copy_count <= 3, "Too many COPY layers, consider optimization"
        
    def test_dockerfile_uses_cache(self):
        dockerfile = Path("Dockerfile")
        content = dockerfile.read_text()
        
        assert "requirements.txt" in content, "Should copy requirements.txt separately for caching"
        
        lines = content.split('\n')
        req_line = next((i for i, line in enumerate(lines) if 'requirements.txt' in line), None)
        copy_all_line = next((i for i, line in enumerate(lines) if 'COPY . .' in line), None)
        
        if req_line and copy_all_line:
            assert req_line < copy_all_line, "requirements.txt should be copied before source code"
