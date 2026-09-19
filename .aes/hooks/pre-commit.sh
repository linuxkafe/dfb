#!/bin/sh
# AES pre-commit hook — runs quick quality gates

set -e

echo "🔍 AES pre-commit: running quick checks..."

# Run ruff lint (fast)
if command -v ruff >/dev/null 2>&1; then
    ruff check src tests 2>/dev/null || { echo "❌ ruff lint failed"; exit 1; }
fi

# Run pytest (fast subset)
if command -v pytest >/dev/null 2>&1; then
    pytest -x -q --tb=short 2>/dev/null || { echo "❌ tests failed"; exit 1; }
fi

echo "✅ AES pre-commit passed"
exit 0