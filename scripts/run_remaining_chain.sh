#!/bin/bash
# run_remaining_chain.sh — D-2637 remaining benchmark chain (single resident model -> serial).
# 1) wait for the Ornith 4bit/8bit A/B   2) gap-fill the 43+2 errored rows
# 3) Run B long-context shortlist        4) production-path S4 vs gold
set -u
cd '/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0' || exit 1

echo "[chain] start $(date '+%F %T')"
while pgrep -f 'eval_models_ornith_ab' > /dev/null 2>&1; do sleep 60; done
echo "[chain] ornith A/B finished $(date '+%F %T')"

echo "[chain] step 2 — gap-fill errored rows"
python3 tools/model_eval_suite.py --models Ornith-1.5-35B-A3B-REAP-19B \
    --suites stability toolcalling planning reviewing >> governance/model_eval_gapfill.log 2>&1
python3 tools/model_eval_suite.py --models gemma-4-12B-it-qat-OptiQ-4bit gpt-oss-20b-MXFP4-Q8 \
    --suites reviewing >> governance/model_eval_gapfill.log 2>&1
echo "[chain] step 2 done"

echo "[chain] step 3 — Run B long-context"
python3 tools/model_eval_suite.py --models-file governance/eval_models_longctx.txt \
    --suites niah lc_reasoning > governance/model_eval_runB.log 2>&1
echo "[chain] step 3 done"

echo "[chain] step 4 — production-path S4 vs gold (100 rows x 2 models)"
python3 scripts/pipe_s4_classify_gold.py \
    --models gpt-oss-20b-MXFP4-Q8 Qwen3.8-27B-MLX-4bit \
    --limit 100 > governance/pipe_s4_classify.log 2>&1
echo "[chain] step 4 done"

python3 tools/model_eval_report.py --md governance/model_eval_report.md >> governance/model_eval_report.log 2>&1
echo "[chain] ALL DONE $(date '+%F %T')"