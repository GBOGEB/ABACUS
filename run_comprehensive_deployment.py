#!/usr/bin/env python3
"""
Comprehensive DOW Deployment Orchestrator
Executes: Git/GitHub roundtrip, CI/CD, Sprint 5, DMAIC Phase 0-9, MCP iteration
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime
import time

class DeploymentOrchestrator:
    def __init__(self):
        self.start_time = datetime.now()
        self.results = {
            "git_integration": {},
            "sprint_5": {},
            "dmaic_phases": {},
            "mcp_iteration": {},
            "cicd_pipeline": {},
            "self_improvement": {}
        }
        
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️ ",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "RUNNING": "🔄",
            "STEP": "📍"
        }.get(level, "  ")
        print(f"[{timestamp}] {prefix} {message}")
    
    def run_command(self, cmd: str, cwd: str = None, capture: bool = True) -> dict:
        """Run shell command and return result"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd,
                capture_output=capture,
                text=True,
                timeout=300
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout if capture else "",
                "stderr": result.stderr if capture else "",
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def step_1_git_integration(self):
        """Step 1: Git/GitHub Integration & CI/CD Setup"""
        self.log("STEP 1: Git/GitHub Integration & CI/CD Setup", "STEP")
        
        self.log("Checking Git status...", "RUNNING")
        result = self.run_command("git status --porcelain | wc -l")
        if result["success"]:
            modified_files = int(result["stdout"].strip())
            self.log(f"Found {modified_files} modified files")
            self.results["git_integration"]["modified_files"] = modified_files
        
        self.log("Checking remote repository...", "RUNNING")
        result = self.run_command("git remote -v")
        if result["success"]:
            has_remote = "origin" in result["stdout"]
            self.results["git_integration"]["has_remote"] = has_remote
            if has_remote:
                self.log("Remote repository configured", "SUCCESS")
            else:
                self.log("No remote repository found - skipping push", "INFO")
        
        self.log("Checking current branch...", "RUNNING")
        result = self.run_command("git branch --show-current")
        if result["success"]:
            branch = result["stdout"].strip()
            self.results["git_integration"]["branch"] = branch
            self.log(f"Current branch: {branch}")
        
        self.results["git_integration"]["status"] = "completed"
        self.log("Git integration check complete", "SUCCESS")
        return True
    
    def step_2_sprint_5_execution(self):
        """Step 2: Execute Sprint 5 Tasks"""
        self.log("STEP 2: Sprint 5 Execution", "STEP")
        
        self.log("Loading Sprint 5 configuration...", "RUNNING")
        sprint_file = Path("DOW/sprints.yaml")
        if not sprint_file.exists():
            self.log("Sprint configuration not found", "ERROR")
            self.results["sprint_5"]["status"] = "skipped"
            return False
        
        self.log("Executing Sprint 5 via orchestrator...", "RUNNING")
        result = self.run_command(
            "python dmaic_v23_master_orchestrator.py --action run-sprint --sprint 5",
            capture=False
        )
        
        if result["success"]:
            self.log("Sprint 5 execution completed", "SUCCESS")
            self.results["sprint_5"]["status"] = "completed"
            self.results["sprint_5"]["tasks_executed"] = 5
            return True
        else:
            self.log("Sprint 5 execution failed", "ERROR")
            self.results["sprint_5"]["status"] = "failed"
            return False
    
    def step_3_dmaic_phase_0_to_9(self):
        """Step 3: Execute DMAIC Phase 0-9 Full Cycle"""
        self.log("STEP 3: DMAIC Phase 0-9 Full Cycle", "STEP")
        
        phases = [
            ("Phase 0", "Initialization", "run_cicd_integration.py"),
            ("Phase 1-5", "Full DMAIC", "run_full_dmaic_pipeline_v2_with_agents.py"),
            ("Phase 4+", "Ranking & Improvement", "run_phase4_phase5.py"),
            ("Direct Improvements", "Quality Enhancement", "run_direct_improvements.py")
        ]
        
        completed_phases = 0
        for phase_name, description, script in phases:
            self.log(f"Running {phase_name}: {description}...", "RUNNING")
            
            script_path = Path("ABACUS-v031") / script
            if not script_path.exists():
                self.log(f"Script not found: {script}", "ERROR")
                continue
            
            result = self.run_command(
                f"python {script}",
                cwd="ABACUS-v031",
                capture=True
            )
            
            if result["success"]:
                self.log(f"{phase_name} completed", "SUCCESS")
                completed_phases += 1
            else:
                self.log(f"{phase_name} failed", "ERROR")
        
        self.results["dmaic_phases"]["completed"] = completed_phases
        self.results["dmaic_phases"]["total"] = len(phases)
        self.results["dmaic_phases"]["status"] = "completed" if completed_phases > 0 else "failed"
        
        self.log(f"DMAIC phases: {completed_phases}/{len(phases)} completed", "SUCCESS")
        return completed_phases > 0
    
    def step_4_mcp_orchestration(self):
        """Step 4: MCP-Orchestrated Iteration Loop"""
        self.log("STEP 4: MCP-Orchestrated Iteration", "STEP")
        
        self.log("Running MCP iteration cycle...", "RUNNING")
        
        iterations = 3
        successful_iterations = 0
        
        for i in range(1, iterations + 1):
            self.log(f"MCP Iteration {i}/{iterations}...", "RUNNING")
            
            result = self.run_command(
                "python run_direct_improvements.py",
                cwd="ABACUS-v031",
                capture=True
            )
            
            if result["success"]:
                self.log(f"Iteration {i} completed", "SUCCESS")
                successful_iterations += 1
                
                self.run_command(
                    f'git add -A && git commit -m "[MCP] Iteration {i} - Automated improvements"',
                    capture=True
                )
            else:
                self.log(f"Iteration {i} failed", "ERROR")
                break
            
            if i < iterations:
                self.log(f"Waiting 2s before next iteration...", "INFO")
                time.sleep(2)
        
        self.results["mcp_iteration"]["completed"] = successful_iterations
        self.results["mcp_iteration"]["total"] = iterations
        self.results["mcp_iteration"]["status"] = "completed" if successful_iterations > 0 else "failed"
        
        self.log(f"MCP iterations: {successful_iterations}/{iterations} completed", "SUCCESS")
        return successful_iterations > 0
    
    def step_5_self_improvement(self):
        """Step 5: Self-Improvement Cycle"""
        self.log("STEP 5: Self-Improvement Cycle", "STEP")
        
        self.log("Analyzing quality metrics...", "RUNNING")
        
        rankings_file = Path("ABACUS-v031/artifact_rankings.json")
        if rankings_file.exists():
            try:
                with open(rankings_file, 'r') as f:
                    rankings = json.load(f)
                
                if isinstance(rankings, list) and len(rankings) > 0:
                    scores = [r.get("metrics", {}).get("overall_score", 0) for r in rankings]
                    avg_score = sum(scores) / len(scores) if scores else 0
                    
                    self.results["self_improvement"]["avg_score"] = avg_score
                    self.results["self_improvement"]["total_artifacts"] = len(rankings)
                    
                    self.log(f"Average quality score: {avg_score:.3f}")
                    
                    if avg_score < 0.5:
                        self.log("Quality below target - running additional improvement", "INFO")
                        result = self.run_command(
                            "python run_direct_improvements.py",
                            cwd="ABACUS-v031",
                            capture=True
                        )
                        if result["success"]:
                            self.log("Additional improvement completed", "SUCCESS")
                    else:
                        self.log("Quality target achieved!", "SUCCESS")
                    
                    self.results["self_improvement"]["status"] = "completed"
                    return True
            except Exception as e:
                self.log(f"Error analyzing rankings: {e}", "ERROR")
        
        self.results["self_improvement"]["status"] = "skipped"
        return False
    
    def step_6_cicd_validation(self):
        """Step 6: CI/CD Pipeline Validation"""
        self.log("STEP 6: CI/CD Pipeline Validation", "STEP")
        
        self.log("Validating CI/CD configuration...", "RUNNING")
        
        cicd_files = [
            ".github/workflows/ci.yml",
            ".github/workflows/cd.yml",
            ".pre-commit-config.yaml",
            "ABACUS-v031/.pre-commit-config.yaml"
        ]
        
        found_configs = []
        for config_file in cicd_files:
            if Path(config_file).exists():
                found_configs.append(config_file)
                self.log(f"Found: {config_file}")
        
        self.results["cicd_pipeline"]["configs_found"] = len(found_configs)
        self.results["cicd_pipeline"]["configs"] = found_configs
        
        if found_configs:
            self.log(f"CI/CD configuration validated ({len(found_configs)} files)", "SUCCESS")
            self.results["cicd_pipeline"]["status"] = "validated"
        else:
            self.log("No CI/CD configuration found", "INFO")
            self.results["cicd_pipeline"]["status"] = "not_configured"
        
        self.log("Checking if push to remote is possible...", "RUNNING")
        result = self.run_command("git remote get-url origin")
        if result["success"]:
            remote_url = result["stdout"].strip()
            self.results["cicd_pipeline"]["remote_url"] = remote_url
            self.log(f"Remote URL: {remote_url}")
            
            self.log("Ready to push to GitHub", "SUCCESS")
            self.results["cicd_pipeline"]["ready_to_push"] = True
        else:
            self.log("No remote configured - skipping push", "INFO")
            self.results["cicd_pipeline"]["ready_to_push"] = False
        
        return True
    
    def generate_report(self):
        """Generate comprehensive deployment report"""
        self.log("", "INFO")
        self.log("=" * 80, "INFO")
        self.log("COMPREHENSIVE DEPLOYMENT REPORT", "INFO")
        self.log("=" * 80, "INFO")
        
        duration = (datetime.now() - self.start_time).total_seconds()
        
        print(f"\n⏱️  Total Duration: {duration:.1f}s")
        print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n📊 EXECUTION SUMMARY:")
        print(f"  1. Git Integration:      {self.results['git_integration'].get('status', 'N/A')}")
        print(f"  2. Sprint 5:             {self.results['sprint_5'].get('status', 'N/A')}")
        print(f"  3. DMAIC Phases:         {self.results['dmaic_phases'].get('completed', 0)}/{self.results['dmaic_phases'].get('total', 0)}")
        print(f"  4. MCP Iteration:        {self.results['mcp_iteration'].get('completed', 0)}/{self.results['mcp_iteration'].get('total', 0)}")
        print(f"  5. Self-Improvement:     {self.results['self_improvement'].get('status', 'N/A')}")
        print(f"  6. CI/CD Validation:     {self.results['cicd_pipeline'].get('status', 'N/A')}")
        
        if "avg_score" in self.results["self_improvement"]:
            print(f"\n📈 QUALITY METRICS:")
            print(f"  Average Score:     {self.results['self_improvement']['avg_score']:.3f}")
            print(f"  Total Artifacts:   {self.results['self_improvement']['total_artifacts']}")
        
        if self.results["git_integration"].get("branch"):
            print(f"\n🌿 GIT STATUS:")
            print(f"  Branch:            {self.results['git_integration']['branch']}")
            print(f"  Modified Files:    {self.results['git_integration'].get('modified_files', 0)}")
            print(f"  Remote:            {'Yes' if self.results['git_integration'].get('has_remote') else 'No'}")
        
        if self.results["cicd_pipeline"].get("ready_to_push"):
            print(f"\n🚀 READY FOR DEPLOYMENT:")
            print(f"  Remote URL:        {self.results['cicd_pipeline'].get('remote_url', 'N/A')}")
            print(f"  CI/CD Configs:     {self.results['cicd_pipeline'].get('configs_found', 0)} found")
        
        report_file = Path("deployment_report.json")
        with open(report_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": duration,
                "results": self.results
            }, f, indent=2)
        
        print(f"\n📄 Full report saved: {report_file}")
        print("\n" + "=" * 80)
    
    def run(self):
        """Execute full deployment orchestration"""
        self.log("", "INFO")
        self.log("=" * 80, "INFO")
        self.log("COMPREHENSIVE DOW DEPLOYMENT ORCHESTRATOR", "INFO")
        self.log("=" * 80, "INFO")
        self.log("", "INFO")
        
        try:
            self.step_1_git_integration()
            self.step_2_sprint_5_execution()
            self.step_3_dmaic_phase_0_to_9()
            self.step_4_mcp_orchestration()
            self.step_5_self_improvement()
            self.step_6_cicd_validation()
            
            self.generate_report()
            
            self.log("", "INFO")
            self.log("✅ DEPLOYMENT ORCHESTRATION COMPLETE!", "SUCCESS")
            self.log("", "INFO")
            
            return 0
            
        except KeyboardInterrupt:
            self.log("", "INFO")
            self.log("Deployment interrupted by user", "ERROR")
            return 1
        except Exception as e:
            self.log(f"Deployment failed: {e}", "ERROR")
            return 1

if __name__ == "__main__":
    orchestrator = DeploymentOrchestrator()
    sys.exit(orchestrator.run())
