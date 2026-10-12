#!/usr/bin/env python3
"""d2767_ab_eval.py — D-2767 full-201 A/B: definition-anchored classifier vs owner gold.

WHAT IT MEASURES (D-2767 / D-2839 gate)
---------------------------------------
The re-derived, owner-adjudicated discipline anchor (D-2820/D-2839 output) is the
referee. The gate is: does the classifier-of-record that `definition_anchored_menu_enabled:
true` WOULD deploy reproduce the owner referee at Cohen's kappa >= 0.800 AND emerging
rate <= 0.35?

BUG-655 CORRECTION (2026-10-06): the prior harness measured the WRONG arm. It called
`run_inference` -> `merged_cribs_classify` with the config flag OFF (free-gen cribs path,
kappa 0.3181), and that number was misread as "non-determinism" when compared against the
redeerive `--generate` definition-anchored candidate (kappa 0.7794). Those two numbers are
the OFF vs ON arms of ONE flag, not two runs of one prompt. THIS harness measures the
flag-ON arm (the definition-anchored closed menu) as the PRIMARY gated arm, using the
SAME production transform (`_apply_definition_anchored_menu`) the flag flip applies —
zero drift. The flag-OFF arm is available via `--baseline` for reference only.

DETERMINISM SELF-CHECK (per BUG-655): before trusting any kappa, the harness re-runs the
flag-ON classification on a small fixed prefix (`--det-check N`) a second time and asserts
byte-identity of the predicted labels. temp=0.0 greedy + D-2637 server settings (grammar
ON, prefix cache ON) + config verifier levers (chat_template_kwargs enable_thinking=false,
thinking_budget) are the once-for-all deterministic configuration; the self-check PROVES it
holds on this run instead of assuming it.

VERDICT IS ADVISORY (D-2798): discipline is not a routing facet, so this script reports
kappa/emerging/deterministic and NEVER fails closed on its own. Flipping
definition_anchored_menu_enabled is the OWNER's human gate (D-2839), not this script's.
Exit 0 on a completed measurement; exit 1 only on load/inference error.

Modes:
  --anchor PATH        override the referee (default: v8 authority 20261007)
  --limit N            run only the first N rows (smoke)
  --baseline           ALSO run the flag-OFF cribs arm (reference only)
  --det-check N        determinism self-check prefix size (default 8)
  --out PATH           R14-stamped JSON output (default governance/d2767_ab_eval_v8_20261010.json)
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
for p in (str(REPO), str(SCRIPTS)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Reuse the production conformance-gate statistics (NO drift): cohen_kappa, load_anchor,
# band, per_class_metrics. run_inference is the flag-OFF arm (baseline only).
from discipline_conformance_gate import (  # noqa: E402
    OPERATIVE_FLOOR,
    REPORTING_FLOOR,
    band,
    cohen_kappa,
    load_anchor,
    per_class_metrics,
    run_inference,
)
# BUG-690 part 1: reuse the 3-way macro ontology (config/discipline_macro_groups.yaml) so the
# harness reports the coarse C+B kappa, NOT only the fine 62-way kappa (D-2767/D-2884 gate).
from discipline_macro_classify import load_macro, to_macro  # noqa: E402

# C12: default referee is the current re-derived authority (v8, D-2866+/D-2879 RATIFIED).
# BUG-650: was the stale v6d manifest; re-pointed to v8 (D-2916). The BUG-689
# noise_drop/abstain handling already makes the 202-row v8 safe (effective N=194).
DEFAULT_ANCHOR = REPO / "governance" / "discipline_anchor_rederived_v8_20261007.json"
DEFAULT_OUT = REPO / "governance" / "d2767_ab_eval_v8_20261010.json"
KAPPA_FLOOR = OPERATIVE_FLOOR  # 0.800 — reported reference (D-2839)
EMERGING_MAX = 0.35  # fallback only; real value read from taxonomy config (C12)


def load_thresholds() -> tuple[float, float, str]:
    """Read kappa floor + emerging max + model from config (C12); fail-closed on missing."""
    import yaml

    cfg_path = REPO / "config" / "pipeline_config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    s4 = cfg.get("stage4", {})
    tax = cfg.get("taxonomy", {})
    kappa_floor = float(s4.get("discipline_conformance_kappa_floor", OPERATIVE_FLOOR))
    emerging_max = float(tax.get("emerging_discipline_rate_max", EMERGING_MAX))
    model = str(s4.get("discipline_model", "gpt-oss-20b-MXFP4-Q8"))
    return kappa_floor, emerging_max, model


def _load_coarse_floor() -> float:
    """Read the C+B coarse-kappa floor (3-way macro) from config (C12); fallback 0.73.

    D-2884/D-2767: the C+B gate is emerging_rate <= 0.35 AND coarse_kappa >=
    discipline_coarse_kappa_floor (re-targeted to the human coarse ceiling, D-2790).
    """
    import yaml

    cfg = yaml.safe_load((REPO / "config" / "pipeline_config.yaml").read_text(encoding="utf-8")) or {}
    s4 = cfg.get("stage4", {})
    return float(s4.get("discipline_coarse_kappa_floor", 0.73))


class WedgeError(RuntimeError):
    """OMLX client wedge: total wall-clock deadline exceeded (BUG-658)."""


def _load_omlx_wall_clock() -> tuple[int, int]:
    """Read total wall-clock deadline + preflight smoke deadline from config (C12).

    BUG-658: the per-read ``read_timeout`` in call_omlx is defeated by OMLX SSE
    keepalive bytes (``sse_keepalive_mode: 'chunk'``), which reset the read timer
    forever. These are hard wall-clock ceilings keepalive cannot reset. Missing
    config falls back to the C12-compliant defaults in pipeline_config.yaml.
    """
    import yaml

    cfg = yaml.safe_load((REPO / "config" / "pipeline_config.yaml").read_text(encoding="utf-8")) or {}
    om = cfg.get("services", {}).get("omlx", {})
    return int(om.get("wall_clock_deadline_sec", 180)), int(om.get("preflight_smoke_deadline_sec", 120))


def _fb_from_example(e: dict) -> dict:
    """Project an anchor row onto the merged-call FB shape (DRY with run_inference_flag_on)."""
    return {
        "name": e["name"],
        "definition": e["definition"],
        "mechanism": e["mechanism"],
        "boundary": e["boundary"],
        "consequence": e.get("consequence", ""),
        "source_text": e.get("source_text", ""),
    }


def _call_omlx_json_with_deadline(
    prompt: str,
    *,
    model: str,
    system: str,
    max_tokens: int,
    deadline_sec: int,
    what: str = "classification",
) -> dict | list:
    """Call call_omlx_json under a total wall-clock deadline (BUG-658).

    call_omlx's per-read timeout (read_timeout) is defeated by OMLX SSE keepalive
    bytes (sse_keepalive_mode: 'chunk'), which reset the read timer forever and
    leave the client silently hung — no exception, so the circuit breaker never
    opens. This wrapper runs the call in a daemon thread and enforces a TOTAL
    deadline that keepalive cannot reset. On expiry it sleeps the recovery window
    and retries ONCE, then fails fast (C16: log AND raise).
    """
    from pipeline.omlx_call import WEDGE_RECOVERY_SLEEP, call_omlx_json

    for attempt in (1, 2):
        result: dict = {}

        def _target() -> None:
            result["value"] = call_omlx_json(prompt, model=model, system=system, max_tokens=max_tokens)

        t = threading.Thread(target=_target, daemon=True, name="omlx-wall-clock")
        t.start()
        t.join(timeout=deadline_sec)
        if t.is_alive():
            if attempt == 1:
                print(
                    f"      🧊  OMLX wall-clock wedge on {what} (>={deadline_sec}s: SSE keepalive "
                    f"defeated read_timeout) — sleeping {WEDGE_RECOVERY_SLEEP}s, ONE retry (BUG-658)",
                    flush=True,
                )
                time.sleep(WEDGE_RECOVERY_SLEEP)
                continue
            raise WedgeError(
                f"OMLX wall-clock deadline ({deadline_sec}s) exceeded twice on {what}: "
                f"SSE keepalive defeated the per-read timeout (BUG-658). Aborting to avoid a silent hang."
            )
        return result.get("value", [])
    raise WedgeError("unreachable deadline state")  # pragma: no cover


def preflight_smoke(examples: list[dict], model: str, deadline_sec: int) -> dict:
    """Fail-closed preflight (BUG-658): prove the model is loaded AND the flag-ON path
    returns parseable JSON BEFORE running the full N-request gate.

    The /v1/models endpoint only proves the server lists a model, not that chat
    completions work (the 'health endpoint lies' failure). One real smoke
    classification through the exact production transform under the wall-clock
    deadline closes that gap; a wedge here aborts before N requests, not after.
    Returns a small stamp for the R14 payload.
    """
    from pipeline.stage4_merged_call import build_merged_prompt

    if not examples:
        raise RuntimeError("preflight smoke: no examples to classify (empty referee)")
    system = _flag_on_system(model)
    max_tokens = _merged_max_tokens()
    t0 = time.time()
    res = _call_omlx_json_with_deadline(
        build_merged_prompt(_fb_from_example(examples[0])),
        model=model,
        system=system,
        max_tokens=max_tokens,
        deadline_sec=deadline_sec,
        what="preflight smoke (examples[0])",
    )
    if isinstance(res, list):
        res = res[0] if res else {}
    ok = isinstance(res, dict) and bool(res.get("discipline"))
    stamp = {
        "passed": ok,
        "elapsed_s": round(time.time() - t0, 2),
        "discipline": res.get("discipline") if isinstance(res, dict) else None,
    }
    if not ok:
        raise RuntimeError(
            f"preflight smoke FAILED: flag-ON path returned no discipline for examples[0] "
            f"(model={model}). Refusing to launch the {len(examples)}-request gate (BUG-658)."
        )
    print(
        f"  ✅ preflight smoke: model loaded + JSON ok "
        f"({stamp['elapsed_s']}s, discipline={stamp['discipline']!r})"
    )
    return stamp


def _git_commit() -> str:
    """Return short git HEAD for the R14 stamp; empty string if unavailable (logged)."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(REPO), capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip()
    except Exception as e:  # C16: log AND continue — stamp is metadata, never gate.
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


def _merged_max_tokens() -> int:
    """Read merged_call_max_tokens from config exactly as merged_cribs_classify does (C12)."""
    from pipeline.pipeline_paths import _CFG

    return int(_CFG.get("stage4", {}).get("merged_call_max_tokens", 512))


def _flag_on_system(model: str) -> str:
    """Build the production flag-ON system prompt (definition-anchored menu), zero drift.

    This is EXACTLY the transform `definition_anchored_menu_enabled: true` applies at import
    time in pipeline/stage4_merged_call.py (line 331: MERGED_CRIBS_CLASSIFY_SYSTEM =
    _apply_definition_anchored_menu(...)), plus the Reasoning:none prefix that
    merged_cribs_classify prepends for reasoning-off models (D2249/BUG-074).
    """
    from pipeline.pipeline_paths import VERIFY_REASONING_OFF_MODELS, VERIFY_REASONING_OFF_PREFIX
    from pipeline.stage4_merged_call import (
        MERGED_CRIBS_CLASSIFY_SYSTEM,
        _apply_definition_anchored_menu,
    )

    system = _apply_definition_anchored_menu(MERGED_CRIBS_CLASSIFY_SYSTEM)
    if model in VERIFY_REASONING_OFF_MODELS and VERIFY_REASONING_OFF_PREFIX:
        system = f"{VERIFY_REASONING_OFF_PREFIX}\n\n{system}"
    return system


def run_inference_flag_on(examples: list[dict], model: str, deadline_sec: int) -> list[str]:
    """Classify each FB on the flag-ON (definition-anchored) path and remap to canonical.

    Mirrors merged_cribs_classify exactly (build_merged_prompt -> system prompt with the
    flag-ON menu -> call_omlx_json) but with the definition-anchored system prompt that the
    flag flip would deploy. This is the arm the D-2839 gate is about.

    BUG-658: each call runs under a total wall-clock deadline (``deadline_sec``) because
    call_omlx's per-read timeout is defeated by OMLX SSE keepalive bytes.
    """
    from pipeline.schemas import get_synonym_index
    from pipeline.stage4_merge import CANONICAL_DISCIPLINES, map_to_canonical_with_fallback
    from pipeline.stage4_merged_call import build_merged_prompt

    synonym_index = get_synonym_index("discipline")
    system = _flag_on_system(model)
    max_tokens = _merged_max_tokens()
    canonical: list[str] = []
    for i, e in enumerate(examples):
        res = _call_omlx_json_with_deadline(
            build_merged_prompt(_fb_from_example(e)),
            model=model,
            system=system,
            max_tokens=max_tokens,
            deadline_sec=deadline_sec,
            what=f"example {e.get('item_id', i)}",
        )
        if isinstance(res, list):
            res = res[0] if res else {}
        raw = res.get("discipline", "") if isinstance(res, dict) else ""
        canonical.append(map_to_canonical_with_fallback(raw, "discipline", synonym_index, CANONICAL_DISCIPLINES))
    return canonical


def determinism_check(examples: list[dict], model: str, pred: list[str], deadline_sec: int) -> dict:
    """Re-run flag-ON classification on the prefix and assert byte-identity (BUG-655).

    Returns {"deterministic": bool, "pass2_match": int, "n": int, "diff_indices": [...]}.
    A mismatch = real serving non-determinism; the kappa must then not be trusted.
    """
    n = len(examples)
    pass2 = run_inference_flag_on(examples, model, deadline_sec)
    diff = [i for i in range(n) if pass2[i] != pred[i]]
    return {
        "deterministic": not diff,
        "pass2_match": n - len(diff),
        "n": n,
        "diff_indices": diff,
    }


def _report(gold: list[str], pred: list[str], kappa_floor: float, emerging_max: float) -> dict:
    """Compute kappa/emerging/per-class and return a payload fragment."""
    n = len(gold)
    kappa = cohen_kappa(gold, pred)
    acc = sum(1 for g, p in zip(gold, pred) if g == p) / n
    emerging_rate = sum(1 for p in pred if p == "emerging") / n
    return {
        "n": n,
        "raw_agreement": round(acc, 4),
        "cohen_kappa": round(kappa, 4),
        "emerging_rate": round(emerging_rate, 4),
        "kappa_pass": bool(kappa >= kappa_floor),
        "emerging_pass": bool(emerging_rate <= emerging_max),
        "per_class": per_class_metrics(gold, pred),
    }


def coarse_collapse(labels: list[str], disc_to_bucket: dict[str, str]) -> list[str]:
    """Collapse fine discipline labels to the 3-way macro bucket (BUG-690 part 1).

    The D-2767 C+B gate (D-2884) needs BOTH the fine 62-way kappa AND the coarse
    3-way macro kappa (config/pipeline_config.yaml#discipline_coarse_kappa_floor).
    Fine -> macro is a pure, deterministic ontology collapse (D-2796:
    config/discipline_macro_groups.yaml). 'emerging' is an explicit routing bucket
    and is never folded into a macro (to_macro maps off-menu/empty to 'emerging').
    """
    return [to_macro(label, disc_to_bucket) for label in labels]


def coarse_report(gold: list[str], pred: list[str], coarse_floor: float) -> dict:
    """Collapse gold+pred to the 3-way macro and compute the coarse C+B kappa.

    Fail-closed (C16): load_macro() raises SystemExit if the macro ontology drifts
    (a group in closed_menu_v8.json without a 3-way bucket — BUG-622 class), so the
    C+B gate can never silently skip the coarse axis.
    """
    scheme, _bucket_members, disc_to_bucket = load_macro()
    cgold = coarse_collapse(gold, disc_to_bucket)
    cpred = coarse_collapse(pred, disc_to_bucket)
    kappa = cohen_kappa(cgold, cpred)
    acc = sum(1 for g, p in zip(cgold, cpred) if g == p) / len(cgold)
    return {
        "scheme": scheme,
        "n": len(cgold),
        "raw_agreement": round(acc, 4),
        "coarse_kappa": round(kappa, 4),
        "coarse_floor": coarse_floor,
        "coarse_pass": bool(kappa >= coarse_floor),
        "per_bucket": per_class_metrics(cgold, cpred),
    }


def _build_rows(examples: list[dict], gold: list[str], pred: list[str]) -> list[dict]:
    """Persist per-row gold/pred/agree so the owner-review CSV and JSON stay reproducible.

    BUG-655 follow-up: the prior harness wrote only summary stats, so the owner-review
    disagreement rows could not be recovered from the output. Persisting rows makes the
    A/B audit self-contained (R14: schema_version, gen_model, pipeline_commit already on
    the parent payload).
    """
    rows: list[dict] = []
    for e, g, p in zip(examples, gold, pred):
        rows.append(
            {
                "item_id": e["item_id"],
                "name": e["name"],
                "gold": g,
                "pred": p,
                "agree": bool(g == p),
                "definition_snippet": (e.get("definition") or "").replace("\n", " ")[:280],
            }
        )
    return rows


def _emit_review_csv(path: Path, rows: list[dict]) -> int:
    """Emit a beginner-friendly owner-review CSV of the disagreement rows (NOT JSON).

    Plain-English `#` comment header + one row per classifier-vs-owner disagreement, with a
    blank "your ruling" column the owner fills in. Returns the disagreement count. Crash-safe
    write (C6) mirrors _atomic_write_json.
    """
    disagreements = [r for r in rows if not r["agree"]]
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["# D-2767 A/B review — these are the rows where the AI classifier disagreed with your label."])
            w.writerow([f"# {len(disagreements)} disagreements out of {len(rows)} anchors."])
            w.writerow(["# How to use: read each row, then write the ONE discipline you want to keep in the last column."])
            w.writerow(["#   'Your label' = what you finalized (the answer key).  'Classifier's label' = what the AI predicted."])
            w.writerow(["#   'Full definition' = the anchor text, so you can re-read it before ruling."])
            w.writerow(["#   'Your ruling' = leave blank until you decide; type a label or 'emerging'."])
            w.writerow([])
            w.writerow(["Row", "FB Name", "Your label", "Classifier's label", "Full definition", "Your ruling (fill in)"])
            for r in disagreements:
                w.writerow(
                    [r["item_id"], r["name"], r["gold"], r["pred"], r["definition_snippet"], ""]
                )
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return len(disagreements)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchor", default=str(DEFAULT_ANCHOR))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--baseline", action="store_true", help="also run the flag-OFF cribs arm (reference)")
    ap.add_argument("--det-check", type=int, default=8, help="determinism self-check prefix size")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    kappa_floor, emerging_max, model = load_thresholds()
    coarse_floor = _load_coarse_floor()
    deadline_sec, preflight_deadline = _load_omlx_wall_clock()
    anchor_path = args.anchor
    out_path = Path(args.out)

    examples = load_anchor(anchor_path)
    # BUG-689 (D-2830/D-2878/D-2880): the v8 referee carries owner-ABSENCE rows the v6 referee
    # never had. `noise_drop` rows (no discipline AND no domains) are OUT OF SCOPE — measuring the
    # classifier on items the owner threw away is meaningless; `abstained` rows have no discipline
    # home but are real in-scope items, whose faithful gold is the referee's OWN declared abstention
    # token (abstention: emerging, D-2830). Both are read from the referee's own discipline_source,
    # never guessed; without this a None/'' gold crashed cohen_kappa (NoneType < str).
    _doc = json.loads(Path(anchor_path).read_text(encoding="utf-8"))
    _drop = {r.get("item_id") for r in _doc.get("rows", []) if r.get("discipline_source") == "noise_drop"}
    _abstain = str(_doc.get("abstention") or "emerging")
    examples = [e for e in examples if e.get("item_id") not in _drop]
    for e in examples:
        if not e.get("discipline"):
            e["discipline"] = _abstain
    print(f"  referee scope: {len(_drop)} noise_drop row(s) EXCLUDED (out of scope), "
          f"{sum(1 for e in examples if e['discipline'] == _abstain)} abstention row(s) -> '{_abstain}' (D-2830)")
    if args.limit is not None:
        examples = examples[: args.limit]

    gold = [e["discipline"] for e in examples]
    n = len(examples)
    print(f"d2767_ab_eval: referee = {anchor_path}")
    print(f"  N = {n}   model = {model}")
    print(f"  gold distinct disciplines = {len(set(gold))}")
    print(f"  gates: kappa >= {kappa_floor}  AND  emerging <= {emerging_max}")
    print(f"  ARM = flag-ON (definition-anchored closed menu) — the D-2839 gate arm")
    print(f"  wall-clock deadline: {deadline_sec}s/call   preflight smoke: {preflight_deadline}s (BUG-658)")

    # Fail-closed preflight (BUG-658): prove the model is loaded + JSON parseable
    # before the N-request gate, under the same wall-clock deadline.
    preflight = preflight_smoke(examples, model, preflight_deadline)

    # Primary arm: flag-ON (definition-anchored).
    pred = run_inference_flag_on(examples, model, deadline_sec)
    result = _report(gold, pred, kappa_floor, emerging_max)
    coarse = coarse_report(gold, pred, coarse_floor)
    rows = _build_rows(examples, gold, pred)

    print(f"\n[flag-ON definition-anchored]")
    print(f"  raw agreement (accuracy): {result['raw_agreement']:.4f}   (reported, NOT gated)")
    print(f"  Cohen's kappa:            {result['cohen_kappa']:.4f}   -> {band(result['cohen_kappa'])}")
    print(f"  emerging rate:            {result['emerging_rate']:.4f}   (gold emerging rows: {sum(1 for g in gold if g == 'emerging')}/{n})")
    print(f"  VERDICT (advisory): kappa_pass={result['kappa_pass']}  emerging_pass={result['emerging_pass']}")

    print(f"\n[coarse 3-way macro C+B gate (BUG-690 part 1)]")
    print(f"  coarse kappa: {coarse['coarse_kappa']:.4f}   (floor {coarse_floor}; D-2796 human ceiling 0.766)")
    print(f"  coarse VERDICT: coarse_pass={coarse['coarse_pass']}")
    cb_pass = bool(result["emerging_pass"] and coarse["coarse_pass"])
    print(f"  C+B GATE (emerging<=0.35 AND coarse>={coarse_floor}): {'PASS' if cb_pass else 'FAIL'}")

    # Determinism self-check (BUG-655): prove the once-for-all settings hold on this run.
    det_n = min(args.det_check, n)
    det = determinism_check(examples[:det_n], model, pred[:det_n], deadline_sec)
    print(f"\n[determinism self-check] {det['pass2_match']}/{det['n']} byte-identical on prefix")
    if not det["deterministic"]:
        print(f"  ⚠️  NON-DETERMINISM DETECTED at indices {det['diff_indices']} — kappa must NOT be trusted", file=sys.stderr)

    payload: dict = {
        "artifact_id": f"d2767_ab_{Path(anchor_path).stem}",
        "schema_version": "1.0",
        "gen_model": model,
        "pipeline_commit": _git_commit(),
        "decision": "D-2767",
        "arm": "flag_ON_definition_anchored",
        "referee": anchor_path,
        "referee_menu_hash": json.loads(Path(anchor_path).read_text(encoding="utf-8")).get("menu_hash", ""),
        "kappa_floor": kappa_floor,
        "emerging_rate_max": emerging_max,
        "deterministic": det["deterministic"],
        "determinism_check": det,
        "preflight": preflight,
        "flag_on": result,
        "coarse_floor": coarse_floor,
        "coarse": coarse,
        "cb_gate_pass": bool(result["emerging_pass"] and coarse["coarse_pass"]),
        "rows": rows,
    }

    # Optional baseline: flag-OFF cribs arm (reference only — NOT the gate).
    if args.baseline:
        base_pred = run_inference(examples, model, 4)
        base = _report(gold, base_pred, kappa_floor, emerging_max)
        payload["baseline_flag_off"] = base
        print(f"\n[flag-OFF cribs baseline — reference only]")
        print(f"  raw agreement: {base['raw_agreement']:.4f}   kappa: {base['cohen_kappa']:.4f}   emerging: {base['emerging_rate']:.4f}")

    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    _atomic_write_json(out_path, payload)
    print(f"\n  wrote {out_path}")

    # Owner-review CSV (NOT JSON): beginner-friendly disagreement sheet for the human gate (D-2839).
    review_csv = out_path.with_name(out_path.stem + "_disagreements.csv")
    n_dis = _emit_review_csv(review_csv, rows)
    print(f"  wrote owner-review CSV: {review_csv}  ({n_dis} disagreements)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
