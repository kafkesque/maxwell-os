#!/bin/bash
# run_s4_gemma.sh — D-2637: the R5-clean S4 classifier alternatives.
# Qwen3.8 wins on accuracy but is Qwen family (R5-illegal as S4 classifier while S2 is
# Qwen3-Coder). The only R5-clean candidates are gpt-oss-20b (incumbent) and gemma-4-E4B —
# and in the 251-row voting suite gemma-4-E4B BEAT gpt-oss on both discipline (0.422 vs
# 0.339) and domain F1 (0.357 vs 0.261). So the production-path table must include it.
# Serialised behind chains 2 and 3 (single resident model — BUG-255).
set -u
cd '/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0' || exit 1
echo "[s4gemma] start $(date '+%F %T')"
while pgrep -f 'run_qwen38_quant_ab.sh' > /dev/null 2>&1 || pgrep -f 'run_vision_probe.sh' > /dev/null 2>&1; do sleep 60; done
echo "[s4gemma] queue clear $(date '+%F %T')"
python3 scripts/pipe_s4_classify_gold.py --models gemma-4-E4B-it-MLX-4bit \
    --limit 100 > governance/pipe_s4_classify_gemma.log 2>&1
echo "[s4gemma] done $(date '+%F %T')"
python3 scripts/pipe_s4_classify_gold.py --models gpt-oss-20b-MXFP4-Q8 Qwen3.8-27B-MLX-4bit gemma-4-E4B-it-MLX-4bit --limit 100 >> governance/pipe_s4_classify_gemma.log 2>&1