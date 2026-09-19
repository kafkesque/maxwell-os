#!/bin/bash
# run_final_chain.sh — D-2637 single linear runner.
# Replaces the five pgrep-handoff watcher scripts: one process, one order, no handoff
# race (a downstream job starting while the Ornith A/B still held the single resident
# model would be BUG-255 again). Two levers applied:
#   LEVER 1: production S4 sampled at 60 rows instead of 100 (+/-65 min)
#   LEVER 2: Tier-1 completeness carries NO reasoning battery (+/-2.7 h); the battery
#            moves to run_completeness_tier2.sh so the data is deferred, not lost.
set -u
cd '/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0' || exit 1
LOG=governance/run_final_chain.log
S4LOG=governance/pipe_s4_classify.log
say() { echo "[final] $*  $(date '+%F %T')" | tee -a $LOG; }

say 'START — waiting for the Ornith 4bit/8bit A/B'
while pgrep -f 'eval_models_ornith_ab' > /dev/null 2>&1; do sleep 60; done
say 'step1 gap-fill 45 errored rows -> REAP + gpt-oss (gemma-4-12B dropped: deleted)'
python3 tools/model_eval_suite.py --models Ornith-1.5-35B-A3B-REAP-19B \
    --suites stability toolcalling planning reviewing >> governance/model_eval_gapfill.log 2>&1
python3 tools/model_eval_suite.py --models gpt-oss-20b-MXFP4-Q8 \
    --suites reviewing >> governance/model_eval_gapfill.log 2>&1
say 'step1 done'

say 'step2 Run B — long-context (niah + lc_reasoning) on the 5 keepers'
python3 tools/model_eval_suite.py --models-file governance/eval_models_longctx.txt \
    --suites niah lc_reasoning > governance/model_eval_runB.log 2>&1
say 'step2 done'

say 'step3 production-path S4 vs gold (LEVER 1: 60 rows)'
python3 scripts/pipe_s4_classify_gold.py \
    --models gpt-oss-20b-MXFP4-Q8 Qwen3.8-27B-MLX-4bit --limit 60 > $S4LOG 2>&1
python3 scripts/pipe_s4_classify_gold.py \
    --models gemma-4-E4B-it-MLX-4bit --limit 60 >> $S4LOG 2>&1
say 'step3 done'

say 'step4 register OptiQ (symlink + reload — safe: nothing else running)'
SNAP=$(ls -d "$HOME"/.cache/huggingface/hub/models--mlx-community--Qwen3.8-27B-OptiQ-4bit/snapshots/*/ 2>/dev/null | head -1)
if [ -z "$SNAP" ]; then say 'FATAL: OptiQ snapshot missing'; exit 1; fi
ln -sfn "${SNAP%/}" "$HOME/.omlx/models/Qwen3.8-27B-OptiQ-4bit"
python3 scripts/omlx_reload.py >> $LOG 2>&1
say 'step4 done'

say 'step5 Qwen3.8 uniform-4bit vs OptiQ — the quant decision'
python3 tools/model_eval_suite.py --models-file governance/eval_models_qwen38_quant.txt \
    --suites voting humaneval mbpp hardcode delegation ifeval planning toolcalling \
    > governance/model_eval_qwen38_ab.log 2>&1
say 'step5 done'

say 'step6 production S4 for OptiQ (60 rows)'
python3 scripts/pipe_s4_classify_gold.py --models Qwen3.8-27B-OptiQ-4bit \
    --limit 60 > governance/pipe_s4_classify_optiq.log 2>&1
say 'step6 done'

say 'step7 vision probe on 3 installed models (zero download)'
python3 -u scripts/vision_probe.py > governance/vision_probe.log 2>&1
say 'step7 done'

say 'step8 Tier-1 completeness: abstain (fail-closed) + OptiQ long-context'
python3 tools/model_eval_suite.py \
    --models gpt-oss-20b-MXFP4-Q8 gemma-4-E4B-it-MLX-4bit Qwen3.8-27B-MLX-4bit Phi-4-mini-instruct-8bit \
    --suites abstain >> governance/model_eval_completeness.log 2>&1
python3 tools/model_eval_suite.py --models Qwen3.8-27B-OptiQ-4bit \
    --suites abstain niah lc_reasoning >> governance/model_eval_completeness.log 2>&1
say 'step8 done'

python3 tools/model_eval_report.py --md governance/model_eval_report.md >> $LOG 2>&1
say 'ALL DONE — consolidation-ready'