"""
adjudicate_reanchor_two_model.py — two-family agreement router for the T-191 re-anchor.

Authority: D-3116 (T-191 re-anchor), R5 (generator != verifier), D-2658 (bridge never
guesses), config/agreement_floor.yaml (agree -> accept, disagree -> human).

WHAT IT DOES
  For each of the 195 dangling ruler names in the triage sheet, two DIFFERENT model
  families (gemma-4-E4B + gpt-oss-20b) each read the top candidate store rows'
  (name, definition, mechanism, boundary, consequence, source_text, evidence_passages,
  source_authors, source_books) and independently verdict
  MATCH(fb_id) | NONE. The two verdicts are merged into a bucket:
      AUTO-NONE   both NONE and content_cos < none_guardrail_cos  -> owner SKIPS
      NONE-MUDDY  both NONE but content_cos >= none_guardrail_cos -> owner glances (cosine disagrees)
      SAME        both MATCH the same fb_id                       -> owner glances (becomes an anchor)
      SPLIT       one MATCH / one NONE                            -> owner reads
      CONFLICT    both MATCH different fb_ids                     -> owner reads
      ERROR       a judge failed                                  -> owner reads (retry)

  ADVISORY ONLY (D-2658): it NEVER writes owner_ruling_fb_id. The cosine guardrail is a
  THIRD, non-LLM signal whose errors are decorrelated from the LLMs', so a false-NONE
  (a lost concept) cannot be certified by two LLMs alone.

  temp=0.0 is enforced by pipeline.omlx_call (R7). Every call is appended to a raw JSONL
  receipt (D-3036). Resumable: completed (item_id, model) pairs are skipped.

USAGE
  python3 scripts/adjudicate_reanchor_two_model.py --limit 2   # selftest (2 rows)
  python3 scripts/adjudicate_reanchor_two_model.py             # full 195x2 run
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.omlx_call import call_omlx_json

CONFIG_PATH = ROOT / "config" / "anchor_family.yaml"

_PROMPT = """Classify whether a concept label is the SAME concept as one candidate knowledge row, or NONE of them.

RULER NAME (concept to find): {ruler}

{candidates}

Synonyms/paraphrase = SAME concept. A near-name match that is actually a DIFFERENT concept
(e.g. "Revenue Model" vs "Value Proposition") = NONE.

Reply JSON only:
{{"verdict":"MATCH"|"NONE","fb_id":"<matching candidate fb_id, or empty string>","confidence":0.0-1.0,"reason":"one short sentence"}}"""


def _trunc(s: str, n: int) -> str:
    s = (s or "").strip().replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def _candidate_block(cands: list[dict]) -> str:
    blocks: list[str] = []
    for i, c in enumerate(cands, 1):
        lines = [
            f"CANDIDATE {i} (fb_id: {c['fb_id']}):",
            f"- name: {_trunc(c.get('name'), 220)}",
            f"- definition: {_trunc(c.get('definition'), 400)}",
            f"- mechanism: {_trunc(c.get('mechanism'), 220)}",
            f"- boundary: {_trunc(c.get('boundary'), 220)}",
            f"- consequence: {_trunc(c.get('consequence'), 220)}",
            f"- source_text: {_trunc(c.get('source_text'), 300)}",
            f"- evidence_passages: {_trunc(c.get('evidence_passages'), 300)}",
            f"- source_authors: {_trunc(c.get('source_authors'), 200)}",
            f"- source_books: {_trunc(c.get('source_books'), 200)}",
        ]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _norm_verdict(v: object) -> dict | None:
    if not isinstance(v, dict):
        return None
    verdict = str(v.get("verdict", "")).strip().upper()
    if verdict.startswith("MATCH") or verdict.startswith("SAME") or verdict == "YES":
        verdict = "MATCH"
    elif verdict.startswith("NONE") or verdict == "NO":
        verdict = "NONE"
    else:
        return None
    fb_id = str(v.get("fb_id", "") or "").strip()
    try:
        confidence = float(v.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    reason = str(v.get("reason", "")).strip()
    if verdict == "MATCH" and not fb_id:
        return None  # MATCH must name the row it matched
    return {"verdict": verdict, "fb_id": fb_id, "confidence": confidence, "reason": reason}


def _ask(ruler: str, cands: list[dict], model: str) -> dict:
    prompt = _PROMPT.format(ruler=ruler, candidates=_candidate_block(cands))
    result = call_omlx_json(prompt, model=model)
    norm = _norm_verdict(result)
    if norm is None:
        return {"ok": False, "error": f"unparseable verdict: {str(result)[:200]}"}
    norm["ok"] = True
    return norm


def _bucket(row: dict, a: dict, b: dict) -> str:
    ok = a.get("ok") and b.get("ok")
    if not ok:
        return "ERROR"
    va, vb = a["verdict"], b["verdict"]
    if va == "NONE" and vb == "NONE":
        try:
            cos = float(row["content_cos"])
        except (TypeError, ValueError):
            cos = 0.0
        guard = row["_guardrail"]
        return "AUTO-NONE" if cos < guard else "NONE-MUDDY"
    if va == "MATCH" and vb == "MATCH":
        return "SAME" if a["fb_id"] == b["fb_id"] else "CONFLICT"
    return "SPLIT"


def _suggest(bucket: str, a: dict, b: dict, model_a: str = "", model_b: str = "") -> tuple[str, str]:
    if bucket == "SAME":
        return a["fb_id"], "both families agree MATCH"
    if bucket == "AUTO-NONE":
        return "NONE", "both families agree NONE + content_cos < guardrail"
    if bucket == "NONE-MUDDY":
        return "NONE?", "both families NONE but content_cos >= guardrail (cosine disagrees)"
    if bucket == "SPLIT":
        return "", f"SPLIT: {model_a}={a.get('verdict')} {model_b}={b.get('verdict')}"
    if bucket == "CONFLICT":
        return "", f"CONFLICT: {model_a}->{a.get('fb_id','')[:12]} {model_b}->{b.get('fb_id','')[:12]}"
    return "", f"ERROR: {a.get('error') or b.get('error')}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="adjudicate only the first N rows (selftest)")
    ap.add_argument("--workers", type=int, default=None, help="override max_workers")
    ap.add_argument("--models", nargs="+", default=None, help="override the two model families (space-separated)")
    ap.add_argument("--items", default=None, help="comma-separated item_ids to adjudicate (default: all rows)")
    ap.add_argument("--out", default=None, help="override output CSV path (relative to repo root)")
    ap.add_argument("--raw", default=None, help="override raw JSONL receipt path (relative to repo root)")
    args = ap.parse_args()

    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    ac = cfg.get("reanchor_adjudication")
    if not ac:
        print("ERROR: missing reanchor_adjudication block in config/anchor_family.yaml", file=sys.stderr)
        return 3

    src = ROOT / ac["source_sheet"]
    cand_src = ROOT / ac["candidate_sheet"]
    out_path = ROOT / (args.out or ac["out"])
    raw_path = ROOT / (args.raw or ac["raw"])
    store = ROOT / ac["store"]
    fields = ac["fields"]
    models: list[str] = args.models or ac["models"]
    guard = float(ac["none_guardrail_cos"])
    max_candidates = int(ac["max_candidates"])
    workers = args.workers or int(ac["max_workers"])

    with src.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = [fn.strip() for fn in (reader.fieldnames or [])]
        rows = [{k.strip(): v for k, v in row.items()} for row in reader]

    # name-cos top-5 candidates per item_id (candidate sheet) — the breadth source
    # that fixes the never-shown retrieval bug (R208's true match was cand3).
    cand_by_id: dict[str, list[str]] = {}
    with cand_src.open(newline="", encoding="utf-8-sig") as f:
        for raw in csv.DictReader(f):
            c = {k.strip(): v for k, v in raw.items()}
            fbs: list[str] = []
            for i in range(1, 6):
                v = (c.get(f"cand{i}_fb_id") or "").strip()
                if v and v not in fbs:
                    fbs.append(v)
            cand_by_id[c["item_id"].strip()] = fbs

    if args.items:
        wanted = {s.strip() for s in args.items.split(",") if s.strip()}
        rows = [r for r in rows if r["item_id"] in wanted]
        missing = sorted(wanted - {r["item_id"] for r in rows})
        if missing:
            print(f"WARNING: {len(missing)} item_ids not in triage sheet: {missing}", file=sys.stderr)

    if args.limit:
        rows = rows[: args.limit]

    con = sqlite3.connect(str(store))
    con.row_factory = sqlite3.Row

    def fields_for(fb_id: str) -> dict:
        r = con.execute(
            f"SELECT {', '.join(fields)} FROM {ac['store_table']} WHERE {ac['store_key']}=?",
            (fb_id,),
        ).fetchone()
        return dict(r) if r else {}

    # candidate fb_ids per row: content-top first (more discriminative), then the
    # name-cos cand1..cand5, deduped, drop empties, cap at max_candidates.
    for row in rows:
        fbs: list[str] = []
        for v in (row.get("content_top_fb_id"), *cand_by_id.get(row["item_id"], [])):
            v = (v or "").strip()
            if v and v not in fbs:
                fbs.append(v)
        row["_cands"] = [{"fb_id": fb, **fields_for(fb)} for fb in fbs[:max_candidates]]
        row["_guardrail"] = guard

    # resume: skip (item_id, model) already completed in the raw receipt
    done: set[tuple[str, str]] = set()
    if raw_path.exists():
        with raw_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("item_id") and rec.get("model"):
                    done.add((rec["item_id"], rec["model"]))

    lock = threading.Lock()
    raw_fh = raw_path.open("a", encoding="utf-8")

    def run_one(item_id: str, ruler: str, cands: list[dict], model: str) -> tuple[tuple[str, str], dict]:
        rec = _ask(ruler, cands, model)
        line = {"item_id": item_id, "model": model, **rec}
        with lock:
            raw_fh.write(json.dumps(line, ensure_ascii=False) + "\n")
            raw_fh.flush()
        return (item_id, model), rec

    tasks = [
        (row["item_id"], row["ruler_name"], row["_cands"], model)
        for row in rows
        for model in models
        if (row["item_id"], model) not in done
    ]
    print(f"{len(tasks)} calls to run ({len(rows)} rows x {len(models)} models); {len(done)} already done")

    # reload completed results from raw so merges stay correct across resume
    results: dict[tuple[str, str], dict] = {}
    if raw_path.exists():
        with raw_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                results[(rec["item_id"], rec["model"])] = rec

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for key, rec in ex.map(lambda t: run_one(*t), tasks):
            results[key] = rec

    raw_fh.close()
    con.close()

    # merge per row
    out_rows: list[dict] = []
    counts: dict[str, int] = {}
    for row in rows:
        a = results.get((row["item_id"], models[0]))
        b = results.get((row["item_id"], models[1]))
        if a is None or b is None:
            a = a or {"ok": False, "error": "not run"}
            b = b or {"ok": False, "error": "not run"}
        bucket = _bucket(row, a, b)
        counts[bucket] = counts.get(bucket, 0) + 1
        sugg_fb, sugg_note = _suggest(bucket, a, b, models[0], models[1])
        out_rows.append({
            "bucket": bucket,
            "item_id": row["item_id"],
            "ruler_name": row["ruler_name"],
            "content_cos": row.get("content_cos", ""),
            "name_cos": row.get("name_cos", ""),
            "verdict_a": a.get("verdict", "ERR"),
            "fb_a": a.get("fb_id", ""),
            "conf_a": a.get("confidence", ""),
            "verdict_b": b.get("verdict", "ERR"),
            "fb_b": b.get("fb_id", ""),
            "conf_b": b.get("confidence", ""),
            "suggested_fb_id": sugg_fb,
            "suggested_note": sugg_note,
            "owner_ruling_fb_id": "",
            "owner_ruling_note": "",
        })

    order = {"ERROR": 0, "CONFLICT": 1, "SPLIT": 2, "NONE-MUDDY": 3, "SAME": 4, "AUTO-NONE": 5}
    out_rows.sort(key=lambda d: (order.get(d["bucket"], 9), d["item_id"]))

    cols = ["bucket", "item_id", "ruler_name", "content_cos", "name_cos",
            "verdict_a", "fb_a", "conf_a", "verdict_b", "fb_b", "conf_b",
            "suggested_fb_id", "suggested_note", "owner_ruling_fb_id", "owner_ruling_note"]
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(out_rows)
    tmp.replace(out_path)  # atomic (C6)

    print("\n=== ADJUDICATION SUMMARY ===")
    total = sum(counts.values())
    for k in sorted(counts, key=lambda x: order.get(x, 9)):
        print(f"  {k:12s} {counts[k]:4d}")
    print(f"  {'TOTAL':12s} {total:4d}")
    print(f"\nFull sheet: {out_path.relative_to(ROOT)}")
    print(f"Raw receipt: {raw_path.relative_to(ROOT)}")
    print("ADVISORY ONLY — owner_ruling_fb_id is still blank; the bridge never guesses (D-2658).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
