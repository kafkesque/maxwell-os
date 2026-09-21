#!/usr/bin/env python3
"""Voter analysis — accuracy, agreement, error correlation, ensembles. Zero API cost.

Sources
  governance/joint_vote_production_checkpoint.jsonl  (8016 rows, 2 voters, 248 overlap gold)
  governance/discipline_domain_vote_checkpoint.jsonl (216 rows, 2 voters)
  governance/depth_vote_checkpoint.jsonl              (996 rows, 3 voters)
  governance/gold_4axis.jsonl                         (251 rows gold)

CIRCULARITY WARNING
  Many gold discipline labels were produced by the reliable pair AGREEING
  (source p5:reliable-pair-*), so measuring that pair's accuracy against those
  rows is circular. Domain labels are overwhelmingly HUMAN-sourced (p5:human-*),
  so domain accuracy IS a valid measurement. Agreement / error-correlation is
  source-independent and is the metric that decides whether voting can help.

Usage: python3 tools/vote_analysis.py
"""
from __future__ import annotations

import itertools
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOV = ROOT / "governance"
GOLD = GOV / "gold_4axis.jsonl"
VOTE_FILES = [
    GOV / "joint_vote_production_checkpoint.jsonl",
    GOV / "discipline_domain_vote_checkpoint.jsonl",
    GOV / "depth_vote_checkpoint.jsonl",
    GOV / "remaining_axes_vote_checkpoint.jsonl",
    GOV / "queue_59_vote_checkpoint.jsonl",
    GOV / "joint_vote_checkpoint.jsonl",
]


def load_jsonl(p: Path) -> list[dict]:
    """Load JSONL into a list of dicts (empty list if missing)."""
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def as_vote(v: object) -> dict:
    """Normalise a stored vote into {discipline, domains} regardless of its shape."""
    if isinstance(v, dict):
        return {"discipline": v.get("discipline"), "domains": v.get("domains")}
    return {"discipline": v, "domains": None}


def nd(s: object) -> str:
    """Normalise a discipline label."""
    return str(s or "").strip().lower()


def ndom(v: object) -> frozenset:
    """Normalise a domain collection into a lowercase frozenset."""
    if not v:
        return frozenset()
    if isinstance(v, str):
        return frozenset([v.strip().lower()])
    return frozenset(str(x).strip().lower() for x in v if str(x).strip())


def f1(a: frozenset, b: frozenset) -> float:
    """Micro-F1 between two sets."""
    tp = len(a & b)
    if not tp:
        return 0.0
    p, r = tp / len(b), tp / len(a)
    return 2 * p * r / (p + r) if (p + r) else 0.0


def collect() -> tuple[dict[str, dict[str, dict]], dict[str, dict]]:
    """Return ({voter: {fb_id: vote}}, gold) across all vote checkpoints."""
    gold = {g["fb_id"]: g for g in load_jsonl(GOLD)}
    per: dict[str, dict[str, dict]] = defaultdict(dict)
    for p in VOTE_FILES:
        for r in load_jsonl(p):
            fb = r.get("fb_id")
            if not fb or fb not in gold:
                continue
            for name, v in (r.get("votes") or {}).items():
                per[name][fb] = as_vote(v)
    return per, gold


def main() -> int:
    """Print the voter report."""
    per, gold = collect()
    voters = sorted(per, key=lambda n: -len(per[n]))
    print("gold rows:", len(gold))
    for v in voters:
        print("  voter", v[:34].ljust(34), "rows with gold overlap:", len(per[v]))

    src = defaultdict(int)
    for g in gold.values():
        src[str(g.get("discipline_source"))] += 1
    circular = sum(n for k, n in src.items() if "reliable-pair" in k)
    print()
    print("CIRCULARITY: " + str(circular) + "/" + str(len(gold))
          + " discipline labels came from the reliable pair agreeing -> those rows cannot")
    print("             measure that pair's accuracy. Domains are human-sourced (valid).")

    for voter in voters:
        rows = sorted(per[voter])
        if not rows:
            continue
        print()
        print("== " + voter + " (" + str(len(rows)) + " rows)")
        print("   domain micro-F1 vs gold      : " + format(sum(f1(ndom(gold[f].get("domains")), ndom(per[voter][f].get("domains"))) for f in rows) / len(rows), ".3f"))
        print("   domain exact-set match       : " + format(sum(1 for f in rows if ndom(gold[f].get("domains")) == ndom(per[voter][f].get("domains"))) / len(rows), ".3f"))
        # discipline only on rows that are NOT pair-derived
        indep = [f for f in rows if "reliable-pair" not in str(gold[f].get("discipline_source")) and "vote" not in str(gold[f].get("discipline_source"))]
        if indep:
            a = sum(1 for f in indep if nd(per[voter][f].get("discipline")) == nd(gold[f].get("discipline"))) / len(indep)
            print("   discipline acc (INDEPENDENT gold, n=" + str(len(indep)) + "): " + format(a, ".3f"))
        else:
            print("   discipline acc               : n/a (no independent gold rows)")

    print()
    print("PAIRWISE AGREEMENT + ERROR CORRELATION (discipline, all shared rows)")
    print("-" * 86)
    for a, b in itertools.combinations(voters, 2):
        shared = sorted(set(per[a]) & set(per[b]))
        if len(shared) < 20:
            continue
        agree = sum(1 for f in shared if nd(per[a][f].get("discipline")) == nd(per[b][f].get("discipline")))
        ea = {f for f in shared if nd(per[a][f].get("discipline")) != nd(gold[f].get("discipline")) and "reliable-pair" not in str(gold[f].get("discipline_source"))}
        eb = {f for f in shared if nd(per[b][f].get("discipline")) != nd(gold[f].get("discipline")) and "reliable-pair" not in str(gold[f].get("discipline_source"))}
        jac = len(ea & eb) / max(len(ea | eb), 1)
        print("  " + (a[:20] + " vs " + b[:20]).ljust(46)
              + " n=" + str(len(shared)).ljust(6)
              + " agree=" + format(agree / len(shared), ".3f")
              + "  errorJaccard=" + format(jac, ".3f"))

    print()
    print("ENSEMBLE SIMULATION (discipline, rows where all voters of the combo voted)")
    print("-" * 86)
    for size in (2, 3):
        combos = [c for c in itertools.combinations(voters, size)]
        accs, covs = [], []
        for combo in combos:
            shared = sorted(set.intersection(*[set(per[n]) for n in combo]))
            if len(shared) < 20:
                continue
            got = dec = 0
            for f in shared:
                tally: dict[str, int] = defaultdict(int)
                for n in combo:
                    tally[nd(per[n][f].get("discipline"))] += 1
                top = max(tally.values())
                w = [k for k, v in tally.items() if v == top]
                if len(w) == 1:
                    dec += 1
                    if w[0] == nd(gold[f].get("discipline")):
                        got += 1
            if dec:
                accs.append(got / dec)
                covs.append(dec / len(shared))
        if accs:
            print("  majority of " + str(size) + "  (n=" + str(len(accs)) + " combos)  acc="
                  + format(sum(accs) / len(accs), ".3f") + "  coverage=" + format(sum(covs) / len(covs), ".3f"))
            print("     NOTE: accuracy is inflated by circular gold for pair-derived rows.")
            print("     The COVERAGE number is the honest signal: how often voters agree at all.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
