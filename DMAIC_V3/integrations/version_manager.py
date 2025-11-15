#!/usr/bin/env python3
"""
DMAIC V3 - Version Manager
Version: 3.2.0
Created: 2025-11-11T23:15:00Z
Updated: 2025-11-11T23:15:00Z

Semantic versioning automation with timestamp alignment.
Manages version bumping, changelog integration, and release tagging.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


VERSION = "3.2.0"


class BumpType(Enum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


@dataclass
class VersionInfo:
    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None

    def __str__(self) -> str:
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        return version

    def __lt__(self, other: 'VersionInfo') -> bool:
        if not isinstance(other, VersionInfo):
            return NotImplemented
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __le__(self, other: 'VersionInfo') -> bool:
        if not isinstance(other, VersionInfo):
            return NotImplemented
        return (self.major, self.minor, self.patch) <= (other.major, other.minor, other.patch)

    def __gt__(self, other: 'VersionInfo') -> bool:
        if not isinstance(other, VersionInfo):
            return NotImplemented
        return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)

    def __ge__(self, other: 'VersionInfo') -> bool:
        if not isinstance(other, VersionInfo):
            return NotImplemented
        return (self.major, self.minor, self.patch) >= (other.major, other.minor, other.patch)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VersionInfo):
            return NotImplemented
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    @classmethod
    def parse(cls, version_string: str) -> 'VersionInfo':
        pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$'
        match = re.match(pattern, version_string)

        if not match:
            raise ValueError(f"Invalid version string: {version_string}")

        major, minor, patch, prerelease = match.groups()
        return cls(int(major), int(minor), int(patch), prerelease)

    def bump(self, bump_type: BumpType) -> 'VersionInfo':
        if bump_type == BumpType.MAJOR:
            return VersionInfo(self.major + 1, 0, 0)
        elif bump_type == BumpType.MINOR:
            return VersionInfo(self.major, self.minor + 1, 0)
        elif bump_type == BumpType.PATCH:
            return VersionInfo(self.major, self.minor, self.patch + 1)
        else:
            raise ValueError(f"Unknown bump type: {bump_type}")


@dataclass
class VersionHistory:
    version: str
    timestamp: str
    iteration: int
    changes: List[str]
    convergence_score: float
    maturity_level: int


class VersionManager:
    def __init__(self, workspace_path: Optional[Path] = None):
        self.workspace_path = workspace_path or Path.cwd()
        self.config_path = self.workspace_path / "DMAIC_V3" / "config.py"
        self.version_history_path = self.workspace_path / "config" / "version_history.json"
        
        self.history: List[VersionHistory] = []
        self.load_history()
    
    def get_current_version(self) -> VersionInfo:
        if not self.config_path.exists():
            return VersionInfo(3, 2, 0)
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                return VersionInfo.parse(match.group(1))
        except Exception as e:
            print(f"[WARN]️  Failed to parse version from config: {e}")
        
        return VersionInfo(3, 2, 0)
    
    def update_version_in_file(self, file_path: Path, new_version: VersionInfo) -> bool:
        if not file_path.exists():
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            patterns = [
                (r'VERSION\s*=\s*["\'][^"\']+["\']', f'VERSION = "{new_version}"'),
                (r'version:\s*["\'][^"\']+["\']', f'version: "{new_version}"'),
                (r'version:\s*[\d\.]+', f'version: {new_version}'),
                (r'Version:\s*[\d\.]+', f'Version: {new_version}'),
            ]
            
            modified = False
            for pattern, replacement in patterns:
                if re.search(pattern, content):
                    content = re.sub(pattern, replacement, content)
                    modified = True
            
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
        
        except Exception as e:
            print(f"[WARN]️  Failed to update version in {file_path}: {e}")
        
        return False
    
    def bump_version(self, bump_type: BumpType, changes: Optional[List[str]] = None) -> VersionInfo:
        current = self.get_current_version()
        new_version = current.bump(bump_type)
        
        files_to_update = [
            self.workspace_path / "DMAIC_V3" / "config.py",
            self.workspace_path / "config" / "maturity_config.yaml",
            self.workspace_path / "config" / "task_definitions.yaml",
        ]
        
        for file_path in files_to_update:
            if file_path.exists():
                self.update_version_in_file(file_path, new_version)
                print(f"[OK] Updated version in: {file_path.name}")
        
        self.record_version(new_version, changes or [])
        
        return new_version
    
    def load_history(self) -> None:
        if not self.version_history_path.exists():
            self.history = []
            return
        
        try:
            with open(self.version_history_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.history = [VersionHistory(**item) for item in data]
        except Exception as e:
            print(f"[WARN]️  Failed to load version history: {e}")
            self.history = []
    
    def save_history(self) -> None:
        self.version_history_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.version_history_path, 'w', encoding='utf-8') as f:
            json.dump(
                [asdict(item) for item in self.history],
                f,
                indent=2,
                ensure_ascii=False
            )
    
    def record_version(self, version: VersionInfo, changes: List[str], 
                      iteration: Optional[int] = None, convergence: Optional[float] = None,
                      maturity: Optional[int] = None) -> None:
        
        if iteration is None:
            iteration = self.get_current_iteration()
        if convergence is None:
            convergence = self.get_convergence_score()
        if maturity is None:
            maturity = self.get_maturity_level()
        
        history_entry = VersionHistory(
            version=str(version),
            timestamp=datetime.now().isoformat(),
            iteration=iteration,
            changes=changes,
            convergence_score=convergence,
            maturity_level=maturity
        )
        
        self.history.append(history_entry)
        self.save_history()
    
    def get_current_iteration(self) -> int:
        tasks_path = self.workspace_path / "config" / "task_definitions.yaml"
        if tasks_path.exists():
            try:
                import yaml
                with open(tasks_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    return data.get('metadata', {}).get('iteration', 0)
            except Exception:
                pass
        return 0
    
    def get_convergence_score(self) -> float:
        tasks_path = self.workspace_path / "config" / "task_definitions.yaml"
        if tasks_path.exists():
            try:
                import yaml
                with open(tasks_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    return data.get('metadata', {}).get('convergence_score', 0.0)
            except Exception:
                pass
        return 0.0
    
    def get_maturity_level(self) -> int:
        tasks_path = self.workspace_path / "config" / "task_definitions.yaml"
        if tasks_path.exists():
            try:
                import yaml
                with open(tasks_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    return data.get('metadata', {}).get('maturity_level', 0)
            except Exception:
                pass
        return 0
    
    def suggest_bump_type(self, changes: List[str]) -> BumpType:
        major_keywords = ['breaking', 'incompatible', 'major', 'rewrite', 'redesign']
        minor_keywords = ['feature', 'add', 'new', 'enhance', 'implement']
        
        changes_lower = [c.lower() for c in changes]
        
        if any(any(keyword in change for keyword in major_keywords) for change in changes_lower):
            return BumpType.MAJOR
        elif any(any(keyword in change for keyword in minor_keywords) for change in changes_lower):
            return BumpType.MINOR
        else:
            return BumpType.PATCH
    
    def generate_changelog_entry(self, version: VersionInfo, changes: List[str]) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d")
        
        entry = f"## [{version}] - {timestamp}\n\n"
        
        if changes:
            entry += "### Changes\n\n"
            for change in changes:
                entry += f"- {change}\n"
        else:
            entry += "- General improvements and bug fixes\n"
        
        entry += "\n"
        return entry
    
    def update_changelog(self, version: VersionInfo, changes: List[str]) -> None:
        changelog_path = self.workspace_path / "CHANGELOG.md"
        entry = self.generate_changelog_entry(version, changes)
        
        if changelog_path.exists():
            with open(changelog_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            insert_index = 0
            for i, line in enumerate(lines):
                if line.startswith('## ['):
                    insert_index = i
                    break
            
            if insert_index > 0:
                lines.insert(insert_index, entry)
                new_content = '\n'.join(lines)
            else:
                new_content = entry + content
        else:
            new_content = f"# Changelog\n\n{entry}"
        
        with open(changelog_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"[OK] Updated CHANGELOG.md")
    
    def print_status(self) -> None:
        current = self.get_current_version()
        iteration = self.get_current_iteration()
        convergence = self.get_convergence_score()
        maturity = self.get_maturity_level()
        
        print("=" * 78)
        print("DMAIC V3 - VERSION MANAGER STATUS")
        print("=" * 78)
        print(f"Current Version: {current}")
        print(f"Iteration: {iteration}")
        print(f"Convergence Score: {convergence}/100")
        print(f"Maturity Level: {maturity}")
        print()
        
        if self.history:
            print("VERSION HISTORY")
            print("-" * 78)
            for entry in self.history[-5:]:
                print(f"{entry.version:10} | {entry.timestamp[:10]} | "
                      f"Iter {entry.iteration} | Conv {entry.convergence_score:.0f}")
                if entry.changes:
                    for change in entry.changes[:2]:
                        print(f"  - {change}")
                    if len(entry.changes) > 2:
                        print(f"  ... and {len(entry.changes) - 2} more changes")
            if len(self.history) > 5:
                print(f"... and {len(self.history) - 5} more versions")
        
        print("=" * 78)


def main():
    import sys
    
    manager = VersionManager()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'status':
            manager.print_status()
        
        elif command == 'current':
            print(manager.get_current_version())
        
        elif command == 'bump' and len(sys.argv) >= 3:
            bump_type_str = sys.argv[2].upper()
            bump_type = BumpType[bump_type_str]
            
            changes = []
            if len(sys.argv) > 3:
                changes = sys.argv[3:]
            
            new_version = manager.bump_version(bump_type, changes)
            print(f"[OK] Version bumped to: {new_version}")
        
        elif command == 'suggest' and len(sys.argv) > 2:
            changes = sys.argv[2:]
            suggested = manager.suggest_bump_type(changes)
            print(f"Suggested bump type: {suggested.value}")
        
        else:
            print("Usage:")
            print("  python version_manager.py status")
            print("  python version_manager.py current")
            print("  python version_manager.py bump <MAJOR|MINOR|PATCH> [changes...]")
            print("  python version_manager.py suggest <change1> [change2...]")
    
    else:
        manager.print_status()


if __name__ == '__main__':
    main()
