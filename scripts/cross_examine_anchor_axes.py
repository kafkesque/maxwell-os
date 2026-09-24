#!/usr/bin/env python3
"""cross_examine_anchor_axes.py - the ANCHOR domain+depth cross-examination, deterministic and LLM-free.

WHY: after the 2026-09-24 frontier pass the 150 anchor rows carry FIVE independent readings of the same two axes:
DeepSeek-v4-pro and Qwen3.8 (the D2618 reliable pair, domains only), Claude (rows 101-150, domains+depth), Kimi
(rows 001-145, domains+depth) and the OWNER's own depth pass (gold, 150/150). Nothing in the repo could compare
them, so "which coder do we trust" was answerable only by impression. This script makes the comparison a
measurement: coverage per source, inter-coder agreement, per-coder error against the owner's gold depth, and the
DISPUTE SET that is the only thing the owner should ever be asked to adjudicate.

WHAT IT DOES NOT DO (guaranteeable properties, not promises):
  - detected: every source carries a DECLARED coverage fingerprint in config/anchor_cross_exam.yaml (rows,
    first/last item_id, sha256). A changed or shrunken file FAILS the run instead of being scored silently.
  - fail-closed: the owner's gold sheet is read only after its sha256 matches the rail-1 lock registry; a frontier
    reply with a bad header, an off-menu value, a duplicate or a PARTIAL line is refused whole (never hand-fixed).
  - advisory-only: it writes NO *_final column and mutates no instrument. The owner's workbook is emitted with the
    owner columns EMPTY for the one adjudication session.
  - declared: the format deviation of an unfenced frontier reply and every coverage gap are printed and written into
    the report, never swallowed.

Usage:
  python3 scripts/cross_examine_anchor_axes.py --check          # coverage + lock audit only, no scoring
  python3 scripts/cross_examine_anchor_axes.py                  # full run: long CSV + workbook + stats + report
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import io
import json
import pathlib
import re
import statistics
import sys
from typing import Any

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import build_discipline_domain_vote as bddv  # noqa: E402  (the shared taxonomy surface, never a copy)

CONFIG = REPO / "config" / "anchor_cross_exam.yaml"
HEADER = ["item_id", "domains", "domains_secondary", "depth", "conf_domain", "conf_depth",
          "evidence_quote", "rationale", "boundary_condition", "coder", "date"]
ITEM_RE = re.compile(r"^R\d{3}$")
N_ROWS = 150
WORKBOOK_OWNER_COLS = ["domains_final", "depth_final", "owner_note", "owner_date"]


def sha256_of(path: pathlib.Path) -> str:
    """Return the sha256 of a file without loading it twice."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def depth_menu() -> tuple[dict[str, int], dict[int, str]]:
    """Return (label -> ordinal id, ordinal id -> label) from config/depth_classes.yaml."""
    classes = yaml.safe_load((REPO / "config" / "depth_classes.yaml").read_text(encoding="utf-8"))["classes"]
    return ({c["label"]: int(c["id"]) for c in classes}, {int(c["id"]): c["label"] for c in classes})


def canonical_domain(raw: str) -> str | None:
    """Map a coder's domain string to a closed-menu canonical label, or None if off-menu."""
    v = (raw or "").strip()
    if not v:
        return None
    if v in bddv.DOM_NAMES:
        return v
    return bddv.DOM_ALIAS.get(v.lower())


def read_frontier(path: pathlib.Path, declared: dict[str, Any]) -> tuple[list[dict[str, str]], list[str], list[str]]:
    """Parse one frontier reply. Returns (rows, fatal, notes).

    `fatal` means REFUSE (never repair, never score): a changed sha256, an undeclared truncation, a duplicate
    item_id, an off-menu value. `notes` are DECLARED conditions - an unfenced reply, a repeated header line, a
    tail cut by the coder's output cap - which are surfaced and carried into the report instead of swallowed.
    """
    fatal: list[str] = []
    notes: list[str] = []
    if not path.exists():
        return [], [f"{path.name}: MISSING"], notes
    blob = path.read_bytes()
    got = hashlib.sha256(blob).hexdigest()
    want = declared.get("sha256")
    if want and got != want:
        fatal.append(f"{path.name}: sha256 {got[:12]} != declared {want[:12]} - reply changed since it was declared")
    text = blob.decode("utf-8", errors="replace")
    if declared.get("fenced", True):
        blocks = re.findall(r"```(?:csv)?\s*\n(.*?)```", text, re.S)
        if len(blocks) != 1:
            return [], fatal + [f"{path.name}: expected 1 fenced CSV block, found {len(blocks)}"], notes
        body = blocks[0].strip()
    else:
        body = text
        notes.append(f"DECLARED FORMAT DEVIATION {path.name}: unfenced raw CSV (accepted by config declaration)")
    lines = [l for l in body.splitlines() if l.strip()]
    kept: list[str] = []
    seen_header = False
    repeats = 0
    for line in lines:
        if line.split(",")[0].strip().strip('"') == "item_id":
            if seen_header:
                repeats += 1
                continue
            seen_header = True
        kept.append(line)
    if repeats:
        if declared.get("accept_repeated_header"):
            notes.append(f"{path.name}: header line repeated {repeats}x - dropped as a declared format artifact")
        else:
            fatal.append(f"{path.name}: header line repeated {repeats}x, undeclared")
    rows = list(csv.DictReader(io.StringIO("\n".join(kept))))
    if not rows or list(rows[0].keys()) != HEADER:
        return [], fatal + [f"{path.name}: header mismatch"], notes
    seen: set[str] = set()
    short: list[str] = []
    out: list[dict[str, str]] = []
    menu = depth_menu()[0]
    for r in rows:
        i = (r.get("item_id") or "").strip()
        if not ITEM_RE.match(i):
            short.append(i[:40])
            continue
        if i in seen:
            fatal.append(f"{path.name}: duplicate {i}")
        seen.add(i)
        if r["depth"].strip() not in menu and r["depth"].strip() != "none_fits":
            fatal.append(f"{path.name}:{i}: depth '{r['depth'].strip()}' outside the closed menu")
        if not (r["evidence_quote"] or "").strip():
            fatal.append(f"{path.name}:{i}: empty evidence_quote")
        out.append(r)
    if short:
        msg = f"{path.name}: {len(short)} partial record(s) at the tail {short[:3]}"
        if declared.get("allow_truncated_tail"):
            notes.append(f"DECLARED SHORTFALL {msg} - the reply was cut by the coder's output cap")
        else:
            fatal.append(f"{msg} - reply is truncated, refused")
    want_n = declared.get("rows")
    if want_n is not None and len(out) != want_n:
        fatal.append(f"{path.name}: {len(out)} valid rows != declared {want_n}")
    ids = sorted(seen)
    if declared.get("first") and ids and ids[0] != declared["first"]:
        fatal.append(f"{path.name}: first item_id {ids[0]} != declared {declared['first']}")
    if declared.get("last") and ids and ids[-1] != declared["last"]:
        fatal.append(f"{path.name}: last item_id {ids[-1]} != declared {declared['last']}")
    return out, fatal, notes


def read_pair_checkpoint(path: pathlib.Path) -> dict[str, dict[str, Any]]:
    """Return item_id -> last record (append-only checkpoint: latest record per item wins)."""
    recs: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            recs[r["item_id"]] = r
    return recs


def read_owner_gold(cfg: dict[str, Any]) -> tuple[dict[str, int], dict[str, str], list[str]]:
    """Read the owner's depth pass, but only after its sha256 matches the rail-1 lock registry."""
    g = cfg["owner_gold"]
    sheet = REPO / g["path"]
    locks = yaml.safe_load((REPO / g["lock_registry"]).read_text(encoding="utf-8"))
    entry = next((i for i in locks["instruments"] if i["path"] == g["path"]), None)
    if entry is None:
        return {}, {}, [f"owner gold {g['path']} is NOT in the lock registry - refusing to read it"]
    got = sha256_of(sheet)
    if got != entry["sha256"]:
        return {}, {}, [f"owner gold sha256 {got[:12]} != locked {entry['sha256'][:12]} - REFUSING (rail 1)"]
    depths: dict[str, int] = {}
    confs: dict[str, str] = {}
    with sheet.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            i = (row.get("item_id") or "").strip()
            if ITEM_RE.match(i):
                depths[i] = int(row[g["column"]])
                confs[i] = (row.get(g["conf_column"]) or "").strip()
    return depths, confs, []


def jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity of two label sets; two empty sets count as 0 (no evidence of agreement)."""
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def collect(cfg: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    """Build item_id -> {coder readings} across every source. Returns (items, fatal, notes)."""
    items: dict[str, dict[str, Any]] = {f"R{i:03d}": {"coders": {}} for i in range(1, N_ROWS + 1)}
    notes: list[str] = []
    fatal: list[str] = []
    labels = depth_menu()[0]
    for src in cfg["sources"]:
        path = REPO / src["path"]
        if src["kind"] == "declared_missing":
            notes.append(f"declared missing: {src['path']} ({src.get('note','')})")
            continue
        if src["kind"] == "pair_voter":
            recs = read_pair_checkpoint(path)
            for item, rec in recs.items():
                vote = (rec.get("votes") or {}).get(src["id"]) or {}
                if isinstance(vote, dict) and not vote.get("error"):
                    doms = [c for c in (canonical_domain(d) for d in (vote.get("domains") or [])) if c]
                    items[item]["coders"][src["id"]] = {"domains": doms, "depth": None,
                                                       "conf_domain": None, "conf_depth": None,
                                                       "authority": src["authority"]}
            continue
        rows, fr, nt = read_frontier(path, src.get("declared") or {})
        fatal.extend(fr)
        notes.extend(nt)
        for r in rows:
            i = r["item_id"].strip()
            if i not in items:
                notes.append(f"{src['id']}: item {i} not in the 150-row family")
                continue
            raw_doms = [c for c in (canonical_domain(x) for x in
                                    ((r["domains"] or "") + "|" + (r["domains_secondary"] or "")).split("|")) if c]
            items[i]["coders"][src["id"]] = {
                "domains": raw_doms,
                "depth": labels.get(r["depth"].strip()),
                "conf_domain": (r["conf_domain"] or "").strip(),
                "conf_depth": (r["conf_depth"] or "").strip(),
                "rationale": (r["rationale"] or "").strip(),
                "boundary_condition": (r["boundary_condition"] or "").strip(),
                "authority": src["authority"],
            }
    return items, fatal, notes


def score(items: dict[str, dict[str, Any]], gold: dict[str, int], gconf: dict[str, str],
          cfg: dict[str, Any]) -> dict[str, Any]:
    """Compute per-row verdicts, inter-coder agreement and per-coder depth error against the owner."""
    th = cfg["thresholds"]
    coder_ids = sorted({c for it in items.values() for c in it["coders"]})
    per_row: list[dict[str, Any]] = []
    depth_vs_gold: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    depth_err: dict[str, list[int]] = collections.defaultdict(list)
    dom_pair_exact: collections.Counter = collections.Counter()
    dom_pair_primary: collections.Counter = collections.Counter()
    dom_pair_n: collections.Counter = collections.Counter()
    dom_pair_j: dict[tuple[str, str], list[float]] = collections.defaultdict(list)
    dep_pair_exact: collections.Counter = collections.Counter()
    dep_pair_n: collections.Counter = collections.Counter()
    dep_pair_dev: dict[tuple[str, str], list[int]] = collections.defaultdict(list)

    for item in sorted(items):
        it = items[item]
        coders = it["coders"]
        dom_coders = {c: set(v["domains"]) for c, v in coders.items() if v["domains"]}
        dep_coders = {c: v["depth"] for c, v in coders.items() if v["depth"]}
        dom_sets = list(dom_coders.values())
        dep_vals = list(dep_coders.values())
        union = set().union(*dom_sets) if dom_sets else set()
        inter = set.intersection(*dom_sets) if dom_sets else set()
        js = [jaccard(a, b) for i, a in enumerate(dom_sets) for b in dom_sets[i + 1:]]
        spread = (max(dep_vals) - min(dep_vals)) if dep_vals else 0
        # plurality is a MULTISET vote over coders (a set would count every label once and say nothing)
        all_labels = [x for s in dom_sets for x in s]
        plural = collections.Counter(all_labels)
        primaries = [s_prim for s_prim in
                     (next(iter(v["domains"])) for v in coders.values() if v["domains"])]
        flags: list[str] = []
        if dom_sets and not inter and len(dom_sets) >= th["domain_hard_min_coders"]:
            flags.append("DOMAIN_NO_OVERLAP")
        if spread >= th["depth_hard_spread"]:
            flags.append("DEPTH_HARD_SPLIT")
        if dom_sets and len(set(frozenset(s) for s in dom_sets)) > 1:
            flags.append("DOMAIN_DIFFERS")
        if len(primaries) >= 2 and len(set(primaries)) > 1:
            flags.append("PRIMARY_DOMAIN_DIFFERS")
        if len(set(dep_vals)) > 1:
            flags.append("DEPTH_DIFFERS")
        dom_plurality = plural.most_common(1)[0] if plural else ("", 0)
        dep_plurality = collections.Counter(dep_vals).most_common(1)[0] if dep_vals else (None, 0)
        if dom_plurality[1] and dom_sets and dom_plurality[1] / max(1, len(dom_sets)) < th["majority_min_share"]:
            flags.append("DOMAIN_NO_MAJORITY_LABEL")
        owner = gold.get(item)
        if owner is not None and dep_vals and dep_plurality[0] != owner:
            flags.append("OWNER_coder_majority_DIFFERS")
        tier = "HARD" if ("DOMAIN_NO_OVERLAP" in flags or "DEPTH_HARD_SPLIT" in flags) else \
            ("SOFT" if flags else ("AGREE" if len(coders) >= 2 else "SINGLE"))
        per_row.append({
            "item_id": item,
            "row": int(item[1:]),
            "n_coders": len(coders),
            "n_domain_coders": len(dom_sets),
            "n_depth_coders": len(dep_vals),
            "domain_union": "|".join(sorted(union)),
            "domain_intersection": "|".join(sorted(inter)),
            "domain_plurality": dom_plurality[0],
            "domain_plurality_share": round(dom_plurality[1] / max(1, len(dom_sets)), 3),
            "domain_jaccard_mean": round(statistics.mean(js), 3) if js else "",
            "depth_mean": round(statistics.mean(dep_vals), 2) if dep_vals else "",
            "depth_spread": spread,
            "depth_plurality": dep_plurality[0] or "",
            "owner_depth": owner if owner is not None else "",
            "owner_conf_depth": gconf.get(item, ""),
            "flags": ";".join(flags),
            "tier": tier,
            "coders": coders,
        })
        for c, v in coders.items():
            if owner is not None and v["depth"]:
                d = abs(v["depth"] - owner)
                depth_err[c].append(d)
                depth_vs_gold[c]["exact" if d == 0 else ("within1" if d == 1 else "far")] += 1
                depth_vs_gold[c][f"gold_{owner}"] += 1
        for c1, c2 in [(a, b) for i, a in enumerate(sorted(dom_coders)) for b in sorted(dom_coders)[i + 1:]]:
            dom_pair_n[(c1, c2)] += 1
            dom_pair_j[(c1, c2)].append(jaccard(dom_coders[c1], dom_coders[c2]))
            dom_pair_exact[(c1, c2)] += int(dom_coders[c1] == dom_coders[c2])
            dom_pair_primary[(c1, c2)] += int(next(iter(dom_coders[c1])) == next(iter(dom_coders[c2])))
        for c1, c2 in [(a, b) for i, a in enumerate(sorted(dep_coders)) for b in sorted(dep_coders)[i + 1:]]:
            dep_pair_n[(c1, c2)] += 1
            dep_pair_exact[(c1, c2)] += int(dep_coders[c1] == dep_coders[c2])
            dep_pair_dev[(c1, c2)].append(abs(dep_coders[c1] - dep_coders[c2]))
    stats = {
        "per_row": per_row,
        "depth_vs_gold": {c: dict(v) for c, v in depth_vs_gold.items()},
        "depth_err_mean": {c: round(statistics.mean(v), 3) for c, v in depth_err.items() if v},
        "domain_pair": {f"{a}~{b}": {"n": dom_pair_n[(a, b)], "exact": dom_pair_exact[(a, b)],
                                     "primary_exact": dom_pair_primary[(a, b)],
                                     "jaccard_mean": round(statistics.mean(dom_pair_j[(a, b)]), 3)}
                        for (a, b) in sorted(dom_pair_n)},
        "depth_pair": {f"{a}~{b}": {"n": dep_pair_n[(a, b)], "exact": dep_pair_exact[(a, b)],
                                    "mean_abs_class_diff": round(statistics.mean(dep_pair_dev[(a, b)]), 3)}
                       for (a, b) in sorted(dep_pair_n)},
        "coder_ids": coder_ids,
    }
    return stats


def write_outputs(cfg: dict[str, Any], items: dict[str, dict[str, Any]], stats: dict[str, Any],
                  gold: dict[str, int], notes: list[str]) -> list[str]:
    """Write the long CSV, the owner workbook, the stats JSON and the report. Returns the paths written."""
    out = {k: REPO / v for k, v in cfg["outputs"].items()}
    written: list[str] = []
    cols = ["item_id", "row", "n_coders", "n_domain_coders", "n_depth_coders", "tier", "flags",
            "domain_union", "domain_intersection", "domain_plurality", "domain_plurality_share",
            "domain_jaccard_mean", "depth_mean", "depth_spread", "depth_plurality",
            "owner_depth", "owner_conf_depth"]
    with out["long_csv"].open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in stats["per_row"]:
            w.writerow(r)
    written.append(str(out["long_csv"].relative_to(REPO)))
    coders = stats["coder_ids"]
    wb_cols = ["item_id", "row", "tier", "flags", "name"] + [f"{c}_depth" for c in coders] + \
              [f"{c}_domains" for c in coders] + ["owner_depth", "owner_plurality_note"] + WORKBOOK_OWNER_COLS
    dispute = [r for r in stats["per_row"] if r["tier"] in ("HARD", "SOFT") or r["flags"]]
    dispute.sort(key=lambda r: (0 if r["tier"] == "HARD" else 1, r["row"]))
    with out["workbook"].open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=wb_cols, extrasaction="ignore")
        w.writeheader()
        for r in dispute:
            rec = {"item_id": r["item_id"], "row": r["row"], "tier": r["tier"], "flags": r["flags"],
                   "owner_depth": r["owner_depth"]}
            for c in coders:
                v = r["coders"].get(c) or {}
                rec[f"{c}_depth"] = v.get("depth", "")
                rec[f"{c}_domains"] = "|".join(v.get("domains") or [])
            rec["owner_plurality_note"] = ("coder plurality == owner depth" if r["depth_plurality"] == r["owner_depth"]
                                           and r["owner_depth"] != "" else
                                           "CODERS vs OWNER: check this row first" if r["owner_depth"] != "" else "")
            for k in WORKBOOK_OWNER_COLS:
                rec[k] = ""
            w.writerow(rec)
    written.append(str(out["workbook"].relative_to(REPO)))
    out["stats_json"].write_text(json.dumps({"sources": cfg["sources"], "notes": notes,
                                             "thresholds": cfg["thresholds"], **stats}, indent=1),
                                encoding="utf-8")
    written.append(str(out["stats_json"].relative_to(REPO)))
    out["report_md"].write_text(render_report(cfg, stats, notes, len(dispute)), encoding="utf-8")
    written.append(str(out["report_md"].relative_to(REPO)))
    return written


def render_report(cfg: dict[str, Any], stats: dict[str, Any], notes: list[str], n_dispute: int) -> str:
    """Render the human report: coverage, agreement structure, per-coder error, dispute set, recommendation."""
    per_row = stats["per_row"]
    tiers = collections.Counter(r["tier"] for r in per_row)
    flags = collections.Counter(f for r in per_row for f in r["flags"].split(";") if f)
    L: list[str] = ["# ANCHOR two-axis cross-examination - 2026-09-24", "",
                    "Deterministic, LLM-free comparison of every independent reading of the ANCHOR's DOMAIN and DEPTH",
                    "axes. Generated by `scripts/cross_examine_anchor_axes.py`; sources and declared coverage are in",
                    "`config/anchor_cross_exam.yaml`. Authority: machine/frontier rows are ADVISORY; only the owner",
                    "writes a `*_final` value.", "",
                    "## 1. Coverage ledger", "",
                    "| source | axes | authority | declared rows | delivered | gap |",
                    "|---|---|---|---|---|---|"]
    for src in cfg["sources"]:
        d = src.get("declared") or {}
        if src["kind"] == "declared_missing":
            L.append(f"| {src['id']} | {','.join(src['axes'])} | {src['authority']} | - | **0 (not delivered)** | "
                     f"{src['path'].split('/')[-1]} |")
        else:
            got = sum(1 for r in per_row if src["id"] in r["coders"] and
                      (r["coders"][src["id"]]["domains"] or r["coders"][src["id"]]["depth"]))
            L.append(f"| {src['id']} | {','.join(src['axes'])} | {src['authority']} | {d.get('rows','-')} | {got} | "
                     f"{'none' if got == d.get('rows') else 'MISMATCH'} |")
    L += ["", "## 2. Format and integrity notes", ""]
    L += [f"- {n}" for n in notes] or ["- none"]
    L += ["", "## 3. Verdict per row", "", "| tier | rows |", "|---|---|"]
    for t in ("AGREE", "SOFT", "HARD", "SINGLE"):
        L.append(f"| {t} | {tiers.get(t, 0)} |")
    L += ["", "flag counts: " + (", ".join(f"`{k}`={v}" for k, v in flags.most_common()) or "none"), "",
          "## 4. Depth error against the OWNER's pass (gold, 150/150)", "",
          "| coder | n | exact | within 1 | >=2 off | mean abs diff |", "|---|---|---|---|---|---|"]
    for c, v in sorted(stats["depth_vs_gold"].items()):
        n = v.get("exact", 0) + v.get("within1", 0) + v.get("far", 0)
        L.append(f"| {c} | {n} | {v.get('exact',0)} ({round(100*v.get('exact',0)/max(1,n))}%) | "
                 f"{v.get('within1',0)} | {v.get('far',0)} | {stats['depth_err_mean'].get(c,'-')} |")
    L += ["", "## 5. Inter-coder agreement", "", "DOMAIN (set overlap; primary = the coder's most central label)", "",
          "| pair | n | identical set | identical PRIMARY | mean Jaccard |", "|---|---|---|---|---|"]
    for k, v in stats["domain_pair"].items():
        L.append(f"| {k} | {v['n']} | {v['exact']} ({round(100*v['exact']/max(1,v['n']))}%) | "
                 f"{v['primary_exact']} ({round(100*v['primary_exact']/max(1,v['n']))}%) | {v['jaccard_mean']} |")
    L += ["", "DEPTH (ordinal)", "", "| pair | n | identical class | mean abs class diff |", "|---|---|---|---|"]
    for k, v in stats["depth_pair"].items():
        L.append(f"| {k} | {v['n']} | {v['exact']} ({round(100*v['exact']/max(1,v['n']))}%) | "
                 f"{v['mean_abs_class_diff']} |")
    L += ["", f"## 6. The dispute set - {n_dispute} rows for ONE owner session", "",
          "`governance/anchor_adjudication_workbook_20260924.csv` - ordered HARD split first, owner columns EMPTY.",
          "The workbook is the instrument: do not pre-filter it, and do not let a coder's plurality anchor the cell.", "",
          "## 7. Recommendation", "",
          "1. **Do not average or majority-vote the coders.** With four independent readings the mean is not a label,",
          "   and a plurality that gets written into a frozen sheet becomes unrecoverable provenance.",
          "2. **Adjudicate the dispute set only, on the workbook**, and record `domains_final` / `depth_final` there.",
          "3. **Score, never adopt, the frontier coders**: their depth error against the owner's pass is the honest",
          "   release gate for the S4 depth head (D274d) and for the D274f test-retest.",
          "4. **Close the coverage gaps before finalising**: Claude chunks 1-50 / 51-100 and Kimi R146-R150 are owed;",
          "   without them the domain axis is 2-coder on 100 of 150 rows.",
          "5. **Any coder file that changes must change its declared sha256** in `config/anchor_cross_exam.yaml` - the",
          "   run fails closed otherwise, so the ruler sample can never be silently re-scoped.", "",
          "## 8. Files", "",
          "- long CSV: `governance/anchor_axis_coders_20260924.csv`",
          "- workbook: `governance/anchor_adjudication_workbook_20260924.csv`",
          "- stats: `governance/anchor_axis_cross_exam_20260924.json`", ""]
    return "\n".join(L)


def main() -> int:
    """Run the cross-examination; `--check` audits coverage only and never writes."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="coverage + lock audit only, no scoring outputs")
    args = ap.parse_args()
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    items, fatal, notes = collect(cfg)
    for n in notes:
        print("  note: " + n)
    if fatal:
        print("FAIL cross-exam: the sample changed or a declared coverage bound was broken (refusing to score)")
        for n in fatal:
            print("  !! " + n)
        return 1
    if not items:
        print("FAIL cross-exam: no items collected")
        return 1
    gold, gconf, gnotes = read_owner_gold(cfg)
    notes.extend(gnotes)
    if gnotes:
        print("FAIL cross-exam: owner gold refused")
        for n in gnotes:
            print("  ", n)
        return 1
    stats = score(items, gold, gconf, cfg)
    hard = sum(1 for r in stats["per_row"] if r["tier"] == "HARD")
    print(f"coverage: gold={len(gold)}/150 rows; coders={stats['coder_ids']}")
    print(f"depth vs owner: " + ", ".join(f"{c}={stats['depth_vs_gold'].get(c,{}).get('exact',0)}exact/"
                                          f"{sum(stats['depth_vs_gold'].get(c,{}).get(k,0) for k in ('exact','within1','far'))}n"
                                          for c in stats["coder_ids"] if c in stats["depth_vs_gold"]))
    print(f"disputes: HARD={hard} of {len(stats['per_row'])} rows")
    if args.check:
        print("check only - nothing written")
        return 0
    for p in write_outputs(cfg, items, stats, gold, notes):
        print("wrote", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
