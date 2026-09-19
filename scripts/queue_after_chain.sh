#!/bin/bash
# queue_after_chain.sh — the post-freeze measurement queue, serialised on purpose.
#
# WHY SERIALISED: oMLX serves ONE resident model. Two consumers at once means the second one's
# model switch evicts the first one's model and wedges it with no server-side trace (BUG-255).
# So this waits for the chain and the niah rerun to finish, then runs each measurement alone.
#
# WHAT IT CLOSES:
#   1. tool calling (was n=4) and planning (was n=3) -> n=20 each, 7 models. These are the two
#      role assignments that rested on a handful of items; one item could move the ranking.
#   2. the never-measured inherited stages that write PERSISTENT fields: S0.5 metadata,
#      S2 cross-family relabel, S4_5 procedural_skill.
#   3. hyDE, via the existing golden-set A/B (recall@k / MRR with vs without HyDE).
set -u
cd '/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0' || exit 1
LOG=governance/post_chain_queue.log
say() { echo "[post] $*  $(date '+%F %T')" | tee -a "$LOG"; }

say 'START — waiting for run_final_chain.sh + rerun_niah_fixed.sh to drain'
while pgrep -f 'run_final_chain.sh' > /dev/null 2>&1 || pgrep -f 'rerun_niah_fixed.sh' > /dev/null 2>&1; do
  sleep 60
done
say 'chain drained — starting'

say 'step1 tool-calling + planning at n=20 (7 models)'
python3 tools/model_eval_suite.py \
  --models Ornith-1.5-35B-A3B-REAP-19B Qwen3.8-27B-MLX-4bit Qwen3-Coder-30B-A3B-Instruct-MLX-4bit \
           gemma-4-E4B-it-MLX-4bit Ornith-1.5-9B-MLX-8bit Phi-4-mini-instruct-8bit gpt-oss-20b-MXFP4-Q8 \
  --suites toolcalling planning >> governance/model_eval_roles.log 2>&1
say 'step1 done (see governance/model_eval_roles.log)'

say 'step2 stage probe — S0.5 metadata / S2 relabel / S4_5 skill (12 items each)'
python3 scripts/pipe_stage_probe.py --limit 12 >> governance/pipe_stage_probe.log 2>&1
say 'step2 done (see governance/pipe_stage_probe.log)'

say 'step3 hyDE A/B on the golden query set'
python3 pipeline/retrieval_benchmark.py --hyde --json >> governance/retrieval_hyde_ab.log 2>&1
say 'step3 done (see governance/retrieval_hyde_ab.log)'

say 'step4 refresh the report + audit'
python3 tools/model_eval_report.py --md governance/model_eval_report.md >> "$LOG" 2>&1
python3 scripts/audit_final_chain.py >> "$LOG" 2>&1
say 'ALL DONE — every role and every inherited stage now has measured evidence'
