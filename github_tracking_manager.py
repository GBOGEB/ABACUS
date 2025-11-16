#!/usr/bin/env python3
"""
GitHub CI/CD Tracking Manager
Tracks PR lifecycle, CI/CD runs, issues, Copilot feedback, and missed opportunities
Maintains both JSON and YAML state files for local and GitHub synchronization
"""

import os
import sys
import json
import yaml
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

try:
    from github import Github
except ImportError:
    print("Installing PyGithub...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "PyGithub", "PyYAML"])
    from github import Github


class GitHubTrackingManager:
    """Manages GitHub CI/CD tracking state"""
    
    def __init__(self, token: str, repo_name: str):
        self.github = Github(token)
        self.repo = self.github.get_repo(repo_name)
        self.repo_name = repo_name
        
        self.json_file = Path("github_tracking_state.json")
        self.yaml_file = Path("github_tracking_state.yaml")
        
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """Load tracking state from JSON file"""
        if self.json_file.exists():
            with open(self.json_file, 'r') as f:
                return json.load(f)
        return self._create_empty_state()
    
    def _create_empty_state(self) -> Dict:
        """Create empty tracking state"""
        return {
            "metadata": {
                "version": "1.0.0",
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "repository": self.repo_name,
                "tracking_started": datetime.utcnow().isoformat() + "Z"
            },
            "pull_requests": {},
            "issues": {},
            "ci_cd_history": {
                "ci_runs": [],
                "cd_deployments": [],
                "missed_opportunities": []
            },
            "copilot_feedback_queue": [],
            "action_items": []
        }
    
    def _save_state(self):
        """Save tracking state to both JSON and YAML"""
        self.state["metadata"]["last_updated"] = datetime.utcnow().isoformat() + "Z"
        
        with open(self.json_file, 'w') as f:
            json.dump(self.state, f, indent=2)
        
        with open(self.yaml_file, 'w') as f:
            yaml.dump(self.state, f, default_flow_style=False, sort_keys=False)
        
        print(f"✅ State saved to {self.json_file} and {self.yaml_file}")
    
    def sync_pr(self, pr_number: int):
        """Sync PR data from GitHub"""
        print(f"\n🔄 Syncing PR #{pr_number}...")
        
        try:
            pr = self.repo.get_pull(pr_number)
        except Exception as e:
            print(f"❌ Error fetching PR #{pr_number}: {e}")
            return
        
        pr_key = str(pr_number)
        
        if pr_key not in self.state["pull_requests"]:
            self.state["pull_requests"][pr_key] = {
                "number": pr_number,
                "title": pr.title,
                "branch": pr.head.ref,
                "status": "open",
                "created_at": pr.created_at.isoformat() + "Z",
                "author": pr.user.login,
                "reviewers": [],
                "ci_runs": [],
                "cd_deployments": [],
                "issues_created": [],
                "copilot_feedback": [],
                "post_merge_actions": [],
                "lessons_learned": [],
                "tags": []
            }
        
        pr_data = self.state["pull_requests"][pr_key]
        
        pr_data["title"] = pr.title
        pr_data["status"] = "merged" if pr.merged else ("closed" if pr.closed_at else "open")
        
        if pr.merged_at:
            pr_data["merged_at"] = pr.merged_at.isoformat() + "Z"
        if pr.closed_at:
            pr_data["closed_at"] = pr.closed_at.isoformat() + "Z"
        
        pr_data["reviewers"] = [r.login for r in pr.get_reviews()]
        
        print(f"✅ PR #{pr_number} synced: {pr_data['status']}")
        
        self._save_state()
    
    def sync_ci_runs(self, pr_number: int):
        """Sync CI runs for a PR"""
        print(f"\n🔄 Syncing CI runs for PR #{pr_number}...")
        
        try:
            pr = self.repo.get_pull(pr_number)
            commits = list(pr.get_commits())
            
            if not commits:
                print("⚠️  No commits found")
                return
            
            latest_commit = commits[-1]
            check_runs = latest_commit.get_check_runs()
            
            pr_key = str(pr_number)
            if pr_key not in self.state["pull_requests"]:
                self.sync_pr(pr_number)
            
            pr_data = self.state["pull_requests"][pr_key]
            
            for check in check_runs:
                run_data = {
                    "run_id": check.id,
                    "name": check.name,
                    "status": check.status,
                    "conclusion": check.conclusion,
                    "started_at": check.started_at.isoformat() + "Z" if check.started_at else None,
                    "completed_at": check.completed_at.isoformat() + "Z" if check.completed_at else None,
                    "workflow": check.name,
                    "url": check.html_url
                }
                
                existing = next((r for r in pr_data["ci_runs"] if r.get("run_id") == check.id), None)
                if existing:
                    existing.update(run_data)
                else:
                    pr_data["ci_runs"].append(run_data)
                
                self.state["ci_cd_history"]["ci_runs"].append({
                    **run_data,
                    "pr_number": pr_number
                })
            
            print(f"✅ Synced {len(list(check_runs))} CI runs")
            
            self._save_state()
            
        except Exception as e:
            print(f"❌ Error syncing CI runs: {e}")
    
    def capture_copilot_feedback(self, pr_number: int, feedback_type: str, message: str, 
                                  file: str = "", line: int = 0, source: str = "github_copilot"):
        """Capture Copilot or GitHub feedback"""
        print(f"\n📝 Capturing {feedback_type} feedback for PR #{pr_number}...")
        
        feedback_id = f"fb_{pr_number}_{datetime.utcnow().timestamp()}"
        
        feedback = {
            "id": feedback_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "pr_number": pr_number,
            "type": feedback_type,
            "source": source,
            "message": message,
            "file": file,
            "line": line,
            "status": "pending",
            "reviewed_by": "",
            "reviewed_at": "",
            "implementation_pr": None
        }
        
        self.state["copilot_feedback_queue"].append(feedback)
        
        pr_key = str(pr_number)
        if pr_key in self.state["pull_requests"]:
            self.state["pull_requests"][pr_key]["copilot_feedback"].append({
                "timestamp": feedback["timestamp"],
                "type": feedback_type,
                "source": source,
                "message": message,
                "file": file,
                "line": line,
                "action_taken": False,
                "action_details": ""
            })
        
        print(f"✅ Feedback captured: {feedback_id}")
        
        self._save_state()
        
        return feedback_id
    
    def create_action_item(self, title: str, description: str, priority: str = "medium",
                          category: str = "general", related_pr: int = None, related_issue: int = None):
        """Create an action item"""
        print(f"\n📋 Creating action item: {title}...")
        
        action_id = f"action_{datetime.utcnow().timestamp()}"
        
        action = {
            "id": action_id,
            "title": title,
            "description": description,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "due_date": "",
            "assigned_to": "",
            "related_pr": related_pr,
            "related_issue": related_issue,
            "category": category
        }
        
        self.state["action_items"].append(action)
        
        print(f"✅ Action item created: {action_id}")
        
        self._save_state()
        
        return action_id
    
    def analyze_missed_opportunities(self, pr_number: int):
        """Analyze PR for missed CI/CD opportunities"""
        print(f"\n🔍 Analyzing PR #{pr_number} for missed opportunities...")
        
        try:
            pr = self.repo.get_pull(pr_number)
            
            opportunities = []
            
            if pr.merged:
                commits = list(pr.get_commits())
                if commits:
                    latest_commit = commits[-1]
                    check_runs = list(latest_commit.get_check_runs())
                    
                    if not check_runs:
                        opportunities.append({
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "type": "ci_missing",
                            "description": "No CI checks found for this PR",
                            "potential_impact": "Untested code merged to main branch",
                            "action_item": "Add CI workflow to repository",
                            "priority": "high"
                        })
                    
                    failed_checks = [c for c in check_runs if c.conclusion == "failure"]
                    if failed_checks:
                        opportunities.append({
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "type": "ci_failure_merged",
                            "description": f"PR merged with {len(failed_checks)} failing checks",
                            "potential_impact": "Failed tests merged to main branch",
                            "action_item": "Review and fix failing tests, consider branch protection",
                            "priority": "critical"
                        })
                    
                    files = list(pr.get_files())
                    test_files = [f for f in files if 'test' in f.filename.lower()]
                    
                    if not test_files and len(files) > 0:
                        opportunities.append({
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "type": "test_coverage",
                            "description": "No test files added/modified in PR",
                            "potential_impact": "Reduced test coverage",
                            "action_item": "Add tests for new functionality",
                            "priority": "medium"
                        })
            
            if opportunities:
                self.state["ci_cd_history"]["missed_opportunities"].extend(opportunities)
                print(f"⚠️  Found {len(opportunities)} missed opportunities")
                for opp in opportunities:
                    print(f"   - {opp['type']}: {opp['description']}")
            else:
                print("✅ No missed opportunities found")
            
            self._save_state()
            
        except Exception as e:
            print(f"❌ Error analyzing opportunities: {e}")
    
    def create_sub_issue(self, parent_issue: int, title: str, description: str):
        """Create a sub-issue for complex issues"""
        print(f"\n🔗 Creating sub-issue for #{parent_issue}...")
        
        try:
            body = f"**Parent Issue:** #{parent_issue}\n\n{description}"
            
            issue = self.repo.create_issue(
                title=f"[Sub-Issue] {title}",
                body=body,
                labels=["sub-issue", "automated"]
            )
            
            parent_key = str(parent_issue)
            if parent_key not in self.state["issues"]:
                self.state["issues"][parent_key] = {
                    "number": parent_issue,
                    "title": "",
                    "status": "open",
                    "priority": "medium",
                    "labels": [],
                    "created_at": datetime.utcnow().isoformat() + "Z",
                    "closed_at": "",
                    "related_pr": None,
                    "parent_issue": None,
                    "sub_issues": [],
                    "ci_failure": False,
                    "cd_failure": False,
                    "copilot_suggestion": False
                }
            
            self.state["issues"][parent_key]["sub_issues"].append(issue.number)
            
            self.state["issues"][str(issue.number)] = {
                "number": issue.number,
                "title": issue.title,
                "status": "open",
                "priority": "medium",
                "labels": [l.name for l in issue.labels],
                "created_at": issue.created_at.isoformat() + "Z",
                "closed_at": "",
                "related_pr": None,
                "parent_issue": parent_issue,
                "sub_issues": [],
                "ci_failure": False,
                "cd_failure": False,
                "copilot_suggestion": False
            }
            
            print(f"✅ Sub-issue created: #{issue.number}")
            
            self._save_state()
            
            return issue.number
            
        except Exception as e:
            print(f"❌ Error creating sub-issue: {e}")
            return None
    
    def review_feedback_queue(self):
        """Review pending Copilot feedback"""
        print("\n📋 Reviewing Copilot Feedback Queue...")
        print("=" * 60)
        
        pending = [f for f in self.state["copilot_feedback_queue"] if f["status"] == "pending"]
        
        if not pending:
            print("✅ No pending feedback items")
            return
        
        print(f"Found {len(pending)} pending feedback items:\n")
        
        for i, feedback in enumerate(pending, 1):
            print(f"{i}. [{feedback['type'].upper()}] PR #{feedback['pr_number']}")
            print(f"   Source: {feedback['source']}")
            print(f"   Message: {feedback['message']}")
            if feedback['file']:
                print(f"   File: {feedback['file']}:{feedback['line']}")
            print(f"   Status: {feedback['status']}")
            print()
    
    def generate_report(self, pr_number: Optional[int] = None):
        """Generate tracking report"""
        print("\n" + "=" * 60)
        print("GitHub CI/CD Tracking Report")
        print("=" * 60)
        
        if pr_number:
            pr_key = str(pr_number)
            if pr_key in self.state["pull_requests"]:
                pr_data = self.state["pull_requests"][pr_key]
                print(f"\n📊 PR #{pr_number}: {pr_data['title']}")
                print(f"   Status: {pr_data['status']}")
                print(f"   Branch: {pr_data['branch']}")
                print(f"   Author: {pr_data['author']}")
                print(f"   CI Runs: {len(pr_data['ci_runs'])}")
                print(f"   Issues Created: {len(pr_data['issues_created'])}")
                print(f"   Copilot Feedback: {len(pr_data['copilot_feedback'])}")
            else:
                print(f"⚠️  PR #{pr_number} not found in tracking state")
        else:
            print(f"\n📊 Summary:")
            print(f"   Total PRs: {len(self.state['pull_requests'])}")
            print(f"   Total Issues: {len(self.state['issues'])}")
            print(f"   CI Runs: {len(self.state['ci_cd_history']['ci_runs'])}")
            print(f"   CD Deployments: {len(self.state['ci_cd_history']['cd_deployments'])}")
            print(f"   Missed Opportunities: {len(self.state['ci_cd_history']['missed_opportunities'])}")
            print(f"   Pending Feedback: {len([f for f in self.state['copilot_feedback_queue'] if f['status'] == 'pending'])}")
            print(f"   Action Items: {len([a for a in self.state['action_items'] if a['status'] == 'pending'])}")
        
        print("=" * 60)


def get_github_token():
    """Get GitHub token from gh CLI or environment"""
    try:
        result = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True, check=True)
        token = result.stdout.strip()
        if token:
            return token, "GitHub CLI"
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Warning: Failed to get GitHub token from CLI: {e}", file=sys.stderr)
    
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        return token, "Environment Variable"
    
    return None, None


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GitHub CI/CD Tracking Manager")
    parser.add_argument('--pr', type=int, help='PR number to track')
    parser.add_argument('--sync-pr', type=int, help='Sync PR data from GitHub')
    parser.add_argument('--sync-ci', type=int, help='Sync CI runs for PR')
    parser.add_argument('--analyze', type=int, help='Analyze PR for missed opportunities')
    parser.add_argument('--report', action='store_true', help='Generate tracking report')
    parser.add_argument('--review-feedback', action='store_true', help='Review pending feedback')
    parser.add_argument('--repo', help='Repository name (owner/repo)')
    parser.add_argument('--token', help='GitHub token')
    
    args = parser.parse_args()
    
    token = args.token
    auth_method = "Command Line"
    
    if not token:
        token, auth_method = get_github_token()
    
    if not token:
        print("❌ GitHub authentication required!")
        print("\nPlease use one of these methods:")
        print("  1. GitHub CLI: gh auth login")
        print("  2. Environment variable: export GITHUB_TOKEN=<token>")
        print("  3. Command line: --token <token>")
        sys.exit(1)
    
    print(f"✅ Authenticated via: {auth_method}")
    
    repo_name = args.repo or os.environ.get('GITHUB_REPOSITORY')
    if not repo_name:
        try:
            result = subprocess.run(['git', 'remote', 'get-url', 'origin'], capture_output=True, text=True)
            if result.returncode == 0:
                url = result.stdout.strip()
                if 'github.com' in url:
                    parts = url.split('github.com')[-1].strip('/:').replace('.git', '')
                    repo_name = parts
        except:
            pass
    
    if not repo_name:
        print("❌ Repository name required")
        sys.exit(1)
    
    print(f"📦 Repository: {repo_name}\n")
    
    manager = GitHubTrackingManager(token, repo_name)
    
    if args.sync_pr:
        manager.sync_pr(args.sync_pr)
    
    if args.sync_ci:
        manager.sync_ci_runs(args.sync_ci)
    
    if args.analyze:
        manager.analyze_missed_opportunities(args.analyze)
    
    if args.review_feedback:
        manager.review_feedback_queue()
    
    if args.report:
        manager.generate_report(args.pr)
    
    if not any([args.sync_pr, args.sync_ci, args.analyze, args.review_feedback, args.report]):
        print("No action specified. Use --help for options.")


if __name__ == '__main__':
    main()
