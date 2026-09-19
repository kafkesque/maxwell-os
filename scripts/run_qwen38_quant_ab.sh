#!/bin/bash
# run_qwen38_quant_ab.sh — D-2637 follow-up: is OptiQ mixed-precision better than the
# uniform 4-bit currently installed?  Waits for the current benchmark chain AND the
# download, registers the model via /admin/api/reload (no GUI restart), then runs the
# decisive suites on BOTH variants so the comparison uses identical gold rows.
set -u
cd '/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0' || exit 1

echo "[ab] start $(date '+%F %T')"
while pgrep -f 'run_remaining_chain.sh' > /dev/null 2>&1; do sleep 60; done
echo "[ab] run chain finished"
while pgrep -f '_dl_optiq' > /dev/null 2>&1; do sleep 60; done
echo "[ab] download finished $(date '+%F %T')"

SRC="$HOME/.cache/huggingface/hub/models--mlx-community--Qwen3.8-27B-OptiQ-4bit/snapshots"
SNAP=$(ls -d "$SRC"/*/ 2>/dev/null | head -1)
if [ -z "$SNAP" ]; then echo "[ab] FATAL: no snapshot found under $SRC"; exit 1; fi
ln -sfn "${SNAP%/}" "$HOME/.omlx/models/Qwen3.8-27B-OptiQ-4bit"
echo "[ab] symlinked $(basename "${SNAP%/}")"
python3 scripts/omlx_reload.py || { echo '[ab] FATAL: reload failed'; exit 1; }

echo '[ab] decisive suites on BOTH variants'
printf '%s\n' 'Qwen3.8-27B-MLX-4bit' 'Qwen3.8-27B-OptiQ-4bit' > governance/eval_models_qwen38_quant.txt
python3 tools/model_eval_suite.py --models-file governance/eval_models_qwen38_quant.txt \
    --suites voting humaneval mbpp hardcode delegation ifeval planning toolcalling \
    > governance/model_eval_qwen38_ab.log 2>&1
echo '[ab] quant A/B done'

python3 scripts/pipe_s4_classify_gold.py --models Qwen3.8-27B-OptiQ-4bit \
    --limit 100 > governance/pipe_s4_classify_optiq.log 2>&1
python3 tools/model_eval_report.py --md governance/model_eval_report.md \
    >> governance/model_eval_qwen38_ab.log 2>&1
echo "[ab] ALL DONE $(date '+%F %T')"