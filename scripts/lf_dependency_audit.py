#!/usr/bin/env python3
"""scripts/lf_dependency_audit.py — D2585 P1 (Step 3A) labeling-function dependency audit.

Mandatory gate BEFORE scripts/build_label_model.py. The roundtable adjudication
(D2585) established that the labeling functions (LFs) available to the label model
are NOT automatically independent:

  - T-NLI contradiction (definition<->label entailment, contra_dominant)
  - cleanlab Confident Learning (TF-IDF + CV-LR self-confidence)

Both are machine-generated from the SAME gpt-oss teacher labels, so they can share
correlated failure modes. Feeding correlated LFs into an independence-assuming
estimator (plain Dawid-Skene) overcounts agreement and yields "precisely
calibrated-looking probabilities that are statistically unjustified" (ChatGPT,
second-round peer review). This script measures the actual dependence so the
estimator choice (Snorkel dependency modeling vs Dawid-Skene) is evidence-based.

Read-only w.r.t. the DB. Writes governance/lf_dependency_audit.{json,md}.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from pipeline.pipeline_paths import DB_PATH  # noqa: E402

_NLI_JSON = _ROOT / "governance" / "nli_label_audit.json"
_CLEANLAB_JSON = _ROOT / "governance" / "cleanlab_label_audit.json"
_OUT_JSON = _ROOT / "governance" / "lf_dependency_audit.json"
_OUT_MD = _ROOT / "governance" / "lf_dependency_audit.md"

# C20: interpretation thresholds for the 2x2 dependence metrics.
_PHI_HIGH = 0.5      # above this, treat the LFs as strongly correlated
_PHI_LOW = 0.2       # below this, treat the LFs as near-independent


def _load_nli_discipline(path: Path) -> dict[str, dict]:
    """Return fb_id -> discipline-axis NLI record (contra_dominant/weak/entail/label)."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    collisions = 0
    for r in doc.get("results", []):
        if r.get("axis") != "discipline":
            continue
        fb_id = r["fb_id"]
        if fb_id in out:
            collisions += 1
        out[fb_id] = r
    return out


def _load_cleanlab(path: Path) -> tuple[set[str], dict]:
    """Return (flagged_fb_ids set, summary dict) for the cleanlab audit."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    return set(doc.get("flagged_fb_ids", [])), doc.get("summary", {})


def _load_cleanlab_assessed(db_path: Path) -> set[str]:
    """Re-derive the full cleanlab-assessed FB population from the DB.

    Mirrors scripts/cleanlab_label_audit.py `_load_fbs` exactly, so the
    non-flagged complement is reconstructed without re-running cleanlab.
    """
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT fb_id, definition, discipline FROM fbs "
            "WHERE definition IS NOT NULL AND definition != '' "
            "AND discipline IS NOT NULL AND discipline != '' AND discipline != 'emerging'"
        ).fetchall()
    finally:
        conn.close()
    return {r[0] for r in rows}


def _contingency(nli_flags: dict[str, int], cleanlab_flags: set[str], assessed: set[str]) -> dict:
    """Build a 2x2 contingency table for the two binary LFs.

    Args:
        nli_flags: fb_id -> 0/1 (T-NLI flag).
        cleanlab_flags: fb_id set (cleanlab flag == 1).
        assessed: fb_id set (cleanlab-assessed population; cleanlab flag == 0 if not flagged).

    Returns:
        Dict with a/b/c/d cells + marginal/conditional rates.
    """
    a = b = c = d = 0
    for fb_id in assessed:
        if fb_id not in nli_flags:
            continue  # only FBs with BOTH signals count for the joint
        nli = nli_flags[fb_id]
        cl = 1 if fb_id in cleanlab_flags else 0
        if cl == 1 and nli == 1:
            a += 1
        elif cl == 1 and nli == 0:
            b += 1
        elif cl == 0 and nli == 1:
            c += 1
        else:
            d += 1
    n = a + b + c + d
    return {
        "both": a, "cleanlab_only": b, "nli_only": c, "neither": d, "n": n,
        "p_cleanlab_given_nli": round(a / (a + c), 4) if (a + c) else None,
        "p_cleanlab_given_not_nli": round(b / (b + d), 4) if (b + d) else None,
        "p_nli_given_cleanlab": round(a / (a + b), 4) if (a + b) else None,
        "p_nli_given_not_cleanlab": round(c / (c + d), 4) if (c + d) else None,
    }


def _phi_kappa(ct: dict) -> dict:
    """Compute Pearson phi and Cohen's kappa for a 2x2 contingency table."""
    a, b, c, d = ct["both"], ct["cleanlab_only"], ct["nli_only"], ct["neither"]
    n = a + b + c + d
    if n == 0:
        return {"phi": None, "kappa": None, "agreement": None}
    # phi
    denom = ((a + b) * (c + d) * (a + c) * (b + d)) ** 0.5
    phi = (a * d - b * c) / denom if denom else None
    # kappa
    p_o = (a + d) / n
    p_e = ((a + b) / n) * ((a + c) / n) + ((c + d) / n) * ((b + d) / n)
    kappa = (p_o - p_e) / (1 - p_e) if (1 - p_e) else None
    return {
        "phi": round(phi, 4) if phi is not None else None,
        "kappa": round(kappa, 4) if kappa is not None else None,
        "agreement": round(p_o, 4),
    }


def _per_label(nli_discipline: dict[str, dict], cleanlab_flags: set[str], assessed: set[str]) -> list[dict]:
    """Per-discipline flag counts for both LFs (do they target the same labels?)."""
    counts: dict[str, dict] = {}
    for fb_id in assessed:
        rec = nli_discipline.get(fb_id)
        if rec is None:
            continue
        label = rec.get("label", "?")
        c = counts.setdefault(label, {"cleanlab": 0, "nli": 0, "both": 0, "n": 0})
        c["n"] += 1
        cl = fb_id in cleanlab_flags
        nl = bool(rec.get("contra_dominant"))
        if cl:
            c["cleanlab"] += 1
        if nl:
            c["nli"] += 1
        if cl and nl:
            c["both"] += 1
    rows = [
        {"label": lbl, **v}
        for lbl, v in sorted(counts.items(), key=lambda kv: -(kv[1]["both"] + kv[1]["cleanlab"]))
    ]
    return rows


def main() -> int:
    nli_discipline = _load_nli_discipline(_NLI_JSON)
    cleanlab_flags, cleanlab_summary = _load_cleanlab(_CLEANLAB_JSON)
    assessed = _load_cleanlab_assessed(DB_PATH)

    # Two NLI flag variants: contra_dominant (strong) and weak (weak_support).
    nli_contra = {fb: int(bool(r.get("contra_dominant"))) for fb, r in nli_discipline.items()}
    nli_weak = {fb: int(bool(r.get("weak"))) for fb, r in nli_discipline.items()}

    ct_contra = _contingency(nli_contra, cleanlab_flags, assessed)
    ct_weak = _contingency(nli_weak, cleanlab_flags, assessed)

    report = {
        "inputs": {
            "nli_discipline_fbs": len(nli_discipline),
            "cleanlab_assessed_fbs": len(assessed),
            "cleanlab_flagged_fbs": len(cleanlab_flags),
            "cleanlab_pct_flagged": cleanlab_summary.get("pct_flagged"),
        },
        "contra_variant": {**ct_contra, **_phi_kappa(ct_contra)},
        "weak_variant": {**ct_weak, **_phi_kappa(ct_weak)},
        "per_label": _per_label(nli_discipline, cleanlab_flags, assessed),
    }
    _OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    phi = report["contra_variant"]["phi"]
    verdict = "near-independent" if phi is not None and abs(phi) < _PHI_LOW else (
        "strongly-correlated" if phi is not None and abs(phi) >= _PHI_HIGH else "weakly-correlated"
    )

    md = [
        "# LF DEPENDENCY AUDIT — Step 3A (D2585 P1)",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| T-NLI discipline FBs | {report['inputs']['nli_discipline_fbs']} |",
        f"| cleanlab assessed FBs | {report['inputs']['cleanlab_assessed_fbs']} |",
        f"| cleanlab flagged FBs | {report['inputs']['cleanlab_flagged_fbs']} ({report['inputs']['cleanlab_pct_flagged']}) |",
        "",
        "## 2x2 dependence — T-NLI contradiction vs cleanlab",
        "",
        "| Cell | Count |",
        "|---|---|",
        f"| both flag | {ct_contra['both']} |",
        f"| cleanlab only | {ct_contra['cleanlab_only']} |",
        f"| NLI only | {ct_contra['nli_only']} |",
        f"| neither | {ct_contra['neither']} |",
        "",
        "| Stat | Contradiction | Weak |",
        "|---|---|---|",
        f"| phi | {report['contra_variant']['phi']} | {report['weak_variant']['phi']} |",
        f"| kappa | {report['contra_variant']['kappa']} | {report['weak_variant']['kappa']} |",
        f"| agreement | {report['contra_variant']['agreement']} | {report['weak_variant']['agreement']} |",
        f"| P(cleanlab\\|NLI) | {ct_contra['p_cleanlab_given_nli']} | {ct_weak['p_cleanlab_given_nli']} |",
        f"| P(cleanlab\\|~NLI) | {ct_contra['p_cleanlab_given_not_nli']} | {ct_weak['p_cleanlab_given_not_nli']} |",
        "",
        f"**Verdict:** {verdict} (phi = {phi}).",
        "",
        "## Top labels targeted by both LFs",
        "",
        "| Label | n | cleanlab | NLI | both |",
        "|---|---|---|---|---|",
    ]
    for row in report["per_label"][:15]:
        md.append(
            f"| {row['label']} | {row['n']} | {row['cleanlab']} | {row['nli']} | {row['both']} |"
        )
    md.append("")
    _OUT_MD.write_text("\n".join(md), encoding="utf-8")

    print(json.dumps(report["contra_variant"], indent=2))
    print(f"\nverdict: {verdict}")
    print(f"wrote {_OUT_JSON} + {_OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
