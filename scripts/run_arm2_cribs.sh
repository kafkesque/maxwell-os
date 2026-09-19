#!/usr/bin/env bash
# ARM-2 CRIBS (D2618) — gpt-oss-20b-MXFP4-Q8 vs Qwen3-Coder-30B-A3B-Instruct-MLX-4bit
# on the FROZEN S2 convergent-extraction benchmark (governance/s2_qwen38_vs_coder_benchmark.json).
#
# Goal: "retain gpt-oss until replacement WINS" — decide whether gpt-oss (current S4
# classifier) is competitive with Qwen3-Coder (current S2 generator) as a GENERATOR,
# informing the gpt-oss retirement gate.
#
# Metric: route agreement (FB/NULL vs Qwen3-Coder baseline), schema validity, FB rate,
# wall-clock speed. Frozen 6 canary clusters (cluster_66/109/113/185/306/321) — verified
# deterministic: probe_targets.jsonl unchanged since 2026-08-13, first 6 convergent
# clusters == the frozen set.
#
# SEQUENCING (IMPORTANT): do NOT run while the 190-row vote is using Qwen3.8-27B on OMLX.
# gpt-oss + Qwen3-Coder evict Qwen3.8 from OMLX memory (~55GB ceiling, BUG-224 wedge risk),
# stalling the reliable-pair vote. Queue behind the vote, or explicitly pause the vote first.
set -euo pipefail
cd "$(dirname "$0")/.."
exec caffeinate -disu python3 tools/benchmark_s2_qwen38_vs_coder.py \
  --n 6 \
  --models Qwen3-Coder-30B-A3B-Instruct-MLX-4bit gpt-oss-20b-MXFP4-Q8 \
  --out governance/arm2_cribs_benchmark.json
