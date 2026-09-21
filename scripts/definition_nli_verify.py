#!/usr/bin/env python3
"""scripts/definition_nli_verify.py — R2 definition-anchored NLI (D-281/D-284).

Verifies a proposed label against a hypothesis, with the R5 repaired definitions
(config/r5_slot_repair.yaml) taking precedence for the weak slots. This is the R2
guardrail: instead of a flat "This text is about {label}." hypothesis (which
under-entails on broad labels — D2571 anomaly-C), the hypothesis is anchored.

D-284 (arm C, 2026-09-20): for the CONTENT_TYPE axis the hypothesis is a
PARAPHRASE content-claim (from config/content_types.yaml `nli_paraphrase`), NOT
the category meta-definition — BUG-305 proved the meta-definition under-entails
on principle. discipline/domains keep the DEFINITION hypothesis (D-281).

For each FB and each proposed label (discipline + domains + content_type), run
DeBERTa/ModernBERT NLI with:
    premise    = FB definition (truncated to S5_NLI_MAX_PREMISE_CHARS)
    hypothesis = paraphrase content-claim (content_type) | menu/r5 definition (discipline/domains)

`contra` (contradiction) is a HARD mislabel signal; `neutral`/low-entail is a
WEAK signal. This is Mechanism B (a meter) per D-277: it calibrates confidence
and triggers human review / abstention — it NEVER flips a label by itself.

Read-only w.r.t. the DB. Writes a JSON report (crash-safe, C6).

Modes:
    --selfcheck      load menu + r5 definitions, print coverage, NO NLI inference
    (default)        run NLI over the input FBs (stage5 checkpoint by default)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import yaml  # noqa: E402

from pipeline.closed_menu import menu_hash, render_closed_menu  # noqa: E402
from pipeline.io_guard import safe_write  # noqa: E402
from pipeline.pipeline_paths import S5_NLI_MAX_PREMISE_CHARS, STAGE5_CHECKPOINT  # noqa: E402

_R5_REPAIR_PATH = _ROOT / "config" / "r5_slot_repair.yaml"
_DEFAULT_OUT = _ROOT / "governance" / "r2_definition_nli_20260920.json"
# D282 (2026-09-20): the "contradiction-dominant" flag threshold is a separate
# heuristic from the S5 entail-pass threshold. Do NOT reuse S5_NLI_PASS_THRESHOLD
# here — entail-pass and contra-dominance are semantically distinct decisions.
_CONTRA_DOMINANT_THRESHOLD = 0.5


def _load_r5_definitions() -> dict[str, dict[str, str]]:
    """Return {label: definition} for re-derived slots (content_type + discipline).

    The r5 override is the repaired definition, which supersedes taxonomy_v5.yaml
    for the weak slots while the repair is BOUND (human review on write).
    """
    if not _R5_REPAIR_PATH.exists():
        return {}
    doc = yaml.safe_load(open(_R5_REPAIR_PATH, encoding="utf-8")) or {}
    out: dict[str, dict[str, str]] = {}
    for section in ("content_type", "discipline"):
        out[section] = {}
        for label, entry in (doc.get(section) or {}).items():
            if isinstance(entry, dict) and entry.get("definition"):
                out[section][label] = entry["definition"].strip()
    return out


def _r5_hash() -> str | None:
    """sha256 of the FULL r5 override set (content_type + discipline, all fields).

    The r5 overrides change verification behaviour but were previously unstamped
    (BUG-307): an FB verified under the D-283 sharpened definitions was
    indistinguishable, by provenance, from one verified pre-sharpening. This hash
    (alongside menu_hash) makes a label's R2 verification traceable to the EXACT
    override set that produced its hypotheses.
    """
    if not _R5_REPAIR_PATH.exists():
        return None
    doc = yaml.safe_load(open(_R5_REPAIR_PATH, encoding="utf-8")) or {}
    subset = {k: doc.get(k) for k in ("content_type", "discipline") if k in doc}
    canonical = json.dumps(subset, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _menu_definition(menu: dict, axis: str, label: str) -> str | None:
    axis_key = "content_types" if axis == "content_type" else ("disciplines" if axis == "discipline" else "domains")
    for e in menu.get(axis_key, []):
        if e.get("value") == label:
            return (e.get("definition") or e.get("description") or "").strip() or None
    return None


def _definition_for(menu: dict, r5: dict[str, dict[str, str]], axis: str, label: str) -> str | None:
    """Resolve the definition for a label: r5 override → menu (taxonomy) definition."""
    if not label or label in ("emerging", "none"):
        return None
    override = r5.get(axis, {}).get(label)
    if override:
        return override
    return _menu_definition(menu, axis, label)


def _load_nli_paraphrase() -> dict[str, str]:
    """Load the per-role NLI paraphrase content-claims (D-284 arm C) from config."""
    ct_path = _ROOT / "config" / "content_types.yaml"
    doc = yaml.safe_load(open(ct_path, encoding="utf-8")) or {}
    return {k: str(v).strip() for k, v in (doc.get("nli_paraphrase") or {}).items()}


def _hypothesis_for(menu: dict, r5: dict[str, dict[str, str]], para: dict[str, str],
                    axis: str, label: str) -> tuple[str | None, str | None]:
    """Return (hypothesis_text, hypothesis_type) for a label.

    D-284 (arm C): content_type uses the paraphrase content-claim (NOT the meta-
    definition). discipline/domains keep the definition hypothesis (D-281).
    """
    if axis == "content_type":
        hyp = para.get(label)
        return (hyp, "paraphrase") if hyp else (None, None)
    hyp = _definition_for(menu, r5, axis, label)
    return (hyp, "definition") if hyp else (None, None)


def _iter_fbs(path: Path, limit: int | None):
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            if limit is not None and i >= limit:
                break
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                print(f"  ⚠️  skip malformed line {i}: {e}", file=sys.stderr)
                continue


def _parse_domains(raw) -> list[str]:
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if not raw:
        return []
    s = str(raw).strip()
    if s.startswith("["):
        try:
            return [str(x).strip() for x in json.loads(s) if str(x).strip()]
        except (json.JSONDecodeError, TypeError):
            pass
    return [x.strip() for x in s.split("|") if x.strip()]


def selfcheck(menu: dict, r5: dict[str, dict[str, str]]) -> int:
    """Load everything and print coverage — proves the script parses without NLI."""
    print("menu:", {k: len(v) for k, v in menu.items() if isinstance(v, list)})
    print(f"r5 overrides: content_type={len(r5.get('content_type', {}))} "
          f"discipline={len(r5.get('discipline', {}))}")
    # every re-derived discipline must resolve to a definition (override or menu)
    missing = [lbl for lbl in r5.get("discipline", {}) if lbl not in {e["value"] for e in menu["disciplines"]}]
    if missing:
        print(f"⚠️  r5 discipline slots missing from the closed menu: {missing}", file=sys.stderr)
    for axis in ("content_type", "discipline"):
        for label, defn in r5.get(axis, {}).items():
            print(f"  [{axis}] {label}: {'✓' if defn else '✗'} definition "
                  f"({len(defn.split()) if defn else 0} words)")
    return 0


def run(menu: dict, r5: dict[str, dict[str, str]], para: dict[str, str],
        path: Path, limit: int | None, out: Path) -> int:
    from pipeline.stage5_verify import NLIInferenceError, _nli_pair_scores  # noqa: E402

    results: list[dict] = []
    n_labels = 0
    n_contra = 0
    n_errors = 0

    def _score(premise: str, hypothesis: str) -> dict | None:
        try:
            entail, neutral, contra = _nli_pair_scores(premise, hypothesis, raise_on_error=True)
            return {"entail": round(float(entail), 4), "neutral": round(float(neutral), 4), "contra": round(float(contra), 4)}
        except NLIInferenceError as e:
            return {"error": str(e)}

    for fb in _iter_fbs(path, limit):
        fb_id = fb.get("fb_id") or fb.get("name", "?")
        premise = (fb.get("definition") or "")[:S5_NLI_MAX_PREMISE_CHARS]
        if not premise:
            continue
        labels: list[tuple[str, str]] = []
        labels.append(("discipline", str(fb.get("discipline") or "")))
        for d in _parse_domains(fb.get("domains")):
            labels.append(("domains", d))
        labels.append(("content_type", str(fb.get("content_type") or "")))

        row = {"fb_id": fb_id, "name": fb.get("name", ""), "labels": []}
        for axis, label in labels:
            if not label or label in ("emerging", "none"):
                continue
            hyp, htype = _hypothesis_for(menu, r5, para, axis, label)
            if not hyp:
                continue
            n_labels += 1
            sc = _score(premise, hyp)
            if sc and "contra" in sc:
                contra = float(sc["contra"])
                if contra >= _CONTRA_DOMINANT_THRESHOLD:
                    n_contra += 1
            elif sc and "error" in sc:
                n_errors += 1
            row["labels"].append({"axis": axis, "label": label, "hypothesis_type": htype,
                                  "hypothesis": hyp, "scores": sc})
        results.append(row)

    report = {
        "schema_version": "1.0",
        "decision": "D-281/D-284",
        "content_type_hypothesis": "paraphrase",
        "menu_hash": menu_hash(menu),
        "r5_hash": _r5_hash(),
        "n_fbs": len(results),
        "n_labels_scored": n_labels,
        "n_contra": n_contra,
        "n_inference_errors": n_errors,
        "results": results,
    }
    safe_write(out, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"✅ R2 definition NLI: {len(results)} FBs, {n_labels} label-definition pairs scored, "
          f"{n_contra} contra, {n_errors} inference errors")
    print(f"   menu_hash={report['menu_hash'][:16]}… r5_hash={report['r5_hash'][:16] if report['r5_hash'] else None}")
    print(f"   -> {out}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="R2 definition-anchored NLI (D-281).")
    ap.add_argument("--input", default=str(STAGE5_CHECKPOINT), help="JSONL of FB dicts")
    ap.add_argument("--limit", type=int, default=None, help="max FBs to verify")
    ap.add_argument("--output", default=str(_DEFAULT_OUT))
    ap.add_argument("--selfcheck", action="store_true", help="load defs only, no NLI inference")
    args = ap.parse_args()

    menu = render_closed_menu()
    r5 = _load_r5_definitions()
    para = _load_nli_paraphrase()

    if args.selfcheck:
        print(f"nli_paraphrase: {len(para)} roles loaded (arm C)")
        return selfcheck(menu, r5)

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"❌ input not found: {in_path} (run stage5 first, or pass --input)", file=sys.stderr)
        return 1
    return run(menu, r5, para, in_path, args.limit, Path(args.output))


if __name__ == "__main__":
    raise SystemExit(main())
