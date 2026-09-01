"""Persistent master-document registry used by the ABACUS test surface."""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class DocumentType(Enum):
    ADR = "ADR"
    OCD = "OCD"
    SOR = "SOR"
    SPEC = "SPEC"
    REPORT = "REPORT"


class DocumentStatus(Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    DEPRECATED = "DEPRECATED"


@dataclass
class DocumentVersion:
    version: str
    date: datetime
    author: str
    changes: str
    file_path: Path
    checksum: str


@dataclass
class DocumentMetadata:
    doc_id: str
    doc_type: DocumentType
    title: str
    version: str
    status: DocumentStatus
    epic: str | None
    topics: list[str]
    file_path: Path
    created_date: datetime
    modified_date: datetime
    author: str
    dependencies: list[str] = field(default_factory=list)
    golden_threads: list[str] = field(default_factory=list)


class MasterDocumentManager:
    def __init__(self, workspace_root: Path | str):
        self.workspace_root = Path(workspace_root)
        self.registry_path = self.workspace_root / "13_CORE_SYSTEMS" / "CENTRAL_LIBRARY" / "master_document_registry.yaml"
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.documents: dict[str, DocumentMetadata] = {}
        self.version_history: dict[str, list[DocumentVersion]] = {}
        if self.registry_path.exists():
            self._load_registry()

    @staticmethod
    def _checksum(path: Path) -> str:
        if not path.exists():
            return ""

        sha256 = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def register_document(self, doc_id: str, doc_type: DocumentType, title: str, file_path: Path, epic: str | None = None,
                          topics: list[str] | None = None, author: str = "unknown", version: str = "1.0.0", **_: Any) -> DocumentMetadata:
        if doc_id in self.documents:
            return self.documents[doc_id]
        now = datetime.now()
        path = Path(file_path)
        doc = DocumentMetadata(doc_id, doc_type, title, version, DocumentStatus.DRAFT, epic, list(topics or []), path, now, now, author)
        self.documents[doc_id] = doc
        self.version_history[doc_id] = [DocumentVersion(version, now, author, "Initial version", path, self._checksum(path))]
        return doc

    def get_document(self, doc_id: str) -> DocumentMetadata | None:
        return self.documents.get(doc_id)

    def update_document(self, doc_id: str, version: str, author: str, changes: str, status: DocumentStatus | None = None) -> DocumentMetadata:
        doc = self._require(doc_id)
        doc.version = version
        doc.author = author
        doc.modified_date = datetime.now()
        if status is not None:
            doc.status = status
        self.version_history[doc_id].append(DocumentVersion(version, doc.modified_date, author, changes, doc.file_path, self._checksum(doc.file_path)))
        return doc

    def get_by_type(self, doc_type: DocumentType) -> list[DocumentMetadata]:
        return [d for d in self.documents.values() if d.doc_type == doc_type]

    def get_by_epic(self, epic: str) -> list[DocumentMetadata]:
        return [d for d in self.documents.values() if d.epic == epic]

    def get_by_status(self, status: DocumentStatus) -> list[DocumentMetadata]:
        return [d for d in self.documents.values() if d.status == status]

    def get_version_history(self, doc_id: str) -> list[DocumentVersion]:
        return list(self.version_history.get(doc_id, []))

    def add_dependency(self, doc_id: str, dependency_id: str) -> None:
        doc = self._require(doc_id)
        if dependency_id not in doc.dependencies:
            doc.dependencies.append(dependency_id)

    def add_golden_thread(self, doc_id: str, thread_id: str) -> None:
        doc = self._require(doc_id)
        if thread_id not in doc.golden_threads:
            doc.golden_threads.append(thread_id)

    def promote_status(self, doc_id: str, status: DocumentStatus, author: str) -> None:
        doc = self._require(doc_id)
        doc.status = status
        doc.author = author
        doc.modified_date = datetime.now()

    def deprecate_document(self, doc_id: str, reason: str, author: str) -> None:
        doc = self._require(doc_id)
        doc.status = DocumentStatus.DEPRECATED
        doc.modified_date = datetime.now()
        self.version_history[doc_id].append(DocumentVersion(doc.version, doc.modified_date, author, f"Deprecated: {reason}", doc.file_path, self._checksum(doc.file_path)))

    def get_dependency_tree(self, doc_id: str, _seen: set[str] | None = None) -> dict[str, Any]:
        doc = self._require(doc_id)
        seen = set(_seen or set())
        if doc_id in seen:
            return {"doc_id": doc_id, "dependencies": []}
        seen.add(doc_id)
        deps = []
        for dep_id in doc.dependencies:
            if dep_id in self.documents:
                deps.append(self.get_dependency_tree(dep_id, seen))
        return {"doc_id": doc_id, "dependencies": deps}

    def _require(self, doc_id: str) -> DocumentMetadata:
        doc = self.documents.get(doc_id)
        if doc is None:
            raise ValueError(f"Unknown document: {doc_id}")
        return doc

    @staticmethod
    def _doc_to_dict(doc: DocumentMetadata) -> dict[str, Any]:
        data = asdict(doc)
        data["doc_type"] = doc.doc_type.value
        data["status"] = doc.status.value
        data["file_path"] = str(doc.file_path)
        data["created_date"] = doc.created_date.isoformat()
        data["modified_date"] = doc.modified_date.isoformat()
        return data

    @staticmethod
    def _version_to_dict(item: DocumentVersion) -> dict[str, Any]:
        return {"version": item.version, "date": item.date.isoformat(), "author": item.author, "changes": item.changes,
                "file_path": str(item.file_path), "checksum": item.checksum}

    def save_registry(self) -> None:
        payload = {
            "documents": {k: self._doc_to_dict(v) for k, v in self.documents.items()},
            "version_history": {k: [self._version_to_dict(v) for v in values] for k, values in self.version_history.items()},
        }
        self.registry_path.write_text(yaml.safe_dump(payload, sort_keys=True), encoding="utf-8")

    def _load_registry(self) -> None:
        payload = yaml.safe_load(self.registry_path.read_text(encoding="utf-8")) or {}
        for doc_id, data in (payload.get("documents") or {}).items():
            self.documents[doc_id] = DocumentMetadata(
                doc_id=doc_id, doc_type=DocumentType(data["doc_type"]), title=data["title"], version=data["version"],
                status=DocumentStatus(data["status"]), epic=data.get("epic"), topics=list(data.get("topics") or []),
                file_path=Path(data["file_path"]), created_date=datetime.fromisoformat(data["created_date"]),
                modified_date=datetime.fromisoformat(data["modified_date"]), author=data["author"],
                dependencies=list(data.get("dependencies") or []), golden_threads=list(data.get("golden_threads") or []))
        for doc_id, values in (payload.get("version_history") or {}).items():
            self.version_history[doc_id] = [DocumentVersion(v["version"], datetime.fromisoformat(v["date"]), v["author"], v["changes"], Path(v["file_path"]), v["checksum"]) for v in values]

    def _count_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for doc in self.documents.values():
            counts[doc.doc_type.value] = counts.get(doc.doc_type.value, 0) + 1
        return counts

    def _count_by_status(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for doc in self.documents.values():
            counts[doc.status.value] = counts.get(doc.status.value, 0) + 1
        return counts

    def _count_by_epic(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for doc in self.documents.values():
            if doc.epic:
                counts[doc.epic] = counts.get(doc.epic, 0) + 1
        return counts

    def generate_report(self) -> str:
        lines = ["# Master Document Registry Report", ""]
        for doc in sorted(self.documents.values(), key=lambda d: d.doc_id):
            lines.append(
                f"- {doc.doc_id}: {doc.title} [{doc.doc_type.value}] "
                f"EPIC={doc.epic or '-'} STATUS={doc.status.value}"
            )
        return "\n".join(lines)

    def get_registry_report(self) -> str:
        return self.generate_report()
