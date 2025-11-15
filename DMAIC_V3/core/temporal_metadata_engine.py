from typing import Any
"""
DMAIC V3 - Temporal Metadata Engine
Comprehensive tracking system for file/folder hierarchy, execution metadata, and digital twin

Features:
- Real-time metadata tracking with timestamps
- File/folder hierarchy mapping
- Bidirectional input/output tracking
- CI/CD quality control integration
- Digital twin provenance
- Task JSON generation
"""

import json
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum


class FileType(Enum):
    """TODO: Add class description"""

    PYTHON = "python"
    JSON = "json"
    YAML = "yaml"
    MARKDOWN = "markdown"
    CONFIG = "config"
    GITIGNORE = "gitignore"
    README = "readme"
    REQUIREMENTS = "requirements"
    SQL = "sql"
    DATABASE = "database"
    LOG = "log"
    WORD = "word"
    EXCEL = "excel"
    POWERPOINT = "powerpoint"
    GO = "go"
    VBA = "vba"
    OTHER = "other"


class ExecutionPhase(Enum):
    """TODO: Add class description"""

    DEFINE = "define"
    MEASURE = "measure"
    ANALYZE = "analyze"
    IMPROVE = "improve"
    CONTROL = "control"


@dataclass
class FileMetadata:
    """TODO: Add class description"""

    file_path: str
    file_type: FileType
    size_bytes: int
    hash_sha256: str
    created_at: str
    modified_at: str
    accessed_at: str
    parent_folder: str
    depth_level: int
    is_main_entry: bool = False
    dependencies: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    linked_outputs: List[str] = field(default_factory=list)
    linked_inputs: List[str] = field(default_factory=list)
    execution_count: int = 0
    last_execution: Optional[str] = None
    quality_score: float = 0.0
    test_coverage: float = 0.0


@dataclass
class FolderMetadata:
    """TODO: Add class description"""

    folder_path: str
    depth_level: int
    file_count: int
    subfolder_count: int
    total_size_bytes: int
    created_at: str
    modified_at: str
    purpose: str
    is_venv: bool = False
    is_git: bool = False
    is_config: bool = False
    is_source: bool = False
    is_test: bool = False
    is_output: bool = False
    canonical_index: Optional[str] = None


@dataclass
class ExecutionMetadata:
    """TODO: Add class description"""

    execution_id: str
    timestamp: str
    phase: ExecutionPhase
    iteration: int
    input_files: List[str]
    output_files: List[str]
    duration_seconds: float
    status: str
    metrics: Dict[str, Any]
    logs: List[str]
    errors: List[str]
    warnings: List[str]
    provenance_chain: List[str]


@dataclass
class DigitalTwinState:
    """TODO: Add class description"""

    twin_id: str
    source_workspace: str
    timestamp: str
    file_count: int
    folder_count: int
    total_size_bytes: int
    quality_metrics: Dict[str, float]
    execution_history: List[str]
    improvement_actions: List[Dict[str, Any]]
    convergence_status: Dict[str, Any]


class TemporalMetadataEngine:
    """
    Temporal Metadata Engine for comprehensive workspace tracking
    
    Tracks:
    - File/folder hierarchy with temporal metadata
    - Execution provenance and digital twin state
    - Bidirectional input/output relationships
    - CI/CD quality metrics
    """
    
    def __init__(self, workspace_root: Path, db_path: Optional[Path] = None):
        """TODO: Add function description"""

        self.workspace_root = Path(workspace_root)
        self.db_path = db_path or (self.workspace_root / ".dmaic" / "temporal_metadata.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
        self.file_type_map = self._build_file_type_map()
        
    def _init_database(self) -> Any:
        """Initialize SQLite database with comprehensive schema"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_metadata (
                file_path TEXT PRIMARY KEY,
                file_type TEXT,
                size_bytes INTEGER,
                hash_sha256 TEXT,
                created_at TEXT,
                modified_at TEXT,
                accessed_at TEXT,
                parent_folder TEXT,
                depth_level INTEGER,
                is_main_entry INTEGER,
                dependencies TEXT,
                imports TEXT,
                exports TEXT,
                functions TEXT,
                classes TEXT,
                linked_outputs TEXT,
                linked_inputs TEXT,
                execution_count INTEGER,
                last_execution TEXT,
                quality_score REAL,
                test_coverage REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS folder_metadata (
                folder_path TEXT PRIMARY KEY,
                depth_level INTEGER,
                file_count INTEGER,
                subfolder_count INTEGER,
                total_size_bytes INTEGER,
                created_at TEXT,
                modified_at TEXT,
                purpose TEXT,
                is_venv INTEGER,
                is_git INTEGER,
                is_config INTEGER,
                is_source INTEGER,
                is_test INTEGER,
                is_output INTEGER,
                canonical_index TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_metadata (
                execution_id TEXT PRIMARY KEY,
                timestamp TEXT,
                phase TEXT,
                iteration INTEGER,
                input_files TEXT,
                output_files TEXT,
                duration_seconds REAL,
                status TEXT,
                metrics TEXT,
                logs TEXT,
                errors TEXT,
                warnings TEXT,
                provenance_chain TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS digital_twin_state (
                twin_id TEXT PRIMARY KEY,
                source_workspace TEXT,
                timestamp TEXT,
                file_count INTEGER,
                folder_count INTEGER,
                total_size_bytes INTEGER,
                quality_metrics TEXT,
                execution_history TEXT,
                improvement_actions TEXT,
                convergence_status TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bidirectional_links (
                link_id TEXT PRIMARY KEY,
                source_file TEXT,
                target_file TEXT,
                link_type TEXT,
                timestamp TEXT,
                metadata TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        
    def _build_file_type_map(self) -> Dict[str, FileType]:
        """Build file extension to FileType mapping"""
        return {
            '.py': FileType.PYTHON,
            '.json': FileType.JSON,
            '.yaml': FileType.YAML,
            '.yml': FileType.YAML,
            '.md': FileType.MARKDOWN,
            '.cfg': FileType.CONFIG,
            '.conf': FileType.CONFIG,
            '.ini': FileType.CONFIG,
            '.gitignore': FileType.GITIGNORE,
            'README': FileType.README,
            'requirements.txt': FileType.REQUIREMENTS,
            '.sql': FileType.SQL,
            '.db': FileType.DATABASE,
            '.sqlite': FileType.DATABASE,
            '.log': FileType.LOG,
            '.docx': FileType.WORD,
            '.doc': FileType.WORD,
            '.xlsx': FileType.EXCEL,
            '.xls': FileType.EXCEL,
            '.pptx': FileType.POWERPOINT,
            '.ppt': FileType.POWERPOINT,
            '.go': FileType.GO,
            '.vba': FileType.VBA,
            '.bas': FileType.VBA,
        }
        
    def scan_workspace(self) -> Tuple[List[FileMetadata], List[FolderMetadata]]:
        """
        Scan entire workspace and generate comprehensive metadata
        
        Returns:
            Tuple of (file_metadata_list, folder_metadata_list)
        """
        files = []
        folders = []
        
        for path in self.workspace_root.rglob('*'):
            if self._should_skip(path):
                continue
                
            if path.is_file():
                file_meta = self._extract_file_metadata(path)
                files.append(file_meta)
                self._store_file_metadata(file_meta)
            elif path.is_dir():
                folder_meta = self._extract_folder_metadata(path)
                folders.append(folder_meta)
                self._store_folder_metadata(folder_meta)
                
        return files, folders
        
    def _should_skip(self, path: Path) -> bool:
        """Determine if path should be skipped"""
        skip_patterns = [
            '__pycache__',
            '.git',
            'node_modules',
            '.pytest_cache',
            '.mypy_cache',
            '.tox',
            'dist',
            'build',
            '*.pyc',
            '.DS_Store'
        ]
        
        for pattern in skip_patterns:
            if pattern in str(path):
                return True
        return False
        
    def _extract_file_metadata(self, file_path: Path) -> FileMetadata:
        """Extract comprehensive metadata from file"""
        stat = file_path.stat()
        
        file_type = self._determine_file_type(file_path)
        hash_val = self._compute_file_hash(file_path)
        
        parent = str(file_path.parent.relative_to(self.workspace_root))
        depth = len(file_path.relative_to(self.workspace_root).parts) - 1
        
        is_main = file_path.name in ['main.py', '__main__.py', 'app.py', 'run.py']
        
        dependencies,
            imports,
            exports,
            functions,
            classes = self._analyze_python_file(file_path) if file_type == FileType.PYTHON else ([],
            [],
            [],
            [],
            [])
        
        return FileMetadata(
            file_path=str(file_path.relative_to(self.workspace_root)),
            file_type=file_type,
            size_bytes=stat.st_size,
            hash_sha256=hash_val,
            created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
            modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            accessed_at=datetime.fromtimestamp(stat.st_atime).isoformat(),
            parent_folder=parent,
            depth_level=depth,
            is_main_entry=is_main,
            dependencies=dependencies,
            imports=imports,
            exports=exports,
            functions=functions,
            classes=classes
        )
        
    def _determine_file_type(self, file_path: Path) -> FileType:
        """Determine file type from extension"""
        if file_path.name in self.file_type_map:
            return self.file_type_map[file_path.name]
        
        suffix = file_path.suffix.lower()
        return self.file_type_map.get(suffix, FileType.OTHER)
        
    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except:
            return "error_computing_hash"
            
    def _analyze_python_file(self,
        file_path: Path) -> Tuple[List[str],
        List[str],
        List[str],
        List[str],
        List[str]]:
        """Analyze Python file for dependencies, imports, exports, functions, classes"""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            imports = []
            functions = []
            classes = []
            
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    imports.append(line)
                elif line.startswith('def '):
                    func_name = line.split('(')[0].replace('def ', '').strip()
                    functions.append(func_name)
                elif line.startswith('class '):
                    class_name = line.split('(')[0].split(':')[0].replace('class ', '').strip()
                    classes.append(class_name)
                    
            dependencies = [imp.split()[1].split('.')[0] for imp in imports if 'import' in imp]
            exports = functions + classes
            
            return dependencies, imports, exports, functions, classes
        except:
            return [], [], [], [], []
            
    def _extract_folder_metadata(self, folder_path: Path) -> FolderMetadata:
        """Extract metadata from folder"""
        stat = folder_path.stat()
        
        files = list(folder_path.glob('*'))
        file_count = sum(1 for f in files if f.is_file())
        subfolder_count = sum(1 for f in files if f.is_dir())
        
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        
        depth = len(folder_path.relative_to(self.workspace_root).parts)
        
        folder_name = folder_path.name.lower()
        is_venv = 'venv' in folder_name or 'env' in folder_name
        is_git = folder_name == '.git'
        is_config = folder_name in ['config', 'configs', 'settings']
        is_source = folder_name in ['src', 'source', 'lib']
        is_test = folder_name in ['test', 'tests', 'testing']
        is_output = folder_name in ['output', 'outputs', 'results', 'artifacts']
        
        purpose = self._determine_folder_purpose(folder_path)
        
        return FolderMetadata(
            folder_path=str(folder_path.relative_to(self.workspace_root)),
            depth_level=depth,
            file_count=file_count,
            subfolder_count=subfolder_count,
            total_size_bytes=total_size,
            created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
            modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            purpose=purpose,
            is_venv=is_venv,
            is_git=is_git,
            is_config=is_config,
            is_source=is_source,
            is_test=is_test,
            is_output=is_output
        )
        
    def _determine_folder_purpose(self, folder_path: Path) -> str:
        """Determine folder purpose from name and contents"""
        name = folder_path.name.lower()
        
        purpose_map = {
            'src': 'Source Code',
            'source': 'Source Code',
            'lib': 'Library Code',
            'test': 'Test Suite',
            'tests': 'Test Suite',
            'docs': 'Documentation',
            'documentation': 'Documentation',
            'config': 'Configuration',
            'configs': 'Configuration',
            'data': 'Data Storage',
            'output': 'Output/Results',
            'artifacts': 'Build Artifacts',
            'scripts': 'Utility Scripts',
            'tools': 'Development Tools',
            'dmaic_v3': 'DMAIC Engine',
            'phases': 'DMAIC Phases',
            'core': 'Core Functionality',
            'convergence': 'Convergence Logic',
            'integrations': 'External Integrations'
        }
        
        return purpose_map.get(name, 'General Purpose')
        
    def _store_file_metadata(self, metadata: FileMetadata):
        """Store file metadata in database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO file_metadata VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            metadata.file_path,
            metadata.file_type.value,
            metadata.size_bytes,
            metadata.hash_sha256,
            metadata.created_at,
            metadata.modified_at,
            metadata.accessed_at,
            metadata.parent_folder,
            metadata.depth_level,
            int(metadata.is_main_entry),
            json.dumps(metadata.dependencies),
            json.dumps(metadata.imports),
            json.dumps(metadata.exports),
            json.dumps(metadata.functions),
            json.dumps(metadata.classes),
            json.dumps(metadata.linked_outputs),
            json.dumps(metadata.linked_inputs),
            metadata.execution_count,
            metadata.last_execution,
            metadata.quality_score,
            metadata.test_coverage
        ))
        
        conn.commit()
        conn.close()
        
    def _store_folder_metadata(self, metadata: FolderMetadata):
        """Store folder metadata in database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO folder_metadata VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            metadata.folder_path,
            metadata.depth_level,
            metadata.file_count,
            metadata.subfolder_count,
            metadata.total_size_bytes,
            metadata.created_at,
            metadata.modified_at,
            metadata.purpose,
            int(metadata.is_venv),
            int(metadata.is_git),
            int(metadata.is_config),
            int(metadata.is_source),
            int(metadata.is_test),
            int(metadata.is_output),
            metadata.canonical_index
        ))
        
        conn.commit()
        conn.close()
        
    def record_execution(self, execution: ExecutionMetadata):
        """Record execution metadata"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO execution_metadata VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            execution.execution_id,
            execution.timestamp,
            execution.phase.value,
            execution.iteration,
            json.dumps(execution.input_files),
            json.dumps(execution.output_files),
            execution.duration_seconds,
            execution.status,
            json.dumps(execution.metrics),
            json.dumps(execution.logs),
            json.dumps(execution.errors),
            json.dumps(execution.warnings),
            json.dumps(execution.provenance_chain)
        ))
        
        conn.commit()
        conn.close()
        
    def create_digital_twin(self) -> DigitalTwinState:
        """Create digital twin snapshot of current workspace state"""
        files, folders = self.scan_workspace()
        
        twin_id = f"twin_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        total_size = sum(f.size_bytes for f in files)
        
        quality_metrics = {
            'avg_file_size': total_size / len(files) if files else 0,
            'python_file_ratio': sum(1 for f in files if f.file_type == FileType.PYTHON) / len(files) if files else 0,
                
            'test_coverage': sum(f.test_coverage for f in files) / len(files) if files else 0,
            'avg_quality_score': sum(f.quality_score for f in files) / len(files) if files else 0
        }
        
        twin = DigitalTwinState(
            twin_id=twin_id,
            source_workspace=str(self.workspace_root),
            timestamp=datetime.now().isoformat(),
            file_count=len(files),
            folder_count=len(folders),
            total_size_bytes=total_size,
            quality_metrics=quality_metrics,
            execution_history=[],
            improvement_actions=[],
            convergence_status={}
        )
        
        self._store_digital_twin(twin)
        
        return twin
        
    def _store_digital_twin(self, twin: DigitalTwinState):
        """Store digital twin state in database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO digital_twin_state VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            twin.twin_id,
            twin.source_workspace,
            twin.timestamp,
            twin.file_count,
            twin.folder_count,
            twin.total_size_bytes,
            json.dumps(twin.quality_metrics),
            json.dumps(twin.execution_history),
            json.dumps(twin.improvement_actions),
            json.dumps(twin.convergence_status)
        ))
        
        conn.commit()
        conn.close()
        
    def generate_hierarchy_report(self, output_path: Path):
        """Generate comprehensive hierarchy report in JSON"""
        files, folders = self.scan_workspace()
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'workspace_root': str(self.workspace_root),
            'summary': {
                'total_files': len(files),
                'total_folders': len(folders),
                'total_size_bytes': sum(f.size_bytes for f in files),
                'file_types': self._count_file_types(files),
                'folder_purposes': self._count_folder_purposes(folders)
            },
            'files': [asdict(f) for f in files],
            'folders': [asdict(f) for f in folders],
            'main_entry_points': [f.file_path for f in files if f.is_main_entry],
            'dependency_graph': self._build_dependency_graph(files)
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
            
        return report
        
    def _count_file_types(self, files: List[FileMetadata]) -> Dict[str, int]:
        """Count files by type"""
        counts = {}
        for f in files:
            type_name = f.file_type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts
        
    def _count_folder_purposes(self, folders: List[FolderMetadata]) -> Dict[str, int]:
        """Count folders by purpose"""
        counts = {}
        for f in folders:
            counts[f.purpose] = counts.get(f.purpose, 0) + 1
        return counts
        
    def _build_dependency_graph(self, files: List[FileMetadata]) -> Dict[str, List[str]]:
        """Build dependency graph from file metadata"""
        graph = {}
        for f in files:
            if f.dependencies:
                graph[f.file_path] = f.dependencies
        return graph
