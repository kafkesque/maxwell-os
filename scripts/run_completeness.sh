#!/bin/bash
# run_completeness.sh — D-2637 TIER-1 completeness: the holes that can change a decision.
# Tier-2 (all remaining combos for roles that are already settled) lives in
# scripts/run_completeness_tier2.sh and is opt-in.
# Ordered by decision-relevance; the harness skips measured rows, so partial == resumable.
# Runs LAST in the serial chain (single resident model — BUG-255).
set -u
cd '/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0' || exit 1
LOG=governance/model_eval_completeness.log
echo "[complete] TIER-1 start $(date '+%F %T')" | tee -a $LOG

while pgrep -f 'run_s4_gemma.sh' > /dev/null 2>&1 || pgrep -f 'run_vision_probe.sh' > /dev/null 2>&1 \
   || pgrep -f 'run_qwen38_quant_ab.sh' > /dev/null 2>&1 || pgrep -f 'run_remaining_chain.sh' > /dev/null 2>&1 \
   || pgrep -f 'eval_models_ornith_ab' > /dev/null 2>&1; do sleep 60; done
echo "[complete] queue clear $(date '+%F %T')" | tee -a $LOG
python3 scripts/omlx_reload.py 2>&1 | tee -a $LOG

echo '[complete] step0 smoke: abstain x3 on the cheapest model' | tee -a $LOG
python3 tools/model_eval_suite.py --models Phi-4-mini-instruct-8bit --suites abstain --limit 3 >> $LOG 2>&1

echo '[complete] step1 abstain (fail-closed) x4 decision-critical models' | tee -a $LOG
python3 tools/model_eval_suite.py \
    --models gpt-oss-20b-MXFP4-Q8 gemma-4-E4B-it-MLX-4bit Qwen3.8-27B-MLX-4bit Phi-4-mini-instruct-8bit \
    --suites abstain >> $LOG 2>&1
echo "[complete] step1 done $(date '+%F %T')" | tee -a $LOG

echo '[complete] step2 reasoning battery x4 role-holders' | tee -a $LOG
python3 tools/model_eval_suite.py \
    --models Qwen3.8-27B-MLX-4bit Qwen3.8-27B-OptiQ-4bit Ornith-1.5-35B-A3B-REAP-19B Qwen3-Coder-30B-A3B-Instruct-MLX-4bit \
    --suites mmlu_pro gsm8k math500 hotpot_qa >> $LOG 2>&1
echo "[complete] step2 done $(date '+%F %T')" | tee -a $LOG

echo '[complete] step3 long-context for OptiQ (Run B covers the other five)' | tee -a $LOG
python3 tools/model_eval_suite.py --models Qwen3.8-27B-OptiQ-4bit --suites niah lc_reasoning >> $LOG 2>&1
echo '[complete] step4 abstain for OptiQ (may inherit the decider role)' | tee -a $LOG
python3 tools/model_eval_suite.py --models Qwen3.8-27B-OptiQ-4bit --suites abstain >> $LOG 2>&1
echo "[complete] step3+4 done $(date '+%F %T')" | tee -a $LOG

python3 tools/model_eval_report.py --md governance/model_eval_report.md >> $LOG 2>&1
echo "[complete] TIER-1 ALL DONE $(date '+%F %T')" | tee -a $LOG