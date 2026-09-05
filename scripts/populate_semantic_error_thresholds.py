#!/usr/bin/env python3
"""scripts/populate_semantic_error_thresholds.py — D2547 per-label threshold population.

Populates `config/pipeline_config.yaml` → `taxonomy.semantic_error_rate_max.per_label`
with the EMPIRICAL per-label mislabel rate derived from the D2547 calibration
(`governance/d2547_calibration.json`) and the current corpus counts.

Formula (data-driven baseline; cost-weighting is a separate future policy):
    error_rate(label) = nli_contradict(label) / nli_total(label)

  * `nli_contradict` = contradiction-dominant pairs (contra > entail AND neutral),
    the direct "definition contradicts label" mislabel signal (P0 #1 split).
  * `nli_total` = full audited population for the label (P0 #2), NOT the flagged
    subset — so this is a full-population contradiction rate, not a flag-rate proxy.

  * discipline axis (61 canonical labels, single-valued):
        flagged = calibration[(discipline, L)].nli_flagged
        total   = count(FBs WHERE discipline = L)
  * domain axis (43 canonical labels, multi-valued):
        flagged = Σ over calibration domain-entries whose pipe-joined label-set
                  contains D, of (nli_flagged / |label-set|)   [even split]
        total   = count(FBs WHERE D ∈ domains)

NOTE: the rate is now the FULL-POPULATION contradiction rate (nli_contradict /
nli_total), not the conflated contradiction+weak flag rate. Weak-entailment pairs
are excluded from this numerator (they are a separate signal, see nli_weak).
Cost-weighting + ground-truth calibration remain future work (D2547).

Surgical write: ONLY the `    per_label: {}` line under `semantic_error_rate_max`
is replaced (comments and all other config preserved). The value is the observed
error rate (not a policy threshold) — the gate consumer applies cost-weighting.

Run:
    python3 scripts/populate_semantic_error_thresholds.py            # dry-run
    python3 scripts/populate_semantic_error_thresholds.py --apply    # write config
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import yaml  # noqa: E402

from pipeline.pipeline_paths import DB_PATH  # noqa: E402

_CALIBRATION = _ROOT / "governance" / "d2547_calibration.json"
_TAXONOMY = _ROOT / "config" / "taxonomy_v5.yaml"
_CFG = _ROOT / "config" / "pipeline_config.yaml"

# C20: match the whole `per_label:` block (key line + indented entries), so the
# script is idempotent — it replaces either the empty `{}` marker OR a previously
# populated block of label entries.
_PER_LABEL_BLOCK_RE = re.compile(r"    per_label:[^\n]*\n(?:      [^\n]*\n)*")
_ROUND_DIGITS = 4                        # C20: output precision
_COMBO_SEP = "|"                         # C20: calibration pipe-joins domain sets
_DEFAULT_MIN_SAMPLE = 10                 # C20: fallback if config omits the threshold


def _min_sample() -> int:
    """Minimum corpus size for a label to get a per-label rate (from config)."""
    cfg = yaml.safe_load(open(_CFG, encoding="utf-8"))
    return int((cfg.get("taxonomy") or {}).get("emerging_freq_threshold", _DEFAULT_MIN_SAMPLE))


def _parse_domains(raw: str | None) -> list[str]:
    if not raw:
        return []
    s = raw.strip()
    if s.startswith("["):
        try:
            return [str(x).strip() for x in json.loads(s) if str(x).strip()]
        except (json.JSONDecodeError, TypeError):
            return []
    return [x.strip() for x in s.split(_COMBO_SEP) if x.strip()]


def _load_totals() -> tuple[dict[str, int], dict[str, int]]:
    """Return (discipline_total, domain_total) from the live DB."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        disc: dict[str, int] = {}
        for (label, n) in conn.execute(
            "SELECT discipline, COUNT(*) FROM fbs WHERE discipline IS NOT NULL AND discipline != '' GROUP BY discipline"
        ):
            disc[label] = n
        dom: dict[str, int] = {}
        for (raw,) in conn.execute("SELECT domains FROM fbs"):
            for d in _parse_domains(raw):
                dom[d] = dom.get(d, 0) + 1
    finally:
        conn.close()
    return disc, dom


def _compute_per_label() -> dict[str, float]:
    cal = json.loads(_CALIBRATION.read_text(encoding="utf-8"))
    tax = yaml.safe_load(open(_TAXONOMY, encoding="utf-8"))
    canon_dom = {d["canonical"] for d in tax["domains"]}
    canon_disc = {d["canonical"] for d in tax["disciplines"]}

    disc_total, dom_total = _load_totals()

    # discipline: clean 1:1 (label == canonical)
    disc_flagged: dict[str, int] = {}
    # domain: aggregate combo entries by even split
    dom_flagged: dict[str, float] = {}
    for rec in cal.get("labels", []):
        axis, label = rec["axis"], rec["label"]
        # NLI contradiction count (P0 #1 split) = the more direct "definition
        # contradicts label" mislabel signal (vs k-NN agreement, which tracks
        # topical diversity). Weak-entailment is deliberately NOT folded in here.
        flagged = int(rec.get("nli_contradict") or 0)
        if axis == "discipline" and label in canon_disc:
            disc_flagged[label] = disc_flagged.get(label, 0) + flagged
        elif axis == "domain":
            parts = [p for p in label.split(_COMBO_SEP) if p in canon_dom]
            if parts:
                share = flagged / len(parts)
                for p in parts:
                    dom_flagged[p] = dom_flagged.get(p, 0.0) + share

    min_sample = _min_sample()
    out: dict[str, float] = {}
    for label in sorted(canon_disc):
        total = disc_total.get(label, 0)
        if total >= min_sample:
            out[label] = round(disc_flagged.get(label, 0) / total, _ROUND_DIGITS)
    for label in sorted(canon_dom):
        total = dom_total.get(label, 0)
        if total >= min_sample:
            out[label] = round(dom_flagged.get(label, 0.0) / total, _ROUND_DIGITS)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Write config (default = dry-run).")
    args = ap.parse_args()

    per_label = _compute_per_label()
    print(f"computed per-label error rates for {len(per_label)} canonical labels\n")

    # show the extremes for a sanity check
    items = sorted(per_label.items(), key=lambda kv: -kv[1])
    print("top 10 (highest observed error rate):")
    for k, v in items[:10]:
        print(f"  {v:.4f}  {k}")
    print("bottom 5 (lowest):")
    for k, v in items[-5:]:
        print(f"  {v:.4f}  {k}")

    # build the replacement YAML block (indented under the taxonomy key)
    block_lines = ["    per_label:"]
    for k, v in per_label.items():
        block_lines.append(f"      {k}: {v}")
    replacement = "\n".join(block_lines)

    cfg_text = _CFG.read_text(encoding="utf-8")
    if not _PER_LABEL_BLOCK_RE.search(cfg_text):
        print(f"❌ per_label block not found in {_CFG}")
        return 1
    # Replace the whole block (empty marker or prior populated entries) idempotently.
    new_text = _PER_LABEL_BLOCK_RE.sub(replacement + "\n", cfg_text, count=1)

    if not args.apply:
        print(f"\n(dry-run — would replace the per_label block with {len(per_label)} entries)")
        print("preview of first lines:")
        print(replacement[:400])
        return 0

    _CFG.write_text(new_text, encoding="utf-8")
    # round-trip validate the written YAML still parses
    yaml.safe_load(open(_CFG, encoding="utf-8"))
    print(f"\n✅ populated {len(per_label)} per-label thresholds → {_CFG.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
