#!/usr/bin/env bash

set -uo pipefail

usage() {
    echo "Usage: bash ci/run_repo_lint.sh [--strict|--report]"
}

mode="strict"
if [[ $# -gt 1 ]]; then
    usage
    exit 2
fi
if [[ $# -eq 1 ]]; then
    case "$1" in
        --strict)
            mode="strict"
            ;;
        --report)
            mode="report"
            ;;
        *)
            usage
            exit 2
            ;;
    esac
fi

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root_dir" || exit 1

if ! command -v black >/dev/null 2>&1; then
    echo "black is required but was not found on PATH."
    exit 2
fi
if ! command -v flake8 >/dev/null 2>&1; then
    echo "flake8 is required but was not found on PATH."
    exit 2
fi

black_exit=0
flake8_exit=0

echo "[lint] Running Black across the repository"
black --check --exclude '/(\.git|__pycache__|\.venv|ci/logs)/' . || black_exit=$?

echo "[lint] Running Flake8 across the repository"
flake8 . || flake8_exit=$?

echo
echo "[lint] Summary"
echo "  Black exit code:  $black_exit"
echo "  Flake8 exit code: $flake8_exit"

if [[ "$mode" == "strict" && ( $black_exit -ne 0 || $flake8_exit -ne 0 ) ]]; then
    exit 1
fi

if [[ $black_exit -ne 0 || $flake8_exit -ne 0 ]]; then
    echo "[lint] Repository-wide report found issues."
else
    echo "[lint] Repository-wide report is clean."
fi

exit 0