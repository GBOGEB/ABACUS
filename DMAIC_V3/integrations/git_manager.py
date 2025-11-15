"""
DMAIC V3.3 - Git Manager
=============================================================================
Priority: M3-006 (HIGH) from CHATREADY_HANDOVER.yaml Iteration 6
=============================================================================
Automated git operations for DMAIC iterations:
- Create baselines/tags for each iteration
- Track changes by iteration
- Generate diff reports
- Manage branches
- Integration with version manager
=============================================================================
"""

import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class GitManager:
    """
    Manages git operations for DMAIC iterations
    
    Features:
    - Automatic commits after each phase
    - Iteration tagging and baselining
    - Change tracking and diff reports
    - Branch management for experiments
    - Historic git log analysis
    """
    
    def __init__(self, workspace_root: Path = Path(".")):
        self.workspace_root = workspace_root
        self.git_available = self._check_git_available()
        
    def _check_git_available(self) -> bool:
        """Check if git is available"""
        try:
            result = subprocess.run(['git', '--version'], 
                                   capture_output=True, 
                                   text=True,
                                   timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _run_git(self, args: List[str], check: bool = True) -> Tuple[bool, str]:
        """
        Run git command
        
        Args:
            args: Git command arguments (without 'git' prefix)
            check: Raise exception on failure
            
        Returns:
            Tuple of (success, output)
        """
        if not self.git_available:
            return False, "Git not available"
        
        try:
            result = subprocess.run(
                ['git'] + args,
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=30,
                check=check
            )
            return True, result.stdout + result.stderr
        except subprocess.CalledProcessError as e:
            return False, e.stderr
        except Exception as e:
            return False, str(e)
    
    def commit_iteration(self, 
                        iteration: int, 
                        phase: Optional[str] = None,
                        message: Optional[str] = None) -> bool:
        """
        Commit iteration results
        
        Args:
            iteration: Iteration number
            phase: Optional phase name
            message: Optional custom message
            
        Returns:
            Success status
        """
        if not self.git_available:
            print("[GIT] Git not available, skipping commit")
            return False
        
        # Stage files
        files_to_add = [
            "DMAIC_V3_OUTPUT/",
            "planning_matrix.json",
            "planning_history.json",
            "maturity_assessment.json",
            "convergence_report.json",
            "GLOBAL_ARTIFACT_RANKING_SUMMARY.yaml"
        ]
        
        for file_path in files_to_add:
            full_path = self.workspace_root / file_path
            if full_path.exists():
                self._run_git(['add', file_path], check=False)
        
        # Generate commit message
        if message is None:
            if phase:
                message = f"DMAIC V3.3 - Iteration {iteration} - {phase} complete"
            else:
                message = f"DMAIC V3.3 - Iteration {iteration} complete"
        
        message += f"\n\nTimestamp: {datetime.now().isoformat()}"
        
        # Commit
        success, output = self._run_git(['commit', '-m', message], check=False)
        
        if success and "nothing to commit" not in output:
            print(f"[GIT] Committed: {message.split(chr(10))[0]}")
            return True
        elif "nothing to commit" in output:
            print("[GIT] No changes to commit")
            return True
        else:
            print(f"[GIT] Commit failed: {output}")
            return False
    
    def create_baseline_tag(self, iteration: int, version: str = None) -> bool:
        """
        Create a git tag for iteration baseline
        
        Args:
            iteration: Iteration number
            version: Optional version string (e.g., "v3.3.0")
            
        Returns:
            Success status
        """
        if not self.git_available:
            return False
        
        if version:
            tag_name = f"{version}-iteration{iteration}"
        else:
            tag_name = f"iteration{iteration}-baseline"
        
        tag_message = f"DMAIC V3.3 Iteration {iteration} Baseline\nCreated: {datetime.now().isoformat()}"
        
        success, output = self._run_git(['tag', '-a', tag_name, '-m', tag_message], check=False)
        
        if success:
            print(f"[GIT] Created tag: {tag_name}")
            return True
        else:
            print(f"[GIT] Tag creation failed: {output}")
            return False
    
    def generate_diff_report(self, 
                            iteration_from: int, 
                            iteration_to: int) -> Dict:
        """
        Generate diff report between iterations
        
        Args:
            iteration_from: Starting iteration
            iteration_to: Ending iteration
            
        Returns:
            Dict with diff statistics
        """
        if not self.git_available:
            return {'error': 'Git not available'}
        
        tag_from = f"iteration{iteration_from}-baseline"
        tag_to = f"iteration{iteration_to}-baseline"
        
        # Get diff stats
        success, output = self._run_git(['diff', '--stat', tag_from, tag_to], check=False)
        
        if not success:
            return {'error': f'Diff failed: {output}'}
        
        # Parse diff stats
        lines = output.strip().split('\n')
        files_changed = []
        
        for line in lines[:-1]:  # Exclude summary line
            parts = line.split('|')
            if len(parts) == 2:
                file_path = parts[0].strip()
                changes = parts[1].strip()
                files_changed.append({
                    'file': file_path,
                    'changes': changes
                })
        
        # Parse summary line
        summary_line = lines[-1] if lines else ""
        
        return {
            'from_iteration': iteration_from,
            'to_iteration': iteration_to,
            'files_changed': files_changed,
            'summary': summary_line,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_changes_since_iteration(self, iteration: int) -> List[str]:
        """
        Get list of changed files since iteration
        
        Args:
            iteration: Iteration number
            
        Returns:
            List of changed file paths
        """
        if not self.git_available:
            return []
        
        tag_name = f"iteration{iteration}-baseline"
        
        success, output = self._run_git(['diff', '--name-only', tag_name], check=False)
        
        if success:
            return [line.strip() for line in output.split('\n') if line.strip()]
        else:
            return []
    
    def get_iteration_log(self, iteration: int) -> Dict:
        """
        Get git log for specific iteration
        
        Args:
            iteration: Iteration number
            
        Returns:
            Dict with log information
        """
        if not self.git_available:
            return {'error': 'Git not available'}
        
        # Get commits with "Iteration X" in message
        success, output = self._run_git([
            'log', 
            '--grep', f'Iteration {iteration}',
            '--pretty=format:%H|%an|%at|%s',
            '--no-merges'
        ], check=False)
        
        if not success:
            return {'error': f'Log failed: {output}'}
        
        commits = []
        for line in output.strip().split('\n'):
            if not line:
                continue
            
            parts = line.split('|')
            if len(parts) >= 4:
                commits.append({
                    'commit_hash': parts[0],
                    'author': parts[1],
                    'timestamp': parts[2],
                    'message': '|'.join(parts[3:])
                })
        
        return {
            'iteration': iteration,
            'commits': commits,
            'commit_count': len(commits)
        }
    
    def save_git_history(self, output_file: Path):
        """
        Save complete git history to JSON
        
        Args:
            output_file: Output file path
        """
        if not self.git_available:
            return
        
        success, output = self._run_git([
            'log',
            '--pretty=format:%H|%an|%at|%s',
            '--no-merges',
            '-100'  # Last 100 commits
        ], check=False)
        
        if not success:
            return
        
        commits = []
        for line in output.strip().split('\n'):
            if not line:
                continue
            
            parts = line.split('|')
            if len(parts) >= 4:
                commits.append({
                    'commit_hash': parts[0],
                    'author': parts[1],
                    'timestamp': parts[2],
                    'message': '|'.join(parts[3:])
                })
        
        history = {
            'generated': datetime.now().isoformat(),
            'commits': commits,
            'total_commits': len(commits)
        }
        
        with open(output_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        print(f"[GIT] Saved history: {output_file}")


def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='DMAIC V3.3 Git Manager')
    parser.add_argument('--commit', type=int, metavar='ITERATION',
                       help='Commit iteration results')
    parser.add_argument('--tag', type=int, metavar='ITERATION',
                       help='Create baseline tag')
    parser.add_argument('--diff', nargs=2, type=int, metavar=('FROM', 'TO'),
                       help='Generate diff report between iterations')
    parser.add_argument('--changes', type=int, metavar='ITERATION',
                       help='Show changes since iteration')
    parser.add_argument('--log', type=int, metavar='ITERATION',
                       help='Show log for iteration')
    parser.add_argument('--history', type=str, metavar='FILE',
                       help='Save git history to file')
    
    args = parser.parse_args()
    
    manager = GitManager()
    
    if args.commit:
        manager.commit_iteration(args.commit)
    
    if args.tag:
        manager.create_baseline_tag(args.tag)
    
    if args.diff:
        report = manager.generate_diff_report(args.diff[0], args.diff[1])
        print(json.dumps(report, indent=2))
    
    if args.changes:
        changes = manager.get_changes_since_iteration(args.changes)
        print('\n'.join(changes))
    
    if args.log:
        log = manager.get_iteration_log(args.log)
        print(json.dumps(log, indent=2))
    
    if args.history:
        manager.save_git_history(Path(args.history))


if __name__ == "__main__":
    main()
