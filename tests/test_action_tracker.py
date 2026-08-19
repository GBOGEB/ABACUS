#!/usr/bin/env python3
"""
# Version: 1.0.0
# Date: 2025-11-25
# Description: Unit tests for Action Tracker

Tests action creation, status updates, priority management,
due date tracking, and reporting capabilities.
"""

import pytest
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "13_CORE_SYSTEMS" / "CENTRAL_LIBRARY"))

from action_tracker import (
    ActionTracker,
    ActionItem,
    ActionUpdate,
    ActionStatus,
    ActionPriority,
    ActionType
)


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace"""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def tracker(temp_workspace):
    """Create tracker instance"""
    return ActionTracker(workspace_root=temp_workspace)


@pytest.fixture
def sample_action():
    """Sample action data"""
    return {
        'action_id': 'ACT-001',
        'title': 'Test Action Item',
        'description': 'This is a test action item',
        'action_type': ActionType.TASK,
        'priority': ActionPriority.HIGH,
        'epic': 'GLOOB',
        'topics': ['Phase2', 'Week3'],
        'assignee': 'test_user'
    }


class TestActionTracker:
    """Test suite for Action Tracker"""
    
    def test_initialization(self, tracker, temp_workspace):
        """Test tracker initialization"""
        assert tracker.workspace_root == temp_workspace
        assert isinstance(tracker.actions, dict)
        assert isinstance(tracker.updates, dict)
    
    def test_create_action(self, tracker, sample_action):
        """Test action creation"""
        action = tracker.create_action(**sample_action)
        
        assert action.action_id == 'ACT-001'
        assert action.title == 'Test Action Item'
        assert action.status == ActionStatus.OPEN
        assert action.priority == ActionPriority.HIGH
        assert action.epic == 'GLOOB'
        assert 'ACT-001' in tracker.actions
        assert 'ACT-001' in tracker.updates
    
    def test_create_duplicate_action(self, tracker, sample_action):
        """Test creating duplicate action"""
        action1 = tracker.create_action(**sample_action)
        action2 = tracker.create_action(**sample_action)
        
        assert action1.action_id == action2.action_id
        assert len(tracker.actions) == 1
    
    def test_update_status(self, tracker, sample_action):
        """Test status update"""
        tracker.create_action(**sample_action)
        
        tracker.update_status('ACT-001', ActionStatus.IN_PROGRESS, 'test_user', 'Started work')
        
        action = tracker.get_action('ACT-001')
        assert action.status == ActionStatus.IN_PROGRESS
        assert len(tracker.updates['ACT-001']) == 1
    
    def test_complete_action(self, tracker, sample_action):
        """Test completing an action"""
        tracker.create_action(**sample_action)
        
        tracker.update_status('ACT-001', ActionStatus.COMPLETED, 'test_user', 'Work completed')
        
        action = tracker.get_action('ACT-001')
        assert action.status == ActionStatus.COMPLETED
        assert action.completed_date is not None
    
    def test_add_comment(self, tracker, sample_action):
        """Test adding comment to action"""
        tracker.create_action(**sample_action)
        
        tracker.add_comment('ACT-001', 'test_user', 'This is a test comment')
        
        updates = tracker.get_updates('ACT-001')
        assert len(updates) == 1
        assert updates[0].comment == 'This is a test comment'
    
    def test_block_action(self, tracker, sample_action):
        """Test blocking an action"""
        tracker.create_action(**sample_action)
        
        tracker.block_action('ACT-001', 'Waiting for dependency', 'test_user')
        
        action = tracker.get_action('ACT-001')
        assert action.status == ActionStatus.BLOCKED
        assert action.blocked_reason == 'Waiting for dependency'
    
    def test_unblock_action(self, tracker, sample_action):
        """Test unblocking an action"""
        tracker.create_action(**sample_action)
        tracker.block_action('ACT-001', 'Waiting for dependency', 'test_user')
        
        tracker.unblock_action('ACT-001', 'test_user')
        
        action = tracker.get_action('ACT-001')
        assert action.status == ActionStatus.OPEN
        assert action.blocked_reason is None
    
    def test_get_action(self, tracker, sample_action):
        """Test getting action by ID"""
        tracker.create_action(**sample_action)
        
        action = tracker.get_action('ACT-001')
        assert action is not None
        assert action.action_id == 'ACT-001'
        
        missing = tracker.get_action('MISSING-001')
        assert missing is None
    
    def test_get_by_status(self, tracker, sample_action):
        """Test getting actions by status"""
        tracker.create_action(**sample_action)
        
        sample_action['action_id'] = 'ACT-002'
        tracker.create_action(**sample_action)
        
        tracker.update_status('ACT-001', ActionStatus.IN_PROGRESS, 'test_user')
        
        open_actions = tracker.get_by_status(ActionStatus.OPEN)
        assert len(open_actions) == 1
        assert open_actions[0].action_id == 'ACT-002'
        
        in_progress = tracker.get_by_status(ActionStatus.IN_PROGRESS)
        assert len(in_progress) == 1
        assert in_progress[0].action_id == 'ACT-001'
    
    def test_get_by_priority(self, tracker, sample_action):
        """Test getting actions by priority"""
        tracker.create_action(**sample_action)
        
        sample_action['action_id'] = 'ACT-002'
        sample_action['priority'] = ActionPriority.LOW
        tracker.create_action(**sample_action)
        
        high_priority = tracker.get_by_priority(ActionPriority.HIGH)
        assert len(high_priority) == 1
        assert high_priority[0].priority == ActionPriority.HIGH
        
        low_priority = tracker.get_by_priority(ActionPriority.LOW)
        assert len(low_priority) == 1
        assert low_priority[0].priority == ActionPriority.LOW
    
    def test_get_by_epic(self, tracker, sample_action):
        """Test getting actions by EPIC"""
        tracker.create_action(**sample_action)
        
        sample_action['action_id'] = 'ACT-002'
        sample_action['epic'] = 'DMAIC'
        tracker.create_action(**sample_action)
        
        gloob_actions = tracker.get_by_epic('GLOOB')
        assert len(gloob_actions) == 1
        assert gloob_actions[0].epic == 'GLOOB'
        
        dmaic_actions = tracker.get_by_epic('DMAIC')
        assert len(dmaic_actions) == 1
        assert dmaic_actions[0].epic == 'DMAIC'
    
    def test_get_by_assignee(self, tracker, sample_action):
        """Test getting actions by assignee"""
        tracker.create_action(**sample_action)
        
        sample_action['action_id'] = 'ACT-002'
        sample_action['assignee'] = 'other_user'
        tracker.create_action(**sample_action)
        
        test_user_actions = tracker.get_by_assignee('test_user')
        assert len(test_user_actions) == 1
        assert test_user_actions[0].assignee == 'test_user'
        
        other_user_actions = tracker.get_by_assignee('other_user')
        assert len(other_user_actions) == 1
        assert other_user_actions[0].assignee == 'other_user'
    
    def test_get_overdue(self, tracker, sample_action):
        """Test getting overdue actions"""
        past_date = datetime.now() - timedelta(days=7)
        sample_action['due_date'] = past_date
        tracker.create_action(**sample_action)
        
        overdue = tracker.get_overdue()
        assert len(overdue) == 1
        assert overdue[0].action_id == 'ACT-001'
    
    def test_get_due_soon(self, tracker, sample_action):
        """Test getting actions due soon"""
        future_date = datetime.now() + timedelta(days=3)
        sample_action['due_date'] = future_date
        tracker.create_action(**sample_action)
        
        due_soon = tracker.get_due_soon(days=7)
        assert len(due_soon) == 1
        assert due_soon[0].action_id == 'ACT-001'
    
    def test_get_updates(self, tracker, sample_action):
        """Test getting action updates"""
        tracker.create_action(**sample_action)
        tracker.add_comment('ACT-001', 'test_user', 'Comment 1')
        tracker.add_comment('ACT-001', 'test_user', 'Comment 2')
        
        updates = tracker.get_updates('ACT-001')
        assert len(updates) == 2
        assert all(isinstance(u, ActionUpdate) for u in updates)
    
    def test_link_document(self, tracker, sample_action):
        """Test linking action to document"""
        tracker.create_action(**sample_action)
        
        tracker.link_document('ACT-001', 'DOC-001')
        
        action = tracker.get_action('ACT-001')
        assert 'DOC-001' in action.related_docs
    
    def test_link_action(self, tracker, sample_action):
        """Test linking action to another action"""
        tracker.create_action(**sample_action)
        
        sample_action['action_id'] = 'ACT-002'
        tracker.create_action(**sample_action)
        
        tracker.link_action('ACT-001', 'ACT-002')
        
        action = tracker.get_action('ACT-001')
        assert 'ACT-002' in action.related_actions
    
    def test_save_and_load_tracker(self, tracker, sample_action):
        """Test tracker persistence"""
        tracker.create_action(**sample_action)
        tracker.save_tracker()
        
        assert tracker.tracker_path.exists()
        
        new_tracker = ActionTracker(workspace_root=tracker.workspace_root)
        assert 'ACT-001' in new_tracker.actions
        assert new_tracker.get_action('ACT-001').title == 'Test Action Item'
    
    def test_generate_report(self, tracker, sample_action):
        """Test report generation"""
        tracker.create_action(**sample_action)
        
        sample_action['action_id'] = 'ACT-002'
        sample_action['priority'] = ActionPriority.CRITICAL
        sample_action['due_date'] = datetime.now() - timedelta(days=1)
        tracker.create_action(**sample_action)
        
        report = tracker.generate_report()
        
        assert 'Action Tracker Report' in report
        assert 'ACT-001' in report
        assert 'ACT-002' in report
        assert 'Overdue Actions' in report
    
    def test_action_lifecycle(self, tracker, sample_action):
        """Test complete action lifecycle"""
        tracker.create_action(**sample_action)
        
        tracker.update_status('ACT-001', ActionStatus.IN_PROGRESS, 'test_user', 'Started')
        action = tracker.get_action('ACT-001')
        assert action.status == ActionStatus.IN_PROGRESS
        
        tracker.add_comment('ACT-001', 'test_user', 'Making progress')
        
        tracker.update_status('ACT-001', ActionStatus.COMPLETED, 'test_user', 'Finished')
        action = tracker.get_action('ACT-001')
        assert action.status == ActionStatus.COMPLETED
        assert action.completed_date is not None
        
        updates = tracker.get_updates('ACT-001')
        assert len(updates) == 3
    
    def test_invalid_action_operations(self, tracker):
        """Test error handling for invalid operations"""
        with pytest.raises(ValueError):
            tracker.update_status('MISSING-001', ActionStatus.COMPLETED, 'test_user')
        
        with pytest.raises(ValueError):
            tracker.add_comment('MISSING-001', 'test_user', 'Comment')
        
        with pytest.raises(ValueError):
            tracker.block_action('MISSING-001', 'Reason', 'test_user')
        
        with pytest.raises(ValueError):
            tracker.link_document('MISSING-001', 'DOC-001')
        
        with pytest.raises(ValueError):
            tracker.link_action('MISSING-001', 'ACT-001')
    
    def test_multiple_action_types(self, tracker, sample_action):
        """Test different action types"""
        for action_type in ActionType:
            sample_action['action_id'] = f'ACT-{action_type.value}'
            sample_action['action_type'] = action_type
            tracker.create_action(**sample_action)
        
        assert len(tracker.actions) == len(ActionType)
    
    def test_priority_levels(self, tracker, sample_action):
        """Test all priority levels"""
        for priority in ActionPriority:
            sample_action['action_id'] = f'ACT-{priority.value}'
            sample_action['priority'] = priority
            tracker.create_action(**sample_action)
        
        assert len(tracker.actions) == len(ActionPriority)
    
    def test_status_transitions(self, tracker, sample_action):
        """Test status transitions"""
        tracker.create_action(**sample_action)
        
        transitions = [
            ActionStatus.IN_PROGRESS,
            ActionStatus.BLOCKED,
            ActionStatus.IN_PROGRESS,
            ActionStatus.COMPLETED
        ]
        
        for status in transitions:
            tracker.update_status('ACT-001', status, 'test_user')
        
        action = tracker.get_action('ACT-001')
        assert action.status == ActionStatus.COMPLETED
        
        updates = tracker.get_updates('ACT-001')
        assert len(updates) == len(transitions)


class TestActionItem:
    """Test ActionItem dataclass"""
    
    def test_action_creation(self):
        """Test creating action item"""
        now = datetime.now()
        action = ActionItem(
            action_id='TEST-001',
            title='Test Action',
            description='Test description',
            action_type=ActionType.TASK,
            status=ActionStatus.OPEN,
            priority=ActionPriority.HIGH,
            epic='GLOOB',
            topics=['Phase2'],
            assignee='test_user',
            created_date=now
        )
        
        assert action.action_id == 'TEST-001'
        assert action.status == ActionStatus.OPEN
        assert action.priority == ActionPriority.HIGH


class TestActionUpdate:
    """Test ActionUpdate dataclass"""
    
    def test_update_creation(self):
        """Test creating action update"""
        now = datetime.now()
        update = ActionUpdate(
            update_id='UPD-001',
            action_id='ACT-001',
            author='test_user',
            timestamp=now,
            comment='Test comment',
            status_change='open → in_progress'
        )
        
        assert update.update_id == 'UPD-001'
        assert update.action_id == 'ACT-001'
        assert update.comment == 'Test comment'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=action_tracker', '--cov-report=term-missing'])
