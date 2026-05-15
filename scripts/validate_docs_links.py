#!/usr/bin/env python3
"""
Validate docs internal links (markdown + html) to prevent broken navigation.
"""

import re
import logging
from pathlib import Path
from typing import Iterable, List, Tuple

ROOT_DIR = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT_DIR / "docs"
LOGGER = logging.getLogger(__name__)

MD_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
HTML_HREF = re.compile(r"""(?:href|src)\s*=\s*(["'])(.*?)\1""", re.IGNORECASE)


def _iter_docs_files() -> Iterable[Path]:
    for pattern in ("**/*.md", "**/*.html"):
        yield from DOCS_DIR.glob(pattern)


def _is_external(link: str) -> bool:
    normalized = link.strip()
    return (
        normalized.startswith("http://")
        or normalized.startswith("https://")
        or normalized.startswith("mailto:")
        or normalized.startswith("#")
    )


def _normalize_target(base_file: Path, link: str) -> Path:
    without_anchor = link.split("#", 1)[0]
    target = Path(without_anchor)
    if target.is_absolute():
        return target
    return (base_file.parent / target).resolve()


def _collect_links(file_path: Path) -> List[str]:
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    if file_path.suffix.lower() == ".md":
        return MD_LINK.findall(content)
    return [match[1] for match in HTML_HREF.findall(content)]


def main() -> int:
    if not DOCS_DIR.exists():
        LOGGER.warning("docs directory not found; skipping checks")
        return 0

    errors: List[Tuple[str, str]] = []
    for file_path in sorted(set(_iter_docs_files())):
        if not file_path.is_file():
            continue
        for link in _collect_links(file_path):
            if _is_external(link):
                continue
            resolved = _normalize_target(file_path, link)
            if not resolved.exists():
                errors.append((str(file_path.relative_to(ROOT_DIR)), link))

    if errors:
        LOGGER.error("Broken docs links detected:")
        for source, link in errors:
            LOGGER.error("  - %s: %s", source, link)
        return 1

    LOGGER.info("Docs link validation passed")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    raise SystemExit(main())
