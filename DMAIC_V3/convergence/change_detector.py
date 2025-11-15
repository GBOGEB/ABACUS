"""
DMAIC V3.3 - Change Detection Module
Version: 3.3.0
Updated: 2025-11-12

Detects and tracks file changes between iterations to enable:
- Incremental processing
- Change-based re-analysis
- Version tracking
- Input modification detection
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class FileChange:
    """Represents a file change"""
    path: str
    change_type: str  # 'added', 'modified', 'deleted'
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
    old_size: Optional[int] = None
    new_size: Optional[int] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class ChangeDetector:
    """
    Detects changes in workspace files between iterations
    
    Tracks:
    - File additions
    - File modifications (content hash changes)
    - File deletions
    - File size changes
    """
    
    def __init__(self, workspace_root: Path, state_dir: Path):
        """
        Initialize change detector
        
        Args:
            workspace_root: Root directory to monitor
            state_dir: Directory to store change tracking state
        """
        self.workspace_root = workspace_root
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        self.snapshot_file = state_dir / "file_snapshot.json"
        self.changes_file = state_dir / "detected_changes.json"
        
        self.current_snapshot: Dict[str, Dict[str, Any]] = {}
        self.previous_snapshot: Dict[str, Dict[str, Any]] = {}
        
    def compute_file_hash(self, file_path: Path) -> str:
        """
        Compute SHA256 hash of file content

        Args:
            file_path: Path to file

        Returns:
            Hex digest of file hash
        """
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except (OSError, PermissionError, UnicodeDecodeError):
            return ""
        except Exception:
            return ""

    def create_snapshot(self, files: List[Path]) -> Dict[str, Dict[str, Any]]:
        """
        Create snapshot of current file states

        Args:
            files: List of files to snapshot

        Returns:
            Dictionary mapping file paths to their metadata
        """
        snapshot = {}
        total_files = len(files)
        processed = 0

        print(f"\n[Change Detection] Analyzing file changes...")

        for file_path in files:
            if not file_path.exists():
                continue

            processed += 1
            if processed % 5000 == 0:
                print(f"  Progress: {processed}/{total_files} files analyzed...")

            try:
                rel_path = str(file_path.relative_to(self.workspace_root))
                stat = file_path.stat()

                snapshot[rel_path] = {
                    'hash': self.compute_file_hash(file_path),
                    'size': stat.st_size,
                    'mtime': stat.st_mtime,
                    'timestamp': datetime.now().isoformat()
                }
            except Exception:
                pass

        print(f"  Completed: {processed}/{total_files} files analyzed")
        return snapshot
    
    def load_previous_snapshot(self) -> Dict[str, Dict[str, Any]]:
        """
        Load previous snapshot from disk
        
        Returns:
            Previous snapshot dictionary
        """
        if not self.snapshot_file.exists():
            return {}
            
        try:
            with open(self.snapshot_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"  [!] Error loading previous snapshot: {e}")
            return {}

    def save_snapshot(self, snapshot: Dict[str, Dict[str, Any]]):
        """
        Save snapshot to disk

        Args:
            snapshot: Snapshot dictionary to save
        """
        try:
            with open(self.snapshot_file, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, indent=2)
        except Exception as e:
            print(f"  [!] Error saving snapshot: {e}")

    def detect_changes(self, current_files: List[Path]) -> List[FileChange]:
        """
        Detect changes between previous and current snapshots

        Args:
            current_files: List of current files to check

        Returns:
            List of detected changes
        """
        print("\n[Change Detection] Quick scan mode (mtime-based)...")

        self.previous_snapshot = self.load_previous_snapshot()
        self.current_snapshot = {}

        changes = []
        current_paths = set()

        for file_path in current_files:
            if not file_path.exists():
                continue

            try:
                rel_path = str(file_path.relative_to(self.workspace_root))
                current_paths.add(rel_path)
                stat = file_path.stat()

                self.current_snapshot[rel_path] = {
                    'size': stat.st_size,
                    'mtime': stat.st_mtime,
                    'timestamp': datetime.now().isoformat()
                }

                if rel_path not in self.previous_snapshot:
                    changes.append(FileChange(
                        path=rel_path,
                        change_type='added',
                        new_size=stat.st_size
                    ))
                else:
                    prev = self.previous_snapshot[rel_path]
                    if (stat.st_size != prev.get('size') or
                        abs(stat.st_mtime - prev.get('mtime', 0)) > 1):
                        changes.append(FileChange(
                            path=rel_path,
                            change_type='modified',
                            old_size=prev.get('size'),
                            new_size=stat.st_size
                        ))
            except Exception:
                pass

        for prev_path in self.previous_snapshot:
            if prev_path not in current_paths:
                changes.append(FileChange(
                    path=prev_path,
                    change_type='deleted',
                    old_size=self.previous_snapshot[prev_path].get('size')
                ))

        self.save_snapshot(self.current_snapshot)
        self._save_changes(changes)

        print(f"  Detected {len(changes)} changes")
        return changes

    def _save_changes(self, changes: List[FileChange]):
        """Save detected changes to disk"""
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'total_changes': len(changes),
                'changes': [asdict(c) for c in changes]
            }
            with open(self.changes_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"  [!] Error saving changes: {e}")

    def get_change_summary(self) -> Dict[str, Any]:
        """Get summary of detected changes"""
        if not self.changes_file.exists():
            return {'total': 0, 'added': 0, 'modified': 0, 'deleted': 0}

        try:
            with open(self.changes_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            changes = data.get('changes', [])
            return {
                'total': len(changes),
                'added': sum(1 for c in changes if c['change_type'] == 'added'),
                'modified': sum(1 for c in changes if c['change_type'] == 'modified'),
                'deleted': sum(1 for c in changes if c['change_type'] == 'deleted'),
                'timestamp': data.get('timestamp', '')
            }
        except:
            return {'total': 0, 'added': 0, 'modified': 0, 'deleted': 0}
        
        Args:
            file_types: Set of file extensions to filter (e.g., {'.py', '.md'})
            
        Returns:
            List of changed file paths
        """
        if not self.changes_file.exists():
            return []
            
        try:
            with open(self.changes_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            changed_files = []
            for change in data.get('changes', []):
                if change['change_type'] != 'deleted':
                    path = change['path']
                    if file_types is None or Path(path).suffix in file_types:
                        changed_files.append(path)
                        
            return changed_files
            
        except Exception as e:
            print(f"  [!] Error loading changes: {e}")
            return []
    
    def has_changes(self) -> bool:
        """Check if any changes were detected"""
        if not self.changes_file.exists():
            return True  # First run, consider everything changed
            
        try:
            with open(self.changes_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('total_changes', 0) > 0
        except:
            return True
    
    def get_change_summary(self) -> Dict[str, Any]:
        """Get summary of detected changes"""
        if not self.changes_file.exists():
            return {'total': 0, 'added': 0, 'modified': 0, 'deleted': 0}
            
        try:
            with open(self.changes_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            changes = data.get('changes', [])
            return {
                'total': len(changes),
                'added': sum(1 for c in changes if c['change_type'] == 'added'),
                'modified': sum(1 for c in changes if c['change_type'] == 'modified'),
                'deleted': sum(1 for c in changes if c['change_type'] == 'deleted'),
                'timestamp': data.get('timestamp', '')
            }
        except:
            return {'total': 0, 'added': 0, 'modified': 0, 'deleted': 0}
