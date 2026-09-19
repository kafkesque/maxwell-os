#!/usr/bin/env python3
"""pipe_stage_probe.py — measure the model assigned to each LLM stage that was never benchmarked.

The consolidation draft assigned seven stages by inheritance (a model was in the config when the
stage was written; nobody measured it). These stages write PERSISTENT fields, so a wrong model
here corrupts data rather than a score. This probe measures the three that can be graded
objectively against real rows, on the model each stage is actually configured to use:

  s0_5_metadata   Phi-4-mini-instruct-8bit   extraction of author/title from an MD preamble.
                  Graded against the filename when the filename encodes "Title - Author.md",
                  which is an INDEPENDENT truth source (not the model's own cache).
  s2_relabel      gpt-oss-20b-MXFP4-Q8       cross-family re-judgment of extraction_type (FORM).
                  Graded on valid-label rate + agreement with the stored label. Agreement is
                  the point of the stage (it exists to undo single-source FORM drift, chi^2
                  ~2247 toward causal_mechanism).
  s4_5_skill      gpt-oss-20b-MXFPQ4-Q8      procedural_skill (one call per FB). Graded on
                  snake_case validity / clean declarative "" + agreement with the stored value
                  when the column exists.

NOT probed here (measured through their own CLIs, see scripts/queue_after_chain.sh):
  retrieval_eval  retrieval_evaluator.py    -> judges retrieved text; run its main().
  hyDE            retrieval_benchmark.py    -> recall@k/MRR A/B on config/golden/retrieval_queries.yaml.
  s3_summarizer   DOES NOT EXIST            -> phantom role, remove from model_assignments.yaml.
  dedup/suffix/alias "judges" DO NOT EXIST  -> dedup is deterministic (bge-m3 cosine >= threshold).
  s0_convert      no LLM                    -> pandoc/docling fidelity, unmeasured.

Resumable, append-only checkpoint (C6/R14). NEVER run this while another oMLX consumer is active:
a model switch evicts the single resident model (BUG-255).
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.stage0_5_extract_metadata import extract_from_text  # noqa: E402
from pipeline.stage2_relabel_extraction_type import EXTRACTION_TYPES, _judge  # noqa: E402
from pipeline.stage4_5_enrich import classify_procedural_skill  # noqa: E402

CKPT = ROOT / "governance" / "pipe_stage_probe_checkpoint.jsonl"
DB = ROOT / "knowledge pipeline" / "maxwell.db"
SNAKE = re.compile(r"^[a-z][a-z0-9_]{2,60}$")
FILENAME_PAIR = re.compile(r"^(?P<title>.+?)\s+-\s+(?P<author>.+?)$")

STAGE_MODEL = {
    "s0_5_metadata": "Phi-4-mini-instruct-8bit",
    "s2_relabel": "gpt-oss-20b-MXFP4-Q8",
    "s4_5_skill": "gpt-oss-20b-MXFP4-Q8",
}


def _prompt_texts() -> list[dict]:
    """Return S0.5 probe items: MD preambles with a filename that encodes title - author."""
    from pipeline.pipeline_paths import BOOKS_DIR  # config-driven, never hardcoded

    items: list[dict] = []
    for md in sorted(Path(BOOKS_DIR).rglob("*.md")):
        stem = md.stem
        m = FILENAME_PAIR.match(stem)
        if not m:
            continue
        try:
            head = md.read_text(encoding="utf-8", errors="replace")[:1500]
        except OSError:
            continue
        if len(head) < 200:
            continue
        items.append({"id": md.name, "filename": md.name, "text": head,
                      "truth_title": m.group("title").strip(),
                      "truth_author": m.group("author").strip()})
    return items


def _db_rows(limit: int) -> list[dict]:
    """Return FB rows carrying the fields the S2 relabel / S4_5 prompts need."""
    db = sqlite3.connect(DB)
    cols = {r[1] for r in db.execute("pragma table_info(fbs)")}
    want = [c for c in ("fb_id", "name", "definition", "mechanism", "boundary", "consequence",
                        "extraction_type", "procedural_skill") if c in cols]
    if "evidence_passages" in cols:
        want.append("evidence_passages")
    rows = db.execute(
        "select " + ",".join(want) + " from fbs where definition is not null "
        "and length(definition) > 200 limit ?", (limit,)).fetchall()
    db.close()
    return [dict(zip(want, r)) for r in rows]


def _norm(s: object) -> str:
    """Lowercase, collapse whitespace, strip punctuation edges — for title comparison."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", str(s or "").lower())).strip()


def measure_s0_5(items: list[dict], model: str) -> list[dict]:
    """Measure S0.5 metadata extraction against the filename-encoded truth."""
    out: list[dict] = []
    for it in items:
        t0 = time.time()
        row = {"stage": "s0_5_metadata", "model": model, "id": it["id"]}
        try:
            res = extract_from_text(it["text"], it["filename"], model)
            row["secs"] = round(time.time() - t0, 2)
            if not isinstance(res, dict):
                row.update({"ok": False, "err": "non_dict_result: " + str(type(res).__name__)})
            else:
                title, author = str(res.get("title") or ""), str(res.get("author") or "")
                t_norm, a_norm = _norm(title), _norm(author)
                left, right = _norm(it["truth_title"]), _norm(it["truth_author"])
                # The filename convention is not guaranteed: some files are "Author - Title".
                # So the primary metric is pair_hit — the model found the right two strings,
                # possibly swapped — and title_side reports the documented left-hand convention.
                pair_hit = int(bool(t_norm and a_norm) and
                               ((t_norm in left or left in t_norm) and (a_norm in right or right in a_norm)
                                or (t_norm in right or right in t_norm) and (a_norm in left or left in a_norm)))
                row.update({
                    "ok": bool(title.strip() and author.strip()),
                    "pred_title": title[:120], "pred_author": author[:80],
                    "title_side": int(bool(t_norm) and (t_norm in left or left in t_norm)),
                    "pair_hit": pair_hit,
                    "err": None,
                })
        except Exception as exc:  # noqa: BLE001 — fail-closed, record and continue
            row.update({"secs": round(time.time() - t0, 2), "ok": False,
                        "err": type(exc).__name__ + ": " + str(exc)[:120]})
        out.append(row)
    return out


def measure_s2_relabel(rows: list[dict], model: str) -> list[dict]:
    """Measure the cross-family FORM re-judgment against the stored extraction_type."""
    out: list[dict] = []
    for r in rows:
        t0 = time.time()
        row = {"stage": "s2_relabel", "model": model, "id": r["fb_id"]}
        try:
            label = _judge(r, model=model)
            row["secs"] = round(time.time() - t0, 2)
            stored = str(r.get("extraction_type") or "").strip().lower()
            row.update({"pred": str(label)[:60], "stored": stored,
                        "ok": bool(str(label).strip()) and str(label).strip().lower() in
                              {t.lower() for t in EXTRACTION_TYPES},
                        "agrees": int(bool(label) and str(label).strip().lower() == stored),
                        "err": None})
        except Exception as exc:  # noqa: BLE001
            row.update({"secs": round(time.time() - t0, 2), "ok": False, "agrees": 0,
                        "err": type(exc).__name__ + ": " + str(exc)[:120]})
        out.append(row)
    return out


def measure_s4_5(rows: list[dict], model: str) -> list[dict]:
    """Measure a stage with no prior benchmark at all: S4_5 procedural_skill."""
    out: list[dict] = []
    for r in rows:
        t0 = time.time()
        row = {"stage": "s4_5_skill", "model": model, "id": r["fb_id"]}
        try:
            skill = classify_procedural_skill(dict(r), model=model)
            row["secs"] = round(time.time() - t0, 2)
            stored = str(r.get("procedural_skill") or "").strip()
            s = str(skill or "").strip()
            row.update({
                "pred": s[:60] or "(declarative)",
                "ok": s == "" or bool(SNAKE.match(s)),          # "" = correctly declarative
                "declarative": int(s == ""),
                "snake_case": int(bool(s) and bool(SNAKE.match(s))),
                "agrees": int(s == stored) if "procedural_skill" in r else None,
                "err": None,
            })
        except Exception as exc:  # noqa: BLE001
            row.update({"secs": round(time.time() - t0, 2), "ok": False, "snake_case": 0,
                        "declarative": 0, "err": type(exc).__name__ + ": " + str(exc)[:120]})
        out.append(row)
    return out


def done_keys() -> set[tuple[str, str, str]]:
    """(stage, model, id) triples already measured; transport errors are retried."""
    keys: set[tuple[str, str, str]] = set()
    if not CKPT.exists():
        return keys
    for line in CKPT.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("err"):
            continue
        keys.add((str(d.get("stage")), str(d.get("model")), str(d.get("id"))))
    return keys


def append(rows: list[dict]) -> None:
    """Append rows to the checkpoint (crash-safe append, one write per row)."""
    with CKPT.open("a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + chr(10))


def report() -> None:
    """Print the per-stage scoreboard from the checkpoint."""
    if not CKPT.exists():
        print("no checkpoint yet")
        return
    rows = [json.loads(l) for l in CKPT.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
    print()
    print("STAGE PROBE — assigned model vs measured behaviour")
    print("-" * 96)
    for stage in ("s0_5_metadata", "s2_relabel", "s4_5_skill"):
        rs = [r for r in rows if r.get("stage") == stage]
        if not rs:
            continue
        ok = [r for r in rs if not r.get("err")]
        med = statistics.median(r["secs"] for r in rs if r.get("secs")) if rs else 0.0
        line = (f"  {stage:15s} {str(rs[0].get('model'))[:30]:32s} n={len(rs):3d} "
                f"valid={len(ok)/len(rs):5.2f} med={med:6.1f}s")
        if stage == "s0_5_metadata" and ok:
            line += (f"  pair_hit={statistics.mean(r['pair_hit'] for r in ok):.2f}"
                     f" title_side={statistics.mean(r['title_side'] for r in ok):.2f}")
        if stage == "s2_relabel" and ok:
            line += f"  agrees_with_stored={statistics.mean(r['agrees'] for r in ok):.2f}"
        if stage == "s4_5_skill" and ok:
            line += (f"  snake_case={statistics.mean(r['snake_case'] for r in ok):.2f}"
                     f" declarative={statistics.mean(r['declarative'] for r in ok):.2f}")
        print(line)
        errs = [r for r in rs if r.get("err")]
        if errs:
            print(f"      errors: {len(errs)} — e.g. {str(errs[0].get('err'))[:90]}")
    print("-" * 96)
    print("  NOTE: run this ONLY with no other oMLX consumer active (BUG-255: a model switch")
    print("  evicts the single resident model and wedges the other client).")


def main() -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", nargs="*", default=["s0_5_metadata", "s2_relabel", "s4_5_skill"])
    ap.add_argument("--limit", type=int, default=12, help="items per stage")
    ap.add_argument("--report", action="store_true", help="print the scoreboard and exit")
    args = ap.parse_args()

    if args.report:
        report()
        return 0

    done = done_keys()
    for stage in args.stages:
        model = STAGE_MODEL[stage]
        if stage == "s0_5_metadata":
            items = [i for i in _prompt_texts()[:args.limit] if (stage, model, i["id"]) not in done]
            todo = [i for i in items]
            if todo:
                print(f"== {stage} ({model}): {len(todo)} to do", flush=True)
                append(measure_s0_5(todo, model))
        else:
            rows = [r for r in _db_rows(2000) if (stage, model, r["fb_id"]) not in done][:args.limit]
            if rows:
                print(f"== {stage} ({model}): {len(rows)} to do", flush=True)
                append(measure_s2_relabel(rows, model) if stage == "s2_relabel"
                       else measure_s4_5(rows, model))
    report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
