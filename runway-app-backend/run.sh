#!/usr/bin/env bash
set -euo pipefail

# Transaction Analysis Pipeline Runner
# Pass any arguments to main.py, or run with defaults

if [ "$#" -eq 0 ]; then
    echo "Running transaction analysis pipeline with default settings..."
    echo "Use './run.sh --help' to see all options"
    echo ""
fi

python3 main.py "$@"
