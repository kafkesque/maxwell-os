#!/usr/bin/env python3
"""build_phase0_adjudication_form.py — Phase-0 freeze: 149-core adjudication form.

D2613 ruled: freeze a human+DeepSeek-verified core (69→~150) as the SOLE eval
target before any further classification/voting.  This script emits the
adjudication artifact for the 149-core (69 frontier + 80 extension) across the
FOUR semantic axes that are all currently model-labelled and UNVERIFIED:

    content_type  (7-way)     — Qwen3.8 ontology-bound audit value
    depth         (4-way)     — Qwen3.8 ontology-bound audit value
    discipline    (61-way)    — Qwen3.8 ontology-bound audit value
    domains       (43-way)    — Qwen3.8 ontology-bound audit value (list)

For each axis the human sees: the AUDIT proposal (Qwen3.8, definition-grounded),
its deterministic agreement vs the gpt-oss SILVER label (computed here, NOT the
audit's self-reported `*_verdict` fields — those are LLM self-reports and are
internally inconsistent: they claim "override" even when the value is identical,
see BUG-242), the silver value, and a non-binding hint.

R5 discipline: the two generative labels (gpt-oss silver + Qwen3.8 audit) are the
generators; the human is the verifier.  Neither model is authoritative — the
42% cross-model depth disagreement + 57.5% domain-override rate prove it.

Outputs (both stamped R14):
    1. governance/phase0_149core_adjudication_form.md   — human-readable form
    2. governance/phase0_adjudication_ledger.jsonl      — machine apply path
       (one line per row: proposals pre-filled, human verdict fields empty)

Usage:
    python3 scripts/build_phase0_adjudication_form.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "config" / "golden" / "stage4_golden_mined.yaml"
FRONTIER69 = ROOT / "governance" / "deepseek_frontier69_audit_v2.json"
EXTENSION80 = ROOT / "governance" / "deepseek_extension80_audit.json"
FORM_OUT = ROOT / "governance" / "phase0_149core_adjudication_form.md"
LEDGER_OUT = ROOT / "governance" / "phase0_adjudication_ledger.jsonl"

# R14 stamps (C12: no hardcoded paths/models — module constants only for provenance)
SCHEMA_VERSION = "3.0"
PIPELINE_COMMIT = "phase0-149core"


def _norm_list(v: Any) -> set:
    if isinstance(v, str):
        return {s.strip().lower() for s in v.split(",") if s.strip()}
    return {str(s).strip().lower() for s in (v or []) if str(s).strip()}


def _differs(axis: str, audit_val: Any, silver_val: Any) -> bool:
    """Deterministic agree/disagree — NEVER trust the LLM self-reported verdict."""
    if silver_val is None:
        return False  # no silver baseline → nothing to compare
    if axis == "domains":
        return _norm_list(audit_val) != _norm_list(silver_val)
    return str(audit_val or "").strip().lower() != str(silver_val or "").strip().lower()


def load_golden() -> Dict[str, Dict[str, Any]]:
    data = yaml.safe_load(GOLDEN.read_text(encoding="utf-8")) or {}
    out: Dict[str, Dict[str, Any]] = {}
    for e in data.get("examples", []):
        fb = e.get("input_fb") or {}
        exp = e.get("expected_classification") or {}
        out[e["id"]] = {
            "name": fb.get("name", ""),
            "definition": fb.get("definition", ""),
            "mechanism": fb.get("mechanism", ""),
            "boundary": fb.get("boundary", ""),
            "silver_content_type": e.get("content_type"),
            "silver_depth": e.get("depth"),
            "silver_discipline": exp.get("discipline"),
            "silver_domains": exp.get("domains") or [],
        }
    return out


def load_audits() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for path in (FRONTIER69, EXTENSION80):
        data = json.loads(path.read_text(encoding="utf-8"))
        for eid, v in data.items():
            out[eid] = v
    return out


def _row_differs(row: Dict[str, Any]) -> bool:
    p = row["proposals"]
    s = row["silver"]
    return (
        _differs("depth", p["depth"], s["depth"])
        or _differs("discipline", p["discipline"], s["discipline"])
        or _differs("domains", p["domains"], s["domains"])
    )


def build_row(eid: str, gold: Dict[str, Any], audit: Dict[str, Any]) -> Dict[str, Any]:
    proposals = {
        "content_type": audit.get("content_type"),
        "depth": audit.get("depth"),
        "discipline": audit.get("discipline"),
        "domains": audit.get("domains"),
    }
    silver = {
        "content_type": gold.get("silver_content_type"),
        "depth": gold.get("silver_depth"),
        "discipline": gold.get("silver_discipline"),
        "domains": gold.get("silver_domains"),
    }
    differs = {
        "depth": _differs("depth", proposals["depth"], silver["depth"]),
        "discipline": _differs("discipline", proposals["discipline"], silver["discipline"]),
        "domains": _differs("domains", proposals["domains"], silver["domains"]),
    }
    # Priority = audit actually differs from silver on a semantic axis, OR
    # non-high confidence, OR non-principle content_type (depth is NA there).
    priority = (
        any(differs.values())
        or audit.get("confidence") != "high"
        or audit.get("content_type") != "principle"
    )
    # D2612: depth applies ONLY to principle.  Non-principle rows carrying a
    # 4-way depth are an audit-output defect (BUG-242) — flag, don't propagate.
    depth_na = proposals["content_type"] != "principle"
    return {
        "example_id": eid,
        "priority": "flagged" if priority else "clean",
        "name": gold.get("name", ""),
        "definition": gold.get("definition", ""),
        "mechanism": gold.get("mechanism", ""),
        "boundary": gold.get("boundary", ""),
        "proposals": proposals,
        "silver": silver,
        "differs": differs,
        "depth_na": depth_na,
        "audit_confidence": audit.get("confidence"),
        "audit_reason": audit.get("reason", ""),
        # human fills these (empty = pending):
        "human": {
            "content_type": None,
            "depth": None,
            "discipline": None,
            "domains": None,
        },
        "schema_version": SCHEMA_VERSION,
        "pipeline_commit": PIPELINE_COMMIT,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _fmt(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, list):
        return ", ".join(v) if v else "—"
    return str(v)


def main() -> int:
    gold = load_golden()
    audits = load_audits()

    missing = [eid for eid in audits if eid not in gold]
    if missing:
        print(f"WARN: {len(missing)} audit rows missing golden text: {missing[:5]}")
    ids = sorted(audits)
    rows = [build_row(eid, gold.get(eid, {}), audits[eid]) for eid in ids]
    rows.sort(key=lambda r: (r["priority"] != "flagged", r["example_id"]))

    n_flag = sum(1 for r in rows if r["priority"] == "flagged")
    print(f"149-core: {len(rows)} rows ({n_flag} flagged priority, "
          f"{len(rows) - n_flag} clean)")

    # ---- human-readable form ----
    md: List[str] = []
    md.append("# Phase-0 Freeze — 149-Core Adjudication Form")
    md.append("")
    md.append("> **Purpose (D2613):** freeze a human+DeepSeek-verified core as the SOLE eval target.")
    md.append("> Neither generative label is authoritative — CONFIRM or OVERRIDE each axis on the")
    md.append("> FULL text (definition + mechanism + boundary). The AUDIT proposal is non-binding.")
    md.append("> \"differs\" is computed deterministically here (NOT the audit's self-reported verdict).")
    md.append("")
    md.append(f"**Rows:** {len(rows)}  |  **Flagged (priority):** {n_flag}  |  "
              f"**Clean:** {len(rows) - n_flag}")
    md.append("")
    md.append("**Axes:** `content_type` (7-way) · `depth` (4-way) · `discipline` (61-way) · `domains` (43-way, list)")
    md.append("")
    md.append("---")
    md.append("")

    for r in rows:
        tag = "🔴 FLAGGED" if r["priority"] == "flagged" else "🟢 clean"
        md.append(f"## {r['example_id']} — {r['name']}  `[{tag}]`")
        md.append("")
        md.append(f"**Definition:** {r['definition']}")
        md.append("")
        if r["mechanism"]:
            md.append(f"**Mechanism:** {r['mechanism']}")
            md.append("")
        if r["boundary"]:
            md.append(f"**Boundary:** {r['boundary']}")
            md.append("")
        if r["audit_reason"]:
            md.append(f"**Audit reason:** {r['audit_reason']}")
            md.append("")
        md.append("| Axis | AUDIT (Qwen3.8) | differs? | silver (gpt-oss) | Human: CONFIRM / OVERRIDE |")
        md.append("|---|---|---|---|---|")
        for axis, key in (("content_type", "content_type"), ("depth", "depth"),
                          ("discipline", "discipline"), ("domains", "domains")):
            av = _fmt(r["proposals"][key])
            sv = _fmt(r["silver"][key])
            d = r["differs"].get(key, "")
            d_s = "YES" if d else ("—" if r["silver"][key] is None else "no")
            if key == "depth" and r["depth_na"]:
                # non-principle: depth is N/A per D2612 (audit output was wrong)
                md.append(f"| depth | `N/A (non-principle)` | — | `{sv}` | — (only if principle) |")
                continue
            md.append(f"| {axis} | `{av}` | {d_s} | `{sv}` | [ ] confirm / [ ] override: ____ |")
        md.append("")
        md.append("---")
        md.append("")

    FORM_OUT.write_text("\n".join(md), encoding="utf-8")

    # ---- machine ledger ----
    with LEDGER_OUT.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"wrote {FORM_OUT.name} ({len(rows)} rows)")
    print(f"wrote {LEDGER_OUT.name} ({len(rows)} rows)")
    print("priority: flagged first")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
