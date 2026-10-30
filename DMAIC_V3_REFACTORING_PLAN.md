# DMAIC V3.0 REFACTORING PLAN
## Modular Architecture with Idempotency and Phase Separation

**Version:** 3.0.0
**Date:** 2024
**Status:** Planning Phase
**Previous Version:** v2.3 (Enhanced Engine with Pause Functionality)

---

## 🎯 CORE OBJECTIVES

### 1. **Modular Phase Separation**
- Break monolithic engine into independent phase modules
- Each phase as a separate file for easier maintenance and iteration
- Enable individual phase execution and testing
- Reduce file size for better manageability

### 2. **IDEMPOTENCY Principle** ⭐ NEW CORE PRINCIPLE
- **Definition:** Running the same operation multiple times produces the same result
- **Implementation:**
  - State tracking and checkpointing
  - Resume capability from any phase
  - Deterministic outputs
  - No side effects from repeated execution
  - Atomic operations with rollback capability

### 3. **Phase 0: Setup & Initialization** 🆕
- Pre-flight checks before execution
- Dependency validation
- Virtual environment setup
- Configuration validation
- Root directory verification
- Error prevention through pre-checks

### 4. **Professional Python Structure**
- Proper `__init__.py` for package structure
- `__main__.py` for module execution
- Centralized configuration management
- Comprehensive requirements management
- Cross-platform compatibility (Windows/Linux)

---

## #
```
DMAIC_V3/
├── dmaic_v3_engine.py              # Main orchestrator (lightweight glue code)
├── config.py                        # Centralized configuration
├── requirements.txt                 # Canonical dependencies
├── setup.py                         # Package installation
├── README.md                        # Documentation
├── CHANGELOG.md                     # Version history
│
├── phases/                          # Phase modules directory
│   ├── __init__.py                 # Package initialization
│   ├── phase0_setup.py             # Phase 0: Setup & Initialization
│   ├── phase1_define.py            # Phase 1: Define
│   ├── phase2_measure.py           # Phase 2: Measure
│   ├── phase3_analyze.py           # Phase 3: Analyze
│   ├── phase4_improve.py           # Phase 4: Improve
│   ├── phase5_control.py           # Phase 5: Control
│   └── phase6_knowledge_devour.py  # Phase 6: Knowledge Devour
│
├── core/                            # Core utilities
│   ├── __init__.py
│   ├── models.py                   # Data models (Metric, PhaseMetrics, etc.)
│   ├── metrics.py                  # Metrics tracking
│   ├── knowledge.py                # Knowledge management
│   ├── state.py                    # State management (idempotency)
│   └── utils.py                    # Utility functions
│
├── setup/                           # Setup scripts
│   ├── setup_environment.ps1       # PowerShell setup (Windows)
│   ├── setup_environment.sh        # Bash setup (Linux/Mac)
│   └── activate_venv.ps1           # Auto-venv activation
│
├── tests/                           # Test suite
│   ├── __init__.py
│   ├── test_phase0.py
│   ├── test_phase1.py
│   └── ...
│
└── output/                          # Output directory
    ├── iterations/
    ├── knowledge_packs/
    ├── reports/
    └── state/                       # State files for idempotency
```

---

## 🔧 CORE PRINCIPLES & DESIGN PATTERNS

### 1. **IDEMPOTENCY Implementation**

```python
class IdempotentPhase:
    """Base class for idempotent phase execution"""

    def __init__(self, state_manager):
        self.state = state_manager
        self.phase_id = None

    def execute(self, context):
        """Execute phase with idempotency"""
        # Check if already executed
        if self.state.is_completed(self.phase_id, context):
            return self.state.get_result(self.phase_id, context)

        # Execute phase
        try:
            result = self._execute_impl(context)
            self.state.save_result(self.phase_id, context, result)
            return result
        except Exception as e:
            self.state.save_error(self.phase_id, context, e)
            raise

    def _execute_impl(self, context):
        """Override in subclass"""
        raise NotImplementedError
```

### 2. **Phase Interface Contract**

Each phase module must implement:

```python
class PhaseInterface:
    """Standard interface for all phases"""

    def validate_inputs(self, context) -> bool:
        """Validate phase inputs"""
        pass

    def execute(self, context) -> PhaseMetrics:
        """Execute phase logic"""
        pass

    def rollback(self, context) -> bool:
        """Rollback phase changes if needed"""
        pass

    def get_metrics(self) -> PhaseMetrics:
        """Return phase metrics"""
        pass
```

### 3. **State Management**

```python
class StateManager:
    """Manages execution state for idempotency"""

    def __init__(self, state_dir):
        self.state_dir = Path(state_dir)
        self.state_file = self.state_dir / "execution_state.json"

    def is_completed(self, phase_id, context):
        """Check if phase completed successfully"""
        pass

    def save_checkpoint(self, phase_id, context, data):
        """Save checkpoint for resume capability"""
        pass

    def load_checkpoint(self, phase_id, context):
        """Load checkpoint to resume"""
        pass
```

---

## 📋 PHASE 0: SETUP & INITIALIZATION

### Purpose
Pre-flight checks and environment setup before DMAIC execution

### Responsibilities
1. **Environment Validation**
   - Python version check (>= 3.8)
   - Required system tools (git, etc.)
   - Disk space availability

2. **Virtual Environment**
   - Create/activate venv if not exists
   - Install/update dependencies
   - Verify package versions

3. **Configuration Validation**
   - Load and validate config.py
   - Check workspace paths
   - Verify output directories

4. **Dependency Checks**
   - Verify all required packages
   - Check for conflicts
   - Validate versions

5. **Pre-execution Checks**
   - Workspace accessibility
   - Write permissions
   - Previous state recovery (if resuming)

### Implementation

```python
# phases/phase0_setup.py

class Phase0Setup(PhaseInterface):
    """Phase 0: Setup and Initialization"""

    def __init__(self, config):
        self.config = config
        self.checks_passed = []
        self.checks_failed = []

    def execute(self, context):
        """Execute all setup checks"""
        print("="*80)
        print("PHASE 0: SETUP & INITIALIZATION")
        print("="*80)

        # 1. Python version check
        self._check_python_version()

        # 2. Virtual environment
        self._setup_virtual_environment()

        # 3. Dependencies
        self._check_dependencies()

        # 4. Configuration
        self._validate_configuration()

        # 5. Workspace
        self._validate_workspace()

        # 6. State recovery
        self._check_previous_state()

        return self._generate_setup_report()
```

---

ere
