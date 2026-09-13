#!/usr/bin/env bash
# run_discipline_domain_vote.sh — D2618 P1: reliable-pair discipline+domain vote (216 core).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-$(grep -iE '^DEEPSEEK_API_KEY=' .env | cut -d= -f2- | tr -d '[:space:]')}"
if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  echo "FATAL: no DEEPSEEK_API_KEY in env or .env (C22 opt-in)" >&2
  exit 1
fi
exec caffeinate -disu python3 scripts/build_discipline_domain_vote.py \
  --run --workers "${DISC_DOM_WORKERS:-1}"
