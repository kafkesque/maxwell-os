#!/usr/bin/env python3
"""D2532: BUG-197 targeted re-classification of the merged-call DISCIPLINE axis.

The gpt-oss merged S4 call historically filed DOMAIN labels as DISCIPLINE, leaving
~2,343 production FBs with `discipline = 'emerging'`. The D2519 deterministic
kind-swap cleaned the *canonical* axis (a discipline that literally equals a
canonical domain is now swapped), but the residual `discipline = 'emerging'` rows
still need an LLM re-decision under the corrected disjointness prompt.

SCOPE (deliberately NARROW):
  - Re-decides the DISCIPLINE axis ONLY. Domains are PRESERVED as-is: they were
    already canonically mapped, and the A/B (D2532) showed re-deriving them from
    scratch REGRESSES valid canonicals ('legal & public policy' → [] because the
    raw domain label simply isn't in the 44-entry canonical list). Do NOT re-derive.
  - Only WRITES a row when the re-decision RESOLVES the discipline
    (emerging → a real canonical discipline). Still-emerging rows are taxonomy
    gaps (BUG-150), not classifier errors — they are left untouched in the DB.
  - HARVESTS every corrected raw discipline to a JSONL sidecar (resolved AND
    still-emerging) so the BUG-150 promotion pass can lift genuinely-missing
    labels into the canonical taxonomy without re-running the LLM.

Safety (C13 / C6 / C12):
  - Default is DRY-RUN: reports what WOULD change, writes nothing.
  - `--apply` requires a pre-write timestamped DB backup + an integrity gate
    (PRAGMA quick_check + foreign_key_check); it REFUSES to write if either fails.
  - Writes are a single SQLite transaction (atomic; crash-safe). No silent errors.

Usage:
  python3 pipeline/reclassify_merged_axis.py --limit 8 --batch     # A/B sample, batch mode
  python3 pipeline/reclassify_merged_axis.py --limit 8 --no-batch  # A/B sample, sequential
  python3 pipeline/reclassify_merged_axis.py --apply               # full corpus, backup + integrity gate
  python3 pipeline/reclassify_merged_axis.py --where "discipline='emerging'" --apply
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from pipeline.io_guard import safe_write  # noqa: E402
from pipeline.omlx_call import call_omlx_json  # noqa: E402
from pipeline.pipeline_paths import (  # noqa: E402
    DB_PATH,
    VERIFY_MODEL,
    VERIFY_REASONING_OFF_MODELS,
    VERIFY_REASONING_OFF_PREFIX,
    _CFG,
)
from pipeline.schemas import (  # noqa: E402
    CANONICAL_DISCIPLINES,
    get_synonym_index,
)
from pipeline.stage4_merge import map_to_canonical_with_fallback  # noqa: E402
from pipeline.stage4_merged_call import (  # noqa: E402
    BATCH_SIZE_DEFAULT,
    batch_cribs_classify,
    merged_cribs_classify,
)

DEFAULT_WHERE = "discipline = 'emerging'"

# Checkpoint/apply granularity: number of FBs classified before an ATOMIC apply
# + crash-safe harvest append. A crash mid-run loses at most one chunk; re-running
# the same --where skips already-applied FBs (they no longer match: discipline
# changed OR discipline_raw filled), so resume is automatic (D2533 hardening).
CHUNK_SIZE_DEFAULT = 200

# FB fields the merged/batch classifier consumes (prompt input). Everything else
# (domains, evidence, application, elaboration, keywords, jargon, depth,
# is_specialized) is deliberately NOT re-generated — this script only repairs the
# DISCIPLINE axis so already-committed content survives intact.
_PROMPT_FIELDS = ("name", "definition", "mechanism", "boundary", "consequence", "source_text", "evidence_passages")


def _cfg_stage4(key: str, default: Any) -> Any:
    return _CFG.get("stage4", {}).get(key, default)


def load_affected(db_path: Path, where: str, limit: int | None) -> list[dict]:
    """Load the affected FB rows (fb_id + prompt fields + current taxonomy labels)."""
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    sql = (
        "SELECT fb_id, name, definition, mechanism, boundary, consequence, "
        "       source_text, evidence_passages, "
        "       discipline, discipline_raw, taxonomy_match_method "
        f"FROM fbs WHERE {where} ORDER BY fb_id"
    )
    params: list = []
    if limit:
        sql += " LIMIT ?"
        params.append(int(limit))
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def remap_discipline(result: dict, synonym_index: dict[str, str]) -> tuple[str, str, str]:
    """Map a merged/batch result's raw discipline → canonical (DISCIPLINE axis only).

    Mirrors stage4_merge.py's D2138 discipline mapping exactly (singular, with
    emerging_real/emerging_unmapped/exact/synonym match-method). Domains are NOT
    touched here — see module docstring (A/B D2532 regression finding).

    Returns: (canonical_discipline, discipline_raw, taxonomy_match_method).
    """
    raw_disc = result.get("discipline")
    if isinstance(raw_disc, list):
        raw_disc = raw_disc[0] if raw_disc else ""
    raw_disc = str(raw_disc) if raw_disc else ""

    if not raw_disc.strip():
        return ("emerging", raw_disc, "emerging_unmapped")

    canonical_disc = map_to_canonical_with_fallback(
        raw_disc, "discipline", synonym_index, CANONICAL_DISCIPLINES
    )
    if canonical_disc == "emerging":
        match = "emerging_real"
    elif canonical_disc.lower() == raw_disc.lower():  # D2532: mirror stage4_merge exact-vs-synonym split exactly
        match = "exact"
    else:
        match = "synonym"
    return (canonical_disc, raw_disc, match)


def _to_prompt_dict(fb: dict) -> dict:
    return {k: fb.get(k, "") for k in _PROMPT_FIELDS}


# ── SLIM discipline-only classification (D2534) ──────────────────────────────
# The re-classification only needs the DISCIPLINE axis (domains are preserved).
# Generating the full CRIBS + classification per FB (merged_cribs_classify) is why
# the A/B measured 12s/FB → ~8h for 2,339 FBs. A discipline-only prompt generates
# ~1/30th of the tokens → ~30-60 min for the full corpus, quality-neutral for the
# discipline question (same input fields, same gpt-oss model, same disjointness rules).
_SLIM_DISCIPLINE_SYSTEM = """You classify the single most precise academic discipline for a Foundation Block.

discipline = an ACADEMIC FIELD OF STUDY (e.g. cognitive science, economics, philosophy,
computer science, psychology, linguistics, systems engineering, information science,
organizational theory, anthropology, sociology, machine learning).

A label naming an APPLIED PRACTICE/INDUSTRY (e.g. "graphic design", "organizational behavior",
"data visualization", "marketing", "product design", "HR", "entrepreneurship") is a DOMAIN,
NOT a discipline.

DO NOT use "emerging" as a discipline — use the most specific real discipline name.
Return ONLY a JSON array: [{"fb_index": 0, "discipline": "..."}, ...] one object per FB."""


def build_slim_discipline_prompt(fbs_data: list[dict]) -> str:
    """Build a discipline-only batch prompt (input = the same 5 S4 core fields)."""
    lines = ["Classify the academic discipline of each Foundation Block.", ""]
    for i, fb in enumerate(fbs_data):
        lines.append(f"--- FB {i} ---")
        lines.append(f"NAME: {fb.get('name', '')}")
        lines.append(f"DEFINITION: {fb.get('definition', '')}")
        if fb.get("mechanism"):
            lines.append(f"MECHANISM: {fb['mechanism']}")
        if fb.get("boundary"):
            lines.append(f"BOUNDARY: {fb['boundary']}")
        lines.append("")
    lines.append('Return ONLY a JSON array: [{"fb_index": N, "discipline": "..."}] one object per FB, matching fb_index to input order.')
    return "\n".join(lines)


def slim_batch_discipline_classify(fbs_data: list[dict], model: str, batch_size: int = BATCH_SIZE_DEFAULT) -> list[dict]:
    """Discipline-only batched classification. Returns one {"discipline": ...} per input FB.

    Same model (gpt-oss, R5) + same disjointness rules as the full merged call, but
    skips CRIBS/domains/depth generation (which the re-classification discards anyway).
    Raises on a missing batch entry (fail-closed, mirroring batch_cribs_classify).
    """
    system = _SLIM_DISCIPLINE_SYSTEM
    if model in VERIFY_REASONING_OFF_MODELS and VERIFY_REASONING_OFF_PREFIX:
        system = f"{VERIFY_REASONING_OFF_PREFIX}\n\n{system}"
    out: list[dict] = []
    for i in range(0, len(fbs_data), batch_size):
        chunk = fbs_data[i:i + batch_size]
        prompt = build_slim_discipline_prompt(chunk)
        try:
            res = call_omlx_json(prompt=prompt, model=model, system=system, max_tokens=1024, timeout=180)
        except Exception as e:  # C16: log AND fall back to single-FB, never silent
            print(f"  ⚠️  slim batch [{i}-{i + len(chunk)}) FAILED ({type(e).__name__}: {e}) — single-FB fallback", file=sys.stderr)
            for fb in chunk:
                try:
                    r = call_omlx_json(prompt=build_slim_discipline_prompt([fb]), model=model, system=system, max_tokens=256, timeout=180)
                    out.append({"discipline": _extract_discipline(r)})
                except Exception as e2:
                    print(f"    ⚠️  FB slim FAILED ({type(e2).__name__}: {e2})", file=sys.stderr)
                    out.append({"discipline": ""})
            continue
        if isinstance(res, dict):
            res = [res]
        if not isinstance(res, list):
            raise ValueError(f"slim classify returned non-list: {type(res)}")
        indexed: dict[int, dict] = {}
        for item in res:
            if isinstance(item, dict):
                idx = item.get("fb_index", item.get("index", -1))
                if isinstance(idx, int) and 0 <= idx < len(chunk):
                    indexed[idx] = item
        for j in range(len(chunk)):
            if j not in indexed:
                raise ValueError(f"slim batch missing fb_index={j} ({len(indexed)}/{len(chunk)} returned)")
            out.append({"discipline": _extract_discipline(indexed[j])})
        done = min(i + len(chunk), len(fbs_data))
        print(f"   slim batch {i // batch_size + 1}/{(len(fbs_data) - 1) // batch_size + 1}: {done}/{len(fbs_data)} classified")
    return out


def _extract_discipline(entry: dict) -> str:
    """Pull the singular discipline string from a slim result entry."""
    disc = entry.get("discipline", "")
    if isinstance(disc, list):
        disc = disc[0] if disc else ""
    return str(disc) if disc else ""


def classify_fbs(fbs: list[dict], batch: bool, batch_size: int, model: str, slim: bool = False) -> list[tuple[dict, dict | None]]:
    """Re-classify each FB's discipline; returns (fb, result-or-None).

    slim=True (default) → discipline-only prompt (~1/30th the tokens, D2534).
    slim=False → full merged CRIBS+classification (slower, richer context).
    """
    if slim:
        slim_results = slim_batch_discipline_classify([_to_prompt_dict(fb) for fb in fbs], model, batch_size)
        return [(fb, r) for fb, r in zip(fbs, slim_results)]

    results: list[tuple[dict, dict | None]] = []
    t_start = time.time()
    if batch:
        for i in range(0, len(fbs), batch_size):
            chunk = fbs[i:i + batch_size]
            try:
                out = batch_cribs_classify([_to_prompt_dict(fb) for fb in chunk], model=model)
                results.extend(zip(chunk, out))
                done = min(i + len(chunk), len(fbs))
                print(f"   batch {i // batch_size + 1}/{(len(fbs) - 1) // batch_size + 1}: {done}/{len(fbs)} classified ({time.time() - t_start:.0f}s)")
            except Exception as e:  # C16: log AND keep going (serial fallback), never silent
                print(f"  ⚠️  batch chunk [{i}-{i + len(chunk)}) FAILED ({type(e).__name__}: {e}) — serial fallback", file=sys.stderr)
                for fb in chunk:
                    try:
                        out = merged_cribs_classify(_to_prompt_dict(fb), model=model)
                        results.append((fb, out))
                    except Exception as e2:
                        print(f"    ⚠️  FB {fb['fb_id']} FAILED ({type(e2).__name__}: {e2})", file=sys.stderr)
                        results.append((fb, None))
    else:
        for idx, fb in enumerate(fbs):
            try:
                out = merged_cribs_classify(_to_prompt_dict(fb), model=model)
                results.append((fb, out))
                if (idx + 1) % 20 == 0 or idx + 1 == len(fbs):
                    print(f"   {idx + 1}/{len(fbs)} classified ({time.time() - t_start:.0f}s)")
            except Exception as e:
                print(f"  ⚠️  FB {fb['fb_id']} FAILED ({type(e).__name__}: {e})", file=sys.stderr)
                results.append((fb, None))
    return results


def _backup_db(db_path: Path) -> Path:
    """C13: timestamped pre-write DB backup, size-verified + fsync'd (C6)."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = Path(str(db_path) + f".bak_{ts}_pre_reclassify")
    shutil.copy2(str(db_path), str(bak))
    with open(bak, "rb") as _f:  # C6: fsync so a crash can't leave a torn copy
        os.fsync(_f.fileno())
    if db_path.stat().st_size != bak.stat().st_size:
        raise RuntimeError(f"backup size mismatch — aborting write")
    print(f"  🔒 Backup: {bak} ({bak.stat().st_size:,} bytes)")
    return bak


def _integrity_gate(db_path: Path) -> None:
    """C13: refuse to write if quick_check or foreign_key_check fails."""
    conn = sqlite3.connect(str(db_path))
    try:
        qc = conn.execute("PRAGMA quick_check").fetchone()[0]
        fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        conn.close()
    if qc != "ok":
        raise RuntimeError(f"integrity gate FAILED (quick_check={qc}) — aborting write")
    if fk:
        raise RuntimeError(f"integrity gate FAILED ({len(fk)} foreign_key violations) — aborting write")
    print("  ✅ Integrity gate: quick_check ok, foreign_key_check clean")


def _apply_updates(db_path: Path, updates: list[dict]) -> int:
    """C6: single atomic transaction for all resolved-discipline writes.

    Only discipline / discipline_raw / taxonomy_match_method are updated — domains
    and every other committed field are untouched.
    """
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("BEGIN IMMEDIATE")
        for u in updates:
            conn.execute(
                "UPDATE fbs SET discipline=?, discipline_raw=?, taxonomy_match_method=? WHERE fb_id=?",
                (u["discipline"], u["discipline_raw"], u["taxonomy_match_method"], u["fb_id"]),
            )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return len(updates)


def _sync_checkpoints() -> None:
    """Blindspot fix (D2533): re-sync S4/S5 checkpoints after DB mutation.

    The reclassification mutates maxwell.db directly, which (D2519/D2520) leaves
    stage4_merge/t11/checkpoint_enriched.jsonl + stage5_verify/t11/checkpoint.jsonl
    STALE. Running the proven sync scripts propagates the DB's taxonomy fields back
    into the checkpoints so no downstream re-run reads pre-reclassification labels.
    """
    scripts = [
        _PROJECT_ROOT / "scripts" / "sync_checkpoint_from_db.py",
        _PROJECT_ROOT / "scripts" / "sync_s5_checkpoint_from_db.py",
    ]
    for s in scripts:
        if not s.exists():
            print(f"  ⚠️  sync script missing: {s.name} — checkpoint NOT re-synced", file=sys.stderr)
            continue
        print(f"  🔄 Re-syncing checkpoint: {s.name} ...")
        try:
            r = subprocess.run(
                [sys.executable, str(s)],
                cwd=str(_PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=1800,
            )
        except Exception as e:  # C16: fail-loud
            print(f"  ⚠️  {s.name} FAILED ({type(e).__name__}: {e})", file=sys.stderr)
            continue
        if r.returncode != 0:
            print(f"  ⚠️  {s.name} FAILED (rc={r.returncode}): {r.stderr[-400:]}", file=sys.stderr)
        else:
            print(f"  ✅ {s.name} re-synced")


def _append_harvest(path: Path, entries: list[dict]) -> None:
    """Crash-safe APPEND of harvest entries (C6: fsync before returning).

    Appends (never overwrites) so each checkpoint chunk's corrected raw labels
    accumulate. A duplicate entry on a crash-retry is harmless — the BUG-150
    consumer dedups by fb_id.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def _process_batch(chunk: list[dict], results: list[tuple[dict, dict | None]],
                   synonym_index: dict[str, str]) -> tuple[list[dict], list[dict], dict]:
    """Compute DB updates + harvest entries for one classified chunk.

    Returns (updates, harvest_entries, stats). Mirrors the D2532/D2540 remap rules:
    resolve emerging → real canonical discipline; else if unresolved and the LLM
    emitted a domain, use that as the raw label (D2540: precise for the follow-up
    kind-swap); else leave as-is (genuine taxonomy gap → BUG-150).
    """
    updates: list[dict] = []
    harvest: list[dict] = []
    resolved = raw_fixed = still_emerging = failed = 0
    samples: list[str] = []
    for fb, result in results:
        if result is None:
            failed += 1
            continue
        canonical, raw, match = remap_discipline(result, synonym_index)
        if canonical == "emerging" and isinstance(result, dict):
            doms = result.get("domains") or []
            if isinstance(doms, list) and doms and str(doms[0]).strip():
                raw = str(doms[0]).strip()
        old_disc = fb["discipline"]
        old_raw = fb.get("discipline_raw") or ""
        harvest.append({
            "fb_id": fb["fb_id"],
            "name": fb["name"],
            "old_discipline_raw": old_raw,
            "new_discipline_raw": raw,
            "canonical_discipline": canonical,
            "taxonomy_match_method": match,
        })
        changed = (canonical != old_disc) or (raw != old_raw)
        if changed:
            updates.append({
                "fb_id": fb["fb_id"],
                "discipline": canonical,
                "discipline_raw": raw,
                "taxonomy_match_method": match,
            })
            if old_disc == "emerging" and canonical != "emerging":
                resolved += 1
                if len(samples) < 10:
                    samples.append(f"  {fb['fb_id'][:16]}  {old_disc!r} → {canonical!r} (raw={raw!r})")
            elif canonical == "emerging":
                raw_fixed += 1
                if len(samples) < 10:
                    samples.append(f"  {fb['fb_id'][:16]}  raw {old_raw!r} → {raw!r} (still emerging)")
        if canonical == "emerging" and raw == old_raw:
            still_emerging += 1
    return updates, harvest, {
        "resolved": resolved, "raw_fixed": raw_fixed,
        "still_emerging": still_emerging, "failed": failed, "samples": samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="BUG-197 targeted merged-axis DISCIPLINE re-classification (D2532)")
    parser.add_argument("--db", default=str(DB_PATH), help="Path to maxwell.db (default from config)")
    parser.add_argument("--where", default=DEFAULT_WHERE, help="SQL predicate selecting affected FBs")
    parser.add_argument("--limit", type=int, default=None, help="Cap rows (A/B sample); deterministic ORDER BY fb_id")
    parser.add_argument("--batch", dest="batch", action="store_true", default=None, help="Force batch mode")
    parser.add_argument("--slim", dest="slim", action="store_true", default=False, help="Discipline-only prompt (D2534; ~2x faster, experimental)")
    parser.add_argument("--no-slim", dest="slim", action="store_false", help="Full merged CRIBS+classification (slow)")
    parser.add_argument("--no-batch", dest="batch", action="store_false", help="Force sequential (merged-call) mode")
    parser.add_argument("--batch-size", type=int, default=None, help="Batch chunk size (default stage4.batch_size)")
    parser.add_argument("--model", default=None, help="Classifier model (default VERIFY_MODEL)")
    parser.add_argument("--apply", action="store_true", help="Write resolved disciplines to DB (backup + integrity gate)")
    parser.add_argument("--harvest", default=None, help="JSONL path for harvested raw labels (BUG-150 promotion input)")
    parser.add_argument("--sync", dest="sync", action="store_true", default=True, help="Re-sync S4/S5 checkpoints after apply (default; fixes DB↔checkpoint drift)")
    parser.add_argument("--no-sync", dest="sync", action="store_false", help="Skip checkpoint re-sync after apply")
    parser.add_argument("--chunk", type=int, default=CHUNK_SIZE_DEFAULT, help="FBs per atomic apply (checkpoint/resume granularity)")
    parser.add_argument("--skip-backup", action="store_true", help="DANGER: skip pre-write backup (dev only)")
    parser.add_argument("--skip-integrity", action="store_true", help="DANGER: skip integrity gate (dev only)")
    args = parser.parse_args()

    db_path = Path(args.db)
    batch_size = args.batch_size if args.batch_size is not None else int(_cfg_stage4("batch_size", BATCH_SIZE_DEFAULT))
    batch = args.batch if args.batch is not None else bool(_cfg_stage4("batch_enabled", False))
    model = args.model or VERIFY_MODEL

    fbs = load_affected(db_path, args.where, args.limit)
    if not fbs:
        print(f"⚠️  No FBs match `{args.where}` — nothing to do.")
        return 0

    chunk_size = max(1, args.chunk)
    mode = "BATCH" if batch else "SEQUENTIAL"
    print(f"🎯 D2532 discipline re-classification: {len(fbs)} FBs | mode={mode} | batch_size={batch_size} | chunk={chunk_size} | model={model}")
    print(f"   where: {args.where}")

    # D2534: unbuffered stdout so the backgrounded run's log is tail-able in real time.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception as e:  # C16: fail-loud, never silently swallow
        print(f"  ⚠️  stdout.reconfigure failed ({type(e).__name__}: {e}) — progress log will be buffered", file=sys.stderr)

    synonym_index = get_synonym_index()

    # C13: backup + integrity gate ONCE, before the first write (not per chunk).
    if args.apply and not args.skip_backup:
        _backup_db(db_path)
    elif args.apply:
        print("  ⚠️  --skip-backup: proceeding WITHOUT a pre-write backup (dev only)")
    if args.apply and not args.skip_integrity:
        _integrity_gate(db_path)
    elif args.apply:
        print("  ⚠️  --skip-integrity: proceeding WITHOUT integrity gate (dev only)")

    harvest_path = Path(args.harvest) if args.harvest else None
    t0 = time.time()
    n_chunks = (len(fbs) + chunk_size - 1) // chunk_size
    total_updates = 0
    total_resolved = total_raw_fixed = total_still = total_failed = 0
    all_samples: list[str] = []

    # D2533 resume: process in checkpoint chunks. Each chunk is classified, its
    # harvest appended (crash-safe), then applied ATOMICALLY. A crash mid-run loses
    # at most one chunk; re-running the same --where skips already-applied FBs
    # (their discipline changed OR discipline_raw filled), so resume is automatic.
    for ci in range(n_chunks):
        chunk = fbs[ci * chunk_size:(ci + 1) * chunk_size]
        results = classify_fbs(chunk, batch, batch_size, model, slim=args.slim)
        updates, harvest, stats = _process_batch(chunk, results, synonym_index)
        total_updates += len(updates)
        total_resolved += stats["resolved"]
        total_raw_fixed += stats["raw_fixed"]
        total_still += stats["still_emerging"]
        total_failed += stats["failed"]
        all_samples.extend(stats["samples"])
        if harvest_path and harvest:
            _append_harvest(harvest_path, harvest)
        if args.apply and updates:
            _apply_updates(db_path, updates)
        done = min((ci + 1) * chunk_size, len(fbs))
        print(f"   chunk {ci + 1}/{n_chunks}: {done}/{len(fbs)} classified | +{len(updates)} applied | {time.time() - t0:.0f}s elapsed")

    elapsed = time.time() - t0
    n_ok = len(fbs) - total_failed
    print(f"\n📊 RESULTS ({mode}, {elapsed:.1f}s, {elapsed / max(n_ok, 1):.1f}s/FB successful):")
    print(f"   classified: {n_ok}/{len(fbs)}  failed: {total_failed}")
    print(f"   RESOLVED (emerging → real canonical discipline): {total_resolved}")
    print(f"   raw-corrected (still emerging, raw label repaired): {total_raw_fixed}")
    print(f"   still emerging + unchanged (genuine taxonomy gap → BUG-150): {total_still}")
    print(f"   DB rows written: {total_updates}")
    for s in all_samples[:10]:
        print(s)

    if harvest_path:
        print(f"\n🌾 Harvested corrected raw disciplines → {harvest_path} (BUG-150 promotion input)")

    if total_updates == 0:
        print("\n✅ No discipline/raw changes — nothing to write.")
        return 0

    if not args.apply:
        print(f"\n🔍 DRY-RUN — no writes. Re-run with --apply to persist {total_updates} resolved disciplines.")
        return 0

    print(f"\n✅ Applied {total_updates} resolved disciplines to {db_path}.")
    if args.sync:
        _sync_checkpoints()
    else:
        print("   ⚠️  --no-sync: checkpoints NOT re-synced (manual: scripts/sync_checkpoint_from_db.py + sync_s5_checkpoint_from_db.py)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
