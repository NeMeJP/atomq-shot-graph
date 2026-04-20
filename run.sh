#!/usr/bin/env bash
# One-click runner for atomq-shot-graph.
#
# Usage:
#   ./run.sh            — install + test + demo (default)
#   ./run.sh demo       — just run the demo
#   ./run.sh viz        — regenerate docs/images/*.png
#   ./run.sh test       — run the pytest suite
#   ./run.sh clean      — remove .venv and caches
#
# Works on Linux and macOS. Requires python3.10+ on PATH.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

PY="${PYTHON:-python3}"
if command -v python3.12 >/dev/null 2>&1; then PY=python3.12
elif command -v python3.11 >/dev/null 2>&1; then PY=python3.11
elif command -v python3.10 >/dev/null 2>&1; then PY=python3.10
fi

PY_VER=$("$PY" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_OK=$("$PY" -c 'import sys; print(1 if sys.version_info >= (3,10) else 0)')
if [[ "$PY_OK" != "1" ]]; then
    echo "[ERR] Python 3.10+ required (found $PY_VER)" >&2
    echo "      Ubuntu/Debian: sudo apt install python3.10 python3.10-venv" >&2
    echo "      Fedora:        sudo dnf install python3.11" >&2
    echo "      macOS:         brew install python@3.11" >&2
    exit 1
fi

install_deps() {
    if [[ ! -d .venv ]]; then
        echo ">>> creating venv with $PY ($PY_VER)"
        "$PY" -m venv .venv
    fi
    echo ">>> installing dependencies (quiet)"
    .venv/bin/pip install --quiet --upgrade pip
    .venv/bin/pip install --quiet -e '.[dev,export,viz]'
    # types-networkx keeps mypy --strict happy
    .venv/bin/pip install --quiet types-networkx 2>/dev/null || true
}

run_tests() {
    echo ">>> running test suite"
    .venv/bin/python -m pytest -q
}

run_demo() {
    echo ">>> running examples/01_dual_isotope_feedback.py"
    echo "--------------------------------------------------"
    .venv/bin/python examples/01_dual_isotope_feedback.py
    echo "--------------------------------------------------"
}

run_viz() {
    echo ">>> regenerating docs/images/"
    .venv/bin/python examples/_viz_shot_graph.py
    .venv/bin/python examples/_viz_latency.py
    echo ">>> output:"
    ls -la docs/images/
    # Offer to open
    if command -v xdg-open >/dev/null 2>&1; then
        echo ">>> opening with xdg-open (Linux)"
        xdg-open docs/images/shot_graph.png 2>/dev/null &
    elif command -v open >/dev/null 2>&1; then
        echo ">>> opening with open (macOS)"
        open docs/images/*.png
    else
        echo ">>> PNGs are at docs/images/ — open them with any viewer"
    fi
}

clean() {
    echo ">>> removing .venv and caches"
    rm -rf .venv .pytest_cache .mypy_cache .ruff_cache
    find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
    echo ">>> done"
}

case "${1:-all}" in
    demo)  install_deps; run_demo ;;
    test)  install_deps; run_tests ;;
    viz)   install_deps; run_viz ;;
    clean) clean ;;
    all)   install_deps; run_tests; run_demo; run_viz ;;
    *)     echo "Usage: $0 [demo|test|viz|clean|all]" >&2; exit 1 ;;
esac
