#!/bin/bash
# reclaim_optiq.sh — delete the retired Qwen3.8-27B-OptiQ-4bit weights (Prune #5).
#
# WHY THIS IS A SCRIPT AND NOT A COMMAND: the model was still resident in oMLX when it was
# retired, and deleting a loaded model's weights mid-run risks taking the server down in the
# middle of the completeness sweep. This waits until nothing is running, then reclaims.
#
# Deleting a file that is mapped into memory does not crash macOS: the inode survives until it
# is unmapped, so the space appears once oMLX releases it. The symlink is removed first so the
# registry cannot load it again before oMLX re-scans.
set -u
cd '/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0' || exit 1
LOG=governance/reclaim_optiq.log
say() { echo "[reclaim] $*  $(date '+%F %T')" | tee -a "$LOG"; }

say 'START — waiting for chain + niah rerun + post-chain queue to drain'
while pgrep -f 'run_final_chain.sh' > /dev/null 2>&1 \
   || pgrep -f 'rerun_niah_fixed.sh' > /dev/null 2>&1 \
   || pgrep -f 'queue_after_chain.sh' > /dev/null 2>&1 \
   || pgrep -f 'model_eval_suite.py' > /dev/null 2>&1 \
   || pgrep -f 'pipe_s4_classify_gold.py' > /dev/null 2>&1 \
   || pgrep -f 'pipe_stage_probe.py' > /dev/null 2>&1 \
   || pgrep -f 'retrieval_benchmark.py' > /dev/null 2>&1; do
  sleep 60
done

MODEL_DIR="$HOME/.omlx/models/Qwen3.8-27B-OptiQ-4bit"
HF_DIR="$HOME/.cache/huggingface/hub/models--mlx-community--Qwen3.8-27B-OptiQ-4bit"

say 'nothing running — reclaiming'
df -h "$HOME" | tail -1 | tee -a "$LOG"

if [ -L "$MODEL_DIR" ]; then
  rm -f "$MODEL_DIR" && say "removed symlink $MODEL_DIR"
else
  say "no symlink at $MODEL_DIR (already gone)"
fi

if [ -d "$HF_DIR" ]; then
  SIZE=$(du -sh "$HF_DIR" 2>/dev/null | awk '{print $1}')
  say "deleting $HF_DIR ($SIZE) — DIRECT rm -rf, NO backup: R-D410 protects pipeline OUTPUT, and
      model weights are not output. safe_delete.py copies before deleting, which needs ~2x the
      target free: on 2026-09-17 that drove this volume to 1.7 GB free and had to be killed
      mid-copy (BUG-261). Deleting weights must not need space."
  rm -rf "$HF_DIR"
else
  say "no HF cache dir at $HF_DIR (already gone)"
fi

say 'df after:'
df -h "$HOME" | tail -1 | tee -a "$LOG"
say 'NOTE: the oMLX registry is start-cached (BUG-254). If OptiQ still appears in /v1/models,'
say 'run: python3 scripts/omlx_reload.py   (safe now — nothing else is running)'
say 'DONE'
