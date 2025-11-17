#!/usr/bin/env python3
"""
Automated Issue Creator for CI/CD Test Failures

This script:
1. Parses test results from pytest JSON report
2. Creates GitHub issues for each failing test
3. Links issues to the PR
4. Assigns labels and priorities
5. Avoids duplicate issues
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

try:
    from github import Github, GithubException
except ImportError:
    print("Installing PyGithub...")
    os.system("pip install PyGithub")
    from github import Github, GithubException


class CIIssueCreator:
    """Creates GitHub issues from CI/CD test failures"""
    
    def __init__(self, token: str, repo_name: str, pr_number: Optional[int] = None):
        self.github = Github(token)
        self.repo = self.github.get_repo(repo_name)
        self.pr_number = pr_number
        self.created_issues = []
        
    def parse_test_report(self, report_path: str = "test_report.json") -> Dict:
        """Parse pytest JSON report"""
        if not Path(report_path).exists():
            print(f"⚠️  Test report not found: {report_path}")
            return {"tests": [], "summary": {}}
        
        with open(report_path, 'r') as f:
            return json.load(f)
    
    def get_existing_issues(self, test_name: str) -> List:
        """Check if issue already exists for this test"""
        query = f'repo:{self.repo.full_name} is:issue is:open label:ci-failure "{test_name}"'
        return list(self.github.search_issues(query))
    
    def create_issue_for_test(self, test: Dict) -> Optional[str]:
        """Create a GitHub issue for a failing test"""
        test_name = test.get('nodeid', 'Unknown Test')
        test_file = test_name.split('::')[0] if '::' in test_name else 'Unknown'
        test_function = test_name.split('::')[-1] if '::' in test_name else test_name
        
        # Check for existing issues
        existing = self.get_existing_issues(test_name)
        if existing:
            print(f"ℹ️  Issue already exists for {test_name}: #{existing[0].number}")
            return None
        
        # Extract failure information
        failure_message = test.get('call', {}).get('longrepr', 'No error message available')
        duration = test.get('call', {}).get('duration', 0)
        
        # Determine priority based on test type
        priority = self._determine_priority(test_name, failure_message)
        
        # Create issue title
        title = f"🔴 CI Failure: {test_function}"
        
        # Create issue body
        body = self._create_issue_body(
            test_name=test_name,
            test_file=test_file,
            failure_message=failure_message,
            duration=duration,
            pr_number=self.pr_number
        )
        
        # Create labels
        labels = ['ci-failure', 'automated', priority]
        if 'integration' in test_name.lower():
            labels.append('integration-test')
        elif 'unit' in test_name.lower():
            labels.append('unit-test')
        
        try:
            # Create the issue
            issue = self.repo.create_issue(
                title=title,
                body=body,
                labels=labels
            )
            
            print(f"✅ Created issue #{issue.number}: {title}")
            self.created_issues.append(issue.number)
            
            # Link to PR if available
            if self.pr_number:
                self._link_to_pr(issue.number)
            
            return issue.html_url
            
        except GithubException as e:
            print(f"❌ Failed to create issue for {test_name}: {e}")
            return None
    
    def _determine_priority(self, test_name: str, failure_message: str) -> str:
        """Determine issue priority based on test characteristics"""
        # Critical: Integration tests, core functionality
        if any(keyword in test_name.lower() for keyword in ['integration', 'core', 'critical']):
            return 'priority:high'
        
        # High: Import errors, syntax errors
        if any(keyword in failure_message.lower() for keyword in ['importerror', 'syntaxerror', 'modulenotfounderror']):
            return 'priority:high'
        
        # Medium: Most other failures
        return 'priority:medium'
    
    def _create_issue_body(
        self,
        test_name: str,
        test_file: str,
        failure_message: str,
        duration: float,
        pr_number: Optional[int]
    ) -> str:
        """Create detailed issue body"""
        body = f"""## 🔴 CI/CD Test Failure

**Test:** `{test_name}`  
**File:** `{test_file}`  
**Duration:** {duration:.2f}s  
**Detected:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

"""
        
        if pr_number:
            body += f"**Related PR:** #{pr_number}\n\n"
        
        body += f"""### ❌ Failure Details

```
{failure_message[:2000]}
```

### 🔍 Investigation Steps

1. **Reproduce locally:**
   ```bash
   pytest {test_file}::{test_name.split('::')[-1]} -v
   ```

2. **Check recent changes:**
   - Review commits in the related PR
   - Check for dependency updates
   - Verify environment configuration

3. **Debug:**
   ```bash
   pytest {test_file}::{test_name.split('::')[-1]} -v --pdb
   ```

### 🛠️ Fix Checklist

- [ ] Identify root cause
- [ ] Implement fix
- [ ] Add/update tests
- [ ] Verify fix locally
- [ ] Update PR
- [ ] Verify CI passes

### 📋 Context

This issue was automatically created by the CI monitoring system. The test failed during automated checks.

**Workflow:** CI Monitor & Auto Issue Creator  
**Trigger:** Test failure detected in PR #{pr_number if pr_number else 'N/A'}

### 🔗 Related Links

- [CI Workflow Runs](https://github.com/{self.repo.full_name}/actions)
"""
        
        if pr_number:
            body += f"- [Pull Request #{pr_number}](https://github.com/{self.repo.full_name}/pull/{pr_number})\n"
        
        body += """
---

**Note:** This issue will be automatically closed when the test passes in CI.
"""
        
        return body
    
    def _link_to_pr(self, issue_number: int):
        """Add comment linking issue to PR"""
        if not self.pr_number:
            return
        
        try:
            pr = self.repo.get_pull(self.pr_number)
            comment = f"🔗 Linked to issue #{issue_number} - CI test failure detected"
            pr.create_issue_comment(comment)
        except GithubException as e:
            print(f"⚠️  Could not link issue to PR: {e}")
    
    def process_test_results(self, report_path: str = "test_report.json"):
        """Main processing function"""
        print("=" * 60)
        print("🤖 CI/CD Issue Creator - Starting")
        print("=" * 60)
        
        # Parse test report
        report = self.parse_test_report(report_path)
        
        if not report.get('tests'):
            print("ℹ️  No test results found")
            return
        
        # Get summary
        summary = report.get('summary', {})
        total = summary.get('total', 0)
        passed = summary.get('passed', 0)
        failed = summary.get('failed', 0)
        
        print(f"\n📊 Test Summary:")
        print(f"   Total: {total}")
        print(f"   ✅ Passed: {passed}")
        print(f"   ❌ Failed: {failed}")
        print()
        
        if failed == 0:
            print("✅ All tests passing! No issues to create.")
            return
        
        # Process each failing test
        print(f"🔍 Processing {failed} failing test(s)...\n")
        
        for test in report.get('tests', []):
            if test.get('outcome') == 'failed':
                self.create_issue_for_test(test)
        
        # Summary
        print("\n" + "=" * 60)
        print(f"✅ Created {len(self.created_issues)} issue(s)")
        if self.created_issues:
            print(f"   Issue numbers: {', '.join(f'#{n}' for n in self.created_issues)}")
        print("=" * 60)


def main():
    """Main entry point"""
    # Get environment variables
    token = os.environ.get('GITHUB_TOKEN')
    repo_name = os.environ.get('GITHUB_REPOSITORY')
    pr_number = os.environ.get('PR_NUMBER')
    
    if not token:
        print("❌ GITHUB_TOKEN not found in environment")
        sys.exit(1)
    
    if not repo_name:
        print("❌ GITHUB_REPOSITORY not found in environment")
        sys.exit(1)
    
    # Convert PR number to int if available
    pr_number = int(pr_number) if pr_number and pr_number.isdigit() else None
    
    # Create issue creator
    creator = CIIssueCreator(token, repo_name, pr_number)
    
    # Process test results
    creator.process_test_results()


if __name__ == '__main__':
    main()
