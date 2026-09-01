"""Action tracking runtime used by the ABACUS parent test suite."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class ActionStatus(str, Enum):
    """Lifecycle states for action items."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ActionPriority(str, Enum):
    """Priority levels for action items."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionType(str, Enum):
    """Action item categories."""

    TASK = "task"
    BUG = "bug"
    FEATURE = "feature"
    DECISION = "decision"
    RISK = "risk"


@dataclass
class ActionUpdate:
    """One update attached to an action."""

    update_id: str
    action_id: str
    author: str
    timestamp: datetime
    comment: str = ""
    status_change: str | None = None


@dataclass
class ActionItem:
    """Tracked action item."""

    action_id: str
    title: str
    description: str
    action_type: ActionType
    status: ActionStatus
    priority: ActionPriority
    epic: str
    topics: list[str]
    assignee: str
    created_date: datetime
    due_date: datetime | None = None
    completed_date: datetime | None = None
    blocked_reason: str | None = None
    related_docs: list[str] = field(default_factory=list)
    related_actions: list[str] = field(default_factory=list)


class ActionTracker:
    """Simple persistent action tracker."""

    def __init__(self, workspace_root: Path | str) -> None:
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.tracker_path = self.workspace_root / "action_tracker.yaml"
        self.actions: dict[str, ActionItem] = {}
        self.updates: dict[str, list[ActionUpdate]] = {}
        self._load_tracker()

    def create_action(
        self,
        action_id: str,
        title: str,
        description: str,
        action_type: ActionType,
        priority: ActionPriority,
        epic: str,
        topics: list[str],
        assignee: str,
        due_date: datetime | None = None,
    ) -> ActionItem:
        if action_id in self.actions:
            return self.actions[action_id]
        item = ActionItem(
            action_id=action_id,
            title=title,
            description=description,
            action_type=ActionType(action_type),
            status=ActionStatus.OPEN,
            priority=ActionPriority(priority),
            epic=epic,
            topics=list(topics),
            assignee=assignee,
            due_date=due_date,
            created_date=datetime.now(),
        )
        self.actions[action_id] = item
        self.updates[action_id] = []
        return item

    def get_action(self, action_id: str) -> ActionItem | None:
        return self.actions.get(action_id)

    def get_updates(self, action_id: str) -> list[ActionUpdate]:
        return list(self.updates.get(action_id, []))

    def update_status(
        self,
        action_id: str,
        status: ActionStatus,
        author: str,
        comment: str = "",
    ) -> None:
        action = self._require_action(action_id)
        old_status = action.status
        action.status = ActionStatus(status)
        if action.status == ActionStatus.COMPLETED:
            action.completed_date = datetime.now()
        self._add_update(
            action_id,
            author,
            comment,
            f"{old_status.value} -> {action.status.value}",
        )

    def add_comment(self, action_id: str, author: str, comment: str) -> None:
        self._require_action(action_id)
        self._add_update(action_id, author, comment, None)

    def block_action(self, action_id: str, reason: str, author: str) -> None:
        action = self._require_action(action_id)
        old_status = action.status
        action.status = ActionStatus.BLOCKED
        action.blocked_reason = reason
        self._add_update(action_id, author, reason, f"{old_status.value} -> blocked")

    def unblock_action(self, action_id: str, author: str) -> None:
        action = self._require_action(action_id)
        old_status = action.status
        action.status = ActionStatus.OPEN
        action.blocked_reason = None
        self._add_update(action_id, author, "Unblocked", f"{old_status.value} -> open")

    def link_document(self, action_id: str, document_id: str) -> None:
        action = self._require_action(action_id)
        if document_id not in action.related_docs:
            action.related_docs.append(document_id)

    def link_action(self, action_id: str, related_action_id: str) -> None:
        action = self._require_action(action_id)
        if related_action_id not in action.related_actions:
            action.related_actions.append(related_action_id)

    def get_by_status(self, status: ActionStatus) -> list[ActionItem]:
        return [a for a in self.actions.values() if a.status == ActionStatus(status)]

    def get_by_priority(self, priority: ActionPriority) -> list[ActionItem]:
        return [a for a in self.actions.values() if a.priority == ActionPriority(priority)]

    def get_by_epic(self, epic: str) -> list[ActionItem]:
        return [a for a in self.actions.values() if a.epic == epic]

    def get_by_assignee(self, assignee: str) -> list[ActionItem]:
        return [a for a in self.actions.values() if a.assignee == assignee]

    def get_overdue(self) -> list[ActionItem]:
        now = datetime.now()
        return [
            action
            for action in self.actions.values()
            if action.due_date
            and action.due_date < now
            and action.status != ActionStatus.COMPLETED
        ]

    def get_due_soon(self, days: int = 7) -> list[ActionItem]:
        now = datetime.now()
        limit = now + timedelta(days=days)
        return [
            action
            for action in self.actions.values()
            if action.due_date
            and now <= action.due_date <= limit
            and action.status != ActionStatus.COMPLETED
        ]

    def generate_report(self) -> str:
        lines = ["# Action Tracker Report", ""]
        for action in sorted(self.actions.values(), key=lambda item: item.action_id):
            lines.append(f"- {action.action_id}: {action.title} [{action.status.value}]")
        overdue = self.get_overdue()
        if overdue:
            lines.extend(["", "## Overdue Actions"])
            lines.extend(f"- {action.action_id}" for action in overdue)
        return "\n".join(lines)

    def save_tracker(self) -> None:
        payload = {
            "actions": [self._action_to_dict(action) for action in self.actions.values()],
            "updates": {
                key: [self._update_to_dict(update) for update in value]
                for key, value in self.updates.items()
            },
        }
        self.tracker_path.write_text(yaml.safe_dump(payload, sort_keys=True), encoding="utf-8")

    def _load_tracker(self) -> None:
        if not self.tracker_path.exists():
            return
        data = yaml.safe_load(self.tracker_path.read_text(encoding="utf-8")) or {}
        for raw_action in data.get("actions", []):
            action = self._action_from_dict(raw_action)
            self.actions[action.action_id] = action
        for action_id, raw_updates in data.get("updates", {}).items():
            self.updates[action_id] = [
                self._update_from_dict(update) for update in raw_updates
            ]
        for action_id in self.actions:
            self.updates.setdefault(action_id, [])

    def _require_action(self, action_id: str) -> ActionItem:
        action = self.get_action(action_id)
        if action is None:
            raise ValueError(f"Unknown action: {action_id}")
        return action

    def _add_update(
        self,
        action_id: str,
        author: str,
        comment: str,
        status_change: str | None,
    ) -> None:
        updates = self.updates.setdefault(action_id, [])
        updates.append(
            ActionUpdate(
                update_id=f"UPD-{len(updates) + 1:03d}",
                action_id=action_id,
                author=author,
                timestamp=datetime.now(),
                comment=comment,
                status_change=status_change,
            )
        )

    @staticmethod
    def _action_to_dict(action: ActionItem) -> dict[str, Any]:
        data = asdict(action)
        data["action_type"] = action.action_type.value
        data["status"] = action.status.value
        data["priority"] = action.priority.value
        for key in ("created_date", "due_date", "completed_date"):
            if data[key] is not None:
                data[key] = data[key].isoformat()
        return data

    @staticmethod
    def _update_to_dict(update: ActionUpdate) -> dict[str, Any]:
        data = asdict(update)
        data["timestamp"] = update.timestamp.isoformat()
        return data

    @staticmethod
    def _action_from_dict(data: dict[str, Any]) -> ActionItem:
        payload = dict(data)
        payload["action_type"] = ActionType(payload["action_type"])
        payload["status"] = ActionStatus(payload["status"])
        payload["priority"] = ActionPriority(payload["priority"])
        for key in ("created_date", "due_date", "completed_date"):
            if payload.get(key):
                payload[key] = datetime.fromisoformat(payload[key])
        return ActionItem(**payload)

    @staticmethod
    def _update_from_dict(data: dict[str, Any]) -> ActionUpdate:
        payload = dict(data)
        payload["timestamp"] = datetime.fromisoformat(payload["timestamp"])
        return ActionUpdate(**payload)
