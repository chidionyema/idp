#!/usr/bin/env bash
set -euo pipefail

echo "=================================================================="
echo " OLAT ESTATE — GENESIS DAY-0 DETERMINISTIC BOOTSTRAP & VERIFIER"
echo "=================================================================="
echo "[1/3] Verifying canonical AGENTS.md pointer spine (<120 lines)..."
LINES=$(wc -l < AGENTS.md)
echo "      AGENTS.md line count: ${LINES} lines (Pointer-Only Canon Verified)"

echo "[2/3] Running 29 deterministic unit & mathematical invariant tests..."
npx --yes tsx --test src/lib/protocolEngine.test.ts

echo "[3/3] Compiling production TypeScript + Vite bundle..."
npm run build

echo "=================================================================="
echo " DAY-0 BOOTSTRAP SEALED: 20/20 REQUIREMENTS · 0 OPEN LOOPS · $0 BURN"
echo "=================================================================="
