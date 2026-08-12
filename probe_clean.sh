#!/usr/bin/env bash
# probe_clean.sh — Clean S2→S4→S5 probe with proper background execution,
# per-stage checkpoints, and visual markdown summaries.
#
# Solves prior failures:
#   1. nohup + PID tracking → no orphaned processes
#   2. split_probe disabled → no k-means timing blowup
#   3. per-stage JSONL + .md visual summaries
#   4. lazy model loading (unload after each stage)
set -euo pipefail

cd "/Users/barn/Library/CloudStorage/Dropbox/claude projects/maxwell os 2.0"
OUT="probe_output"
S15="knowledge pipeline/stage1_5_embed_cluster/latest/checkpoint.jsonl"
S15_BAK="${S15}.bak"
S2_DIR="knowledge pipeline/stage2_extract/latest"
S2_CKPT="$S2_DIR/checkpoint.jsonl"
S2_CACHE="$S2_DIR/probe_targets.jsonl"
S4_CKPT="knowledge pipeline/stage4_merge/latest/checkpoint.jsonl"
S5_CKPT="knowledge pipeline/stage5_verify/latest/checkpoint.jsonl"

mkdir -p "$OUT"

echo "════════════════════════════════════════════════"
echo "🔬 CLEAN PROBE — S2→S4→S5 (50 convergent clusters)"
echo "════════════════════════════════════════════════"

# ── Step 0: Sample 50 convergent clusters ─────────────────────────────
echo ""
echo "📂 [0/5] Sampling 50 convergent clusters..."
python3 - <<'PYEOF'
import json, random
random.seed(123)
conv = []
with open("knowledge pipeline/stage1_5_embed_cluster/latest/checkpoint.jsonl") as f:
    for line in f:
        c = json.loads(line)
        if c.get("is_convergent"):
            conv.append(c)
random.shuffle(conv)
sampled = conv[:50]
with open("probe_output/probe_clusters_50.jsonl", "w") as f:
    for c in sampled:
        f.write(json.dumps(c) + "\n")
sources = set()
for c in sampled:
    for s in c.get("source_books", []):
        sources.add(s)
print(f"   ✅ {len(sampled)} clusters from {len(sources)} unique books")
PYEOF

# ── Step 1: Swap in sample + disable split probe + clear S2 state ─────
echo ""
echo "🔄 [1/5] Preparing clean state..."
cp "$S15" "$S15_BAK" 2>/dev/null || true
cp "$OUT/probe_clusters_50.jsonl" "$S15"
rm -f "$S2_CKPT" "$S2_CACHE" "$S4_CKPT" "$S5_CKPT"
# Disable split probe for probe (config-driven, restored later)
python3 - <<'PYEOF'
import yaml
p = "config/pipeline_config.yaml"
with open(p) as f:
    cfg = yaml.safe_load(f)
cfg["stage2"]["split_probe_enabled"] = False
with open(p, "w") as f:
    yaml.dump(cfg, f, default_flow_style=False, sort_keys=False, allow_unicode=True, width=120)
print("   ✅ split_probe_enabled=False (probe only, will restore)")
PYEOF
echo "   ✅ S1.5 swapped (50 clusters), S2/S4/S5 checkpoints cleared"

# ── Step 2: Run S2 ────────────────────────────────────────────────────
echo ""
echo "🧠 [2/5] Stage 2 — Convergent Extraction (Qwen3-Coder)..."
echo "   Start: $(date)"
nohup python3 -u pipeline/stage2_extract.py --only-convergent --hybrid \
    > "$OUT/s2_run.log" 2>&1 &
S2_PID=$!
echo "   PID: $S2_PID"
# Poll until done
while kill -0 "$S2_PID" 2>/dev/null; do
    sleep 10
    # Show progress
    if [ -f "$S2_CKPT" ]; then
        N=$(wc -l < "$S2_CKPT")
        echo -ne "\r   FBs so far: $N"
    fi
done
wait "$S2_PID" || true
echo ""
echo "   ✅ S2 done: $(date)"
if [ -f "$S2_CKPT" ]; then
    cp "$S2_CKPT" "$OUT/stage2_fbs.jsonl"
    echo "   📋 $(wc -l < "$S2_CKPT") FBs → $OUT/stage2_fbs.jsonl"
else
    echo "   ⚠️  S2 produced no checkpoint — check $OUT/s2_run.log"
    tail -30 "$OUT/s2_run.log"
fi

# ── Step 3: Run S4 ────────────────────────────────────────────────────
echo ""
echo "🏷️  [3/5] Stage 4 — Classify + Enrich (GPT-OSS-20B)..."
echo "   Start: $(date)"
nohup python3 -u pipeline/stage4_merge.py > "$OUT/s4_run.log" 2>&1 &
S4_PID=$!
while kill -0 "$S4_PID" 2>/dev/null; do
    sleep 5
done
wait "$S4_PID" || true
echo "   ✅ S4 done: $(date)"
if [ -f "$S4_CKPT" ]; then
    cp "$S4_CKPT" "$OUT/stage4_fbs.jsonl"
    echo "   📋 $(wc -l < "$S4_CKPT") FBs → $OUT/stage4_fbs.jsonl"
else
    echo "   ⚠️  S4 produced no checkpoint — check $OUT/s4_run.log"
    tail -30 "$OUT/s4_run.log"
fi

# ── Step 4: Run S5 ────────────────────────────────────────────────────
echo ""
echo "🔍 [4/5] Stage 5 — Verify (DeBERTa-v3-large, local)..."
echo "   Start: $(date)"
nohup python3 -u pipeline/stage5_verify.py > "$OUT/s5_run.log" 2>&1 &
S5_PID=$!
while kill -0 "$S5_PID" 2>/dev/null; do
    sleep 5
done
wait "$S5_PID" || true
echo "   ✅ S5 done: $(date)"
if [ -f "$S5_CKPT" ]; then
    cp "$S5_CKPT" "$OUT/stage5_fbs.jsonl"
    echo "   📋 $(wc -l < "$S5_CKPT") FBs → $OUT/stage5_fbs.jsonl"
else
    echo "   ⚠️  S5 produced no checkpoint — check $OUT/s5_run.log"
    tail -30 "$OUT/s5_run.log"
fi

# ── Step 5: Generate visual summaries + restore state ─────────────────
echo ""
echo "📊 [5/5] Generating visual markdown summaries + restoring state..."
python3 - "$OUT" <<'PYEOF'
import sys, json
from pathlib import Path

out = Path(sys.argv[1])

def gen_visual(stage: str, fields: list[str]) -> None:
    jf = out / f"stage{stage}_fbs.jsonl"
    mf = out / f"stage{stage}_visual.md"
    if not jf.exists():
        return
    lines = []
    lines.append(f"# Stage {stage} — Visual Summary\n")
    lines.append(f"> {jf.stat().st_size//1024}KB, generated {jf.stat().st_mtime:.0f}\n")
    count = 0
    with open(jf) as f:
        for line in f:
            if count >= 20:  # First 20 FBs for visual scan
                break
            try:
                d = json.loads(line)
            except Exception:
                continue
            count += 1
            lines.append(f"\n## {count}. {d.get('name', 'unnamed')}")
            lines.append(f"**Status:** {d.get('verification_status', d.get('route', '?'))}")
            if 'epistemic_status' in d:
                lines.append(f"**Epistemic:** {d.get('epistemic_status')} | **ISOR:** {d.get('isor', {}).get('rating', '?') if isinstance(d.get('isor'), dict) else '?'} | **Confidence:** {d.get('confidence_score', '?')}")
            for field in fields:
                v = d.get(field, '')
                if v and isinstance(v, str):
                    lines.append(f"\n**{field}:** {v[:400]}")
            lines.append("\n---")
    if count:
        mf.write_text("\n".join(lines))
        print(f"   ✅ stage{stage}_visual.md ({count} FBs)")

gen_visual("2", ["definition", "mechanism", "boundary", "consequence"])
gen_visual("4", ["definition", "application", "failure_mode", "depth", "discipline"])
gen_visual("5", ["definition", "mechanism"])

# Totals
for s in ["2", "4", "5"]:
    jf = out / f"stage{s}_fbs.jsonl"
    if jf.exists():
        n = sum(1 for _ in open(jf))
        print(f"   stage{s}: {n} FBs")
PYEOF

# Restore S1.5 + config
mv "$S15_BAK" "$S15" 2>/dev/null || true
python3 - <<'PYEOF'
import yaml
p = "config/pipeline_config.yaml"
with open(p) as f:
    cfg = yaml.safe_load(f)
cfg["stage2"]["split_probe_enabled"] = True
with open(p, "w") as f:
    yaml.dump(cfg, f, default_flow_style=False, sort_keys=False, allow_unicode=True, width=120)
print("   ✅ split_probe_enabled=True restored")
PYEOF
echo "   ✅ S1.5 checkpoint restored (12,964 clusters)"

echo ""
echo "════════════════════════════════════════════════"
echo "✅ PROBE COMPLETE"
echo "   Output: $OUT/"
ls -la "$OUT"/*.jsonl "$OUT"/*_visual.md 2>/dev/null | awk '{print "   "$NF" ("$5" bytes)"}'
echo "════════════════════════════════════════════════"
