#!/usr/bin/env bash
# canary_rerun.sh — T1.1 canary re-run (S2 → S4 → S5 → S6), run_id=canary
# Chained, stop-on-first-failure, fully logged. Launched via nohup so it
# survives the controlling terminal.
set -uo pipefail

cd "$(dirname "$0")/.."

TS="$(date +%Y%m%d_%H%M%S)"
LOG="knowledge pipeline/canary_rerun_${TS}.log"
export MAXWELL_RUN_ID=canary

{
echo "=== T1.1 canary re-run started $(date) ==="
echo "HEAD=$(git rev-parse --short HEAD)"
echo "caffeinate: $(pgrep -f 'caffeinate -disu' >/dev/null && echo ACTIVE || echo MISSING)"
echo ""

run_stage() {
  local name="$1"; shift
  echo "=== [$name] START $(date) ==="
  "$@"
  local rc=$?
  echo "=== [$name] END rc=$rc $(date) ==="
  if [ $rc -ne 0 ]; then
    echo "⛔ [$name] FAILED — canary halted."
    exit $rc
  fi
}

run_stage "S2_extract" python3 pipeline/stage2_extract.py --only-convergent
run_stage "S4_merge"   python3 pipeline/stage4_merge.py
run_stage "S5_verify"  python3 pipeline/stage5_verify.py
run_stage "S6_commit"  python3 pipeline/stage6_commit.py

echo ""
echo "=== CANARY COMPLETE $(date) ==="
} >>"$LOG" 2>&1

echo "CANARY DONE rc=$? — log: $LOG" >>"$LOG"
