import os
import json
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import re

class RecentFilesAnalyzer:
    def __init__(self, base_path, days=7):
        self.base_path = Path(base_path)
        self.days = days
        self.cutoff_date = datetime.now() - timedelta(days=days)
        self.results = {
            'yaml_files': [],
            'json_files': [],
            'markdown_files': [],
            'gaps': defaultdict(list),
            'statistics': {},
            'top_30_files': []
        }
        
    def scan_directories(self, directories):
        for directory in directories:
            dir_path = self.base_path / directory
            if not dir_path.exists():
                continue
            
            for file_path in dir_path.rglob('*'):
                if not file_path.is_file():
                    continue
                    
                try:
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime < self.cutoff_date:
                        continue
                    
                    file_info = {
                        'path': str(file_path.relative_to(self.base_path)),
                        'name': file_path.name,
                        'size': file_path.stat().st_size,
                        'modified': mtime.isoformat(),
                        'extension': file_path.suffix
                    }
                    
                    if file_path.suffix in ['.yaml', '.yml']:
                        self.analyze_yaml(file_path, file_info)
                    elif file_path.suffix == '.json':
                        self.analyze_json(file_path, file_info)
                    elif file_path.suffix == '.md':
                        self.analyze_markdown(file_path, file_info)
                        
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
    
    def analyze_yaml(self, file_path, file_info):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)
                file_info['content_type'] = 'yaml'
                file_info['has_version'] = 'version' in content if isinstance(content, dict) else False
                file_info['has_actions'] = 'actions' in content if isinstance(content, dict) else False
                file_info['has_sprints'] = 'sprints' in content if isinstance(content, dict) else False
                file_info['keys'] = list(content.keys()) if isinstance(content, dict) else []
                
                self.check_yaml_gaps(content, file_info)
                self.results['yaml_files'].append(file_info)
        except Exception as e:
            file_info['error'] = str(e)
            self.results['yaml_files'].append(file_info)
    
    def analyze_json(self, file_path, file_info):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                file_info['content_type'] = 'json'
                file_info['has_metadata'] = 'metadata' in content if isinstance(content, dict) else False
                file_info['has_phase'] = 'phase' in content if isinstance(content, dict) else False
                file_info['has_iteration'] = 'iteration' in content if isinstance(content, dict) else False
                file_info['keys'] = list(content.keys()) if isinstance(content, dict) else []
                
                self.check_json_gaps(content, file_info)
                self.results['json_files'].append(file_info)
        except Exception as e:
            file_info['error'] = str(e)
            self.results['json_files'].append(file_info)
    
    def analyze_markdown(self, file_path, file_info):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                file_info['content_type'] = 'markdown'
                file_info['line_count'] = len(content.split('\n'))
                file_info['has_headers'] = bool(re.search(r'^#+\s', content, re.MULTILINE))
                file_info['has_code_blocks'] = '```' in content
                file_info['has_tables'] = '|' in content
                
                self.check_markdown_gaps(content, file_info)
                self.results['markdown_files'].append(file_info)
        except Exception as e:
            file_info['error'] = str(e)
            self.results['markdown_files'].append(file_info)
    
    def check_yaml_gaps(self, content, file_info):
        if not isinstance(content, dict):
            return
            
        gaps = []
        
        if 'actions' in content:
            for action_name, action_data in content.get('actions', {}).items():
                if 'inputs' not in action_data:
                    gaps.append(f"Action '{action_name}' missing 'inputs'")
                if 'outputs' not in action_data:
                    gaps.append(f"Action '{action_name}' missing 'outputs'")
                if 'command' not in action_data:
                    gaps.append(f"Action '{action_name}' missing 'command'")
        
        if 'sprints' in content:
            for sprint_name, sprint_data in content.get('sprints', {}).items():
                if 'tasks' not in sprint_data:
                    gaps.append(f"Sprint '{sprint_name}' missing 'tasks'")
                if 'owner' not in sprint_data:
                    gaps.append(f"Sprint '{sprint_name}' missing 'owner'")
        
        if gaps:
            self.results['gaps']['yaml'].extend([{'file': file_info['path'], 'gap': gap} for gap in gaps])
    
    def check_json_gaps(self, content, file_info):
        if not isinstance(content, dict):
            return
            
        gaps = []
        
        if 'phase' in file_info['name']:
            if 'metadata' not in content:
                gaps.append("Missing 'metadata' section")
            if 'timestamp' not in content:
                gaps.append("Missing 'timestamp'")
            if 'version' not in content:
                gaps.append("Missing 'version'")
        
        if 'iteration' in file_info['name']:
            if 'iteration_number' not in content:
                gaps.append("Missing 'iteration_number'")
            if 'convergence_metrics' not in content:
                gaps.append("Missing 'convergence_metrics'")
        
        if gaps:
            self.results['gaps']['json'].extend([{'file': file_info['path'], 'gap': gap} for gap in gaps])
    
    def check_markdown_gaps(self, content, file_info):
        gaps = []
        
        if not re.search(r'^#\s+', content, re.MULTILINE):
            gaps.append("Missing main title (# header)")
        
        if 'DMAIC' in file_info['name'].upper() or 'DOW' in file_info['name'].upper():
            if 'recursive' not in content.lower():
                gaps.append("Missing 'recursive' concept")
            if 'iteration' not in content.lower():
                gaps.append("Missing 'iteration' concept")
            if 'convergence' not in content.lower():
                gaps.append("Missing 'convergence' concept")
        
        if 'README' in file_info['name']:
            if '## Installation' not in content and '## Setup' not in content:
                gaps.append("Missing installation/setup section")
            if '## Usage' not in content:
                gaps.append("Missing usage section")
        
        if gaps:
            self.results['gaps']['markdown'].extend([{'file': file_info['path'], 'gap': gap} for gap in gaps])
    
    def calculate_statistics(self):
        all_files = self.results['yaml_files'] + self.results['json_files'] + self.results['markdown_files']
        
        self.results['statistics'] = {
            'total_files': len(all_files),
            'yaml_count': len(self.results['yaml_files']),
            'json_count': len(self.results['json_files']),
            'markdown_count': len(self.results['markdown_files']),
            'total_size': sum(f['size'] for f in all_files),
            'files_with_errors': len([f for f in all_files if 'error' in f]),
            'yaml_gaps': len(self.results['gaps']['yaml']),
            'json_gaps': len(self.results['gaps']['json']),
            'markdown_gaps': len(self.results['gaps']['markdown'])
        }
        
        sorted_files = sorted(all_files, key=lambda x: x['size'], reverse=True)
        self.results['top_30_files'] = sorted_files[:30]
    
    def generate_report(self, output_path):
        self.calculate_statistics()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# RECENT FILES ANALYSIS REPORT\n\n")
            f.write(f"**Analysis Date:** {datetime.now().isoformat()}\n")
            f.write(f"**Time Window:** Last {self.days} days\n\n")
            
            f.write("## STATISTICS\n\n")
            for key, value in self.results['statistics'].items():
                f.write(f"- **{key.replace('_', ' ').title()}:** {value}\n")
            
            f.write("\n## TOP 30 FILES BY SIZE\n\n")
            f.write("| Rank | File | Type | Size (KB) | Modified |\n")
            f.write("|------|------|------|-----------|----------|\n")
            for i, file_info in enumerate(self.results['top_30_files'], 1):
                size_kb = file_info['size'] / 1024
                f.write(f"| {i} | {file_info['name']} | {file_info['extension']} | {size_kb:.2f} | {file_info['modified'][:10]} |\n")
            
            f.write("\n## YAML FILES ANALYSIS\n\n")
            for file_info in self.results['yaml_files']:
                f.write(f"### {file_info['name']}\n")
                f.write(f"- **Path:** `{file_info['path']}`\n")
                f.write(f"- **Modified:** {file_info['modified']}\n")
                if 'error' in file_info:
                    f.write(f"- **Error:** {file_info['error']}\n")
                else:
                    f.write(f"- **Has Version:** {file_info.get('has_version', False)}\n")
                    f.write(f"- **Has Actions:** {file_info.get('has_actions', False)}\n")
                    f.write(f"- **Has Sprints:** {file_info.get('has_sprints', False)}\n")
                    keys = [str(k) for k in file_info.get('keys', [])]
                    f.write(f"- **Keys:** {', '.join(keys)}\n")
                f.write("\n")
            
            f.write("\n## JSON FILES ANALYSIS\n\n")
            for file_info in self.results['json_files'][:20]:
                f.write(f"### {file_info['name']}\n")
                f.write(f"- **Path:** `{file_info['path']}`\n")
                f.write(f"- **Modified:** {file_info['modified']}\n")
                if 'error' in file_info:
                    f.write(f"- **Error:** {file_info['error']}\n")
                else:
                    f.write(f"- **Has Metadata:** {file_info.get('has_metadata', False)}\n")
                    f.write(f"- **Has Phase:** {file_info.get('has_phase', False)}\n")
                    f.write(f"- **Has Iteration:** {file_info.get('has_iteration', False)}\n")
                f.write("\n")
            
            f.write("\n## MARKDOWN FILES ANALYSIS\n\n")
            for file_info in self.results['markdown_files'][:20]:
                f.write(f"### {file_info['name']}\n")
                f.write(f"- **Path:** `{file_info['path']}`\n")
                f.write(f"- **Modified:** {file_info['modified']}\n")
                f.write(f"- **Line Count:** {file_info.get('line_count', 0)}\n")
                f.write(f"- **Has Headers:** {file_info.get('has_headers', False)}\n")
                f.write(f"- **Has Code Blocks:** {file_info.get('has_code_blocks', False)}\n")
                f.write("\n")
            
            f.write("\n## IDENTIFIED GAPS\n\n")
            
            if self.results['gaps']['yaml']:
                f.write("### YAML Gaps\n\n")
                for gap in self.results['gaps']['yaml']:
                    f.write(f"- **{gap['file']}:** {gap['gap']}\n")
                f.write("\n")
            
            if self.results['gaps']['json']:
                f.write("### JSON Gaps\n\n")
                for gap in self.results['gaps']['json']:
                    f.write(f"- **{gap['file']}:** {gap['gap']}\n")
                f.write("\n")
            
            if self.results['gaps']['markdown']:
                f.write("### Markdown Gaps\n\n")
                for gap in self.results['gaps']['markdown']:
                    f.write(f"- **{gap['file']}:** {gap['gap']}\n")
                f.write("\n")

        json_output_path = str(output_path).replace('.md', '.json')
        with open(json_output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2)

if __name__ == "__main__":
    base_path = Path(__file__).parent.parent
    
    directories = [
        "deployment",
        "DMAIC_CANONICAL_DEEP_OUTPUT",
        "DMAIC_CANONICAL_OUTPUT",
        "DMAIC_CANONICAL_TEST",
        "dmaic_metrics",
        "DMAIC_PRODUCTION_FULL",
        "DMAIC_PRODUCTION_OUTPUT",
        "DMAIC_SAMPLE_TEST",
        "DMAIC_TEST_OUTPUT",
        "DMAIC_TEST_SAMPLE",
        "DMAIC_V2_OUTPUT",
        "DMAIC_V2.3_ITERATION_1",
        "DMAIC_V2.3_ITERATION_2",
        "DMAIC_V2.3_ITERATION_3",
        "DMAIC_V3",
        "DASHBOARDS_V2.3",
        "DOW",
        "docs",
        "docs_versioned"
    ]
    
    analyzer = RecentFilesAnalyzer(base_path, days=7)
    analyzer.scan_directories(directories)
    
    output_path = base_path / "DMAIC_V3" / "RECENT_FILES_ANALYSIS.md"
    analyzer.generate_report(output_path)
    
    print(f"Analysis complete. Report saved to: {output_path}")
    print(f"Total files analyzed: {analyzer.results['statistics']['total_files']}")
    print(f"YAML files: {analyzer.results['statistics']['yaml_count']}")
    print(f"JSON files: {analyzer.results['statistics']['json_count']}")
    print(f"Markdown files: {analyzer.results['statistics']['markdown_count']}")
    print(f"Total gaps found: {sum(len(v) for v in analyzer.results['gaps'].values())}")
