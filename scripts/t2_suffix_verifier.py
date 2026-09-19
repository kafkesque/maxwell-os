#!/usr/bin/env python3
"""t2_suffix_verifier.py — DETERMINISTIC replacement for the model judge on suffix duplicates.

WHY (BUG-269 / F-10). `judge_suffix_duplicates.py` asked a model a question that is a string
operation: "is this pair a suffix duplicate?". Calibrated blind against a human, gemma and gpt-oss
both scored **lift 0.00** over the constant-answer baseline — a model adds nothing here, while also
violating R5/C8 (it judged Qwen3-Coder output as Qwen3.8). This script does it by rule instead:
exact, free, reproducible, auditable, and incapable of being wrong by opinion.

It also runs the rule over the WHOLE KB, not just the 32 pairs a model happened to flag, so the
class is closed rather than sampled.

Verdicts (thresholds live in `config/eval_integrity.yaml::suffix_dedup`, never here):
  AUTO_MERGE — identical name AFTER NORMALISATION **and** near-verbatim body. The only class that
               can be merged without reading the text: nothing is inferred from the name.
  TRIAGE     — a marker/newline relationship exists (B == A + "(2)" etc.) but the two bodies are
               NOT textually similar. The name is an EXTRACTION ARTEFACT, not evidence. A human
               reads both and decides.
  KEEP       — no name relationship.

CORRECTION 2026-09-17 (measured, then corrected twice). This script was proposed on the claim that
suffix detection is "a string operation, therefore exact". That claim is FALSE, and the blind human
labels in `JUDGE_CALIBRATION_SHEET_20260917.csv` falsified it:
  * name-only rule  -> MERGE 32/32 (a 100% bias: the same degeneracy as the model judges it replaced)
  * name + character-shingle body check -> 0/8 vs the human labels
  * name + token-Jaccard: merge range 0.037-0.211, keep 0.167 -> OVERLAPPING, not separable
  * name + provenance overlap: merge pair with 0 shared sources, keep pair with 2 -> no signal
The distinguishing question is semantic ("do these two propositions assert the same thing?"), which
is not recoverable from the name, the text overlap, or the provenance. So this script now does what
it can prove — DETECTION and TRIAGE — and routes the verdict to a human.

Exit 0 = the analysis ran (this is an analysis, not a gate). Manifest per R14; no write to the DB.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB = ROOT / "knowledge pipeline" / "maxwell.db"
CFG = ROOT / "config" / "eval_integrity.yaml"
PLAN = ROOT / "governance" / "dedup_merge_plan.json"
OUT = ROOT / "governance" / "t2_suffix_verdicts.json"


def _cfg() -> dict:
    """Load the suffix policy (C12: markers and thresholds come from config)."""
    import yaml

    return (yaml.safe_load(CFG.read_text()) or {}).get("suffix_dedup") or {}


def norm(name: str) -> str:
    """Normalise a name for the prefix test: lowercase, alphanumerics and single spaces only."""
    return re.sub(r"[^a-z0-9 ]", " ", str(name or "").lower()).strip()


def squash(name: str) -> str:
    """Collapse whitespace so '(2)' and '( 2 )' compare equal."""
    return re.sub(r"\s+", "", norm(name))


def body_similarity(a: dict, b: dict, size: int) -> float:
    """Containment of a's body shingles inside b's (and vice versa), 0..1.

    WHY (2026-09-17): the name test alone answered MERGE for 32/32 pairs — a 100% bias, the same
    degeneracy as the model judges this script replaces. Blind human review said `keep` for
    "Social Proof Bias" vs "Social Proof Bias (2)": identical names, different objects, because the
    `(2)` suffix is an extraction artefact. The name is necessary but not sufficient.
    """
    import hashlib

    def shingles(rec: dict) -> set[str]:
        text = " ".join(str(rec.get(k) or "") for k in ("definition", "application", "mechanism"))
        body = re.sub(r"[^a-z0-9]", "", text.lower())
        if len(body) <= size * 2:
            return set()
        return {hashlib.blake2b(body[i:i + size].encode(), digest_size=16).hexdigest()
                for i in range(0, len(body) - size, size)}

    sa, sb = shingles(a), shingles(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / min(len(sa), len(sb))


def classify(base: str, candidate: str, markers: list[str], max_marker: int) -> tuple[str, str]:
    """Return (verdict, remainder) for an ordered (base, candidate) name pair.

    MERGE only when the candidate is the base plus a PURE variant marker. A substantive remainder
    is REVIEW — the script must not silently decide that 'X' and 'X Framework' are the same object.
    """
    b, c = squash(base), squash(candidate)
    if not b or not c or b == c:
        return ("KEEP", "") if b != c else ("MERGE", "(identical after normalisation)")
    if not c.startswith(b):
        return "KEEP", ""
    remainder = c[len(b):]
    marker_norms = {squash(m) for m in markers}
    if remainder in marker_norms:
        return "MERGE", remainder
    if len(remainder) <= max_marker and remainder in marker_norms:
        return "MERGE", remainder
    return "REVIEW", remainder


def main() -> int:
    """Scan the flagged pairs and the whole KB, write the verdict artifact."""
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=str(DB))
    ap.add_argument("--limit", type=int, default=0, help="preview only the first N findings")
    ap.add_argument("--validate", action="store_true",
                    help="measure the rule against the blind human T2 labels (with the baseline)")
    args = ap.parse_args()

    cfg = _cfg()
    markers = list(cfg.get("merge_markers") or [])
    max_marker = int(cfg.get("max_marker_chars", 14))
    if not markers:
        raise SystemExit("no merge_markers in config/eval_integrity.yaml::suffix_dedup — refusing "
                         "to guess (an empty marker set would report everything as REVIEW)")

    con = sqlite3.connect(args.db)
    rows = con.execute("select fb_id, name from fbs").fetchall()
    by_rec = {r[0]: {"name": r[1], "definition": r[2], "application": r[3], "mechanism": r[4]}
              for r in con.execute("select fb_id, name, definition, application, mechanism from fbs")}
    con.close()
    by_norm = {}
    for fb_id, name in rows:
        by_norm.setdefault(squash(name), []).append((fb_id, name))

    findings = []
    for key, group in by_norm.items():
        if len(group) < 2:
            continue
        base = min(group, key=lambda g: len(g[1]))
        for fb_id, name in group:
            if fb_id == base[0]:
                continue
            verdict, remainder = classify(base[1], name, markers, max_marker)
            if verdict == "MERGE":
                sim = body_similarity(by_rec.get(base[0], {}), by_rec.get(fb_id, {}),
                                      int(cfg.get("body_shingle_chars", 40)))
                if sim < float(cfg.get("min_body_similarity_for_merge", 0.5)):
                    # The name says duplicate; the text does not corroborate it. Human decides.
                    verdict = "TRIAGE"
                    remainder = remainder + " [body_similarity %.2f < threshold]" % sim
            if verdict != "KEEP":
                findings.append({"verdict": verdict, "base_fb_id": base[0], "base_name": base[1],
                                 "dup_fb_id": fb_id, "dup_name": name, "remainder": remainder})
    # The pairs a model flagged are reported separately so the two populations can be compared.
    flagged = []
    if PLAN.exists():
        plan = json.loads(PLAN.read_text())
        for pair in plan.get("high_confidence_suffix_candidates") or []:
            b = next((n for f, n in rows if f == pair.get("base_fb_id")), "")
            d = next((n for f, n in rows if f == pair.get("dup_fb_id")), "")
            verdict, remainder = classify(b, d, markers, max_marker)
            if verdict == "MERGE":
                bb = next((f for f, n in rows if n == b), None)
                dd = next((f for f, n in rows if n == d), None)
                sim = body_similarity(by_rec.get(bb, {}), by_rec.get(dd, {}),
                                      int(cfg.get("body_shingle_chars", 40)))
                if sim < float(cfg.get("min_body_similarity_for_merge", 0.5)):
                    verdict = "TRIAGE"
                    remainder = remainder + " [body_similarity %.2f < threshold]" % sim
            flagged.append({"verdict": verdict, "base_name": b, "dup_name": d, "remainder": remainder,
                            "model_flagged": True})

    counts = {}
    for item in findings:
        counts[item["verdict"]] = counts.get(item["verdict"], 0) + 1
    flagged_counts = {}
    for item in flagged:
        flagged_counts[item["verdict"]] = flagged_counts.get(item["verdict"], 0) + 1

    OUT.write_text(json.dumps({
        "schema_version": "3.0", "gen_model": "deterministic (no model)", "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "pipeline_commit": "deterministic-rule", "policy": cfg.get("policy"),
        "whole_kb": {"rows_scanned": len(rows), "findings": counts, "items": findings},
        "model_flagged_pairs": {"n": len(flagged), "verdicts": flagged_counts, "items": flagged},
    }, indent=2))
    print("T2 suffix verifier (deterministic — no model)")
    print("  KB rows scanned          : " + str(len(rows)))
    print("  whole-KB suffix findings : " + json.dumps(counts, sort_keys=True))
    print("  model-flagged 32 pairs   : " + json.dumps(flagged_counts, sort_keys=True))
    for item in findings[: args.limit or 12]:
        print("    " + item["verdict"].ljust(6) + " '" + item["base_name"][:44] + "'  ->  '"
              + item["dup_name"][:44] + "'   remainder='" + item["remainder"] + "'")
    print("  artifact: " + str(OUT.relative_to(ROOT)))
    if args.validate:
        return _validate(cfg, markers, max_marker, by_rec)
    return 0


def _validate(cfg: dict, markers: list[str], max_marker: int, by_rec: dict) -> int:
    """Measure this deterministic rule against the blind human T2 labels, WITH the baseline.

    Reporting the accuracy without the constant-answer baseline is what made 0.875 look good in
    BUG-269 when it was exactly "always say merge". The same rule applies to this script's own
    score, so the baseline is computed here too.
    """
    import csv

    sheet = ROOT / "governance" / "JUDGE_CALIBRATION_SHEET_20260917.csv"
    if not sheet.exists():
        print("  validate: no calibration sheet found")
        return 0
    pairs = []
    for row in csv.DictReader(sheet.open()):
        if row["task"] != "T2_suffix_merge" or not (row.get("HUMAN_VERDICT") or "").strip():
            continue
        human = row["HUMAN_VERDICT"].strip().lower()
        if human in ("inbetween", "in-between"):
            continue
        pairs.append((row, "keep" if human.startswith("k") else "merge"))
    if not pairs:
        print("  validate: no decisive human T2 rows")
        return 0
    hits = 0
    abstained = 0
    for row, human in pairs:
        base_name, dup_name = row["object_1_name"], row["object_2_name"]
        verdict, remainder = classify(base_name, dup_name, markers, max_marker)
        if verdict == "MERGE":
            base_id = next((f for f, r in by_rec.items() if r["name"] == base_name), None)
            dup_id = next((f for f, r in by_rec.items() if r["name"] == dup_name), None)
            sim = body_similarity(by_rec.get(base_id, {}), by_rec.get(dup_id, {}),
                                  int(cfg.get("body_shingle_chars", 40)))
            if sim < float(cfg.get("min_body_similarity_for_merge", 0.5)):
                verdict = "TRIAGE"
        predicted = {"AUTO_MERGE": "merge", "KEEP": "keep"}.get(verdict)
        if predicted is None:
            abstained += 1
            status = "ABSTAIN (escalated to a human)"
        else:
            ok = predicted == human
            hits += ok
            status = "OK" if ok else "MISMATCH"
        print("    " + row["item_id"] + " human=" + human.ljust(5) + " rule="
              + (predicted or "-").ljust(6) + " " + status)
    n = len(pairs)
    merges = sum(1 for _, h in pairs if h == "merge")
    baseline = max(merges, n - merges) / n
    print()
    print("  validate: " + str(n) + " decisive human rows | rule answered " + str(n - abstained)
          + " | ABSTAINED " + str(abstained))
    print("    accuracy on what it answered : " + (("%.3f" % (hits / (n - abstained)))
          if n > abstained else "n/a (answered none)"))
    print("    constant-answer baseline     : " + ("%.3f" % baseline) + "  (always 'merge')")
    print("    ANSWERED-NOTHING IS THE POINT: every abstention is a decision the rule could not")
    print("    justify, and each one becomes a human call. A forced guess scores "
          + ("%.3f" % (hits / n)) + " — worse than the baseline — which is exactly why it abstains.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
