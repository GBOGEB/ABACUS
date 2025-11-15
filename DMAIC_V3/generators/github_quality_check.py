from typing import Any
#!/usr/bin/env python3
"""
DMAIC V3 - GitHub Quality Check & Cleanup
Prepares repository for GitHub with quality checks, cleanup, and CI/CD validation
"""

import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

class GitHubQualityCheck:
    """Comprehensive GitHub quality check and cleanup"""
    
    # Files to KEEP (core system)
    CORE_PYTHON_FILES = {
        # Master Document System (KEEP)
        "master_document_system/master_engine.py",
        "master_document_system/demo_python_dashboard.py",
        "master_document_system/integration_example.py",
        "master_document_system/quick_start.py",
        "master_document_system/core/dmaic_manager.py",
        "master_document_system/core/input_manager.py",
        "master_document_system/core/style_extractor.py",
        "master_document_system/core/temporal_tracker.py",
        "master_document_system/core/__init__.py",
        
        # DMAIC V3 Generators (KEEP)
        "DMAIC_V3/generators/execution_tracker.py",
        "DMAIC_V3/generators/documentation_aligner.py",
        "DMAIC_V3/generators/master_reconciliation.py",
        "DMAIC_V3/generators/test_real_execution.py",
        "DMAIC_V3/generators/test_integration_pipeline.py",
        "DMAIC_V3/generators/github_quality_check.py",
    }
    
    # Patterns to REMOVE (temporary/test files)
    REMOVE_PATTERNS = [
        # Temporary test files
        "**/test_*.py",
        "**/*_test.py",
        "**/temp_*.py",
        "**/*_temp.py",
        
        # Backup files
        "**/*_backup*.py",
        "**/*_old.py",
        "**/*_v1.py",
        "**/*_v2.py",
        
        # Analysis/debug files
        "**/analyze_*.py",
        "**/debug_*.py",
        "**/fix_*.py",
        "**/quick_*.py",
        "**/simple_*.py",
        
        # Jupyter notebooks
        "**/*.ipynb",
        
        # Python cache
        "**/__pycache__",
        "**/*.pyc",
        "**/*.pyo",
        "**/*.pyd",
        
        # IDE files
        "**/.vscode",
        "**/.idea",
        "**/*.swp",
        "**/*.swo",
        
        # OS files
        "**/.DS_Store",
        "**/Thumbs.db",
        "**/desktop.ini",
    ]
    
    # Binary extensions to exclude from git
    BINARY_EXTENSIONS = {
        ".exe", ".dll", ".so", ".dylib", ".bin",
        ".pdf", ".docx", ".xlsx", ".pptx",
        ".png", ".jpg", ".jpeg", ".gif", ".bmp",
        ".zip", ".tar", ".gz", ".7z", ".rar",
        ".mp4", ".avi", ".mov", ".wmv",
        ".mp3", ".wav", ".flac",
    }
    
    def __init__(self, root_dir: Path):
        """TODO: Add function description"""

        self.root_dir = root_dir
        self.report = {
            "timestamp": datetime.now().isoformat(),
            "removed_files": [],
            "kept_files": [],
            "quality_checks": {},
            "git_status": {}
        }
    
    def cleanup_temporary_files(self) -> Any:
        """Remove temporary and test files"""
        print("\n" + "="*80)
        print("CLEANUP: Removing temporary files")
        print("="*80)
        
        removed_count = 0
        
        # Remove files matching patterns (except core files)
        for pattern in self.REMOVE_PATTERNS:
            for file_path in self.root_dir.glob(pattern):
                if file_path.is_file():
                    relative_path = str(file_path.relative_to(self.root_dir))
                    
                    # Skip if it's a core file
                    if relative_path.replace("\\", "/") in self.CORE_PYTHON_FILES:
                        print(f"[KEEP] {relative_path} (core file)")
                        continue
                    
                    # Remove the file
                    try:
                        file_path.unlink()
                        print(f"[REMOVE] {relative_path}")
                        self.report["removed_files"].append(relative_path)
                        removed_count += 1
                    except Exception as e:
                        print(f"[ERROR] Failed to remove {relative_path}: {e}")
                
                elif file_path.is_dir():
                    relative_path = str(file_path.relative_to(self.root_dir))
                    try:
                        shutil.rmtree(file_path)
                        print(f"[REMOVE DIR] {relative_path}")
                        self.report["removed_files"].append(relative_path)
                        removed_count += 1
                    except Exception as e:
                        print(f"[ERROR] Failed to remove {relative_path}: {e}")
        
        print(f"\nRemoved {removed_count} temporary files/directories")
    
    def validate_core_files(self) -> Any:
        """Validate that all core files exist and are valid Python"""
        print("\n" + "="*80)
        print("VALIDATION: Checking core Python files")
        print("="*80)
        
        valid_count = 0
        invalid_count = 0
        
        for core_file in self.CORE_PYTHON_FILES:
            file_path = self.root_dir / core_file
            
            if not file_path.exists():
                print(f"[MISSING] {core_file}")
                invalid_count += 1
                continue
            
            # Check if valid Python syntax
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    compile(f.read(), str(file_path), 'exec')
                print(f"[VALID] {core_file}")
                self.report["kept_files"].append(core_file)
                valid_count += 1
            except SyntaxError as e:
                print(f"[INVALID] {core_file}: {e}")
                invalid_count += 1
        
        print(f"\nValid: {valid_count}, Invalid: {invalid_count}")
        self.report["quality_checks"]["core_files_valid"] = valid_count
        self.report["quality_checks"]["core_files_invalid"] = invalid_count
    
    def run_linting(self) -> Any:
        """Run flake8 linting on core files"""
        print("\n" + "="*80)
        print("LINTING: Running flake8")
        print("="*80)
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "flake8", 
                 "master_document_system", "DMAIC_V3/generators",
                 "--max-line-length=120",
                 "--ignore=E501,W503,E203",
                 "--count",
                 "--statistics"],
                capture_output=True,
                text=True,
                cwd=str(self.root_dir)
            )
            
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            
            self.report["quality_checks"]["flake8_exit_code"] = result.returncode
            self.report["quality_checks"]["flake8_output"] = result.stdout
            
        except Exception as e:
            print(f"[ERROR] Flake8 not installed or failed: {e}")
            self.report["quality_checks"]["flake8_error"] = str(e)
    
    def run_formatting_check(self) -> Any:
        """Check code formatting with black"""
        print("\n" + "="*80)
        print("FORMATTING: Checking with black")
        print("="*80)
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "black",
                 "--check",
                 "--line-length=120",
                 "master_document_system", "DMAIC_V3/generators"],
                capture_output=True,
                text=True,
                cwd=str(self.root_dir)
            )
            
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            
            self.report["quality_checks"]["black_exit_code"] = result.returncode
            self.report["quality_checks"]["black_output"] = result.stdout
            
        except Exception as e:
            print(f"[ERROR] Black not installed or failed: {e}")
            self.report["quality_checks"]["black_error"] = str(e)
    
    def run_type_checking(self) -> Any:
        """Run mypy type checking"""
        print("\n" + "="*80)
        print("TYPE CHECKING: Running mypy")
        print("="*80)
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "mypy",
                 "master_document_system", "DMAIC_V3/generators",
                 "--ignore-missing-imports",
                 "--no-strict-optional"],
                capture_output=True,
                text=True,
                cwd=str(self.root_dir)
            )
            
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            
            self.report["quality_checks"]["mypy_exit_code"] = result.returncode
            self.report["quality_checks"]["mypy_output"] = result.stdout
            
        except Exception as e:
            print(f"[WARNING] Mypy not installed or failed: {e}")
            self.report["quality_checks"]["mypy_error"] = str(e)
    
    def create_gitignore(self) -> Any:
        """Create comprehensive .gitignore"""
        print("\n" + "="*80)
        print("GIT: Creating .gitignore")
        print("="*80)
        
        gitignore_content = """# DMAIC V3 - .gitignore

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
venv_*/
ENV/
env/
.venv

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
desktop.ini

# Jupyter
.ipynb_checkpoints/
*.ipynb

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Temporary files
temp_*
*_temp.*
*_backup.*
*_old.*

# Binaries (keep in LFS or external storage)
*.exe
*.dll
*.so
*.dylib
*.pdf
*.docx
*.xlsx
*.pptx
*.png
*.jpg
*.jpeg
*.gif
*.zip
*.tar
*.gz

# Output directories (keep structure, ignore contents)
output/execution_reports/*.json
output/integration_reports/*.json
output/dmaic_reports/*.json
!output/**/.gitkeep

# Logs
*.log
logs/

# Environment
.env
.env.local
"""
        
        gitignore_path = self.root_dir / ".gitignore"
        with open(gitignore_path, 'w', encoding='utf-8') as f:
            f.write(gitignore_content)
        
        print(f"[CREATED] .gitignore")
        self.report["git_status"]["gitignore_created"] = True
    
    def create_gitattributes(self) -> Any:
        """Create .gitattributes for LFS and line endings"""
        print("\n" + "="*80)
        print("GIT: Creating .gitattributes")
        print("="*80)
        
        gitattributes_content = """# DMAIC V3 - .gitattributes

# Line endings
* text=auto
*.py text eol=lf
*.md text eol=lf
*.yml text eol=lf
*.yaml text eol=lf
*.json text eol=lf
*.txt text eol=lf
*.sh text eol=lf
*.bat text eol=crlf

# Binary files (Git LFS)
*.pdf filter=lfs diff=lfs merge=lfs -text
*.docx filter=lfs diff=lfs merge=lfs -text
*.xlsx filter=lfs diff=lfs merge=lfs -text
*.pptx filter=lfs diff=lfs merge=lfs -text
*.png filter=lfs diff=lfs merge=lfs -text
*.jpg filter=lfs diff=lfs merge=lfs -text
*.jpeg filter=lfs diff=lfs merge=lfs -text
*.gif filter=lfs diff=lfs merge=lfs -text
*.zip filter=lfs diff=lfs merge=lfs -text
*.tar filter=lfs diff=lfs merge=lfs -text
*.gz filter=lfs diff=lfs merge=lfs -text
*.exe filter=lfs diff=lfs merge=lfs -text
*.dll filter=lfs diff=lfs merge=lfs -text
"""
        
        gitattributes_path = self.root_dir / ".gitattributes"
        with open(gitattributes_path, 'w', encoding='utf-8') as f:
            f.write(gitattributes_content)
        
        print(f"[CREATED] .gitattributes")
        self.report["git_status"]["gitattributes_created"] = True
    
    def initialize_git_repo(self) -> Any:
        """Initialize git repository if not exists"""
        print("\n" + "="*80)
        print("GIT: Initializing repository")
        print("="*80)
        
        git_dir = self.root_dir / ".git"
        
        if git_dir.exists():
            print("[EXISTS] Git repository already initialized")
            self.report["git_status"]["repo_exists"] = True
            return
        
        try:
            subprocess.run(
                ["git", "init"],
                cwd=str(self.root_dir),
                check=True
            )
            print("[CREATED] Git repository initialized")
            self.report["git_status"]["repo_initialized"] = True
            
            # Set default branch to main
            subprocess.run(
                ["git", "branch", "-M", "main"],
                cwd=str(self.root_dir),
                check=True
            )
            print("[CONFIGURED] Default branch set to 'main'")
            
        except Exception as e:
            print(f"[ERROR] Failed to initialize git: {e}")
            self.report["git_status"]["init_error"] = str(e)
    
    def create_requirements_txt(self) -> Any:
        """Create comprehensive requirements.txt"""
        print("\n" + "="*80)
        print("DEPENDENCIES: Creating requirements.txt")
        print("="*80)
        
        requirements_content = """# DMAIC V3 - Python Dependencies

# Core dependencies
python-docx>=0.8.11
openpyxl>=3.1.2
PyYAML>=6.0.1
Jinja2>=3.1.2

# Testing
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.11.1

# Code quality
flake8>=6.1.0
black>=23.12.1
mypy>=1.7.0
pylint>=3.0.0

# Type stubs
types-PyYAML>=6.0.12
types-openpyxl>=3.1.0

# Pre-commit
pre-commit>=3.5.0

# Flask (for API)
Flask>=3.0.0
Flask-CORS>=4.0.0

# FastAPI (alternative)
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.5.0

# Documentation
sphinx>=7.2.0
sphinx-rtd-theme>=2.0.0

# Utilities
python-dateutil>=2.8.2
colorama>=0.4.6
tqdm>=4.66.0
"""
        
        requirements_path = self.root_dir / "requirements.txt"
        with open(requirements_path, 'w', encoding='utf-8') as f:
            f.write(requirements_content)
        
        print(f"[CREATED] requirements.txt")
        self.report["git_status"]["requirements_created"] = True
    
    def create_setup_py(self) -> Any:
        """Create setup.py for package installation"""
        print("\n" + "="*80)
        print("PACKAGE: Creating setup.py")
        print("="*80)
        
        setup_content = """#!/usr/bin/env python3
\"\"\"
DMAIC V3 - Master Document System
Setup configuration for package installation
\"\"\"

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="dmaic-v3-master-document-system",
    version="3.1.0",
    author="DMAIC V3 Team",
    description="Master Document System with DMAIC V3 Integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/dmaic-v3",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Documentation",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "dmaic-v3=master_document_system.master_engine:main",
        ],
    },
)
"""
        
        setup_path = self.root_dir / "setup.py"
        with open(setup_path, 'w', encoding='utf-8') as f:
            f.write(setup_content)
        
        print(f"[CREATED] setup.py")
        self.report["git_status"]["setup_created"] = True
    
    def save_report(self) -> Any:
        """Save quality check report"""
        report_dir = self.root_dir / "output" / "quality_reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"github_quality_report_{timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.report, f, indent=2, ensure_ascii=False)
        
        print(f"\n[REPORT] Saved to: {report_file}")
    
    def print_summary(self) -> Any:
        """Print quality check summary"""
        print("\n" + "="*80)
        print("GITHUB QUALITY CHECK SUMMARY")
        print("="*80)
        
        print(f"\nCleanup:")
        print(f"  Removed files: {len(self.report['removed_files'])}")
        print(f"  Kept core files: {len(self.report['kept_files'])}")
        
        print(f"\nQuality Checks:")
        for key, value in self.report["quality_checks"].items():
            print(f"  {key}: {value}")
        
        print(f"\nGit Status:")
        for key, value in self.report["git_status"].items():
            print(f"  {key}: {value}")
        
        print("\n" + "="*80)
        print("NEXT STEPS:")
        print("="*80)
        print("1. Review removed files list")
        print("2. Fix any linting/formatting issues")
        print("3. Run: git add .")
        print("4. Run: git commit -m 'Initial commit - DMAIC V3'")
        print("5. Run: git remote add origin <your-github-repo-url>")
        print("6. Run: git push -u origin main")
        print("7. Enable GitHub Actions in repository settings")
        print("8. Install pre-commit hooks: pre-commit install")
        print("="*80)
    
    def run_all_checks(self) -> Any:
        """Run all quality checks"""
        print("="*80)
        print("DMAIC V3 - GITHUB QUALITY CHECK & CLEANUP")
        print("="*80)
        print(f"Timestamp: {self.report['timestamp']}")
        print("="*80)
        
        # Cleanup
        self.cleanup_temporary_files()
        
        # Validation
        self.validate_core_files()
        
        # Quality checks
        self.run_linting()
        self.run_formatting_check()
        self.run_type_checking()
        
        # Git setup
        self.create_gitignore()
        self.create_gitattributes()
        self.initialize_git_repo()
        
        # Package setup
        self.create_requirements_txt()
        self.create_setup_py()
        
        # Report
        self.save_report()
        self.print_summary()

def main() -> Any:
    """TODO: Add function description"""

    root_dir = Path(__file__).parent.parent.parent
    checker = GitHubQualityCheck(root_dir)
    checker.run_all_checks()

if __name__ == "__main__":
    main()
