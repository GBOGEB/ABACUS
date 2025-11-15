"""
Background Change Detector for DMAIC V3.3
Lightweight, non-blocking file change detection that runs continuously
"""

import json
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


class BackgroundChangeDetector:
    """
    Lightweight background change detector that runs continuously
    throughout the pipeline execution without blocking.
    
    Uses mtime-based detection for speed.
    """
    
    def __init__(self, workspace_root: Path, state_dir: Path):
        self.workspace_root = workspace_root
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        self.snapshot_file = state_dir / "background_snapshot.json"
        self.changes_file = state_dir / "background_changes.json"
        
        self.running = False
        self.thread = None
        self.snapshot_interval = 30  # seconds
        
    def start(self):
        """Start background change detection"""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.thread.start()
        print(f"[Background Change Detector] Started (snapshot every {self.snapshot_interval}s)")
        
    def stop(self):
        """Stop background change detection"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("[Background Change Detector] Stopped")
        
    def _detection_loop(self):
        """Main detection loop running in background"""
        while self.running:
            try:
                self._take_snapshot()
            except Exception as e:
                print(f"[Background Change Detector] Error: {e}")
            
            # Sleep in small intervals to allow quick shutdown
            for _ in range(self.snapshot_interval):
                if not self.running:
                    break
                time.sleep(1)
    
    def _take_snapshot(self):
        """Take a quick snapshot of file mtimes"""
        snapshot = {}
        changes = []
        
        # Load previous snapshot
        prev_snapshot = {}
        if self.snapshot_file.exists():
            try:
                with open(self.snapshot_file, 'r') as f:
                    prev_snapshot = json.load(f)
            except:
                pass
        
        # Quick scan of key directories only
        scan_dirs = [
            self.workspace_root / "DMAIC_V3",
            self.workspace_root / "DMAIC_V3_OUTPUT"
        ]
        
        file_count = 0
        for scan_dir in scan_dirs:
            if not scan_dir.exists():
                continue
                
            for file_path in scan_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                    
                # Skip large binary files
                if file_path.suffix.lower() in ['.pyc', '.pyo', '.so', '.dll', '.exe']:
                    continue
                
                try:
                    rel_path = str(file_path.relative_to(self.workspace_root))
                    mtime = file_path.stat().st_mtime
                    
                    snapshot[rel_path] = mtime
                    
                    # Detect changes
                    if rel_path not in prev_snapshot:
                        changes.append({'path': rel_path, 'type': 'added'})
                    elif abs(mtime - prev_snapshot.get(rel_path, 0)) > 1:
                        changes.append({'path': rel_path, 'type': 'modified'})
                    
                    file_count += 1
                    
                    # Limit scan to prevent blocking
                    if file_count > 10000:
                        break
                        
                except:
                    pass
        
        # Detect deletions
        for prev_path in prev_snapshot:
            if prev_path not in snapshot:
                changes.append({'path': prev_path, 'type': 'deleted'})
        
        # Save snapshot
        try:
            with open(self.snapshot_file, 'w') as f:
                json.dump(snapshot, f)
                
            # Save changes
            if changes:
                change_data = {
                    'timestamp': datetime.now().isoformat(),
                    'total_changes': len(changes),
                    'changes': changes
                }
                with open(self.changes_file, 'w') as f:
                    json.dump(change_data, f, indent=2)
        except:
            pass
    
    def get_summary(self) -> Dict[str, Any]:
        """Get current change summary"""
        if not self.changes_file.exists():
            return {'total': 0, 'added': 0, 'modified': 0, 'deleted': 0}
        
        try:
            with open(self.changes_file, 'r') as f:
                data = json.load(f)
            
            changes = data.get('changes', [])
            return {
                'total': len(changes),
                'added': sum(1 for c in changes if c['type'] == 'added'),
                'modified': sum(1 for c in changes if c['type'] == 'modified'),
                'deleted': sum(1 for c in changes if c['type'] == 'deleted'),
                'timestamp': data.get('timestamp', '')
            }
        except:
            return {'total': 0, 'added': 0, 'modified': 0, 'deleted': 0}
