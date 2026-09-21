#!/bin/bash
# run_completeness_tier2.sh — D-2637 TIER-2 (OPT-IN). Deferred, not lost.
# LEVER 2 moved the reasoning battery here. Nothing in Tier-2 can change a gated
# decision (long-context, S4 production, Qwen3.8 quant, Ornith A/B); it completes the
# characterisation of models whose roles are already settled by other evidence.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || exit 1  # C12: self-locating, no hardcoded path
LOG=governance/model_eval_completeness.log
say() { echo "[tier2] $*  $(date '+%F %T')" | tee -a $LOG; }
while pgrep -f 'run_final_chain.sh' > /dev/null 2>&1; do sleep 60; done
say 'reasoning battery x4 role-holders (mmlu_pro gsm8k math500 hotpot_qa)'
python3 tools/model_eval_suite.py \
    --models Qwen3.8-27B-MLX-4bit Qwen3.8-27B-OptiQ-4bit Ornith-1.5-35B-A3B-REAP-19B Qwen3-Coder-30B-A3B-Instruct-MLX-4bit \
    --suites mmlu_pro gsm8k math500 hotpot_qa >> $LOG 2>&1
say 'abstain for the remaining models'
python3 tools/model_eval_suite.py \
    --models Qwen3-Coder-30B-A3B-Instruct-MLX-4bit Ornith-1.5-35B-A3B-REAP-19B Ornith-1.5-9B-OptiQ-4bit \
    --suites abstain >> $LOG 2>&1
say 'reasoning + abstain for the settled-role models'
python3 tools/model_eval_suite.py \
    --models gpt-oss-20b-MXFP4-Q8 gemma-4-E4B-it-MLX-4bit Phi-4-mini-instruct-8bit Ornith-1.5-9B-OptiQ-4bit \
    --suites mmlu_pro gsm8k math500 hotpot_qa >> $LOG 2>&1
python3 tools/model_eval_report.py --md governance/model_eval_report.md >> $LOG 2>&1
say 'TIER-2 ALL DONE'