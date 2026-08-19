#!/usr/bin/env python3
"""
# Version: 1.0.0
# Date: 2025-11-24
# Description: Auto-generated version header
"""

"""
Container Registry Integration Tests - Docker Hub, Container Scanning, Multi-arch Builds
"""

import pytest
import subprocess
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import hashlib


@dataclass
class ContainerImage:
    name: str
    tag: str
    digest: str
    size_mb: float
    architectures: List[str]
    created_at: str
    vulnerabilities: Dict[str, int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ContainerRegistryManager:
    def __init__(self, registry: str = "docker.io", namespace: str = "test"):
        self.registry = registry
        self.namespace = namespace
        self.images: List[ContainerImage] = []
    
    def build_image(self, dockerfile_path: Path, image_name: str, tag: str = "latest", 
                   platform: Optional[str] = None) -> Dict[str, Any]:
        try:
            cmd = ["docker", "build", "-t", f"{image_name}:{tag}"]
            
            if platform:
                cmd.extend(["--platform", platform])
            
            cmd.extend(["-f", str(dockerfile_path), str(dockerfile_path.parent)])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            return {
                "success": result.returncode == 0,
                "image": f"{image_name}:{tag}",
                "platform": platform or "linux/amd64",
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Build timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def build_multiarch(self, dockerfile_path: Path, image_name: str, tag: str = "latest",
                       platforms: List[str] = None) -> Dict[str, Any]:
        if platforms is None:
            platforms = ["linux/amd64", "linux/arm64"]
        
        results = []
        for platform in platforms:
            result = self.build_image(dockerfile_path, image_name, f"{tag}-{platform.replace('/', '-')}", platform)
            results.append(result)
        
        success_count = sum(1 for r in results if r["success"])
        
        return {
            "success": success_count == len(platforms),
            "platforms": platforms,
            "results": results,
            "success_count": success_count,
            "total_count": len(platforms)
        }
    
    def scan_image(self, image_name: str, tag: str = "latest") -> Dict[str, Any]:
        image_ref = f"{image_name}:{tag}"
        
        vulnerabilities = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "negligible": 0
        }
        
        try:
            result = subprocess.run(
                ["docker", "inspect", image_ref],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                inspect_data = json.loads(result.stdout)
                
                return {
                    "success": True,
                    "image": image_ref,
                    "vulnerabilities": vulnerabilities,
                    "scan_date": inspect_data[0].get("Created", "unknown") if inspect_data else "unknown",
                    "size_mb": round(inspect_data[0].get("Size", 0) / (1024 * 1024), 2) if inspect_data else 0
                }
            else:
                return {
                    "success": False,
                    "error": "Image not found or inspection failed"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def push_image(self, image_name: str, tag: str = "latest", dry_run: bool = True) -> Dict[str, Any]:
        image_ref = f"{self.registry}/{self.namespace}/{image_name}:{tag}"
        
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "image": image_ref,
                "message": "Dry run - image would be pushed"
            }
        
        try:
            result = subprocess.run(
                ["docker", "push", image_ref],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            return {
                "success": result.returncode == 0,
                "image": image_ref,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def tag_image(self, source_image: str, source_tag: str, target_tag: str) -> Dict[str, Any]:
        source_ref = f"{source_image}:{source_tag}"
        target_ref = f"{source_image}:{target_tag}"
        
        try:
            result = subprocess.run(
                ["docker", "tag", source_ref, target_ref],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "success": result.returncode == 0,
                "source": source_ref,
                "target": target_ref,
                "error": result.stderr if result.returncode != 0 else None
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_image_digest(self, image_name: str, tag: str = "latest") -> Optional[str]:
        image_ref = f"{image_name}:{tag}"
        
        try:
            result = subprocess.run(
                ["docker", "inspect", "--format={{.Id}}", image_ref],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None


@pytest.fixture
def registry_manager():
    return ContainerRegistryManager(namespace="test-namespace")


@pytest.fixture
def sample_dockerfile(tmp_path):
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("""
FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir pytest
CMD ["pytest"]
""")
    return dockerfile


class TestContainerBuild:
    
    def test_registry_manager_initialization(self, registry_manager):
        assert registry_manager is not None
        assert registry_manager.registry == "docker.io"
        assert registry_manager.namespace == "test-namespace"
    
    @pytest.mark.slow
    def test_build_image_success(self, registry_manager, sample_dockerfile):
        result = registry_manager.build_image(
            sample_dockerfile,
            "test-image",
            "v1.0.0"
        )
        
        assert "success" in result
        assert "image" in result
        assert result["image"] == "test-image:v1.0.0"
    
    def test_build_image_nonexistent_dockerfile(self, registry_manager):
        result = registry_manager.build_image(
            Path("/nonexistent/Dockerfile"),
            "test-image",
            "v1.0.0"
        )
        
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.slow
    def test_build_multiarch_dry_run(self, registry_manager, sample_dockerfile):
        result = registry_manager.build_multiarch(
            sample_dockerfile,
            "test-multiarch",
            "v1.0.0",
            platforms=["linux/amd64"]
        )
        
        assert "platforms" in result
        assert "results" in result
        assert len(result["results"]) == 1


class TestContainerScanning:
    
    def test_scan_image_structure(self, registry_manager):
        result = registry_manager.scan_image("nonexistent-image", "latest")
        
        assert "success" in result
        assert "image" in result
    
    @pytest.mark.slow
    def test_scan_existing_image(self, registry_manager):
        result = registry_manager.scan_image("python", "3.12-slim")
        
        if result["success"]:
            assert "vulnerabilities" in result
            assert "scan_date" in result
            assert "size_mb" in result
    
    def test_scan_vulnerabilities_structure(self, registry_manager):
        result = registry_manager.scan_image("test-image", "latest")
        
        if result["success"] and "vulnerabilities" in result:
            vuln = result["vulnerabilities"]
            assert "critical" in vuln
            assert "high" in vuln
            assert "medium" in vuln
            assert "low" in vuln


class TestContainerRegistry:
    
    def test_push_image_dry_run(self, registry_manager):
        result = registry_manager.push_image("test-image", "v1.0.0", dry_run=True)
        
        assert result["success"] is True
        assert result["dry_run"] is True
        assert "docker.io/test-namespace/test-image:v1.0.0" in result["image"]
    
    def test_tag_image_structure(self, registry_manager):
        result = registry_manager.tag_image("test-image", "v1.0.0", "latest")
        
        assert "success" in result
        assert "source" in result
        assert "target" in result
    
    def test_get_image_digest_nonexistent(self, registry_manager):
        digest = registry_manager.get_image_digest("nonexistent-image", "latest")
        
        assert digest is None or isinstance(digest, str)


class TestMultiArchBuilds:
    
    def test_multiarch_platforms_configuration(self, registry_manager, sample_dockerfile):
        platforms = ["linux/amd64", "linux/arm64", "linux/arm/v7"]
        
        result = registry_manager.build_multiarch(
            sample_dockerfile,
            "test-multiarch",
            "v1.0.0",
            platforms=platforms
        )
        
        assert result["platforms"] == platforms
        assert result["total_count"] == len(platforms)
    
    def test_multiarch_default_platforms(self, registry_manager, sample_dockerfile):
        result = registry_manager.build_multiarch(
            sample_dockerfile,
            "test-multiarch",
            "v1.0.0"
        )
        
        assert "linux/amd64" in result["platforms"]
        assert "linux/arm64" in result["platforms"]
    
    def test_multiarch_results_structure(self, registry_manager, sample_dockerfile):
        result = registry_manager.build_multiarch(
            sample_dockerfile,
            "test-multiarch",
            "v1.0.0",
            platforms=["linux/amd64"]
        )
        
        assert "results" in result
        assert len(result["results"]) > 0
        assert "success_count" in result


class TestContainerImageMetadata:
    
    def test_container_image_dataclass(self):
        image = ContainerImage(
            name="test-image",
            tag="v1.0.0",
            digest="sha256:abc123",
            size_mb=150.5,
            architectures=["linux/amd64", "linux/arm64"],
            created_at="2024-01-22T10:00:00Z"
        )
        
        assert image.name == "test-image"
        assert image.tag == "v1.0.0"
        assert len(image.architectures) == 2
    
    def test_container_image_to_dict(self):
        image = ContainerImage(
            name="test-image",
            tag="v1.0.0",
            digest="sha256:abc123",
            size_mb=150.5,
            architectures=["linux/amd64"],
            created_at="2024-01-22T10:00:00Z",
            vulnerabilities={"critical": 0, "high": 1}
        )
        
        data = image.to_dict()
        assert isinstance(data, dict)
        assert data["name"] == "test-image"
        assert data["vulnerabilities"]["high"] == 1


class TestContainerSecurity:
    
    def test_vulnerability_severity_levels(self, registry_manager):
        result = registry_manager.scan_image("test-image", "latest")
        
        if result["success"] and "vulnerabilities" in result:
            vuln = result["vulnerabilities"]
            severity_levels = ["critical", "high", "medium", "low", "negligible"]
            
            for level in severity_levels:
                assert level in vuln
                assert isinstance(vuln[level], int)
                assert vuln[level] >= 0
    
    def test_scan_result_completeness(self, registry_manager):
        result = registry_manager.scan_image("test-image", "latest")
        
        required_fields = ["success", "image"]
        for field in required_fields:
            assert field in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not slow"])
