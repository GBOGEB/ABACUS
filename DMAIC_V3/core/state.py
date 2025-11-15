"""
DMAIC V3.0 - State Management for Idempotency
Handles execution state, checkpoints, and resume capability
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum


class PhaseStatus(Enum):
    """Phase execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PhaseState:
    """State of a single phase execution"""
    phase_id: str
    phase_number: int
    status: PhaseStatus
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: float = 0.0
    input_hash: Optional[str] = None
    output_hash: Optional[str] = None
    error_message: Optional[str] = None
    checkpoint_data: Dict[str, Any] = None
    metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.checkpoint_data is None:
            self.checkpoint_data = {}
        if self.metrics is None:
            self.metrics = {}


@dataclass
class IterationState:
    """State of a complete iteration"""
    iteration_number: int
    start_time: str
    end_time: Optional[str] = None
    status: str = "running"
    phases: Dict[str, PhaseState] = None
    
    def __post_init__(self):
        if self.phases is None:
            self.phases = {}


class StateManager:
    """
    Manages execution state for idempotent operations
    
    Responsibilities:
    - Track phase execution status
    - Save/load checkpoints
    - Compute input/output hashes
    - Enable resume capability
    - Verify idempotency
    """
    
    def __init__(self, state_dir: Path, hash_algorithm: str = "sha256"):
        """
        Initialize state manager
        
        Args:
            state_dir: Directory to store state files
            hash_algorithm: Hash algorithm for checksums (sha256, md5, etc.)
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        self.state_file = self.state_dir / "execution_state.json"
        self.hash_algorithm = hash_algorithm
        
        self.current_iteration: Optional[IterationState] = None
        self.execution_history: List[IterationState] = []
        
        self._load_state()
    
    def _load_state(self):
        """Load state from disk"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self._deserialize_state(data)
            except Exception as e:
                print(f"[STATE] Warning: Could not load state: {e}")
    
    def _save_state(self):
        """Save state to disk"""
        try:
            data = self._serialize_state()
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[STATE] Error: Could not save state: {e}")
    
    def _serialize_state(self) -> Dict[str, Any]:
        """Serialize state to dictionary"""
        return {
            "current_iteration": self._serialize_iteration(self.current_iteration) if self.current_iteration else None,
            "execution_history": [self._serialize_iteration(it) for it in self.execution_history],
            "last_updated": datetime.now().isoformat()
        }
    
    def _serialize_iteration(self, iteration: IterationState) -> Dict[str, Any]:
        """Serialize iteration state"""
        return {
            "iteration_number": iteration.iteration_number,
            "start_time": iteration.start_time,
            "end_time": iteration.end_time,
            "status": iteration.status,
            "phases": {
                phase_id: self._serialize_phase(phase)
                for phase_id, phase in iteration.phases.items()
            }
        }
    
    def _serialize_phase(self, phase: PhaseState) -> Dict[str, Any]:
        """Serialize phase state"""
        return {
            "phase_id": phase.phase_id,
            "phase_number": phase.phase_number,
            "status": phase.status.value,
            "start_time": phase.start_time,
            "end_time": phase.end_time,
            "duration_seconds": phase.duration_seconds,
            "input_hash": phase.input_hash,
            "output_hash": phase.output_hash,
            "error_message": phase.error_message,
            "checkpoint_data": phase.checkpoint_data,
            "metrics": phase.metrics
        }
    
    def _deserialize_state(self, data: Dict[str, Any]):
        """Deserialize state from dictionary"""
        if data.get("current_iteration"):
            self.current_iteration = self._deserialize_iteration(data["current_iteration"])
        
        self.execution_history = [
            self._deserialize_iteration(it_data)
            for it_data in data.get("execution_history", [])
        ]
    
    def _deserialize_iteration(self, data: Dict[str, Any]) -> IterationState:
        """Deserialize iteration state"""
        phases = {
            phase_id: self._deserialize_phase(phase_data)
            for phase_id, phase_data in data.get("phases", {}).items()
        }
        
        return IterationState(
            iteration_number=data["iteration_number"],
            start_time=data["start_time"],
            end_time=data.get("end_time"),
            status=data.get("status", "running"),
            phases=phases
        )
    
    def _deserialize_phase(self, data: Dict[str, Any]) -> PhaseState:
        """Deserialize phase state"""
        return PhaseState(
            phase_id=data["phase_id"],
            phase_number=data["phase_number"],
            status=PhaseStatus(data["status"]),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            duration_seconds=data.get("duration_seconds", 0.0),
            input_hash=data.get("input_hash"),
            output_hash=data.get("output_hash"),
            error_message=data.get("error_message"),
            checkpoint_data=data.get("checkpoint_data", {}),
            metrics=data.get("metrics", {})
        )
    
    def compute_hash(self, data: Any) -> str:
        """
        Compute hash of data for idempotency checking
        
        Args:
            data: Data to hash (will be converted to string)
        
        Returns:
            Hex digest of hash
        """
        if isinstance(data, dict):
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)
        
        hasher = hashlib.new(self.hash_algorithm)
        hasher.update(data_str.encode('utf-8'))
        return hasher.hexdigest()
    
    def start_iteration(self, iteration_number: int):
        """Start a new iteration"""
        self.current_iteration = IterationState(
            iteration_number=iteration_number,
            start_time=datetime.now().isoformat(),
            status="running"
        )
        self._save_state()
    
    def end_iteration(self, status: str = "completed"):
        """End current iteration"""
        if self.current_iteration:
            self.current_iteration.end_time = datetime.now().isoformat()
            self.current_iteration.status = status
            self.execution_history.append(self.current_iteration)
            self.current_iteration = None
            self._save_state()
    
    def start_phase(self, phase_id: str, phase_number: int, input_data: Any = None):
        """Start phase execution"""
        if not self.current_iteration:
            raise RuntimeError("No active iteration")
        
        phase_state = PhaseState(
            phase_id=phase_id,
            phase_number=phase_number,
            status=PhaseStatus.RUNNING,
            start_time=datetime.now().isoformat(),
            input_hash=self.compute_hash(input_data) if input_data else None
        )
        
        self.current_iteration.phases[phase_id] = phase_state
        self._save_state()
    
    def end_phase(self, phase_id: str, status: PhaseStatus, output_data: Any = None, 
                  error: Optional[str] = None, metrics: Optional[Dict] = None):
        """End phase execution"""
        if not self.current_iteration:
            raise RuntimeError("No active iteration")
        
        if phase_id not in self.current_iteration.phases:
            raise RuntimeError(f"Phase {phase_id} not started")
        
        phase = self.current_iteration.phases[phase_id]
        phase.status = status
        phase.end_time = datetime.now().isoformat()
        
        if phase.start_time:
            start = datetime.fromisoformat(phase.start_time)
            end = datetime.fromisoformat(phase.end_time)
            phase.duration_seconds = (end - start).total_seconds()
        
        if output_data:
            phase.output_hash = self.compute_hash(output_data)
        
        if error:
            phase.error_message = error
        
        if metrics:
            phase.metrics = metrics
        
        self._save_state()
    
    def save_checkpoint(self, phase_id: str, checkpoint_data: Dict[str, Any]):
        """Save checkpoint data for a phase"""
        if not self.current_iteration:
            raise RuntimeError("No active iteration")
        
        if phase_id not in self.current_iteration.phases:
            raise RuntimeError(f"Phase {phase_id} not started")
        
        phase = self.current_iteration.phases[phase_id]
        phase.checkpoint_data.update(checkpoint_data)
        self._save_state()
    
    def load_checkpoint(self, phase_id: str) -> Optional[Dict[str, Any]]:
        """Load checkpoint data for a phase"""
        if not self.current_iteration:
            return None
        
        if phase_id not in self.current_iteration.phases:
            return None
        
        return self.current_iteration.phases[phase_id].checkpoint_data
    
    def is_phase_completed(self, phase_id: str) -> bool:
        """Check if phase completed successfully"""
        if not self.current_iteration:
            return False
        
        if phase_id not in self.current_iteration.phases:
            return False
        
        return self.current_iteration.phases[phase_id].status == PhaseStatus.COMPLETED
    
    def can_skip_phase(self, phase_id: str, input_data: Any) -> bool:
        """
        Check if phase can be skipped (idempotency check)
        
        Returns True if:
        - Phase completed successfully in current iteration
        - Input hash matches previous execution
        """
        if not self.is_phase_completed(phase_id):
            return False
        
        phase = self.current_iteration.phases[phase_id]
        current_hash = self.compute_hash(input_data) if input_data else None
        
        return phase.input_hash == current_hash
    
    def get_phase_result(self, phase_id: str) -> Optional[Dict[str, Any]]:
        """Get cached result from completed phase"""
        if not self.is_phase_completed(phase_id):
            return None
        
        phase = self.current_iteration.phases[phase_id]
        return {
            "metrics": phase.metrics,
            "checkpoint_data": phase.checkpoint_data,
            "output_hash": phase.output_hash
        }
    
    def get_resume_point(self) -> Optional[int]:
        """Get phase number to resume from"""
        if not self.current_iteration:
            return None

        for phase_id in sorted(self.current_iteration.phases.keys()):
            phase = self.current_iteration.phases[phase_id]
            if phase.status in [PhaseStatus.RUNNING, PhaseStatus.FAILED]:
                return phase.phase_number

        return None

    def add_iteration_result(self, result: 'IterationResult'):
        """
        Add an iteration result to the state

        Args:
            result: IterationResult object containing iteration data
        """
        result_data = {
            "iteration": result.iteration,
            "phases_completed": result.phases_completed,
            "phases_failed": result.phases_failed,
            "phases_skipped": result.phases_skipped,
            "total_duration_seconds": result.total_duration_seconds,
            "metrics": {k: v.to_dict() for k, v in (result.metrics or {}).items()},
            "knowledge_packs": [kp.to_dict() for kp in (result.knowledge_packs or [])],
            "start_time": result.start_time.isoformat() if getattr(result, "start_time", None) else None,
            "end_time": result.end_time.isoformat() if getattr(result, "end_time", None) else None
        }

        if not hasattr(self, 'iteration_results'):
            self.iteration_results = []

        self.iteration_results.append(result_data)

        # Also append a lightweight entry to execution_history for visibility in summaries
        try:
            iter_status = getattr(result, "status", "completed")
            iter_start = result.start_time.isoformat() if getattr(result, "start_time", None) else None
            iter_end = result.end_time.isoformat() if getattr(result, "end_time", None) else None
            iteration_state = IterationState(
                iteration_number=result.iteration,
                start_time=iter_start,
                end_time=iter_end,
                status=iter_status,
                phases={}
            )
            self.execution_history.append(iteration_state)
        except Exception:
            # If creating IterationState fails for any reason, we still persist raw result_data
            pass

        self._save_state()

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of execution state"""
        summary = {
            "total_iterations": len(self.execution_history),
            "current_iteration": None,
            "history": []
        }

        if self.current_iteration:
            summary["current_iteration"] = {
                "iteration_number": self.current_iteration.iteration_number,
                "status": self.current_iteration.status,
                "phases_completed": sum(
                    1 for p in self.current_iteration.phases.values()
                    if p.status == PhaseStatus.COMPLETED
                ),
                "phases_total": len(self.current_iteration.phases)
            }

        for iteration in self.execution_history:
            summary["history"].append({
                "iteration_number": iteration.iteration_number,
                "status": iteration.status,
                "start_time": iteration.start_time,
                "end_time": iteration.end_time
            })

        # Include any collected iteration_results for richer reporting
        if hasattr(self, 'iteration_results'):
            summary["iteration_results_count"] = len(self.iteration_results)

        return summary


if __name__ == "__main__":
    # Example usage
    print("="*80)
    print("DMAIC V3.0 - State Manager Test")
    print("="*80)
    
    state_dir = Path("test_state")
    manager = StateManager(state_dir)
    
    # Start iteration
    manager.start_iteration(1)
    print("\n[OK] Started iteration 1")
    
    # Start phase
    manager.start_phase("phase0_setup", 0, {"config": "test"})
    print("[OK] Started Phase 0")
    
    # Save checkpoint
    manager.save_checkpoint("phase0_setup", {"step": 1, "validated": True})
    print("[OK] Saved checkpoint")
    
    # End phase
    manager.end_phase("phase0_setup", PhaseStatus.COMPLETED, 
                     output_data={"result": "success"},
                     metrics={"checks_passed": 5})
    print("[OK] Completed Phase 0")
    
    # Check if can skip
    can_skip = manager.can_skip_phase("phase0_setup", {"config": "test"})
    print(f"[OK] Can skip phase: {can_skip}")
    
    # Get summary
    summary = manager.get_execution_summary()
    print(f"\n[OK] Execution Summary:")
    print(f"  Current Iteration: {summary['current_iteration']['iteration_number']}")
    print(f"  Phases Completed: {summary['current_iteration']['phases_completed']}")
    
    # End iteration
    manager.end_iteration("completed")
    print("\n[OK] Ended iteration 1")
    
    print("\n" + "="*80)
