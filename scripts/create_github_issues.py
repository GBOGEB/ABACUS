#!/usr/bin/env python3
"""
Generate GitHub Issues for Failed Workflow Checks
Based on PR #9 failures
"""

import json
from pathlib import Path

# Define issues based on the screenshots
ISSUES = [
    {
        "title": "Fix Static Analysis - flake8 AttributeError",
        "body": """## 🔴 Issue Description

The **Static Analysis** workflow is failing with an AttributeError in flake8.

## 📊 Workflow Details

- **Workflow:** Static Analysis
- **Job:** Run flake8
- **Duration:** 10m 1s
- **Status:** ❌ Failed

## 🐛 Error Details

```
File "/opt/hostedtoolcache/Python/3.12.12/x64/lib/python3.12/site-packages/flake8/plugins/manager.py", line 363, in __init__
    self.manager = PluginManager(
File "/opt/hostedtoolcache/Python/3.12.12/x64/lib/python3.12/site-packages/flake8/plugins/manager.py", line 243, in __init__
    self._load_entrypoint_plugins()
File "/opt/hostedtoolcache/Python/3.12.12/x64/lib/python3.12/site-packages/flake8/plugins/manager.py", line 261, in _load_entrypoint_plugins
    eps = importlib_metadata.entry_points().get(self.namespace, ())
AttributeError: 'EntryPoints' object has no attribute 'get'
```

## 🔍 Root Cause

This is a known compatibility issue between:
- **flake8** and newer versions of **importlib-metadata**
- Python 3.12 changed the EntryPoints API

## 🔧 Proposed Fix

### Option 1: Pin importlib-metadata version
```python
# In requirements.txt or pyproject.toml
importlib-metadata<5.0
```

### Option 2: Update flake8
```python
# Use latest flake8 that supports Python 3.12
flake8>=7.0.0
```

### Option 3: Use ruff instead
```python
# Ruff is faster and more modern
ruff>=0.1.0
```

## 📋 Action Items

- [ ] Update `requirements.txt` with compatible versions
- [ ] Test locally with Python 3.12
- [ ] Update workflow if needed
- [ ] Re-run checks

## 🔗 References

- Workflow run: https://github.com/GBOGEB/ABACUS/actions
- Related issue: https://github.com/PyCQA/flake8/issues/1800

## 🏷️ Labels

`ci/cd`, `bug`, `code-quality`, `P1`
""",
        "labels": ["ci/cd", "bug", "code-quality", "P1"]
    },
    {
        "title": "Fix Bridge Smoke Tests - Missing 'dmaic' module",
        "body": """## 🔴 Issue Description

The **Bridge Smoke Tests** workflow is failing with import errors.

## 📊 Workflow Details

- **Workflow:** Bridge Smoke Tests
- **Job:** Run bridge integration tests (smoke)
- **Duration:** 10m 3s
- **Status:** ❌ Failed

## 🐛 Error Details

```
ImportError while importing test module '/home/runner/work/ABACUS/ABACUS/DMAIC_V3/tests/test_bridge_integration.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/opt/hostedtoolcache/Python/3.12.12/x64/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
DMAIC_V3/tests/test_bridge_integration.py:7: in <module>
    from DMAIC_V3.core.test_system_bridge import TestSystemBridge, MCPControlPoint
DMAIC_V3/core/test_system_bridge.py:15: in <module>
    from .handover_bridge import HandoverBridge
DMAIC_V3/core/handover_bridge.py:12: in <module>
    from dmaic import Idempotency, provenance, metrics as handover_metrics, recursion
E   ModuleNotFoundError: No module named 'dmaic'
```

## 🔍 Root Cause

The test is trying to import `dmaic` module which is not installed or not in the Python path.

## 🔧 Proposed Fix

### Option 1: Add missing dependency
```python
# In requirements.txt
dmaic>=1.0.0  # Or appropriate version
```

### Option 2: Fix import path
```python
# In DMAIC_V3/core/handover_bridge.py
# Change:
from dmaic import Idempotency, provenance, metrics as handover_metrics, recursion

# To:
from DMAIC_V3.dmaic import Idempotency, provenance, metrics as handover_metrics, recursion
```

### Option 3: Install package in editable mode
```yaml
# In workflow file
- name: Install dependencies
  run: |
    pip install -e .  # Install package in editable mode
    pip install -r DMAIC_V3/requirements.txt
```

## 📋 Action Items

- [ ] Identify where `dmaic` module should come from
- [ ] Add to requirements.txt OR fix import paths
- [ ] Update `setup.py` if needed
- [ ] Test imports locally
- [ ] Re-run smoke tests

## 🔗 References

- Workflow run: https://github.com/GBOGEB/ABACUS/actions
- Test file: `DMAIC_V3/tests/test_bridge_integration.py`

## 🏷️ Labels

`ci/cd`, `bug`, `tests`, `P0`
""",
        "labels": ["ci/cd", "bug", "tests", "P0"]
    },
    {
        "title": "Fix Bridge Unit Tests - Import and dependency issues",
        "body": """## 🔴 Issue Description

The **Bridge Unit Tests** workflow needs investigation for potential failures.

## 📊 Workflow Details

- **Workflow:** Bridge Unit Tests
- **Status:** ⚠️ Needs investigation

## 🔍 Investigation Needed

Based on the Bridge Smoke Tests failure, this workflow likely has similar import issues.

## 🔧 Proposed Fix

1. Apply fixes from Bridge Smoke Tests issue
2. Ensure all dependencies are installed
3. Fix import paths if needed

## 📋 Action Items

- [ ] Check workflow logs for specific errors
- [ ] Apply fixes from related issues
- [ ] Test locally
- [ ] Re-run checks

## 🔗 References

- Related: Bridge Smoke Tests issue
- Workflow run: https://github.com/GBOGEB/ABACUS/actions

## 🏷️ Labels

`ci/cd`, `tests`, `P1`
""",
        "labels": ["ci/cd", "tests", "P1"]
    },
    {
        "title": "Fix Bridge Integration Tests - Import errors",
        "body": """## 🔴 Issue Description

The **Bridge Integration Tests** workflow likely has import errors similar to smoke tests.

## 📊 Workflow Details

- **Workflow:** Bridge Integration Tests
- **Status:** ⚠️ Needs investigation

## 🔍 Investigation Needed

Check for:
- Missing `dmaic` module imports
- Python path issues
- Dependency installation problems

## 🔧 Proposed Fix

Apply fixes from Bridge Smoke Tests issue.

## 📋 Action Items

- [ ] Check workflow logs
- [ ] Apply dependency fixes
- [ ] Test locally
- [ ] Re-run checks

## 🔗 References

- Related: Bridge Smoke Tests issue
- Workflow run: https://github.com/GBOGEB/ABACUS/actions

## 🏷️ Labels

`ci/cd`, `tests`, `P1`
""",
        "labels": ["ci/cd", "tests", "P1"]
    },
    {
        "title": "Fix Full Deployment Test - Dependency and integration issues",
        "body": """## 🔴 Issue Description

The **Full Deployment Test** workflow needs investigation.

## 📊 Workflow Details

- **Workflow:** Full Deployment Test
- **Status:** ⚠️ Needs investigation

## 🔍 Investigation Needed

This is a comprehensive test that may fail due to:
- Missing dependencies
- Import errors
- Configuration issues
- Integration problems

## 🔧 Proposed Fix

1. Apply fixes from other test issues
2. Ensure all dependencies installed
3. Check deployment configuration
4. Verify integration points

## 📋 Action Items

- [ ] Check workflow logs for specific errors
- [ ] Apply fixes from related issues
- [ ] Test deployment locally if possible
- [ ] Re-run checks

## 🔗 References

- Workflow run: https://github.com/GBOGEB/ABACUS/actions

## 🏷️ Labels

`ci/cd`, `tests`, `deployment`, `P2`
""",
        "labels": ["ci/cd", "tests", "deployment", "P2"]
    }
]

def generate_issue_files():
    """Generate markdown files for each issue"""
    output_dir = Path("github_issues")
    output_dir.mkdir(exist_ok=True)
    
    print("📝 Generating GitHub Issue Files...\n")
    
    for i, issue in enumerate(ISSUES, 1):
        filename = output_dir / f"issue_{i:02d}_{issue['title'].lower().replace(' ', '_').replace('-', '_')[:50]}.md"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# {issue['title']}\n\n")
            f.write(issue['body'])
            f.write(f"\n\n## Labels\n\n")
            f.write(", ".join(f"`{label}`" for label in issue['labels']))
        
        print(f"✅ Created: {filename}")
    
    print(f"\n📊 Total issues created: {len(ISSUES)}")
    print(f"📁 Location: {output_dir}/")
    
    # Generate summary
    summary_file = output_dir / "README.md"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("# GitHub Issues for Failed Workflow Checks\n\n")
        f.write("## Summary\n\n")
        f.write(f"Total issues: {len(ISSUES)}\n\n")
        f.write("## Issues\n\n")
        
        for i, issue in enumerate(ISSUES, 1):
            priority = [l for l in issue['labels'] if l.startswith('P')]
            priority_str = priority[0] if priority else "P2"
            f.write(f"{i}. **{issue['title']}** - Priority: {priority_str}\n")
        
        f.write("\n## How to Create Issues on GitHub\n\n")
        f.write("### Option 1: Manual Creation\n\n")
        f.write("1. Go to: https://github.com/GBOGEB/ABACUS/issues/new\n")
        f.write("2. Copy title from issue file\n")
        f.write("3. Copy body from issue file\n")
        f.write("4. Add labels\n")
        f.write("5. Click 'Submit new issue'\n\n")
        
        f.write("### Option 2: GitHub CLI (if installed)\n\n")
        f.write("```bash\n")
        for i, issue in enumerate(ISSUES, 1):
            labels_str = ",".join(issue['labels'])
            f.write(f"# Issue {i}\n")
            f.write(f"gh issue create --repo GBOGEB/ABACUS \\\n")
            f.write(f"  --title \"{issue['title']}\" \\\n")
            f.write(f"  --label \"{labels_str}\" \\\n")
            f.write(f"  --body-file github_issues/issue_{i:02d}_*.md\n\n")
        f.write("```\n\n")
        
        f.write("### Option 3: Bulk Import\n\n")
        f.write("Use the GitHub API or a tool like `gh` to bulk import all issues.\n")
    
    print(f"✅ Created summary: {summary_file}")
    
    # Generate quick reference
    quick_ref = output_dir / "QUICK_REFERENCE.md"
    with open(quick_ref, 'w', encoding='utf-8') as f:
        f.write("# Quick Reference - Failed Checks\n\n")
        f.write("## Priority Order\n\n")
        
        # Sort by priority
        p0_issues = [i for i in ISSUES if 'P0' in i['labels']]
        p1_issues = [i for i in ISSUES if 'P1' in i['labels']]
        p2_issues = [i for i in ISSUES if 'P2' in i['labels']]
        
        if p0_issues:
            f.write("### 🔴 P0 - Critical (Fix First)\n\n")
            for issue in p0_issues:
                f.write(f"- **{issue['title']}**\n")
        
        if p1_issues:
            f.write("\n### 🟡 P1 - Important (Fix Soon)\n\n")
            for issue in p1_issues:
                f.write(f"- **{issue['title']}**\n")
        
        if p2_issues:
            f.write("\n### 🟢 P2 - Nice to Have (Fix Later)\n\n")
            for issue in p2_issues:
                f.write(f"- **{issue['title']}**\n")
        
        f.write("\n## Common Root Causes\n\n")
        f.write("1. **Missing `dmaic` module** - Most test failures\n")
        f.write("2. **flake8 compatibility** - Static analysis failure\n")
        f.write("3. **Import path issues** - Module not found errors\n\n")
        
        f.write("## Quick Fixes\n\n")
        f.write("### Fix 1: Add dmaic to requirements\n")
        f.write("```python\n")
        f.write("# In requirements.txt\n")
        f.write("dmaic>=1.0.0\n")
        f.write("```\n\n")
        
        f.write("### Fix 2: Update flake8 compatibility\n")
        f.write("```python\n")
        f.write("# In requirements.txt\n")
        f.write("importlib-metadata<5.0\n")
        f.write("# OR\n")
        f.write("flake8>=7.0.0\n")
        f.write("```\n\n")
        
        f.write("### Fix 3: Install package in editable mode\n")
        f.write("```yaml\n")
        f.write("# In workflow files\n")
        f.write("- name: Install dependencies\n")
        f.write("  run: |\n")
        f.write("    pip install -e .\n")
        f.write("    pip install -r DMAIC_V3/requirements.txt\n")
        f.write("```\n")
    
    print(f"✅ Created quick reference: {quick_ref}")
    print("\n🎉 Done! Check the 'github_issues/' directory for all files.")

if __name__ == '__main__':
    generate_issue_files()
