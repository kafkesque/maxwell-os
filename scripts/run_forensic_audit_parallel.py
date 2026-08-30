#!/usr/bin/env python3
"""Run 4 forensic-audit prompts against local OMLX models in parallel (D2493).

Delegate transport is flaky for long multi-step audits ("error decoding response
body" on OMLX streaming), so we call call_omlx (non-streaming, the pipeline's own
path) directly and run the 4 role prompts concurrently. Each prompt carries
self-contained evidence; the model TRIAGES/RANKS it (no file exploration needed).
"""
from __future__ import annotations

import concurrent.futures
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from pipeline.omlx_call import call_omlx  # noqa: E402

OUT = REPO / "temp" / "forensic_audit_local_llms.json"

# ── Evidence (gathered by the orchestrator) ──────────────────────────────

SILENT_SITES = """Active-path `except ...: pass/continue` swallows found (file:line):
- stage0_convert.py:111/113  FileNotFoundError / TimeoutExpired -> pass
- stage0_5_extract_metadata.py:98  JSONDecodeError -> continue (skips malformed metadata lines)
- stage1_5_embed_cluster.py:125  OSError -> pass ; :161 JSONDecodeError/KeyError -> pass ; :273/:288/:355 torch.mps.empty_cache / np.load(cache) -> pass
- stage2_extract.py:1969  (AttributeError, ValueError) -> pass (unbuffered fd)
- stage4_merge.py:1228  (ValueError, OSError) -> pass (signal handler)
- stage6_commit.py:227 PRAGMA unsupported -> pass ; :288 sqlite OperationalError (column exists) -> pass ; :552 OSError -> pass ; :623 vec_fbs COUNT -> pass (prints warning after) ; :642 orphaned-vector reconcile -> pass
- stage6_okf_export.py:121  (JSONDecodeError, TypeError) -> pass (verification field parse)

Non-atomic open(...,"w") writers NOT using safe_write/tempfile-fsync-replace:
- calibrate.py:30 (PROGRESS), coverage_check.py:129, nli_calibrate.py:273, protect.py:47 (RUNNING_FLAG), route.py:127, run_diagnostic.py:251/454/932/935, run_monitor.py:284/345, taxonomy_manager.py:435/506, stress_test_s2_exhaustive.py:225, test_matryoshka_nli.py:470
"""

S4_BOUNDARY = """S4/S5/S6 boundary findings already made by the orchestrator:
1. S4_DEPTH_FALLBACK_DEPTH='domain' (stage4_merge.py:1879): when raw_depth is INVALID/hallucinated, depth silently becomes 'domain' with NO classification_status/classification_error marker — indistinguishable from a confident 'domain' classification. (The depth-call-FAILURE path at :1864 DOES set status='FAILED'.) 
2. S5 preflight gate (_preflight_gate, stage5_verify.py:250) runs scripts/preflight_checkpoint_check.py --check WITHOUT --expect-count, so it validates against the SELF-REFERENTIAL manifest (sha256+record_count written by the S4 writer) but does NOT cross-check an authoritative S2 population count — a silent S4-side record DROP (not truncation) would pass.
3. BUG-187 (schema drift, deferred): 7 emitted fields not in schemas.FB (classification_error/classify_model/evidence_passages/evidence_passages_shown/is_summary/manifest_hash/source_segments) + jargon key omitted-when-empty.
"""

CONTAMINATION = """S0-S2 upstream contamination findings already on record (buglog BUG-181/182/175):
- BUG-181#1: 9.8% singleton evidence_passages carry EPUB->MD conversion artifacts; 29 severe quarantined at S5 (accept-and-flag, NOT full re-clean).
- BUG-175: Phi-4-mini hallucinated author="string"/"Unknown" on 253 records -> sentinel-guard + backfill (FIXED).
- BUG-182: 48 singleton empty-shell deterministically re-return empty (temp=0.0) — model-level, not S4 blocker.
- BUG-159: prompt-injection contamination cluster_11649 (OPEN).
- BUG-148: S2 `route` field stale/uniform 'FB' on ALL 2,878 records (OPEN).
"""

CONFIG_DRIFT = """Governance/config/script coherence observations:
- MEMORY BUDGET documented three ways: AGENTS.md:83 '~24GB of 64GB'; decisions.yaml D2208 'OMLX memory guard ceiling 55GB'; user-stated wall 48GB. These are three different concepts (delegate model budget / OMLX guard ceiling / run budget) but not clearly labeled.
- batch_enabled=false (D2265 rejected), merged_call_enabled=true, depth_batch_enabled=true (D2477) — confirm no orphaned/contradictory flags.
- gate_emerging_rate.py NOW wired into justfile triad (D2491) + standalone 'gate-emerging' recipe.
- preflight S5 gate wired (D2490).
"""

PROMPTS = [
    ("gemma-4-E4B-it-MLX-4bit", "silent-exception triage",
     "You are a forensic reliability auditor. Below are raw grep findings from a RAG pipeline. "
     "For EACH site, classify CRITICAL (silent loss on active path) / HIGH (silent degradation reaching consumer) / MED / LOW (benign/future), with a one-line reason. "
     "Then give a 2-line overall verdict on the remaining silent-failure surface.\n\n" + SILENT_SITES),
    ("gemma-4-E4B-it-MLX-4bit", "S4 boundary triage",
     "You are a forensic reliability auditor. Below are 3 findings already made on the S4->S5->S6 write/read boundary. "
     "For each: confirm or refute, assign CRITICAL/HIGH/MED/LOW, and give a one-line fix. Then name any OTHER boundary blind-spot you would check.\n\n" + S4_BOUNDARY),
    ("Qwen3.8-27B-MLX-4bit", "governance/config drift",
     "You are a forensic auditor for governance/config/script coherence. Below are observations about a RAG pipeline. "
     "For each: state whether it is a real DRIFT/MISMATCH, FUTURE-TAX, or benign, with a one-line reason and a one-line fix if real. "
     "Then give a 3-line verdict on governance coherence.\n\n" + CONFIG_DRIFT),
    ("gemma-4-E4B-it-MLX-4bit", "S0-S2 contamination triage",
     "You are a forensic auditor for data provenance/contamination. Below are contamination findings already on record for an extraction pipeline. "
     "For each: classify remaining risk CRITICAL/HIGH/MED/LOW (given the stated mitigation), and name ONE additional contamination vector you would check that is NOT listed.\n\n" + CONTAMINATION),
]


def run_one(model: str, tag: str, prompt: str) -> dict:
    try:
        text = call_omlx(prompt=prompt, model=model, max_tokens=1500, timeout=180)
        return {"model": model, "tag": tag, "ok": True, "text": text.strip()}
    except Exception as e:  # noqa: BLE001
        return {"model": model, "tag": tag, "ok": False, "error": f"{type(e).__name__}: {e}"}


def main() -> int:
    results: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(run_one, m, t, p): (m, t) for m, t, p in PROMPTS}
        for f in concurrent.futures.as_completed(futs):
            m, t = futs[f]
            r = f.result()
            results.append(r)
            status = "✅" if r["ok"] else "❌"
            print(f"{status} {r['tag']} [{r['model']}]")
    results.sort(key=lambda r: r["tag"])
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n📄 wrote {OUT}")
    for r in results:
        print("\n" + "=" * 70)
        print(f"### {r['tag']} [{r['model']}]")
        print("=" * 70)
        print(r.get("text") or r.get("error"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
