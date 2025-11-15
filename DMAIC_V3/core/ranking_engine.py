from typing import Any
"""
DMAIC V3 - Ranking Engine
Self-ranking and global ranking system for files, modules, and executions

Version: 1.0.0
Date: 2025-01-12
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum


class RankingCategory(Enum):
    """Categories for ranking"""
    QUALITY = "quality"
    COMPLEXITY = "complexity"
    MAINTAINABILITY = "maintainability"
    PERFORMANCE = "performance"
    COVERAGE = "coverage"
    DOCUMENTATION = "documentation"
    DEPENDENCIES = "dependencies"
    SECURITY = "security"


class RankingScope(Enum):
    """Scope of ranking"""
    FILE = "file"
    MODULE = "module"
    PACKAGE = "package"
    WORKSPACE = "workspace"
    EXECUTION = "execution"
    PHASE = "phase"


@dataclass
class RankingScore:
    """Individual ranking score"""
    category: str
    score: float  # 0.0 to 1.0
    weight: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    evidence: Dict[str, Any]
    timestamp: str
    version: str = "1.0.0"
    
    def weighted_score(self) -> float:
        """Calculate weighted score"""
        return self.score * self.weight * self.confidence


@dataclass
class GlobalRanking:
    """Global ranking for an entity"""
    entity_id: str
    entity_type: str  # file, module, package, etc.
    entity_path: str
    overall_score: float  # 0.0 to 1.0
    category_scores: Dict[str, RankingScore]
    rank_position: int  # 1-based ranking
    percentile: float  # 0.0 to 100.0
    total_entities: int
    timestamp: str
    version: str = "1.0.0"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self) -> Any:
        """TODO: Add function description"""

        if self.metadata is None:
            self.metadata = {}


@dataclass
class SelfRanking:
    """Self-assessment ranking"""
    entity_id: str
    entity_path: str
    self_score: float  # 0.0 to 1.0
    improvement_areas: List[str]
    strengths: List[str]
    recommendations: List[str]
    confidence: float  # 0.0 to 1.0
    timestamp: str
    version: str = "1.0.0"


class RankingEngine:
    """
    Comprehensive ranking engine for DMAIC V3
    
    Features:
    - Self-ranking: Entity assesses itself
    - Global ranking: Compare across all entities
    - Multi-category scoring
    - Weighted aggregation
    - Confidence tracking
    - Historical trends
    - Percentile calculation
    """
    
    def __init__(self, workspace_root: Path, db_path: Optional[Path] = None):
        """
        Initialize ranking engine
        
        Args:
            workspace_root: Root directory of workspace
            db_path: Path to SQLite database (default: .dmaic/rankings.db)
        """
        self.workspace_root = Path(workspace_root)
        self.db_path = db_path or (self.workspace_root / ".dmaic" / "rankings.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.version = "1.0.0"
        self.timestamp = datetime.now().isoformat()
        
        # Default weights for categories
        self.default_weights = {
            RankingCategory.QUALITY.value: 0.20,
            RankingCategory.COMPLEXITY.value: 0.15,
            RankingCategory.MAINTAINABILITY.value: 0.20,
            RankingCategory.PERFORMANCE.value: 0.10,
            RankingCategory.COVERAGE.value: 0.15,
            RankingCategory.DOCUMENTATION.value: 0.10,
            RankingCategory.DEPENDENCIES.value: 0.05,
            RankingCategory.SECURITY.value: 0.05,
        }
        
        self._init_database()
    
    def _init_database(self) -> Any:
        """Initialize SQLite database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Global rankings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS global_rankings (
                entity_id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                entity_path TEXT NOT NULL,
                overall_score REAL NOT NULL,
                rank_position INTEGER NOT NULL,
                percentile REAL NOT NULL,
                total_entities INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                version TEXT NOT NULL,
                metadata TEXT
            )
        """)
        
        # Category scores table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS category_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT NOT NULL,
                category TEXT NOT NULL,
                score REAL NOT NULL,
                weight REAL NOT NULL,
                confidence REAL NOT NULL,
                evidence TEXT,
                timestamp TEXT NOT NULL,
                version TEXT NOT NULL,
                FOREIGN KEY (entity_id) REFERENCES global_rankings(entity_id)
            )
        """)
        
        # Self rankings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS self_rankings (
                entity_id TEXT PRIMARY KEY,
                entity_path TEXT NOT NULL,
                self_score REAL NOT NULL,
                improvement_areas TEXT,
                strengths TEXT,
                recommendations TEXT,
                confidence REAL NOT NULL,
                timestamp TEXT NOT NULL,
                version TEXT NOT NULL
            )
        """)
        
        # Ranking history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ranking_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT NOT NULL,
                overall_score REAL NOT NULL,
                rank_position INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                version TEXT NOT NULL
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_type ON global_rankings(entity_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rank_position ON global_rankings(rank_position)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_overall_score ON global_rankings(overall_score DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON category_scores(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_entity ON ranking_history(entity_id)")
        
        conn.commit()
        conn.close()
    
    def calculate_self_ranking(self, entity_path: Path, 
                              metrics: Dict[str, Any]) -> SelfRanking:
        """
        Calculate self-ranking for an entity
        
        Args:
            entity_path: Path to entity (file, module, etc.)
            metrics: Metrics dictionary with quality indicators
            
        Returns:
            SelfRanking object
        """
        entity_id = self._generate_entity_id(entity_path)
        
        # Extract metrics
        quality_score = metrics.get('quality_score', 0.5)
        complexity = metrics.get('complexity', 0.5)
        coverage = metrics.get('test_coverage', 0.0)
        doc_coverage = metrics.get('doc_coverage', 0.0)
        
        # Calculate self score (weighted average)
        self_score = (
            quality_score * 0.3 +
            (1.0 - complexity) * 0.2 +  # Lower complexity is better
            coverage * 0.3 +
            doc_coverage * 0.2
        )
        
        # Identify improvement areas
        improvement_areas = []
        if quality_score < 0.7:
            improvement_areas.append("Code quality needs improvement")
        if complexity > 0.7:
            improvement_areas.append("High complexity - consider refactoring")
        if coverage < 0.8:
            improvement_areas.append("Test coverage below 80%")
        if doc_coverage < 0.6:
            improvement_areas.append("Documentation coverage below 60%")
        
        # Identify strengths
        strengths = []
        if quality_score >= 0.8:
            strengths.append("High code quality")
        if complexity <= 0.3:
            strengths.append("Low complexity - maintainable code")
        if coverage >= 0.8:
            strengths.append("Excellent test coverage")
        if doc_coverage >= 0.7:
            strengths.append("Well documented")
        
        # Generate recommendations
        recommendations = []
        if not improvement_areas:
            recommendations.append("Maintain current quality standards")
        else:
            if quality_score < 0.7:
                recommendations.append("Run linters and fix code quality issues")
            if complexity > 0.7:
                recommendations.append("Break down complex functions into smaller units")
            if coverage < 0.8:
                recommendations.append("Add unit tests to increase coverage")
            if doc_coverage < 0.6:
                recommendations.append("Add docstrings and inline comments")
        
        # Calculate confidence based on data availability
        confidence = min(1.0, sum([
            0.25 if 'quality_score' in metrics else 0.0,
            0.25 if 'complexity' in metrics else 0.0,
            0.25 if 'test_coverage' in metrics else 0.0,
            0.25 if 'doc_coverage' in metrics else 0.0,
        ]))
        
        self_ranking = SelfRanking(
            entity_id=entity_id,
            entity_path=str(entity_path),
            self_score=self_score,
            improvement_areas=improvement_areas,
            strengths=strengths,
            recommendations=recommendations,
            confidence=confidence,
            timestamp=datetime.now().isoformat(),
            version=self.version
        )
        
        self._save_self_ranking(self_ranking)
        return self_ranking
    
    def calculate_global_ranking(self, entity_path: Path, 
                                entity_type: str,
                                category_metrics: Dict[str, Dict[str, Any]],
                                custom_weights: Optional[Dict[str, float]] = None) -> GlobalRanking:
        """
        Calculate global ranking for an entity
        
        Args:
            entity_path: Path to entity
            entity_type: Type of entity (file, module, package, etc.)
            category_metrics: Metrics for each category
            custom_weights: Optional custom weights for categories
            
        Returns:
            GlobalRanking object
        """
        entity_id = self._generate_entity_id(entity_path)
        weights = custom_weights or self.default_weights
        
        # Calculate category scores
        category_scores = {}
        weighted_sum = 0.0
        total_weight = 0.0
        
        for category, metrics in category_metrics.items():
            score = metrics.get('score', 0.5)
            confidence = metrics.get('confidence', 1.0)
            evidence = metrics.get('evidence', {})
            weight = weights.get(category, 0.1)
            
            ranking_score = RankingScore(
                category=category,
                score=score,
                weight=weight,
                confidence=confidence,
                evidence=evidence,
                timestamp=datetime.now().isoformat(),
                version=self.version
            )
            
            category_scores[category] = ranking_score
            weighted_sum += ranking_score.weighted_score()
            total_weight += weight * confidence
        
        # Calculate overall score
        overall_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        # Get rank position and percentile (will be updated after all entities are ranked)
        rank_position = 0
        percentile = 0.0
        total_entities = 0
        
        global_ranking = GlobalRanking(
            entity_id=entity_id,
            entity_type=entity_type,
            entity_path=str(entity_path),
            overall_score=overall_score,
            category_scores=category_scores,
            rank_position=rank_position,
            percentile=percentile,
            total_entities=total_entities,
            timestamp=datetime.now().isoformat(),
            version=self.version,
            metadata={
                'weights': weights,
                'total_weight': total_weight
            }
        )
        
        self._save_global_ranking(global_ranking)
        return global_ranking
    
    def update_rankings_for_all_entities(self, entity_type -> Any: Optional[str] = None):
        """
        Update rank positions and percentiles for all entities
        
        Args:
            entity_type: Optional filter by entity type
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build query
        query = "SELECT entity_id, overall_score FROM global_rankings"
        params = []
        if entity_type:
            query += " WHERE entity_type = ?"
            params.append(entity_type)
        query += " ORDER BY overall_score DESC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        total_entities = len(results)
        
        # Update rank positions and percentiles
        for rank_position, (entity_id, overall_score) in enumerate(results, start=1):
            percentile = ((total_entities - rank_position + 1) / total_entities) * 100.0
            
            cursor.execute("""
                UPDATE global_rankings
                SET rank_position = ?, percentile = ?, total_entities = ?
                WHERE entity_id = ?
            """, (rank_position, percentile, total_entities, entity_id))
            
            # Add to history
            cursor.execute("""
                INSERT INTO ranking_history (entity_id,
                    overall_score,
                    rank_position,
                    timestamp,
                    version)
                VALUES (?, ?, ?, ?, ?)
            """, (entity_id, overall_score, rank_position, datetime.now().isoformat(), self.version))
        
        conn.commit()
        conn.close()
    
    def get_top_ranked(self, entity_type: Optional[str] = None, 
                      limit: int = 10) -> List[GlobalRanking]:
        """
        Get top ranked entities
        
        Args:
            entity_type: Optional filter by entity type
            limit: Number of results to return
            
        Returns:
            List of GlobalRanking objects
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM global_rankings"
        params = []
        if entity_type:
            query += " WHERE entity_type = ?"
            params.append(entity_type)
        query += " ORDER BY overall_score DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        rankings = []
        for row in results:
            # Load category scores
            category_scores = self._load_category_scores(row[0])
            
            ranking = GlobalRanking(
                entity_id=row[0],
                entity_type=row[1],
                entity_path=row[2],
                overall_score=row[3],
                category_scores=category_scores,
                rank_position=row[4],
                percentile=row[5],
                total_entities=row[6],
                timestamp=row[7],
                version=row[8],
                metadata=json.loads(row[9]) if row[9] else {}
            )
            rankings.append(ranking)
        
        return rankings
    
    def get_ranking_history(self, entity_id: str, 
                           limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get ranking history for an entity
        
        Args:
            entity_id: Entity identifier
            limit: Number of historical records to return
            
        Returns:
            List of historical ranking records
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT overall_score, rank_position, timestamp, version
            FROM ranking_history
            WHERE entity_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (entity_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        history = []
        for row in results:
            history.append({
                'overall_score': row[0],
                'rank_position': row[1],
                'timestamp': row[2],
                'version': row[3]
            })
        
        return history
    
    def generate_ranking_report(self, output_path -> Any: Path, 
                               entity_type: Optional[str] = None):
        """
        Generate comprehensive ranking report
        
        Args:
            output_path: Path to save report (JSON)
            entity_type: Optional filter by entity type
        """
        top_ranked = self.get_top_ranked(entity_type=entity_type, limit=50)
        
        report = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'version': self.version,
                'workspace_root': str(self.workspace_root),
                'entity_type_filter': entity_type,
                'total_entities': top_ranked[0].total_entities if top_ranked else 0
            },
            'top_ranked': [],
            'statistics': self._calculate_statistics(entity_type)
        }
        
        for ranking in top_ranked:
            report['top_ranked'].append({
                'entity_id': ranking.entity_id,
                'entity_type': ranking.entity_type,
                'entity_path': ranking.entity_path,
                'overall_score': ranking.overall_score,
                'rank_position': ranking.rank_position,
                'percentile': ranking.percentile,
                'category_scores': {
                    cat: {
                        'score': score.score,
                        'weight': score.weight,
                        'confidence': score.confidence,
                        'weighted_score': score.weighted_score()
                    }
                    for cat, score in ranking.category_scores.items()
                },
                'timestamp': ranking.timestamp
            })
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
    
    def _generate_entity_id(self, entity_path: Path) -> str:
        """Generate unique entity ID"""
        rel_path = entity_path.relative_to(self.workspace_root) if entity_path.is_relative_to(self.workspace_root) else entity_path
        return str(rel_path).replace('\\', '/').replace('/', '__')
    
    def _save_self_ranking(self, self_ranking -> Any: SelfRanking):
        """Save self ranking to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO self_rankings
            (entity_id, entity_path, self_score, improvement_areas, strengths, 
             recommendations, confidence, timestamp, version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self_ranking.entity_id,
            self_ranking.entity_path,
            self_ranking.self_score,
            json.dumps(self_ranking.improvement_areas),
            json.dumps(self_ranking.strengths),
            json.dumps(self_ranking.recommendations),
            self_ranking.confidence,
            self_ranking.timestamp,
            self_ranking.version
        ))
        
        conn.commit()
        conn.close()
    
    def _save_global_ranking(self, global_ranking -> Any: GlobalRanking):
        """Save global ranking to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Save global ranking
        cursor.execute("""
            INSERT OR REPLACE INTO global_rankings
            (entity_id, entity_type, entity_path, overall_score, rank_position,
             percentile, total_entities, timestamp, version, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            global_ranking.entity_id,
            global_ranking.entity_type,
            global_ranking.entity_path,
            global_ranking.overall_score,
            global_ranking.rank_position,
            global_ranking.percentile,
            global_ranking.total_entities,
            global_ranking.timestamp,
            global_ranking.version,
            json.dumps(global_ranking.metadata)
        ))
        
        # Save category scores
        for category, score in global_ranking.category_scores.items():
            cursor.execute("""
                INSERT INTO category_scores
                (entity_id, category, score, weight, confidence, evidence, timestamp, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                global_ranking.entity_id,
                category,
                score.score,
                score.weight,
                score.confidence,
                json.dumps(score.evidence),
                score.timestamp,
                score.version
            ))
        
        conn.commit()
        conn.close()
    
    def _load_category_scores(self, entity_id: str) -> Dict[str, RankingScore]:
        """Load category scores for an entity"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT category, score, weight, confidence, evidence, timestamp, version
            FROM category_scores
            WHERE entity_id = ?
        """, (entity_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        category_scores = {}
        for row in results:
            category_scores[row[0]] = RankingScore(
                category=row[0],
                score=row[1],
                weight=row[2],
                confidence=row[3],
                evidence=json.loads(row[4]) if row[4] else {},
                timestamp=row[5],
                version=row[6]
            )
        
        return category_scores
    
    def _calculate_statistics(self, entity_type: Optional[str] = None) -> Dict[str, Any]:
        """Calculate ranking statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT overall_score FROM global_rankings"
        params = []
        if entity_type:
            query += " WHERE entity_type = ?"
            params.append(entity_type)
        
        cursor.execute(query, params)
        scores = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not scores:
            return {}
        
        return {
            'count': len(scores),
            'mean': sum(scores) / len(scores),
            'min': min(scores),
            'max': max(scores),
            'median': sorted(scores)[len(scores) // 2],
            'std_dev': (sum((x - sum(scores) / len(scores)) ** 2 for x in scores) / len(scores)) ** 0.5
        }
