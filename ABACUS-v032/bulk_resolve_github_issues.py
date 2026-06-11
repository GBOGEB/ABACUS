#!/usr/bin/env python3
"""
ABACUS - Bulk GitHub Issues/PRs Resolution Script
==================================================
Detects and resolves duplicate issues and PRs created by CI/CD automation.

Usage:
    python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action [check|close|comment]
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import List, Dict, Set
from collections import defaultdict

try:
    from github import Github, GithubException
except ImportError:
    print("ERROR: PyGithub not installed. Install with: pip install PyGithub")
    sys.exit(1)


class GitHubBulkResolver:
    """Bulk resolver for duplicate GitHub issues and PRs."""
    
    def __init__(self, repo_name: str, token: str = None):
        """Initialize GitHub connection."""
        self.repo_name = repo_name
        self.token = token or os.environ.get('GITHUB_TOKEN')
        
        if not self.token:
            print("ERROR: GitHub token not found. Set GITHUB_TOKEN environment variable.")
            sys.exit(1)
        
        try:
            self.github = Github(self.token)
            self.repo = self.github.get_repo(repo_name)
            print(f"✅ Connected to repository: {repo_name}")
        except GithubException as e:
            print(f"ERROR: Failed to connect to repository: {e}")
            sys.exit(1)
    
    def find_duplicate_issues(self) -> Dict[str, List]:
        """Find duplicate issues based on title patterns."""
        print("\n🔍 Scanning for duplicate issues...")
        
        issues = self.repo.get_issues(state='open')
        issue_groups = defaultdict(list)
        
        for issue in issues:
            # Skip pull requests
            if issue.pull_request:
                continue
            
            # Extract test name from title
            title = issue.title
            if 'CI Failure:' in title or 'CI/CD test failure' in title:
                # Normalize title to group duplicates
                test_name = self._extract_test_name(title)
                issue_groups[test_name].append({
                    'number': issue.number,
                    'title': issue.title,
                    'created_at': issue.created_at,
                    'labels': [label.name for label in issue.labels],
                    'url': issue.html_url,
                    'issue_obj': issue
                })
        
        # Filter to only groups with duplicates
        duplicates = {k: v for k, v in issue_groups.items() if len(v) > 1}
        
        print(f"✅ Found {len(duplicates)} groups with duplicate issues")
        print(f"   Total duplicate issues: {sum(len(v) - 1 for v in duplicates.values())}")
        
        return duplicates
    
    def find_duplicate_prs(self) -> Dict[str, List]:
        """Find duplicate pull requests based on title patterns."""
        print("\n🔍 Scanning for duplicate pull requests...")
        
        pulls = self.repo.get_pulls(state='open')
        pr_groups = defaultdict(list)
        
        for pr in pulls:
            title = pr.title
            if '[WIP]' in title and 'Fix CI' in title:
                # Normalize title to group duplicates
                test_name = self._extract_test_name(title)
                pr_groups[test_name].append({
                    'number': pr.number,
                    'title': pr.title,
                    'created_at': pr.created_at,
                    'labels': [label.name for label in pr.labels],
                    'url': pr.html_url,
                    'pr_obj': pr,
                    'draft': pr.draft
                })
        
        # Filter to only groups with duplicates
        duplicates = {k: v for k, v in pr_groups.items() if len(v) > 1}
        
        print(f"✅ Found {len(duplicates)} groups with duplicate PRs")
        print(f"   Total duplicate PRs: {sum(len(v) - 1 for v in duplicates.values())}")
        
        return duplicates
    
    def _extract_test_name(self, title: str) -> str:
        """Extract normalized test name from title."""
        # Remove common prefixes
        title = title.replace('[WIP] Fix CI', '').replace('CI Failure:', '').replace('CI/CD test failure', '')
        title = title.replace('failure for', '').replace('failure in', '').replace('test failure', '')
        
        # Extract test name
        parts = title.split()
        test_parts = [p for p in parts if p.startswith('test_') or '_' in p]
        
        if test_parts:
            return test_parts[0].strip()
        
        # Fallback to cleaned title
        return title.strip().lower()
    
    def check_duplicates(self, dry_run: bool = True):
        """Check and report duplicate issues and PRs."""
        print("\n" + "="*70)
        print("DUPLICATE DETECTION REPORT")
        print("="*70)
        
        # Find duplicates
        duplicate_issues = self.find_duplicate_issues()
        duplicate_prs = self.find_duplicate_prs()
        
        # Report issues
        if duplicate_issues:
            print("\n📋 DUPLICATE ISSUES:")
            print("-" * 70)
            for test_name, issues in duplicate_issues.items():
                print(f"\n🔴 Test: {test_name}")
                print(f"   Duplicates: {len(issues)} issues")
                
                # Sort by creation date (oldest first)
                issues.sort(key=lambda x: x['created_at'])
                
                for i, issue in enumerate(issues):
                    status = "KEEP (oldest)" if i == 0 else "CLOSE (duplicate)"
                    print(f"   [{status}] #{issue['number']}: {issue['title']}")
                    print(f"      Created: {issue['created_at']}")
                    print(f"      URL: {issue['url']}")
        
        # Report PRs
        if duplicate_prs:
            print("\n📋 DUPLICATE PULL REQUESTS:")
            print("-" * 70)
            for test_name, prs in duplicate_prs.items():
                print(f"\n🔴 Test: {test_name}")
                print(f"   Duplicates: {len(prs)} PRs")
                
                # Sort by creation date (oldest first)
                prs.sort(key=lambda x: x['created_at'])
                
                for i, pr in enumerate(prs):
                    status = "KEEP (oldest)" if i == 0 else "CLOSE (duplicate)"
                    draft_status = "[DRAFT]" if pr['draft'] else ""
                    print(f"   [{status}] #{pr['number']}: {pr['title']} {draft_status}")
                    print(f"      Created: {pr['created_at']}")
                    print(f"      URL: {pr['url']}")
        
        # Summary
        total_duplicate_issues = sum(len(v) - 1 for v in duplicate_issues.values())
        total_duplicate_prs = sum(len(v) - 1 for v in duplicate_prs.values())
        
        print("\n" + "="*70)
        print("SUMMARY:")
        print(f"  Issues to close: {total_duplicate_issues}")
        print(f"  PRs to close: {total_duplicate_prs}")
        print(f"  Total to close: {total_duplicate_issues + total_duplicate_prs}")
        print("="*70)
        
        return duplicate_issues, duplicate_prs
    
    def close_duplicates(self, duplicate_issues: Dict, duplicate_prs: Dict, 
                        comment: str = None, dry_run: bool = True):
        """Close duplicate issues and PRs."""
        if dry_run:
            print("\n⚠️  DRY RUN MODE - No changes will be made")
            return
        
        print("\n🔧 Closing duplicate issues and PRs...")
        
        closed_count = 0
        
        # Close duplicate issues (keep oldest)
        for test_name, issues in duplicate_issues.items():
            issues.sort(key=lambda x: x['created_at'])
            
            for i, issue_data in enumerate(issues):
                if i == 0:
                    # Keep the oldest issue
                    continue
                
                issue = issue_data['issue_obj']
                
                # Add comment
                close_comment = comment or f"""
This issue is a duplicate of #{issues[0]['number']} and is being automatically closed.

**Reason**: Multiple issues were created for the same test failure.
**Action**: Keeping the oldest issue (#{issues[0]['number']}) and closing duplicates.

If this test failure is still occurring, please comment on #{issues[0]['number']}.
"""
                
                try:
                    issue.create_comment(close_comment)
                    issue.edit(state='closed')
                    print(f"✅ Closed issue #{issue.number}: {issue.title}")
                    closed_count += 1
                except GithubException as e:
                    print(f"❌ Failed to close issue #{issue.number}: {e}")
        
        # Close duplicate PRs (keep oldest)
        for test_name, prs in duplicate_prs.items():
            prs.sort(key=lambda x: x['created_at'])
            
            for i, pr_data in enumerate(prs):
                if i == 0:
                    # Keep the oldest PR
                    continue
                
                pr = pr_data['pr_obj']
                
                # Add comment
                close_comment = comment or f"""
This PR is a duplicate of #{prs[0]['number']} and is being automatically closed.

**Reason**: Multiple PRs were created for the same test failure.
**Action**: Keeping the oldest PR (#{prs[0]['number']}) and closing duplicates.

If you want to continue working on this fix, please use PR #{prs[0]['number']}.
"""
                
                try:
                    pr.create_issue_comment(close_comment)
                    pr.edit(state='closed')
                    print(f"✅ Closed PR #{pr.number}: {pr.title}")
                    closed_count += 1
                except GithubException as e:
                    print(f"❌ Failed to close PR #{pr.number}: {e}")
        
        print(f"\n✅ Successfully closed {closed_count} duplicates")
    
    def add_comment_to_all(self, duplicate_issues: Dict, duplicate_prs: Dict, 
                          comment: str, dry_run: bool = True):
        """Add a comment to all duplicate issues and PRs."""
        if dry_run:
            print("\n⚠️  DRY RUN MODE - No changes will be made")
            return
        
        print("\n💬 Adding comments to all duplicates...")
        
        comment_count = 0
        
        # Comment on issues
        for test_name, issues in duplicate_issues.items():
            for issue_data in issues:
                issue = issue_data['issue_obj']
                
                try:
                    issue.create_comment(comment)
                    print(f"✅ Commented on issue #{issue.number}")
                    comment_count += 1
                except GithubException as e:
                    print(f"❌ Failed to comment on issue #{issue.number}: {e}")
        
        # Comment on PRs
        for test_name, prs in duplicate_prs.items():
            for pr_data in prs:
                pr = pr_data['pr_obj']
                
                try:
                    pr.create_issue_comment(comment)
                    print(f"✅ Commented on PR #{pr.number}")
                    comment_count += 1
                except GithubException as e:
                    print(f"❌ Failed to comment on PR #{pr.number}: {e}")
        
        print(f"\n✅ Successfully added {comment_count} comments")
    
    def export_report(self, duplicate_issues: Dict, duplicate_prs: Dict, 
                     output_file: str = "duplicate_report.json"):
        """Export duplicate report to JSON."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'repository': self.repo_name,
            'summary': {
                'duplicate_issue_groups': len(duplicate_issues),
                'duplicate_pr_groups': len(duplicate_prs),
                'total_duplicate_issues': sum(len(v) - 1 for v in duplicate_issues.values()),
                'total_duplicate_prs': sum(len(v) - 1 for v in duplicate_prs.values())
            },
            'duplicate_issues': {},
            'duplicate_prs': {}
        }
        
        # Add issue details
        for test_name, issues in duplicate_issues.items():
            report['duplicate_issues'][test_name] = [
                {
                    'number': issue['number'],
                    'title': issue['title'],
                    'created_at': issue['created_at'].isoformat(),
                    'url': issue['url'],
                    'labels': issue['labels']
                }
                for issue in issues
            ]
        
        # Add PR details
        for test_name, prs in duplicate_prs.items():
            report['duplicate_prs'][test_name] = [
                {
                    'number': pr['number'],
                    'title': pr['title'],
                    'created_at': pr['created_at'].isoformat(),
                    'url': pr['url'],
                    'labels': pr['labels'],
                    'draft': pr['draft']
                }
                for pr in prs
            ]
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n✅ Report exported to: {output_file}")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Bulk resolve duplicate GitHub issues and PRs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check for duplicates (dry run)
  python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action check
  
  # Close duplicates (dry run)
  python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action close --dry-run
  
  # Close duplicates (actual execution)
  python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action close
  
  # Add comment to all duplicates
  python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action comment --message "Investigating..."
  
  # Export report
  python bulk_resolve_github_issues.py --repo GBOGEB/ABACUS --action export
        """
    )
    
    parser.add_argument('--repo', required=True, help='Repository name (e.g., GBOGEB/ABACUS)')
    parser.add_argument('--action', required=True, 
                       choices=['check', 'close', 'comment', 'export'],
                       help='Action to perform')
    parser.add_argument('--token', help='GitHub token (or set GITHUB_TOKEN env var)')
    parser.add_argument('--message', help='Comment message (for comment action)')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Dry run mode (no changes made)')
    parser.add_argument('--output', default='duplicate_report.json',
                       help='Output file for export action')
    
    args = parser.parse_args()
    
    # Initialize resolver
    resolver = GitHubBulkResolver(args.repo, args.token)
    
    # Execute action
    if args.action == 'check':
        duplicate_issues, duplicate_prs = resolver.check_duplicates()
    
    elif args.action == 'close':
        duplicate_issues, duplicate_prs = resolver.check_duplicates()
        
        if not args.dry_run:
            confirm = input("\n⚠️  Are you sure you want to close these duplicates? (yes/no): ")
            if confirm.lower() != 'yes':
                print("❌ Operation cancelled")
                return
        
        resolver.close_duplicates(duplicate_issues, duplicate_prs, dry_run=args.dry_run)
    
    elif args.action == 'comment':
        if not args.message:
            print("ERROR: --message required for comment action")
            sys.exit(1)
        
        duplicate_issues, duplicate_prs = resolver.check_duplicates()
        
        if not args.dry_run:
            confirm = input(f"\n⚠️  Add comment to {sum(len(v) for v in duplicate_issues.values()) + sum(len(v) for v in duplicate_prs.values())} items? (yes/no): ")
            if confirm.lower() != 'yes':
                print("❌ Operation cancelled")
                return
        
        resolver.add_comment_to_all(duplicate_issues, duplicate_prs, 
                                   args.message, dry_run=args.dry_run)
    
    elif args.action == 'export':
        duplicate_issues, duplicate_prs = resolver.check_duplicates()
        resolver.export_report(duplicate_issues, duplicate_prs, args.output)
    
    print("\n✅ Operation completed successfully")


if __name__ == '__main__':
    main()
