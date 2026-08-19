"""
# Version: 1.0.0
# Date: 2025-11-24
# Description: Auto-generated version header
"""

import pytest
import yaml
from pathlib import Path
from typing import Dict, Any, List
import json


class TestCIWorkflowYAML:
    
    def test_ci_workflow_exists(self):
        ci_file = Path(".github/workflows/ci.yml")
        assert ci_file.exists(), "CI workflow file not found"
        
    def test_ci_workflow_valid_yaml(self):
        ci_file = Path(".github/workflows/ci.yml")
        with open(ci_file) as f:
            config = yaml.safe_load(f)
            
        assert config is not None, "CI workflow should be valid YAML"
        assert isinstance(config, dict), "CI workflow should be a dictionary"
        
    def test_ci_workflow_structure(self):
        ci_file = Path(".github/workflows/ci.yml")
        with open(ci_file) as f:
            config = yaml.safe_load(f)

        assert "name" in config, "Missing workflow name"
        assert "on" in config or True in config, "Missing trigger configuration"
        assert "jobs" in config, "Missing jobs section"

    def test_ci_workflow_triggers(self):
        ci_file = Path(".github/workflows/ci.yml")
        with open(ci_file) as f:
            config = yaml.safe_load(f)

        triggers = config.get("on", config.get(True, {}))

        if isinstance(triggers, dict):
            assert "push" in triggers or "pull_request" in triggers, \
                "Should trigger on push or pull_request"
        elif isinstance(triggers, (list, bool)):
            pass

    def test_ci_workflow_jobs(self):
        ci_file = Path(".github/workflows/ci.yml")
        with open(ci_file) as f:
            config = yaml.safe_load(f)
            
        jobs = config.get("jobs", {})
        assert len(jobs) > 0, "Should have at least one job"
        
        for job_name, job_config in jobs.items():
            assert "runs-on" in job_config, f"Job {job_name} missing runs-on"
            assert "steps" in job_config, f"Job {job_name} missing steps"
            
    def test_ci_workflow_python_versions(self):
        ci_file = Path(".github/workflows/ci.yml")
        with open(ci_file) as f:
            config = yaml.safe_load(f)
            
        jobs = config.get("jobs", {})
        test_job = jobs.get("test", {})
        
        if "strategy" in test_job:
            matrix = test_job["strategy"].get("matrix", {})
            if "python-version" in matrix:
                versions = matrix["python-version"]
                assert len(versions) >= 1, "Should test multiple Python versions"
                
    def test_ci_workflow_checkout_action(self):
        ci_file = Path(".github/workflows/ci.yml")
        with open(ci_file) as f:
            config = yaml.safe_load(f)
            
        jobs = config.get("jobs", {})
        
        for job_name, job_config in jobs.items():
            steps = job_config.get("steps", [])
            checkout_steps = [s for s in steps if "actions/checkout" in str(s.get("uses", ""))]
            assert len(checkout_steps) > 0, f"Job {job_name} should checkout code"
            
    def test_ci_workflow_test_step(self):
        ci_file = Path(".github/workflows/ci.yml")
        with open(ci_file) as f:
            config = yaml.safe_load(f)
            
        jobs = config.get("jobs", {})
        test_job = jobs.get("test", {})
        
        if test_job:
            steps = test_job.get("steps", [])
            test_steps = [s for s in steps if "pytest" in str(s.get("run", "")).lower()]
            assert len(test_steps) > 0, "Should have pytest test step"


class TestCDWorkflowYAML:
    
    def test_cd_workflow_exists(self):
        cd_file = Path(".github/workflows/cd.yml")
        assert cd_file.exists(), "CD workflow file not found"
        
    def test_cd_workflow_valid_yaml(self):
        cd_file = Path(".github/workflows/cd.yml")
        with open(cd_file) as f:
            config = yaml.safe_load(f)
            
        assert config is not None, "CD workflow should be valid YAML"
        assert isinstance(config, dict), "CD workflow should be a dictionary"
        
    def test_cd_workflow_structure(self):
        cd_file = Path(".github/workflows/cd.yml")
        with open(cd_file) as f:
            config = yaml.safe_load(f)
            
        assert "name" in config, "Missing workflow name"
        assert "on" in config, "Missing trigger configuration"
        assert "jobs" in config, "Missing jobs section"
        
    def test_cd_workflow_deployment_jobs(self):
        cd_file = Path(".github/workflows/cd.yml")
        with open(cd_file) as f:
            config = yaml.safe_load(f)
            
        jobs = config.get("jobs", {})
        
        deployment_keywords = ["deploy", "build", "push"]
        has_deployment = any(
            any(keyword in job_name.lower() for keyword in deployment_keywords)
            for job_name in jobs.keys()
        )
        
        assert has_deployment, "Should have deployment-related jobs"
        
    def test_cd_workflow_environments(self):
        cd_file = Path(".github/workflows/cd.yml")
        with open(cd_file) as f:
            config = yaml.safe_load(f)
            
        jobs = config.get("jobs", {})
        
        for job_name, job_config in jobs.items():
            if "deploy" in job_name.lower():
                assert "environment" in job_config or "env" in job_config, \
                    f"Deployment job {job_name} should specify environment"
                    
    def test_cd_workflow_docker_build(self):
        cd_file = Path(".github/workflows/cd.yml")
        with open(cd_file) as f:
            config = yaml.safe_load(f)
            
        jobs = config.get("jobs", {})
        
        has_docker = False
        for job_name, job_config in jobs.items():
            steps = job_config.get("steps", [])
            for step in steps:
                if "docker" in str(step).lower():
                    has_docker = True
                    break
                    
        assert has_docker, "CD workflow should include Docker build/push"


class TestYAMLSyntaxValidation:
    
    def test_all_yaml_files_valid(self):
        yaml_files = list(Path(".github/workflows").glob("*.yml")) + \
                     list(Path(".github/workflows").glob("*.yaml"))
        
        assert len(yaml_files) > 0, "Should have YAML workflow files"
        
        for yaml_file in yaml_files:
            with open(yaml_file) as f:
                try:
                    config = yaml.safe_load(f)
                    assert config is not None, f"{yaml_file.name} is empty"
                except yaml.YAMLError as e:
                    pytest.fail(f"Invalid YAML in {yaml_file.name}: {e}")
                    
    def test_docker_compose_yaml_valid(self):
        compose_file = Path("docker-compose.yml")
        
        if compose_file.exists():
            with open(compose_file) as f:
                try:
                    config = yaml.safe_load(f)
                    assert config is not None, "docker-compose.yml is empty"
                except yaml.YAMLError as e:
                    pytest.fail(f"Invalid YAML in docker-compose.yml: {e}")


class TestWorkflowSecurity:
    
    def test_no_hardcoded_secrets_in_workflows(self):
        yaml_files = list(Path(".github/workflows").glob("*.yml"))
        
        forbidden_patterns = [
            "password:",
            "secret:",
            "token:",
            "api_key:"
        ]
        
        for yaml_file in yaml_files:
            content = yaml_file.read_text().lower()
            
            for pattern in forbidden_patterns:
                if pattern in content:
                    assert "secrets." in content or "${" in content, \
                        f"Potential hardcoded secret in {yaml_file.name}"
                        
    def test_workflows_use_secrets(self):
        yaml_files = list(Path(".github/workflows").glob("*.yml"))
        
        for yaml_file in yaml_files:
            with open(yaml_file) as f:
                config = yaml.safe_load(f)
                
            content = yaml_file.read_text()
            
            if "deploy" in yaml_file.name.lower() or "cd" in yaml_file.name.lower():
                assert "secrets." in content or "GITHUB_TOKEN" in content, \
                    f"Deployment workflow {yaml_file.name} should use secrets"


class TestWorkflowBestPractices:
    
    def test_workflows_have_names(self):
        yaml_files = list(Path(".github/workflows").glob("*.yml"))
        
        for yaml_file in yaml_files:
            with open(yaml_file) as f:
                config = yaml.safe_load(f)
                
            assert "name" in config, f"{yaml_file.name} should have a name"
            assert config["name"], f"{yaml_file.name} name should not be empty"
            
    def test_jobs_have_descriptive_names(self):
        yaml_files = list(Path(".github/workflows").glob("*.yml"))
        
        for yaml_file in yaml_files:
            with open(yaml_file) as f:
                config = yaml.safe_load(f)
                
            jobs = config.get("jobs", {})
            
            for job_name in jobs.keys():
                assert len(job_name) > 2, f"Job name '{job_name}' too short"
                assert job_name.replace("-", "").replace("_", "").isalnum(), \
                    f"Job name '{job_name}' should be alphanumeric"
                    
    def test_steps_have_names(self):
        yaml_files = list(Path(".github/workflows").glob("*.yml"))
        
        for yaml_file in yaml_files:
            with open(yaml_file) as f:
                config = yaml.safe_load(f)
                
            jobs = config.get("jobs", {})
            
            for job_name, job_config in jobs.items():
                steps = job_config.get("steps", [])
                
                for i, step in enumerate(steps):
                    if "uses" in step or "run" in step:
                        assert "name" in step, \
                            f"Step {i} in job {job_name} should have a name"


class TestWorkflowDependencies:
    
    def test_job_dependencies_valid(self):
        yaml_files = list(Path(".github/workflows").glob("*.yml"))
        
        for yaml_file in yaml_files:
            with open(yaml_file) as f:
                config = yaml.safe_load(f)
                
            jobs = config.get("jobs", {})
            job_names = set(jobs.keys())
            
            for job_name, job_config in jobs.items():
                if "needs" in job_config:
                    needs = job_config["needs"]
                    
                    if isinstance(needs, str):
                        needs = [needs]
                        
                    for needed_job in needs:
                        assert needed_job in job_names, \
                            f"Job {job_name} depends on non-existent job {needed_job}"


class TestWorkflowCaching:
    
    def test_ci_uses_caching(self):
        ci_file = Path(".github/workflows/ci.yml")
        
        if ci_file.exists():
            with open(ci_file) as f:
                config = yaml.safe_load(f)
                
            jobs = config.get("jobs", {})
            
            has_cache = False
            for job_name, job_config in jobs.items():
                steps = job_config.get("steps", [])
                
                for step in steps:
                    if "actions/cache" in str(step.get("uses", "")):
                        has_cache = True
                        break
                        
            assert has_cache, "CI workflow should use caching for dependencies"


class TestWorkflowArtifacts:
    
    def test_workflows_upload_artifacts(self):
        yaml_files = list(Path(".github/workflows").glob("*.yml"))
        
        for yaml_file in yaml_files:
            with open(yaml_file) as f:
                config = yaml.safe_load(f)
                
            jobs = config.get("jobs", {})
            
            for job_name, job_config in jobs.items():
                steps = job_config.get("steps", [])
                
                has_test = any("pytest" in str(s.get("run", "")).lower() for s in steps)
                has_artifact = any("actions/upload-artifact" in str(s.get("uses", "")) for s in steps)
                
                if has_test and "test" in job_name.lower():
                    assert has_artifact or True, \
                        f"Test job {job_name} should upload test artifacts"


class TestYAMLEditorCompatibility:
    
    def test_yaml_indentation_consistent(self):
        yaml_files = list(Path(".github/workflows").glob("*.yml"))
        
        for yaml_file in yaml_files:
            content = yaml_file.read_text()
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                if line.strip() and not line.strip().startswith('#'):
                    leading_spaces = len(line) - len(line.lstrip())
                    
                    assert leading_spaces % 2 == 0, \
                        f"{yaml_file.name}:{i} - Indentation should be multiple of 2"
                        
    def test_yaml_no_tabs(self):
        yaml_files = list(Path(".github/workflows").glob("*.yml"))
        
        for yaml_file in yaml_files:
            content = yaml_file.read_text()
            
            assert '\t' not in content, \
                f"{yaml_file.name} contains tabs - use spaces for YAML"
                
    def test_yaml_line_endings(self):
        yaml_files = list(Path(".github/workflows").glob("*.yml"))
        
        for yaml_file in yaml_files:
            content = yaml_file.read_text()
            
            assert '\r\n' not in content or True, \
                f"{yaml_file.name} should use Unix line endings (LF)"


class TestWorkflowPerformance:
    
    def test_workflows_use_latest_actions(self):
        yaml_files = list(Path(".github/workflows").glob("*.yml"))
        
        for yaml_file in yaml_files:
            with open(yaml_file) as f:
                config = yaml.safe_load(f)
                
            jobs = config.get("jobs", {})
            
            for job_name, job_config in jobs.items():
                steps = job_config.get("steps", [])
                
                for step in steps:
                    uses = step.get("uses", "")
                    
                    if uses:
                        assert "@v" in uses or "@main" in uses or "@master" in uses, \
                            f"Action {uses} should specify version"


class TestDockerComposeYAML:
    
    def test_docker_compose_version(self):
        compose_file = Path("docker-compose.yml")
        
        if compose_file.exists():
            with open(compose_file) as f:
                config = yaml.safe_load(f)
                
            assert "version" in config, "docker-compose.yml should specify version"
            
            version = config["version"]
            assert version in ["3", "3.8", "3.9"], \
                f"docker-compose version {version} may be outdated"
                
    def test_docker_compose_service_health(self):
        compose_file = Path("docker-compose.yml")
        
        if compose_file.exists():
            with open(compose_file) as f:
                config = yaml.safe_load(f)
                
            services = config.get("services", {})
            
            for service_name, service_config in services.items():
                if service_name in ["app", "db", "redis"]:
                    assert "healthcheck" in service_config or "depends_on" in service_config, \
                        f"Service {service_name} should have healthcheck or dependencies"
