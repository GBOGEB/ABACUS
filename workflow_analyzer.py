#!/usr/bin/env python3
"""
GitHub Workflow Analyzer
Analyzes past GitHub Actions workflows to identify missed opportunities
Reviews CI/CD history and suggests improvements
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

try:
    from github import Github
except ImportError:
    print("Installing PyGithub...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "PyGithub"])
    from github import Github


class WorkflowAnalyzer:
    """Analyze GitHub Actions workflows"""
    
    def __init__(self, token: str, repo_name: str):
        self.github = Github(token)
        self.repo = self.github.get_repo(repo_name)
        self.repo_name = repo_name
    
    def get_workflow_runs(self, days: int = 30) -> List[Dict]:
        """Get workflow runs from the last N days"""
        print(f"\n🔍 Fetching workflow runs from last {days} days...")
        
        since = datetime.utcnow() - timedelta(days=days)
        runs = []
        
        try:
            for run in self.repo.get_workflow_runs():
                if run.created_at < since:
                    break
                
                run_data = {
                    "id": run.id,
                    "name": run.name,
                    "status": run.status,
                    "conclusion": run.conclusion,
                    "created_at": run.created_at.isoformat() + "Z",
                    "updated_at": run.updated_at.isoformat() + "Z",
                    "run_number": run.run_number,
                    "event": run.event,
                    "head_branch": run.head_branch,
                    "head_sha": run.head_sha[:7] if run.head_sha else "",
                    "url": run.html_url
                }
                
                runs.append(run_data)
        
        except Exception as e:
            print(f"⚠️  Error fetching workflow runs: {e}")
        
        print(f"✅ Found {len(runs)} workflow runs")
        return runs
    
    def analyze_failure_patterns(self, runs: List[Dict]) -> Dict:
        """Analyze failure patterns"""
        print("\n🔍 Analyzing failure patterns...")
        
        failures_by_workflow = defaultdict(int)
        failures_by_branch = defaultdict(int)
        total_failures = 0
        
        for run in runs:
            if run["conclusion"] == "failure":
                total_failures += 1
                failures_by_workflow[run["name"]] += 1
                failures_by_branch[run["head_branch"]] += 1
        
        analysis = {
            "total_runs": len(runs),
            "total_failures": total_failures,
            "failure_rate": (total_failures / len(runs) * 100) if runs else 0,
            "failures_by_workflow": dict(failures_by_workflow),
            "failures_by_branch": dict(failures_by_branch),
            "most_failing_workflow": max(failures_by_workflow.items(), key=lambda x: x[1])[0] if failures_by_workflow else None,
            "most_failing_branch": max(failures_by_branch.items(), key=lambda x: x[1])[0] if failures_by_branch else None
        }
        
        return analysis
    
    def identify_missed_opportunities(self, runs: List[Dict]) -> List[Dict]:
        """Identify missed CI/CD opportunities"""
        print("\n🎯 Identifying missed opportunities...")
        
        opportunities = []
        
        failure_runs = [r for r in runs if r["conclusion"] == "failure"]
        if len(failure_runs) > len(runs) * 0.2:
            opportunities.append({
                "type": "high_failure_rate",
                "severity": "high",
                "description": f"High failure rate detected: {len(failure_runs)}/{len(runs)} runs failed",
                "recommendation": "Review test stability, consider flaky test detection",
                "action_items": [
                    "Identify and fix flaky tests",
                    "Add retry logic for unstable tests",
                    "Review test environment setup"
                ]
            })
        
        workflow_names = set(r["name"] for r in runs)
        if "test" not in " ".join(workflow_names).lower():
            opportunities.append({
                "type": "missing_tests",
                "severity": "critical",
                "description": "No test workflow detected",
                "recommendation": "Add automated testing workflow",
                "action_items": [
                    "Create test workflow",
                    "Add unit tests",
                    "Add integration tests"
                ]
            })
        
        if "deploy" not in " ".join(workflow_names).lower() and "cd" not in " ".join(workflow_names).lower():
            opportunities.append({
                "type": "missing_cd",
                "severity": "medium",
                "description": "No deployment workflow detected",
                "recommendation": "Add continuous deployment workflow",
                "action_items": [
                    "Create deployment workflow",
                    "Set up staging environment",
                    "Add production deployment"
                ]
            })
        
        long_runs = [r for r in runs if r["status"] == "completed"]
        if long_runs:
            opportunities.append({
                "type": "workflow_optimization",
                "severity": "low",
                "description": "Workflow runtime could be optimized",
                "recommendation": "Consider caching dependencies, parallel jobs",
                "action_items": [
                    "Add dependency caching",
                    "Parallelize test execution",
                    "Optimize build steps"
                ]
            })
        
        pr_runs = [r for r in runs if r["event"] == "pull_request"]
        push_runs = [r for r in runs if r["event"] == "push"]
        
        if len(pr_runs) < len(push_runs) * 0.5:
            opportunities.append({
                "type": "insufficient_pr_checks",
                "severity": "medium",
                "description": "Few PR checks compared to push events",
                "recommendation": "Ensure all PRs trigger CI checks",
                "action_items": [
                    "Review workflow triggers",
                    "Add required status checks",
                    "Enable branch protection"
                ]
            })
        
        return opportunities
    
    def generate_recommendations(self, analysis: Dict, opportunities: List[Dict]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if analysis["failure_rate"] > 20:
            recommendations.append(
                f"🔴 HIGH PRIORITY: Failure rate is {analysis['failure_rate']:.1f}%. "
                "Focus on stabilizing tests and improving code quality."
            )
        
        if analysis["most_failing_workflow"]:
            recommendations.append(
                f"⚠️  Workflow '{analysis['most_failing_workflow']}' has the most failures. "
                "Review and fix this workflow first."
            )
        
        for opp in opportunities:
            if opp["severity"] == "critical":
                recommendations.append(f"🔴 CRITICAL: {opp['description']} - {opp['recommendation']}")
            elif opp["severity"] == "high":
                recommendations.append(f"🟠 HIGH: {opp['description']} - {opp['recommendation']}")
            elif opp["severity"] == "medium":
                recommendations.append(f"🟡 MEDIUM: {opp['description']} - {opp['recommendation']}")
        
        return recommendations
    
    def create_analysis_report(self, days: int = 30) -> Dict:
        """Create comprehensive analysis report"""
        runs = self.get_workflow_runs(days)
        
        if not runs:
            return {
                "error": "No workflow runs found",
                "recommendations": ["Add GitHub Actions workflows to enable CI/CD"]
            }
        
        analysis = self.analyze_failure_patterns(runs)
        opportunities = self.identify_missed_opportunities(runs)
        recommendations = self.generate_recommendations(analysis, opportunities)
        
        report = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "repository": self.repo_name,
            "analysis_period_days": days,
            "summary": analysis,
            "missed_opportunities": opportunities,
            "recommendations": recommendations,
            "workflow_runs": runs
        }
        
        return report
    
    def display_report(self, report: Dict):
        """Display analysis report"""
        print("\n" + "=" * 80)
        print("📊 GitHub Workflow Analysis Report")
        print("=" * 80)
        
        if "error" in report:
            print(f"\n❌ {report['error']}")
            print("\n💡 Recommendations:")
            for rec in report["recommendations"]:
                print(f"   {rec}")
            return
        
        summary = report["summary"]
        
        print(f"\n📈 Summary ({report['analysis_period_days']} days):")
        print(f"   Total Runs: {summary['total_runs']}")
        print(f"   Total Failures: {summary['total_failures']}")
        print(f"   Failure Rate: {summary['failure_rate']:.1f}%")
        
        if summary["most_failing_workflow"]:
            print(f"   Most Failing Workflow: {summary['most_failing_workflow']}")
        
        if summary["most_failing_branch"]:
            print(f"   Most Failing Branch: {summary['most_failing_branch']}")
        
        print(f"\n🎯 Missed Opportunities ({len(report['missed_opportunities'])}):")
        for opp in report["missed_opportunities"]:
            severity_icon = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢"
            }.get(opp["severity"], "ℹ️")
            
            print(f"\n{severity_icon} {opp['type'].upper()} ({opp['severity']})")
            print(f"   Description: {opp['description']}")
            print(f"   Recommendation: {opp['recommendation']}")
            print(f"   Action Items:")
            for action in opp["action_items"]:
                print(f"      - {action}")
        
        print(f"\n💡 Top Recommendations:")
        for i, rec in enumerate(report["recommendations"][:5], 1):
            print(f"   {i}. {rec}")
        
        print("\n" + "=" * 80)
    
    def save_report(self, report: Dict, filename: str = "workflow_analysis_report.json"):
        """Save analysis report to file"""
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n✅ Analysis report saved to {filename}")


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
    
    parser = argparse.ArgumentParser(description="GitHub Workflow Analyzer")
    parser.add_argument('--days', type=int, default=30, help='Number of days to analyze (default: 30)')
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
            # Ignore errors if unable to determine repo name from git
            pass
    
    if not repo_name:
        print("❌ Repository name required")
        sys.exit(1)
    
    print(f"📦 Repository: {repo_name}\n")
    
    analyzer = WorkflowAnalyzer(token, repo_name)
    
    report = analyzer.create_analysis_report(args.days)
    analyzer.display_report(report)
    
    if args.save_report:
        analyzer.save_report(report, args.save_report)
    else:
        analyzer.save_report(report)


if __name__ == '__main__':
    main()
