"""
Notebook parser for codespace_jyperter ↔ ABACUS integration.

Reads Jupyter notebook (.ipynb) files and extracts structured cell-level data
consumable by ABACUS's DMAIC phases (primarily Phase2Measure and Phase6Knowledge).

Usage
-----
From code::

    from integration.codespace_jyperter.notebook_parser import NotebookParser
    parser = NotebookParser()
    extract = parser.parse("path/to/notebook.ipynb")
    parser.save_extract(extract, "integration/codespace_jyperter/extracts/")

From CLI::

    python -m integration.codespace_jyperter.notebook_parser path/to/notebook.ipynb

Output format
-------------
The ``parse()`` method returns a ``NotebookExtract`` dict with the schema
described in ``integration/codespace_jyperter/abacus_contract.yaml``
(``produced_for_abacus[0]`` — notebook_cell_extracts).
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

CellExtract = Dict[str, Any]

NotebookExtract = Dict[str, Any]  # see _EXTRACT_SCHEMA in contract YAML


# ---------------------------------------------------------------------------
# NotebookParser
# ---------------------------------------------------------------------------

class NotebookParser:
    """Parse a .ipynb file and emit ABACUS-compatible cell extract JSON."""

    #: Notebook format versions supported
    SUPPORTED_NBFORMAT = {4}

    def parse(self, notebook_path: str | Path) -> NotebookExtract:
        """Parse *notebook_path* and return a structured extract dict.

        Args:
            notebook_path: Path to a ``.ipynb`` file.

        Returns:
            NotebookExtract dict containing:
                notebook_path (str): resolved path
                notebook_sha256 (str): SHA-256 hex digest of the raw file
                nbformat (int): notebook format version
                kernel_name (str): kernel display name (or "unknown")
                language (str): kernel language (or "unknown")
                timestamp (str): ISO-8601 parse timestamp (UTC)
                cells (list[CellExtract]): per-cell data
                cell_count (int)
                code_cell_count (int)
                markdown_cell_count (int)
                raw_cell_count (int)

        Raises:
            FileNotFoundError: if *notebook_path* does not exist.
            ValueError: if the file is not a supported .ipynb.
        """
        path = Path(notebook_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Notebook not found: {path}")
        if path.suffix.lower() != ".ipynb":
            raise ValueError(f"Expected a .ipynb file, got: {path.suffix}")

        raw = path.read_bytes()
        sha256 = hashlib.sha256(raw).hexdigest()
        nb = json.loads(raw)

        nbformat = nb.get("nbformat", 0)
        if nbformat not in self.SUPPORTED_NBFORMAT:
            raise ValueError(
                f"Unsupported notebook format version {nbformat}. "
                f"Supported: {self.SUPPORTED_NBFORMAT}"
            )

        kernel_info = nb.get("metadata", {}).get("kernelspec", {})
        language_info = nb.get("metadata", {}).get("language_info", {})

        cells: List[CellExtract] = []
        code_count = 0
        markdown_count = 0
        raw_count = 0

        for idx, cell in enumerate(nb.get("cells", [])):
            cell_type = cell.get("cell_type", "unknown")
            source_lines = cell.get("source", [])
            # source can be a list of strings or a single string
            source = (
                "".join(source_lines)
                if isinstance(source_lines, list)
                else source_lines
            )
            outputs = cell.get("outputs", [])
            execution_count = cell.get("execution_count")
            cell_metadata = cell.get("metadata", {})

            cells.append(
                {
                    "cell_index": idx,
                    "cell_type": cell_type,
                    "source": source,
                    "outputs": _sanitize_outputs(outputs),
                    "execution_count": execution_count,
                    "metadata": cell_metadata,
                }
            )

            if cell_type == "code":
                code_count += 1
            elif cell_type == "markdown":
                markdown_count += 1
            elif cell_type == "raw":
                raw_count += 1

        return {
            "notebook_path": str(path),
            "notebook_sha256": sha256,
            "nbformat": nbformat,
            "kernel_name": kernel_info.get("display_name", "unknown"),
            "language": (
                language_info.get("name")
                or kernel_info.get("language", "unknown")
            ),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "cells": cells,
            "cell_count": len(cells),
            "code_cell_count": code_count,
            "markdown_cell_count": markdown_count,
            "raw_cell_count": raw_count,
        }

    def save_extract(
        self,
        extract: NotebookExtract,
        output_dir: str | Path,
        *,
        iteration: Optional[int] = None,
    ) -> Path:
        """Serialise *extract* to JSON inside *output_dir*.

        The output filename is derived from the notebook name and an optional
        iteration suffix so that successive runs do not overwrite each other.

        Args:
            extract: Dict returned by :meth:`parse`.
            output_dir: Directory to write the JSON file into (created if
                needed).
            iteration: Optional iteration number appended to the filename.

        Returns:
            Path to the written JSON file.
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        nb_stem = Path(extract["notebook_path"]).stem
        suffix = f"_iter{iteration}" if iteration is not None else ""
        filename = f"notebook_cells_{nb_stem}{suffix}.json"
        dest = out / filename
        dest.write_text(json.dumps(extract, indent=2), encoding="utf-8")
        return dest

    def build_knowledge_source(
        self,
        extract: NotebookExtract,
        *,
        source_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build a knowledge-source descriptor for Phase6Knowledge registration.

        Args:
            extract: Dict returned by :meth:`parse`.
            source_id: Optional explicit ID; defaults to
                ``codespace_jyperter:<notebook_sha256[:8]>``.

        Returns:
            Dict matching the ``notebook_knowledge_source`` schema in the
            integration contract.
        """
        sha_prefix = extract["notebook_sha256"][:8]
        sid = source_id or f"codespace_jyperter:{sha_prefix}"
        return {
            "source_id": sid,
            "source_type": "notebook_extract",
            "repo": "GBOGEB/codespace_jyperter",
            "extract_path": extract["notebook_path"],
            "timestamp": extract["timestamp"],
            "cell_count": extract["cell_count"],
            "code_cell_count": extract["code_cell_count"],
            "markdown_cell_count": extract["markdown_cell_count"],
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sanitize_outputs(outputs: list) -> list:
    """Return outputs stripped of binary/image data to keep JSON compact."""
    clean = []
    for out in outputs:
        if not isinstance(out, dict):
            continue
        o = dict(out)
        # Remove large binary fields
        data = o.get("data", {})
        if isinstance(data, dict):
            o["data"] = {
                k: v
                for k, v in data.items()
                if not k.startswith("image/") and k != "application/octet-stream"
            }
        clean.append(o)
    return clean


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _main(argv: List[str]) -> int:
    if not argv:
        print("Usage: python -m integration.codespace_jyperter.notebook_parser <notebook.ipynb>", file=sys.stderr)
        return 1
    parser = NotebookParser()
    for nb_path in argv:
        try:
            extract = parser.parse(nb_path)
            print(json.dumps(extract, indent=2))
        except (FileNotFoundError, ValueError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
