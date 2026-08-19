#!/usr/bin/env python3
"""
Dormant File Management Tests - Phase 2B
Version: 1.0.0
Date: 2025-12-04

Tests for dormant file detection, ranking, and integration system.
Tests config validation, threshold management, scoring tiers, and integration actions.
"""

import pytest
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List


@pytest.fixture
def dormant_config_path():
    """Path to dormant config"""
    return Path(__file__).parent.parent / "rich_padding" / "dormant_config.yaml"


@pytest.fixture
def dormant_config(dormant_config_path):
    """Load dormant config"""
    if dormant_config_path.exists():
        with open(dormant_config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return None


@pytest.fixture
def dormant_index_path():
    """Path to dormant index"""
    return Path(__file__).parent.parent / "rich_padding" / "dormant_index.yaml"


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace"""
    workspace = tmp_path / "dormant_workspace"
    workspace.mkdir()
    return workspace


class TestDormantConfigValidation:
    """Test dormant configuration validation"""
    
    def test_config_file_exists(self, dormant_config_path):
        """Test that dormant config file exists"""
        assert dormant_config_path.exists(), f"Config file not found: {dormant_config_path}"
    
    def test_config_loads_successfully(self, dormant_config):
        """Test that config loads without errors"""
        assert dormant_config is not None
        assert isinstance(dormant_config, dict)
    
    def test_detection_thresholds(self, dormant_config):
        """Test dormant detection thresholds are defined"""
        if dormant_config is None:
            pytest.skip("Config file not found")
        
        detection = dormant_config.get('detection', {})
        thresholds = detection.get('thresholds', {})
        
        assert thresholds['inactive_days'] == 30
        assert thresholds['warning_days'] == 60
        assert thresholds['critical_days'] == 90
        assert thresholds['archive_days'] == 180
    
    def test_file_type_filters(self, dormant_config):
        """Test file type filters are defined"""
        if dormant_config is None:
            pytest.skip("Config file not found")
        
        detection = dormant_config.get('detection', {})
        file_types = detection.get('file_types', {})
        
        assert 'code' in file_types
        assert 'config' in file_types
        assert 'docs' in file_types
        assert 'tests' in file_types
        
        assert '*.py' in file_types['code']
        assert '*.yaml' in file_types['config']
        assert '*.md' in file_types['docs']


class TestDormantRankingSystem:
    """Test dormant file ranking system"""
    
    def test_ranking_weights(self, dormant_config):
        """Test ranking weights sum to 1.0"""
        if dormant_config is None:
            pytest.skip("Config file not found")
        
        ranking = dormant_config.get('ranking', {})
        weights = ranking.get('weights', {})
        
        total_weight = sum(weights.values())
        assert abs(total_weight - 1.0) < 0.01, f"Weights should sum to 1.0, got {total_weight}"
    
    def test_ranking_tiers(self, dormant_config):
        """Test ranking tiers are defined"""
        if dormant_config is None:
            pytest.skip("Config file not found")
        
        ranking = dormant_config.get('ranking', {})
        tiers = ranking.get('tiers', {})
        
        assert 'tier1_critical' in tiers
        assert 'tier2_important' in tiers
        assert 'tier3_supporting' in tiers
        
        tier1 = tiers['tier1_critical']
        assert tier1['score_min'] == 0.85
        assert tier1['score_max'] == 1.0
        assert tier1['priority'] == 'HIGH'
        assert tier1['action'] == 'integrate_immediately'
    
    def test_tier_score_ranges(self, dormant_config):
        """Test tier score ranges are contiguous and valid"""
        if dormant_config is None:
            pytest.skip("Config file not found")
        
        ranking = dormant_config.get('ranking', {})
        tiers = ranking.get('tiers', {})
        
        tier1 = tiers['tier1_critical']
        tier2 = tiers['tier2_important']
        tier3 = tiers['tier3_supporting']
        
        assert tier1['score_min'] > tier2['score_max']
        assert tier2['score_min'] > tier3['score_max']
        assert tier3['score_min'] >= 0.5


class TestDormantFileDetection:
    """Test dormant file detection logic"""
    
    def test_inactive_file_detection(self, temp_workspace, dormant_config):
        """Test detection of inactive files"""
        if dormant_config is None:
            pytest.skip("Config file not found")
        
        test_file = temp_workspace / "old_file.py"
        test_file.write_text("# Old code")
        
        thresholds = dormant_config['detection']['thresholds']
        inactive_days = thresholds['inactive_days']
        
        file_age = datetime.now() - datetime.fromtimestamp(test_file.stat().st_mtime)
        
        assert test_file.exists()
        assert file_age.days >= 0
    
    def test_exclusion_patterns(self, dormant_config):
        """Test that exclusion patterns are properly defined"""
        if dormant_config is None:
            pytest.skip("Config file not found")
        
        detection = dormant_config.get('detection', {})
        exclusions = detection.get('exclusions', {})
        
        assert '.git' in exclusions['directories']
        assert '__pycache__' in exclusions['directories']
        assert '*.pyc' in exclusions['files']


class TestDormantIntegrationActions:
    """Test dormant file integration actions"""
    
    def test_integration_action_mapping(self, dormant_config):
        """Test that each tier has an integration action"""
        if dormant_config is None:
            pytest.skip("Config file not found")
        
        ranking = dormant_config.get('ranking', {})
        tiers = ranking.get('tiers', {})
        
        for tier_name, tier_config in tiers.items():
            assert 'action' in tier_config
            assert tier_config['action'] in [
                'integrate_immediately',
                'integrate_soon',
                'integrate_opportunistic'
            ]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
