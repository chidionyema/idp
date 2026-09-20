#!/usr/bin/env bash
# A state question answered by shell recon instead of the platform (ADR 0006).
cat docs/reports/flux-state.md
grep -rln agent-reader ~/.claude/projects/*/*.jsonl
sqlite3 catalog/estate.db 'select * from nodes limit 5'
