"""
DMAIC V3 - Documentation Version Aligner
=========================================

Aligns all markdown documentation files with version numbers and changelogs.

Manages:
- master_document_system/INTEGRATION_PLAN.md
- master_document_system/DEPLOYMENT_COMPLETE.md
- master_document_system/IMPLEMENTATION_SUMMARY.md
- master_document_system/README.md

Features:
- Version number synchronization
- Changelog generation and linking
- Cross-references to code, JSON, YAML
- Victory condition tracking
- Bidirectional DMAIC V3 integration markers
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
import json
import yaml


class DocumentationAligner:
    """Align documentation with version numbers and changelogs"""
    
    VERSION = "3.1.0"
    DMAIC_VERSION = "V3"
    INTEGRATION_MODE = "BIDIRECTIONAL"
    
    MARKDOWN_FILES = [
        "INTEGRATION_PLAN.md",
        "DEPLOYMENT_COMPLETE.md",
        "IMPLEMENTATION_SUMMARY.md",
        "README.md"
    ]
    
    def __init__(self, docs_dir: Path):
        self.docs_dir = Path(docs_dir)
        self.changelog = self._load_changelog()
        self.version_info = self._create_version_info()
    
    def _load_changelog(self) -> List[Dict]:
        """Load changelog from version history"""
        return [
            {
                'version': '3.1.0',
                'date': '2025-11-10',
                'changes': [
                    'Integrated with DMAIC V3 architecture',
                    'Added execution tracker for Python and VBA',
                    'Implemented error type classification',
                    'Created victory condition framework',
                    'Established bidirectional pipeline integration',
                    'Added comprehensive statistics tracking',
                    'Linked documentation to code/JSON/YAML'
                ],
                'files_modified': [
                    'DMAIC_V3/generators/__init__.py',
                    'DMAIC_V3/generators/execution_tracker.py',
                    'DMAIC_V3/generators/documentation_aligner.py'
                ],
                'victory_conditions': [
                    'All Python code executes without errors',
                    'All VBA code validates successfully',
                    'Execution statistics tracked per file',
                    'Error types classified and reported',
                    'Documentation aligned with version numbers',
                    'JSON/YAML reports generated and linked'
                ]
            },
            {
                'version': '3.0.1',
                'date': '2025-11-10',
                'changes': [
                    'Initial master_document_system implementation',
                    'Created temporal tracker',
                    'Created DMAIC manager',
                    'Created style extractor',
                    'Created input manager',
                    'Created master engine'
                ],
                'status': 'SUPERSEDED - Refactored to DMAIC V3 integration'
            }
        ]
    
    def _create_version_info(self) -> Dict:
        """Create version information block"""
        return {
            'version': self.VERSION,
            'dmaic_version': self.DMAIC_VERSION,
            'integration_mode': self.INTEGRATION_MODE,
            'last_updated': datetime.now().isoformat(),
            'changelog_link': './CHANGELOG.md',
            'code_links': {
                'generators': 'DMAIC_V3/generators/',
                'execution_tracker': 'DMAIC_V3/generators/execution_tracker.py',
                'metrics': 'DMAIC_V3/core/metrics.py',
                'state_manager': 'DMAIC_V3/core/state.py'
            },
            'report_links': {
                'json': 'output/execution_reports/execution_report.json',
                'yaml': 'output/execution_reports/execution_report.yaml',
                'markdown': 'output/execution_reports/EXECUTION_REPORT.md'
            }
        }
    
    def _create_version_header(self) -> str:
        """Create standardized version header"""
        return f"""---
**Version**: {self.VERSION}  
**DMAIC Version**: {self.DMAIC_VERSION}  
**Integration**: {self.INTEGRATION_MODE} (`DMAIC V3 Engine <--> Document Generator <--> Recursive Engine`)  
**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Status**: [OK] ACTIVE

**Quick Links**:
- [Execution Tracker](../DMAIC_V3/generators/execution_tracker.py)
- [Metrics System](../DMAIC_V3/core/metrics.py)
- [JSON Report]({self.version_info['report_links']['json']})
- [YAML Report]({self.version_info['report_links']['yaml']})
- [Changelog](#changelog)
---
"""
    
    def _create_changelog_section(self) -> str:
        """Create changelog section"""
        changelog_md = "\n## Changelog\n\n"
        
        for entry in self.changelog:
            changelog_md += f"### Version {entry['version']} - {entry['date']}\n\n"
            
            if 'status' in entry:
                changelog_md += f"**Status**: {entry['status']}\n\n"
            
            changelog_md += "**Changes**:\n"
            for change in entry['changes']:
                changelog_md += f"- {change}\n"
            changelog_md += "\n"
            
            if 'files_modified' in entry:
                changelog_md += "**Files Modified**:\n"
                for file in entry['files_modified']:
                    changelog_md += f"- [`{file}`](../{file})\n"
                changelog_md += "\n"
            
            if 'victory_conditions' in entry:
                changelog_md += "**Victory Conditions**:\n"
                for condition in entry['victory_conditions']:
                    changelog_md += f"- {condition}\n"
                changelog_md += "\n"
        
        return changelog_md
    
    def _create_integration_diagram(self) -> str:
        """Create integration diagram"""
        return """
## Integration Architecture

```
+-----------------------------------------------------------------+
|                      DMAIC V3 ECOSYSTEM                         |
+-----------------------------------------------------------------+
|                                                                 |
|  +--------------+         +--------------+         +---------+|
|  |  DMAIC V3    |◄-------►|  Document    |◄-------►|Recursive||
|  |   Engine     |         |  Generator   |         | Engine  ||
|  +--------------+         +--------------+         +---------+|
|         |                        |                       |     |
|         |                        |                       |     |
|         ▼                        ▼                       ▼     |
|  +--------------+         +--------------+         +---------+|
|  |   Phases     |         |   Execution  |         |Artifact ||
|  |  (0-5)       |         |   Tracker    |         |Processor||
|  +--------------+         +--------------+         +---------+|
|         |                        |                       |     |
|         +------------------------+-----------------------+     |
|                                  |                             |
|                                  ▼                             |
|                         +--------------+                       |
|                         |   Metrics    |                       |
|                         |   System     |                       |
|                         +--------------+                       |
|                                  |                             |
|                                  ▼                             |
|                    +--------------------------+               |
|                    |  JSON/YAML/Markdown      |               |
|                    |  Reports & Documentation |               |
|                    +--------------------------+               |
+-----------------------------------------------------------------+
```

### Entry Points

1. **From DMAIC V3 Phases**:
   ```python
   from DMAIC_V3.generators import DocumentGenerator
   generator = DocumentGenerator(config)
   generator.generate(output_formats=['docx', 'json'])
   ```

2. **From Recursive Engine**:
   ```python
   from DMAIC_V3.generators import ArtifactProcessor
   processor = ArtifactProcessor(config)
   processor.process_artifacts(artifacts)
   ```

3. **Standalone CLI**:
   ```bash
   python -m DMAIC_V3.generators generate --format docx --output report.docx
   ```
"""
    
    def align_file(self, filename: str) -> Tuple[bool, str]:
        """Align a single markdown file"""
        file_path = self.docs_dir / filename
        
        if not file_path.exists():
            return False, f"File not found: {file_path}"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            if lines and lines[0].startswith('#'):
                title = lines[0]
                rest_content = '\n'.join(lines[1:])
            else:
                title = f"# {filename.replace('.md', '').replace('_', ' ').title()}"
                rest_content = content
            
            rest_content = re.sub(r'---\n\*\*Version\*\*:.*?---\n', '', rest_content, flags=re.DOTALL)
            
            rest_content = re.sub(r'## Changelog\n.*?(?=\n##|\Z)', '', rest_content, flags=re.DOTALL)
            
            rest_content = re.sub(r'## Integration Architecture\n.*?```\n', '', rest_content, flags=re.DOTALL)
            
            aligned_content = (
                title + '\n\n' +
                self._create_version_header() + '\n' +
                rest_content.strip() + '\n\n' +
                self._create_integration_diagram() + '\n' +
                self._create_changelog_section()
            )
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(aligned_content)
            
            return True, f"[OK] Aligned: {filename}"
            
        except Exception as e:
            return False, f"[FAIL] Error aligning {filename}: {e}"
    
    def align_all(self) -> Dict[str, Tuple[bool, str]]:
        """Align all markdown files"""
        results = {}
        
        print(f"\n{'='*80}")
        print("DOCUMENTATION VERSION ALIGNER")
        print(f"{'='*80}")
        print(f"Version: {self.VERSION}")
        print(f"DMAIC Version: {self.DMAIC_VERSION}")
        print(f"Integration Mode: {self.INTEGRATION_MODE}")
        print(f"{'='*80}\n")
        
        for filename in self.MARKDOWN_FILES:
            success, message = self.align_file(filename)
            results[filename] = (success, message)
            print(message)
        
        print(f"\n{'='*80}")
        successful = sum(1 for s, _ in results.values() if s)
        print(f"Aligned {successful}/{len(self.MARKDOWN_FILES)} files successfully")
        print(f"{'='*80}\n")
        
        return results
    
    def export_version_info_json(self) -> Path:
        """Export version info to JSON"""
        output_file = self.docs_dir / "VERSION_INFO.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'version_info': self.version_info,
                'changelog': self.changelog
            }, f, indent=2)
        
        print(f"[OK] Version info exported: {output_file}")
        return output_file
    
    def export_version_info_yaml(self) -> Path:
        """Export version info to YAML"""
        output_file = self.docs_dir / "VERSION_INFO.yaml"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump({
                'version_info': self.version_info,
                'changelog': self.changelog
            }, f, default_flow_style=False, sort_keys=False)
        
        print(f"[OK] Version info exported: {output_file}")
        return output_file


if __name__ == '__main__':
    docs_dir = Path(__file__).parent.parent.parent / 'master_document_system'
    
    aligner = DocumentationAligner(docs_dir)
    
    results = aligner.align_all()
    
    aligner.export_version_info_json()
    aligner.export_version_info_yaml()
    
    all_success = all(success for success, _ in results.values())
    
    if all_success:
        print("\n[OK] All documentation files aligned successfully!")
    else:
        print("\n[FAIL] Some files failed to align. Check messages above.")
