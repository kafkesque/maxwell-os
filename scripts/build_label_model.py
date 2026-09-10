#!/usr/bin/env python3
"""scripts/build_label_model.py — D2585 P2/P4 weak-supervision label model.

Combines three labeling functions into a probabilistic mislabel score per FB,
then ranks the golden training set by suspicion so the high-disagreement subset
feeds the human GOLD-A/B/C freeze (P5) and the corrected training set (P4).

Labeling functions (verified near-independent by scripts/lf_dependency_audit.py):
  LF-1 T-NLI       — definition<->discipline contradiction (contra_dominant), high precision
  LF-2 cleanlab    — Confident Learning self-confidence flag, high recall (uncalibrated)
  LF-3 challenger  — 3-model generative challenger (P3): votes 1 where a 2/3
                     majority DISAGREES with the teacher silver label, 0 where it
                     AGREES, abstains on no-majority (fail-closed) FBs.

Estimator: regularized Dawid-Skene EM over a binary latent (silver label
CORRECT vs WRONG), anchored by a prior on the silver-label accuracy. With LF-3
added the model is identified on the 135 challenger-voted golden FBs (was weakly
identified with 2 LFs only).

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
_CHALLENGER_JSONL = _ROOT / "temp" / "label_vote_high_suspicion.jsonl"

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


def _load_challenger(path: Path) -> dict[str, dict]:
    """Return example_id -> challenger vote record for the P3 high-suspicion run.

    The challenger record's fb_id IS the golden example id (label_vote.py keys
    golden targets by example id). The LF-3 vote is derived from the consensus:
      vote 1  = 2/3 challenger majority DISAGREES with the teacher silver label,
      vote 0  = challenger majority AGREES with the teacher,
      abstain = no 2/3 majority (fail-closed 'emerging') -> no LF signal.
    """
    out: dict[str, dict] = {}
    raw_records: list[dict] = json.loads(path.read_text(encoding="utf-8"))
    for r in raw_records:
        cons = r.get("consensus") or {}
        cons_disc = cons.get("discipline")
        cur_disc = r.get("current_discipline")
        if cons_disc is None or cons_disc == "emerging" or cons_disc == cur_disc:
            vote: int | None = None if (cons_disc is None or cons_disc == "emerging") else 0
            correction: str | None = None
        else:
            vote, correction = 1, cons_disc
        out[r["fb_id"]] = {
            "vote": vote,
            "correction": correction,
            "consensus_discipline": cons_disc,
            "current_discipline": cur_disc,
        }
    return out


def _build_votes(
    fb_ids: list[str],
    nli: dict[str, dict],
    cleanlab_flags: set[str],
    challenger: dict[str, dict],
) -> tuple[np.ndarray, np.ndarray]:
    """Build the (n, 3) binary vote matrix + availability mask.

    Column 0 = T-NLI contra_dominant, column 1 = cleanlab flagged,
    column 2 = challenger disagreement (LF-3). Missing NLI / challenger-abstain
    is encoded as 0 and masked out of the EM (so it does not bias the estimate).
    """
    votes = np.zeros((len(fb_ids), 3), dtype=np.float64)
    avail = np.zeros((len(fb_ids), 3), dtype=np.float64)
    for i, fb_id in enumerate(fb_ids):
        rec = nli.get(fb_id)
        if rec is not None:
            votes[i, 0] = 1.0 if rec.get("contra_dominant") else 0.0
            avail[i, 0] = 1.0
        votes[i, 1] = 1.0 if fb_id in cleanlab_flags else 0.0
        avail[i, 1] = 1.0
        ch = challenger.get(fb_id)
        if ch is not None and ch["vote"] is not None:
            votes[i, 2] = float(ch["vote"])
            avail[i, 2] = 1.0
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
    challenger_by_example = _load_challenger(_CHALLENGER_JSONL)
    # LF-3 is keyed by golden EXAMPLE id (S4-GOLD-MINED-*); NLI/cleanlab and the
    # DB operate on the 64-hex source fb_id. Align through the golden mapping so
    # the vote matrices stay in one id space.
    challenger: dict[str, dict] = {}
    for g in golden:
        ch = challenger_by_example.get(g["example_id"])
        if ch is not None:
            challenger[g["fb_id"]] = ch

    # 1) Estimate LF params on the FULL assessed population (more data = stable params).
    assessed_sorted = sorted(cleanlab_assessed)
    pop_votes, pop_avail = _build_votes(assessed_sorted, nli, cleanlab_flags, challenger)
    params, pop_p_wrong = _dawid_skene(pop_votes, pop_avail)

    # 2) Apply to the golden training set.
    golden_ids = [g["fb_id"] for g in golden]
    gold_votes, gold_avail = _build_votes(golden_ids, nli, cleanlab_flags, challenger)
    _, gold_p_wrong = _dawid_skene(gold_votes, gold_avail)

    rows: list[dict] = []
    for g, votes, avail, p_wrong in zip(golden, gold_votes, gold_avail, gold_p_wrong):
        nli_flag = int(votes[0])
        cl_flag = int(votes[1])
        ch_flag = int(votes[2]) if avail[2] else None
        ch = challenger_by_example.get(g["example_id"])
        rows.append({
            "fb_id": g["fb_id"],
            "example_id": g["example_id"],
            "silver_discipline": g["silver_discipline"],
            "silver_domains": g["silver_domains"],
            "silver_depth": g["silver_depth"],
            "is_backfill": g["is_backfill"],
            "p_mislabel": round(float(p_wrong), 4),
            "lf_votes": {"t_nli": nli_flag, "cleanlab": cl_flag,
                         "challenger": ch_flag},
            "nli_available": bool(avail[0]),
            "tier": _tier(nli_flag, cl_flag),
            "challenger_correction": (ch or {}).get("correction"),
            "source": "label_model_v2",
        })

    # Summary: how many golden FBs fall in each tier + distribution of p_mislabel.
    tiers: dict[str, int] = {}
    for r in rows:
        tiers[r["tier"]] = tiers.get(r["tier"], 0) + 1
    p_arr = np.array([r["p_mislabel"] for r in rows])

    # Challenger/GOLD-A seed: the high-suspicion subset (both-flag + NLI-only).
    high_suspicion = [r for r in rows if r["tier"] in ("both", "nli_only")]
    high_suspicion.sort(key=lambda r: -r["p_mislabel"])

    ch_avail = sum(1 for r in rows if r["lf_votes"]["challenger"] is not None)
    ch_vote1 = sum(1 for r in rows if r["lf_votes"]["challenger"] == 1)
    ch_vote0 = sum(1 for r in rows if r["lf_votes"]["challenger"] == 0)

    report = {
        "params": params,
        "population": {"n": len(assessed_sorted), "p_correct_prior": _PRIOR_CORRECT},
        "golden": {
            "n": len(rows),
            "tiers": tiers,
            "p_mislabel_mean": round(float(p_arr.mean()), 4),
            "p_mislabel_median": round(float(np.median(p_arr)), 4),
            "n_high_suspicion": len(high_suspicion),
            "challenger_lf3": {
                "n_available": ch_avail,
                "n_disagree_vote1": ch_vote1,
                "n_agree_vote0": ch_vote0,
                "n_abstain": len(rows) - ch_avail,
            },
        },
    }
    _OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _OUT_JSONL.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )

    md = [
        "# LABEL MODEL OUTPUT — Step 3B/3C (D2585 P2 + P4 LF-3)",
        "",
        "## Estimated LF parameters (Dawid-Skene, 3 LF)",
        "",
        "| LF | P(flag\\|correct) θ | P(flag\\|wrong) ψ |",
        "|---|---|---|",
        f"| T-NLI contradiction | {params['theta'][0]:.4f} | {params['psi'][0]:.4f} |",
        f"| cleanlab | {params['theta'][1]:.4f} | {params['psi'][1]:.4f} |",
        f"| challenger (LF-3) | {params['theta'][2]:.4f} | {params['psi'][2]:.4f} |",
        "",
        f"P(label correct) π = {params['pi_correct']:.4f} (prior {_PRIOR_CORRECT}).",
        "",
        "## Golden-set suspicion tiers (2-LF tier retained for P3-compat)",
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
