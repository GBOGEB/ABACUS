"""
DMAIC V3.3 Configuration Module
Updated: 2025-11-12

Centralized configuration for all DMAIC phases with support for:
- Phase-specific settings
- Idempotency controls
- Ranking integration
- Metrics collection
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

VERSION = "3.3.0"
PREVIOUS_VERSION = "2.3.0"

# Core Principles
CORE_PRINCIPLES = [
    "KNOWLEDGE MUST GROW, NEVER DILUTE",
    "IDEMPOTENCY: Same input → Same output",
    "MODULARITY: Independent, testable phases",
    "OBSERVABILITY: Track everything",
]


class ExecutionMode(Enum):
    """Execution modes for the engine"""
    FULL = "full"                    # Execute all phases
    SINGLE_PHASE = "single_phase"    # Execute single phase
    RESUME = "resume"                # Resume from checkpoint
    DRY_RUN = "dry_run"             # Validation only
    SETUP_ONLY = "setup_only"       # Phase 0 only


@dataclass
class PathConfig:
    """Path configuration"""
    workspace_root: Path = Path(__file__).parent.parent.resolve()
    output_root: Path = Path("DMAIC_V3_OUTPUT")
    state_dir: Path = Path("DMAIC_V3_OUTPUT/state")
    knowledge_dir: Path = Path("DMAIC_V3_OUTPUT/knowledge_packs")
    reports_dir: Path = Path("DMAIC_V3_OUTPUT/reports")
    iterations_dir: Path = Path("DMAIC_V3_OUTPUT/iterations")
    logs_dir: Path = Path("DMAIC_V3_OUTPUT/logs")

    def create_directories(self):
        """Create all required directories"""
        for attr_name in dir(self):
            if attr_name.endswith('_dir') or attr_name.endswith('_root'):
                path = getattr(self, attr_name)
                if isinstance(path, Path):
                    path.mkdir(parents=True, exist_ok=True)
        for attr_name in dir(self):
            if attr_name.endswith('_dir') or attr_name.endswith('_root'):
                path = getattr(self, attr_name)
                if isinstance(path, Path):
                    path.mkdir(parents=True, exist_ok=True)


@dataclass
class Phase0Config:
    """Phase 0: Setup & Initialization Configuration"""
    enabled: bool = True
    python_min_version: str = "3.10.0"
    required_disk_space_mb: int = 100
    check_git: bool = True
    auto_create_venv: bool = True
    venv_name: str = ".venv"
    validate_dependencies: bool = True
    fail_on_warning: bool = False


@dataclass
class PhaseConfig:
    """Generic phase configuration"""
    enabled: bool = True
    timeout_seconds: int = 3600
    retry_on_failure: bool = False
    max_retries: int = 3
    save_checkpoints: bool = True
    verbose: bool = True


@dataclass
class IdempotencyConfig:
    """Idempotency configuration"""
    enabled: bool = True
    state_file: str = "execution_state.json"
    checkpoint_interval: int = 60  # seconds
    hash_algorithm: str = "sha256"
    verify_checksums: bool = True
    allow_resume: bool = True


@dataclass
class MetricsConfig:
    """Metrics tracking configuration"""
    enabled: bool = True
    track_baseline: bool = True
    track_trends: bool = True
    export_format: List[str] = field(default_factory=lambda: ["json", "csv"])
    visualization: bool = True


@dataclass
class KnowledgeConfig:
    """Knowledge management configuration"""
    enabled: bool = True
    pack_format: str = "json"
    compression: bool = True
    versioning: bool = True
    max_pack_size_mb: int = 10


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_logging: bool = True
    console_logging: bool = True
    log_file: str = "dmaic_v3.log"


@dataclass
class DMAICConfig:
    """Main DMAIC Configuration"""
    version: str = VERSION
    execution_mode: ExecutionMode = ExecutionMode.FULL
    workspace_root: str = str(Path(__file__).parent.parent.resolve())

    # Sub-configurations
    paths: PathConfig = field(default_factory=PathConfig)
    phase0: Phase0Config = field(default_factory=Phase0Config)
    phase_defaults: PhaseConfig = field(default_factory=PhaseConfig)
    idempotency: IdempotencyConfig = field(default_factory=IdempotencyConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    knowledge: KnowledgeConfig = field(default_factory=KnowledgeConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # Execution settings
    max_iterations: int = 10
    pause_between_phases: bool = False
    pause_between_iterations: bool = False
    parallel_execution: bool = False

    # Phase-specific overrides
    phase_configs: Dict[str, PhaseConfig] = field(default_factory=dict)

    def __post_init__(self):
        """Post-initialization setup"""
        # Ensure workspace_root is propagated to paths
        try:
            self.paths.workspace_root = Path(self.workspace_root)
        except Exception:
            # If paths doesn't have workspace_root attribute for some reason, ignore
            pass

        # Create directories
        self.paths.create_directories()

        # Initialize phase-specific configs if not provided
        if not self.phase_configs:
            for i in range(10):  # Phase 0-9
                self.phase_configs[f"phase{i}"] = PhaseConfig()

    def get_phase_config(self, phase_number: int) -> PhaseConfig:
        """Get configuration for specific phase"""
        key = f"phase{phase_number}"
        return self.phase_configs.get(key, self.phase_defaults)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "version": self.version,
            "execution_mode": self.execution_mode.value,
            "workspace_root": self.workspace_root,
            "paths": {k: str(v) for k, v in self.paths.__dict__.items()},
            "phase0": self.phase0.__dict__,
            "idempotency": self.idempotency.__dict__,
            "metrics": self.metrics.__dict__,
            "knowledge": self.knowledge.__dict__,
            "logging": self.logging.__dict__,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DMAICConfig':
        """Create configuration from dictionary"""
        # This is a simplified version - full implementation would handle nested objects
        config = cls()
        # Update with provided data
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config


# Default configuration instance
DEFAULT_CONFIG = DMAICConfig()


# Environment-specific configurations
def get_development_config() -> DMAICConfig:
    """Development environment configuration"""
    config = DMAICConfig()
    config.logging.level = "DEBUG"
    config.phase_defaults.verbose = True
    config.idempotency.verify_checksums = False  # Faster for dev
    return config


def get_production_config() -> DMAICConfig:
    """Production environment configuration"""
    config = DMAICConfig()
    config.logging.level = "INFO"
    config.idempotency.verify_checksums = True
    config.phase0.fail_on_warning = True
    config.metrics.visualization = False  # Disable for performance
    return config


def get_testing_config() -> DMAICConfig:
    """Testing environment configuration"""
    config = DMAICConfig()
    config.paths.output_root = Path("test_output")
    config.logging.level = "DEBUG"
    config.phase_defaults.timeout_seconds = 60
    return config


# Configuration loader
def load_config(config_file: Path = None, environment: str = "default") -> DMAICConfig:
    """
    Load configuration from file or use defaults
    
    Args:
        config_file: Path to configuration file (JSON/YAML)
        environment: Environment name (default, development, production, testing)
    
    Returns:
        DMAICConfig instance
    """
    if environment == "development":
        return get_development_config()
    elif environment == "production":
        return get_production_config()
    elif environment == "testing":
        return get_testing_config()
    
    if config_file and config_file.exists():
        # Load from file (implementation depends on format)
        import json
        with open(config_file, 'r') as f:
            data = json.load(f)
        return DMAICConfig.from_dict(data)
    
    return DEFAULT_CONFIG


if __name__ == "__main__":
    # Example usage and validation
    print("="*80)
    print(f"DMAIC V{VERSION} - Configuration")
    print("="*80)
    
    config = DEFAULT_CONFIG
    print(f"\nVersion: {config.version}")
    print(f"Execution Mode: {config.execution_mode.value}")
    print(f"\nCore Principles:")
    for principle in CORE_PRINCIPLES:
        print(f"  - {principle}")
    
    print(f"\nPaths:")
    print(f"  Workspace: {config.paths.workspace_root}")
    print(f"  Output: {config.paths.output_root}")
    print(f"  State: {config.paths.state_dir}")
    
    print(f"\nPhase 0 (Setup):")
    print(f"  Enabled: {config.phase0.enabled}")
    print(f"  Python Min Version: {config.phase0.python_min_version}")
    print(f"  Auto Create Venv: {config.phase0.auto_create_venv}")
    
    print(f"\nIdempotency:")
    print(f"  Enabled: {config.idempotency.enabled}")
    print(f"  Allow Resume: {config.idempotency.allow_resume}")
    print(f"  Verify Checksums: {config.idempotency.verify_checksums}")
    
    print("\n" + "="*80)
