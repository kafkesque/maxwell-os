#!/usr/bin/env python3
"""Post-hoc re-classification of S2 `extraction_type` (R1 — FORM-axis drift).

The single-source S2 extraction drifted the epistemic FORM axis toward
`causal_mechanism` (~60% vs ~11% convergent baseline; chi-square ~2247). This
script re-labels each FB's `extraction_type` using the DECISION-ORDER precedence
rule added to the S2 prompt (see stage2_extract.py SYSTEM_PROMPT), grounded
strictly in the record's existing fields + evidence_passages.

Why LLM-driven (not deterministic): the epistemic FORM is a property of the
CLAIM (does the evidence demonstrate a cause→effect chain?), not the ROLE. A
deterministic role→form relabel would re-introduce the D2417 coupling that
D2427 (R2) removes. So each record is re-judged against its own evidence.

Scope (BUG-160 — evidence relevance): this script repairs FORM drift ONLY. It
does NOT gate on evidence-passage topical relevance. BUG-160 (cluster-internal
evidence conflation) is deferred to the systematic evidence-relevance pass
(D2428), per BUG-160's own note. A relevance gate was investigated and REVERTED:
(1) the relabel generator (Qwen3) does not self-flag its own conflation (R5 —
verified all-true on the known BUG-160 record); (2) cross-encoder rerankers
(bge-reranker-base, bge-reranker-v2-m3, ms-marco-MiniLM) cannot cleanly separate
"off-topic coherent text" from "on-topic truncated fragment" — an A/B test on a
curated labeled set showed the confound is semantic, not model-bound. No gate =
no false-positive flags = no wrongly-skipped relabels.

Stable fields: fb_id, name, definition, content_type, and every body field are
NOT touched — only `extraction_type` is re-written. Stamps (pipeline_commit,
gen_model, schema_version) are left as-is (this is a label repair, not a
re-generation; R14 tracks the GENERATING revision).

Idempotent + crash-safe (safe_write → tempfile+fsync+os.replace) + resumable
(incremental checkpoint every N candidates via a sidecar progress marker, C23).

Usage:
    MAXWELL_RUN_ID=t11 python3 -u pipeline/stage2_relabel_extraction_type.py --checkpoint COPY --dry-run
    MAXWELL_RUN_ID=t11 python3 -u pipeline/stage2_relabel_extraction_type.py --checkpoint COPY --limit 20 --single-source-only
    MAXWELL_RUN_ID=t11 python3 -u pipeline/stage2_relabel_extraction_type.py --checkpoint COPY --single-source-only --checkpoint-every 50
    MAXWELL_RUN_ID=t11 python3 -u pipeline/stage2_relabel_extraction_type.py --checkpoint COPY --single-source-only --resume
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.content_types import EXTRACTION_TYPES
from pipeline.io_guard import load_jsonl, safe_write
from pipeline.omlx_call import call_omlx_json
from pipeline.pipeline_paths import GEN_MODEL, RELABEL_MAX_WORKERS, STAGE2_CHECKPOINT


SYSTEM_PROMPT: str = "You are a precise JSON generator. Return ONLY valid JSON. No markdown."

_DECISION_ORDER: str = (
    "DECISION ORDER (apply strictly, top-down — answer the FIRST question that matches):\n"
    "1. PRESCRIPTIVE (how-to, method, command, or \"do X to get Y\" advice)?\n"
    "   → normative_heuristic\n"
    "2. Else, evidence DEMONSTRATES a cause→effect chain (verbatim \"causes / leads to /\n"
    "   because Y\", not merely an explanation offered for an association)?\n"
    "   → causal_mechanism\n"
    "3. Else, observed co-occurrence / correlation / regularity (X goes with Y, no proven why)?\n"
    "   → empirical_pattern\n"
    "4. Else, taxonomy / typology / classification (\"categories relate as follows\")?\n"
    "   → descriptive_model\n"
    "DECOUPLING: judge from the EVIDENCE, not from the current mechanism wording. Do NOT\n"
    "upgrade association/advice/taxonomy to causal_mechanism just because the mechanism uses\n"
    "\"causes/because\". Prescriptive content is normative_heuristic even if it has an\n"
    "explanation. Return only the single most honest label."
)


def _build_prompt(rec: dict) -> str:
    ev = rec.get("evidence_passages") or []
    ev_snip = ev[:5] if isinstance(ev, list) else []
    return (
        "Re-classify the epistemic FORM (extraction_type) of this knowledge record.\n"
        f"extraction_type ∈ {sorted(EXTRACTION_TYPES)}\n\n"
        f"{_DECISION_ORDER}\n\n"
        "Record (do NOT change any text — only return the label):\n"
        f"name: {rec.get('name', '')}\n"
        f"definition: {rec.get('definition', '')}\n"
        f"mechanism: {rec.get('mechanism', '')}\n"
        f"boundary: {rec.get('boundary', '')}\n"
        f"consequence: {rec.get('consequence', '')}\n"
        f"evidence: {json.dumps(ev_snip, ensure_ascii=False)}\n\n"
        'Return JSON with exactly one key: {"extraction_type": "<one of the four>"}'
    )


def _extract_label(result: object) -> str:
    obj: object = result
    if isinstance(result, list):
        if not result or not isinstance(result[0], dict):
            return ""
        obj = result[0]
    if not isinstance(obj, dict):
        return ""
    label = str(obj.get("extraction_type", "")).strip()
    return label if label in EXTRACTION_TYPES else ""


def _dist(records: list[dict]) -> Counter:
    return Counter(r.get("extraction_type") for r in records)


def _acquire_lock(checkpoint_path: str) -> Path:
    """Prevent concurrent relabel runs on the same checkpoint (D2434 hygiene).

    Writes a lockfile beside the checkpoint holding this process's PID. If a
    lockfile already exists AND its PID is alive, refuse to start — two runs
    mutating the same checkpoint silently corrupt each other (observed: orphaned
    nohup children from `kill` of a bash wrapper, not the Python child).
    """
    lock_path = Path(checkpoint_path).with_suffix(".relabel_lock")
    if lock_path.exists():
        try:
            owner = int(lock_path.read_text().strip())
            os.kill(owner, 0)  # raises OSError if not alive
            print(f"❌ another relabel run is active (PID {owner}) — refusing to start", file=sys.stderr)
            sys.exit(3)
        except (ValueError, OSError):
            # stale lock (owner dead) — safe to take over
            pass
    lock_path.write_text(f"{os.getpid()}\n")
    return lock_path


def _release_lock(lock_path: Path) -> None:
    """Remove the lockfile (best-effort, never raises)."""
    try:
        if lock_path.exists():
            lock_path.unlink()
    except OSError:
        pass


def _checkpoint_now(checkpoint_path: str, records: list[dict],
                    done: int, progress_path: Path) -> None:
    """Persist incremental progress: full checkpoint + resume marker, all via
    crash-safe writes (C6/C23).

    The marker records the candidate count ALREADY processed so a resume skips
    them. Candidate order is deterministic (stable file order + stable filters),
    so a marker value is a valid resume offset.
    """
    content = "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n"
    safe_write(checkpoint_path, content)
    safe_write(progress_path, f"{done}\n")
    print(f"   💾 checkpoint @ {done}/{len(records)} records", flush=True)


def _judge(rec: dict, model: str = GEN_MODEL) -> str:
    """One FORM re-judgment call (worker-safe). Returns the valid new label, or
    "" when the model returned no valid label."""
    result = call_omlx_json(
        prompt=_build_prompt(rec),
        model=model,
        system=SYSTEM_PROMPT,
        max_tokens=64,
    )
    return _extract_label(result)


def relabel(checkpoint_path: str, *, dry_run: bool, limit: int | None,
            single_source_only: bool, types: frozenset[str] | None,
            resume: bool = False, checkpoint_every: int = 50,
            workers: int = RELABEL_MAX_WORKERS,
            model: str = GEN_MODEL) -> dict:
    checkpoint_path = str(Path(checkpoint_path))
    lock_path = _acquire_lock(checkpoint_path)
    records = load_jsonl(checkpoint_path, context="relabel checkpoint")

    candidates: list[int] = []
    for i, r in enumerate(records):
        if single_source_only and r.get("is_convergent"):
            continue
        if types is not None and r.get("extraction_type") not in types:
            continue
        candidates.append(i)

    before = _dist(records)
    print(f"📋 Candidates: {len(candidates)} / {len(records)} records")
    print(f"   before: {dict(before)}")
    if limit is not None:
        candidates = candidates[:limit]

    progress_path = Path(checkpoint_path).with_suffix(".relabel_progress")
    start_pos: int = 0
    if resume and progress_path.exists():
        try:
            start_pos = int(progress_path.read_text().strip())
            print(f"   ⏩ resuming from candidate #{start_pos}")
        except ValueError:
            start_pos = 0

    # Active candidates: drop the resume offset. Parallelism is safe because each
    # record's `extraction_type` is mutated independently (no cross-record deps);
    # mutations are applied on the main thread in candidate order, so checkpoint
    # writes and the resume marker stay deterministic (D2434).
    active: list[tuple[int, int]] = [(pos, i) for pos, i in enumerate(candidates) if pos >= start_pos]

    changed: int = 0
    unchanged: int = 0
    failed: int = 0
    workers = max(1, workers)

    for chunk_start in range(0, len(active), workers):
        chunk = active[chunk_start:chunk_start + workers]
        # Collect judgments concurrently (or serially for workers==1 / dry-run).
        if dry_run:
            for pos, i in chunk:
                rec = records[i]
                print(f"   [dry-run] would re-judge #{i} {rec.get('name', '?')[:40]} "
                      f"(now {rec.get('extraction_type')})")
            continue

        results: dict[int, tuple[str, str]] = {}  # i -> (label, error)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(_judge, records[i], model): i for _, i in chunk}
            for fut in futures:
                i = futures[fut]
                try:
                    results[i] = (fut.result(), "")
                except Exception as e:
                    results[i] = ("", f"{type(e).__name__}: {e}")

        # Apply in deterministic candidate order.
        for pos, i in chunk:
            rec = records[i]
            old = rec.get("extraction_type")
            label = f"{rec.get('name', '?')[:40]}"
            new, err = results[i]
            if err:
                failed += 1
                print(f"   ❌ #{i} {label}: {err}", file=sys.stderr, flush=True)
            elif not new:
                failed += 1
                print(f"   ⚠️  #{i} {label}: no valid label returned", file=sys.stderr, flush=True)
            elif new == old:
                unchanged += 1
            else:
                rec["extraction_type"] = new
                changed += 1
                print(f"   🔁 #{i} {label}: {old} → {new}")

        # Checkpoint at chunk boundaries (deterministic, C23). The marker stores
        # the CUMULATIVE candidate count (start_pos + this-run progress), matching
        # the resume offset semantics.
        if not dry_run:
            done_cum = start_pos + min(chunk_start + workers, len(active))
            if done_cum % checkpoint_every == 0 or chunk_start + workers >= len(active):
                _checkpoint_now(checkpoint_path, records, done_cum, progress_path)

    if not dry_run:
        content = "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n"
        safe_write(checkpoint_path, content)
        load_jsonl(checkpoint_path, context="relabel self-check")
        if progress_path.exists():
            progress_path.unlink()

    after = _dist(records)
    print(f"   after : {dict(after)}")
    print(f"✅ Relabel done: changed {changed}, unchanged {unchanged}, failed {failed}")
    _release_lock(lock_path)
    return {"changed": changed, "unchanged": unchanged, "failed": failed}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", default=str(STAGE2_CHECKPOINT))
    parser.add_argument("--dry-run", action="store_true",
                        help="Report candidates without writing or calling the LLM")
    parser.add_argument("--limit", type=int, default=None,
                        help="Re-judge only the first N candidates (for testing)")
    parser.add_argument("--single-source-only", action="store_true",
                        help="Only reconsider single-source (non-convergent) records")
    parser.add_argument("--types", default=None,
                        help="Comma-separated extraction_type values to reconsider (default: all)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from the last incremental checkpoint")
    parser.add_argument("--checkpoint-every", type=int, default=50,
                        help="Persist a crash-safe checkpoint every N candidates (default: 50)")
    parser.add_argument("--workers", type=int, default=RELABEL_MAX_WORKERS,
                        help="Parallel relabel workers (default: from config stage2.relabel_max_workers)")
    parser.add_argument("--model", default=GEN_MODEL,
                        help="Judge model (default: pipeline GEN_MODEL; pass S4_DEPTH_MODEL for gemma)")
    args = parser.parse_args()
    types: frozenset[str] | None = None
    if args.types:
        vals = {v.strip() for v in args.types.split(",") if v.strip()}
        bad = vals - set(EXTRACTION_TYPES)
        if bad:
            print(f"error: unknown extraction_type(s): {sorted(bad)}", file=sys.stderr)
            sys.exit(2)
        types = frozenset(vals)
    r = relabel(args.checkpoint, dry_run=args.dry_run, limit=args.limit,
                single_source_only=args.single_source_only, types=types,
                resume=args.resume, checkpoint_every=args.checkpoint_every,
                workers=args.workers, model=args.model)
    sys.exit(0 if r["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
