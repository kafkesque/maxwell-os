#!/bin/bash
# run_remaining_axes_vote.sh — launch the 190-row reliable-pair vote (detached).
set -euo pipefail
cd "$(dirname "$0")/.."
export DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-$(grep -iE '^DEEPSEEK_API_KEY=' .env 2>/dev/null | cut -d= -f2- | tr -d '[:space:]')}"
exec caffeinate -disu python3 scripts/vote_remaining_axes.py --run --workers "${REMAINING_AXES_WORKERS:-2}" 2>&1
