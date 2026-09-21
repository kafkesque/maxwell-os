#!/usr/bin/env python3
"""Multi-axis INVERTED-KEY ruler re-scorer (D-275a).

Reference  = the blind HUMAN label (ground truth).
Under test = the STORED free-generated label (the corrupt artefact this exercise
             exists to replace).

Reports stored-label ERROR RATE (1 - agreement), never "accuracy". Abstentions
(blank + out-of-vocabulary relevance judgements) are kept as abstentions, never
imputed. This is the honest replacement for the corrupt ruler_measurement
"0.740 / 0.506 / 0.831" figures (those treated the stored label as the answer key).

Axes:
  form  — extraction_type  (4 canonicals)         [FINAL — reviewer locked FORM]
  ct    — content_type     (7 = 5 roles + 2 dispositions)
  disc  — discipline       (61 canonicals from taxonomy_v5.yaml)

Usage:
  python3 scripts/rescore_ruler_inverted.py [--axis form|ct|disc|all] [--out-dir ...]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SHEET = REPO / "governance" / "RULER_BLIND_SHEET_20260917.csv"
KEY = REPO / "governance" / "ruler_sheet_key_20260917.json"
TAX = REPO / "config" / "taxonomy_v5.yaml"
OUT_JSON = REPO / "governance" / "ruler_inverted_20260920.json"
OUT_MD = REPO / "governance" / "ruler_inverted_20260920.md"

FORM_VALUES = ("causal_mechanism", "descriptive_model", "normative_heuristic", "empirical_pattern")
CT_VALUES = ("principle", "process_template", "process_instance", "tool_instruction",
             "growth_edge", "noise_drop", "quarantine")


def _norm(v: str) -> str:
    """Normalise a label to lowercase alphanumerics for comparison."""
    return re.sub(r"[^a-z0-9]", "", str(v or "").lower())


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson 95% score interval for a proportion."""
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    b = z * (p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5 / d
    return (max(0.0, c - b), min(1.0, c + b))


def load_taxonomy() -> tuple[dict[str, str], dict[str, str]]:
    """Return (norm_canonical -> canonical, canonical -> group) for disciplines."""
    tax = yaml.safe_load(TAX.read_text(encoding="utf-8"))
    disc = tax["disciplines"]
    norm2canon = {_norm(d["canonical"]): d["canonical"] for d in disc}
    group = {}
    for g, members in tax["discipline_groups"].items():
        for m in members:
            group[m] = g
    return norm2canon, group


# ─────────────────────────────────────────────────────────────────────────────
# Resolvers — human side (ground truth) and stored side (under test)
# ─────────────────────────────────────────────────────────────────────────────

def resolve_form(raw: str) -> tuple[str | None, str]:
    s = _norm(raw)
    if not s:
        return None, "blank"
    if "irrelevant" in s:
        return None, "abstain-irrelevant"
    if s.startswith(("casual", "causal")):
        return "causal_mechanism", "typo" if s.startswith("casual") else "exact"
    if s.startswith(("descriptive", "escriptive")):
        return "descriptive_model", "typo" if s.startswith("escriptive") else "exact"
    if s.startswith(("normative", "normativ")):
        return "normative_heuristic", "typo" if s.startswith("normativ") else "exact"
    if s.startswith("empirical"):
        return "empirical_pattern", "exact"
    return None, "unresolved"


def resolve_ct(raw: str) -> tuple[str | None, str]:
    s = _norm(raw)
    if not s:
        return None, "blank"
    if "irrelevant" in s:
        return None, "abstain-irrelevant"
    for c in CT_VALUES:
        if s == _norm(c):
            return c, "exact"
    return None, "unresolved"


def resolve_disc_human(raw: str, norm2canon: dict[str, str]) -> tuple[str | None, str]:
    s = _norm(raw)
    if not s:
        return None, "blank"
    if s == "emerging":
        return None, "abstain-emerging"
    if "irrelevant" in s:
        return None, "abstain-irrelevant"
    c = norm2canon.get(s)
    if c:
        return c, "exact"
    return None, "unresolved"


def resolve_disc_stored(raw: str, norm2canon: dict[str, str]) -> tuple[str | None, str]:
    """Stored discipline: `emerging` is the alias-map dump bucket = a stored FAILURE,
    not an abstention. Non-canonical stored strings are raw leaks (alias map failed)."""
    s = _norm(raw)
    if not s:
        return None, "blank"
    if s == "emerging":
        return "emerging_dump", "dump"
    c = norm2canon.get(s)
    if c:
        return c, "exact"
    return None, "unmapped"


# ─────────────────────────────────────────────────────────────────────────────
# Scoring
# ─────────────────────────────────────────────────────────────────────────────

def score_axis(rows: list[dict], key: dict[str, dict], axis: str,
               norm2canon: dict[str, str], group: dict[str, str]) -> dict:
    """Score one axis. Returns a full results dict for that axis."""
    out = {
        "axis": axis,
        "reference": "human blind label",
        "under_test": "stored free-generated label",
        "rows": [],
        "kinds": Counter(),
        "unresolved": [],
        "abstained": Counter(),
        "scored_n": 0,
        "error_rates": {},       # stratum -> {"n","agrees","error","lo","hi"}
        "per_class": {},         # human class -> {"n","agrees","error"}
        "confusion": [],         # list of {human,stored,n}
        "group_near_miss": None, # disc only
    }

    for r in rows:
        item = r["item_id"]
        stored = key[item]["stored"]
        stratum = key[item]["stratum"]

        if axis == "form":
            human, hkind = resolve_form(r["FORM (1-4)"])
            stored_raw = stored.get("extraction_type")
            stored_c, skind = resolve_form(stored_raw)
        elif axis == "ct":
            human, hkind = resolve_ct(r["CT (1-7)"])
            stored_raw = stored.get("content_type")
            stored_c, skind = resolve_ct(stored_raw)
        else:  # disc
            human, hkind = resolve_disc_human(r["DISC (1-62)"], norm2canon)
            stored_raw = stored.get("discipline")
            stored_c, skind = resolve_disc_stored(stored_raw, norm2canon)

        out["kinds"][hkind] += 1
        if hkind == "unresolved":
            out["unresolved"].append(f"{item}={r[('FORM (1-4)' if axis=='form' else 'DISC (1-62)' if axis=='disc' else 'CT (1-7)')]!r}")
        if hkind.startswith(("abstain", "blank")):
            out["abstained"][hkind] += 1

        scored = human is not None
        agree = scored and stored_c == human
        row = {
            "item_id": item,
            "stratum": stratum,
            "human": human,
            "human_raw": r["FORM (1-4)" if axis == "form" else "DISC (1-62)" if axis == "disc" else "CT (1-7)"],
            "stored": stored_c,
            "stored_raw": stored_raw,
            "stored_kind": skind,
            "agree": agree,
            "scored": scored,
        }
        if axis == "disc" and scored and stored_c and stored_c != "emerging_dump":
            row["same_group"] = group.get(human) == group.get(stored_c)
        out["rows"].append(row)

    # error rates per stratum + overall
    for stratum_label in ("A", "B", "__all__"):
        sub = [x for x in out["rows"] if x["scored"] and (stratum_label == "__all__" or x["stratum"] == stratum_label)]
        n = len(sub)
        agrees = sum(1 for x in sub if x["agree"])
        if n == 0:
            continue
        lo, hi = wilson(agrees, n)
        name = "all" if stratum_label == "__all__" else stratum_label
        out["error_rates"][name] = {
            "n": n, "agrees": agrees,
            "error": round(1 - agrees / n, 4),
            "error_lo": round(1 - hi, 4), "error_hi": round(1 - lo, 4),
        }

    scored = [x for x in out["rows"] if x["scored"]]
    out["scored_n"] = len(scored)

    # per-class stored reliability (all strata, since class n is small)
    pc = defaultdict(lambda: {"n": 0, "agrees": 0})
    for x in scored:
        pc[x["human"]]["n"] += 1
        pc[x["human"]]["agrees"] += int(x["agree"])
    out["per_class"] = {
        lab: {"n": v["n"], "agrees": v["agrees"],
              "error": round(1 - v["agrees"] / v["n"], 4)}
        for lab, v in sorted(pc.items(), key=lambda kv: -kv[1]["n"])
    }

    # confusion
    conf = Counter((x["human"], x["stored"]) for x in scored)
    out["confusion"] = [{"human": h, "stored": s, "n": c} for (h, s), c in sorted(conf.items(), key=lambda kv: -kv[1])]

    # group near-miss (disc only)
    if axis == "disc":
        grp = [x for x in scored if x.get("same_group") is not None]
        if grp:
            exact = sum(1 for x in grp if x["agree"])
            group_agree = sum(1 for x in grp if x["same_group"])
            out["group_near_miss"] = {
                "n": len(grp), "exact_agree": exact,
                "group_agree": group_agree,
                "exact_error": round(1 - exact / len(grp), 4),
                "group_error": round(1 - group_agree / len(grp), 4),
            }
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Rendering
# ─────────────────────────────────────────────────────────────────────────────

def _err_row(name: str, e: dict) -> str:
    return (f"| {name} | **{e['error']:.3f}** | [{e['error_lo']:.3f}, {e['error_hi']:.3f}] "
            f"| {e['agrees']}/{e['n']} |")


def render_md(results: dict, norm2canon: dict[str, str], group: dict[str, str]) -> str:
    L: list[str] = [
        "# RULER — INVERTED KEY, all axes — 2026-09-20",
        "",
        "Reference = blind **human** label (ground truth). Under test = **stored** "
        "free-generated label. Reported = stored-label ERROR RATE (1 − agreement).",
        "This is the honest replacement for the corrupt ruler_measurement "
        "`0.740 / 0.506 / 0.831` figures. (D-275a, BUG-303)",
        "",
    ]

    axis_meta = {
        "form": ("extraction_type (FORM)", list(FORM_VALUES)),
        "ct": ("content_type (CT)", list(CT_VALUES)),
        "disc": ("discipline (DISC)", sorted(norm2canon.values())),
    }

    for axis in ("ct", "disc", "form"):
        res = results[axis]
        title, canonicals = axis_meta[axis]
        L += [f"## {title}", "",
              "### Stored-label error rate",
              "",
              "| scope | error rate | 95% Wilson | stored agrees |",
              "|---|---|---|---|"]
        for name in ("all", "A", "B"):
            if name in res["error_rates"]:
                L.append(_err_row(f"stratum {name}", res["error_rates"][name]))
        L += ["",
              f"- scored: {res['scored_n']} | abstained: {dict(res['abstained'])} | "
              f"typos/dups resolved on human side: {dict(res['kinds'])}",
              ""]

        # per-class
        L += ["### Per-class stored reliability (human class = truth)", "",
              "| human class | n | stored agrees | stored error rate |",
              "|---|---|---|---|"]
        for lab, v in res["per_class"].items():
            L.append(f"| {lab} | {v['n']} | {v['agrees']} | {v['error']:.3f} |")
        L.append("")

        # confusion
        if axis in ("ct", "form"):
            L += ["### Confusion matrix (human rows x stored cols)", "",
                  "| human \\ stored | " + " | ".join(canonicals) + " |",
                  "|---|---" + "|---" * len(canonicals) + " |"]
            conf = {(c["human"], c["stored"]): c["n"] for c in res["confusion"]}
            for h in canonicals:
                cells = [str(conf.get((h, s), 0)) for s in canonicals]
                L.append(f"| {h} | " + " | ".join(cells) + " |")
            L.append("")
        else:  # disc: too big for a matrix, list non-zero disagreements
            off = [c for c in res["confusion"] if c["human"] != c["stored"]]
            if off:
                L += ["### Discipline disagreements (human → stored), non-zero", "",
                      "| human (truth) | stored (under test) | n |",
                      "|---|---|---|"]
                for c in off:
                    L.append(f"| {c['human']} | {c['stored']} | {c['n']} |")
                L.append("")
            if res.get("group_near_miss"):
                g = res["group_near_miss"]
                L += ["### Discipline group-level near-miss (softer agreement)", "",
                      f"- exact-canonical error: **{g['exact_error']:.3f}** ({g['exact_agree']}/{g['n']})",
                      f"- same-group error: **{g['group_error']:.3f}** ({g['group_agree']}/{g['n']})",
                      f"- → {g['n'] - g['group_agree']} stored labels land in a DIFFERENT discipline group than the human.",
                      ""]

        if res["unresolved"]:
            L += ["### Unresolved cells (need cleanup)", ""]
            L += [f"- {u}" for u in res["unresolved"]]
            L.append("")

    L += ["## Notes", "",
          "- `emerging` on the DISC human side is an ABSTENTION (reviewer could not map to the 61-menu).",
          "- `emerging` on the DISC stored side is a DUMP = a stored-label FAILURE (alias map failed to land a slot).",
          "- `irrelevant` is read as an abstention (a relevance judgement, not a FORM/discipline value) — evidence for the missing R4 relevance axis.",
          "- Stratum A is the pre-agreed clean subset; stratum B is included here in the `all` row. "
          "D1/D2: stratum B is non-proportional and the sampling frame mixes PASS/QUARANTINE — treat `all` as the honest bound, `A` as the comparable-to-prior subset.",
          ""]
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--axis", choices=("form", "ct", "disc", "all"), default="all")
    args = ap.parse_args()

    with SHEET.open(encoding="utf-8") as fh:
        sheet = [r for r in csv.DictReader(fh) if (r.get("item_id") or "").strip()]
    key = {r["item_id"]: r for r in json.loads(KEY.read_text(encoding="utf-8"))}
    norm2canon, group = load_taxonomy()

    axes = [args.axis] if args.axis != "all" else ["ct", "disc", "form"]
    results = {}
    for axis in axes:
        results[axis] = score_axis(sheet, key, axis, norm2canon, group)

    payload = {
        "schema_version": "1.0",
        "generated_at": "2026-09-20",
        "key_inverted": True,
        "reference": "human blind label",
        "under_test": "stored free-generated label",
        "taxonomy": "config/taxonomy_v5.yaml",
        "sheet": "governance/RULER_BLIND_SHEET_20260917.csv",
        "key": "governance/ruler_sheet_key_20260917.json",
        "total_rows": len(sheet),
        "results": results,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    OUT_MD.write_text(render_md(results, norm2canon, group), encoding="utf-8")
    print(render_md(results, norm2canon, group))
    print("wrote", OUT_JSON.name, "and", OUT_MD.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
