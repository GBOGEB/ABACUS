# DMAIC v2.1 - QUICK TROUBLESHOOTING GUIDE


**Version:** 2.3.0  
**Generated:** 2025-11-08T19:22:18.814266+00:00  
## 🚨 **IMPORT TIMEOUT - IMMEDIATE FIX**

### **Problem:**
```bash
$ python -c "import recursive_dmaic_engine_v2"
[Hangs for 120+ seconds]
```

### **Quick Fix (5 minutes):**

```bash
# Step 1: Copy to local directory (no OneDrive, no spaces)
mkdir C:\Temp\dmaic_test
cd "C:\Users\gbonthuy\OneDrive - Studiecentrum voor Kernenergie\Master_Input"
copy recursive_dmaic_engine_v2.py C:\Temp\dmaic_test\
copy quick_dmaic_test.py C:\Temp\dmaic_test\
copy -r DMAIC_TEST_SAMPLE C:\Temp\dmaic_test\

# Step 2: Test from new location
cd C:\Temp\dmaic_test
python -c "import recursive_dmaic_engine_v2; print('SUCCESS!')"

# Step 3: If it works, run tests
python quick_dmaic_test.py
```

### **If Still Hangs:**

```bash
# Check for syntax errors
python -m py_compile recursive_dmaic_engine_v2.py

# Verbose import (see where it hangs)
python -v -c "import recursive_dmaic_engine_v2" 2>&1 | tail -50

# Check dependencies
python -c "import yaml, toml, ast; print('Dependencies OK')"
```

---

## ✅ **VERIFICATION CHECKLIST**

### **After Import Works:**

```bash
# 1. Quick test (2 min)
python quick_dmaic_test.py

# 2. Check output files
ls dmaic_output/
cat dmaic_output/phase1_define.json

# 3. Full test (5-10 min)
python recursive_dmaic_engine_v2.py --root . --output dmaic_full_test

# 4. Verify all phases
ls dmaic_full_test/
```

### **Expected Output:**
```
✅ Phase 1: DEFINE - Scanned X files
✅ Phase 2: MEASURE - Analyzed X files
✅ Phase 2A: IDENTIFY - Found X clean files
✅ Phase 2B: EXECUTE - Executed X files
✅ Phase 3: ANALYZE - Found X duplicates
```

---

## 🔍 **COMMON ISSUES**

### **Issue: "No module named 'yaml'"**
```bash
pip install pyyaml toml
```

### **Issue: "No module named 'toml'"**
```bash
pip install toml
```

### **Issue: "Permission denied"**
```bash
# Run as administrator or check file permissions
icacls recursive_dmaic_engine_v2.py
```

### **Issue: "File not found"**
```bash
# Check current directory
pwd
ls *.py
```

---

## 📊 **QUICK STATUS CHECK**

### **Check Type Errors:**
```bash
# Should show 0 errors
python -c "from problems import check; check()"
```

### **Check File Size:**
```bash
# Should be ~1816 lines
wc -l recursive_dmaic_engine_v2.py
```

### **Check Methods:**
```bash
# Should find both helper methods
grep -n "def _score_file_executability" recursive_dmaic_engine_v2.py
grep -n "def _is_likely_executable" recursive_dmaic_engine_v2.py
```

---

## 🎯 **WHAT TO TEST**

### **Priority 1: Import**
```bash
python -c "import recursive_dmaic_engine_v2; print('✅ Import OK')"
```

### **Priority 2: Quick Test**
```bash
python quick_dmaic_test.py
# Should complete in < 30 seconds
```

### **Priority 3: Full Test**
```bash
python recursive_dmaic_engine_v2.py --root . --output test_output
# Should show progress every 1000 files
# Should stop at 50,000 files if needed
```

---

## 📝 **WHAT WAS FIXED**

### **✅ Completed:**
1. All 96 static type errors → 0
2. Helper method indentation bug
3. Progress reporting (every 1000 files)
4. File count limits (50,000 max)
5. Extended directory filtering (14 patterns)
6. Phase 4 stub implementation

### **❌ Blocked:**
1. Import timeout (OneDrive issue suspected)
2. Cannot test any fixes
3. Cannot run on full codebase

---

## 🔧 **EMERGENCY COMMANDS**

### **If Everything Fails:**

```bash
# 1. Check Python version
python --version
# Should be 3.8+

# 2. Check file integrity
python -m py_compile recursive_dmaic_engine_v2.py

# 3. Check imports
python -c "import os, sys, json, yaml, toml, ast; print('OK')"

# 4. Test minimal import
python -c "import sys; sys.path.insert(0, '.'); print('Path OK')"

# 5. Check for file locks (Windows)
# Use Process Explorer to check if file is locked
```

---

## 📞 **CONTACT INFO**

### **Files to Check:**
- `DMAIC_V2.1_SESSION_SUMMARY.md` - What was done
- `DMAIC_V2.1_CRITICAL_FIXES.md` - Current status
- `DMAIC_V2.1_ACTUAL_RESULTS.md` - Test results

### **Key Locations:**
- Main File: `recursive_dmaic_engine_v2.py` (1816 lines)
- Test File: `quick_dmaic_test.py`
- Sample Data: `DMAIC_TEST_SAMPLE/`

---

## 🎯 **SUCCESS CRITERIA**

### **Minimum:**
- ✅ Import works without timeout
- ✅ Quick test passes
- ✅ No type errors

### **Ideal:**
- ✅ Full codebase test completes
- ✅ All phases work
- ✅ Progress reporting visible

---

**Last Updated:** 2025-01-XX  
**Status:** Ready for testing once import works  
**Next Action:** Copy to C:\Temp and test import
