#!/usr/bin/env python3
"""
CD (Continuous Deployment) Monitor
Tracks deployment status, health checks, and rollback capabilities
Complements CI monitoring with deployment tracking
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from typing import Dict, List, Optional

try:
    from github import Github
except ImportError:
    print("Installing PyGithub...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "PyGithub"])
    from github import Github


class CDMonitor:
    """Monitor Continuous Deployment status"""
    
    def __init__(self, token: str, repo_name: str):
        self.github = Github(token)
        self.repo = self.github.get_repo(repo_name)
        self.repo_name = repo_name
    
    def get_deployments(self, environment: Optional[str] = None) -> List[Dict]:
        """Get deployment history"""
        print(f"\n📦 Fetching deployments for {self.repo_name}...")
        
        deployments = []
        
        try:
            for deployment in self.repo.get_deployments():
                if environment and deployment.environment != environment:
                    continue
                
                statuses = list(deployment.get_statuses())
                latest_status = statuses[0] if statuses else None
                
                deployment_data = {
                    "id": deployment.id,
                    "environment": deployment.environment,
                    "ref": deployment.ref,
                    "sha": deployment.sha[:7],
                    "created_at": deployment.created_at.isoformat() + "Z",
                    "creator": deployment.creator.login if deployment.creator else "unknown",
                    "status": latest_status.state if latest_status else "unknown",
                    "description": latest_status.description if latest_status else "",
                    "url": latest_status.target_url if latest_status else ""
                }
                
                deployments.append(deployment_data)
        
        except Exception as e:
            print(f"⚠️  Error fetching deployments: {e}")
        
        return deployments
    
    def display_deployments(self, deployments: List[Dict]):
        """Display deployment status"""
        print("\n" + "=" * 80)
        print("📦 Deployment Status")
        print("=" * 80)
        
        if not deployments:
            print("ℹ️  No deployments found")
            return
        
        environments = {}
        for dep in deployments:
            env = dep["environment"]
            if env not in environments:
                environments[env] = []
            environments[env].append(dep)
        
        for env, deps in environments.items():
            print(f"\n🌍 Environment: {env}")
            print("-" * 80)
            
            for dep in deps[:5]:
                status_icon = {
                    "success": "✅",
                    "failure": "❌",
                    "pending": "⏳",
                    "error": "🔴",
                    "unknown": "❓"
                }.get(dep["status"], "❓")
                
                print(f"{status_icon} {dep['sha']} - {dep['status']}")
                print(f"   Created: {dep['created_at']}")
                print(f"   By: {dep['creator']}")
                if dep['description']:
                    print(f"   Description: {dep['description']}")
                if dep['url']:
                    print(f"   URL: {dep['url']}")
                print()
    
    def check_deployment_health(self, deployment_id: int) -> Dict:
        """Check deployment health"""
        print(f"\n🏥 Checking health for deployment {deployment_id}...")
        
        try:
            deployment = self.repo.get_deployment(deployment_id)
            statuses = list(deployment.get_statuses())
            
            if not statuses:
                return {
                    "healthy": False,
                    "status": "unknown",
                    "message": "No status information available"
                }
            
            latest = statuses[0]
            
            health = {
                "healthy": latest.state == "success",
                "status": latest.state,
                "message": latest.description or "",
                "url": latest.target_url or "",
                "updated_at": latest.created_at.isoformat() + "Z"
            }
            
            return health
        
        except Exception as e:
            return {
                "healthy": False,
                "status": "error",
                "message": str(e)
            }
    
    def create_deployment_report(self, environment: str = None) -> Dict:
        """Create deployment report"""
        deployments = self.get_deployments(environment)
        
        report = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "repository": self.repo_name,
            "environment": environment or "all",
            "total_deployments": len(deployments),
            "successful": len([d for d in deployments if d["status"] == "success"]),
            "failed": len([d for d in deployments if d["status"] == "failure"]),
            "pending": len([d for d in deployments if d["status"] == "pending"]),
            "deployments": deployments
        }
        
        return report
    
    def save_deployment_report(self, report: Dict, filename: str = "cd_deployment_report.json"):
        """Save deployment report to file"""
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"✅ Deployment report saved to {filename}")


def get_github_token():
    """Get GitHub token from gh CLI or environment"""
    try:
        result = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True, check=True)
        token = result.stdout.strip()
        if token:
            return token, "GitHub CLI"
    except:
        pass
    
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        return token, "Environment Variable"
    
    return None, None


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="CD (Continuous Deployment) Monitor")
    parser.add_argument('--environment', help='Filter by environment (staging, production, etc.)')
    parser.add_argument('--health-check', type=int, help='Check health of specific deployment ID')
    parser.add_argument('--report', action='store_true', help='Generate deployment report')
    parser.add_argument('--save-report', help='Save report to file')
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
    
    monitor = CDMonitor(token, repo_name)
    
    if args.health_check:
        health = monitor.check_deployment_health(args.health_check)
        print(f"\n🏥 Health Status:")
        print(f"   Healthy: {'✅ Yes' if health['healthy'] else '❌ No'}")
        print(f"   Status: {health['status']}")
        print(f"   Message: {health['message']}")
        if health.get('url'):
            print(f"   URL: {health['url']}")
    
    elif args.report:
        report = monitor.create_deployment_report(args.environment)
        
        print(f"\n📊 Deployment Report:")
        print(f"   Total Deployments: {report['total_deployments']}")
        print(f"   ✅ Successful: {report['successful']}")
        print(f"   ❌ Failed: {report['failed']}")
        print(f"   ⏳ Pending: {report['pending']}")
        
        if args.save_report:
            monitor.save_deployment_report(report, args.save_report)
        else:
            monitor.save_deployment_report(report)
    
    else:
        deployments = monitor.get_deployments(args.environment)
        monitor.display_deployments(deployments)


if __name__ == '__main__':
    main()
