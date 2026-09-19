#!/usr/bin/env bash
# run_queue_59_vote.sh — D2629 follow-up: reliable-pair 3-axis vote on the 59 queue rows.
# Resumable (checkpoint upserts per fb_id); caffeinate keeps the Mac awake.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-$(grep -iE '^DEEPSEEK_API_KEY=' .env | cut -d= -f2- | tr -d '[:space:]')}"
if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  echo "FATAL: no DEEPSEEK_API_KEY in env or .env (C22 opt-in)" >&2
  exit 1
fi
exec caffeinate -disu python3 scripts/revote_queue_59.py \
  --run --workers "${QUEUE_59_WORKERS:-2}"
