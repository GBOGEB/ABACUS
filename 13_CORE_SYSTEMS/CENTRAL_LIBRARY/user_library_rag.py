"""User Library RAG – document indexing and retrieval for the ABACUS test surface."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class DocumentChunk:
    chunk_id: str
    doc_id: str
    content: str
    epic: str
    topics: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
    importance_score: float = 0.0


@dataclass
class QueryResult:
    chunk: DocumentChunk
    relevance_score: float
    context: str = ""


class UserLibraryRAG:
    """Simple keyword-based RAG index for ABACUS library documents."""

    INDEX_FILE = "rag_index.json"

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root
        self.chunks: dict[str, DocumentChunk] = {}
        self.doc_to_chunks: dict[str, list[str]] = {}
        self.epic_index: dict[str, list[str]] = {}
        self.topic_index: dict[str, list[str]] = {}
        self.index_path = workspace_root / self.INDEX_FILE
        if self.index_path.exists():
            self._load_index()

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def index_document(
        self,
        doc_id: str,
        content: str,
        epic: str,
        topics: list[str],
        metadata: dict[str, Any] | None = None,
        chunk_size: int = 200,
        chunk_overlap: int = 20,
    ) -> list[str]:
        """Chunk *content* and add to the index; return list of chunk IDs."""
        if metadata is None:
            metadata = {}
        raw_chunks = self._split_text(content, chunk_size, chunk_overlap)
        total = len(raw_chunks)
        chunk_ids: list[str] = []
        for idx, text in enumerate(raw_chunks):
            cid = f"{doc_id}_chunk_{uuid.uuid4().hex[:8]}"
            chunk_meta = dict(metadata)
            chunk_meta.update(
                {
                    "chunk_index": idx,
                    "total_chunks": total,
                    "indexed_date": datetime.utcnow().isoformat(),
                }
            )
            chunk = DocumentChunk(
                chunk_id=cid,
                doc_id=doc_id,
                content=text,
                epic=epic,
                topics=list(topics),
                metadata=chunk_meta,
            )
            self.chunks[cid] = chunk
            chunk_ids.append(cid)
            self.doc_to_chunks.setdefault(doc_id, []).append(cid)
            self.epic_index.setdefault(epic, []).append(cid)
            for topic in topics:
                self.topic_index.setdefault(topic, []).append(cid)
        return chunk_ids

    # ------------------------------------------------------------------
    # Retrieval helpers
    # ------------------------------------------------------------------

    def query(
        self,
        query: str,
        epic: str | None = None,
        topics: list[str] | None = None,
        min_score: float | None = None,
        top_k: int = 5,
    ) -> list[QueryResult]:
        candidates = list(self.chunks.values())
        if epic is not None:
            candidates = [c for c in candidates if c.epic == epic]
        if topics is not None:
            candidates = [
                c for c in candidates if any(t in c.topics for t in topics)
            ]
        results: list[QueryResult] = []
        for chunk in candidates:
            score = self._calculate_relevance(query, chunk)
            if min_score is None or score >= min_score:
                results.append(QueryResult(chunk=chunk, relevance_score=score))
        results.sort(key=lambda r: r.relevance_score, reverse=True)
        return results[:top_k]

    def get_by_epic(self, epic: str) -> list[DocumentChunk]:
        ids = self.epic_index.get(epic, [])
        return [self.chunks[i] for i in ids if i in self.chunks]

    def get_by_topic(self, topic: str) -> list[DocumentChunk]:
        ids = self.topic_index.get(topic, [])
        return [self.chunks[i] for i in ids if i in self.chunks]

    def get_document_chunks(self, doc_id: str) -> list[DocumentChunk]:
        ids = self.doc_to_chunks.get(doc_id, [])
        return [self.chunks[i] for i in ids if i in self.chunks]

    def get_related_chunks(
        self, chunk_id: str, top_k: int = 3
    ) -> list[DocumentChunk]:
        if chunk_id not in self.chunks:
            return []
        source = self.chunks[chunk_id]
        results: list[tuple[float, DocumentChunk]] = []
        for cid, chunk in self.chunks.items():
            if cid == chunk_id:
                continue
            sim = self._calculate_chunk_similarity(source, chunk)
            results.append((sim, chunk))
        results.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in results[:top_k]]

    def generate_summary(self, doc_id: str, max_length: int = 100) -> str:
        chunks = self.get_document_chunks(doc_id)
        if not chunks:
            return ""
        combined = " ".join(c.content for c in chunks)
        return combined[:max_length]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_index(self) -> None:
        data: dict[str, Any] = {
            "chunks": {
                cid: {
                    "chunk_id": c.chunk_id,
                    "doc_id": c.doc_id,
                    "content": c.content,
                    "epic": c.epic,
                    "topics": c.topics,
                    "metadata": c.metadata,
                }
                for cid, c in self.chunks.items()
            },
            "doc_to_chunks": self.doc_to_chunks,
            "epic_index": self.epic_index,
            "topic_index": self.topic_index,
        }
        self.index_path.write_text(json.dumps(data, indent=2))

    def _load_index(self) -> None:
        try:
            data = json.loads(self.index_path.read_text())
        except Exception:
            return
        for cid, cd in data.get("chunks", {}).items():
            self.chunks[cid] = DocumentChunk(
                chunk_id=cd["chunk_id"],
                doc_id=cd["doc_id"],
                content=cd["content"],
                epic=cd["epic"],
                topics=cd["topics"],
                metadata=cd.get("metadata", {}),
            )
        self.doc_to_chunks = data.get("doc_to_chunks", {})
        self.epic_index = data.get("epic_index", {})
        self.topic_index = data.get("topic_index", {})

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def generate_report(self) -> str:
        lines = [
            "User Library RAG Index Report",
            "=" * 40,
            f"Total chunks : {len(self.chunks)}",
            f"Documents    : {len(self.doc_to_chunks)}",
        ]
        for doc_id in self.doc_to_chunks:
            lines.append(f"  {doc_id}")
        lines.append("")
        lines.append("EPICs:")
        for epic in self.epic_index:
            lines.append(f"  {epic}: {len(self.epic_index[epic])} chunks")
        lines.append("")
        lines.append("Topics:")
        for topic in self.topic_index:
            lines.append(f"  {topic}: {len(self.topic_index[topic])} chunks")
        return "\n".join(lines)

    def get_index_report(self) -> str:
        return self.generate_report()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _split_text(
        text: str, chunk_size: int, chunk_overlap: int
    ) -> list[str]:
        if len(text) <= chunk_size:
            return [text]
        chunks: list[str] = []
        step = max(1, chunk_size - chunk_overlap)
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            if end >= len(text):
                break
            start += step
        return chunks

    def _build_context(self, chunk_id: str, window: int = 1) -> str:
        if chunk_id not in self.chunks:
            return ""
        chunk = self.chunks[chunk_id]
        sibling_ids = self.doc_to_chunks.get(chunk.doc_id, [])
        try:
            pos = sibling_ids.index(chunk_id)
        except ValueError:
            return chunk.content
        start = max(0, pos - window)
        end = min(len(sibling_ids), pos + window + 1)
        parts = [
            self.chunks[sid].content
            for sid in sibling_ids[start:end]
            if sid in self.chunks
        ]
        return " ".join(parts)

    def _calculate_chunk_importance(
        self, content: str, epic: str, topics: list[str]
    ) -> float:
        score = len(content.split()) * 1.0
        if epic.upper() in ("GLOOB", "DMAIC"):
            score *= 1.5
        for topic in topics:
            if topic.lower().startswith("phase") and topic[-1].isdigit():
                phase_num = int(topic[-1])
                score += max(0, (5 - phase_num) * 2)
        return score

    def _calculate_relevance(self, query: str, chunk: DocumentChunk) -> float:
        if not query:
            return 0.0
        query_words = set(query.lower().split())
        content_words = chunk.content.lower().split()
        if not content_words:
            return 0.0
        hits = sum(1 for w in content_words if w in query_words)
        return (hits / len(content_words)) * 100.0

    @staticmethod
    def _calculate_chunk_similarity(
        chunk1: DocumentChunk, chunk2: DocumentChunk
    ) -> float:
        words1 = set(chunk1.content.lower().split())
        words2 = set(chunk2.content.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union else 0.0
