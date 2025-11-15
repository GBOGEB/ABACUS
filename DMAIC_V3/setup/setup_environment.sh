#!/bin/bash
# DMAIC V3.0 - Bash Setup Script
# Auto-venv activation and dependency management for Linux/Mac
# Version: 3.0.0

set -e

# Configuration
VENV_NAME=".venv"
FORCE=false
SKIP_DEPENDENCIES=false
VALIDATE=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
print_success() { echo -e "${GREEN}$1${NC}"; }
print_info() { echo -e "${CYAN}$1${NC}"; }
print_warning() { echo -e "${YELLOW}$1${NC}"; }
print_error() { echo -e "${RED}$1${NC}"; }

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE=true
            shift
            ;;
        --skip-dependencies)
            SKIP_DEPENDENCIES=true
            shift
            ;;
        --validate)
            VALIDATE=true
            shift
            ;;
        --venv-name)
            VENV_NAME="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--force] [--skip-dependencies] [--validate] [--venv-name NAME]"
            exit 1
            ;;
    esac
done

echo "================================================================================"
echo "DMAIC V3.0 - Environment Setup (Bash)"
echo "================================================================================"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_PATH="$SCRIPT_DIR/$VENV_NAME"

# Check Python installation
print_info "[1/7] Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PYTHON_VERSION=$(python3 --version)
    print_success "  ✓ $PYTHON_VERSION"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    PYTHON_VERSION=$(python --version)
    print_success "  ✓ $PYTHON_VERSION"
else
    print_error "  ✗ Python not found. Please install Python 3.8 or higher."
    exit 1
fi

# Check Python version
VERSION_CHECK=$($PYTHON_CMD -c 'import sys; print(1 if sys.version_info >= (3, 8) else 0)')
if [ "$VERSION_CHECK" -eq 0 ]; then
    print_error "  ✗ Python 3.8 or higher required. Found: $PYTHON_VERSION"
    exit 1
fi
print_success "  ✓ Python version meets requirements (>= 3.8)"

# Check if virtual environment exists
print_info "[2/7] Checking virtual environment..."
if [ -d "$VENV_PATH" ]; then
    if [ "$FORCE" = true ]; then
        print_warning "  ⚠ Removing existing virtual environment..."
        rm -rf "$VENV_PATH"
        print_success "  ✓ Removed existing virtual environment"
    else
        print_success "  ✓ Virtual environment exists: $VENV_PATH"
    fi
fi

# Create virtual environment if needed
if [ ! -d "$VENV_PATH" ]; then
    print_info "  Creating virtual environment: $VENV_PATH"
    $PYTHON_CMD -m venv "$VENV_PATH"
    
    if [ $? -eq 0 ]; then
        print_success "  ✓ Virtual environment created"
    else
        print_error "  ✗ Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
print_info "[3/7] Activating virtual environment..."
ACTIVATE_SCRIPT="$VENV_PATH/bin/activate"

if [ -f "$ACTIVATE_SCRIPT" ]; then
    source "$ACTIVATE_SCRIPT"
    print_success "  ✓ Virtual environment activated"
else
    print_error "  ✗ Activation script not found: $ACTIVATE_SCRIPT"
    exit 1
fi

# Upgrade pip
print_info "[4/7] Upgrading pip..."
python -m pip install --upgrade pip --quiet
if [ $? -eq 0 ]; then
    print_success "  ✓ pip upgraded"
else
    print_warning "  ⚠ Could not upgrade pip"
fi

# Install/upgrade setuptools and wheel
print_info "[5/7] Installing build tools..."
python -m pip install --upgrade setuptools wheel --quiet
if [ $? -eq 0 ]; then
    print_success "  ✓ Build tools installed"
else
    print_warning "  ⚠ Could not install build tools"
fi

# Install dependencies
if [ "$SKIP_DEPENDENCIES" = false ]; then
    print_info "[6/7] Installing dependencies..."
    
    # Check for requirements.txt
    REQUIREMENTS_FILE=""
    if [ -f "$SCRIPT_DIR/DMAIC_V3/requirements.txt" ]; then
        REQUIREMENTS_FILE="$SCRIPT_DIR/DMAIC_V3/requirements.txt"
    elif [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"
    fi
    
    if [ -n "$REQUIREMENTS_FILE" ]; then
        print_info "  Installing from: $REQUIREMENTS_FILE"
        python -m pip install -r "$REQUIREMENTS_FILE"
        
        if [ $? -eq 0 ]; then
            print_success "  ✓ Dependencies installed"
        else
            print_error "  ✗ Failed to install dependencies"
            exit 1
        fi
    else
        print_warning "  ⚠ No requirements.txt found"
    fi
else
    print_info "[6/7] Skipping dependency installation (--skip-dependencies)"
fi

# Validate installation
print_info "[7/7] Validating installation..."

VALIDATION_PASSED=true

# Check core packages
for package in pip setuptools wheel; do
    if python -m pip show "$package" &> /dev/null; then
        print_success "  ✓ $package installed"
    else
        print_warning "  ⚠ $package not found"
        VALIDATION_PASSED=false
    fi
done

# Summary
echo ""
echo "================================================================================"
echo "SETUP SUMMARY"
echo "================================================================================"

if [ "$VALIDATION_PASSED" = true ]; then
    print_success "✅ Environment setup completed successfully!"
    echo ""
    print_info "Virtual environment: $VENV_PATH"
    print_info "Python: $(python --version)"
    print_info "Pip: $(python -m pip --version)"
    echo ""
    print_info "To activate the environment in a new session:"
    echo "  source $VENV_PATH/bin/activate"
    echo ""
    print_info "To deactivate:"
    echo "  deactivate"
else
    print_warning "⚠️  Setup completed with warnings"
fi

echo "================================================================================"
echo ""

# Run validation if requested
if [ "$VALIDATE" = true ]; then
    print_info "Running Phase 0 validation..."
    echo ""
    
    PHASE0_SCRIPT="$SCRIPT_DIR/DMAIC_V3/phases/phase0_setup.py"
    if [ -f "$PHASE0_SCRIPT" ]; then
        python "$PHASE0_SCRIPT"
    else
        print_warning "Phase 0 script not found: $PHASE0_SCRIPT"
    fi
fi

# Create activation helper script
HELPER_SCRIPT="$SCRIPT_DIR/activate_dmaic.sh"
cat > "$HELPER_SCRIPT" << 'EOF'
#!/bin/bash
# DMAIC V3.0 - Quick Activation Helper
# Run this script to activate the virtual environment

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_PATH="$SCRIPT_DIR/.venv"
ACTIVATE_SCRIPT="$VENV_PATH/bin/activate"

if [ -f "$ACTIVATE_SCRIPT" ]; then
    source "$ACTIVATE_SCRIPT"
    echo "✓ DMAIC V3.0 environment activated"
else
    echo "✗ Virtual environment not found. Run setup_environment.sh first."
    exit 1
fi
EOF

chmod +x "$HELPER_SCRIPT"
print_info "Created activation helper: activate_dmaic.sh"

print_success "Setup complete! 🚀"
