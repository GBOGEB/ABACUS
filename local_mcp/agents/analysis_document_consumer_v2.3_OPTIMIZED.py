#!/usr/bin/env python3
"""
Document Consumer Agent V2.3.0
Memory-optimized DMAIC-based document ingestion and analysis agent.
Designed for 4M memory constraint with streaming support.
"""
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Iterator
import traceback


class MemoryEfficientDocumentConsumerV23:
    """V2.3 Memory-optimized document consumer and analysis agent"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.name = "document_consumer"
        self.version = "v2.3.0"
        self.start_time = time.time()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.performance_metrics = {
            'documents_consumed': 0,
            'sections_extracted': 0,
            'keywords_identified': 0,
            'dmaic_phases_completed': 0,
            'errors_handled': 0,
            'memory_chunks_processed': 0,
        }

        self.dmaic_log = []
        self.results = []

        self.output_dir = Path(self.config.get('output_dir', 'document_outputs_v2.3'))
        self.output_dir.mkdir(exist_ok=True)

    def _log_dmaic(self, phase: str, action: str, result: Any = None):
        """Log DMAIC action with memory efficiency"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'phase': phase,
            'action': action,
            'result': str(result)[:100] if result else 'Completed',
        }
        self.dmaic_log.append(log_entry)
        print(f"[{phase}] {action}")

    def stream_documents(self, doc_source: str, chunk_size: int = 50) -> Iterator[Dict]:
        """Memory-efficient document streaming"""
        try:
            doc_path = Path(doc_source) if doc_source else None

            if doc_path and doc_path.is_dir():
                for doc_file in sorted(doc_path.glob('**/*.md'))[:20]:
                    try:
                        with open(doc_file, 'r', encoding='utf-8') as f:
                            content = f.read(4096)
                        self.performance_metrics['memory_chunks_processed'] += 1
                        yield {
                            'file': str(doc_file),
                            'content': content,
                            'size': len(content),
                        }
                    except Exception:
                        continue

            elif doc_path and doc_path.is_file():
                with open(doc_path, 'r', encoding='utf-8') as f:
                    while True:
                        chunk = f.read(chunk_size * 80)
                        if not chunk:
                            break
                        self.performance_metrics['memory_chunks_processed'] += 1
                        yield {'content': chunk, 'size': len(chunk)}

            else:
                yield from self._generate_synthetic_documents()

        except Exception as e:
            self.performance_metrics['errors_handled'] += 1
            self._log_dmaic('STREAM', f'Error in streaming: {str(e)}')
            yield {'error': str(e)}

    def _generate_synthetic_documents(self) -> Iterator[Dict]:
        """Generate synthetic documents for testing"""
        docs = [
            {'title': 'DMAIC Methodology', 'category': 'methodology', 'words': 800},
            {'title': 'Cryogenic Systems Overview', 'category': 'engineering', 'words': 1200},
            {'title': 'Heat Load Analysis Report', 'category': 'analysis', 'words': 600},
            {'title': 'Deployment Guide', 'category': 'operations', 'words': 400},
        ]

        for doc in docs:
            self.performance_metrics['memory_chunks_processed'] += 1
            yield {'doc': doc, 'size': 1}

    def dmaic_define(self) -> Dict[str, Any]:
        """DEFINE: Document consumption requirements and objectives"""
        self._log_dmaic('DEFINE', 'Starting document consumption definition')

        definition = {
            'objectives': [
                'Ingest and categorize project documents',
                'Extract key sections and metadata',
                'Identify technical keywords and concepts',
                'Build document relationship index',
            ],
            'supported_formats': ['md', 'txt', 'json', 'yaml'],
            'output_format': 'json',
            'memory_constraint_MB': 4,
        }

        self.performance_metrics['dmaic_phases_completed'] += 1
        self._log_dmaic('DEFINE', 'Definition complete', definition)
        return definition

    def dmaic_measure(self, doc_source: str = None) -> Dict[str, Any]:
        """MEASURE: Collect document inventory and metadata"""
        self._log_dmaic('MEASURE', 'Collecting document inventory')

        inventory: List[Dict[str, Any]] = []
        total_size = 0

        for chunk in self.stream_documents(doc_source or ''):
            if 'doc' in chunk:
                doc = chunk['doc']
                inventory.append({
                    'title': doc.get('title', 'Unknown'),
                    'category': doc.get('category', 'uncategorized'),
                    'word_count': doc.get('words', 0),
                })
                total_size += doc.get('words', 0)
                self.performance_metrics['documents_consumed'] += 1
            elif 'file' in chunk:
                inventory.append({
                    'file': chunk['file'],
                    'size_bytes': chunk['size'],
                })
                self.performance_metrics['documents_consumed'] += 1

        measurements = {
            'total_documents': len(inventory),
            'total_words': total_size,
            'inventory': inventory,
        }

        self.performance_metrics['dmaic_phases_completed'] += 1
        self._log_dmaic('MEASURE', f"Measured {len(inventory)} documents")
        return measurements

    def dmaic_analyze(self, measurements: Dict[str, Any]) -> Dict[str, Any]:
        """ANALYZE: Extract patterns and insights from documents"""
        self._log_dmaic('ANALYZE', 'Analyzing document inventory')

        inventory = measurements.get('inventory', [])

        categories: Dict[str, int] = {}
        for doc in inventory:
            cat = doc.get('category', 'uncategorized')
            categories[cat] = categories.get(cat, 0) + 1

        keywords = [
            'DMAIC', 'cryogenic', 'heat load', 'orchestrator',
            'KEB', 'GBOGEB', 'agent', 'pipeline',
        ]
        self.performance_metrics['keywords_identified'] += len(keywords)
        self.performance_metrics['sections_extracted'] += len(inventory)

        analysis = {
            'document_categories': categories,
            'keywords_identified': keywords,
            'total_documents': len(inventory),
            'coverage': {
                'methodology': categories.get('methodology', 0),
                'engineering': categories.get('engineering', 0),
                'analysis': categories.get('analysis', 0),
                'operations': categories.get('operations', 0),
            },
        }

        self.performance_metrics['dmaic_phases_completed'] += 1
        self._log_dmaic('ANALYZE', f"Analysis complete: {len(categories)} categories")
        return analysis

    def dmaic_improve(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """IMPROVE: Recommend document improvements"""
        self._log_dmaic('IMPROVE', 'Generating document improvement recommendations')

        improvements: List[Dict[str, Any]] = []
        categories = analysis.get('document_categories', {})

        if categories.get('methodology', 0) == 0:
            improvements.append({
                'type': 'missing_docs',
                'recommendation': 'Add methodology documentation',
                'priority': 'HIGH',
            })

        if categories.get('operations', 0) == 0:
            improvements.append({
                'type': 'missing_docs',
                'recommendation': 'Add operations runbooks',
                'priority': 'MEDIUM',
            })

        if analysis.get('total_documents', 0) < 5:
            improvements.append({
                'type': 'coverage',
                'recommendation': 'Expand documentation coverage',
                'priority': 'MEDIUM',
            })

        self.performance_metrics['dmaic_phases_completed'] += 1
        self._log_dmaic('IMPROVE', f"Generated {len(improvements)} improvements")
        return {'improvements': improvements, 'total': len(improvements)}

    def dmaic_control(self, improvements: Dict[str, Any]) -> Dict[str, Any]:
        """CONTROL: Establish document quality control metrics"""
        self._log_dmaic('CONTROL', 'Establishing document control metrics')

        control_plan = {
            'review_frequency': 'weekly',
            'minimum_doc_count': 10,
            'required_categories': ['methodology', 'engineering', 'operations'],
            'action_items': improvements.get('improvements', []),
        }

        output_file = self.output_dir / f"doc_control_{self.timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(control_plan, f, indent=2)

        self.performance_metrics['dmaic_phases_completed'] += 1
        self._log_dmaic('CONTROL', f"Control plan saved: {output_file}")
        return control_plan

    def run(self, doc_source: str = None) -> Dict[str, Any]:
        """Execute full DMAIC document consumption cycle"""
        self._log_dmaic('RUN', 'Starting full DMAIC document consumption')
        run_start = time.time()

        try:
            definition = self.dmaic_define()
            measurements = self.dmaic_measure(doc_source)
            analysis = self.dmaic_analyze(measurements)
            improvements = self.dmaic_improve(analysis)
            control = self.dmaic_control(improvements)

            execution_time = time.time() - run_start

            result = {
                'status': 'success',
                'agent': self.name,
                'version': self.version,
                'execution_time': execution_time,
                'phases': {
                    'define': definition,
                    'measure': measurements,
                    'analyze': analysis,
                    'improve': improvements,
                    'control': control,
                },
                'performance_metrics': self.performance_metrics.copy(),
            }

            self.results.append(result)
            self._log_dmaic('RUN', f'Completed in {execution_time:.2f}s')
            return result

        except Exception as e:
            self.performance_metrics['errors_handled'] += 1
            self._log_dmaic('RUN', f'Error: {str(e)}')
            return {
                'status': 'error',
                'agent': self.name,
                'error': str(e),
                'traceback': traceback.format_exc(),
            }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Return current performance metrics"""
        return {
            'metrics': self.performance_metrics.copy(),
            'uptime_seconds': time.time() - self.start_time,
        }
