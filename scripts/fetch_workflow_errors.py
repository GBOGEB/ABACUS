#!/usr/bin/env python3
"""
Fetch GitHub Actions workflow errors for PR analysis
"""

import json
import subprocess
import sys
from pathlib import Path

def get_workflow_runs():
    """Get recent workflow runs from git log"""
    try:
        # Get the latest commit SHA
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
        commit_sha = result.stdout.strip()
        
        print(f"📊 Analyzing workflows for commit: {commit_sha[:8]}")
        print(f"🔗 View all runs: https://github.com/GBOGEB/ABACUS/actions")
        print(f"🔗 View PR checks: https://github.com/GBOGEB/ABACUS/pull/9/checks")
        print()
        
        return commit_sha
    except subprocess.CalledProcessError as e:
        print(f"❌ Error getting commit SHA: {e}")
        return None

def analyze_workflow_files():
    """Analyze workflow files for common issues"""
    workflow_dir = Path('.github/workflows')
    
    if not workflow_dir.exists():
        print("❌ No .github/workflows directory found")
        return
    
    print("🔍 Analyzing workflow files for common issues...\n")
    
    issues_found = []
    
    for workflow_file in workflow_dir.glob('*.yml'):
        print(f"📄 Checking: {workflow_file.name}")
        
        try:
            with open(workflow_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for common issues
            file_issues = []
            
            # Check 1: Missing required files
            if 'requirements.txt' in content:
                if not Path('requirements.txt').exists():
                    file_issues.append("❌ References requirements.txt but file doesn't exist")
            
            if 'setup.py' in content:
                if not Path('setup.py').exists():
                    file_issues.append("❌ References setup.py but file doesn't exist")
            
            if 'pyproject.toml' in content:
                if not Path('pyproject.toml').exists():
                    file_issues.append("❌ References pyproject.toml but file doesn't exist")
            
            # Check 2: Python version compatibility
            if 'python-version' in content:
                if '3.11' in content or '3.12' in content:
                    file_issues.append("⚠️  Uses Python 3.11/3.12 - may have compatibility issues")
            
            # Check 3: Missing test directories
            if 'pytest' in content or 'test' in content.lower():
                if not Path('tests').exists() and not Path('test').exists():
                    file_issues.append("⚠️  References tests but no tests/ directory found")
            
            # Check 4: Docker without Dockerfile
            if 'docker' in content.lower():
                if not Path('Dockerfile').exists():
                    file_issues.append("❌ References Docker but no Dockerfile found")
            
            # Check 5: Missing pre-commit config
            if 'pre-commit' in content:
                if not Path('.pre-commit-config.yaml').exists():
                    file_issues.append("❌ References pre-commit but no .pre-commit-config.yaml found")
            
            if file_issues:
                issues_found.append((workflow_file.name, file_issues))
                for issue in file_issues:
                    print(f"  {issue}")
            else:
                print(f"  ✅ No obvious issues detected")
            
            print()
            
        except Exception as e:
            print(f"  ❌ Error reading file: {e}\n")
    
    return issues_found

def check_required_files():
    """Check for required files that workflows might need"""
    print("\n📋 Checking for required files...\n")
    
    required_files = {
        'requirements.txt': 'Python dependencies',
        'setup.py': 'Python package setup',
        'pyproject.toml': 'Python project config',
        'pytest.ini': 'Pytest configuration',
        '.pre-commit-config.yaml': 'Pre-commit hooks',
        'Dockerfile': 'Docker configuration',
        'tests/': 'Test directory',
        'docs/': 'Documentation directory',
    }
    
    missing = []
    found = []
    
    for file_path, description in required_files.items():
        path = Path(file_path)
        if path.exists():
            found.append(f"✅ {file_path} - {description}")
        else:
            missing.append(f"❌ {file_path} - {description}")
    
    print("Found:")
    for item in found:
        print(f"  {item}")
    
    if missing:
        print("\nMissing:")
        for item in missing:
            print(f"  {item}")
    
    return missing

def generate_report():
    """Generate a comprehensive error report"""
    print("=" * 80)
    print("🔍 GITHUB ACTIONS FAILURE ANALYSIS")
    print("=" * 80)
    print()
    
    # Get commit info
    commit_sha = get_workflow_runs()
    
    # Analyze workflows
    workflow_issues = analyze_workflow_files()
    
    # Check required files
    missing_files = check_required_files()
    
    # Generate summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    
    if workflow_issues:
        print(f"\n⚠️  Found issues in {len(workflow_issues)} workflow files:")
        for workflow_name, issues in workflow_issues:
            print(f"\n  {workflow_name}:")
            for issue in issues:
                print(f"    {issue}")
    
    if missing_files:
        print(f"\n⚠️  Missing {len(missing_files)} required files")
    
    print("\n🔧 RECOMMENDED ACTIONS:")
    print()
    
    if missing_files:
        print("1. Create missing required files:")
        for missing in missing_files:
            if 'requirements.txt' in missing:
                print("   - Create requirements.txt with project dependencies")
            elif 'setup.py' in missing:
                print("   - Create setup.py for package installation")
            elif 'pyproject.toml' in missing:
                print("   - Create pyproject.toml for modern Python config")
            elif 'pytest.ini' in missing:
                print("   - Create pytest.ini for test configuration")
            elif '.pre-commit-config.yaml' in missing:
                print("   - Create .pre-commit-config.yaml for code quality")
            elif 'Dockerfile' in missing:
                print("   - Create Dockerfile for containerization")
            elif 'tests/' in missing:
                print("   - Create tests/ directory with test files")
    
    print("\n2. View detailed logs on GitHub:")
    print("   https://github.com/GBOGEB/ABACUS/actions")
    print("   https://github.com/GBOGEB/ABACUS/pull/9/checks")
    
    print("\n3. Click 'Details' on each failed check to see specific errors")
    
    print("\n4. Common fixes:")
    print("   - Add missing dependency files")
    print("   - Fix Python version compatibility")
    print("   - Add missing test files")
    print("   - Update workflow configurations")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    try:
        generate_report()
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        sys.exit(1)
