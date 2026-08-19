"""
# Version: 1.0.0
# Date: 2025-11-24
# Description: Auto-generated version header
"""

"""
Self-Improvement and Ranking System for Test Suite
Implements self-ranking, global ranking, and continuous improvement
"""

import pytest
import pytest_asyncio
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum


class RankingCategory(Enum):
    """Test ranking categories"""
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    COVERAGE = "coverage"
    COMPLEXITY = "complexity"
    MAINTAINABILITY = "maintainability"


@dataclass
class TestRanking:
    """Individual test ranking"""
    test_name: str
    category: RankingCategory
    score: float
    rank: int
    total_tests: int
    percentile: float
    timestamp: str
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['category'] = self.category.value
        return data


@dataclass
class GlobalRanking:
    """Global test suite ranking"""
    suite_name: str
    overall_score: float
    global_rank: int
    total_suites: int
    category_scores: Dict[str, float]
    improvement_trend: str
    timestamp: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


class SelfImprovementEngine:
    """
    Self-improvement engine for test suite optimization
    Analyzes performance, identifies weaknesses, and suggests improvements
    """
    
    def __init__(self, workspace_path: Path = Path(".")):
        self.workspace_path = workspace_path
        self.metrics_dir = workspace_path / "test_metrics"
        self.metrics_dir.mkdir(exist_ok=True)
        
        self.test_rankings: List[TestRanking] = []
        self.global_rankings: List[GlobalRanking] = []
        self.improvement_history: List[Dict] = []
        
    def analyze_test_performance(self, test_results: List[Dict]) -> Dict:
        """Analyze test performance and identify improvement areas"""
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(test_results),
            "performance_metrics": {},
            "improvement_opportunities": [],
            "strengths": [],
            "weaknesses": []
        }
        
        # Calculate performance metrics
        durations = [r.get('duration', 0) for r in test_results]
        pass_count = sum(1 for r in test_results if r.get('status') == 'passed')
        
        analysis['performance_metrics'] = {
            "avg_duration": sum(durations) / len(durations) if durations else 0,
            "max_duration": max(durations) if durations else 0,
            "min_duration": min(durations) if durations else 0,
            "pass_rate": (pass_count / len(test_results) * 100) if test_results else 0
        }
        
        # Identify slow tests
        slow_tests = [r for r in test_results if r.get('duration', 0) > 1.0]
        if slow_tests:
            analysis['improvement_opportunities'].append({
                "type": "performance",
                "description": f"{len(slow_tests)} tests exceed 1s duration",
                "recommendation": "Optimize slow tests or use mocking",
                "priority": "high"
            })
        
        # Identify flaky tests
        failed_tests = [r for r in test_results if r.get('status') == 'failed']
        if failed_tests:
            analysis['weaknesses'].append({
                "type": "reliability",
                "description": f"{len(failed_tests)} tests failed",
                "impact": "high"
            })
        
        # Identify strengths
        if analysis['performance_metrics']['pass_rate'] > 95:
            analysis['strengths'].append({
                "type": "reliability",
                "description": "High pass rate (>95%)",
                "value": analysis['performance_metrics']['pass_rate']
            })
        
        return analysis
    
    def rank_tests(self, test_results: List[Dict]) -> List[TestRanking]:
        """Rank tests based on multiple criteria"""
        rankings = []
        
        # Rank by performance
        sorted_by_duration = sorted(test_results, key=lambda x: x.get('duration', 0))
        for idx, test in enumerate(sorted_by_duration):
            ranking = TestRanking(
                test_name=test.get('name', 'unknown'),
                category=RankingCategory.PERFORMANCE,
                score=1.0 / (test.get('duration', 1) + 0.001),  # Inverse duration
                rank=idx + 1,
                total_tests=len(test_results),
                percentile=(idx + 1) / len(test_results) * 100,
                timestamp=datetime.now().isoformat()
            )
            rankings.append(ranking)
        
        self.test_rankings.extend(rankings)
        return rankings
    
    def calculate_global_rank(self, suite_name: str, test_results: List[Dict]) -> GlobalRanking:
        """Calculate global ranking for test suite"""
        # Calculate category scores
        category_scores = {
            "performance": self._calculate_performance_score(test_results),
            "reliability": self._calculate_reliability_score(test_results),
            "coverage": self._calculate_coverage_score(),
            "complexity": self._calculate_complexity_score(test_results),
            "maintainability": self._calculate_maintainability_score()
        }
        
        # Calculate overall score (weighted average)
        weights = {
            "performance": 0.25,
            "reliability": 0.30,
            "coverage": 0.25,
            "complexity": 0.10,
            "maintainability": 0.10
        }
        
        overall_score = sum(
            category_scores[cat] * weights[cat]
            for cat in category_scores
        )
        
        # Determine improvement trend
        improvement_trend = self._calculate_improvement_trend()
        
        global_ranking = GlobalRanking(
            suite_name=suite_name,
            overall_score=round(overall_score, 2),
            global_rank=1,  # Would compare with other suites
            total_suites=1,
            category_scores=category_scores,
            improvement_trend=improvement_trend,
            timestamp=datetime.now().isoformat()
        )
        
        self.global_rankings.append(global_ranking)
        return global_ranking
    
    def suggest_improvements(self, analysis: Dict) -> List[Dict]:
        """Generate improvement suggestions based on analysis"""
        suggestions = []
        
        # Performance improvements
        if analysis['performance_metrics']['avg_duration'] > 0.5:
            suggestions.append({
                "category": "performance",
                "priority": "high",
                "suggestion": "Use pytest-xdist for parallel test execution",
                "expected_improvement": "50-70% reduction in total test time",
                "implementation": [
                    "Install pytest-xdist",
                    "Run tests with -n auto flag",
                    "Ensure tests are thread-safe"
                ]
            })
        
        # Reliability improvements
        if analysis['performance_metrics']['pass_rate'] < 95:
            suggestions.append({
                "category": "reliability",
                "priority": "critical",
                "suggestion": "Fix failing tests immediately",
                "expected_improvement": "Increase pass rate to >95%",
                "implementation": [
                    "Review failed test logs",
                    "Fix root causes",
                    "Add retry logic for flaky tests"
                ]
            })
        
        # Coverage improvements
        suggestions.append({
            "category": "coverage",
            "priority": "medium",
            "suggestion": "Increase code coverage to 80%+",
            "expected_improvement": "Better test coverage",
            "implementation": [
                "Identify uncovered code paths",
                "Write unit tests for core modules",
                "Add integration tests for workflows"
            ]
        })
        
        return suggestions
    
    async def apply_improvement(self, suggestion: Dict) -> Dict:
        """Apply an improvement suggestion"""
        result = {
            "suggestion": suggestion,
            "status": "applied",
            "timestamp": datetime.now().isoformat(),
            "before_metrics": {},
            "after_metrics": {}
        }
        
        # Simulate improvement application
        await asyncio.sleep(0.1)
        
        # Record improvement
        self.improvement_history.append(result)
        
        return result
    
    def track_improvement_progress(self) -> Dict:
        """Track improvement progress over time"""
        progress = {
            "timestamp": datetime.now().isoformat(),
            "total_improvements": len(self.improvement_history),
            "improvements_by_category": {},
            "success_rate": 0.0,
            "trend": "improving"
        }
        
        # Group by category
        for improvement in self.improvement_history:
            category = improvement['suggestion']['category']
            progress['improvements_by_category'][category] = \
                progress['improvements_by_category'].get(category, 0) + 1
        
        # Calculate success rate
        successful = sum(1 for i in self.improvement_history if i['status'] == 'applied')
        progress['success_rate'] = (successful / len(self.improvement_history) * 100) \
            if self.improvement_history else 0
        
        return progress
    
    # Helper methods
    def _calculate_performance_score(self, test_results: List[Dict]) -> float:
        """Calculate performance score (0-100)"""
        if not test_results:
            return 0.0
        
        durations = [r.get('duration', 0) for r in test_results]
        avg_duration = sum(durations) / len(durations)
        
        # Score: 100 for <0.1s, 0 for >2s
        if avg_duration < 0.1:
            return 100.0
        elif avg_duration > 2.0:
            return 0.0
        else:
            return 100.0 - ((avg_duration - 0.1) / 1.9 * 100)
    
    def _calculate_reliability_score(self, test_results: List[Dict]) -> float:
        """Calculate reliability score (0-100)"""
        if not test_results:
            return 0.0
        
        pass_count = sum(1 for r in test_results if r.get('status') == 'passed')
        return (pass_count / len(test_results)) * 100
    
    def _calculate_coverage_score(self) -> float:
        """Calculate coverage score (0-100)"""
        coverage_file = Path("coverage.json")
        if not coverage_file.exists():
            return 0.0
        
        try:
            with open(coverage_file) as f:
                data = json.load(f)
            return data.get('totals', {}).get('percent_covered', 0.0)
        except:
            return 0.0
    
    def _calculate_complexity_score(self, test_results: List[Dict]) -> float:
        """Calculate complexity score (0-100)"""
        # Lower complexity is better
        # Score based on average test complexity
        return 75.0  # Placeholder
    
    def _calculate_maintainability_score(self) -> float:
        """Calculate maintainability score (0-100)"""
        # Based on code quality, documentation, etc.
        return 80.0  # Placeholder
    
    def _calculate_improvement_trend(self) -> str:
        """Calculate improvement trend"""
        if len(self.improvement_history) < 2:
            return "stable"
        
        recent_improvements = self.improvement_history[-5:]
        successful = sum(1 for i in recent_improvements if i['status'] == 'applied')
        
        if successful >= 4:
            return "improving"
        elif successful <= 1:
            return "declining"
        else:
            return "stable"
    
    def generate_improvement_report(self) -> Dict:
        """Generate comprehensive improvement report"""
        report = {
            "report_type": "Self-Improvement Analysis",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_improvements": len(self.improvement_history),
                "success_rate": 0.0,
                "current_trend": "stable"
            },
            "rankings": {
                "test_rankings": [r.to_dict() for r in self.test_rankings[-10:]],
                "global_rankings": [r.to_dict() for r in self.global_rankings[-5:]]
            },
            "improvement_history": self.improvement_history[-10:],
            "recommendations": []
        }
        
        # Calculate success rate
        if self.improvement_history:
            successful = sum(1 for i in self.improvement_history if i['status'] == 'applied')
            report['summary']['success_rate'] = (successful / len(self.improvement_history)) * 100
        
        # Save report
        report_file = self.metrics_dir / f"improvement_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report


class TestSelfImprovement:
    """Tests for self-improvement system"""
    
    def test_performance_analysis(self):
        """Test performance analysis"""
        engine = SelfImprovementEngine()
        
        test_results = [
            {"name": "test1", "duration": 0.5, "status": "passed"},
            {"name": "test2", "duration": 1.5, "status": "passed"},
            {"name": "test3", "duration": 0.2, "status": "failed"}
        ]
        
        analysis = engine.analyze_test_performance(test_results)
        
        assert 'performance_metrics' in analysis
        assert 'improvement_opportunities' in analysis
        assert analysis['total_tests'] == 3
    
    def test_test_ranking(self):
        """Test test ranking system"""
        engine = SelfImprovementEngine()
        
        test_results = [
            {"name": "test1", "duration": 0.5, "status": "passed"},
            {"name": "test2", "duration": 0.2, "status": "passed"},
            {"name": "test3", "duration": 1.0, "status": "passed"}
        ]
        
        rankings = engine.rank_tests(test_results)
        
        assert len(rankings) == 3
        assert rankings[0].rank == 1
        assert rankings[0].category == RankingCategory.PERFORMANCE
    
    def test_global_ranking(self):
        """Test global ranking calculation"""
        engine = SelfImprovementEngine()
        
        test_results = [
            {"name": "test1", "duration": 0.5, "status": "passed"},
            {"name": "test2", "duration": 0.3, "status": "passed"}
        ]
        
        global_rank = engine.calculate_global_rank("test_suite", test_results)
        
        assert global_rank.suite_name == "test_suite"
        assert 0 <= global_rank.overall_score <= 100
        assert 'performance' in global_rank.category_scores
        assert 'reliability' in global_rank.category_scores
    
    def test_improvement_suggestions(self):
        """Test improvement suggestion generation"""
        engine = SelfImprovementEngine()
        
        analysis = {
            'performance_metrics': {
                'avg_duration': 0.8,
                'pass_rate': 90.0
            },
            'improvement_opportunities': [],
            'strengths': [],
            'weaknesses': []
        }
        
        suggestions = engine.suggest_improvements(analysis)
        
        assert len(suggestions) > 0
        assert all('category' in s for s in suggestions)
        assert all('priority' in s for s in suggestions)
    
    @pytest.mark.asyncio
    async def test_apply_improvement(self):
        """Test improvement application"""
        engine = SelfImprovementEngine()
        
        suggestion = {
            "category": "performance",
            "priority": "high",
            "suggestion": "Use parallel execution"
        }
        
        result = await engine.apply_improvement(suggestion)
        
        assert result['status'] == 'applied'
        assert 'timestamp' in result
    
    def test_improvement_tracking(self):
        """Test improvement progress tracking"""
        engine = SelfImprovementEngine()
        
        # Add some improvement history
        engine.improvement_history = [
            {"suggestion": {"category": "performance"}, "status": "applied"},
            {"suggestion": {"category": "reliability"}, "status": "applied"},
            {"suggestion": {"category": "coverage"}, "status": "applied"}
        ]
        
        progress = engine.track_improvement_progress()
        
        assert progress['total_improvements'] == 3
        assert progress['success_rate'] == 100.0
        assert 'improvements_by_category' in progress
    
    def test_improvement_report_generation(self):
        """Test improvement report generation"""
        engine = SelfImprovementEngine()
        
        report = engine.generate_improvement_report()
        
        assert report['report_type'] == "Self-Improvement Analysis"
        assert 'summary' in report
        assert 'rankings' in report
        assert 'improvement_history' in report
