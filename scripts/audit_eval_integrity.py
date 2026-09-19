#!/usr/bin/env python3
"""audit_eval_integrity.py — the anchor must be evaluable, and must not be trainable-on.

TWO INVARIANTS (config/eval_integrity.yaml), both derived from the 2026-09-17 audit:

1. DISJOINTNESS (fail). The eval anchor must not overlap the fine-tune/training pool. Verified
   0/1027 today; if it ever becomes non-zero, every model comparison silently becomes a
   memorisation test. Compared by 40-char shingle overlap (the anchor stores no free text, so the
   row bodies are pulled from the runtime DB).

2. HUMAN SHARE PER AXIS (warn). An axis whose labels were produced by the model being evaluated
   cannot measure that model. Measured 2026-09-17:

       content_type  0.116 human   <- 222 model-voted, 20 from ONE model, 48% flip on re-sweep
       discipline    0.347 human   <- 164 produced by the reliable pair, then that pair is scored
                                      against them (0.709 overall / 0.437 on the 87 contested)
       depth         0.526 human
       domains       0.920 human
       extraction_type  no anchor at all

   So the two axes with the weakest provenance are the two the pipeline's LLM roles are selected
   against. The floors live in ONE place - `config/eval_integrity.yaml` - and are never restated
   here, so documentation cannot drift from the gate. They gate the ModernBERT retrain and any
   ensemble/model-selection claim; they do not block reading the other axes.
   `--strict` makes an unmet floor exit non-zero so a WARN-severity criterion can surface it.

BUG-267 / F-16 (2026-09-17, found while answering the operator's clarification query): the
tier classifier was a SUBSTRING test and the vocabulary could not distinguish "human decided"
from "human ratified a model's proposal" (kimi/deepseek/claude were used for part of the work
recorded as `p5:human-*`). Both figures are therefore reported:

    <axis>=<blind> blind / <attested> attested (floor ...)

`blind` (tier `human-blind`) counts only decisions made without seeing a model proposal; it is
0.000 everywhere today, which is the honest number. The floor is measured against `attested` so
the gate does not fire on a taxonomy change; the blind figure is the destination and is printed
every run so it cannot be forgotten.

Exit 0 = disjoint AND every floor met. Exit 1 = violation (currently: floors unmet on
content_type + discipline + extraction_type).
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
CFG = REPO / "config" / "eval_integrity.yaml"
DB = REPO / "knowledge pipeline" / "maxwell.db"
AXES = ("content_type", "depth", "discipline", "domains", "extraction_type")


def _cfg() -> dict[str, Any]:
    """Load the integrity config (C12: every floor and path is config-driven)."""
    import yaml

    return yaml.safe_load(CFG.read_text())


def _norm(text: str) -> str:
    """Lowercase and strip non-word characters so formatting cannot hide an overlap."""
    return re.sub(r"\W+", "", (text or "").lower())


def _shingles(text: str, size: int) -> set[str]:
    """Return fixed-size character shingles for overlap comparison.

    blake2b, not md5 — R5 review 2026-09-17 flagged md5 (broken cryptographic hash). Collision
    resistance is not the requirement here, but there is no reason to carry a flagged primitive.
    Memory: the anchor (251 rows) and the train pool (1027 examples) are small and bounded; the
    shingle sets are the only large objects and they are released per example.
    """
    import hashlib

    body = _norm(text)
    if len(body) <= size * 2:
        return set()
    return {
        hashlib.blake2b(body[i:i + size].encode(), digest_size=16).hexdigest()
        for i in range(0, len(body) - size, size)
    }


def _tier_map() -> dict[str, str]:
    """Return {source -> tier} from `provenance_tiers` in config (C12: never hardcode).

    BUG-267/F-16 (2026-09-17): this replaced a SUBSTRING test (`"human" in source`) that
    classified `p5:human-frontier69` as HUMAN although its name asserts a frontier component,
    and made the FRONTIER branch unreachable dead code. Exact match only — an unlisted source
    is reported as UNKNOWN and fails the check closed, so a new provenance source cannot be
    silently absorbed into the wrong bucket.
    """
    tiers = (_cfg().get("provenance_tiers") or {})
    return {str(src).lower(): str(tier) for tier, srcs in tiers.items() for src in (srcs or [])}


def _tier(source: Any, mapping: dict[str, str]) -> str:
    """Classify one provenance source into its declared tier, or UNKNOWN if unregistered."""
    text = str(source or "").strip().lower()
    if text in ("", "none", "null"):
        return "NONE"
    return mapping.get(text, "UNKNOWN")


def check_disjoint(anchor: dict[str, Any], pool: Path) -> tuple[int, str]:
    """Return (status, detail); status 1 = the anchor and the train pool overlap."""
    import yaml

    limit = int(anchor.get("max_train_eval_overlap", 0))
    size = int(anchor.get("overlap_shingle_chars", 40))
    share = float(anchor.get("overlap_shingle_share", 0.4))
    anchor_path = REPO / str(anchor["file"])
    if not anchor_path.exists():
        return 1, "anchor file missing: " + str(anchor_path) + " (cannot verify disjointness)"
    gold = [json.loads(line) for line in anchor_path.read_text().splitlines() if line.strip()]
    if not pool.exists():
        # Fail closed: an absent train pool means disjointness was NOT verified. Reporting OK here
        # is the exact silent-pass class this project keeps paying for (R5 round 4, 2026-09-17).
        return 1, "train pool absent (" + pool.name + ") — disjointness NOT verified"
    try:
        data = yaml.safe_load(pool.read_text())
    except Exception as exc:
        return 1, "cannot read train pool: " + type(exc).__name__
    examples = data.get("examples", data) if isinstance(data, dict) else data
    if not isinstance(examples, list):
        return 1, "train pool has no example list"

    if not DB.exists():
        # sqlite3.connect() would CREATE an empty file and the failure would surface later as a
        # confusing "no such table" — fail closed on the missing runtime KB instead (R5 2026-09-17).
        return 1, "runtime DB missing: " + str(DB) + " (cannot resolve anchor row text)"
    con = sqlite3.connect(str(DB))
    if not con.execute(
        "select name from sqlite_master where type='table' and name='fbs'"
    ).fetchone():
        con.close()
        return 1, "runtime DB has no fbs table: " + str(DB)
    universe: set[str] = set()
    for row in gold:
        got = con.execute(
            "select definition, application, source_text from fbs where fb_id = ?", (row.get("fb_id"),)
        ).fetchone()
        if got:
            universe |= _shingles(" ".join(str(x) for x in got if x), size)
    con.close()

    hits = 0
    for example in examples:
        if not isinstance(example, dict):
            continue
        body = example.get("input_fb")
        text = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
        sh = _shingles(text, size)
        if sh and len(sh & universe) / len(sh) > share:
            hits += 1
    status = 1 if hits > limit else 0
    return status, ("train-pool examples overlapping the anchor: " + str(hits) + " / " + str(len(examples))
                    + " (limit " + str(limit) + ")")


def check_floors(floors: dict[str, float]) -> tuple[int, str]:
    """Return (status, detail) for the per-axis human-share floors."""
    anchor_path = REPO / "governance" / "gold_4axis.jsonl"
    if not anchor_path.exists():
        return 1, "anchor file missing: " + str(anchor_path)
    gold = [json.loads(line) for line in anchor_path.read_text().splitlines() if line.strip()]
    if not gold:
        return 1, "anchor file is empty: " + str(anchor_path)
    target = len(gold)
    mapping = _tier_map()
    share = (_cfg().get("human_share") or {})
    strict_set = {str(x).lower() for x in (share.get("count_strict") or ["human-blind"])}
    lenient_set = {str(x).lower() for x in (share.get("count_lenient") or ["human-blind", "human-attested"])}
    unmet: list[str] = []
    lines: list[str] = []
    unknown: collections.Counter[str] = collections.Counter()
    for axis, floor in floors.items():
        if axis == "extraction_type":
            lines.append(axis + "=0.000 (no anchor)")
            unmet.append(axis)
            continue
        tiers = collections.Counter(_tier(row.get(axis + "_source"), mapping) for row in gold)
        tiers.pop("NA", None)  # a documented not-applicable sentinel is not a label
        for bad in ("UNKNOWN", "NONE"):
            if tiers.get(bad):
                unknown[axis + ":" + bad] += tiers[bad]
        blind = sum(v for k, v in tiers.items() if k in strict_set) / target
        have = sum(v for k, v in tiers.items() if k in lenient_set) / target
        lines.append(axis + "=" + ("%.3f" % blind) + " blind / " + ("%.3f" % have)
                     + " attested (floor " + str(floor) + ")")
        if have < float(floor):
            unmet.append(axis)
    detail = " | ".join(lines)
    if unknown:
        # Fail closed: an unregistered provenance source means the floor is measured against an
        # unknown bucket. Never silently OK (BUG-267).
        detail += " || UNREGISTERED PROVENANCE: " + ",".join(
            k + "x" + str(v) for k, v in sorted(unknown.items()))
        return 1, detail
    return (1 if unmet else 0), detail + (" || UNMET: " + ",".join(unmet) if unmet else "")


def main() -> int:
    """Run both invariants and report; disjointness is blocking, floors are advisory."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", choices=("all", "disjoint", "floors"), default="all")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero on unmet floors too (so a WARN-severity criterion can see it)")
    args = ap.parse_args()

    cfg = _cfg()
    anchor = cfg.get("anchor", {})
    pool = REPO / str(anchor.get("train_pool", ""))
    status_d, detail_d = (0, "skipped")
    status_f, detail_f = (0, "skipped")
    if args.only in ("all", "disjoint"):
        status_d, detail_d = check_disjoint(anchor, pool)
    if args.only in ("all", "floors"):
        status_f, detail_f = check_floors(cfg.get("min_human_share", {}))

    print("anchor integrity")
    print("  DISJOINTNESS " + ("FAIL" if status_d else "ok  ") + " " + detail_d)
    print("  HUMAN SHARE  " + ("WARN" if status_f else "ok  ") + " " + detail_f)
    if status_d:
        print("DRIFT: the eval anchor overlaps the training pool — the evaluation is a memorisation test")
        return 1
    if status_f:
        print("WARN: per-axis human share below the floor — the retrain/selection gate is not met")
        if args.strict:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
