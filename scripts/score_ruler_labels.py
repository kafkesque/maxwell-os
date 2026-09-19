#!/usr/bin/env python3
"""Score the filled G4 ruler sheet: the ruler itself, plus the measured accuracy of the stored labels.

WHY: the sheet turns an unmeasurable system into a measured one. A human answers 150 rows blind; this
script then reports, per axis:
  (1) the CERTIFIED label set (human-blind tier) -- the new reference,
  (2) how accurate the STORED labels actually are against that reference, on the proportional stratum
      only, ALWAYS against the constant-answer baseline (BUG-269: an accuracy with no baseline is noise),
  (3) a Wilson 95% interval, so the number is quoted as an interval, never a point (BUG-267 discipline),
  (4) per-class precision on the forced-minority stratum (never a raw accuracy -- that stratum is not
      proportional by design), including the F-14 untraceable pocket as its own slice.

Refuses to run on an incomplete sheet (an incomplete ruler is worse than none: it invites a guessed number).

Usage:
  python3 scripts/score_ruler_labels.py
"""
from __future__ import annotations

import collections
import csv
import difflib
import importlib.util
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

OUT_JSON = REPO / "governance" / "ruler_measurement_20260917.json"
OUT_MD = REPO / "governance" / "ruler_measurement_20260917.md"
AXES = ("content_type", "discipline", "extraction_type")
COLUMN = {"content_type": "CT (1-7)", "discipline": "DISC (1-62)", "extraction_type": "FORM (1-4)"}


def _module() -> Any:
    """Load the sheet builder as a module so the menus have exactly ONE definition.

    Returns:
        The imported build_ruler_sheet module.
    """
    spec = importlib.util.spec_from_file_location("brs", REPO / "scripts" / "build_ruler_sheet.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def norm(v: Any) -> str:
    """Normalise a label for comparison.

    Args:
        v: raw label.

    Returns:
        Lowercased alphanumeric-only string.
    """
    return re.sub(r"[^a-z0-9]", "", str(v or "").lower())


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a proportion.

    Args:
        k: successes.
        n: trials.
        z: normal quantile (1.96 = 95%).

    Returns:
        (low, high) bounds; (0.0, 1.0) when n == 0.
    """
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def resolve_answer(raw: Any, menu: list[str]) -> tuple[str | None, str]:
    """Resolve a written answer cell to its canonical menu entry.

    Accepts the 1-based index OR the label written out in any casing/spacing/punctuation,
    because the first reviewer filled the sheet by NAME ("causal mechanism", "descriptive_model")
    rather than by index -- a scorer that read only integers would have crashed on 150 valid
    answers (observed 2026-09-19). Near-misses are accepted at a 0.85 ratio and REPORTED
    individually so a typo can never pass silently (C16).

    Args:
        raw: the cell value as written by the reviewer.
        menu: the ordered menu for that axis.

    Returns:
        (canonical label, how it resolved) where how is one of
        index | exact | fuzzy | blank | UNRESOLVED, and label is None when unresolved.
    """
    s = str(raw or "").strip()
    if not s:
        return (None, "blank")
    if s.isdigit():
        i = int(s)
        return (menu[i - 1], "index") if 1 <= i <= len(menu) else (None, "UNRESOLVED")
    target = norm(s)
    for m in menu:
        if norm(m) == target:
            return (m, "exact")
    hits = difflib.get_close_matches(target, [norm(m) for m in menu], n=1, cutoff=0.85)
    if hits:
        for m in menu:
            if norm(m) == hits[0]:
                return (m, "fuzzy")
    return (None, "UNRESOLVED")


def spread(raw: Any) -> list[str]:
    """Parse the stored domains value into a list.

    Args:
        raw: the column value.

    Returns:
        List of labels.
    """
    import json as _j
    if not raw:
        return []
    try:
        v = _j.loads(raw)
        return [str(x) for x in v] if isinstance(v, list) else [str(v)]
    except (ValueError, TypeError):
        return [str(raw)]


def main() -> int:
    """Score the sheet and write the measurement artifacts."""
    brs = _module()
    cfg = brs.load_cfg()
    menus = brs.vocab()
    if not brs.SHEET.exists():
        print("FAIL-CLOSED: no sheet at %s" % brs.SHEET)
        return 1
    with brs.SHEET.open(encoding="utf-8") as fh:
        sheet = list(csv.DictReader(fh))
    key = {r["item_id"]: r for r in json.loads(brs.KEY.read_text(encoding="utf-8"))}
    answered = [r for r in sheet if any(str(r.get(c) or "").strip() for c in COLUMN.values())]
    if len(answered) < len(sheet):
        print("REFUSING TO SCORE: %d of %d rows answered. An incomplete ruler invites a guessed number."
              % (len(answered), len(sheet)))
        return 1

    floors = cfg.get("min_human_share") or {}
    report: dict[str, Any] = {"rows": len(sheet), "axes": {}, "answer_resolution": {}}
    for axis in AXES:
        col = COLUMN[axis]
        menu = menus[axis]
        rows = []
        how = collections.Counter()
        unresolved: list[str] = []
        for r in answered:
            item = r["item_id"]
            human, resolved_by = resolve_answer(r[col], menu)
            how[resolved_by] += 1
            if resolved_by == "UNRESOLVED":
                unresolved.append("%s=%r" % (item, r[col]))
            if human is None:
                continue
            stored_raw = (key[item]["stored"] or {}).get(axis)
            stored = norm(stored_raw)
            human_n = norm(human)
            # 'emerging' is not a label, it is the ABSENCE of a taxonomy home (D2485 emerging_real).
            # Counting it as agreement would flatter both sides, so it is excluded here and reported
            # separately as `emerging_vacuous`.
            rows.append({"item_id": item, "stratum": key[item]["stratum"], "human": human,
                         "stored": stored_raw, "untraceable": key[item]["untraceable_pocket"],
                         "agree": bool(stored) and stored == human_n and human_n not in ("", "emerging"),
                         "emerging_vacuous": bool(stored) and stored == human_n and human_n == "emerging",
                         "conf": str(r.get("conf_" + axis[:4]) or "")})
        report["answer_resolution"][axis] = {
            "by": dict(how), "blank": how["blank"], "unresolved": unresolved,
            "scored_n": len(rows)}
        A = [x for x in rows if x["stratum"] == "A"]
        B = [x for x in rows if x["stratum"] == "B"]
        votes = collections.Counter(x["human"] for x in A)
        base_label, base_n = (votes.most_common(1)[0] if votes else ("n/a", 0))
        base = base_n / len(A) if A else 0.0
        k = sum(1 for x in A if x["agree"])
        acc = k / len(A) if A else 0.0
        lo, hi = wilson(k, len(A))
        per_class = {}
        for lab, grp in sorted(collections.Counter(x["human"] for x in B).items()):
            sub = [x for x in B if x["human"] == lab]
            per_class[lab] = {"n": len(sub), "stored_agrees": sum(1 for x in sub if x["agree"])}
        # F-14 test: the untraceable pocket is ~50.7% of the KB, so it is not a rare slice -- compare it
        # WITHIN the proportional stratum A, where both sides are drawn from the same sampling frame.
        unt = [x for x in A if x["untraceable"]]
        tra = [x for x in A if not x["untraceable"]]
        min_rows = int((cfg.get("stop_rule") or {}).get("min_rows_before_verdict", 60))
        margin = float((cfg.get("stop_rule") or {}).get("decisive_margin_over_floor", 0.10))
        floor = float(floors.get(axis, 0.0))
        verdict = ("UNDECIDED: %d stratum-A rows answered, %d required before a floor verdict"
                   % (len(A), min_rows)) if len(A) < min_rows else (
                   "STOPPED: decisive" if abs(acc - floor) >= margin else "CONTINUE: inside the margin")
        report["axes"][axis] = {
            "floor": floor, "stratum_a_n": len(A), "stratum_b_n": len(B),
            "stratum_a_unanswered": sum(1 for x in answered if key[x["item_id"]]["stratum"] == "A"
                                        and resolve_answer(x[col], menu)[0] is None),
            "answer_resolution": dict(how),
            "human_distribution_A": dict(votes.most_common()),
            "emerging_vacuous_A": sum(1 for x in A if x["emerging_vacuous"]),
            "stored_label_accuracy_A": round(acc, 3), "wilson95": [round(lo, 3), round(hi, 3)],
            "constant_answer_baseline": round(base, 3), "baseline_label": base_label,
            "lift_over_baseline": round(acc - base, 3),
            "verdict": verdict,
            "per_class_precision_B": per_class,
            "untraceable_slice_A": {"n": len(unt), "stored_agrees": sum(1 for x in unt if x["agree"])},
            "traceable_slice_A": {"n": len(tra), "stored_agrees": sum(1 for x in tra if x["agree"])},
        }

    md = ["# RULER MEASUREMENT (2026-09-17)", "",
          "The certified core: %d blind-human-answered rows (%d proportional + %d forced-minority)."
          % (len(sheet), report["axes"]["content_type"]["stratum_a_n"],
             report["axes"]["content_type"]["stratum_b_n"]),
          "",
          "Reviewer: %s | sheet: %s" % (
              collections.Counter(str(r.get("reviewer") or "") for r in sheet).most_common(1)[0][0],
              brs.SHEET.name),
          "",
          "## How the written answers were read (C16: every non-exact resolution is listed)",
          "",
          "The reviewer answered by NAME, not by index, and left some cells blank. Blank is a datum:",
          "it means the reviewer, holding the full menu, could not assign any label at all.",
          "",
          "| axis | exact | index | fuzzy (typo) | blank | unresolved | scored n |",
          "|---|---|---|---|---|---|---|"]
    for axis in AXES:
        r = report["answer_resolution"][axis]
        by = r["by"]
        md.append("| %s | %d | %d | %d | %d | %d | %d |"
                  % (axis, by.get("exact", 0), by.get("index", 0), by.get("fuzzy", 0),
                     by.get("blank", 0), len(r["unresolved"]), r["scored_n"]))
    fuzzy_lines = []
    for axis in AXES:
        for r in answered:
            h, howto = resolve_answer(r[COLUMN[axis]], menus[axis])
            if howto == "fuzzy":
                fuzzy_lines.append("- %s %s: %r -> %r" % (axis, r["item_id"], r[COLUMN[axis]], h))
    if fuzzy_lines:
        md += ["", "Fuzzy (typo) resolutions, itemised so none is silent:", ""] + [
            "- " + x.lstrip("- ") for x in fuzzy_lines]
    for axis in AXES:
        u = report["answer_resolution"][axis]["unresolved"]
        if u:
            md += ["", "UNRESOLVED on %s (answered but not a menu value): %s" % (axis, ", ".join(u))]
    md += [
          "",
          "The FLOOR columns are the accuracy of the STORED labels against the blind human answer on the",
          "PROPORTIONAL stratum only, always beside the constant-answer baseline (BUG-269). An accuracy",
          "without its baseline is not evidence. Rows the reviewer could not label are EXCLUDED from the",
          "numerator and the denominator BOTH, and counted in `stratum A unanswered` below -- excluding",
          "them from only one side is how a floor gets flattered.",
          "",
          "| axis | stratum A n | unanswered | stored-label accuracy | 95% Wilson | baseline | lift | floor | verdict |",
          "|---|---|---|---|---|---|---|---|---|"]
    for axis, d in report["axes"].items():
        md.append("| %s | %d | %d | %.3f | [%.3f, %.3f] | %.3f (%s) | %+0.3f | %.2f | %s |"
                  % (axis, d["stratum_a_n"], d["stratum_a_unanswered"], d["stored_label_accuracy_A"],
                     d["wilson95"][0], d["wilson95"][1], d["constant_answer_baseline"],
                     d["baseline_label"], d["lift_over_baseline"], d["floor"], d["verdict"]))
    md += ["", "`emerging` agreements are excluded and counted separately (it is the absence of a",
           "taxonomy home, not a label): %s" % ", ".join(
               "%s=%d" % (a, d["emerging_vacuous_A"]) for a, d in report["axes"].items())]
    md += ["", "## Per-class precision (stratum B, forced-minority -- never a raw accuracy)", ""]
    for axis, d in report["axes"].items():
        md.append("**%s**" % axis)
        for lab, s in d["per_class_precision_B"].items():
            md.append("- %s: %d/%d" % (lab, s["stored_agrees"], s["n"]))
        un, tr = d["untraceable_slice_A"], d["traceable_slice_A"]
        md.append("- F-14 test, stratum A: untraceable %d/%d vs traceable %d/%d (the stored labels are"
                  " %s on the pre-repair pocket)"
                  % (un["stored_agrees"], un["n"], tr["stored_agrees"], tr["n"],
                     "not better" if un["n"] and tr["n"] and un["stored_agrees"] / un["n"]
                     < tr["stored_agrees"] / tr["n"] else "no worse"))
        md.append("")
    OUT_JSON.write_text(json.dumps(report, indent=1), encoding="utf-8")
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md[:14]))
    print("\nwrote %s and %s" % (OUT_JSON.name, OUT_MD.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())

