#!/usr/bin/env python3
"""build_boundary_corpus.py — D2594 / D2607 Tier3: grow the D2587 boundary
regression corpus from 9 seed cases toward ~150 (CHALLENGE, eval-only).

Mines the two near-boundary pools (D2589 mining_sources):
  * temp/p5_ct758_flags.csv       — 113 non-principle (74 GE + 19 PT highest value)
  * temp/p5_fewshot_manifest.json — 87 human-calibrated rows
dedups against the 9 existing seed cases, and appends each as a NEW case with the
OntoClean adjudication schema (latent dimensions null — to be filled by the
2-of-3 independent-adjudicator pass). This script is DETERMINISTIC scaffolding:
it does NOT adjudicate (that is a separate human/LLM 2-of-3 pass).

C6: atomic write (tempfile -> fsync -> os.replace). Dry-run by default; --apply
writes. Target ~150 total cases.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "config" / "golden" / "d2587_boundary_corpus.yaml"
GOLDEN = ROOT / "config" / "golden" / "stage4_golden_mined.yaml"
CSV_SRC = ROOT / "temp" / "p5_ct758_flags.csv"
JSON_SRC = ROOT / "temp" / "p5_fewshot_manifest.json"

TARGET_TOTAL = 150


def load_golden_lookup() -> Dict[str, Dict[str, str]]:
    """example_id -> {name, definition} from the mined golden set."""
    data = yaml.safe_load(GOLDEN.read_text(encoding="utf-8")) or {}
    out: Dict[str, Dict[str, str]] = {}
    for ex in data.get("examples", []):
        eid = ex.get("id")
        fb = ex.get("input_fb") or {}
        if eid and fb.get("name"):
            out[eid] = {"name": fb["name"], "definition": fb.get("definition", "")}
    return out


def mine_candidates(lookup: Dict[str, Dict[str, str]]) -> List[Dict[str, Any]]:
    """Return deduped candidate dicts {example_id, name, definition, content_type, source}."""
    seen: Dict[str, Dict[str, Any]] = {}

    # D2607: mine ONLY the non-principle pool — "principle" rows are already-correct
    # classifications, not near-boundary cases. The boundary corpus is adversarial
    # near-boundary only (GE/PT/TI/PI/noise = the flip-prone pool).
    SKIP = {"principle", ""}

    if CSV_SRC.exists():
        with CSV_SRC.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                eid = (row.get("example_id") or "").strip()
                if not eid or eid in seen:
                    continue
                ct = (row.get("ds_content_type") or "").strip() or (row.get("human_decision") or "").strip()
                if ct in SKIP:
                    continue
                g = lookup.get(eid)
                seen[eid] = {
                    "example_id": eid,
                    "name": g["name"] if g else (row.get("name") or eid),
                    "definition": g["definition"] if g else "",
                    "content_type": ct,
                    "source": "p5_ct758_flags.csv",
                }

    if JSON_SRC.exists():
        data = json.loads(JSON_SRC.read_text(encoding="utf-8"))
        for row in data:
            eid = (row.get("example_id") or "").strip()
            if not eid or eid in seen:
                continue
            ct = (row.get("content_type") or "").strip()
            if ct in SKIP:
                continue
            g = lookup.get(eid)
            seen[eid] = {
                "example_id": eid,
                "name": g["name"] if g else (row.get("name") or eid),
                "definition": g["definition"] if g else (row.get("definition") or ""),
                "content_type": ct,
                "source": "p5_fewshot_manifest.json",
            }

    return list(seen.values())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write the corpus (else dry-run)")
    ap.add_argument("--target", type=int, default=TARGET_TOTAL)
    args = ap.parse_args()

    corpus = yaml.safe_load(CORPUS.read_text(encoding="utf-8")) or {}
    existing = corpus.get("cases", [])
    existing_ids = {c.get("example_id") for c in existing if isinstance(c, dict)}
    print(f"existing cases: {len(existing)}")

    lookup = load_golden_lookup()
    candidates = [c for c in mine_candidates(lookup) if c["example_id"] not in existing_ids]
    print(f"mined candidates (post-dedup vs existing): {len(candidates)}")

    # Cap to target
    needed = max(0, args.target - len(existing))
    take = candidates[:needed]
    print(f"adding {len(take)} to reach target ~{args.target}")

    new_cases = []
    for c in take:
        new_cases.append({
            "example_id": c["example_id"],
            "name": c["name"],
            "definition": c["definition"],
            "source_content_type": c["content_type"],
            "sequence_present": None,
            "repeatable_method": None,
            "transferability": None,
            "epistemic_status": None,
            "disposition": None,
            "rationale": f"mined from {c['source']} (D2594 Tier3 scaffold); pending 2-of-3 adjudication",
        })

    print(f"resulting corpus size: {len(existing) + len(new_cases)}")
    if not args.apply:
        print("DRY-RUN — re-run with --apply to write.")
        for c in new_cases[:5]:
            print(f"  + {c['example_id']} [{c['source_content_type']}] {c['name'][:50]}")
        return 0

    corpus["cases"] = existing + new_cases
    corpus["tier"] = "CHALLENGE"
    corpus["_last_mined"] = "2026-09-09 (D2607 Tier3 scaffold)"

    # C6 atomic write
    fd, tmp = tempfile.mkstemp(dir=str(CORPUS.parent), suffix=".yaml")
    with os.fdopen(fd, "w") as f:
        yaml.safe_dump(corpus, f, sort_keys=False, default_flow_style=False,
                       allow_unicode=True, width=100)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, CORPUS)
    print(f"✅ wrote {len(existing) + len(new_cases)} cases to {CORPUS.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
