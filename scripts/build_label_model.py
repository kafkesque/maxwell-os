#!/usr/bin/env python3
"""scripts/build_label_model.py — D2585 P2 (Step 3B) weak-supervision label model.

Combines the two near-independent labeling functions into a probabilistic
mislabel score per FB, then ranks the golden training set by suspicion so the
high-disagreement subset can feed the generative challenger (P3) and the human
GOLD-A/B/C freeze (P5).

Labeling functions (verified near-independent by scripts/lf_dependency_audit.py):
  LF-1 T-NLI   — definition<->discipline contradiction (contra_dominant), high precision
  LF-2 cleanlab — Confident Learning self-confidence flag, high recall (uncalibrated)

Estimator: regularized Dawid-Skene EM over a binary latent (silver label
CORRECT vs WRONG), anchored by a prior on the silver-label accuracy. Because only
2 LFs are available the model is WEAKLY identified — a 3rd LF (the generative
challenger, P3) is required for full identifiability; this script reports the
2-LF estimate transparently and emits the challenger target set.

Read-only w.r.t. the DB. Writes governance/label_model_output.{json,md} and
temp/golden_labels_probabilistic.jsonl.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import numpy as np  # noqa: E402
import yaml  # noqa: E402

from pipeline.pipeline_paths import DB_PATH  # noqa: E402

_GOLDEN_YAML = _ROOT / "config" / "golden" / "stage4_golden_mined.yaml"
_NLI_JSON = _ROOT / "governance" / "nli_label_audit.json"
_CLEANLAB_JSON = _ROOT / "governance" / "cleanlab_label_audit.json"
_OUT_JSON = _ROOT / "governance" / "label_model_output.json"
_OUT_MD = _ROOT / "governance" / "label_model_output.md"
_OUT_JSONL = _ROOT / "temp" / "golden_labels_probabilistic.jsonl"

# C20: Dawid-Skene regularization constants.
_PRIOR_CORRECT = 0.80   # prior P(silver label correct) — gpt-oss teacher accuracy
_PRIOR_STRENGTH = 20.0  # pseudo-observations anchoring the prior (weak)
_SMOOTHING = 1.0        # Laplace pseudo-counts for theta/psi (avoid 0/0)
_MAX_ITER = 500
_TOL = 1e-6

_FB_ID_RE = re.compile(r"([0-9a-f]{64})")


def _load_golden(path: Path) -> list[dict]:
    """Load golden examples with their source fb_id extracted from the rationale."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for ex in doc.get("examples", []):
        m = _FB_ID_RE.search(ex.get("rationale", ""))
        exp = ex.get("expected_classification") or {}
        rows.append({
            "example_id": ex.get("id", ""),
            "fb_id": m.group(1) if m else "",
            "silver_discipline": exp.get("discipline", ""),
            "silver_domains": list(exp.get("domains", [])),
            "silver_depth": exp.get("depth", ""),
            "is_backfill": bool(ex.get("is_backfill", False)),
        })
    return rows


def _load_nli(path: Path) -> dict[str, dict]:
    """Return fb_id -> discipline-axis NLI record."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for r in doc.get("results", []):
        if r.get("axis") == "discipline":
            out[r["fb_id"]] = r
    return out


def _load_cleanlab(path: Path) -> tuple[set[str], set[str]]:
    """Return (flagged_fb_ids set, assessed_fb_ids set) for cleanlab."""
    doc = json.loads(path.read_text(encoding="utf-8"))
    flagged = set(doc.get("flagged_fb_ids", []))
    conn = sqlite3.connect(DB_PATH)
    try:
        assessed = {
            r[0] for r in conn.execute(
                "SELECT fb_id FROM fbs WHERE definition IS NOT NULL AND definition != '' "
                "AND discipline IS NOT NULL AND discipline != '' AND discipline != 'emerging'"
            )
        }
    finally:
        conn.close()
    return flagged, assessed


def _build_votes(
    fb_ids: list[str], nli: dict[str, dict], cleanlab_flags: set[str]
) -> tuple[np.ndarray, np.ndarray]:
    """Build the (n, 2) binary vote matrix + availability mask.

    Column 0 = T-NLI contra_dominant, column 1 = cleanlab flagged. Missing NLI
    is encoded as 0 and masked out of the EM (so it does not bias the estimate).
    """
    votes = np.zeros((len(fb_ids), 2), dtype=np.float64)
    avail = np.zeros((len(fb_ids), 2), dtype=np.float64)
    for i, fb_id in enumerate(fb_ids):
        rec = nli.get(fb_id)
        if rec is not None:
            votes[i, 0] = 1.0 if rec.get("contra_dominant") else 0.0
            avail[i, 0] = 1.0
        votes[i, 1] = 1.0 if fb_id in cleanlab_flags else 0.0
        avail[i, 1] = 1.0
    return votes, avail


def _dawid_skene(
    votes: np.ndarray, avail: np.ndarray
) -> tuple[dict, np.ndarray]:
    """Regularized Dawid-Skene EM over a binary latent (label CORRECT/WRONG).

    Returns (params, p_wrong) where p_wrong[i] = P(latent = WRONG | votes_i).
    """
    n, m = votes.shape
    pi = _PRIOR_CORRECT
    theta = np.full(m, 0.30)  # P(flag | correct)  — false-positive rate
    psi = np.full(m, 0.60)    # P(flag | wrong)    — true-positive rate

    prev = np.full(n, 0.5)
    for _ in range(_MAX_ITER):
        # E-step: posterior P(wrong | votes) under current params.
        log_correct = np.log(pi + 1e-12) + np.sum(
            avail * (votes * np.log(theta + 1e-12) + (1 - votes) * np.log(1 - theta + 1e-12)),
            axis=1,
        )
        log_wrong = np.log(1 - pi + 1e-12) + np.sum(
            avail * (votes * np.log(psi + 1e-12) + (1 - votes) * np.log(1 - psi + 1e-12)),
            axis=1,
        )
        logsum = np.logaddexp(log_correct, log_wrong)
        p_wrong = np.exp(log_wrong - logsum)
        p_correct = np.exp(log_correct - logsum)

        # M-step with regularization.
        correct_mass = (avail * p_correct[:, None]).sum(axis=0) + _SMOOTHING
        wrong_mass = (avail * p_wrong[:, None]).sum(axis=0) + _SMOOTHING
        theta = (avail * votes * p_correct[:, None]).sum(axis=0) / correct_mass
        psi = (avail * votes * p_wrong[:, None]).sum(axis=0) / wrong_mass
        # Enforce informative LFs (psi >= theta); swap if degenerate.
        theta = np.minimum(theta, psi)
        psi = np.maximum(psi, theta)
        # Anchor pi with a Beta prior (pseudo-observations).
        pi = (p_correct.sum() + _PRIOR_CORRECT * _PRIOR_STRENGTH) / (
            n + _PRIOR_STRENGTH
        )

        if np.max(np.abs(p_wrong - prev)) < _TOL:
            break
        prev = p_wrong

    return {"pi_correct": float(pi), "theta": theta.tolist(), "psi": psi.tolist()}, p_wrong


def _tier(nli_flag: int, cleanlab_flag: int) -> str:
    if nli_flag and cleanlab_flag:
        return "both"
    if nli_flag:
        return "nli_only"
    if cleanlab_flag:
        return "cleanlab_only"
    return "neither"


def main() -> int:
    golden = _load_golden(_GOLDEN_YAML)
    nli = _load_nli(_NLI_JSON)
    cleanlab_flags, cleanlab_assessed = _load_cleanlab(_CLEANLAB_JSON)

    # 1) Estimate LF params on the FULL assessed population (more data = stable params).
    assessed_sorted = sorted(cleanlab_assessed)
    pop_votes, pop_avail = _build_votes(assessed_sorted, nli, cleanlab_flags)
    params, pop_p_wrong = _dawid_skene(pop_votes, pop_avail)

    # 2) Apply to the golden training set.
    golden_ids = [g["fb_id"] for g in golden]
    gold_votes, gold_avail = _build_votes(golden_ids, nli, cleanlab_flags)
    _, gold_p_wrong = _dawid_skene(gold_votes, gold_avail)

    rows: list[dict] = []
    for g, votes, avail, p_wrong in zip(golden, gold_votes, gold_avail, gold_p_wrong):
        nli_flag = int(votes[0])
        cl_flag = int(votes[1])
        rows.append({
            "fb_id": g["fb_id"],
            "example_id": g["example_id"],
            "silver_discipline": g["silver_discipline"],
            "silver_domains": g["silver_domains"],
            "silver_depth": g["silver_depth"],
            "is_backfill": g["is_backfill"],
            "p_mislabel": round(float(p_wrong), 4),
            "lf_votes": {"t_nli": nli_flag, "cleanlab": cl_flag},
            "nli_available": bool(avail[0]),
            "tier": _tier(nli_flag, cl_flag),
            "source": "label_model_v1",
        })

    # Summary: how many golden FBs fall in each tier + distribution of p_mislabel.
    tiers: dict[str, int] = {}
    for r in rows:
        tiers[r["tier"]] = tiers.get(r["tier"], 0) + 1
    p_arr = np.array([r["p_mislabel"] for r in rows])

    # Challenger/GOLD-A seed: the high-suspicion subset (both-flag + NLI-only).
    high_suspicion = [r for r in rows if r["tier"] in ("both", "nli_only")]
    high_suspicion.sort(key=lambda r: -r["p_mislabel"])

    report = {
        "params": params,
        "population": {"n": len(assessed_sorted), "p_correct_prior": _PRIOR_CORRECT},
        "golden": {
            "n": len(rows),
            "tiers": tiers,
            "p_mislabel_mean": round(float(p_arr.mean()), 4),
            "p_mislabel_median": round(float(np.median(p_arr)), 4),
            "n_high_suspicion": len(high_suspicion),
        },
    }
    _OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _OUT_JSONL.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )

    md = [
        "# LABEL MODEL OUTPUT — Step 3B (D2585 P2)",
        "",
        "## Estimated LF parameters (Dawid-Skene, 2 LF, weakly identified)",
        "",
        "| LF | P(flag\\|correct) θ | P(flag\\|wrong) ψ |",
        "|---|---|---|",
        f"| T-NLI contradiction | {params['theta'][0]:.4f} | {params['psi'][0]:.4f} |",
        f"| cleanlab | {params['theta'][1]:.4f} | {params['psi'][1]:.4f} |",
        "",
        f"P(label correct) π = {params['pi_correct']:.4f} (prior {_PRIOR_CORRECT}).",
        "",
        "## Golden-set suspicion tiers",
        "",
        "| Tier | Count |",
        "|---|---|",
    ]
    for t in ("both", "nli_only", "cleanlab_only", "neither"):
        md.append(f"| {t} | {tiers.get(t, 0)} |")
    md += [
        "",
        f"Mean P(mislabel) = {report['golden']['p_mislabel_mean']}, "
        f"median = {report['golden']['p_mislabel_median']}.",
        "",
        f"**High-suspicion subset (both-flag + NLI-only) = {len(high_suspicion)} FBs** "
        f"— the P3 generative-challenger / GOLD-A seed.",
        "",
    ]
    _OUT_MD.write_text("\n".join(md), encoding="utf-8")

    print(json.dumps(report, indent=2))
    print(f"\nhigh-suspicion subset: {len(high_suspicion)} FBs")
    print(f"wrote {_OUT_JSON}, {_OUT_MD}, {_OUT_JSONL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
