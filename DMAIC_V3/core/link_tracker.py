"""
DMAIC V3.1 - Link Tracker & Term Frequency Analyzer
Tracks recursive documentation links, version history, and term frequency
across markdown and Python files for uniform language validation.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import Counter
import re
import json
from datetime import datetime


@dataclass
class DocumentLink:
    """Represents a link between documents"""
    source_file: str
    target_file: str
    link_type: str  # 'recursive_hook', 'cross_reference', 'code_link', 'version_link'
    line_number: int
    context: str
    version_source: Optional[str] = None
    version_target: Optional[str] = None


@dataclass
class TermFrequency:
    """Term frequency analysis for a file"""
    file_path: str
    file_type: str  # 'markdown', 'python', 'json'
    total_words: int
    unique_words: int
    term_counts: Dict[str, int] = field(default_factory=dict)
    top_terms: List[Tuple[str, int]] = field(default_factory=list)
    technical_terms: Dict[str, int] = field(default_factory=dict)
    version: Optional[str] = None


@dataclass
class VersionNode:
    """Represents a version in the version tree"""
    version: str
    date: datetime
    files: List[str]
    parent_version: Optional[str] = None
    child_versions: List[str] = field(default_factory=list)
    changes: Dict[str, str] = field(default_factory=dict)  # file -> change_type


@dataclass
class LinkGraph:
    """Complete link graph for the project"""
    nodes: Dict[str, VersionNode] = field(default_factory=dict)
    links: List[DocumentLink] = field(default_factory=list)
    term_frequencies: Dict[str, TermFrequency] = field(default_factory=dict)
    version_lineage: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "nodes": {
                v: {
                    "version": node.version,
                    "date": node.date.isoformat(),
                    "files": node.files,
                    "parent_version": node.parent_version,
                    "child_versions": node.child_versions,
                    "changes": node.changes
                }
                for v, node in self.nodes.items()
            },
            "links": [
                {
                    "source_file": link.source_file,
                    "target_file": link.target_file,
                    "link_type": link.link_type,
                    "line_number": link.line_number,
                    "context": link.context,
                    "version_source": link.version_source,
                    "version_target": link.version_target
                }
                for link in self.links
            ],
            "term_frequencies": {
                file: {
                    "file_path": tf.file_path,
                    "file_type": tf.file_type,
                    "total_words": tf.total_words,
                    "unique_words": tf.unique_words,
                    "term_counts": tf.term_counts,
                    "top_terms": tf.top_terms,
                    "technical_terms": tf.technical_terms,
                    "version": tf.version
                }
                for file, tf in self.term_frequencies.items()
            },
            "version_lineage": self.version_lineage
        }


class LinkTracker:
    """Tracks links between documents and versions"""
    
    # Patterns for detecting links
    MARKDOWN_LINK_PATTERN = r'\[([^\]]+)\]\(([^\)]+)\)'
    VERSION_PATTERN = r'[Vv](\d+\.\d+(?:\.\d+)?)'
    RECURSIVE_HOOK_PATTERN = r'(?:recursive\s+hook|parent\s+version|see\s+v\d+)'
    
    # Technical terms to track (DMAIC-specific)
    TECHNICAL_TERMS = {
        'dmaic', 'define', 'measure', 'analyze', 'improve', 'control',
        'idempotent', 'idempotency', 'recursive', 'iteration', 'phase',
        'metric', 'knowledge', 'artifact', 'checkpoint', 'state',
        'orchestrator', 'pipeline', 'validation', 'convergence'
    }
    
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.graph = LinkGraph()
    
    def scan_project(self) -> LinkGraph:
        """Scan entire project for links and term frequencies"""
        # Scan markdown files
        for md_file in self.root_dir.rglob("*.md"):
            self._scan_markdown_file(md_file)
        
        # Scan Python files
        for py_file in self.root_dir.rglob("*.py"):
            self._scan_python_file(py_file)
        
        # Scan JSON files
        for json_file in self.root_dir.rglob("*.json"):
            self._scan_json_file(json_file)
        
        # Build version lineage
        self._build_version_lineage()
        
        return self.graph
    
    def _scan_markdown_file(self, file_path: Path):
        """Scan markdown file for links and terms"""
        try:
            content = file_path.read_text(encoding='utf-8')
            relative_path = str(file_path.relative_to(self.root_dir))
            
            # Extract version
            version = self._extract_version(content)
            
            # Find all links
            for match in re.finditer(self.MARKDOWN_LINK_PATTERN, content, re.IGNORECASE):
                link_text = match.group(1)
                link_target = match.group(2)
                line_number = content[:match.start()].count('\n') + 1
                
                # Determine link type
                link_type = self._classify_link(link_text, link_target, content[max(0, match.start()-100):match.end()+100])
                
                link = DocumentLink(
                    source_file=relative_path,
                    target_file=link_target,
                    link_type=link_type,
                    line_number=line_number,
                    context=link_text,
                    version_source=version
                )
                self.graph.links.append(link)
            
            # Analyze term frequency
            term_freq = self._analyze_term_frequency(content, relative_path, 'markdown', version)
            self.graph.term_frequencies[relative_path] = term_freq
            
        except Exception as e:
            print(f"Error scanning {file_path}: {e}")
    
    def _scan_python_file(self, file_path: Path):
        """Scan Python file for docstring links and terms"""
        try:
            content = file_path.read_text(encoding='utf-8')
            relative_path = str(file_path.relative_to(self.root_dir))
            
            # Extract version from module docstring
            version = self._extract_version(content)
            
            # Analyze term frequency
            term_freq = self._analyze_term_frequency(content, relative_path, 'python', version)
            self.graph.term_frequencies[relative_path] = term_freq
            
        except Exception as e:
            print(f"Error scanning {file_path}: {e}")
    
    def _scan_json_file(self, file_path: Path):
        """Scan JSON file for metadata and links"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            relative_path = str(file_path.relative_to(self.root_dir))
            
            # Convert JSON to text for term analysis
            content = json.dumps(data, indent=2)
            
            # Extract version if present
            version = data.get('version') or data.get('metadata', {}).get('version')
            
            # Analyze term frequency
            term_freq = self._analyze_term_frequency(content, relative_path, 'json', version)
            self.graph.term_frequencies[relative_path] = term_freq
            
        except Exception as e:
            print(f"Error scanning {file_path}: {e}")
    
    def _extract_version(self, content: str) -> Optional[str]:
        """Extract version number from content"""
        match = re.search(r'[Vv]ersion[:\s]+(\d+\.\d+(?:\.\d+)?)', content)
        if match:
            return match.group(1)
        return None
    
    def _classify_link(self, link_text: str, link_target: str, context: str) -> str:
        """Classify the type of link"""
        context_lower = context.lower()
        
        if re.search(self.RECURSIVE_HOOK_PATTERN, context_lower, re.IGNORECASE):
            return 'recursive_hook'
        elif 'version' in context_lower or re.search(self.VERSION_PATTERN, context_lower):
            return 'version_link'
        elif link_target.endswith('.py'):
            return 'code_link'
        else:
            return 'cross_reference'
    
    def _analyze_term_frequency(self, content: str, file_path: str, file_type: str, version: Optional[str]) -> TermFrequency:
        """Analyze term frequency in content"""
        # Tokenize (simple word splitting)
        words = re.findall(r'\b[a-z_][a-z0-9_]*\b', content.lower())
        
        # Count terms
        term_counts = Counter(words)
        
        # Filter technical terms
        technical_terms = {
            term: count 
            for term, count in term_counts.items() 
            if term in self.TECHNICAL_TERMS
        }
        
        # Get top terms (excluding common words)
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been', 'being'}
        filtered_counts = {term: count for term, count in term_counts.items() if term not in common_words and len(term) > 2}
        top_terms = sorted(filtered_counts.items(), key=lambda x: x[1], reverse=True)[:50]
        
        return TermFrequency(
            file_path=file_path,
            file_type=file_type,
            total_words=len(words),
            unique_words=len(term_counts),
            term_counts=dict(term_counts),
            top_terms=top_terms,
            technical_terms=technical_terms,
            version=version
        )
    
    def _build_version_lineage(self):
        """Build version lineage from detected versions"""
        # Extract all versions
        versions = set()
        for tf in self.graph.term_frequencies.values():
            if tf.version:
                versions.add(tf.version)
        
        # Sort versions
        def version_key(v: str) -> Tuple[int, ...]:
            return tuple(map(int, v.split('.')))
        
        sorted_versions = sorted(versions, key=version_key)
        self.graph.version_lineage = sorted_versions
        
        # Build version nodes
        for i, version in enumerate(sorted_versions):
            parent = sorted_versions[i-1] if i > 0 else None
            children = [sorted_versions[i+1]] if i < len(sorted_versions) - 1 else []
            
            # Find files for this version
            files = [
                tf.file_path 
                for tf in self.graph.term_frequencies.values() 
                if tf.version == version
            ]
            
            node = VersionNode(
                version=version,
                date=datetime.now(),  # Would need to extract from git history
                files=files,
                parent_version=parent,
                child_versions=children
            )
            self.graph.nodes[version] = node
    
    def generate_link_report(self, output_path: Path):
        """Generate comprehensive link report"""
        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "root_directory": str(self.root_dir),
                "total_files_scanned": len(self.graph.term_frequencies),
                "total_links_found": len(self.graph.links),
                "versions_detected": self.graph.version_lineage
            },
            "link_graph": self.graph.to_dict(),
            "statistics": self._generate_statistics()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
    
    def _generate_statistics(self) -> Dict:
        """Generate statistics about links and terms"""
        link_types = Counter(link.link_type for link in self.graph.links)
        file_types = Counter(tf.file_type for tf in self.graph.term_frequencies.values())
        
        # Aggregate technical terms across all files
        all_technical_terms = Counter()
        for tf in self.graph.term_frequencies.values():
            all_technical_terms.update(tf.technical_terms)
        
        return {
            "link_types": dict(link_types),
            "file_types": dict(file_types),
            "top_technical_terms": sorted(all_technical_terms.items(), key=lambda x: x[1], reverse=True)[:20],
            "average_words_per_file": sum(tf.total_words for tf in self.graph.term_frequencies.values()) / len(self.graph.term_frequencies) if self.graph.term_frequencies else 0
        }
    
    def validate_uniform_language(self) -> Dict[str, List[str]]:
        """Validate that documentation and code use uniform terminology"""
        issues = {
            "missing_in_docs": [],
            "missing_in_code": [],
            "inconsistent_usage": []
        }
        
        # Get terms from markdown files
        doc_terms = set()
        for tf in self.graph.term_frequencies.values():
            if tf.file_type == 'markdown':
                doc_terms.update(tf.technical_terms.keys())
        
        # Get terms from Python files
        code_terms = set()
        for tf in self.graph.term_frequencies.values():
            if tf.file_type == 'python':
                code_terms.update(tf.technical_terms.keys())
        
        # Find discrepancies
        issues["missing_in_docs"] = list(code_terms - doc_terms)
        issues["missing_in_code"] = list(doc_terms - code_terms)
        
        return issues


def main():
    """Main entry point for link tracking"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python link_tracker.py <project_root>")
        sys.exit(1)
    
    root_dir = Path(sys.argv[1])
    tracker = LinkTracker(root_dir)
    
    print("Scanning project for links and term frequencies...")
    graph = tracker.scan_project()
    
    print(f"Found {len(graph.links)} links")
    print(f"Analyzed {len(graph.term_frequencies)} files")
    print(f"Detected versions: {', '.join(graph.version_lineage)}")
    
    # Generate report
    output_path = root_dir / "link_tracker_report.json"
    tracker.generate_link_report(output_path)
    print(f"Report saved to: {output_path}")
    
    # Validate uniform language
    issues = tracker.validate_uniform_language()
    if any(issues.values()):
        print("\n[!]️  Language consistency issues found:")
        if issues["missing_in_docs"]:
            print(f"  - Terms in code but not docs: {', '.join(issues['missing_in_docs'][:10])}")
        if issues["missing_in_code"]:
            print(f"  - Terms in docs but not code: {', '.join(issues['missing_in_code'][:10])}")
    else:
        print("\n[OK] Documentation and code use uniform terminology")


if __name__ == "__main__":
    main()
