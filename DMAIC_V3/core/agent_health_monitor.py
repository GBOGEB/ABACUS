"""
# Version: 1.0.0
# Date: 2025-11-25
# Description: Auto-generated version header
"""

"""
Agent Health Monitor - Real-time agent health tracking and alerting
Uses agent age data for actionable insights and decision-making
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    STALE = "stale"
    NEW = "new"
    MATURE = "mature"


class MaturityLevel(Enum):
    INFANT = "infant"
    YOUNG = "young"
    MATURE = "mature"
    VETERAN = "veteran"


@dataclass
class HealthAlert:
    agent_name: str
    severity: str
    message: str
    timestamp: str
    metric_value: float
    threshold: float
    recommendation: str


@dataclass
class AgentHealth:
    agent_name: str
    status: HealthStatus
    maturity: MaturityLevel
    health_score: float
    alerts: List[HealthAlert]
    metrics: Dict[str, Any]
    recommendations: List[str]


class AgentHealthMonitor:
    """
    Monitors agent health using age data and provides actionable insights
    """
    
    STALE_THRESHOLD_HOURS = 24
    PERFORMANCE_DEGRADATION_FACTOR = 1.5
    MIN_EXECUTIONS_FOR_ANALYSIS = 3
    
    MATURITY_THRESHOLDS = {
        'infant': 300,
        'young': 3600,
        'mature': 86400,
        'veteran': 604800
    }
    
    def __init__(self, agent_age_file: Path, config: Optional[Any] = None):
        self.agent_age_file = agent_age_file
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.alerts: List[HealthAlert] = []
        
    def load_agent_age_data(self) -> Dict[str, Any]:
        if not self.agent_age_file.exists():
            return {}
        
        with open(self.agent_age_file, 'r') as f:
            return json.load(f)
    
    def calculate_maturity(self, age_seconds: float) -> MaturityLevel:
        if age_seconds < self.MATURITY_THRESHOLDS['infant']:
            return MaturityLevel.INFANT
        elif age_seconds < self.MATURITY_THRESHOLDS['young']:
            return MaturityLevel.YOUNG
        elif age_seconds < self.MATURITY_THRESHOLDS['mature']:
            return MaturityLevel.MATURE
        else:
            return MaturityLevel.VETERAN
    
    def calculate_health_score(self, agent_data: Dict[str, Any]) -> float:
        score = 1.0
        
        first_exec = datetime.fromisoformat(agent_data['first_execution'])
        last_exec = datetime.fromisoformat(agent_data['last_execution'])
        age_seconds = (last_exec - first_exec).total_seconds()
        time_since_last = (datetime.now() - last_exec).total_seconds()
        
        if time_since_last > self.STALE_THRESHOLD_HOURS * 3600:
            score -= 0.5
        elif time_since_last > self.STALE_THRESHOLD_HOURS * 1800:
            score -= 0.2
        
        total_execs = agent_data['total_executions']
        if total_execs < 2:
            score -= 0.1
        
        if age_seconds > 0:
            exec_frequency = total_execs / (age_seconds / 3600)
            if exec_frequency < 0.1:
                score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    def check_stale_agents(self, agent_data: Dict[str, Any], agent_name: str) -> Optional[HealthAlert]:
        last_exec = datetime.fromisoformat(agent_data['last_execution'])
        time_since_last = (datetime.now() - last_exec).total_seconds() / 3600
        
        if time_since_last > self.STALE_THRESHOLD_HOURS:
            return HealthAlert(
                agent_name=agent_name,
                severity="warning",
                message=f"Agent hasn't executed in {time_since_last:.1f} hours",
                timestamp=datetime.now().isoformat(),
                metric_value=time_since_last,
                threshold=self.STALE_THRESHOLD_HOURS,
                recommendation=f"Consider re-running {agent_name} or investigating why it's not being triggered"
            )
        return None
    
    def check_performance_degradation(self, agent_data: Dict[str, Any], agent_name: str) -> Optional[HealthAlert]:
        if 'execution_times' not in agent_data or len(agent_data['execution_times']) < self.MIN_EXECUTIONS_FOR_ANALYSIS:
            return None
        
        exec_times = [datetime.fromisoformat(t) for t in agent_data['execution_times']]
        
        if len(exec_times) < 2:
            return None
        
        intervals = [(exec_times[i+1] - exec_times[i]).total_seconds() 
                    for i in range(len(exec_times)-1)]
        
        if len(intervals) < 2:
            return None
        
        recent_interval = intervals[-1]
        avg_interval = sum(intervals[:-1]) / len(intervals[:-1])
        
        if recent_interval > avg_interval * self.PERFORMANCE_DEGRADATION_FACTOR:
            return HealthAlert(
                agent_name=agent_name,
                severity="warning",
                message=f"Execution interval increased by {((recent_interval/avg_interval - 1) * 100):.1f}%",
                timestamp=datetime.now().isoformat(),
                metric_value=recent_interval,
                threshold=avg_interval,
                recommendation=f"Agent {agent_name} is being called less frequently. Check iteration logic."
            )
        
        return None
    
    def check_execution_frequency(self, agent_data: Dict[str, Any], agent_name: str) -> Optional[HealthAlert]:
        first_exec = datetime.fromisoformat(agent_data['first_execution'])
        last_exec = datetime.fromisoformat(agent_data['last_execution'])
        age_seconds = (last_exec - first_exec).total_seconds()
        
        if age_seconds < 60:
            return None
        
        total_execs = agent_data['total_executions']
        exec_frequency = total_execs / (age_seconds / 3600)
        
        if exec_frequency < 0.1 and total_execs > 2:
            return HealthAlert(
                agent_name=agent_name,
                severity="info",
                message=f"Low execution frequency: {exec_frequency:.2f} executions/hour",
                timestamp=datetime.now().isoformat(),
                metric_value=exec_frequency,
                threshold=0.1,
                recommendation=f"Agent {agent_name} executes infrequently. Consider if this is expected."
            )
        
        return None
    
    def analyze_agent_health(self, agent_name: str, agent_data: Dict[str, Any]) -> AgentHealth:
        first_exec = datetime.fromisoformat(agent_data['first_execution'])
        last_exec = datetime.fromisoformat(agent_data['last_execution'])
        age_seconds = (last_exec - first_exec).total_seconds()
        
        maturity = self.calculate_maturity(age_seconds)
        health_score = self.calculate_health_score(agent_data)
        
        alerts = []
        recommendations = []
        
        stale_alert = self.check_stale_agents(agent_data, agent_name)
        if stale_alert:
            alerts.append(stale_alert)
            recommendations.append(stale_alert.recommendation)
        
        perf_alert = self.check_performance_degradation(agent_data, agent_name)
        if perf_alert:
            alerts.append(perf_alert)
            recommendations.append(perf_alert.recommendation)
        
        freq_alert = self.check_execution_frequency(agent_data, agent_name)
        if freq_alert:
            alerts.append(freq_alert)
            recommendations.append(freq_alert.recommendation)
        
        if health_score < 0.5:
            status = HealthStatus.CRITICAL
        elif health_score < 0.7:
            status = HealthStatus.WARNING
        elif maturity == MaturityLevel.INFANT:
            status = HealthStatus.NEW
        elif maturity == MaturityLevel.VETERAN:
            status = HealthStatus.MATURE
        else:
            status = HealthStatus.HEALTHY
        
        time_since_last = (datetime.now() - last_exec).total_seconds() / 3600
        if time_since_last > self.STALE_THRESHOLD_HOURS:
            status = HealthStatus.STALE
        
        metrics = {
            'age_seconds': age_seconds,
            'age_hours': age_seconds / 3600,
            'age_days': age_seconds / 86400,
            'total_executions': agent_data['total_executions'],
            'execution_frequency': agent_data['total_executions'] / (age_seconds / 3600) if age_seconds > 0 else 0,
            'time_since_last_hours': time_since_last,
            'iterations': agent_data.get('iterations', [])
        }
        
        return AgentHealth(
            agent_name=agent_name,
            status=status,
            maturity=maturity,
            health_score=health_score,
            alerts=alerts,
            metrics=metrics,
            recommendations=recommendations
        )
    
    def monitor_all_agents(self) -> Dict[str, AgentHealth]:
        agent_age_data = self.load_agent_age_data()
        
        health_report = {}
        for agent_name, agent_data in agent_age_data.items():
            health = self.analyze_agent_health(agent_name, agent_data)
            health_report[agent_name] = health
            
            for alert in health.alerts:
                self.alerts.append(alert)
        
        return health_report
    
    def get_critical_alerts(self) -> List[HealthAlert]:
        return [a for a in self.alerts if a.severity == "critical"]
    
    def get_warning_alerts(self) -> List[HealthAlert]:
        return [a for a in self.alerts if a.severity == "warning"]
    
    def should_trigger_iteration(self, agent_name: str) -> Tuple[bool, str]:
        agent_age_data = self.load_agent_age_data()
        
        if agent_name not in agent_age_data:
            return True, "New agent - should execute"
        
        agent_data = agent_age_data[agent_name]
        health = self.analyze_agent_health(agent_name, agent_data)
        
        if health.status == HealthStatus.STALE:
            return True, f"Agent is stale ({health.metrics['time_since_last_hours']:.1f}h since last run)"
        
        if health.status == HealthStatus.CRITICAL:
            return True, f"Agent health critical (score: {health.health_score:.2f})"
        
        if health.maturity == MaturityLevel.INFANT and health.metrics['total_executions'] < 5:
            return True, "Infant agent needs more executions to mature"
        
        return False, "Agent healthy, no immediate iteration needed"
    
    def get_adaptive_strategy(self, agent_name: str) -> Dict[str, Any]:
        agent_age_data = self.load_agent_age_data()
        
        if agent_name not in agent_age_data:
            return {
                'strategy': 'aggressive',
                'reason': 'New agent',
                'recommended_interval_minutes': 5,
                'priority': 'high'
            }
        
        agent_data = agent_age_data[agent_name]
        health = self.analyze_agent_health(agent_name, agent_data)
        
        if health.maturity == MaturityLevel.INFANT:
            return {
                'strategy': 'aggressive',
                'reason': 'Infant agent needs rapid iteration',
                'recommended_interval_minutes': 5,
                'priority': 'high'
            }
        elif health.maturity == MaturityLevel.YOUNG:
            return {
                'strategy': 'moderate',
                'reason': 'Young agent in development',
                'recommended_interval_minutes': 15,
                'priority': 'medium'
            }
        elif health.maturity == MaturityLevel.MATURE:
            return {
                'strategy': 'conservative',
                'reason': 'Mature agent, stable execution',
                'recommended_interval_minutes': 60,
                'priority': 'low'
            }
        else:
            return {
                'strategy': 'maintenance',
                'reason': 'Veteran agent, minimal changes expected',
                'recommended_interval_minutes': 240,
                'priority': 'low'
            }
    
    def generate_health_report(self) -> Dict[str, Any]:
        health_data = self.monitor_all_agents()
        
        critical_count = sum(1 for h in health_data.values() if h.status == HealthStatus.CRITICAL)
        warning_count = sum(1 for h in health_data.values() if h.status == HealthStatus.WARNING)
        healthy_count = sum(1 for h in health_data.values() if h.status == HealthStatus.HEALTHY)
        stale_count = sum(1 for h in health_data.values() if h.status == HealthStatus.STALE)
        
        avg_health_score = sum(h.health_score for h in health_data.values()) / len(health_data) if health_data else 0
        
        maturity_distribution = {}
        for h in health_data.values():
            maturity_distribution[h.maturity.value] = maturity_distribution.get(h.maturity.value, 0) + 1
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_agents': len(health_data),
            'summary': {
                'critical': critical_count,
                'warning': warning_count,
                'healthy': healthy_count,
                'stale': stale_count,
                'average_health_score': avg_health_score
            },
            'maturity_distribution': maturity_distribution,
            'critical_alerts': [
                {
                    'agent': a.agent_name,
                    'message': a.message,
                    'recommendation': a.recommendation
                } for a in self.get_critical_alerts()
            ],
            'warning_alerts': [
                {
                    'agent': a.agent_name,
                    'message': a.message,
                    'recommendation': a.recommendation
                } for a in self.get_warning_alerts()
            ],
            'agents': {
                name: {
                    'status': health.status.value,
                    'maturity': health.maturity.value,
                    'health_score': health.health_score,
                    'metrics': health.metrics,
                    'recommendations': health.recommendations
                } for name, health in health_data.items()
            }
        }
