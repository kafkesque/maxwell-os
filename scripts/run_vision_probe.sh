#!/bin/bash
# run_vision_probe.sh — D-2637: settle the vision/OCR gap on INSTALLED models before
# downloading any 9B VLM. Waits for the benchmark queue (single resident model, BUG-255),
# then probes Qwen3.8-27B / REAP-19B / gemma-4-E4B with a synthesised image.
set -u
cd '/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0' || exit 1
echo "[vision] start $(date '+%F %T')"
while pgrep -f 'run_qwen38_quant_ab.sh' > /dev/null 2>&1; do sleep 60; done
echo "[vision] queue clear $(date '+%F %T')"
python3 -u scripts/vision_probe.py > governance/vision_probe.log 2>&1
echo "[vision] done $(date '+%F %T')"
tail -20 governance/vision_probe.log