# DMAIC Phase 3: Runtime Dependency Analysis


**Version:** 2.3.0  
**Generated:** 2025-11-08T19:22:18.807960+00:00  
**Date:** 2025-11-08  
**Status:** 🔄 Partially Implemented  
**Your Question:** Should we enhance Phase 3 now or wait for full recursive DMAIC completion?

---

## 📊 CURRENT PHASE 3 CAPABILITIES

### What Phase 3 DOES Capture

**1. Static Analysis (Phase 2)**
```python
# From phase2_measure.jsonl - Already captured:
{
  "file_path": "example.py",
  "imports": ["pandas", "numpy", "json"],
  "functions": ["process_data", "load_config"],
  "classes": ["DataProcessor"],
  "dependencies": ["config.json", "data.csv"],  # Hardcoded paths
  "complexity": 15,
  "lines_of_code": 250
}
```

**2. Execution Results (Phase 2B)**
```python
# From phase2b_execution_results.jsonl - Captured:
{
  "file_path": "example.py",
  "success": true,
  "execution_time": 2.5,
  "stdout": "Processing complete...",
  "stderr": "",
  "exit_code": 0,
  "failure_category": null
}
```

**3. Duplicate Detection (Phase 3)**
```python
# From phase3_analyze.json - Currently captures:
{
  "exact_duplicates": [
    {"files": ["file1.py", "file2.py"], "hash": "abc123"}
  ],
  "semantic_duplicates": [
    {"files": ["utils1.py", "utils2.py"], "similarity": 0.85}
  ]
}
```

---

## ⚠️ WHAT PHASE 3 DOES NOT CAPTURE (YET)

### Missing Runtime Dependency Detection

**1. File I/O Operations**
```python
# NOT DETECTED: Runtime file reads/writes
df = pd.read_csv("data/input.csv")  # ❌ Not captured
with open("config.json") as f:      # ❌ Not captured
    config = json.load(f)
results.to_csv("output.csv")        # ❌ Not captured
```

**2. Dynamic Imports**
```python
# NOT DETECTED: Runtime module loading
module_name = "processors." + config["processor_type"]
processor = importlib.import_module(module_name)  # ❌ Not captured
```

**3. Database Connections**
```python
# NOT DETECTED: Database dependencies
conn = sqlite3.connect("database.db")  # ❌ Not captured
engine = create_engine("postgresql://...")  # ❌ Not captured
```

**4. API Calls**
```python
# NOT DETECTED: External service dependencies
response = requests.get("https://api.example.com")  # ❌ Not captured
```

**5. Environment Variables**
```python
# NOT DETECTED: Configuration dependencies
api_key = os.getenv("API_KEY")  # ❌ Not captured
db_url = os.environ["DATABASE_URL"]  # ❌ Not captured
```

**6. Cross-File Function Calls**
```python
# PARTIALLY DETECTED: Only via static import analysis
from utils import process_data  # ✅ Import detected
result = process_data(input)    # ❌ Runtime call not tracked
```

---

## 🎯 YOUR QUESTION: WHEN TO ENHANCE?

### Option 1: Enhance Phase 3 NOW ✅ RECOMMENDED

**Pros:**
- Captures runtime dependencies during Phase 2B execution
- Provides complete dependency graph for Phase 4 (IMPROVE)
- Enables accurate duplicate detection based on actual usage
- Better foundation for Knowledge Devour engine

**Cons:**
- Delays full production test completion
- Requires modifying Phase 2B execution wrapper
- May slow down execution (instrumentation overhead)

**Implementation Approach:**
```python
# Add to Phase 2B execution wrapper:
def execute_with_dependency_tracking(file_path):
    """Execute file and capture runtime dependencies"""
    
    # 1. Wrap file I/O operations
    original_open = builtins.open
    file_accesses = []
    
    def tracked_open(path, *args, **kwargs):
        file_accesses.append({
            "type": "file_read" if "r" in args else "file_write",
            "path": os.path.abspath(path),
            "timestamp": time.time()
        })
        return original_open(path, *args, **kwargs)
    
    builtins.open = tracked_open
    
    # 2. Track imports
    import_tracker = []
    original_import = __import__
    
    def tracked_import(name, *args, **kwargs):
        import_tracker.append({
            "module": name,
            "timestamp": time.time()
        })
        return original_import(name, *args, **kwargs)
    
    builtins.__import__ = tracked_import
    
    # 3. Execute file
    try:
        exec(open(file_path).read())
    finally:
        # Restore originals
        builtins.open = original_open
        builtins.__import__ = original_import
    
    # 4. Return captured dependencies
    return {
        "file_accesses": file_accesses,
        "dynamic_imports": import_tracker,
        "execution_time": time.time()
    }
```

### Option 2: Wait for Full Recursive DMAIC

**Pros:**
- Complete production test first
- Understand full scope before enhancing
- Can design better solution with complete data

**Cons:**
- Phase 4 (IMPROVE) will lack runtime dependency data
- May need to re-run Phase 2B after enhancement
- Delays knowledge graph construction

---

## 🚀 RECOMMENDED APPROACH

### **Hybrid Strategy: Enhance Phase 3 Incrementally**

**Step 1: Complete Current Production Test (In Progress)**
- ✅ Phase 1: DEFINE - Complete
- ✅ Phase 2: MEASURE - Complete
- ✅ Phase 2A: IDENTIFY CLEAN FILES - Complete (1,081 files)
- 🔄 Phase 2B: EXECUTE CLEAN FILES - In Progress
- ⏳ Phase 3: ANALYZE - Pending

**Step 2: Analyze Phase 2B Results**
- Review execution success rate
- Identify common failure patterns
- Understand what files actually execute successfully

**Step 3: Enhance Phase 3 with Runtime Tracking**
- Add file I/O tracking to Phase 2B wrapper
- Capture dynamic imports and module loading
- Track database connections and API calls
- Store runtime dependencies in `phase2b_runtime_deps.jsonl`

**Step 4: Re-run Phase 2B with Enhanced Tracking**
- Only re-run successfully executed files
- Capture complete runtime dependency graph
- Merge with static analysis from Phase 2

**Step 5: Enhanced Phase 3 Analysis**
- Build complete dependency graph (static + runtime)
- Detect duplicates based on actual usage patterns
- Identify orphaned files (no dependencies)
- Map data flow through the codebase

---

## 📋 ENHANCED PHASE 3 OUTPUT STRUCTURE

### Current Output
```
DMAIC_PRODUCTION_FULL/
├── phase1_define.json              # File discovery
├── phase2_measure.jsonl            # Static analysis
├── phase2a_clean_files.json        # Executable candidates
├── phase2b_execution_results.jsonl # Execution results
└── phase3_analyze.json             # Duplicate detection
```

### Enhanced Output (Proposed)
```
DMAIC_PRODUCTION_FULL/
├── phase1_define.json              # File discovery
├── phase2_measure.jsonl            # Static analysis
├── phase2a_clean_files.json        # Executable candidates
├── phase2b_execution_results.jsonl # Execution results
├── phase2b_runtime_deps.jsonl      # ✨ NEW: Runtime dependencies
├── phase3_analyze.json             # Duplicate detection
├── phase3_dependency_graph.json    # ✨ NEW: Complete dependency graph
├── phase3_data_flow.json           # ✨ NEW: Data flow analysis
└── phase3_orphaned_files.json      # ✨ NEW: Unused files
```

### Enhanced Dependency Graph Format
```json
{
  "file_path": "processors/data_processor.py",
  "static_dependencies": {
    "imports": ["pandas", "numpy", "json"],
    "local_imports": ["utils.helpers", "config.settings"]
  },
  "runtime_dependencies": {
    "files_read": [
      {"path": "data/input.csv", "format": "csv", "size_mb": 15.2},
      {"path": "config/settings.json", "format": "json"}
    ],
    "files_written": [
      {"path": "output/results.csv", "format": "csv", "size_mb": 8.5}
    ],
    "dynamic_imports": ["processors.custom_processor"],
    "database_connections": [
      {"type": "sqlite", "path": "data/cache.db"}
    ],
    "api_calls": [
      {"url": "https://api.example.com/data", "method": "GET"}
    ],
    "environment_vars": ["API_KEY", "DATABASE_URL"]
  },
  "execution_metadata": {
    "success": true,
    "execution_time": 2.5,
    "memory_peak_mb": 150,
    "cpu_time": 1.8
  },
  "relationships": {
    "called_by": ["main.py", "batch_processor.py"],
    "calls": ["utils/helpers.py::validate_data"],
    "data_flow": {
      "inputs": ["data/input.csv"],
      "outputs": ["output/results.csv"],
      "intermediate": ["temp/processed.pkl"]
    }
  }
}
```

---

## 🎯 DECISION MATRIX

| Criterion | Enhance Now | Wait for Full Test |
|-----------|-------------|-------------------|
| **Data Completeness** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Time to Complete** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Phase 4 Readiness** | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **Knowledge Graph Quality** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Risk of Rework** | ⭐⭐⭐ | ⭐⭐⭐⭐ |

**Recommendation:** ✅ **Enhance Phase 3 NOW**

---

## 📝 IMPLEMENTATION PLAN

### Phase 1: Complete Current Test (Today)
- ✅ Wait for Phase 2B completion (~30-60 min for 1,081 files)
- ✅ Run Phase 3 with current capabilities
- ✅ Analyze results and identify gaps

### Phase 2: Design Enhancement (Today)
- Create `runtime_dependency_tracker.py` module
- Design instrumentation for file I/O, imports, DB, APIs
- Plan integration with Phase 2B execution wrapper

### Phase 3: Implement Enhancement (Tomorrow)
- Add runtime tracking to Phase 2B
- Create `phase2b_runtime_deps.jsonl` output
- Enhance Phase 3 to merge static + runtime data

### Phase 4: Re-run with Enhancement (Tomorrow)
- Re-run Phase 2B on successfully executed files
- Generate complete dependency graph
- Build enhanced Phase 3 analysis

### Phase 5: Validate & Document (Tomorrow)
- Verify dependency graph accuracy
- Document findings
- Prepare for Phase 4 (IMPROVE) implementation

---

## 🔍 EXAMPLE: What We'll Capture

### Before Enhancement (Current)
```json
{
  "file": "data_processor.py",
  "imports": ["pandas", "json"],
  "functions": ["process_data"],
  "executed": true,
  "success": true
}
```

### After Enhancement (Proposed)
```json
{
  "file": "data_processor.py",
  "static_analysis": {
    "imports": ["pandas", "json"],
    "functions": ["process_data"]
  },
  "runtime_analysis": {
    "files_accessed": [
      {"path": "data/input.csv", "mode": "read", "size": 15728640},
      {"path": "config.json", "mode": "read", "size": 1024},
      {"path": "output/results.csv", "mode": "write", "size": 8912896}
    ],
    "modules_loaded": ["pandas", "json", "numpy"],
    "functions_called": [
      {"module": "pandas", "function": "read_csv", "count": 1},
      {"module": "json", "function": "load", "count": 1}
    ],
    "execution_time": 2.5,
    "memory_peak": 157286400
  },
  "dependency_graph": {
    "inputs": ["data/input.csv", "config.json"],
    "outputs": ["output/results.csv"],
    "dependencies": ["pandas", "json", "numpy"]
  }
}
```

---

## ✅ FINAL RECOMMENDATION

**Enhance Phase 3 NOW** for these reasons:

1. **Phase 2B is already running** - Perfect time to add instrumentation
2. **Phase 4 needs runtime data** - Can't improve without knowing actual dependencies
3. **Knowledge Devour requires it** - Complete dependency graph is essential
4. **Minimal rework** - Only need to re-run successfully executed files
5. **Better insights** - Understand actual vs. declared dependencies

**Next Steps:**
1. ✅ Wait for current Phase 2B to complete
2. ✅ Run Phase 3 with current capabilities (baseline)
3. ✅ Implement runtime dependency tracking
4. ✅ Re-run Phase 2B with enhanced tracking
5. ✅ Generate complete dependency graph
6. ✅ Proceed to Phase 4 (IMPROVE) with full data

---

**Decision:** Proceed with enhancement after current test completes?  
**Timeline:** 1-2 days for full implementation  
**Impact:** High - Enables Phase 4-6 with complete data
