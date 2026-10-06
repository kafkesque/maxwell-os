#!/usr/bin/env python3
"""Deterministic FORM-axis (extraction_type) audit for an S2 checkpoint (D-2749).

Answers the question "does content_type rely on FORM, and is FORM accurate?" with
pure rules (D-343: no LLM). Read-only. Produces a JSON triage artifact.

Signals are lexicons matched against the definition text; the "agreement" is a LOWER
BOUND (a definition may legitimately carry several epistemic forms), so this audit is
a drift detector, not a re-classifier.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

SIGNALS: dict[str, str] = {
    "causal_mechanism": (
        r"\b(causes?|leads? to|increases?|decreases?|triggers?|drives?|results? in|yields?|"
        r"produces?|because|thereby|enabl(es?|ing)|allows?|induces?|reduces?|amplifies?)\b"
    ),
    "descriptive_model": (
        r"(^|\s)(is|are|refers? to|consists? of|compris(es?|ing)|characteri[sz]ed? by|describes?|"
        r"classified? (as|into)|a type of|a form of|a kind of|typolog|taxonom|categories?|"
        r"distinguishe[ds]?|functions? as|serves? as)"
    ),
    "normative_heuristic": (
        r"\b(should|must|ought|need to|requires?|best practice|rule of thumb|guidelines?|"
        r"principles?|heuristics?|in order to|to (achieve|avoid|ensure|maximi[sz]e|minimi[sz]e|"
        r"improve|build|create|maintain))\b"
    ),
    "empirical_pattern": (
        r"\b(tend(s|ed)?|correlat(es?|ed|ion)|associat(es?|ed|ion)|typically|often|observed|"
        r"pattern(s)?|consistent(ly)?|on average|varies? with|more likely|less likely|"
        r"frequency|distribution)\b"
    ),
}


def signals(defn: str) -> set[str]:
    d = defn.lower()
    return {form for form, pat in SIGNALS.items() if re.search(pat, d)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("checkpoint", type=Path)
    ap.add_argument("--out", type=Path, default=Path("temp/form_axis_audit.json"))
    args = ap.parse_args()

    rows = [json.loads(l) for l in args.checkpoint.read_text(encoding="utf-8").splitlines() if l.strip()]

    total = Counter()
    agree = Counter()
    no_signal = Counter()
    mismatch: dict[str, Counter] = defaultdict(Counter)
    cross_tab: dict[str, Counter] = defaultdict(Counter)
    defaulted = 0
    for r in rows:
        lbl = r.get("extraction_type")
        ct = r.get("content_type") or "(missing)"
        if lbl in SIGNALS:
            cross_tab[ct][lbl] += 1
        if r.get("_extraction_type_defaulted"):
            defaulted += 1
        if lbl not in SIGNALS:
            continue
        s = signals(r.get("definition") or "")
        total[lbl] += 1
        if not s:
            no_signal[lbl] += 1
        elif lbl in s:
            agree[lbl] += 1
        else:
            for x in s:
                mismatch[lbl][x] += 1

    out = {
        "generated": "scripts/audit_form_axis.py",
        "source": str(args.checkpoint),
        "n_rows": len(rows),
        "defaulted_extraction_type": defaulted,
        "agreement": {k: {"n": total[k], "agree": agree[k], "pct": round(100 * agree[k] / total[k], 1),
                          "no_signal": no_signal[k]}
                      for k in sorted(total)},
        "top_mismatch": {k: mismatch[k].most_common(4) for k in mismatch},
        "cross_tab": {k: dict(v) for k, v in sorted(cross_tab.items())},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
