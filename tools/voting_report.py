#!/usr/bin/env python3
"""Voting report — per-voter accuracy, agreement, ERROR CORRELATION, and ensembles.

Reads governance/model_eval_checkpoint.jsonl rows for suite == "voting" (251 gold rows
per model) and answers the three questions that decide a voter roster:

  1. per-voter accuracy (discipline exact, domain micro-F1) + latency
  2. pairwise agreement and ERROR CORRELATION (Jaccard of error sets).
     High error correlation => adding that voter cannot help, at any ensemble size.
  3. ensemble simulation: best-single vs majority-of-3 / 5 vs unanimity-gated,
     with the coverage/accuracy tradeoff.

Usage: python3 tools/voting_report.py [--md out.md]
"""
from __future__ import annotations

import argparse
import itertools
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CKPT = ROOT / "governance" / "model_eval_checkpoint.jsonl"
GOLD = ROOT / "governance" / "gold_4axis.jsonl"


def parse_pred(pred: str) -> tuple[str, frozenset]:
    """Extract (discipline, domains) from a model prediction."""
    m = re.search(r"\{.*\}", pred or "", re.S)
    if not m:
        return "", frozenset()
    try:
        d = json.loads(m.group(0))
    except Exception:
        return "", frozenset()
    disc = str(d.get("discipline", "")).strip().lower()
    doms = frozenset(str(x).strip().lower() for x in (d.get("domains") or []))
    return disc, doms


def f1(a: frozenset, b: frozenset) -> float:
    """Micro-F1 between two domain sets."""
    tp = len(a & b)
    if not tp:
        return 0.0
    p, r = tp / len(b), tp / len(a)
    return 2 * p * r / (p + r) if (p + r) else 0.0


def main() -> int:
    """Print the voting report."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default=None)
    args = ap.parse_args()

    gold = {g["fb_id"]: g for g in
            (json.loads(l) for l in GOLD.read_text(encoding="utf-8").splitlines() if l.strip())}

    per: dict[str, dict[str, tuple[str, frozenset]]] = defaultdict(dict)
    lat: dict[str, list[float]] = defaultdict(list)
    fails: dict[str, int] = defaultdict(int)
    for line in CKPT.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("suite") != "voting":
            continue
        if r.get("err"):
            fails[r["model"]] += 1
            continue
        per[r["model"]][r["id"]] = parse_pred(r.get("pred", ""))
        if r.get("secs"):
            lat[r["model"]].append(float(r["secs"]))

    models = sorted(per, key=lambda m: -len(per[m]))
    if not models:
        print("no voting rows yet")
        return 0

    L: list[str] = []
    L.append("VOTING REPORT — " + str(len(gold)) + " gold rows, oMLX temp 0.0")
    L.append("")
    L.append("GOLD CAVEAT: 164/251 discipline labels came from the reliable pair AGREEDING")
    L.append("(circular), 87/251 are that pair's human-adjudicated DISAGREEMENTS (biased hard).")
    L.append("Absolute accuracy is therefore only meaningful for models that never voted on")
    L.append("these rows. Agreement and error correlation are valid regardless.")
    L.append("")

    L.append("PER-VOTER ACCURACY + LATENCY")
    L.append("-" * 78)
    L.append("model".ljust(34) + "disc_acc".rjust(10) + "dom_f1".rjust(9) + "dom_exact".rjust(11) + "med_s".rjust(8) + "n".rjust(6))
    for m in models:
        rows = sorted(per[m])
        de = da = 0
        ds: list[float] = []
        for fb in rows:
            g = gold.get(fb)
            if not g:
                continue
            gd = str(g.get("discipline", "")).strip().lower()
            gdom = frozenset(str(x).strip().lower() for x in (g.get("domains") or []))
            pd, pdom = per[m][fb]
            da += 1 if pd == gd else 0
            de += 1 if pdom == gdom else 0
            ds.append(f1(gdom, pdom))
        n = max(len(rows), 1)
        med = statistics.median(lat[m]) if lat.get(m) else 0.0
        L.append(m[:33].ljust(34) + format(da / n, ".3f").rjust(10) + format(sum(ds) / n, ".3f").rjust(9)
                 + format(de / n, ".3f").rjust(11) + format(med, ".1f").rjust(8) + str(len(rows)).rjust(6))

    L.append("")
    L.append("PAIRWISE AGREEMENT + ERROR CORRELATION (discipline)")
    L.append("-" * 78)
    L.append("pair".ljust(48) + "n".rjust(6) + "agree".rjust(8) + "errJac".rjust(9))
    for a, b in itertools.combinations(models, 2):
        shared = sorted(set(per[a]) & set(per[b]))
        if len(shared) < 20:
            continue
        agr = sum(1 for f in shared if per[a][f][0] == per[b][f][0])
        ea = {f for f in shared if f in gold and per[a][f][0] != str(gold[f].get("discipline", "")).strip().lower()}
        eb = {f for f in shared if f in gold and per[b][f][0] != str(gold[f].get("discipline", "")).strip().lower()}
        jac = len(ea & eb) / max(len(ea | eb), 1)
        L.append((a[:22] + " vs " + b[:22]).ljust(48) + str(len(shared)).rjust(6)
                 + format(agr / len(shared), ".3f").rjust(8) + format(jac, ".3f").rjust(9))
    L.append("")
    L.append("errJac ~1.0 means the two voters fail on the SAME rows -> voting cannot help.")
    L.append("errJac ~0.0 means independent failures -> a third voter is genuinely informative.")

    L.append("")
    L.append("ENSEMBLE SIMULATION (discipline)")
    L.append("-" * 78)

    def eval_combo(combo: tuple, mode: str) -> tuple[float, float]:
        shared = sorted(set.intersection(*[set(per[m]) for m in combo]))
        shared = [f for f in shared if f in gold]
        if not shared:
            return 0.0, 0.0
        got = dec = 0
        for f in shared:
            labs = [per[m][f][0] for m in combo]
            if mode == "majority":
                tally: dict[str, int] = defaultdict(int)
                for l in labs:
                    tally[l] += 1
                top = max(tally.values())
                w = [k for k, v in tally.items() if v == top]
                if len(w) != 1:
                    continue
                pick = w[0]
            else:
                if len(set(labs)) != 1:
                    continue
                pick = labs[0]
            dec += 1
            if pick == str(gold[f].get("discipline", "")).strip().lower():
                got += 1
        return (got / dec if dec else 0.0), (dec / len(shared))

    for size in (1, 3, 5):
        combos = list(itertools.combinations(models, size))
        if not combos:
            continue
        accs, covs = [], []
        for c in combos:
            a, v = eval_combo(c, "majority")
            if v:
                accs.append(a)
                covs.append(v)
        if accs:
            L.append("majority of " + str(size) + "   combos=" + str(len(accs))
                     + "  acc=" + format(sum(accs) / len(accs), ".3f")
                     + "  coverage=" + format(sum(covs) / len(covs), ".3f"))
    for size in (2, 3):
        combos = list(itertools.combinations(models, size))
        accs, covs = [], []
        for c in combos:
            a, v = eval_combo(c, "unanimity")
            if v:
                accs.append(a)
                covs.append(v)
        if accs:
            L.append("unanimity of " + str(size) + "  combos=" + str(len(accs))
                     + "  acc=" + format(sum(accs) / len(accs), ".3f")
                     + "  coverage=" + format(sum(covs) / len(covs), ".3f"))

    if fails:
        L.append("")
        L.append("transport failures: " + str(dict(fails)))

    text = chr(10).join(L)
    print(text)
    if args.md:
        Path(args.md).write_text(text + chr(10), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
