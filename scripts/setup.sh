#!/usr/bin/env bash
#
# Persona Graph — one-shot environment setup.
#
# Dual stack: Python venv (scraping/analysis/scoring) + npm (Next.js dashboard).
# Same macOS chflags workaround as the sibling repos.
set -euo pipefail

cd "$(dirname "$0")/.."
REPO="$(pwd)"
echo "→ repo: $REPO"

# --- 1. Python 3.11+ ---------------------------------------------------------

PY=""
for v in python3.13 python3.12 python3.11; do
  if command -v "$v" >/dev/null 2>&1; then PY="$v"; break; fi
done
if [ -z "$PY" ]; then
  echo "✗ need Python 3.11+ (not found: python3.11 / python3.12 / python3.13)"
  exit 1
fi
echo "→ python: $($PY --version) ($(command -v $PY))"

# --- 2. Node 18+ -------------------------------------------------------------

if ! command -v node >/dev/null 2>&1; then
  echo "✗ need Node 18+ for Next.js. Install from https://nodejs.org"
  exit 1
fi
NODE_VER="$(node -v | sed 's/v//' | cut -d. -f1)"
if [ "$NODE_VER" -lt 18 ]; then
  echo "✗ Node $NODE_VER is too old; need 18+"
  exit 1
fi
echo "→ node: $(node -v)"

# --- 3. Python venv + install -----------------------------------------------

if [ ! -d .venv ]; then
  echo "→ creating .venv"
  "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --quiet --upgrade pip
echo "→ installing persona-graph in editable mode + dev deps"
pip install --quiet -e ".[dev]"

# --- 4. macOS hidden-flag workaround -----------------------------------------

if [ "$(uname)" = "Darwin" ]; then
  echo "→ clearing macOS hidden flag from .venv (Python .pth load workaround)"
  chflags -R nohidden .venv
fi

# --- 5. npm install ---------------------------------------------------------

echo "→ installing npm dependencies (Next.js + d3-force + better-sqlite3)"
npm install --silent --no-audit --no-fund

# --- 6. .env scaffold --------------------------------------------------------

if [ ! -f .env ]; then
  cp .env.example .env
  echo "→ created .env from .env.example"
fi

# --- 7. Initialize SQLite DB if missing -------------------------------------

if [ ! -f data/intel.db ]; then
  echo "→ initializing SQLite schema at data/intel.db"
  mkdir -p data
  sqlite3 data/intel.db < scripts/init_db.sql
  echo "→ run: python scripts/generate_seed.py   # populate with synthetic content"
fi

# --- 8. Smoke test (if any tests exist) -------------------------------------

if compgen -G "tests/test_*.py" >/dev/null; then
  echo "→ python smoke test"
  if ! pytest -q --tb=short; then
    echo "✗ smoke test failed."
    exit 1
  fi
fi

echo
echo "✓ persona-graph ready."
echo "  python: source .venv/bin/activate && python scripts/generate_seed.py"
echo "  next:   npm run dev   # then open http://localhost:3000"
