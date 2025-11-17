#!/bin/bash

# Script to troubleshoot pre-commit hooks

echo "Starting pre-commit hook troubleshooting..."

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "Error: pre-commit is not installed. Install it using 'pip install pre-commit'."
    exit 1
fi

# Check if .pre-commit-config.yaml exists
if [ ! -f ".pre-commit-config.yaml" ]; then
    echo "Error: .pre-commit-config.yaml file not found in the current directory."
    exit 1
fi

# Run pre-commit hooks manually
echo "Running pre-commit hooks..."
pre-commit run --all-files

# Check the exit status of pre-commit
if [ $? -eq 0 ]; then
    echo "Pre-commit hooks ran successfully."
else
    echo "Pre-commit hooks encountered issues. Check the output above for details."
fi

echo "Troubleshooting complete."
