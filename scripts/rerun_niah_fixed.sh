#!/bin/bash
# rerun_niah_fixed.sh — BUG-257 remediation.
# Run B built its item list at process start, so it kept using the BROKEN (4000,16000,32000)
# niah tiers and will keep hitting HTTP 400 on the top tier for every remaining model.
# The fix (4000,12000,24000) only takes effect on a fresh invocation. This re-runs the
# long-context suites for the 5 keepers with corrected tiers; the 32k rows persist in the
# checkpoint as transport errors and are retried automatically (_done_keys skips errors).
set -u
cd '/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0' || exit 1
LOG=governance/model_eval_runB.log
echo "[niah-fix] start $(date '+%F %T')" | tee -a $LOG
while pgrep -f 'run_final_chain.sh' > /dev/null 2>&1; do sleep 60; done
python3 tools/model_eval_suite.py --models-file governance/eval_models_longctx.txt \
    --suites niah lc_reasoning >> $LOG 2>&1
echo "[niah-fix] done $(date '+%F %T')" | tee -a $LOG