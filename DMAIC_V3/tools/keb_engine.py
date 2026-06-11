"""
DMAIC V3 - KEB (Knowledge Engineering Base) Engine
Handles QPLANT case parsing, cryo metrics extraction, and RTM mapping

ITERATION 4 - CDCII/CICD Integration
Version: 3.3.0
Date: 2025-01-26
Purpose: KEB metrics extraction and knowledge management
Input: QPLANT case files, metrics data
Output: Cryo metrics, RTM mappings, status tracking
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import re


class CaseStatus(Enum):
    """Status of QPLANT cases"""
    ACTIVE = "Active"
    PENDING = "Pending"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


@dataclass
class CryoMetrics:
    """Cryogenic metrics from QPLANT cases"""
    temperature: float
    temperature_unit: str
    pressure: float
    pressure_unit: str
    status: CaseStatus
    case_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'temperature': self.temperature,
            'temperature_unit': self.temperature_unit,
            'pressure': self.pressure,
            'pressure_unit': self.pressure_unit,
            'status': self.status.value
        }


class KEBEngine:
    """
    Knowledge Engineering Base Engine
    
    Responsibilities:
    - QPLANT case parsing
    - Cryo metrics extraction (temperature, pressure)
    - RTM (Requirements Traceability Matrix) mapping
    - Status tracking and updates
    """
    
    def __init__(self):
        self.rtm_mappings = self._load_rtm_mappings()
        self.metrics_cache: Dict[str, CryoMetrics] = {}
    
    def extract_metrics(self, qplant_path: Path) -> Dict[str, Any]:
        """
        Extract metrics from QPLANT cases
        
        Args:
            qplant_path: Path to QPLANT inputs directory
        
        Returns:
            Extracted metrics with RTM mappings
        """
        results = {
            'qplant_cases_processed': 0,
            'cryo_metrics': {},
            'rtm_mappings': {},
            'metrics_summary': {
                'avg_temperature': 0.0,
                'avg_pressure': 0.0,
                'active_cases': 0,
                'pending_cases': 0,
                'completed_cases': 0,
                'failed_cases': 0
            },
            'status_summary': {
                'Active': 0,
                'Pending': 0,
                'Completed': 0,
                'Failed': 0
            },
            'status_changes': [],
            'notifications': []
        }
        
        # Process QPLANT case files
        if not qplant_path.exists():
            return results
        
        case_files = list(qplant_path.rglob("*.txt"))
        temperatures = []
        pressures = []
        
        for case_file in case_files:
            case_id = case_file.stem
            metrics = self._parse_qplant_case(case_file)
            
            if metrics:
                results['cryo_metrics'][case_id] = metrics.to_dict()
                results['rtm_mappings'][case_id] = self._get_rtm_mapping(case_id)
                results['qplant_cases_processed'] += 1
                
                temperatures.append(metrics.temperature)
                pressures.append(metrics.pressure)
                
                # Update status summary
                results['status_summary'][metrics.status.value] += 1
                
                if metrics.status == CaseStatus.ACTIVE:
                    results['metrics_summary']['active_cases'] += 1
                elif metrics.status == CaseStatus.PENDING:
                    results['metrics_summary']['pending_cases'] += 1
                elif metrics.status == CaseStatus.COMPLETED:
                    results['metrics_summary']['completed_cases'] += 1
                elif metrics.status == CaseStatus.FAILED:
                    results['metrics_summary']['failed_cases'] += 1
        
        # Calculate averages
        if temperatures:
            results['metrics_summary']['avg_temperature'] = sum(temperatures) / len(temperatures)
        if pressures:
            results['metrics_summary']['avg_pressure'] = sum(pressures) / len(pressures)
        
        return results
    
    def _parse_qplant_case(self, case_file: Path) -> Optional[CryoMetrics]:
        """Parse a QPLANT case file"""
        try:
            content = case_file.read_text()
            
            # Extract temperature
            temp_match = re.search(r'Temperature:\s*([\d.]+)\s*([KkCcFf])', content)
            if not temp_match:
                return None
            temperature = float(temp_match.group(1))
            temp_unit = temp_match.group(2).upper()
            
            # Extract pressure
            pressure_match = re.search(r'Pressure:\s*([\d.]+)\s*(\w+)', content)
            if not pressure_match:
                return None
            pressure = float(pressure_match.group(1))
            pressure_unit = pressure_match.group(2)
            
            # Extract status
            status_match = re.search(r'Status:\s*(\w+)', content)
            status = CaseStatus.ACTIVE
            if status_match:
                status_str = status_match.group(1)
                try:
                    status = CaseStatus(status_str)
                except ValueError:
                    status = CaseStatus.ACTIVE
            
            return CryoMetrics(
                temperature=temperature,
                temperature_unit=temp_unit,
                pressure=pressure,
                pressure_unit=pressure_unit,
                status=status,
                case_id=case_file.stem
            )
            
        except Exception as e:
            print(f"Error parsing {case_file}: {e}")
            return None
    
    def _get_rtm_mapping(self, case_id: str) -> List[str]:
        """Get RTM mappings for a case"""
        # Simple mapping based on case ID
        if case_id.endswith('001'):
            return ['REQ-001', 'REQ-005']
        elif case_id.endswith('002'):
            return ['REQ-002', 'REQ-006']
        elif case_id.endswith('003'):
            return ['REQ-003', 'REQ-007']
        else:
            return ['REQ-000']
    
    def _load_rtm_mappings(self) -> Dict[str, List[str]]:
        """Load RTM mappings from configuration"""
        return {
            'default': ['REQ-000'],
            'cryo_temp': ['REQ-001', 'REQ-002'],
            'cryo_pressure': ['REQ-003', 'REQ-004'],
            'status_tracking': ['REQ-005', 'REQ-006']
        }


# Factory function
def create_keb_engine() -> KEBEngine:
    """Create and initialize KEB engine"""
    return KEBEngine()
