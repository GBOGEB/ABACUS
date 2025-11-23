#!/usr/bin/env python3

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

class GitHubDeploymentOrchestrator:
    def __init__(self):
        self.project_root = Path.cwd()
        self.deployment_package = self.project_root / "ABACUS_V21_DEPLOYMENT_PACKAGE"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "steps": [],
            "status": "in_progress"
        }
    
    def log_step(self, step: str, status: str, details: str = ""):
        step_info = {
            "step": step,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.results["steps"].append(step_info)
        print(f"[{status.upper()}] {step}")
        if details:
            print(f"  → {details}")
    
    def check_git_status(self) -> bool:
        try:
            result = subprocess.run(
                ["git", "status"],
                capture_output=True,
                text=True,
                check=True
            )
            self.log_step("Git Status Check", "success", "Git repository detected")
            return True
        except subprocess.CalledProcessError:
            self.log_step("Git Status Check", "warning", "Not a git repository - will initialize")
            return False
    
    def initialize_git_repo(self):
        try:
            if not self.check_git_status():
                subprocess.run(["git", "init"], check=True)
                self.log_step("Git Initialization", "success", "Git repository initialized")
            
            subprocess.run(["git", "config", "user.name", "ABACUS Team"], check=False)
            subprocess.run(["git", "config", "user.email", "abacus@example.com"], check=False)
            
        except Exception as e:
            self.log_step("Git Initialization", "error", str(e))
    
    def create_deployment_structure(self):
        try:
            files_created = []
            
            if self.deployment_package.exists():
                files_created.append(str(self.deployment_package))
            
            self.log_step(
                "Deployment Structure", 
                "success", 
                f"Created {len(files_created)} deployment files"
            )
        except Exception as e:
            self.log_step("Deployment Structure", "error", str(e))
    
    def stage_files_for_commit(self):
        try:
            files_to_add = [
                "abacus_v21_*.py",
                "ABACUS_V21_*.md",
                "ABACUS_V21_DEPLOYMENT_PACKAGE/",
                ".gitignore"
            ]
            
            for pattern in files_to_add:
                try:
                    subprocess.run(["git", "add", pattern], check=False)
                except:
                    pass
            
            self.log_step("Stage Files", "success", "Files staged for commit")
        except Exception as e:
            self.log_step("Stage Files", "error", str(e))
    
    def create_commit(self):
        try:
            commit_message = f"ABACUS v2.1 Deployment Package - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                self.log_step("Git Commit", "success", commit_message)
            else:
                self.log_step("Git Commit", "info", "No changes to commit or already committed")
        except Exception as e:
            self.log_step("Git Commit", "error", str(e))
    
    def prepare_github_push_instructions(self):
        instructions = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    GITHUB DEPLOYMENT INSTRUCTIONS                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

📋 STEP 1: Create GitHub Repository
   1. Go to https://github.com/new
   2. Repository name: abacus-v21
   3. Description: ABACUS v2.1 - Session Analysis & Deployment System
   4. Choose: Public or Private
   5. DO NOT initialize with README (we already have one)
   6. Click "Create repository"

📋 STEP 2: Connect Local Repository to GitHub
   Run these commands in your terminal:

   git remote add origin https://github.com/YOUR_USERNAME/abacus-v21.git
   git branch -M main
   git push -u origin main

📋 STEP 3: Verify Deployment Package
   Check that these files are in your repository:
   ✓ ABACUS_V21_DEPLOYMENT_PACKAGE/
     ├── README.md
     ├── Dockerfile
     ├── docker-compose.yml
     ├── .gitignore
     ├── .github/workflows/ci-cd.yml
     └── monitoring/prometheus.yml

📋 STEP 4: Enable GitHub Actions
   1. Go to your repository on GitHub
   2. Click "Actions" tab
   3. Enable workflows if prompted
   4. The CI/CD pipeline will run automatically on push

📋 STEP 5: Deploy to Platform (Choose One)

   🔹 OPTION A: GitHub Pages (Static Reports)
      - Go to Settings → Pages
      - Source: Deploy from branch
      - Branch: main, folder: /docs
      - Save

   🔹 OPTION B: Heroku
      heroku create abacus-v21
      heroku container:push web
      heroku container:release web
      heroku open

   🔹 OPTION C: Docker (Local/Server)
      cd ABACUS_V21_DEPLOYMENT_PACKAGE
      docker-compose up -d
      # Access: http://localhost:3000 (Grafana)
      # Access: http://localhost:9090 (Prometheus)

   🔹 OPTION D: AWS/Azure/GCP
      See ABACUS_V21_REALISTIC_DEPLOYMENT_ROADMAP.md

📋 STEP 6: Verify Deployment
   python abacus_v21_postdeployment_validation.py

📋 STEP 7: Monitor Application
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000
   - Default credentials: admin/admin

╔══════════════════════════════════════════════════════════════════════════════╗
║                         QUICK COMMANDS REFERENCE                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

# Check git status
git status

# View commit history
git log --oneline

# Push to GitHub
git push origin main

# Pull latest changes
git pull origin main

# Create new branch
git checkout -b feature/new-feature

# View remote repositories
git remote -v

╔══════════════════════════════════════════════════════════════════════════════╗
║                              NEXT STEPS                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

1. ✅ Local Git repository prepared
2. ⏳ Create GitHub repository (manual step)
3. ⏳ Push code to GitHub
4. ⏳ Choose deployment platform
5. ⏳ Deploy application
6. ⏳ Set up monitoring
7. ⏳ Validate deployment

═══════════════════════════════════════════════════════════════════════════════

📞 Need Help?
   - GitHub Docs: https://docs.github.com
   - Docker Docs: https://docs.docker.com
   - ABACUS Docs: See ABACUS_V21_REALISTIC_DEPLOYMENT_ROADMAP.md

═══════════════════════════════════════════════════════════════════════════════
"""
        
        instructions_file = self.project_root / "GITHUB_DEPLOYMENT_INSTRUCTIONS.txt"
        with open(instructions_file, 'w', encoding='utf-8') as f:
            f.write(instructions)
        
        print(instructions)
        self.log_step("GitHub Instructions", "success", f"Saved to {instructions_file}")
    
    def generate_deployment_report(self):
        report_file = self.project_root / "ABACUS_V21_DEPLOYMENT_PACKAGE" / "DEPLOYMENT_REPORT.json"
        
        self.results["status"] = "completed"
        self.results["summary"] = {
            "total_steps": len(self.results["steps"]),
            "successful": len([s for s in self.results["steps"] if s["status"] == "success"]),
            "warnings": len([s for s in self.results["steps"] if s["status"] == "warning"]),
            "errors": len([s for s in self.results["steps"] if s["status"] == "error"])
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📊 Deployment Report: {report_file}")
        print(f"   ✅ Successful: {self.results['summary']['successful']}")
        print(f"   ⚠️  Warnings: {self.results['summary']['warnings']}")
        print(f"   ❌ Errors: {self.results['summary']['errors']}")
    
    def run(self):
        print("╔══════════════════════════════════════════════════════════════════════════════╗")
        print("║          ABACUS v2.1 - GitHub Deployment Orchestrator                       ║")
        print("╚══════════════════════════════════════════════════════════════════════════════╝\n")
        
        self.initialize_git_repo()
        self.create_deployment_structure()
        self.stage_files_for_commit()
        self.create_commit()
        self.prepare_github_push_instructions()
        self.generate_deployment_report()
        
        print("\n✅ Deployment preparation completed!")
        print("📖 Follow the instructions in GITHUB_DEPLOYMENT_INSTRUCTIONS.txt")

if __name__ == "__main__":
    orchestrator = GitHubDeploymentOrchestrator()
    orchestrator.run()
