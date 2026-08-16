#!/usr/bin/env bash
# canary_rerun_s2onward.sh — full canary S2→S6 with new prompt + golden (D2377/D2378/D2379).
# Gates: caffeinate + preflight (golden hash, memory, OMLX) before extraction.
# OMLX lazy-loads models via --memory-guard-gb 55 (one model resident at a time).
set -uo pipefail

cd "/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0"

TS="$(date +%Y%m%d_%H%M%S)"
LOG="knowledge pipeline/canary_rerun_${TS}.log"
export MAXWELL_RUN_ID=canary

{
echo "=== T1.1 canary S2→S6 started $(date) ==="
echo "HEAD=$(git rev-parse --short HEAD)"
echo ""

# ── caffeinate (prevent sleep during multi-hour run) ─────────────────
if pgrep -f 'caffeinate -dis' >/dev/null; then
  echo "caffeinate: ACTIVE"
else
  nohup caffeinate -dis >/dev/null 2>&1 &
  CAFF_PID=$!
  echo "caffeinate: started (pid $CAFF_PID)"
fi

# ── preflight gates (fail-closed before extraction) ─────────────────
echo ""
echo "=== preflight ==="
python3 tools/verify_golden_hash.py || { echo "⛔ golden hash mismatch"; exit 1; }
PYTHONPATH=. python3 pipeline/memory_guard.py --min-gb 6 || { echo "⛔ low memory"; exit 1; }
python3 -c "from pipeline.omlx_call import check_omlx_health; ok = check_omlx_health(); print('OMLX UP' if ok else 'OMLX DOWN'); exit(0 if ok else 1)" || { echo "⛔ OMLX down"; exit 1; }
echo "preflight: PASS"
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

# ── S2 (convergent-only, new prompt + stratified few-shot) ───────────
run_stage "S2_extract" python3 pipeline/stage2_extract.py --only-convergent
run_stage "S4_merge"   python3 pipeline/stage4_merge.py
run_stage "S5_verify"  python3 pipeline/stage5_verify.py
run_stage "S6_commit"  python3 pipeline/stage6_commit.py

echo ""
echo "=== CANARY COMPLETE $(date) ==="
} >>"$LOG" 2>&1

echo "canary log: $LOG"
