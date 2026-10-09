#!/usr/bin/env python3
"""d2884b_decider_ab.py — D-2884(b) decider A/B: distinct-family decider vs owner 3-way macro referee.

PURPOSE (D-2884(b) / D-2767 C+B gate)
--------------------------------------
D-2884(a) demoted the fine 62-way `discipline` axis to ADVISORY provenance and made the
3-way MACRO (Technical / Human & Design / Method & Business) + `emerging` the OPERATIVE
routing facet. D-2884(b) requires a DISTINCT-FAMILY decider (a dedicated decision model,
NOT the gpt-oss classifier) evaluated against the owner referee before the macro axis
can ship as a hard gate. D-2727 (full S4->S5->S6 rerun) stays BLOCKED until (a)+(b) land.

The gate (D-2767): the decider must reproduce the owner's 3-way macro routing at
coarse_kappa >= discipline_coarse_kappa_floor (0.73, retargeted to the human coarse
ceiling D-2796) AND emerging_rate <= emerging_discipline_rate_max (0.35). If it clears
both, the decider becomes decider-of-record for the macro axis; otherwise the macro axis
remains advisory and the owner re-scopes (no below-ceiling classifier ships — D-2796).

REFEREE (frozen): governance/d2767_ab_v8_20261009.json (194 rows, owner-finalized gold
fine discipline + abstentions already mapped to 'emerging' by the D-2830 rule). Full FB
text (definition/mechanism/boundary/consequence/source) is joined from the v8 anchor via
the production ``load_anchor`` (zero drift — the same text the gpt-oss arm saw).

ZERO-DRIFT REUSE: cohen_kappa / per_class_metrics / load_anchor (discipline_conformance_gate),
load_macro / to_macro (discipline_macro_classify, C21 single home). The 3-way+emerging
criteria are DERIVED from config (discipline_macro_groups.yaml + closed_menu_v8.json) — no
hardcoded ontology (C12).

MODES:
  --plan            NO model loaded. Validate referee join, gold collapse, criteria build
                    and gate math; print the exact per-row state + criteria + collapsed
                    gold; exit 0 on consistency, 1 on any drift. (Runs on the system python3.)
  --arm pplx|laya   run the decider. pplx requires .venv_pplx/bin/python (mlx 0.32.3 /
                    mlx-vlm 0.7.6 / transformers 5.19.0). laya requires .venv_laya/bin/python.

Determinism: the decider is a classifier (noncausal attention -> softmax over the 255-way
readout); argmax is deterministic (no sampling), so no determinism self-check is required
unlike the OMLX chat path (BUG-655). Verdict stays ADVISORY (D-2798): this script reports
the gate and NEVER fails closed on its own; promoting the decider is the owner's gate.

Exit: 0 = measurement completed (advisory); 1 = load/inference/ontology error.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
for p in (str(REPO), str(SCRIPTS)):
    if p not in sys.path:
        sys.path.insert(0, p)

from discipline_conformance_gate import cohen_kappa, load_anchor, per_class_metrics  # noqa: E402
from discipline_macro_classify import load_macro, to_macro  # noqa: E402

# C12: paths are stable artifacts, but the model snapshot is version-pinned (R14 provenance).
DEFAULT_REFEREE = REPO / "governance" / "d2767_ab_v8_20261009.json"
DEFAULT_ANCHOR = REPO / "governance" / "discipline_anchor_rederived_v8_20261007.json"
PPX_SNAPSHOT = (
    Path.home() / ".cache/huggingface/hub/models--mlx-community--pplx-decider-v1.1-27b-4bit"
    / "snapshots/66383f28b37637658b02b8e82b1029598b138642"
)
# Base (typed-decision bundle, BUG-364) — ModernBERT-large encoder + 2-layer RL head. The
# 'typed-decisions' subfolder is a near-identical sibling; bakeoff_laya.yaml pins the BASE
# model.safetensors (sha256 891102d3…) as the typed-decision bundle, so subfolder=None.
LAYA_SNAPSHOT = (
    Path.home() / ".cache/huggingface/hub/models--convaiinnovations--laya"
    / "snapshots/7b928d828b7b0e022f929d9bd2e44165aa270148"
)
SOURCE_MAX = 600  # source_text truncation, mirrors build_merged_prompt (C12 parity)


def load_thresholds() -> tuple[float, float]:
    """Read the C+B gate floors from config (C12); fail-closed on missing."""
    import yaml

    cfg = yaml.safe_load((REPO / "config" / "pipeline_config.yaml").read_text(encoding="utf-8")) or {}
    s4 = cfg.get("stage4", {})
    tax = cfg.get("taxonomy", {})
    coarse_floor = float(s4.get("discipline_coarse_kappa_floor", 0.73))
    emerging_max = float(tax.get("emerging_discipline_rate_max", 0.35))
    return coarse_floor, emerging_max


def criteria_from_config() -> dict[str, str]:
    """Derive the 3-way+emerging choice criteria from config (zero hardcode, C12).

    Returns {bucket: description} in macro-bucket order with the emerging routing bucket
    LAST. Descriptions enumerate the menu groups + their discipline members so the decider
    sees the exact owner-adjudicated scope of each macro bucket.
    """
    import yaml

    groups_doc = yaml.safe_load((REPO / "config" / "discipline_macro_groups.yaml").read_text(encoding="utf-8")) or {}
    scheme = str(groups_doc.get("scheme", "3-way"))
    macros: dict[str, list[str]] = groups_doc.get("macros", {}).get(scheme) or {}
    emerging = str(groups_doc.get("emerging_routing", "emerging"))
    if not macros:
        raise SystemExit(f"FAIL: macro scheme {scheme!r} has no bucket map (discipline_macro_groups.yaml)")

    menu = json.loads((REPO / "config" / "closed_menu_v8.json").read_text(encoding="utf-8"))
    group_to_disciplines: dict[str, list[str]] = {}
    for d in menu.get("disciplines", []):
        g = str(d.get("group", ""))
        v = str(d.get("value", ""))
        if g and v:
            group_to_disciplines.setdefault(g, []).append(v)

    criteria: dict[str, str] = {}
    for bucket, groups in macros.items():
        parts: list[str] = []
        for g in groups:
            members = group_to_disciplines.get(g, [])
            if not members:
                raise SystemExit(f"FAIL: macro bucket {bucket!r} group {g!r} has no disciplines (closed_menu_v8.json)")
            parts.append(f"{g} ({', '.join(members)})")
        criteria[bucket] = "Covers: " + "; ".join(parts) + "."
    criteria[emerging] = (
        "None of the established macro disciplines fit — the item is off-menu, novel, or "
        "ambiguous and must be routed for further review rather than forced into a bucket."
    )
    return criteria


def state_from_example(e: dict) -> str:
    """Build a clean (instruction-free) state for the decider from the FB text fields.

    The decider treats state as data, not instructions, so this deliberately omits the
    classification instruction that build_merged_prompt embeds for the gpt-oss chat path.
    """
    lines = [f"NAME: {e.get('name', '')}", f"DEFINITION: {e.get('definition', '')}"]
    for field in ("mechanism", "boundary", "consequence"):
        val = e.get(field, "")
        if val:
            lines.append(f"{field.upper()}: {val}")
    src = e.get("source_text", "")
    if src:
        lines.append(f"SOURCE TEXT: {src[:SOURCE_MAX]}")
    return "\n".join(lines)


def load_referee_rows(referee_path: Path, anchor_path: Path) -> list[dict]:
    """Load the FROZEN referee gold and join full text from the v8 anchor (zero drift).

    The referee JSON is the owner-finalized 194-row gold (noise_drop rows already excluded,
    abstentions already mapped to 'emerging'). Full text is joined by item_id through the
    production ``load_anchor`` (same text the gpt-oss arm saw). Fail-closed on any
    item_id/name mismatch (referee <-> anchor drift guard, BUG-624 class).
    """
    ref_doc = json.loads(referee_path.read_text(encoding="utf-8"))
    ref_rows = ref_doc.get("rows", [])
    if not ref_rows:
        raise SystemExit(f"FAIL: referee has no rows: {referee_path}")

    anchor_rows = load_anchor(str(anchor_path))
    anchor_by_id = {a["item_id"]: a for a in anchor_rows}

    out: list[dict] = []
    for r in ref_rows:
        iid = r.get("item_id")
        a = anchor_by_id.get(iid)
        if a is None:
            raise SystemExit(f"FAIL: referee row {iid!r} not joinable to anchor (item_id drift)")
        if a.get("name") != r.get("name"):
            raise SystemExit(f"FAIL: referee row {iid!r} name drift: {r.get('name')!r} != {a.get('name')!r}")
        out.append(
            {
                "item_id": iid,
                "name": r.get("name", ""),
                "gold": r.get("gold", ""),
                "state": state_from_example(a),
            }
        )
    return out


def collapse_gold(rows: list[dict]) -> tuple[list[str], str]:
    """Collapse fine gold -> 3-way macro via C21 single home; fail-closed on drift."""
    scheme, _bucket_members, disc_to_bucket = load_macro()
    gold_macro = [to_macro(r["gold"], disc_to_bucket) for r in rows]
    return gold_macro, scheme


def gate_report(gold: list[str], pred: list[str], coarse_floor: float, emerging_max: float) -> dict:
    """Compute the C+B gate: coarse_kappa + emerging_rate + per-bucket metrics."""
    n = len(gold)
    if n == 0:
        raise SystemExit("FAIL: empty referee — nothing to measure")
    if len(pred) != n:
        raise SystemExit(f"FAIL: pred length {len(pred)} != gold length {n}")
    kappa = cohen_kappa(gold, pred)
    acc = sum(1 for g, p in zip(gold, pred) if g == p) / n
    emerging_rate = sum(1 for p in pred if p == "emerging") / n
    return {
        "n": n,
        "raw_agreement": round(acc, 4),
        "coarse_kappa": round(kappa, 4),
        "coarse_floor": coarse_floor,
        "coarse_pass": bool(kappa >= coarse_floor),
        "emerging_rate": round(emerging_rate, 4),
        "emerging_max": emerging_max,
        "emerging_pass": bool(emerging_rate <= emerging_max),
        "cb_gate_pass": bool(kappa >= coarse_floor and emerging_rate <= emerging_max),
        "per_bucket": per_class_metrics(gold, pred),
    }


def _git_commit() -> str:
    """Short git HEAD for the R14 stamp; empty on failure (metadata, never gate)."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(REPO), capture_output=True, text=True, timeout=10
        )
        return out.stdout.strip()
    except Exception as e:  # C16: log AND continue — stamp is metadata.
        print(f"⚠️  git HEAD unreadable for R14 stamp ({type(e).__name__}: {e})", file=sys.stderr)
        return ""


def _atomic_write_json(path: Path, payload: dict) -> None:
    """Crash-safe write (C6): tempfile -> fsync -> os.replace in the same directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _run_arm_pplx(rows: list[dict], criteria: dict[str, str]) -> list[str]:
    """Run the pplx decider (choice over the 3-way+emerging criteria) and return argmax labels."""
    sys.path.insert(0, str(PPX_SNAPSHOT))
    try:
        import decider_mlx  # noqa: F401  (lazy: requires .venv_pplx)
    except ImportError as e:
        raise SystemExit(
            f"FAIL: cannot import decider_mlx — run with .venv_pplx/bin/python "
            f"(mlx 0.32.3 / mlx-vlm 0.7.6): {e}"
        ) from e

    model = decider_mlx.Decider.from_pretrained(str(PPX_SNAPSHOT))
    keys = list(criteria.keys())
    question = {"type": "choice", "criteria": criteria}
    decider_rows = [{"state": r["state"], "question": question} for r in rows]
    probs = model.predict(decider_rows, batch_size=8, token_budget=4096)
    preds: list[str] = []
    for p in probs:
        best = max(range(len(p)), key=p.__getitem__)
        preds.append(keys[best])
    return preds


def _run_arm_laya(rows: list[dict], criteria: dict[str, str]) -> list[str]:
    """Run the laya decider (Arm B) — MLX RL-agent, typed-decision bundle (D-305/BUG-364).

    Distinct family from pplx (ModernBERT-large ~421M encoder + 2-layer RL head vs the
    Qwen3.8-27B decision readout). Same 3-way+emerging choice criteria. laya REQUIRES an
    explicit ``instructions`` field (its _to_internal raises without one) — unlike pplx's
    instruction-free question — so a minimal neutral instruction names the choice task and
    the bucket scope stays in the criteria (zero hardcode, C12). laya's 512-token context
    truncates the state front-first and caps each option text at 48 tokens (its own
    build_prefix); this is a documented Arm-B-only constraint, not a gate asymmetry.
    """
    try:
        from laya_mlx.agent import Agent  # lazy: requires .venv_laya
    except ImportError as e:
        raise SystemExit(f"FAIL: cannot import laya_mlx — run with .venv_laya/bin/python: {e}") from e

    instructions = "Choose the single macro-discipline bucket that best fits the item."
    question = {"type": "choice", "criteria": criteria, "instructions": instructions}
    agent = Agent(model_id_or_path=str(LAYA_SNAPSHOT), batch_size=16)
    preds: list[str] = []
    for r in rows:
        result = agent.system_one(r["state"], {"q1": question})
        choice = result["answers"]["q1"]["choice"]
        if choice not in criteria:
            raise SystemExit(f"FAIL: laya returned unknown label {choice!r} (criteria drift)")
        preds.append(choice)
    return preds


# C21 swappable infrastructure: every decider arm is a callable behind the SAME
# Jev/SystemOne contract — run_fn(rows, criteria) -> list[str] of argmax labels, where
# criteria is {bucket: description} and each returned label is a criteria key. Adding a
# decider (e.g. mlx-community/clef-flash-4bit, manjunathshiva/opendecider-small-mlx-4bit,
# wfzyx/von) = add ONE registry entry + ONE run function; the referee/gate/criteria
# machinery is shared (zero duplication, zero drift).
DECIDER_ARMS: dict[str, tuple[Callable[[list[dict], dict[str, str]], list[str]], str]] = {
    "pplx": (_run_arm_pplx, "pplx-decider-v1.1-27b-4bit"),
    "laya": (_run_arm_laya, "convaiinnovations/laya"),
}


def main() -> int:
    ap = argparse.ArgumentParser(description="D-2884(b) decider A/B against the owner 3-way macro referee.")
    ap.add_argument("--referee", default=str(DEFAULT_REFEREE))
    ap.add_argument("--anchor", default=str(DEFAULT_ANCHOR))
    ap.add_argument("--arm", choices=list(DECIDER_ARMS), default=None, help="run this decider arm (omit for --plan)")
    ap.add_argument("--plan", action="store_true", help="validate ontology + gate math WITHOUT loading a model")
    ap.add_argument("--limit", type=int, default=None, help="smoke: run only the first N rows")
    ap.add_argument("--out", default=None, help="R14-stamped JSON output path")
    args = ap.parse_args()

    referee_path = Path(args.referee)
    anchor_path = Path(args.anchor)
    coarse_floor, emerging_max = load_thresholds()

    rows = load_referee_rows(referee_path, anchor_path)
    if args.limit is not None:
        rows = rows[: args.limit]
    gold_macro, scheme = collapse_gold(rows)
    criteria = criteria_from_config()

    # C12/R14: the criteria keys MUST equal the macro buckets + emerging (the gate's label space).
    expected_buckets = set(gold_macro)
    if not set(criteria.keys()) >= expected_buckets:
        raise SystemExit(
            f"FAIL: criteria keys {list(criteria.keys())} do not cover gold buckets {sorted(expected_buckets)}"
        )

    if args.plan:
        print("d2884b_decider_ab --plan (no model)")
        print(f"  referee = {referee_path}  ({len(rows)} rows after join)")
        print(f"  anchor  = {anchor_path}")
        print(f"  macro scheme = {scheme}")
        print(f"  C+B gate: coarse_kappa >= {coarse_floor}  AND  emerging <= {emerging_max}")
        from collections import Counter

        print(f"  gold macro distribution: {dict(Counter(gold_macro))}")
        print(f"  criteria keys (order = decider option order): {list(criteria.keys())}")
        print("\n  criteria:")
        for k, v in criteria.items():
            print(f"    - {k}: {v}")
        print("\n  sample state (row 0):")
        print("    " + rows[0]["state"].replace("\n", "\n    "))
        print("\n  PLAN OK: referee join, gold collapse, criteria build and gate math are consistent.")
        print("  Next: run the decider with `.venv_pplx/bin/python scripts/d2884b_decider_ab.py --arm pplx`")
        return 0

    if args.arm is None:
        print("Nothing to do: pass --plan or --arm pplx|laya.", file=sys.stderr)
        return 1

    run_fn, gen_model = DECIDER_ARMS[args.arm]
    pred = run_fn(rows, criteria)

    report = gate_report(gold_macro, pred, coarse_floor, emerging_max)
    out_rows = [
        {
            "item_id": r["item_id"],
            "name": r["name"],
            "gold_fine": r["gold"],
            "gold": gm,
            "pred": p,
            "agree": bool(gm == p),
        }
        for r, gm, p in zip(rows, gold_macro, pred)
    ]

    print(f"\n[D-2884(b) decider A/B — arm {args.arm}]")
    print(f"  model = {gen_model}   N = {report['n']}")
    print(f"  raw agreement (3-way+emerging): {report['raw_agreement']:.4f}")
    print(f"  coarse kappa: {report['coarse_kappa']:.4f}  (floor {coarse_floor})  -> {'PASS' if report['coarse_pass'] else 'FAIL'}")
    print(f"  emerging rate: {report['emerging_rate']:.4f}  (max {emerging_max})  -> {'PASS' if report['emerging_pass'] else 'FAIL'}")
    print(f"  C+B GATE: {'PASS' if report['cb_gate_pass'] else 'FAIL'}")

    payload = {
        "artifact_id": f"d2884b_decider_ab_{args.arm}",
        "schema_version": "1.0",
        "gen_model": gen_model,
        "pipeline_commit": _git_commit(),
        "decision": "D-2884(b)",
        "arm": args.arm,
        "referee": str(referee_path),
        "anchor": str(anchor_path),
        "macro_scheme": scheme,
        "criteria": criteria,
        "coarse": report,
        "rows": out_rows,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    out_path = Path(args.out) if args.out else (
        REPO / "governance" / f"d2884b_decider_ab_{args.arm}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
    )
    _atomic_write_json(out_path, payload)
    print(f"\n  wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
