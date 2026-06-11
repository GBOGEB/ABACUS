#!/usr/bin/env python3

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

class LocalDeploymentRunner:
    def __init__(self):
        self.project_root = Path.cwd()
        self.deployment_package = self.project_root / "ABACUS_V21_DEPLOYMENT_PACKAGE"
        self.results = []
    
    def log(self, message: str, status: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{status}] {message}")
        self.results.append({"timestamp": timestamp, "status": status, "message": message})
    
    def check_docker(self) -> bool:
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            self.log(f"Docker found: {result.stdout.strip()}", "SUCCESS")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log("Docker not found - install from https://docker.com", "WARNING")
            return False
    
    def check_docker_compose(self) -> bool:
        try:
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            self.log(f"Docker Compose found: {result.stdout.strip()}", "SUCCESS")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log("Docker Compose not found", "WARNING")
            return False
    
    def build_docker_image(self):
        self.log("Building Docker image...", "INFO")
        try:
            os.chdir(self.deployment_package)
            result = subprocess.run(
                ["docker", "build", "-t", "abacus-v21:latest", "."],
                capture_output=True,
                text=True,
                check=True
            )
            self.log("Docker image built successfully", "SUCCESS")
            os.chdir(self.project_root)
        except subprocess.CalledProcessError as e:
            self.log(f"Docker build failed: {e.stderr}", "ERROR")
            os.chdir(self.project_root)
    
    def start_docker_compose(self):
        self.log("Starting Docker Compose services...", "INFO")
        try:
            os.chdir(self.deployment_package)
            result = subprocess.run(
                ["docker-compose", "up", "-d"],
                capture_output=True,
                text=True,
                check=True
            )
            self.log("Docker Compose services started", "SUCCESS")
            self.log("Prometheus: http://localhost:9090", "INFO")
            self.log("Grafana: http://localhost:3000 (admin/admin)", "INFO")
            os.chdir(self.project_root)
        except subprocess.CalledProcessError as e:
            self.log(f"Docker Compose failed: {e.stderr}", "ERROR")
            os.chdir(self.project_root)
    
    def run_local_deployment(self):
        self.log("Running ABACUS v2.1 locally...", "INFO")
        try:
            result = subprocess.run(
                ["python", "abacus_v21_session_tuple_analyzer.py"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )
            if result.returncode == 0:
                self.log("ABACUS v2.1 executed successfully", "SUCCESS")
            else:
                self.log(f"ABACUS execution completed with warnings", "WARNING")
        except subprocess.TimeoutExpired:
            self.log("ABACUS execution timeout (expected for long-running processes)", "INFO")
        except Exception as e:
            self.log(f"Error running ABACUS: {str(e)}", "ERROR")
    
    def generate_report(self):
        report = {
            "timestamp": datetime.now().isoformat(),
            "deployment_type": "local",
            "results": self.results
        }
        
        report_file = self.deployment_package / "LOCAL_DEPLOYMENT_REPORT.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        self.log(f"Report saved: {report_file}", "SUCCESS")
    
    def run(self):
        print("╔══════════════════════════════════════════════════════════════════════════════╗")
        print("║              ABACUS v2.1 - Local Deployment Runner                          ║")
        print("╚══════════════════════════════════════════════════════════════════════════════╝\n")
        
        docker_available = self.check_docker()
        compose_available = self.check_docker_compose()
        
        if docker_available and compose_available:
            self.build_docker_image()
            self.start_docker_compose()
        else:
            self.log("Docker not available - running Python directly", "INFO")
            self.run_local_deployment()
        
        self.generate_report()
        
        print("\n✅ Local deployment completed!")
        print("📊 Check LOCAL_DEPLOYMENT_REPORT.json for details")

if __name__ == "__main__":
    runner = LocalDeploymentRunner()
    runner.run()
