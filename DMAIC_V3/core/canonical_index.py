from typing import Any
"""
DMAIC V3 - Canonical Index System
Global naming, versioning, and metadata standards for all artifacts

Version: 1.0.0
Date: 2025-01-12
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict, field
from enum import Enum


class ArtifactType(Enum):
    """Types of artifacts"""
    FILE = "file"
    MODULE = "module"
    PACKAGE = "package"
    EXECUTION = "execution"
    REPORT = "report"
    DATABASE = "database"
    CONFIG = "config"
    NOTEBOOK = "notebook"
    DASHBOARD = "dashboard"


class VersionStatus(Enum):
    """Version status"""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class CanonicalVersion:
    """Canonical version information"""
    major: int
    minor: int
    patch: int
    build: Optional[str] = None
    prerelease: Optional[str] = None

    def __str__(self) -> str:
        """Format as semantic version string"""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    @classmethod
    def from_string(cls, version_str: str) -> 'CanonicalVersion':
        """Parse version string"""
        # Handle build metadata
        if '+' in version_str:
            version_str, build = version_str.split('+', 1)
        else:
            build = None

        # Handle prerelease
        if '-' in version_str:
            version_str, prerelease = version_str.split('-', 1)
        else:
            prerelease = None

        # Parse major.minor.patch
        parts = version_str.split('.')
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0

        return cls(major=major, minor=minor, patch=patch,
                  build=build, prerelease=prerelease)


@dataclass
class CanonicalMetadata:
    """Canonical metadata for artifacts"""
    canonical_name: str  # e.g., "dmaic_v3_engine"
    display_name: str  # e.g., "DMAIC V3 Engine"
    version: CanonicalVersion
    artifact_type: str
    status: str
    created_at: str
    updated_at: str
    author: str = "DMAIC V3 System"
    description: str = ""
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    related_artifacts: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    rank_position: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['version'] = str(self.version)
        return data


@dataclass
class IndexEntry:
    """Entry in canonical index"""
    canonical_id: str  # Unique identifier
    canonical_name: str
    display_name: str
    version: str
    artifact_type: str
    file_path: str
    status: str
    metadata: CanonicalMetadata
    checksum: str  # SHA256 hash
    size_bytes: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['metadata'] = self.metadata.to_dict()
        return data


class CanonicalIndexSystem:
    """
    Canonical index system for DMAIC V3

    Features:
    - Global naming conventions
    - Semantic versioning
    - Metadata standards
    - JSON/YAML index files
    - Artifact tracking
    - Version history
    - Dependency management
    """

    def __init__(self, workspace_root: Path):
        """
        Initialize canonical index system

        Args:
            workspace_root: Root directory of workspace
        """
        self.workspace_root = Path(workspace_root)
        self.index_dir = self.workspace_root / ".dmaic" / "indexes"
        self.index_dir.mkdir(parents=True, exist_ok=True)

        self.master_index_json = self.index_dir / "master_index.json"
        self.master_index_yaml = self.index_dir / "master_index.yaml"

        self.version = CanonicalVersion(1, 0, 0)
        self.timestamp = datetime.now().isoformat()

        # Naming conventions
        self.naming_rules = {
            'canonical_name': {
                'pattern': r'^[a-z][a-z0-9_]*$',
                'description': 'Lowercase with underscores, starts with letter'
            },
            'display_name': {
                'pattern': r'^[A-Z].*$',
                'description': 'Human-readable, starts with capital letter'
            },
            'version': {
                'pattern': r'^\d+\.\d+\.\d+(-[a-z0-9]+)?(\+[a-z0-9]+)?$',
                'description': 'Semantic versioning: major.minor.patch[-prerelease][+build]'
            }
        }

        self.index: Dict[str, IndexEntry] = {}
        self._load_index()

    def _load_index(self) -> Any:
        """Load master index from JSON"""
        if self.master_index_json.exists():
            with open(self.master_index_json, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for entry_data in data.get('entries', []):
                metadata_data = entry_data['metadata']
                version = CanonicalVersion.from_string(metadata_data['version'])

                metadata = CanonicalMetadata(
                    canonical_name=metadata_data['canonical_name'],
                    display_name=metadata_data['display_name'],
                    version=version,
                    artifact_type=metadata_data['artifact_type'],
                    status=metadata_data['status'],
                    created_at=metadata_data['created_at'],
                    updated_at=metadata_data['updated_at'],
                    author=metadata_data.get('author', 'DMAIC V3 System'),
                    description=metadata_data.get('description', ''),
                    tags=metadata_data.get('tags', []),
                    dependencies=metadata_data.get('dependencies', []),
                    related_artifacts=metadata_data.get('related_artifacts', []),
                    quality_score=metadata_data.get('quality_score', 0.0),
                    rank_position=metadata_data.get('rank_position', 0)
                )

                entry = IndexEntry(
                    canonical_id=entry_data['canonical_id'],
                    canonical_name=entry_data['canonical_name'],
                    display_name=entry_data['display_name'],
                    version=entry_data['version'],
                    artifact_type=entry_data['artifact_type'],
                    file_path=entry_data['file_path'],
                    status=entry_data['status'],
                    metadata=metadata,
                    checksum=entry_data['checksum'],
                    size_bytes=entry_data['size_bytes'],
                    timestamp=entry_data['timestamp']
                )

                self.index[entry.canonical_id] = entry

    def _save_index(self) -> Any:
        """Save master index to JSON and YAML"""
        data = {
            'metadata': {
                'version': str(self.version),
                'generated_at': datetime.now().isoformat(),
                'workspace_root': str(self.workspace_root),
                'total_entries': len(self.index)
            },
            'naming_rules': self.naming_rules,
            'entries': [entry.to_dict() for entry in self.index.values()]
        }

        # Save JSON
        with open(self.master_index_json, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        # Save YAML
        with open(self.master_index_yaml, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def register_artifact(self, file_path: Path,
                         canonical_name: str,
                         display_name: str,
                         artifact_type: ArtifactType,
                         version: Optional[CanonicalVersion] = None,
                         description: str = "",
                         tags: Optional[List[str]] = None,
                         dependencies: Optional[List[str]] = None) -> IndexEntry:
        """
        Register artifact in canonical index

        Args:
            file_path: Path to artifact file
            canonical_name: Canonical name (lowercase_with_underscores)
            display_name: Display name (Human Readable)
            artifact_type: Type of artifact
            version: Version (default: 1.0.0)
            description: Description of artifact
            tags: Tags for categorization
            dependencies: List of dependencies

        Returns:
            IndexEntry object
        """
        if version is None:
            version = CanonicalVersion(1, 0, 0)

        # Generate canonical ID
        canonical_id = self._generate_canonical_id(canonical_name, version)

        # Calculate checksum
        checksum = self._calculate_checksum(file_path)

        # Get file size
        size_bytes = file_path.stat().st_size if file_path.exists() else 0

        # Create metadata
        metadata = CanonicalMetadata(
            canonical_name=canonical_name,
            display_name=display_name,
            version=version,
            artifact_type=artifact_type.value,
            status=VersionStatus.ACTIVE.value,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            description=description,
            tags=tags or [],
            dependencies=dependencies or []
        )

        # Create index entry
        entry = IndexEntry(
            canonical_id=canonical_id,
            canonical_name=canonical_name,
            display_name=display_name,
            version=str(version),
            artifact_type=artifact_type.value,
            file_path=str(file_path),
            status=VersionStatus.ACTIVE.value,
            metadata=metadata,
            checksum=checksum,
            size_bytes=size_bytes,
            timestamp=datetime.now().isoformat()
        )

        # Add to index
        self.index[canonical_id] = entry
        self._save_index()

        return entry

    def update_artifact(self, canonical_id: str,
                       version: Optional[CanonicalVersion] = None,
                       status: Optional[VersionStatus] = None,
                       quality_score: Optional[float] = None,
                       rank_position: Optional[int] = None):
        """
        Update artifact in index

        Args:
            canonical_id: Canonical ID of artifact
            version: New version
            status: New status
            quality_score: Quality score
            rank_position: Rank position
        """
        if canonical_id not in self.index:
            raise ValueError(f"Artifact not found: {canonical_id}")

        entry = self.index[canonical_id]

        if version:
            entry.version = str(version)
            entry.metadata.version = version

        if status:
            entry.status = status.value
            entry.metadata.status = status.value

        if quality_score is not None:
            entry.metadata.quality_score = quality_score

        if rank_position is not None:
            entry.metadata.rank_position = rank_position

        entry.metadata.updated_at = datetime.now().isoformat()
        entry.timestamp = datetime.now().isoformat()

        # Recalculate checksum
        file_path = Path(entry.file_path)
        if file_path.exists():
            entry.checksum = self._calculate_checksum(file_path)
            entry.size_bytes = file_path.stat().st_size

        self._save_index()

    def get_artifact(self, canonical_id: str) -> Optional[IndexEntry]:
        """Get artifact by canonical ID"""
        return self.index.get(canonical_id)

    def search_artifacts(self,
                        artifact_type: Optional[ArtifactType] = None,
                        status: Optional[VersionStatus] = None,
                        tags: Optional[List[str]] = None,
                        min_quality_score: Optional[float] = None) -> List[IndexEntry]:
        """
        Search artifacts by criteria

        Args:
            artifact_type: Filter by artifact type
            status: Filter by status
            tags: Filter by tags (any match)
            min_quality_score: Minimum quality score

        Returns:
            List of matching IndexEntry objects
        """
        results = []

        for entry in self.index.values():
            # Filter by artifact type
            if artifact_type and entry.artifact_type != artifact_type.value:
                continue

            # Filter by status
            if status and entry.status != status.value:
                continue

            # Filter by tags
            if tags and not any(tag in entry.metadata.tags for tag in tags):
                continue

            # Filter by quality score
            if min_quality_score and entry.metadata.quality_score < min_quality_score:
                continue

            results.append(entry)

        return results

    def get_version_history(self, canonical_name: str) -> List[IndexEntry]:
        """
        Get version history for an artifact

        Args:
            canonical_name: Canonical name of artifact

        Returns:
            List of IndexEntry objects sorted by version (newest first)
        """
        entries = [
            entry for entry in self.index.values()
            if entry.canonical_name == canonical_name
        ]

        # Sort by version (newest first)
        entries.sort(
            key=lambda e: CanonicalVersion.from_string(e.version),
            reverse=True
        )

        return entries

    def generate_canonical_name(self, display_name: str) -> str:
        """
        Generate canonical name from display name

        Args:
            display_name: Human-readable display name

        Returns:
            Canonical name (lowercase_with_underscores)
        """
        # Convert to lowercase
        canonical = display_name.lower()

        # Replace spaces and special characters with underscores
        canonical = ''.join(c if c.isalnum() else '_' for c in canonical)

        # Remove consecutive underscores
        while '__' in canonical:
            canonical = canonical.replace('__', '_')

        # Remove leading/trailing underscores
        canonical = canonical.strip('_')

        # Ensure starts with letter
        if canonical and not canonical[0].isalpha():
            canonical = 'artifact_' + canonical

        return canonical

    def generate_display_name(self, canonical_name: str) -> str:
        """
        Generate display name from canonical name

        Args:
            canonical_name: Canonical name

        Returns:
            Display name (Human Readable)
        """
        # Split by underscores
        words = canonical_name.split('_')

        # Capitalize each word
        display = ' '.join(word.capitalize() for word in words)

        return display

    def export_index_report(self, output_path: Path, format: str = 'json'):
        """
        Export index report

        Args:
            output_path: Path to save report
            format: Format ('json' or 'yaml')
        """
        report = {
            'metadata': {
                'version': str(self.version),
                'generated_at': datetime.now().isoformat(),
                'workspace_root': str(self.workspace_root),
                'total_entries': len(self.index)
            },
            'statistics': {
                'by_type': self._count_by_field('artifact_type'),
                'by_status': self._count_by_field('status'),
                'avg_quality_score': sum(e.metadata.quality_score for e in self.index.values()) / len(self.index) if self.index else 0.0
            },
            'entries': [entry.to_dict() for entry in sorted(
                self.index.values(),
                key=lambda e: e.metadata.rank_position if e.metadata.rank_position > 0 else 999999
            )]
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
        elif format == 'yaml':
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(report, f, default_flow_style=False, sort_keys=False)

    def _generate_canonical_id(self, canonical_name: str,
                              version: CanonicalVersion) -> str:
        """Generate unique canonical ID"""
        return f"{canonical_name}__v{version}"

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        import hashlib

        if not file_path.exists():
            return ""

        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)

        return sha256.hexdigest()

    def _count_by_field(self, field: str) -> Dict[str, int]:
        """Count entries by field value"""
        counts = {}
        for entry in self.index.values():
            value = getattr(entry, field, None)
            if value:
                counts[value] = counts.get(value, 0) + 1
        return counts

    def export_to_json(self, output_path: Path):
        """
        Export index to JSON format

        Args:
            output_path: Path to save JSON file
        """
        self.export_index_report(output_path, format='json')

    def export_to_yaml(self, output_path: Path):
        """
        Export index to YAML format

        Args:
            output_path: Path to save YAML file
        """
        self.export_index_report(output_path, format='yaml')
