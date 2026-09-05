#!/usr/bin/env python3
"""scripts/build_mislabel_triage.py — D2547 calibration + triaged mislabel queue.

Deterministic (LLM-free) downstream of the two measurement audits:

  * governance/knn_label_disagreement.json  (D2544/D2557) — neighbor-agreement
  * governance/nli_label_audit.json         (D2558)       — T-NLI entailment

Produces two artifacts:

  1. D2547 per-(axis,label) calibration table — the empirical entail / agreement
     / contradiction distributions that unblock replacing the single global 5%
     semantic-error budget with cost-weighted per-label thresholds.
  2. A triaged mislabel queue — FB ids flagged by BOTH audits (low neighbor
     agreement AND T-NLI contradiction) ranked by contradiction strength, i.e.
     the highest-confidence mislabel/human-review candidates.

Read-only w.r.t. the DB. Writes via C6 safe_write.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from pipeline.io_guard import safe_write  # noqa: E402
from pipeline.pipeline_paths import S5_NLI_PASS_THRESHOLD  # noqa: E402

_KNN_FILE = _ROOT / "governance" / "knn_label_disagreement.json"
_NLI_FILE = _ROOT / "governance" / "nli_label_audit.json"
_OUT_CALIB = _ROOT / "governance" / "d2547_calibration.json"
_OUT_TRIAGE = _ROOT / "governance" / "mislabel_triage.json"
_OUT_TRIAGE_MD = _ROOT / "governance" / "mislabel_triage.md"
_TOP_N = 50  # C20: how many triage rows to surface in the .md


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _per_label_stats(nli: dict, knn: dict) -> list[dict]:
    """Join the two audits per (axis,label): entail + agreement distributions."""
    # NLI: group by (axis,label) over the FULL population (P0 #2), so the
    # statistics are full-population means, not flagged-subset flag-rates.
    nli_by_label: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for rec in nli.get("results", []):
        if rec.get("entail") is not None:
            nli_by_label[(rec["axis"], rec["label"])].append(rec)

    # kNN: group by (axis,label)
    knn_by_label: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for rec in knn.get("low_agreement", []):
        knn_by_label[(rec["axis"], rec["label"])].append(rec)

    rows: list[dict] = []
    labels: set[tuple[str, str]] = set(nli_by_label) | set(knn_by_label)
    for (axis, label) in sorted(labels):
        nli_recs = nli_by_label.get((axis, label), [])
        knn_recs = knn_by_label.get((axis, label), [])
        entails = [r["entail"] for r in nli_recs]
        contras = [r["contra"] for r in nli_recs]
        agrees = [r["agreement"] for r in knn_recs]
        # P0 #1: split contradiction-dominant vs weak-entailment into separate
        # counts instead of a conflated union ("nli_flagged").
        n_contradict = sum(1 for r in nli_recs if r.get("contra_dominant"))
        n_weak = sum(1 for r in nli_recs if r.get("weak") and not r.get("contra_dominant"))
        rows.append({
            "axis": axis,
            "label": label,
            "nli_total": len(nli_recs),
            "nli_contradict": n_contradict,
            "nli_weak": n_weak,
            "nli_flagged": n_contradict + n_weak,  # backward-compat union (P0 #1)
            "mean_entail": round(sum(entails) / len(entails), 4) if entails else None,
            "mean_contra": round(sum(contras) / len(contras), 4) if contras else None,
            "knn_low_agreement": len(knn_recs),
            "mean_agreement": round(sum(agrees) / len(agrees), 3) if agrees else None,
        })
    return rows


def _triage(nli: dict, knn: dict) -> list[dict]:
    """FBs flagged by both audits, ranked by contradiction strength."""
    knn_by_fb: dict[str, list[dict]] = defaultdict(list)
    for rec in knn.get("low_agreement", []):
        knn_by_fb[rec["fb_id"]].append(rec)

    contra_by_fb: dict[str, list[dict]] = defaultdict(list)
    for rec in nli.get("contradicts_label", []):
        contra_by_fb[rec["fb_id"]].append(rec)

    shared = set(knn_by_fb) & set(contra_by_fb)
    rows: list[dict] = []
    for fb_id in shared:
        krecs = knn_by_fb[fb_id]
        crecs = contra_by_fb[fb_id]
        min_agree = min(r["agreement"] for r in krecs)
        k_axis_label = sorted({(r["axis"], r["label"]) for r in krecs})
        max_gap = max(r["contra"] - r["entail"] for r in crecs)
        c_axis_label = sorted({(r["axis"], r["label"]) for r in crecs})
        rows.append({
            "fb_id": fb_id,
            "knn_min_agreement": min_agree,
            "knn_axes": [f"{a}:{l}" for a, l in k_axis_label],
            "nli_max_contra_gap": round(max_gap, 4),
            "nli_axes": [f"{a}:{l}" for a, l in c_axis_label],
        })
    rows.sort(key=lambda r: (-r["nli_max_contra_gap"], r["knn_min_agreement"]))
    return rows


def _build_md(triage: list[dict], top: int = _TOP_N) -> str:
    lines = [
        "# MISLABEL TRIAGE — intersection of k-NN + T-NLI audits",
        "",
        "> Highest-confidence mislabel/human-review candidates: an FB is listed "
        "only if it is flagged by BOTH the k-NN neighbor-disagreement audit "
        "(agreement ≤ 0.3) AND the T-NLI entailment audit (contradiction-dominant). "
        "Ranked by T-NLI contradiction gap (contra − entail), desc.",
        "",
        f"| # | fb_id | knn min agree | nli contra gap | knn axes | nli axes |",
        "|---|-------|--------------:|---------------:|----------|----------|",
    ]
    for i, r in enumerate(triage[:top], 1):
        lines.append(
            f"| {i} | `{r['fb_id']}` | {r['knn_min_agreement']} | "
            f"{r['nli_max_contra_gap']} | {', '.join(r['knn_axes'])} | "
            f"{', '.join(r['nli_axes'])} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    nli = _load(_NLI_FILE)
    knn = _load(_KNN_FILE)

    calib = _per_label_stats(nli, knn)
    triage = _triage(nli, knn)

    safe_write(_OUT_CALIB, json.dumps({
        "note": ("Per-(axis,label) FULL-POPULATION NLI statistics (P0 #2) with "
                 "contradict/weak split (P0 #1): nli_contradict = contradiction-"
                 "dominant pairs, nli_weak = weak-entailment pairs, nli_total = "
                 "full audited population. kNN remains a flag-subset (low-agreement)."),
        "weak_threshold": S5_NLI_PASS_THRESHOLD,
        "labels": calib,
    }, indent=2) + "\n", force_shrink=True)

    safe_write(_OUT_TRIAGE, json.dumps({
        "n_shared": len(triage),
        "knn_low_agreement_total": knn["summary"]["low_agreement_count"],
        "nli_contradict_total": nli["summary"]["contradicts_label"],
        "triage": triage,
    }, indent=2) + "\n", force_shrink=True)

    safe_write(_OUT_TRIAGE_MD, _build_md(triage), force_shrink=True)

    print(f"✅ D2547 calibration: {len(calib)} (axis,label) rows → {_OUT_CALIB.name}")
    print(f"✅ triage: {len(triage)} FBs shared by both audits "
          f"(kNN low-agree {knn['summary']['low_agreement_count']} ∩ "
          f"NLI contradict {nli['summary']['contradicts_label']}) → {_OUT_TRIAGE.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
