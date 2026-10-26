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
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
from lib import artifact_encoding  # noqa: E402 - D-2646: the decode rule has ONE home
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


def pipeline_commit() -> str:
    """Return the short HEAD commit, so every generated artifact is traceable to a code state (R14)."""
    try:
        return subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, check=False).stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def stamp() -> dict[str, Any]:
    """Return the R14 provenance stamp carried by every persistent object this script writes."""
    return {"schema_version": "1.0", "artifact_id": "ANCHOR-AXIS-CROSS-EXAM",
            "gen_model": "none (deterministic, LLM-free)", "gen_temperature": 0.0,
            "pipeline_commit": pipeline_commit(),
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}


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
    text = artifact_encoding.open_artifact(path, REPO).read()  # BUG-511: no silent U+FFFD; the declaration decides
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
    if not seen_header:
        if declared.get("prepend_header"):
            kept = [",".join(HEADER)] + kept
            notes.append(f"DECLARED HEADERLESS FRAGMENT {path.name}: {len(kept) - 1} data line(s), no header line - "
                         f"the reply CONTINUES the declared header of this coder's earlier chunk")
        else:
            return [], fatal + [f"{path.name}: header mismatch"], notes
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
        if declared.get("expect_coder") and (r["coder"] or "").strip() != declared["expect_coder"]:
            fatal.append(f"{path.name}:{i}: coder '{(r['coder'] or '').strip()}' != declared "
                         f"'{declared['expect_coder']}' - a reply from a different model is a different source")
        if r["depth"].strip() == "none_fits":
            notes.append(f"MENU DECLINED {path.name}:{i}: the coder returned 'none_fits' on the DEPTH axis (and, "
                         f"where domains are empty, on DOMAIN too). That is a disagreement with the MENU, not a "
                         f"missing value - it must reach the owner, never be coerced into a class")
        out.append(r)
    if short:
        msg = f"{path.name}: {len(short)} partial record(s) at the tail {short[:3]}"
        if declared.get("allow_truncated_tail"):
            if declared.get("tail_superseded_by"):
                notes.append(f"HISTORICAL BOUNDARY {msg} - the reply was cut by the coder's output cap; those rows "
                             f"were delivered later and are declared separately as {declared['tail_superseded_by']}")
            else:
                notes.append(f"DECLARED SHORTFALL {msg} - the reply was cut by the coder's output cap")
        else:
            fatal.append(f"{msg} - reply is truncated, refused")
    m = re.search(r"rows_expected=(\d+)\s+rows_emitted=(\d+)", text)
    if declared.get("self_check"):
        if not m:
            fatal.append(f"{path.name}: declared self-check line is absent from the reply")
        elif int(m.group(2)) != len(out):
            fatal.append(f"{path.name}: the coder's own self-check says rows_emitted={m.group(2)} but {len(out)} valid "
                         f"row(s) parsed - never score a file whose own count disagrees with the parse")
        else:
            notes.append(f"{path.name}: coder self-check rows_expected={m.group(1)} rows_emitted={m.group(2)} "
                         f"- agrees with the parse")
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
    with artifact_encoding.open_artifact(sheet, REPO) as fh:
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
    # NAMES come from the SHARED blind input (one source of truth), never from a coder's reply: a title typed by
    # a model would be a second, drifting copy of the anchor. Fail closed if the blind input is gone.
    blind = REPO / cfg.get("blind_input", "governance/frontier_pack_20260924/BLIND_INPUT_150.csv")
    if not blind.exists():
        return items, [f"blind input {blind} is missing - the workbook cannot carry row names, refusing"], []
    with artifact_encoding.open_artifact(blind, REPO) as fh:
        for row in csv.DictReader(fh):
            if row.get("item_id") in items:
                items[row["item_id"]]["name"] = (row.get("name") or "").strip()
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
                                                       "depth_declined": False,
                                                       "source_path": src["path"],
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
            prev = items[i]["coders"].get(src["id"])
            if prev is not None and prev.get("source_path") != src["path"]:
                fatal.append(f"{src['id']}:{i} was coded TWICE from different files "
                             f"({prev.get('source_path')} and {src['path']}) - a chunked delivery must be disjoint")
            raw_doms = [c for c in (canonical_domain(x) for x in
                                    ((r["domains"] or "") + "|" + (r["domains_secondary"] or "")).split("|")) if c]
            items[i]["coders"][src["id"]] = {
                "domains": raw_doms,
                "depth": labels.get(r["depth"].strip()),
                "depth_declined": r["depth"].strip() == "none_fits",
                "conf_domain": (r["conf_domain"] or "").strip(),
                "conf_depth": (r["conf_depth"] or "").strip(),
                "rationale": (r["rationale"] or "").strip(),
                "boundary_condition": (r["boundary_condition"] or "").strip(),
                "source_path": src["path"],
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
        if any(v.get("depth_declined") for v in coders.values()):
            flags.append("DEPTH_MENU_DECLINED")
        dom_plurality = plural.most_common(1)[0] if plural else ("", 0)
        # a label being PRESENT in a set is weaker than a coder LEADING with it, so the two are stored apart:
        # domain_plurality_share counts membership, primary_share counts coders whose FIRST label it is.
        pri_plural = collections.Counter(primaries).most_common(1)[0] if primaries else ("", 0)
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
            "primary_plurality": pri_plural[0],
            "primary_share": round(pri_plural[1] / max(1, len(primaries)), 3) if primaries else "",
            "name": it.get("name", ""),
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


def recommend_row(r: dict[str, Any], th: dict[str, Any]) -> tuple[str, str, str]:
    """Return (recommendation, basis, owner_answer_needed) for one disputed row. ADVISORY - never a `*_final`.

    A recommendation is emitted only where the coders can carry it (a real plurality). Everywhere else the
    honest output is OWNER_ONLY. Depth recommendations never invent a class: they NAME the dispute and say
    which one your ruling would teach. A row is only asked about on an axis that is actually in dispute.
    """
    flags = set(f for f in r["flags"].split(";") if f)
    n_dom, n_dep = r["n_domain_coders"], r["n_depth_coders"]
    has_dom = n_dom == 0 or any(f.startswith(("DOMAIN_", "PRIMARY_DOMAIN")) or
                                f == "OWNER_coder_majority_DIFFERS" for f in flags)
    has_dep = n_dep == 0 or any(f.startswith("DEPTH_") for f in flags)
    basis: list[str] = []
    need: list[str] = []
    if not has_dom:
        dom_r = "domain=no dispute"
    elif n_dom == 0:
        dom_r = "domain=NO_ANSWER"
        need.append("domain")
        basis.append("no coder answered the domain axis")
    else:
        share = float(r["domain_plurality_share"] or 0)
        pri = r.get("primary_plurality") or ""
        pri_share = float(r.get("primary_share") or 0)
        if pri and pri_share >= float(th["majority_min_share"]):
            dom_r = f"domain={pri} as PRIMARY"
            need.append("domain")
            basis.append(f"{int(round(pri_share * n_dom))}/{n_dom} coders LEAD with {pri} - confirm it, or replace it "
                         f"if it is wrong (it is also shared by {share:.2f} of the coder sets)")
        else:
            dom_r = "domain=OWNER_ONLY"
            need.append("domain")
            basis.append(f"no label is LED by half the coders (best primary share {pri_share:.2f} of {n_dom}, "
                         f"best set-membership share {share:.2f}) - the PRIMARY label is yours to name; "
                         f"the coder sets stay in this row as provenance")
    if not has_dep:
        dep_r = "depth=no dispute"
    elif any(v.get("depth_declined") for v in r["coders"].values()):
        dep_r = "depth=NOT_A_CLAIM?"
        need.append("depth")
        basis.append("a coder REFUSED the menu ('none_fits') - decide whether the row is a claim at all")
    elif n_dep == 0:
        dep_r = "depth=NO_ANSWER"
        need.append("depth")
        basis.append("no coder answered the depth axis")
    elif r["depth_spread"] == 0 and r["depth_plurality"] == r["owner_depth"]:
        dep_r = f"depth=KEEP owner {r['owner_depth']}"
        basis.append("all coders agree with your depth - nothing to do")
    elif r["depth_spread"] == 0:
        dep_r = "depth=CHECK_OWNER_FIRST"
        need.append("depth")
        basis.append(f"all coders say {r['depth_plurality']} where you said {r['owner_depth']} - a CLEAN signal, "
                     f"so read it first: either your cell or the rubric is off, and it is cheap to tell which")
    elif int(r["depth_spread"]) >= int(th["depth_hard_spread"]):
        dep_r = "depth=RECODE_BAND"
        need.append("depth")
        basis.append(f"coders span {r['depth_spread']} classes - name the boundary in the rubric and re-code this band")
    else:
        dep_r = "depth=OWNER_RULING_NEAR"
        need.append("depth")
        basis.append(f"coders differ by ONE class (mean D{r['depth_mean']}) - this is the D2/D3 boundary; "
                     f"a ruling here is what teaches the rubric")
    return f"{dom_r}; {dep_r}", " | ".join(basis), ";".join(need)


def render_review(stats: dict[str, Any], dispute: list[dict[str, Any]], th: dict[str, Any]) -> str:
    """Render the readable review sheet: one block per disputed row, before anything is consolidated."""
    coders = stats["coder_ids"]
    L: list[str] = ["# ANCHOR adjudication - REVIEW SHEET (read this before the CSV)", "",
                    "Every row the cross-examination puts in front of you, with what each independent reader said and",
                    "the recommendation this repo can defend. Advisory only: your `*_final` values are written by you,",
                    "in the workbooks CSV (`governance/anchor_adjudication_workbook_20260924.csv`), whose owner",
                    "columns are EMPTY and must stay empty until you type in them.", "",
                    "`machine_recommendation` legend: `domain=<label> as PRIMARY` = a coder plurality exists, confirm",
                    f"or replace | `domain=OWNER_ONLY` = no label reaches share {th['majority_min_share']}, yours to name |",
                    "`depth=KEEP` = coders agree with you, nothing to do | `depth=CHECK_OWNER_FIRST` = coders agree with",
                    "EACH OTHER against you, so it is a clean signal about the cell or the rubric | `depth=OWNER_RULING_NEAR`",
                    "= one class apart, the D2/D3 boundary | `depth=RECODE_BAND` = span >= 2 classes, do not adjudicate it,",
                    "re-code it | `depth=NOT_A_CLAIM?` = a coder refused the menu.", ""]
    for tier in ("HARD", "SOFT"):
        rows = [r for r in dispute if r["tier"] == tier]
        L += [f"## {tier} ({len(rows)} rows)", ""]
        for r in rows:
            rec, why, need = recommend_row(r, th)
            L.append(f"### {r['item_id']} - {r['name'][:90] or '(no name)'}")
            L.append("- **coders** - " + " | ".join(
                f"{c}: d={(r['coders'].get(c) or {}).get('depth') if not (r['coders'].get(c) or {}).get('depth_declined') else 'none_fits'}"
                f" / {'|'.join((r['coders'].get(c) or {}).get('domains') or []) or '-'}" for c in coders))
            L.append(f"- **owner depth** {r['owner_depth'] or '-'} (conf {r['owner_conf_depth'] or '-'}) | "
                     f"coder spread {r['depth_spread']} | domain union: {r['domain_union'] or '-'}")
            L.append(f"- **RECOMMEND** `{rec}`")
            L.append(f"- why: {why}")
            L.append(f"- **you must answer: {need or 'nothing'}**")
            if r["flags"]:
                L.append(f"- flags: `{r['flags']}`")
            L.append("")
    return "\n".join(L) + "\n"


def _write_owner_workbook(cfg: dict[str, Any], path: pathlib.Path, cols: list[str],
                          recs: list[dict[str, Any]], written: list[str]) -> None:
    """CREATE the owner's blind workbook once, or leave it exactly as it is (BUG-478 root).

    WHY. This path used to open the workbook with mode "w" and rebuild it from the dispute set, blanking every
    column in WORKBOOK_OWNER_COLS. MEASURED 2026-09-25: the artifact carries 148 rows of the owner's typed
    adjudication (depth_final, owner_date, domains_final), so the documented way to run a cross-exam was one
    command away from destroying the instrument it exists to produce. config/artifact_ownership.yaml did not
    merely omit this writer, it named it under machine_writers_forbidden: the declaration was right and the code
    was wrong. Repair: a machine may CREATE this file when it is ABSENT (the blind instrument has to come from
    somewhere) and may never rewrite one, and even the creation goes through write_guard.append_rows, so every
    row is addressable by item_id and every column it fills is declared. Filling a panel column is
    scripts/ingest_panel_column.py (D-398), never this script.
    """
    import sys as _sys
    _sys.path.insert(0, str(REPO / "scripts"))
    from lib import write_guard
    create_only = (cfg.get("outputs") or {}).get("workbook_create_only")
    if create_only is None:
        raise SystemExit("REFUSING: config/anchor_cross_exam.yaml#outputs.workbook_create_only is not declared "
                         "- a machine may not write the owner's instrument on an UNDECLARED default (C12, "
                         "BUG-478: the default is how an owner artifact gets rewritten silently)")
    rel = str(path.relative_to(REPO))
    if create_only and path.exists():
        print("  SKIP workbook " + rel + ": it EXISTS - a machine may create this instrument once and never "
              "rewrite it (BUG-478 root; the owner's typed cells ARE the instrument, D-398)")
        return
    rep = write_guard.append_rows(path, recs, owned_keys=set(cols), writer=pathlib.Path(__file__).resolve()
                                  .relative_to(REPO).as_posix(), id_column="item_id", columns=cols,
                                  backup=False, journal=True)
    print("  ok   workbook " + rel + " CREATED (" + str(rep.added) + " row(s), sha16 " + rep.post_sha16 + ")")
    written.append(rel)


def write_outputs(cfg: dict[str, Any], items: dict[str, dict[str, Any]], stats: dict[str, Any],
                  gold: dict[str, int], notes: list[str]) -> list[str]:
    """Write the long CSV, the owner workbook, the stats JSON and the report. Returns the paths written."""
    out = {k: REPO / v for k, v in cfg["outputs"].items()}
    written: list[str] = []
    cols = ["item_id", "row", "n_coders", "n_domain_coders", "n_depth_coders", "tier", "flags", "name",
            "domain_union", "domain_intersection", "domain_plurality", "domain_plurality_share",
            "primary_plurality", "primary_share",
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
              [f"{c}_domains" for c in coders] + ["owner_depth", "owner_plurality_note",
                                                  "machine_recommendation", "recommendation_basis",
                                                  "owner_answer_needed"] + WORKBOOK_OWNER_COLS
    dispute = [r for r in stats["per_row"] if r["tier"] in ("HARD", "SOFT") or r["flags"]]
    dispute.sort(key=lambda r: (0 if r["tier"] == "HARD" else 1, r["row"]))
    wb_recs: list[dict[str, Any]] = []
    for r in dispute:
            rec = {"item_id": r["item_id"], "row": r["row"], "tier": r["tier"], "flags": r["flags"],
                   "name": r.get("name", ""), "owner_depth": r["owner_depth"]}
            for c in coders:
                v = r["coders"].get(c) or {}
                rec[f"{c}_depth"] = ("none_fits" if v.get("depth_declined") else v.get("depth", ""))
                rec[f"{c}_domains"] = "|".join(v.get("domains") or [])
            rec["owner_plurality_note"] = ("coder plurality == owner depth" if r["depth_plurality"] == r["owner_depth"]
                                           and r["owner_depth"] != "" else
                                           "CODERS vs OWNER: check this row first" if r["owner_depth"] != "" else "")
            rec["machine_recommendation"], rec["recommendation_basis"], rec["owner_answer_needed"] = \
                recommend_row(r, cfg["thresholds"])
            for k in WORKBOOK_OWNER_COLS:
                rec[k] = ""
            wb_recs.append(rec)
    _write_owner_workbook(cfg, out["workbook"], wb_cols, wb_recs, written)
    out["review_md"].write_text(render_review(stats, dispute, cfg["thresholds"]), encoding="utf-8")
    written.append(str(out["review_md"].relative_to(REPO)))
    out["stats_json"].write_text(json.dumps({"stamp": stamp(), "sources": cfg["sources"], "notes": notes,
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
    L: list[str] = ["# ANCHOR two-axis cross-examination - anchor family 2026-09-23, coder pass 2026-09-24, coverage completed 2026-09-25", "",
                    "Deterministic, LLM-free comparison of every independent reading of the ANCHOR's DOMAIN and DEPTH",
                    "axes. Generated by `scripts/cross_examine_anchor_axes.py`; sources and declared coverage are in",
                    "`config/anchor_cross_exam.yaml`. Authority: machine/frontier rows are ADVISORY; only the owner",
                    "writes a `*_final` value.", "",
                    f"Run stamp: pipeline_commit `{pipeline_commit()}` | deterministic (no LLM, temp not applicable) | "
                    f"generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}", "",
                    "## 1. Coverage ledger", "",
                    "| source | axes | authority | declared rows | delivered | gap |",
                    "|---|---|---|---|---|---|"]
    for src in cfg["sources"]:
        d = src.get("declared") or {}
        if src["kind"] == "declared_missing":
            L.append(f"| {src['id']} | {','.join(src['axes'])} | {src['authority']} | - | **0 (not delivered)** | "
                     f"{src['path'].split('/')[-1]} |")
        else:
            got = sum(1 for r in per_row if (r["coders"].get(src["id"]) or {}).get("source_path") == src["path"])
            L.append(f"| {src['id']} | {','.join(src['axes'])} | {src['authority']} | {d.get('rows','-')} | {got} | "
                     f"{'none' if got == d.get('rows') else 'MISMATCH'} |")
    L += ["", "Per coder - all files of one model merged. This is the number that decides whether an axis is",
          "measurable at all, and it is NOT the same as the file list above:", "",
          "| coder | rows with domains | rows with depth | files |", "|---|---|---|---|"]
    for c in stats["coder_ids"]:
        dom = sum(1 for r in per_row if (r["coders"].get(c) or {}).get("domains"))
        dep = sum(1 for r in per_row if (r["coders"].get(c) or {}).get("depth"))
        files = sorted({(r["coders"].get(c) or {}).get("source_path") for r in per_row if r["coders"].get(c)})
        L.append(f"| {c} | {dom}/150 | {dep}/150 | {' + '.join(f.split('raw_')[-1] for f in files)} |")
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
          "1. **Do not average or majority-vote the coders.** The mean of ordinal classes is not a label, and a",
          "   plurality written into a frozen sheet becomes unrecoverable provenance. Coders stay advisory; the",
          "   owner's adjudication is the only path from a reading to a `*_final` value.",
          "2. **Adjudicate the dispute set only**, on `governance/anchor_adjudication_workbook_20260924.csv`",
          "   (owner columns EMPTY). Ask for the PRIMARY domain label and the depth class; the coder sets stay in",
          "   the same row as secondary provenance.",
          "3. **Depth is now 2 coders on all 150 rows - that is enough for a cross-check, not for a verdict.**",
          "   Both frontier coders sit below the ruler bar against the owner's pass and the disagreement clusters",
          "   on the D2/D3 boundary, so the remaining depth error is a RUBRIC problem before it is a coder problem.",
          "4. **Fix the depth rubric and re-measure the disputed band only.** Add a 2-3 row worked-example annex for",
          "   the cross-domain/domain boundary to `taxonomy_domain_depth.md`, then re-run the frontier pair on the",
          "   disputed rows. Do NOT train the S4 depth head on these labels (D274d).",
          "5. **Score, never adopt, the frontier coders**: their depth error against the owner's pass is the honest",
          "   release gate for the S4 head (D274d) and for the D274f test-retest.",
          "6. **Every coder file must declare its fingerprint** in `config/anchor_cross_exam.yaml` - rows, first/last",
          "   item_id, sha256, expected coder. A changed, shrunken, re-scoped or mis-attributed file fails the run",
          "   closed, and a chunked delivery that overlaps another chunk of the SAME coder is refused rather than",
          "   silently overwritten. Freeze the coder roster + hashes as part of the anchor family definition so a",
          "   later session physically cannot re-code the ruler sample.", "",
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
    for c in stats["coder_ids"]:
        dom = sum(1 for r in stats["per_row"] if (r["coders"].get(c) or {}).get("domains"))
        dep = sum(1 for r in stats["per_row"] if (r["coders"].get(c) or {}).get("depth"))
        print(f"  per coder {c}: domains {dom}/150, depth {dep}/150")
    print("depth vs owner: " + ", ".join(f"{c}={stats['depth_vs_gold'].get(c,{}).get('exact',0)}exact/"
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
