#!/usr/bin/env python3
"""
AbacusVerificationHook — Binary Asset Verification Engine
GBOGEB/ABACUS Governance Pipeline

Processes binary files dropped into Input_Master/:
  1. Calculates SHA256 hash of each binary asset
  2. Creates .mock sidecar files with immutable metadata
  3. Maintains _data/lineage_manifest.json for system-wide tracking

Usage:
  python engines/verification_hook.py
  python engines/verification_hook.py --input-dir Input_Master/ --data-dir _data/
  python engines/verification_hook.py --watch  # continuous monitoring mode
  python engines/verification_hook.py --verify <file>  # verify single file
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── Constants ──
BINARY_EXTENSIONS = {
    ".pptx", ".pdf", ".docx", ".xlsx", ".xls",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".tiff",
    ".mp4", ".mov", ".avi", ".mkv",
    ".zip", ".tar", ".gz", ".7z",
}

MANIFEST_VERSION = "1.0.0"


# ── Utility Functions ──

def sha256_hash(filepath: str, chunk_size: int = 8192) -> str:
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def get_git_commit() -> str | None:
    """Get current git commit SHA, or None if not in a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def get_mime_type(filepath: str) -> str:
    """Infer MIME type from file extension."""
    ext = Path(filepath).suffix.lower()
    mime_map = {
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
        ".mp4": "video/mp4",
        ".zip": "application/zip",
    }
    return mime_map.get(ext, "application/octet-stream")


def now_iso() -> str:
    """Return current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Mock Sidecar File ──

def create_mock_sidecar(filepath: str, file_hash: str, file_size: int) -> dict[str, Any]:
    """Create a .mock sidecar file for a binary asset."""
    path = Path(filepath)
    mock_path = path.with_suffix(path.suffix + ".mock")

    mock_data = {
        "schema_version": MANIFEST_VERSION,
        "filename": path.name,
        "original_path": str(path),
        "sha256": file_hash,
        "file_size": file_size,
        "mime_type": get_mime_type(filepath),
        "ingested_at": now_iso(),
        "render_commit": get_git_commit(),
        "processing_status": "verified",
        "mock_file": str(mock_path),
        "verification_engine": "AbacusVerificationHook/1.0.0",
    }

    with open(mock_path, "w", encoding="utf-8") as f:
        json.dump(mock_data, f, indent=2, sort_keys=False)

    return mock_data


# ── Lineage Manifest ──

def load_manifest(manifest_path: str) -> dict[str, Any]:
    """Load existing manifest or create a new one."""
    path = Path(manifest_path)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {
        "version": MANIFEST_VERSION,
        "last_updated": now_iso(),
        "assets": [],
        "lineage": [],
    }


def save_manifest(manifest: dict[str, Any], manifest_path: str) -> None:
    """Save manifest to disk."""
    path = Path(manifest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest["last_updated"] = now_iso()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=False)


def update_manifest(
    manifest: dict[str, Any],
    mock_data: dict[str, Any],
) -> bool:
    """Add or update an asset record in the manifest. Returns True if new."""
    assets = manifest.get("assets", [])

    # Check for existing entry by filename
    for i, asset in enumerate(assets):
        if asset.get("filename") == mock_data["filename"]:
            # Update existing entry
            old_hash = asset.get("sha256")
            assets[i] = {
                "filename": mock_data["filename"],
                "sha256": mock_data["sha256"],
                "file_size": mock_data["file_size"],
                "mime_type": mock_data["mime_type"],
                "ingested_at": mock_data["ingested_at"],
                "mock_file": mock_data["mock_file"],
                "processing_status": mock_data["processing_status"],
                "previous_sha256": old_hash,
                "updated_at": now_iso(),
            }
            manifest["assets"] = assets
            return False

    # Add new entry
    assets.append({
        "filename": mock_data["filename"],
        "sha256": mock_data["sha256"],
        "file_size": mock_data["file_size"],
        "mime_type": mock_data["mime_type"],
        "ingested_at": mock_data["ingested_at"],
        "mock_file": mock_data["mock_file"],
        "processing_status": mock_data["processing_status"],
    })
    manifest["assets"] = assets
    return True


# ── Processing Logic ──

def process_file(filepath: str, data_dir: str, verbose: bool = True) -> dict[str, Any] | None:
    """Process a single binary file: hash, create .mock, update manifest."""
    path = Path(filepath)

    if not path.exists():
        if verbose:
            print(f"  SKIP: File not found: {filepath}", file=sys.stderr)
        return None

    if path.suffix.lower() not in BINARY_EXTENSIONS:
        if verbose:
            print(f"  SKIP: Non-binary extension: {path.suffix}")
        return None

    if path.suffix == ".mock":
        return None  # Skip sidecar files

    file_size = path.stat().st_size
    if verbose:
        print(f"  Processing: {path.name} ({file_size:,} bytes)")

    # Calculate SHA256
    file_hash = sha256_hash(filepath)
    if verbose:
        print(f"    SHA256: {file_hash}")

    # Create .mock sidecar
    mock_data = create_mock_sidecar(filepath, file_hash, file_size)
    if verbose:
        print(f"    Mock:   {mock_data['mock_file']}")

    # Update manifest
    manifest_path = os.path.join(data_dir, "lineage_manifest.json")
    manifest = load_manifest(manifest_path)
    is_new = update_manifest(manifest, mock_data)
    save_manifest(manifest, manifest_path)

    status = "NEW" if is_new else "UPDATED"
    if verbose:
        print(f"    Status: {status}")
        print(f"    Manifest: {manifest_path}")

    return mock_data


def process_directory(
    input_dir: str,
    data_dir: str,
    verbose: bool = True,
) -> list[dict[str, Any]]:
    """Process all binary files in the input directory."""
    root = Path(input_dir)

    if not root.exists():
        print(f"ERROR: Input directory not found: {input_dir}", file=sys.stderr)
        root.mkdir(parents=True, exist_ok=True)
        print(f"  Created: {input_dir}")
        return []

    results = []
    files = sorted(root.iterdir())
    binary_files = [
        f for f in files
        if f.is_file()
        and f.suffix.lower() in BINARY_EXTENSIONS
        and f.suffix != ".mock"
    ]

    if not binary_files:
        if verbose:
            print(f"  No binary assets found in {input_dir}")
        return results

    if verbose:
        print(f"\nProcessing {len(binary_files)} file(s) in {input_dir}:\n")

    for filepath in binary_files:
        result = process_file(str(filepath), data_dir, verbose)
        if result:
            results.append(result)
        if verbose:
            print()

    return results


def verify_single(filepath: str) -> bool:
    """Verify a single file's .mock sidecar matches current file state."""
    path = Path(filepath)
    mock_path = path.with_suffix(path.suffix + ".mock")

    if not path.exists():
        print(f"ERROR: File not found: {filepath}")
        return False

    if not mock_path.exists():
        print(f"ERROR: No .mock sidecar found: {mock_path}")
        return False

    # Read mock data
    with open(mock_path, encoding="utf-8") as f:
        mock_data = json.load(f)

    # Recalculate hash
    current_hash = sha256_hash(filepath)
    stored_hash = mock_data.get("sha256", "")

    if current_hash == stored_hash:
        print(f"VERIFIED: {path.name}")
        print(f"  SHA256: {current_hash}")
        print(f"  Ingested: {mock_data.get('ingested_at', 'unknown')}")
        return True
    else:
        print(f"MISMATCH: {path.name}")
        print(f"  Current:  {current_hash}")
        print(f"  Recorded: {stored_hash}")
        print(f"  File may have been modified after ingestion!")
        return False


# ── CLI ──

def main() -> int:
    parser = argparse.ArgumentParser(
        description="AbacusVerificationHook — GBOGEB/ABACUS Binary Asset Verification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Workflow:
  1. Drop binary assets into Input_Master/
  2. Run this hook to process them
  3. .mock sidecar files are created alongside each binary
  4. _data/lineage_manifest.json is updated
  5. Commit .mock files and manifest (binaries are .gitignored)

Examples:
  %(prog)s                                          # Process all files in Input_Master/
  %(prog)s --input-dir Input_Master/ --data-dir _data/
  %(prog)s --verify Input_Master/presentation.pptx  # Verify a single file
  %(prog)s --status                                 # Show manifest summary
        """,
    )

    parser.add_argument(
        "--input-dir",
        type=str,
        default="Input_Master",
        help="Directory containing binary assets (default: Input_Master)",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="_data",
        help="Directory for lineage_manifest.json (default: _data)",
    )
    parser.add_argument(
        "--verify",
        type=str,
        help="Verify a single file against its .mock sidecar",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show manifest summary",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    args = parser.parse_args()

    if args.verify:
        return 0 if verify_single(args.verify) else 1

    if args.status:
        manifest_path = os.path.join(args.data_dir, "lineage_manifest.json")
        manifest = load_manifest(manifest_path)
        assets = manifest.get("assets", [])

        if args.format == "json":
            print(json.dumps({
                "version": manifest.get("version"),
                "last_updated": manifest.get("last_updated"),
                "asset_count": len(assets),
                "assets": [{"filename": a["filename"], "sha256": a["sha256"][:16] + "..."} for a in assets],
            }, indent=2))
        else:
            print(f"\nGBOGEB/ABACUS Lineage Manifest Status")
            print(f"{'='*50}")
            print(f"  Version:      {manifest.get('version', 'unknown')}")
            print(f"  Last Updated: {manifest.get('last_updated', 'never')}")
            print(f"  Assets:       {len(assets)}")
            if assets:
                print(f"\n  Tracked Assets:")
                for a in assets:
                    print(f"    - {a['filename']} ({a.get('sha256', '')[:16]}...)")
            print(f"{'='*50}\n")
        return 0

    verbose = not args.quiet
    if verbose:
        print(f"\n{'='*60}")
        print(f"  AbacusVerificationHook — GBOGEB/ABACUS")
        print(f"  Processing: {args.input_dir}")
        print(f"  Manifest:   {args.data_dir}/lineage_manifest.json")
        print(f"{'='*60}")

    results = process_directory(args.input_dir, args.data_dir, verbose)

    if verbose:
        print(f"\nProcessed {len(results)} file(s).")

    if args.format == "json":
        print(json.dumps({"processed": len(results), "results": results}, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
