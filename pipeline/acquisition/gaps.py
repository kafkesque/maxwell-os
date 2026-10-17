"""The gap reader: what the knowledge layer CANNOT back, said in its three declared classes.

D-3078 fixed the classes and, more usefully, fixed WHERE each is measured. This module reads those sources and
never re-derives them:

  discipline_starvation  plan_targeted_ingestion.py's census (18 starved / 9 CRITICAL on 2026-10-17) — a
                         discipline whose golden and convergent counts fall short of the declared targets.
  primitive_absence      a query whose top-k retrieval cosine falls below a DECLARED tau. NO tau is calibrated
                         yet, so the class reports NOT_MEASURED until a readings file exists — a threshold that
                         only looks measured is the slop this lane exists to avoid (D-3036).
  claim_unsupported      stage5_verify.py's fail-closed verdicts. The file is read when present, and its absence
                         is reported as NOT_MEASURED rather than as "no unsupported claims".

A gap is only ever a QUESTION here. It authorises an ask, never a fetch; the fetch is a separate act with its own
owner word for any rung that is not lawful (D-3078).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import ROOT


def starvation_gaps(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """The measured starvation census, filtered to the eligible tiers and ordered by shortfall."""
    path = ROOT / str((cfg.get("gaps") or {}).get("starvation_census") or "governance/targeted_ingestion_plan.json")
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    eligible = {str(item).upper() for item in (cfg.get("gaps") or {}).get("tiers_eligible") or []}
    gaps = []
    for entry in payload.get("entries") or []:
        tier = str(entry.get("tier") or "").upper()
        if eligible and tier not in eligible:
            continue
        discipline = str(entry.get("discipline") or "").strip()
        if not discipline:
            continue
        gaps.append(
            {
                "gap_id": f"starvation:{discipline}",
                "class": "discipline_starvation",
                "discipline": discipline,
                "tier": tier,
                "trigger": {
                    "golden_count": entry.get("golden_count"),
                    "golden_shortfall": entry.get("golden_shortfall"),
                    "convergent_count": entry.get("convergent_count"),
                    "convergent_shortfall": entry.get("convergent_shortfall"),
                },
                "source": str(path.relative_to(ROOT)),
            }
        )
    gaps.sort(key=lambda gap: (-int(gap["trigger"].get("convergent_shortfall") or 0), gap["discipline"]))
    return gaps


def primitive_gaps(cfg: dict[str, Any], readings_path: Path | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Queries whose retrieval cosine falls below the declared tau, plus the reading that produced them.

    The readings file is a JSONL of {"query": str, "cosine": float}. It is DECLARED here and produced by the
    retrieval surface; when it is absent the class says NOT_MEASURED instead of inventing a threshold.
    """
    policy = (cfg.get("gaps") or {}).get("tau_cosine") or {}
    tau = float(policy.get("value") or 0.0)
    path = Path(readings_path) if readings_path else ROOT / str(
        (cfg.get("gaps") or {}).get("primitive_readings") or "knowledge pipeline/acquisition/primitive_readings.jsonl"
    )
    if not path.exists():
        return [], {"state": "NOT_MEASURED", "tau": tau, "why": f"no readings at {path}"}
    gaps = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        cosine = float(row.get("cosine") or 0.0)
        if cosine < tau:
            gaps.append(
                {
                    "gap_id": f"primitive:{row.get('query', '')[:60]}",
                    "class": "primitive_absence",
                    "query": str(row.get("query") or ""),
                    "discipline": str(row.get("discipline") or ""),
                    "trigger": {"cosine": cosine, "tau": tau},
                    "source": str(path),
                }
            )
    return gaps, {"state": "MEASURED", "tau": tau, "tau_state": policy.get("state", "unknown"), "rows": len(gaps)}


def claim_gaps(cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Unsupported claims from the fail-closed verifier, grouped by the claim's own discipline when it has one."""
    path = ROOT / str((cfg.get("gaps") or {}).get("verify_report") or "knowledge pipeline/checkpoints/stage5_verify_report.jsonl")
    if not path.exists():
        return [], {"state": "NOT_MEASURED", "why": f"no verify report at {path}"}
    gaps = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(row.get("verdict") or "").upper() not in {"UNSUPPORTED", "REFUTED", "FAIL"}:
            continue
        discipline = str(row.get("discipline") or "").strip()
        gaps.append(
            {
                "gap_id": f"claim:{str(row.get('claim_id') or row.get('id') or len(gaps))}",
                "class": "claim_unsupported",
                "discipline": discipline,
                "claim": str(row.get("claim") or "")[:400],
                "trigger": {"verdict": row.get("verdict"), "nli": row.get("nli_score")},
                "source": str(path.relative_to(ROOT)),
            }
        )
    return gaps, {"state": "MEASURED", "rows": len(gaps)}


def read_all(cfg: dict[str, Any], limit: int | None = None) -> dict[str, Any]:
    """All three classes, with every class that could not be measured NAMED rather than silently empty."""
    starvation = starvation_gaps(cfg)
    primitive, primitive_state = primitive_gaps(cfg)
    claims, claim_state = claim_gaps(cfg)
    ceiling = int(limit or (cfg.get("gaps") or {}).get("max_gaps_per_run") or 5)
    ordered = starvation + primitive + claims
    return {
        "schema_version": "1.0",
        "gen_model": "deterministic",
        "act": "gap_reader",
        "authority": "D-3078",
        "reading": {
            "discipline_starvation": {"state": "MEASURED" if starvation else "EMPTY", "rows": len(starvation)},
            "primitive_absence": primitive_state,
            "claim_unsupported": claim_state,
        },
        "gaps": ordered[:ceiling],
        "owed": ordered[ceiling:],
        "counts": {"total": len(ordered), "returned": min(len(ordered), ceiling)},
    }
