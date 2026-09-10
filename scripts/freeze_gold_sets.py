#!/usr/bin/env python3
"""scripts/freeze_gold_sets.py — D2585 P5 Step 4 (GOLD-A/B/CHALLENGE freeze).

Partitions the golden training pool into stratified, book/author-disjoint
tiers for the frozen evaluation protocol:

  CHALLENGE  -> held-out TEST  (feeds GOLDEN_TEST_IDS in train_discipline_classifier)
  GOLD-B     -> DEV  (hyper-parameters; never trained on)
  GOLD-A     -> human-confirmed labels, safe to TRAIN on
  (rest)     -> the remaining training pool

Selection policy (v1 skeleton — refine after human adjudication):
  - Stratified across disciplines (per-class quota, min floor so the train pool
    keeps >= MIN_EXAMPLES_PER_CLASS per class).
  - Book/author-disjointness is GREEDY: CHALLENGE/GOLD-B candidates are picked
    by ascending book-share (books shared by fewest golden examples first), then
    ascending author-share, to minimise train/test provenance leakage. Residual
    overlap is MEASURED and reported honestly (never silently claimed clean).
  - Adjudication overrides (temp/p5_human_adjudication.jsonl) are applied to
    discipline/domains when present.

Read-only w.r.t. DB. Writes config/golden/gold_frozen.yaml (all examples, each
with a ``tier`` field) + governance/gold_freeze_report.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import yaml  # noqa: E402

from pipeline.schemas import CANONICAL_DISCIPLINES  # noqa: E402

_GOV_DIR = _ROOT / "governance"
_MIN_PER_CLASS = 5  # mirror train script floor

TIER_ORDER = ("CHALLENGE", "GOLD-B", "GOLD-A")


def main() -> int:
    ap = argparse.ArgumentParser(description="P5 freeze GOLD-A/B/CHALLENGE")
    ap.add_argument("--golden", default="config/golden/stage4_golden_mined_p4.yaml")
    ap.add_argument("--source-map", default="temp/golden_source_map_clean.json")
    ap.add_argument("--adjudication", default=None,
                    help="temp/p5_human_adjudication.jsonl (optional overrides)")
    ap.add_argument("--size", type=int, default=400, help="target frozen size 300-500")
    ap.add_argument("--challenge-fraction", type=float, default=0.25)
    ap.add_argument("--goldb-fraction", type=float, default=0.15)
    # ── Provenance-disjoint selection ─────────────────────────────────────────
    # STRUCTURAL FINDING (2026-09-06): the book<->example graph has ONE giant
    # component (1008/1027 examples) + 19 examples in small components. Strict
    # book/author-disjointness is therefore INFEASIBLE from the current pool at
    # any useful size. The freeze script supports two modes:
    #   strict  (default): freeze ONLY the small components (< --max-component);
    #            refuses the run if that yields < --min-strict (default 30) —
    #            signalling that a fresh disjoint eval pool must be mined.
    #   --allow-soft: additionally carve from the giant component and REPORT the
    #            residual book/author overlap honestly (never claimed clean).
    ap.add_argument("--max-component", type=int, default=50)
    ap.add_argument("--min-strict", type=int, default=30)
    ap.add_argument("--allow-soft", action="store_true")
    ap.add_argument("--out", default="config/golden/gold_frozen.yaml")
    args = ap.parse_args()
    if not (300 <= args.size <= 500):
        print(f"--size {args.size} outside 300-500", file=sys.stderr)
        return 1

    doc = yaml.safe_load(Path(args.golden).read_text(encoding="utf-8")) or {}
    examples: list[dict] = doc.get("examples", [])
    n = len(examples)
    if n < args.size + 50:
        print(f"pool too small ({n}) for a {args.size}-freeze + floor", file=sys.stderr)
        return 1

    # Optional adjudication overrides: example_id -> {discipline, domains}.
    adj: dict[str, dict] = {}
    if args.adjudication and Path(args.adjudication).exists():
        for line in Path(args.adjudication).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("final_discipline"):
                adj[r["example_id"]] = {
                    "discipline": r["final_discipline"],
                    "domains": r.get("final_domains"),
                }

    # Provenance: example_id -> (book_set, author_set).
    prov: dict[str, tuple[set, set]] = {}
    for r in json.loads(Path(args.source_map).read_text(encoding="utf-8")):
        prov[r["example_id"]] = (set(r.get("books") or []), set(r.get("authors") or []))
    book_share: Counter = Counter()
    for (books, _) in prov.values():
        for b in books:
            book_share[b] += 1
    author_share: Counter = Counter()
    for (_, authors) in prov.values():
        for a in authors:
            author_share[a] += 1

    # Apply adjudication + freeze the tier field.
    for ex in examples:
        eid = str(ex["id"])
        o = adj.get(eid)
        if o:
            exp = ex["expected_classification"]
            exp["discipline"] = o["discipline"]
            if o.get("domains"):
                exp["domains"] = o["domains"]
            ex["adjudicated"] = True
        ex["tier"] = None

    # Discipline counts.
    disc_of = lambda ex: ex["expected_classification"]["discipline"]  # noqa: E731
    counts = Counter(disc_of(ex) for ex in examples)

    # Connected components over the book<->example bipartite graph (union-find).
    parent = {eid: eid for eid in prov}
    def _find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def _union(a: str, b: str) -> None:
        ra, rb = _find(a), _find(b)
        if ra != rb:
            parent[rb] = ra
    book2ex: dict[str, list[str]] = defaultdict(list)
    for eid, (books, _) in prov.items():
        for b in books:
            book2ex[b].append(eid)
    for _, ids in book2ex.items():
        for eid in ids[1:]:
            _union(ids[0], eid)
    # Also union examples sharing an author.
    author2ex: dict[str, list[str]] = defaultdict(list)
    for eid, (_, authors) in prov.items():
        for a in authors:
            author2ex[a].append(eid)
    for _, ids in author2ex.items():
        for eid in ids[1:]:
            _union(ids[0], eid)
    comps: dict[str, list[str]] = defaultdict(list)
    for eid in prov:
        comps[_find(eid)].append(eid)
    sizes = sorted((len(v) for v in comps.values()), reverse=True)
    giant = sizes[0] if sizes else 0

    small_ids = [eid for c in comps.values() if len(c) <= args.max_component
                 for eid in c]
    strict_capable = len(small_ids)
    if not args.allow_soft and strict_capable < args.min_strict:
        print(json.dumps({
            "status": "INFEASIBLE_STRICT_DISJOINT",
            "n_examples": n,
            "giant_component_size": giant,
            "n_components": len(comps),
            "strict_disjoint_capacity": strict_capable,
            "min_strict": args.min_strict,
            "finding": (
                "book/author-disjoint freeze of 300-500 is infeasible from this "
                "pool: the provenance graph is one giant component (multi-book FBs "
                "share books/authors). MINE a fresh eval pool from disjoint books "
                "(D2585) or rerun with --allow-soft (documented residual overlap)."
            ),
        }, indent=2))
        return 2

    # Tier assignment: CHALLENGE / GOLD-B from the least-connected frozen ids.
    if args.allow_soft:
        frozen_ids: set[str] = set(small_ids)
        # top up from the giant component, least-shared examples first
        rest = sorted(
            (eid for eid in prov if eid not in frozen_ids),
            key=lambda eid: (sum(book_share[b] for b in prov[eid][0])
                             + sum(author_share[a] for a in prov[eid][1]), eid),
        )
        for eid in rest:
            if len(frozen_ids) >= args.size:
                break
            frozen_ids.add(eid)
    else:
        frozen_ids = set(small_ids)
    if len(frozen_ids) < args.size and not args.allow_soft:
        print(f"strict-disjoint capacity {len(frozen_ids)} < target {args.size}; "
              "use --allow-soft or mine a disjoint pool", file=sys.stderr)
        return 2
    if len(frozen_ids) > args.size:
        # trim least-shared extras
        frozen_ids = set(sorted(frozen_ids,
                                key=lambda e: (sum(book_share[b] for b in prov[e][0])
                                               + sum(author_share[a] for a in prov[e][1]),
                                               e))[:args.size])

    # Assign tiers within the frozen set: CHALLENGE first (stratified attempt by
    # class, least-shared ids first), then GOLD-B, then GOLD-A.
    remaining_frozen = sorted(
        frozen_ids,
        key=lambda eid: (sum(book_share[b] for b in prov.get(eid, (set(),))[0]),
                         eid),
    )
    target = args.size
    eligible_classes = [d for d, c in counts.items() if c >= _MIN_PER_CLASS]
    n_challenge = int(round(target * args.challenge_fraction))
    n_goldb = int(round(target * args.goldb_fraction))

    def by_class_of(ids) -> dict[str, list[str]]:
        d: dict[str, list[str]] = defaultdict(list)
        for eid in ids:
            ex = next((x for x in examples if str(x["id"]) == eid), None)
            if ex:
                d[disc_of(ex)].append(eid)
        return d

    # Greedy CHALLENGE: per class take up to ~n_challenge/n_classes ids.
    ch_per = max(1, n_challenge // max(len(eligible_classes), 1))
    ch_taken: set[str] = set()
    for disc_ids in by_class_of(remaining_frozen).values():
        for eid in sorted(disc_ids, key=lambda e: (
            sum(book_share[b] for b in prov.get(e, (set(),))[0]), e))[:ch_per]:
            ch_taken.add(eid)
    for eid in ch_taken:
        next(x for x in examples if str(x["id"]) == eid)["tier"] = "CHALLENGE"

    gb_per = max(1, n_goldb // max(len(eligible_classes), 1))
    gb_taken: set[str] = set()
    left = [e for e in remaining_frozen if e not in ch_taken]
    for disc_ids in by_class_of(left).values():
        for eid in sorted(disc_ids, key=lambda e: (
            sum(book_share[b] for b in prov.get(e, (set(),))[0]), e))[:gb_per]:
            gb_taken.add(eid)
    for eid in gb_taken:
        next(x for x in examples if str(x["id"]) == eid)["tier"] = "GOLD-B"
    for eid in remaining_frozen:
        if eid not in ch_taken and eid not in gb_taken:
            next(x for x in examples if str(x["id"]) == eid)["tier"] = "GOLD-A"

    for ex in examples:
        if ex["tier"] is None:
            ex["tier"] = "TRAIN_POOL"
    # Residual provenance overlap: frozen books/authors that also appear in pool.
    frozen = [e for e in examples if e["tier"] in TIER_ORDER]
    pool = [e for e in examples if e["tier"] == "TRAIN_POOL"]
    pool_books: set = set()
    pool_authors: set = set()
    for ex in pool:
        b, a = prov.get(str(ex["id"]), (set(), set()))
        pool_books |= b
        pool_authors |= a
    overlap_books = overlap_authors = 0
    for ex in frozen:
        b, a = prov.get(str(ex["id"]), (set(), set()))
        overlap_books += len(b & pool_books)
        overlap_authors += len(a & pool_authors)

    tier_counts = Counter(e["tier"] for e in examples)
    per_class_frozen = Counter(disc_of(e) for e in frozen)
    per_class_pool = Counter(disc_of(e) for e in pool)

    meta = dict(doc.get("meta") or {})
    meta["note"] = (
        "FROZEN GOLD partition (D2585 P5 v1). Source: " + args.golden +
        f" + adjudication({Path(args.adjudication).name if args.adjudication else 'none'}). "
        "tier: CHALLENGE=test(never train), GOLD-B=dev, GOLD-A=train-safe, "
        "TRAIN_POOL=remaining pool. DO NOT EDIT after freeze."
    )
    meta["tier_counts"] = dict(tier_counts)
    doc["meta"] = meta

    out_path = _ROOT / args.out
    out_path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True),
                        encoding="utf-8")

    report = {
        "n_examples": n,
        "tier_counts": dict(tier_counts),
        "frozen_size": len(frozen),
        "challenge": tier_counts.get("CHALLENGE", 0),
        "gold_b": tier_counts.get("GOLD-B", 0),
        "gold_a": tier_counts.get("GOLD-A", 0),
        "train_pool": tier_counts.get("TRAIN_POOL", 0),
        "residual_book_overlap_frozen_vs_pool": int(overlap_books),
        "residual_author_overlap_frozen_vs_pool": int(overlap_authors),
        "per_class_frozen_min": min(per_class_frozen.values()) if per_class_frozen else 0,
        "per_class_pool_min": min(per_class_pool.values()) if per_class_pool else 0,
        "out": str(out_path),
    }
    (_GOV_DIR / "gold_freeze_report.md").write_text(
        "\n".join([
            "# GOLD FREEZE REPORT (D2585 P5 v1)",
            "",
            f"- frozen size: **{len(frozen)}** (target {args.size})",
            f"- CHALLENGE (test): **{tier_counts.get('CHALLENGE', 0)}** | "
            f"GOLD-B (dev): **{tier_counts.get('GOLD-B', 0)}** | "
            f"GOLD-A (train-safe): **{tier_counts.get('GOLD-A', 0)}** | "
            f"TRAIN_POOL: **{tier_counts.get('TRAIN_POOL', 0)}**",
            f"- residual book overlap frozen-vs-pool: **{overlap_books}** "
            f"(0 = fully disjoint)",
            f"- residual author overlap frozen-vs-pool: **{overlap_authors}**",
            f"- min per-class in frozen: **{report['per_class_frozen_min']}** | "
            f"min per-class in pool: **{report['per_class_pool_min']}**",
            "",
            "## Usage",
            "",
            "    GOLDEN_YAML=config/golden/gold_frozen.yaml "
            "GOLDEN_TEST_IDS=<CHALLENGE example ids> python3 "
            "scripts/train_discipline_classifier.py",
            "",
        ]),
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
