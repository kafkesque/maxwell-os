#!/usr/bin/env python3
"""
rederive_kindsafe_domains.py — BUG-200 post-hoc re-derivation of canonical `domains`.

Deterministic, LLM-free, non-destructive. Re-derives each FB's canonical `domains`
from its preserved `domains_raw` using the NOW-kind-safe matcher (BUG-200 fix in
pipeline/schemas.py). Before the fix, a discipline label emitted into `domains_raw`
(e.g. 'software engineering') was silently COERCED into a domain canonical (e.g.
'engineering practice') via cross-kind raw-alias/synonym pollution. After the fix it
correctly resolves to 'emerging' (honest "unmapped domain").

Scope is deliberately NARROW:
  * ONLY the `domains` field is recomputed.
  * `discipline`, `discipline_raw`, `domains_raw`, `taxonomy_match_method` and every
    other field are preserved BYTE-IDENTICAL.
  * `discipline` is NOT recomputed on purpose — it carries the Phase-0b alias remap
    (alias_map.yaml, 754 records), which match_to_canonical() does not apply.

Output is written to a NEW file (never overwrites the input). Use --in-place only
after human review of the --diff report.

Usage:
    python3 scripts/rederive_kindsafe_domains.py --input <enriched.jsonl> --output <out.jsonl> [--diff] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.schemas import match_to_canonical  # noqa: E402


def to_list(value: object) -> list[str]:
    """Normalize a JSON field that may be a str, list, or None into a list of str."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value]


def rederive_domains(old_domains: list[str], domains_raw: list[str]) -> list[str]:
    """Re-derive canonical domains, preserving the old order for unchanged labels.

    Returns `old_domains` UNCHANGED when the label SET is identical — avoids spurious
    re-ordering that would perturb order-sensitive consumers (route.py folder naming,
    "first non-emerging" selection). When a coercion is actually fixed (a cross-kind
    raw label now resolves to 'emerging' instead of a coerced domain), survivors keep
    their old order and the new label is appended deterministically.
    """
    new_set: set[str] = set()
    for raw in domains_raw:
        mapped = match_to_canonical(raw, "domain")
        new_set.add(mapped if mapped is not None else "emerging")
    if not new_set:
        new_set = {"emerging"}

    if new_set == set(old_domains):
        return old_domains

    result = [x for x in old_domains if x in new_set]
    for x in sorted(new_set - set(old_domains)):
        result.append(x)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="enriched checkpoint JSONL (read-only)")
    parser.add_argument("--output", required=True, help="output JSONL (NEW file)")
    parser.add_argument("--diff", action="store_true", help="print a change report")
    parser.add_argument("--limit", type=int, default=0, help="process first N records (0=all)")
    args = parser.parse_args()

    src = Path(args.input)
    dst = Path(args.output)
    if src.resolve() == dst.resolve():
        print("ERROR: --output must differ from --input (non-destructive by design)", file=sys.stderr)
        return 2

    total = 0
    changed = 0
    coercion_fixed = 0  # records whose domains changed AND previously had no 'emerging'
    examples: list[tuple[str, list[str], list[str]]] = []

    with open(src, "r", encoding="utf-8") as fin, open(dst, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            if args.limit and total >= args.limit:
                break
            rec = json.loads(line)
            total += 1

            old_domains = to_list(rec.get("domains"))
            raw_domains = to_list(rec.get("domains_raw"))
            new_domains = rederive_domains(old_domains, raw_domains)

            if new_domains != old_domains:
                changed += 1
                if "emerging" not in old_domains and "emerging" in new_domains:
                    coercion_fixed += 1
                if len(examples) < 10:
                    examples.append((rec.get("fb_id", "?"), old_domains, new_domains))

            rec["domains"] = new_domains
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"total records          : {total}")
    print(f"domains changed        : {changed}")
    print(f"  of which coercion→emerging fixed: {coercion_fixed}")
    print(f"output written         : {dst}")
    if args.diff and examples:
        print("\n-- example changes (fb_id | OLD domains → NEW domains) --")
        for fb, old, new in examples:
            print(f"  {fb[:12]}… | {old} → {new}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
