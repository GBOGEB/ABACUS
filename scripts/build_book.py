#!/usr/bin/env python3
"""
DMAIC V3 Book Builder
Compiles Pandoc book from markdown sources with version validation
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

__version__ = "3.3.0"

BOOK_SOURCES = [
    "DMAIC_V3_MASTER_SUMMARY.md",
    "DMAIC_V3_QUICK_REFERENCE.md",
    "12CLUSTER_DMAIC_V3_QUICK_START_GUIDE.md",
    "DMAIC_V3_REFACTORING_PLAN.md",
    "DMAIC_V3_ARCHITECTURE_DIAGRAM.md",
    "DMAIC_V3_12CLUSTER_TEMPORAL_INTEGRATION_MASTER.md",
    "DMAIC_V3_BOOK_STRUCTURE.md",
    "DMAIC_V3_3_IMPLEMENTATION_SUMMARY.md",
    "DMAIC_V3_EXECUTION_SUMMARY.md",
    "DMAIC_TEMPORAL_MAPPING_COMPLETE.md",
    "V2.2_RECURSIVE_HOOKS_VERSION_ALIGNMENT.md",
    "knowledge_packages/README.md",
    "DMAIC_V3_FINAL_REPORT.md",
    "DMAIC_V3_GIT_SETUP_GUIDE.md",
    "DMAIC_V3_GIT_GITHUB_STRATEGY.md",
    "DMAIC_V3_GIT_INTEGRATION_SUMMARY.md",
    "HANDOVER_CLOSURE_COMPLETE_20241112.md",
    "DMAIC_V3_DOCUMENTATION_INDEX.md",
]

def build_pdf():
    """Build PDF version of the book"""
    print("Building PDF...")
    cmd = [
        "pandoc",
        "--from=markdown",
        "--to=pdf",
        "--output=build/DMAIC_V3_BOOK.pdf",
        "--toc",
        "--toc-depth=3",
        "--number-sections",
        "--highlight-style=tango",
        "--pdf-engine=xelatex",
        "--variable=geometry:margin=1in",
        "--variable=fontsize:12pt",
        "--variable=documentclass:book",
        "--variable=colorlinks:true",
        "--variable=linkcolor:blue",
        "--variable=urlcolor:blue",
        "--variable=citecolor:green",
        "book.yaml",
    ] + BOOK_SOURCES
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ PDF built successfully: build/DMAIC_V3_BOOK.pdf")
        return True
    else:
        print(f"❌ PDF build failed: {result.stderr}")
        return False

def build_html():
    """Build HTML version of the book"""
    print("Building HTML...")
    cmd = [
        "pandoc",
        "--from=markdown",
        "--to=html5",
        "--output=build/DMAIC_V3_BOOK.html",
        "--toc",
        "--toc-depth=3",
        "--number-sections",
        "--highlight-style=tango",
        "--standalone",
        "--self-contained",
        "book.yaml",
    ] + BOOK_SOURCES
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ HTML built successfully: build/DMAIC_V3_BOOK.html")
        return True
    else:
        print(f"❌ HTML build failed: {result.stderr}")
        return False

def build_epub():
    """Build EPUB version of the book"""
    print("Building EPUB...")
    cmd = [
        "pandoc",
        "--from=markdown",
        "--to=epub3",
        "--output=build/DMAIC_V3_BOOK.epub",
        "--toc",
        "--toc-depth=3",
        "--number-sections",
        "book.yaml",
    ] + BOOK_SOURCES
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ EPUB built successfully: build/DMAIC_V3_BOOK.epub")
        return True
    else:
        print(f"❌ EPUB build failed: {result.stderr}")
        return False

def main():
    """Main build function"""
    print(f"DMAIC V3 Book Builder v{__version__}")
    print(f"Build started: {datetime.now()}")
    
    Path("build").mkdir(exist_ok=True)
    
    missing = [f for f in BOOK_SOURCES if not Path(f).exists()]
    if missing:
        print(f"❌ Missing source files: {missing}")
        sys.exit(1)
    
    results = {
        "PDF": build_pdf(),
        "HTML": build_html(),
        "EPUB": build_epub(),
    }
    
    print(f"\n{'='*60}")
    print(f"Build Summary ({datetime.now()})")
    print(f"{'='*60}")
    for format_name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{format_name:10} {status}")
    
    if all(results.values()):
        print(f"\n✅ All builds complete!")
        print("Output files:")
        print("  - build/DMAIC_V3_BOOK.pdf")
        print("  - build/DMAIC_V3_BOOK.html")
        print("  - build/DMAIC_V3_BOOK.epub")
        sys.exit(0)
    else:
        print(f"\n❌ Some builds failed. Check errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
