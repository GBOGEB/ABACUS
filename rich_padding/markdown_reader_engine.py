"""Minimal deterministic Markdown reader used by the ABACUS runtime tests."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ElementType(Enum):
    HEADER = "header"
    LINK = "link"
    CODE_BLOCK = "code_block"
    TEXT = "text"


@dataclass
class MarkdownElement:
    element_type: ElementType
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LinkValidationResult:
    link: str
    valid: bool
    link_type: str
    reason: str = ""


@dataclass
class ArtifactMetadata:
    path: str
    artifact_type: str
    size: int


class MarkdownReaderEngine:
    LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    def __init__(self, workspace: Path | str):
        self.workspace = Path(workspace)
        self.artifact_patterns = {
            "yaml": ("*.yaml", "*.yml"),
            "json": ("*.json",),
            "python": ("*.py",),
            "markdown": ("*.md",),
        }
        self.output_dir = self.workspace / "rich_padding" / "reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def parse_markdown(self, content: str) -> list[MarkdownElement]:
        elements: list[MarkdownElement] = []
        in_code = False
        code_lang = ""
        code_lines: list[str] = []
        for line in content.splitlines():
            if line.startswith("```"):
                if in_code:
                    elements.append(MarkdownElement(ElementType.CODE_BLOCK, "\n".join(code_lines), {"language": code_lang}))
                    in_code = False
                    code_lang = ""
                    code_lines = []
                else:
                    in_code = True
                    code_lang = line[3:].strip()
                continue
            if in_code:
                code_lines.append(line)
                continue
            if line.startswith("#"):
                elements.append(MarkdownElement(ElementType.HEADER, line))
            for match in self.LINK_RE.finditer(line):
                elements.append(MarkdownElement(ElementType.LINK, match.group(1), {"target": match.group(2)}))
            if line.strip() and not line.startswith("#"):
                elements.append(MarkdownElement(ElementType.TEXT, line))
        if in_code:
            elements.append(MarkdownElement(ElementType.CODE_BLOCK, "\n".join(code_lines), {"language": code_lang}))
        return elements

    def validate_link(self, link: str, base_path: Path | str | None) -> LinkValidationResult:
        if link.startswith(("http://", "https://")):
            return LinkValidationResult(link=link, valid=True, link_type="external")
        base = Path(base_path) if base_path is not None else self.workspace
        candidate = (base / link).resolve() if not Path(link).is_absolute() else Path(link)
        return LinkValidationResult(link=link, valid=candidate.exists(), link_type="internal", reason="" if candidate.exists() else "missing")

    def discover_artifacts(self, root: Path | str) -> list[ArtifactMetadata]:
        root_path = Path(root)
        artifacts: list[ArtifactMetadata] = []
        for artifact_type, patterns in self.artifact_patterns.items():
            for pattern in patterns:
                for path in root_path.rglob(pattern):
                    if path.is_file():
                        artifacts.append(ArtifactMetadata(str(path), artifact_type, path.stat().st_size))
        return sorted(artifacts, key=lambda a: (a.artifact_type, a.path))

    def generate_statistics(self, root: Path | str) -> dict[str, Any]:
        root_path = Path(root)
        files = list(root_path.rglob("*.md"))
        total_elements = 0
        counts: dict[str, int] = {}
        for path in files:
            for element in self.parse_markdown(path.read_text(encoding="utf-8", errors="ignore")):
                total_elements += 1
                key = element.element_type.value
                counts[key] = counts.get(key, 0) + 1
        return {"files_processed": len(files), "total_elements": total_elements, "elements_by_type": counts}

    def export_results(self, elements: list[MarkdownElement], stats: dict[str, Any], format: str = "json") -> str:
        if format != "json":
            raise ValueError(f"Unsupported export format: {format}")
        output = self.output_dir / "markdown_reader_results.json"
        payload = {
            "elements": [
                {"element_type": item.element_type.value, "content": item.content, "metadata": item.metadata}
                for item in elements
            ],
            "stats": stats,
        }
        output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return str(output)
