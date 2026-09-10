#!/usr/bin/env python3
"""scripts/build_p4_training_set.py — D2585 P4 corrected training set.

Applies the P3 challenger corrections (validated by the 3-LF label model,
p_mislabel = 1.0) to a COPY of the golden training YAML so the ModernBERT
classifier can be retrained on label-model-corrected labels.

Correction policy (defensible, documented in the manifest):
  APPLY  a challenger correction when ALL hold:
    (a) the correction target is a CANONICAL discipline (no taxonomy pollution);
    (b) applying it does not push ANY currently-trainable discipline (>=5
        examples) below the MIN_EXAMPLES_PER_CLASS=5 floor — preserving the
        61-way coverage P0 had, so the retrain A/B (ΔF1 vs silver labels)
        compares like-for-like;
  DEFER  otherwise (logged to the manifest for the P5 human-GOLD freeze).

Discipline-only correction scope: domains/depth keep the teacher silver labels
(sigmoid multi-label + 4-way depth correction is a separate step; the P3 depth
signal is known-biased, D2576).

Read-only w.r.t. the DB and the ORIGINAL golden YAML (writes a _p4 copy).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import yaml  # noqa: E402

from pipeline.schemas import CANONICAL_DISCIPLINES  # noqa: E402

_GOLDEN_YAML = _ROOT / "config" / "golden" / "stage4_golden_mined.yaml"
_OUT_YAML = _ROOT / "config" / "golden" / "stage4_golden_mined_p4.yaml"
_LABEL_MODEL_JSONL = _ROOT / "temp" / "golden_labels_probabilistic.jsonl"
_MANIFEST_JSON = _ROOT / "temp" / "p4_corrections_manifest.json"
_MANIFEST_MD = _ROOT / "governance" / "p4_corrections_manifest.md"

_MIN_EXAMPLES_PER_CLASS = 5  # must mirror train_discipline_classifier.py


def main() -> int:
    doc = yaml.safe_load(_GOLDEN_YAML.read_text(encoding="utf-8")) or {}
    examples: list[dict] = doc.get("examples", [])
    if not examples:
        print("no examples in golden YAML", file=sys.stderr)
        return 1

    # example_id -> label-model row (has challenger_correction + p_mislabel).
    lm: dict[str, dict] = {}
    for line in _LABEL_MODEL_JSONL.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        lm[r["example_id"]] = r

    canonical = set(CANONICAL_DISCIPLINES)
    by_id = {e.get("id"): e for e in examples if isinstance(e, dict)}
    current = Counter(
        (e.get("expected_classification") or {}).get("discipline") for e in examples
    )
    counts = Counter(current)  # mutable working copy

    def discipline_of(ex: dict) -> str:
        return (ex.get("expected_classification") or {}).get("discipline", "")

    def would_endanger(src: str, dst: str) -> bool:
        """True if applying this correction drops a >=5 class below the floor."""
        if counts[src] >= _MIN_EXAMPLES_PER_CLASS and counts[src] - 1 < _MIN_EXAMPLES_PER_CLASS:
            return True
        # dst growing can only help dst; only src loss endangers. (dst <5 but
        # >0 stays below either way; dst == 0 becomes a singleton -> filtered.)
        return False

    applied: list[dict] = []
    deferred: list[dict] = []

    # Deterministic order: by example id so reruns are stable.
    corrections = sorted(
        ((eid, lm[eid]["challenger_correction"]) for eid, row in lm.items()
         if row.get("challenger_correction")),
        key=lambda t: t[0],
    )
    for eid, new_disc in corrections:
        ex = by_id.get(eid)
        if ex is None:
            deferred.append({"example_id": eid, "reason": "example not in golden YAML"})
            continue
        old_disc = discipline_of(ex)
        if new_disc not in canonical:
            deferred.append({
                "example_id": eid, "old": old_disc, "proposed": new_disc,
                "reason": "non-canonical discipline",
            })
            continue
        if would_endanger(old_disc, new_disc):
            deferred.append({
                "example_id": eid, "old": old_disc, "proposed": new_disc,
                "reason": "would drop source class below MIN_EXAMPLES_PER_CLASS",
            })
            continue
        # Apply: patch expected_classification.discipline only.
        (ex["expected_classification"])["discipline"] = new_disc
        counts[old_disc] -= 1
        counts[new_disc] += 1
        applied.append({
            "example_id": eid,
            "old_discipline": old_disc,
            "new_discipline": new_disc,
            "p_mislabel": lm[eid]["p_mislabel"],
            "lf_votes": lm[eid]["lf_votes"],
            "tier": lm[eid]["tier"],
        })

    # Guard: no currently-trainable class may fall below the floor after all edits.
    dropped_classes = sorted(
        d for d, c in counts.items() if c and c < _MIN_EXAMPLES_PER_CLASS
    )
    # Meta note: provenance on the corrected copy (never touch the original).
    meta = dict(doc.get("meta") or {})
    meta["note"] = (
        "P4 label-model-corrected COPY (D2585 P4). Source: stage4_golden_mined.yaml + "
        f"3-LF Dawid-Skene label model v2. {len(applied)} challenger corrections "
        f"applied (p_mislabel=1.0), {len(deferred)} deferred to P5 human GOLD. "
        "Discipline-only; domains/depth unchanged (teacher silver). "
        "Original silver file is the P5 source of truth."
    )
    meta["total_examples"] = len(examples)
    meta["p4_applied_corrections"] = len(applied)
    meta["p4_deferred_corrections"] = len(deferred)
    doc["meta"] = meta
    doc["examples"] = examples

    _OUT_YAML.write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    manifest = {
        "applied": applied,
        "deferred": deferred,
        "classes_after": dict(sorted(counts.items())),
        "n_applied": len(applied),
        "n_deferred": len(deferred),
        "classes_below_floor_after": dropped_classes,
        "note": (
            "applied = challenger 2/3-majority canonical correction kept (class "
            "floor preserved); deferred = routed to P5 human GOLD."
        ),
    }
    _MANIFEST_JSON.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    _MANIFEST_MD.write_text(
        "\n".join([
            "# P4 CORRECTION MANIFEST (D2585 P4)",
            "",
            f"**{len(applied)} corrections applied** to "
            "`config/golden/stage4_golden_mined_p4.yaml` "
            f"| **{len(deferred)} deferred** to P5 human GOLD.",
            "",
            "| example_id | old | new | p_mislabel |",
            "|---|---|---|---|",
            *[
                f"| {a['example_id']} | {a['old_discipline']} | {a['new_discipline']} "
                f"| {a['p_mislabel']} |"
                for a in applied
            ],
            "",
            "## Deferred (P5 human GOLD)",
            "",
            *[
                f"- `{d['example_id']}` {d.get('old','')} → {d.get('proposed','')} "
                f"({d['reason']})"
                for d in deferred
            ],
            "",
            f"Classes below floor after: {dropped_classes or 'none'}",
            "",
        ]),
        encoding="utf-8",
    )
    print(json.dumps({
        "n_applied": len(applied), "n_deferred": len(deferred),
        "deferred": deferred, "classes_below_floor_after": dropped_classes,
        "out": str(_OUT_YAML),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
