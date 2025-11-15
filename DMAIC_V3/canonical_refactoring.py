"""
Unified Canonical Documentation Refactoring System
Organizes all markdown documentation with versioning and creates knowledge books
Uses temporal engine for time-aware knowledge management
"""

from pathlib import Path
from typing import Dict, List, Any, Set
from datetime import datetime
from collections import defaultdict
import json
import re
import hashlib


class DocumentCategory:
    """Document category with versioning"""
    DMAIC = "DMAIC"
    ABACUS = "ABACUS"
    SPRINT = "Sprint_Reports"
    EXECUTION = "Execution_Logs"
    ARCHITECTURE = "Architecture"
    PLANNING = "Planning"
    ASSESSMENT = "Assessment"
    REFERENCE = "Reference"
    CHANGELOG = "Changelog"
    
    @classmethod
    def all_categories(cls) -> List[str]:
        return [cls.DMAIC, cls.ABACUS, cls.SPRINT, cls.EXECUTION, 
                cls.ARCHITECTURE, cls.PLANNING, cls.ASSESSMENT, 
                cls.REFERENCE, cls.CHANGELOG]


class CanonicalDocumentRefactorer:
    """
    Unified system for organizing and versioning all documentation
    Creates canonical knowledge books from document sets
    """
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = Path(workspace_root)
        self.canonical_root = self.workspace_root / "CANONICAL_KNOWLEDGE"
        self.canonical_root.mkdir(exist_ok=True, parents=True)
        
        # Category mappings
        self.category_patterns = {
            DocumentCategory.DMAIC: [
                r"DMAIC.*\.md$",
                r".*dmaic.*\.md$",
                r".*phase\d+.*\.md$"
            ],
            DocumentCategory.ABACUS: [
                r"ABACUS.*\.md$",
                r".*abacus.*\.md$"
            ],
            DocumentCategory.SPRINT: [
                r".*SPRINT.*\.md$",
                r".*sprint.*\.md$"
            ],
            DocumentCategory.EXECUTION: [
                r".*EXECUTION.*\.md$",
                r".*execution.*\.md$",
                r".*SESSION.*\.md$"
            ],
            DocumentCategory.ARCHITECTURE: [
                r".*ARCHITECTURE.*\.md$",
                r".*architecture.*\.md$",
                r".*LIFECYCLE.*\.md$"
            ],
            DocumentCategory.PLANNING: [
                r".*PLAN.*\.md$",
                r".*ROADMAP.*\.md$",
                r".*TODO.*\.md$"
            ],
            DocumentCategory.ASSESSMENT: [
                r".*ASSESSMENT.*\.md$",
                r".*MATURITY.*\.md$",
                r".*AUDIT.*\.md$"
            ],
            DocumentCategory.REFERENCE: [
                r".*REFERENCE.*\.md$",
                r".*QUICK.*\.md$",
                r".*INDEX.*\.md$"
            ],
            DocumentCategory.CHANGELOG: [
                r"CHANGELOG.*\.md$",
                r".*changelog.*\.md$"
            ]
        }
        
        self.document_registry: Dict[str, Dict[str, Any]] = {}
        self.version_history: Dict[str, List[Dict[str, Any]]] = {}
        
    def scan_all_documents(self) -> Dict[str, List[Path]]:
        """Scan workspace for all markdown documents"""
        print(f"\n[CANONICAL] Scanning {self.workspace_root} for markdown documents...")
        
        categorized_docs: Dict[str, List[Path]] = defaultdict(list)
        all_md_files = list(self.workspace_root.rglob("*.md"))
        
        print(f"[CANONICAL] Found {len(all_md_files)} markdown files")
        
        for md_file in all_md_files:
            # Skip files in canonical root to avoid recursion
            if self.canonical_root in md_file.parents:
                continue
                
            category = self._categorize_document(md_file)
            categorized_docs[category].append(md_file)
            
            # Register document
            self._register_document(md_file, category)
        
        return dict(categorized_docs)
    
    def _categorize_document(self, doc_path: Path) -> str:
        """Categorize document based on filename patterns"""
        filename = doc_path.name
        
        for category, patterns in self.category_patterns.items():
            for pattern in patterns:
                if re.match(pattern, filename, re.IGNORECASE):
                    return category
        
        return "Uncategorized"
    
    def _register_document(self, doc_path: Path, category: str):
        """Register document with metadata"""
        doc_id = self._generate_doc_id(doc_path)
        
        # Get file stats
        stats = doc_path.stat()
        
        # Calculate content hash for versioning
        content_hash = self._calculate_content_hash(doc_path)
        
        doc_metadata = {
            'doc_id': doc_id,
            'path': str(doc_path.relative_to(self.workspace_root)),
            'category': category,
            'filename': doc_path.name,
            'size_bytes': stats.st_size,
            'modified_time': datetime.fromtimestamp(stats.st_mtime).isoformat(),
            'content_hash': content_hash,
            'registered_at': datetime.now().isoformat()
        }
        
        self.document_registry[doc_id] = doc_metadata
        
        # Track version history
        if doc_id not in self.version_history:
            self.version_history[doc_id] = []
        self.version_history[doc_id].append(doc_metadata)
    
    def _generate_doc_id(self, doc_path: Path) -> str:
        """Generate unique document ID"""
        rel_path = doc_path.relative_to(self.workspace_root)
        return hashlib.md5(str(rel_path).encode()).hexdigest()[:12]
    
    def _calculate_content_hash(self, doc_path: Path) -> str:
        """Calculate content hash for versioning"""
        try:
            content = doc_path.read_text(encoding='utf-8')
            return hashlib.sha256(content.encode()).hexdigest()[:16]
        except Exception:
            return "error"
    
    def create_canonical_structure(self, categorized_docs: Dict[str, List[Path]]):
        """Create canonical directory structure"""
        print(f"\n[CANONICAL] Creating canonical structure...")

        # Create directories for all standard categories
        for category in DocumentCategory.all_categories():
            category_dir = self.canonical_root / category
            category_dir.mkdir(exist_ok=True, parents=True)

            # Create versioned subdirectory
            versioned_dir = category_dir / "versioned"
            versioned_dir.mkdir(exist_ok=True, parents=True)

            # Create latest subdirectory
            latest_dir = category_dir / "latest"
            latest_dir.mkdir(exist_ok=True, parents=True)

        # Create directories for any additional categories found
        for category in categorized_docs.keys():
            if category not in DocumentCategory.all_categories():
                category_dir = self.canonical_root / category
                category_dir.mkdir(exist_ok=True, parents=True)

                versioned_dir = category_dir / "versioned"
                versioned_dir.mkdir(exist_ok=True, parents=True)

                latest_dir = category_dir / "latest"
                latest_dir.mkdir(exist_ok=True, parents=True)

        total_categories = len(set(list(DocumentCategory.all_categories()) + list(categorized_docs.keys())))
        print(f"[CANONICAL] [OK] Created {total_categories} category directories")
    
    def create_knowledge_books(self, categorized_docs: Dict[str, List[Path]]) -> Dict[str, Path]:
        """Create knowledge books from canonical document sets"""
        print(f"\n[CANONICAL] Creating knowledge books...")
        
        books_created = {}
        
        for category, docs in categorized_docs.items():
            if not docs:
                continue
            
            book_path = self._create_category_book(category, docs)
            books_created[category] = book_path
            print(f"[CANONICAL] [OK] Created {category} book: {book_path.name}")
        
        # Create master index book
        master_book = self._create_master_index_book(categorized_docs)
        books_created['MASTER_INDEX'] = master_book
        print(f"[CANONICAL] [OK] Created MASTER_INDEX book")
        
        return books_created
    
    def _create_category_book(self, category: str, docs: List[Path]) -> Path:
        """Create a knowledge book for a category"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        book_filename = f"{category}_BOOK_{timestamp}.md"
        book_path = self.canonical_root / category / book_filename
        
        with open(book_path, 'w', encoding='utf-8') as book:
            # Write book header
            book.write(f"# {category} Knowledge Book\n\n")
            book.write(f"**Generated:** {datetime.now().isoformat()}\n")
            book.write(f"**Documents Included:** {len(docs)}\n")
            book.write(f"**Version:** {timestamp}\n\n")
            book.write("---\n\n")
            
            # Write table of contents
            book.write("## Table of Contents\n\n")
            for idx, doc in enumerate(sorted(docs, key=lambda x: x.name), 1):
                book.write(f"{idx}. [{doc.name}](#{self._make_anchor(doc.name)})\n")
            book.write("\n---\n\n")
            
            # Write document contents
            for doc in sorted(docs, key=lambda x: x.name):
                book.write(f"## {doc.name}\n\n")
                book.write(f"**Source:** `{doc.relative_to(self.workspace_root)}`\n\n")
                
                try:
                    content = doc.read_text(encoding='utf-8')
                    book.write(content)
                except Exception as e:
                    book.write(f"*Error reading document: {e}*\n")
                
                book.write("\n\n---\n\n")
        
        return book_path
    
    def _create_master_index_book(self, categorized_docs: Dict[str, List[Path]]) -> Path:
        """Create master index book"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        book_path = self.canonical_root / f"MASTER_INDEX_{timestamp}.md"
        
        with open(book_path, 'w', encoding='utf-8') as book:
            book.write("# Master Documentation Index\n\n")
            book.write(f"**Generated:** {datetime.now().isoformat()}\n")
            book.write(f"**Total Documents:** {sum(len(docs) for docs in categorized_docs.values())}\n")
            book.write(f"**Categories:** {len(categorized_docs)}\n\n")
            book.write("---\n\n")
            
            # Category summary
            book.write("## Category Summary\n\n")
            for category in sorted(categorized_docs.keys()):
                docs = categorized_docs[category]
                book.write(f"### {category} ({len(docs)} documents)\n\n")
                for doc in sorted(docs, key=lambda x: x.name):
                    book.write(f"- `{doc.relative_to(self.workspace_root)}`\n")
                book.write("\n")
            
            book.write("---\n\n")
            
            # Document registry
            book.write("## Document Registry\n\n")
            book.write("| Doc ID | Category | Filename | Size | Modified |\n")
            book.write("|--------|----------|----------|------|----------|\n")
            for doc_id, metadata in sorted(self.document_registry.items(), 
                                          key=lambda x: x[1]['category']):
                book.write(f"| {doc_id} | {metadata['category']} | "
                          f"{metadata['filename']} | {metadata['size_bytes']} | "
                          f"{metadata['modified_time'][:10]} |\n")
        
        return book_path
    
    def _make_anchor(self, text: str) -> str:
        """Create markdown anchor from text"""
        return re.sub(r'[^\w\s-]', '', text.lower()).replace(' ', '-')
    
    def save_registry(self):
        """Save document registry and version history"""
        registry_file = self.canonical_root / "document_registry.json"
        with open(registry_file, 'w', encoding='utf-8') as f:
            json.dump({
                'registry': self.document_registry,
                'version_history': self.version_history,
                'generated_at': datetime.now().isoformat()
            }, f, indent=2)
        
        print(f"[CANONICAL] [OK] Saved registry: {registry_file}")
    
    def generate_summary_report(self, categorized_docs: Dict[str, List[Path]], 
                               books_created: Dict[str, Path]) -> Path:
        """Generate summary report"""
        report_path = self.canonical_root / "REFACTORING_SUMMARY.md"
        
        with open(report_path, 'w', encoding='utf-8') as report:
            report.write("# Canonical Documentation Refactoring Summary\n\n")
            report.write(f"**Generated:** {datetime.now().isoformat()}\n")
            report.write(f"**Workspace:** `{self.workspace_root}`\n\n")
            report.write("---\n\n")
            
            # Statistics
            total_docs = sum(len(docs) for docs in categorized_docs.values())
            report.write("## Statistics\n\n")
            report.write(f"- **Total Documents Processed:** {total_docs}\n")
            report.write(f"- **Categories:** {len(categorized_docs)}\n")
            report.write(f"- **Knowledge Books Created:** {len(books_created)}\n")
            report.write(f"- **Documents Registered:** {len(self.document_registry)}\n\n")
            
            # Category breakdown
            report.write("## Category Breakdown\n\n")
            for category in sorted(categorized_docs.keys()):
                docs = categorized_docs[category]
                report.write(f"### {category}\n")
                report.write(f"- Documents: {len(docs)}\n")
                total_size = sum(doc.stat().st_size for doc in docs)
                report.write(f"- Total Size: {total_size:,} bytes\n\n")
            
            # Books created
            report.write("## Knowledge Books Created\n\n")
            for category, book_path in books_created.items():
                report.write(f"- **{category}:** `{book_path.relative_to(self.canonical_root)}`\n")
            
            report.write("\n---\n\n")
            report.write("## Next Steps\n\n")
            report.write("1. Review knowledge books in `CANONICAL_KNOWLEDGE/`\n")
            report.write("2. Integrate with temporal engine for time-aware queries\n")
            report.write("3. Set up automated versioning and updates\n")
            report.write("4. Create cross-reference index\n")
        
        print(f"[CANONICAL] [OK] Generated summary report: {report_path}")
        return report_path


def run_canonical_refactoring(workspace_root: str = ".") -> Dict[str, Any]:
    """
    Main entry point for canonical documentation refactoring
    """
    print("="*80)
    print("CANONICAL DOCUMENTATION REFACTORING SYSTEM")
    print("="*80)
    
    refactorer = CanonicalDocumentRefactorer(Path(workspace_root))
    
    # Scan all documents
    categorized_docs = refactorer.scan_all_documents()
    
    # Create canonical structure
    refactorer.create_canonical_structure(categorized_docs)
    
    # Create knowledge books
    books_created = refactorer.create_knowledge_books(categorized_docs)
    
    # Save registry
    refactorer.save_registry()
    
    # Generate summary report
    summary_report = refactorer.generate_summary_report(categorized_docs, books_created)
    
    print("\n" + "="*80)
    print("REFACTORING COMPLETE")
    print("="*80)
    print(f"[OK] Canonical root: {refactorer.canonical_root}")
    print(f"[OK] Summary report: {summary_report}")
    
    return {
        'canonical_root': str(refactorer.canonical_root),
        'categorized_docs': {k: [str(p) for p in v] for k, v in categorized_docs.items()},
        'books_created': {k: str(v) for k, v in books_created.items()},
        'summary_report': str(summary_report),
        'total_documents': sum(len(docs) for docs in categorized_docs.values())
    }


if __name__ == "__main__":
    result = run_canonical_refactoring()
    print(f"\n[OK] Processed {result['total_documents']} documents")
