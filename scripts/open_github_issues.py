#!/usr/bin/env python3
"""
Open GitHub Issue Creation Pages with Pre-filled Content
This script generates URLs that open GitHub with pre-filled issue forms
"""

import webbrowser
import urllib.parse
from pathlib import Path
import time

REPO = "GBOGEB/ABACUS"
BASE_URL = f"https://github.com/{REPO}/issues/new"

ISSUES = [
    {
        "priority": "P0",
        "title": "Fix Bridge Smoke Tests - Missing 'dmaic' module",
        "labels": ["ci/cd", "bug", "tests", "P0"],
        "body": """## 🔴 Issue Description

The **Bridge Smoke Tests** workflow is failing with import errors.

## 📊 Workflow Details

- **Workflow:** Bridge Smoke Tests
- **Job:** Run bridge integration tests (smoke)
- **Status:** ❌ Failed

## 🐛 Error Details

```
ModuleNotFoundError: No module named 'dmaic'
```

**Full traceback:**
```
ImportError while importing test module '/home/runner/work/ABACUS/ABACUS/DMAIC_V3/tests/test_bridge_integration.py'.
DMAIC_V3/core/handover_bridge.py:12: in <module>
    from dmaic import Idempotency, provenance, metrics as handover_metrics, recursion
E   ModuleNotFoundError: No module named 'dmaic'
```

## 🔍 Root Cause

The test is trying to import `dmaic` module which is not installed or not in the Python path.

## 🔧 Proposed Fix

### Option 1: Add missing dependency
```python
# In DMAIC_V3/requirements.txt
dmaic>=1.0.0
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
    pip install -e .
    pip install -r DMAIC_V3/requirements.txt
```

## 📋 Action Items

- [ ] Identify where `dmaic` module should come from
- [ ] Add to requirements.txt OR fix import paths
- [ ] Update `setup.py` if needed
- [ ] Test imports locally
- [ ] Re-run smoke tests

## 🔗 References

- Workflow: https://github.com/GBOGEB/ABACUS/actions
- Test file: `DMAIC_V3/tests/test_bridge_integration.py`
"""
    },
    {
        "priority": "P1",
        "title": "Fix Static Analysis - flake8 AttributeError",
        "labels": ["ci/cd", "bug", "code-quality", "P1"],
        "body": """## 🔴 Issue Description

The **Static Analysis** workflow is failing with an AttributeError in flake8.

## 📊 Workflow Details

- **Workflow:** Static Analysis
- **Job:** Run flake8
- **Status:** ❌ Failed

## 🐛 Error Details

```
AttributeError: 'EntryPoints' object has no attribute 'get'
```

**Full traceback:**
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

Compatibility issue between flake8 and newer versions of importlib-metadata on Python 3.12.

## 🔧 Proposed Fix

### Option 1: Pin importlib-metadata version
```python
# In DMAIC_V3/requirements.txt
importlib-metadata<5.0
```

### Option 2: Update flake8
```python
# In DMAIC_V3/requirements.txt
flake8>=7.0.0
```

### Option 3: Use ruff instead
```python
# In DMAIC_V3/requirements.txt
ruff>=0.1.0
```

## 📋 Action Items

- [ ] Update `requirements.txt` with compatible versions
- [ ] Test locally with Python 3.12
- [ ] Update workflow if needed
- [ ] Re-run checks

## 🔗 References

- Related issue: https://github.com/PyCQA/flake8/issues/1800
"""
    },
    {
        "priority": "P1",
        "title": "Fix Bridge Unit Tests - Import and dependency issues",
        "labels": ["ci/cd", "tests", "P1"],
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
"""
    },
    {
        "priority": "P1",
        "title": "Fix Bridge Integration Tests - Import errors",
        "labels": ["ci/cd", "tests", "P1"],
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
"""
    },
    {
        "priority": "P2",
        "title": "Fix Full Deployment Test - Dependency and integration issues",
        "labels": ["ci/cd", "tests", "deployment", "P2"],
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
"""
    }
]

def create_github_issue_url(title, body, labels):
    """Create a GitHub issue URL with pre-filled content"""
    params = {
        'title': title,
        'body': body,
        'labels': ','.join(labels)
    }
    query_string = urllib.parse.urlencode(params)
    return f"{BASE_URL}?{query_string}"

def main():
    print("🚀 Opening GitHub Issue Creation Pages...\n")
    print(f"Repository: {REPO}\n")
    print("=" * 70)
    
    for i, issue in enumerate(ISSUES, 1):
        print(f"\n{i}. [{issue['priority']}] {issue['title']}")
        print(f"   Labels: {', '.join(issue['labels'])}")
        
        url = create_github_issue_url(issue['title'], issue['body'], issue['labels'])
        
        print(f"   Opening in browser...")
        
        try:
            webbrowser.open(url)
            print(f"   ✅ Opened!")
            
            if i < len(ISSUES):
                print(f"   ⏳ Waiting 3 seconds before opening next issue...")
                time.sleep(3)
        except Exception as e:
            print(f"   ❌ Error: {e}")
            print(f"   📋 Manual URL: {url[:100]}...")
    
    print("\n" + "=" * 70)
    print("\n✅ All issue creation pages opened!")
    print("\n📝 For each browser tab:")
    print("   1. Review the pre-filled content")
    print("   2. Make any adjustments if needed")
    print("   3. Click 'Submit new issue'")
    print("\n🎉 Done!")

if __name__ == '__main__':
    main()
