#!/usr/bin/env bash
# run_joint_vote.sh — production joint content_type + depth vote launcher (D2612).
#
# Purpose: launch the FULL 7,966-row resumable joint vote safely.
#
#   caffeinate   → keep the Mac awake for the ~11h run (no display/idle/system sleep).
#   lazy-load    → --reliable-only calls ONLY Qwen3.8-27B (local) + DeepSeek; the
#                  advisory Qwen3-Coder-30B is skipped, so OMLX never loads it.
#   preflight    → DeepSeek probe + OMLX cache-gate (D2460) + Qwen3.8 live stress
#                  + target-population count, BEFORE any row is voted.
#   resumable    → checkpoint upserts one line per fb_id; re-running this same
#                  command skips done rows and resumes where it stopped (C23).
#   pausable     → SIGINT/SIGTERM propagates through caffeinate→python; flushed
#                  rows are durable, in-flight rows re-vote on resume.
#
# Usage:
#   scripts/run_joint_vote.sh                     # full production run
#   JOINT_VOTE_LIMIT=200 scripts/run_joint_vote.sh # small batch
#   JOINT_VOTE_WORKERS=2 scripts/run_joint_vote.sh # lower concurrency
#
# To run detached (recommended for ~11h):
#   nohup scripts/run_joint_vote.sh > governance/joint_vote_production.log 2>&1 & disown
#
# To resume after interruption: run the SAME command again. Idempotent.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# DeepSeek key from .env (never hardcode — C12/C22 opt-in). Env var overrides.
export DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-$(grep -iE '^DEEPSEEK_API_KEY=' .env | cut -d= -f2- | tr -d '[:space:]')}"

CHECKPOINT="governance/joint_vote_production_checkpoint.jsonl"
SEED=0
LIMIT="${JOINT_VOTE_LIMIT:-7966}"     # full principle-labelled population
WORKERS="${JOINT_VOTE_WORKERS:-3}"    # 3 concurrent FBs (network + single OMLX server)

if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
    echo "FATAL: no DEEPSEEK_API_KEY in env or .env (C22 opt-in)" >&2
    exit 1
fi

echo "[$(date -u +%FT%TZ)] launching joint vote: limit=$LIMIT workers=$WORKERS checkpoint=$CHECKPOINT"
echo "[$(date -u +%FT%TZ)] caffeinate -disu active (no sleep) | reliable-only (lazy-load advisory skipped)"

# -d prevent display sleep | -i prevent idle sleep | -s prevent system sleep | -u declare activity
exec caffeinate -disu python3 scripts/build_joint_vote_set.py \
    --run --preflight \
    --limit "$LIMIT" --seed "$SEED" \
    --reliable-only --workers "$WORKERS" \
    --checkpoint "$CHECKPOINT"
