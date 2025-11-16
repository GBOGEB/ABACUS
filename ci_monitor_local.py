#!/usr/bin/env python3
"""
Local CI Monitor for GitHub Pull Requests
Monitors CI/CD status and creates issues for failures
Uses GitHub CLI authentication (gh auth) for secure access
"""

import os
import sys
import time
import argparse
import subprocess
from datetime import datetime

try:
    from github import Github
except ImportError:
    print("Installing required packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "PyGithub"])
    from github import Github


def get_github_token():
    """
    Get GitHub token using multiple methods (in order of preference):
    1. GitHub CLI (gh auth token)
    2. GITHUB_TOKEN environment variable
    3. Command line argument
    """
    # Try GitHub CLI first (most secure)
    try:
        result = subprocess.run(
            ['gh', 'auth', 'token'],
            capture_output=True,
            text=True,
            check=True
        )
        token = result.stdout.strip()
        if token:
            return token, "GitHub CLI"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Try environment variable
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        return token, "Environment Variable"

    return None, None


class LocalCIMonitor:
    """Monitor CI/CD status and create issues locally"""
    
    def __init__(self, token: str, repo_name: str, pr_number: int):
        self.github = Github(token)
        self.repo = self.github.get_repo(repo_name)
        self.pr_number = pr_number
        self.pr = self.repo.get_pull(pr_number)
        
    def get_ci_status(self) -> Dict:
        """Get current CI/CD status"""
        # Get the latest commit
        commits = list(self.pr.get_commits())
        if not commits:
            return {"status": "unknown", "checks": []}
        
        latest_commit = commits[-1]
        
        # Get check runs
        check_runs = latest_commit.get_check_runs()
        
        status = {
            "commit": latest_commit.sha[:7],
            "status": "pending",
            "checks": [],
            "total": 0,
            "passed": 0,
            "failed": 0,
            "pending": 0
        }
        
        for check in check_runs:
            check_info = {
                "name": check.name,
                "status": check.status,
                "conclusion": check.conclusion,
                "url": check.html_url
            }
            status["checks"].append(check_info)
            status["total"] += 1
            
            if check.conclusion == "success":
                status["passed"] += 1
            elif check.conclusion == "failure":
                status["failed"] += 1
            else:
                status["pending"] += 1
        
        # Overall status
        if status["failed"] > 0:
            status["status"] = "failed"
        elif status["pending"] > 0:
            status["status"] = "pending"
        elif status["passed"] == status["total"]:
            status["status"] = "success"
        
        return status
    
    def display_status(self, status: Dict):
        """Display CI/CD status in terminal"""
        print("\n" + "=" * 70)
        print(f"🔍 CI/CD Status for PR #{self.pr_number}")
        print("=" * 70)
        print(f"Title: {self.pr.title}")
        print(f"Commit: {status['commit']}")
        print(f"Status: {self._format_status(status['status'])}")
        print(f"\n📊 Summary:")
        print(f"   Total Checks: {status['total']}")
        print(f"   ✅ Passed: {status['passed']}")
        print(f"   ❌ Failed: {status['failed']}")
        print(f"   ⏳ Pending: {status['pending']}")
        
        if status['checks']:
            print(f"\n🔧 Check Details:")
            for check in status['checks']:
                icon = self._get_check_icon(check['conclusion'])
                print(f"   {icon} {check['name']}: {check['conclusion'] or check['status']}")
        
        print("=" * 70)
    
    def _format_status(self, status: str) -> str:
        """Format status with emoji"""
        if status == "success":
            return "✅ SUCCESS"
        elif status == "failed":
            return "❌ FAILED"
        elif status == "pending":
            return "⏳ PENDING"
        else:
            return "❓ UNKNOWN"
    
    def _get_check_icon(self, conclusion: Optional[str]) -> str:
        """Get icon for check conclusion"""
        if conclusion == "success":
            return "✅"
        elif conclusion == "failure":
            return "❌"
        elif conclusion == "cancelled":
            return "🚫"
        elif conclusion == "skipped":
            return "⏭️"
        else:
            return "⏳"
    
    def fetch_test_results(self) -> Optional[Dict]:
        """Fetch test results from CI artifacts"""
        print("\n🔍 Fetching test results from CI artifacts...")
        
        # Get workflow runs for this PR
        commits = list(self.pr.get_commits())
        if not commits:
            print("⚠️  No commits found")
            return None
        
        latest_commit = commits[-1]
        
        # Get workflow runs
        runs = self.repo.get_workflow_runs(
            head_sha=latest_commit.sha,
            status="completed"
        )
        
        for run in runs:
            # Get artifacts
            artifacts = run.get_artifacts()
            for artifact in artifacts:
                if 'test' in artifact.name.lower():
                    print(f"   Found artifact: {artifact.name}")
                    # Note: Downloading artifacts requires additional authentication
                    # For now, we'll rely on the GitHub Actions workflow
        
        return None
    
    def create_issues_from_failures(self, status: Dict):
        """Create GitHub issues for failing checks"""
        if status['failed'] == 0:
            print("\n✅ No failures to create issues for")
            return
        
        print(f"\n🔧 Creating issues for {status['failed']} failing check(s)...")
        
        for check in status['checks']:
            if check['conclusion'] == 'failure':
                self._create_issue_for_check(check)
    
    def _create_issue_for_check(self, check: Dict):
        """Create issue for a failing check"""
        check_name = check['name']
        
        # Check for existing issues
        query = f'repo:{self.repo.full_name} is:issue is:open label:ci-failure "{check_name}"'
        existing = list(self.github.search_issues(query))
        
        if existing:
            print(f"   ℹ️  Issue already exists for {check_name}: #{existing[0].number}")
            return
        
        # Create issue
        title = f"🔴 CI Failure: {check_name}"
        body = f"""## 🔴 CI/CD Check Failure

**Check:** `{check_name}`  
**Status:** {check['conclusion']}  
**PR:** #{self.pr_number}  
**Detected:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

### 🔗 Links

- [Check Details]({check['url']})
- [Pull Request #{self.pr_number}](https://github.com/{self.repo.full_name}/pull/{self.pr_number})

### 🔍 Investigation Steps

1. **View check logs:**
   - Click the link above to see detailed logs
   - Look for error messages and stack traces

2. **Reproduce locally:**
   ```bash
   git fetch origin pull/{self.pr_number}/head:pr-{self.pr_number}
   git checkout pr-{self.pr_number}
   # Run the failing check locally
   ```

3. **Fix and verify:**
   - Implement the fix
   - Test locally
   - Push to the PR branch
   - Verify CI passes

### 🛠️ Fix Checklist

- [ ] Identify root cause
- [ ] Implement fix
- [ ] Test locally
- [ ] Update PR
- [ ] Verify CI passes

---

**Note:** This issue was automatically created by the local CI monitoring system.
"""
        
        try:
            issue = self.repo.create_issue(
                title=title,
                body=body,
                labels=['ci-failure', 'automated', 'priority:high']
            )
            print(f"   ✅ Created issue #{issue.number}: {title}")
            
            # Add comment to PR
            self.pr.create_issue_comment(f"🔗 Created issue #{issue.number} for failing check: {check_name}")
            
        except GithubException as e:
            print(f"   ❌ Failed to create issue: {e}")
    
    def watch_ci(self, interval: int = 30):
        """Watch CI/CD status continuously"""
        print(f"\n👀 Watching CI/CD status (checking every {interval}s)...")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                status = self.get_ci_status()
                self.display_status(status)
                
                if status['status'] == 'success':
                    print("\n🎉 All checks passed!")
                    break
                elif status['status'] == 'failed':
                    print("\n⚠️  Some checks failed. Run with --create-issues to create GitHub issues.")
                    break
                
                print(f"\n⏳ Waiting {interval}s before next check...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n👋 Stopped watching")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Monitor CI/CD status and create issues for failures"
    )
    parser.add_argument(
        '--pr',
        type=int,
        required=True,
        help='Pull request number'
    )
    parser.add_argument(
        '--watch',
        action='store_true',
        help='Watch CI/CD status continuously'
    )
    parser.add_argument(
        '--create-issues',
        action='store_true',
        help='Create GitHub issues for failures'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=30,
        help='Watch interval in seconds (default: 30)'
    )
    parser.add_argument(
        '--token',
        help='GitHub token (optional - will use gh CLI if not provided)'
    )
    parser.add_argument(
        '--repo',
        help='Repository name (owner/repo) (or set GITHUB_REPOSITORY env var)'
    )

    args = parser.parse_args()

    # Get token using multiple methods
    token = args.token
    auth_method = "Command Line"

    if not token:
        token, auth_method = get_github_token()

    if not token:
        print("❌ GitHub authentication required!")
        print("\nPlease use one of these methods:")
        print("  1. GitHub CLI (recommended): gh auth login")
        print("  2. Environment variable: export GITHUB_TOKEN=<token>")
        print("  3. Command line: --token <token>")
        sys.exit(1)

    print(f"✅ Authenticated via: {auth_method}")

    # Get repo name
    repo_name = args.repo or os.environ.get('GITHUB_REPOSITORY')
    if not repo_name:
        # Try to get from git remote
        try:
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                url = result.stdout.strip()
                # Parse GitHub URL
                if 'github.com' in url:
                    parts = url.split('github.com')[-1].strip('/:').replace('.git', '')
                    repo_name = parts
        except:
            pass

    if not repo_name:
        print("❌ Repository name required. Set GITHUB_REPOSITORY env var or use --repo")
        sys.exit(1)

    print(f"📦 Repository: {repo_name}")
    print(f"🔍 PR Number: #{args.pr}\n")

    # Create monitor
    monitor = LocalCIMonitor(token, repo_name, args.pr)

    # Get status
    status = monitor.get_ci_status()
    monitor.display_status(status)

    # Create issues if requested
    if args.create_issues:
        monitor.create_issues_from_failures(status)

    # Watch if requested
    if args.watch:
        monitor.watch_ci(args.interval)


if __name__ == '__main__':
    main()
