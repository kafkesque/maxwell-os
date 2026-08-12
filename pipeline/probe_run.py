#!/usr/bin/env python3
"""
probe_run.py — Controlled S2→S4→S5 probe with lazy loading, sleep prevention, and per-stage checkpoints.

Usage:
    python3 pipeline/probe_run.py --n-clusters 200 --output-dir probe_output/

Process:
  1. Loads S1.5 clusters, samples N convergent clusters + all single-source
  2. S2: Extracts FBs (Qwen3-Coder, lazy-loaded)
  3. S4: Merges + classifies (GPT-OSS-20B, lazy-loaded)
  4. S5: Verifies (DeBERTa-v3-large, always local)
  5. Checkpoints at each stage for visual inspection

Lazy loading: OMLX loads only the model needed for current stage, unloads after.
Sleep prevention: caffeinate keeps Mac awake during probe.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Config paths ──────────────────────────────────────────────────────
S15_CHECKPOINT = PROJECT_ROOT / "knowledge pipeline/stage1_5_embed_cluster/latest/checkpoint.jsonl"
S1_CHECKPOINT = PROJECT_ROOT / "knowledge pipeline/stage1_chunk/latest/checkpoint.jsonl"
PROBE_DIR = PROJECT_ROOT / "probe_output"

# ── OMLX lazy loading ─────────────────────────────────────────────────
OMLX_URL = "http://localhost:11435"

def omlx_load_model(model_name: str) -> bool:
    """Load a model into OMLX memory. Returns True if successful."""
    try:
        import requests
        r = requests.post(f"{OMLX_URL}/v1/models/load", json={"model": model_name}, timeout=30)
        return r.status_code == 200
    except Exception:
        return False

def omlx_unload_model(model_name: str) -> bool:
    """Unload a model from OMLX memory. Returns True if successful."""
    try:
        import requests
        r = requests.post(f"{OMLX_URL}/v1/models/unload", json={"model": model_name}, timeout=10)
        return r.status_code == 200
    except Exception:
        return False

def omlx_health() -> dict:
    """Check OMLX health."""
    try:
        import requests
        r = requests.get(f"{OMLX_URL}/health", timeout=5)
        return r.json()
    except Exception:
        return {"status": "unreachable"}

# ── Sleep prevention ──────────────────────────────────────────────────
def start_caffeinate() -> subprocess.Popen | None:
    """Start caffeinate to prevent sleep/screensaver."""
    try:
        proc = subprocess.Popen(
            ["caffeinate", "-dimsu"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("☕ caffeinate: preventing sleep/screensaver (PID {})".format(proc.pid))
        return proc
    except Exception:
        print("⚠️  caffeinate unavailable — Mac may sleep during probe")
        return None

def stop_caffeinate(proc: subprocess.Popen | None) -> None:
    """Stop caffeinate."""
    if proc:
        proc.terminate()
        print("☕ caffeinate: released")

# ── Cluster sampling ──────────────────────────────────────────────────
def load_clusters(max_convergent: int = 200) -> list[dict]:
    """Load and sample clusters from S1.5 checkpoint."""
    conv: list[dict] = []
    single: list[dict] = []
    
    print(f"📂 Loading clusters from {S15_CHECKPOINT}...")
    with open(S15_CHECKPOINT) as f:
        for line in f:
            c = json.loads(line)
            if c.get("is_convergent"):
                conv.append(c)
            else:
                single.append(c)
    
    # Sample convergent clusters (shuffle to get diversity)
    import random
    random.seed(42)
    random.shuffle(conv)
    sampled = conv[:max_convergent]
    
    print(f"   Convergent: {len(sampled)}/{len(conv)} sampled | Single-source: {len(single)}")
    return sampled + single

# ── Stage runners ─────────────────────────────────────────────────────
def run_stage2(clusters: list[dict], output_dir: Path) -> list[dict]:
    """Run S2 extraction on sampled clusters. Returns extracted FBs."""
    print(f"\n{'='*60}")
    print(f"🧠 STAGE 2: Convergent Extraction — {len(clusters)} clusters")
    print(f"{'='*60}")
    
    # Write temporary cluster file for stage2 to read
    tmp_clusters = output_dir / "probe_clusters.jsonl"
    with open(tmp_clusters, "w") as f:
        for c in clusters:
            f.write(json.dumps(c) + "\n")
    
    # Run stage2 with our cluster file
    s2_start = time.time()
    result = subprocess.run(
        [sys.executable, "-c", f"""
import sys, json
sys.path.insert(0, '{PROJECT_ROOT}')
from pipeline.stage2_extract import load_segments, _process_cluster, build_convergent_prompt, build_single_source_prompt
from pipeline.stage2_extract import SYSTEM_PROMPT, SINGLE_SOURCE_SYSTEM, GEN_MODEL, call_llm, load_golden_parity, format_golden_fewshot, S2_GOLDEN_PATH, S2_GOLDEN_POSITIVE, S2_GOLDEN_NEGATIVE, S2_GOLDEN_MAX, S2_GOLDEN_INJECT, enforce_gate, S2_GATE_ENABLED, S2_GATE_STRICT
from pipeline.pipeline_paths import STAGE2_CHECKPOINT
from pipeline.io_guard import safe_write
from pipeline.stamp import stamp_record
import time

clusters = []
with open('{tmp_clusters}') as f:
    for line in f:
        clusters.append(json.loads(line))

segments = load_segments()

# Golden examples
pos_ex, neg_ex, golden_total = load_golden_parity(S2_GOLDEN_PATH, S2_GOLDEN_POSITIVE, S2_GOLDEN_NEGATIVE, S2_GOLDEN_MAX)
few_shot_text = ''
if S2_GOLDEN_INJECT and pos_ex:
    few_shot_text = format_golden_fewshot(pos_ex, neg_ex)
    print(f'   🎯 Golden few-shot: {{len(pos_ex)}} pos + {{len(neg_ex)}} neg examples')

all_fbs = []
total_null = 0
total_extracted = 0

for i, cluster in enumerate(clusters, 1):
    cid = cluster.get('cluster_id', f'cluster_{{i}}')
    is_conv = cluster.get('is_convergent', False)
    conv_tag = '🌐' if is_conv else '📖'
    
    # Build prompt
    if is_conv:
        prompt, evidence_passages = build_convergent_prompt(cluster, segments)
        system = SYSTEM_PROMPT
    else:
        prompt, evidence_passages = build_single_source_prompt(cluster, segments)
        system = SINGLE_SOURCE_SYSTEM
    
    try:
        result = call_llm(prompt, system, GEN_MODEL, 'omlx',
                         few_shot=few_shot_text if few_shot_text and is_conv else None)
    except Exception as e:
        print(f'  [{{i}}/{{len(clusters)}}] ❌ {{conv_tag}} {{cid}}: {{e}}')
        continue
    
    if result is None:
        print(f'  [{{i}}/{{len(clusters)}}] ❌ {{conv_tag}} {{cid}}: LLM returned None')
        continue
    
    principles = result if isinstance(result, list) else [result]
    
    for principle in principles:
        route = str(principle.get('route', 'FB')).strip().upper()
        if route == 'NULL':
            total_null += 1
            continue
        
        fb = {{
            'name': principle.get('name', '').strip(),
            'definition': principle.get('definition', '').strip(),
            'mechanism': principle.get('mechanism', '').strip(),
            'boundary': principle.get('boundary', '').strip(),
            'consequence': principle.get('consequence', '').strip(),
            'is_summary': principle.get('is_summary', False),
            'extraction_type': principle.get('extraction_type', 'causal_mechanism'),
            'content_type': principle.get('content_type', 'principle'),
            'evidence_passages': evidence_passages if isinstance(evidence_passages, list) else json.loads(evidence_passages) if isinstance(evidence_passages, str) else [],
            'evidence_passages_shown': principle.get('evidence_passages', []),
            'route': route,
            'source_cluster': cid,
            'source_books': cluster.get('source_books', []),
            'source_ids': cluster.get('source_ids', []),
            'cluster_cohesion': cluster.get('cohesion', 0.0),
            'cluster_size': cluster.get('size', 0),
            'source_diversity': cluster.get('source_diversity', 0),
        }}
        fb = stamp_record(fb, gen_model=GEN_MODEL)
        all_fbs.append(fb)
        total_extracted += 1
    
    elapsed = time.time() - {s2_start} if i > 1 else 0
    rate = i / elapsed if elapsed > 0 else 0
    print(f'  [{{i}}/{{len(clusters)}}] {{conv_tag}} {{cid}}: {{total_extracted}} FBs, {{total_null}} NULLs ({{rate:.1f}} cls/s)')

# Gate enforcement
if S2_GATE_ENABLED:
    all_fbs, gate_violations = enforce_gate(all_fbs, strict=S2_GATE_STRICT)
    print(f'   🚪 Gate: {{gate_violations}} FBs gated, {{len(all_fbs)}} passed')

# Save checkpoint
STAGE2_CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
checkpoint_text = '\\n'.join(json.dumps(fb, ensure_ascii=False) for fb in all_fbs) + '\\n'
with open(STAGE2_CHECKPOINT, 'w') as f:
    f.write(checkpoint_text)
print(f'\\n✅ Stage 2 complete: {{len(all_fbs)}} FBs → {{STAGE2_CHECKPOINT}}')

# Also save to probe output
import shutil
probe_s2 = Path('{output_dir}') / 'stage2_checkpoint.jsonl'
shutil.copy(STAGE2_CHECKPOINT, probe_s2)
print(f'   📋 Copy: {{probe_s2}}')
"""],
        capture_output=True,
        text=True,
        timeout=7200,  # 2h max
        env={**os.environ, "MAXWELL_RUN_ID": "probe"},
    )
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr[-500:])
    
    s2_elapsed = time.time() - s2_start
    print(f"   ⏱️  S2 elapsed: {s2_elapsed:.0f}s")
    
    # Load S2 FBs
    s2_checkpoint = output_dir / "stage2_checkpoint.jsonl"
    fbs = []
    if s2_checkpoint.exists():
        with open(s2_checkpoint) as f:
            for line in f:
                if line.strip():
                    fbs.append(json.loads(line))
    return fbs


def run_stage4(fbs: list[dict], output_dir: Path) -> list[dict]:
    """Run S4 merge + classification on S2 FBs. Returns classified FBs."""
    print(f"\n{'='*60}")
    print(f"🏷️  STAGE 4: Merge + Classify — {len(fbs)} FBs")
    print(f"{'='*60}")
    
    # Write input FBs
    s4_input = output_dir / "stage4_input.jsonl"
    with open(s4_input, "w") as f:
        for fb in fbs:
            f.write(json.dumps(fb, ensure_ascii=False) + "\n")
    
    s4_start = time.time()
    result = subprocess.run(
        [sys.executable, "-c", f"""
import sys, json, time
sys.path.insert(0, '{PROJECT_ROOT}')
from pipeline.stage4_merge import run_stage4 as _run_s4
_run_s4()
"""],
        capture_output=True,
        text=True,
        timeout=7200,
        env={**os.environ, "MAXWELL_RUN_ID": "probe"},
    )
    
    print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr[-500:])
    
    s4_elapsed = time.time() - s4_start
    print(f"   ⏱️  S4 elapsed: {s4_elapsed:.0f}s")
    
    # Load S4 FBs from pipeline checkpoint
    from pipeline.pipeline_paths import STAGE4_CHECKPOINT
    fbs_out = []
    if STAGE4_CHECKPOINT.exists():
        with open(STAGE4_CHECKPOINT) as f:
            for line in f:
                if line.strip():
                    fbs_out.append(json.loads(line))
        # Copy to probe output
        probe_s4 = output_dir / "stage4_checkpoint.jsonl"
        import shutil
        shutil.copy(STAGE4_CHECKPOINT, probe_s4)
        print(f"   📋 {len(fbs_out)} FBs → {probe_s4}")
    return fbs_out


def run_stage5(fbs: list[dict], output_dir: Path) -> list[dict]:
    """Run S5 verification on S4 FBs."""
    print(f"\n{'='*60}")
    print(f"🔍 STAGE 5: Verify — {len(fbs)} FBs")
    print(f"{'='*60}")
    
    s5_start = time.time()
    result = subprocess.run(
        [sys.executable, "-c", f"""
import sys
sys.path.insert(0, '{PROJECT_ROOT}')
from pipeline.stage5_verify import run_stage5
run_stage5(strict=False)
"""],
        capture_output=True,
        text=True,
        timeout=3600,
    )
    
    print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr[-500:])
    
    s5_elapsed = time.time() - s5_start
    print(f"   ⏱️  S5 elapsed: {s5_elapsed:.0f}s")
    
    # Load S5 FBs
    from pipeline.pipeline_paths import STAGE5_CHECKPOINT
    fbs_out = []
    if STAGE5_CHECKPOINT.exists():
        with open(STAGE5_CHECKPOINT) as f:
            for line in f:
                if line.strip():
                    fbs_out.append(json.loads(line))
        probe_s5 = output_dir / "stage5_checkpoint.jsonl"
        import shutil
        shutil.copy(STAGE5_CHECKPOINT, probe_s5)
        print(f"   📋 {len(fbs_out)} FBs → {probe_s5}")
    return fbs_out


# ── Main ──────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="S2→S4→S5 probe with per-stage checkpoints")
    parser.add_argument("--n-clusters", type=int, default=200, help="Convergent clusters to sample (default: 200)")
    parser.add_argument("--output-dir", type=str, default="probe_output", help="Output directory")
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("🔬 MAXWELL OS PROBE — S2→S4→S5")
    print(f"   Clusters: {args.n_clusters} convergent + all single-source")
    print(f"   Output: {output_dir}")
    print("=" * 60)
    
    # Check OMLX health
    health = omlx_health()
    print(f"   OMLX: {health.get('status', '?')} ({health.get('engine_pool', {}).get('loaded_count', '?')} models loaded)")
    
    # Start caffeinate
    caf = start_caffeinate()
    
    try:
        # Load clusters
        clusters = load_clusters(max_convergent=args.n_clusters)
        print(f"   Total clusters to process: {len(clusters)}")
        
        # Stage 2: Extraction (needs Qwen3-Coder)
        print("\n🔄 Lazy-loading Qwen3-Coder for S2...")
        omlx_load_model("Qwen3-Coder-30B-A3B-Instruct-MLX-4bit")
        fbs_s2 = run_stage2(clusters, output_dir)
        
        # Unload Qwen3-Coder, load GPT-OSS for S4
        print("\n🔄 Swapping: unload Qwen3-Coder → load GPT-OSS-20B for S4...")
        omlx_unload_model("Qwen3-Coder-30B-A3B-Instruct-MLX-4bit")
        omlx_load_model("gpt-oss-20b-MXFP4-Q8")
        
        # Stage 4: Classification
        fbs_s4 = run_stage4(fbs_s2, output_dir)
        
        # Unload GPT-OSS (S5 uses local DeBERTa, no OMLX needed)
        print("\n🔄 Unloading GPT-OSS-20B — S5 uses local DeBERTa...")
        omlx_unload_model("gpt-oss-20b-MXFP4-Q8")
        
        # Stage 5: Verification (local DeBERTa — no OMLX model needed)
        fbs_s5 = run_stage5(fbs_s4, output_dir)
        
        # Summary
        print(f"\n{'='*60}")
        print(f"✅ PROBE COMPLETE")
        print(f"   S2 FBs extracted: {len(fbs_s2)}")
        print(f"   S4 FBs classified: {len(fbs_s4)}")
        print(f"   S5 FBs verified: {len(fbs_s5)}")
        print(f"   Checkpoints: {output_dir}/")
        for f in sorted(output_dir.glob("*.jsonl")):
            lines = sum(1 for _ in open(f))
            size_kb = f.stat().st_size / 1024
            print(f"     {f.name}: {lines} lines, {size_kb:.0f}KB")
        print(f"{'='*60}")
        
    finally:
        stop_caffeinate(caf)


if __name__ == "__main__":
    main()
