#!/usr/bin/env python3
"""pipeline/nli_definition_control.py — D2571 definition-bearing NLI control.

Resolves the anomaly-C question: is the near-zero `mean_entail` on catch-all
labels a MEASUREMENT confound (the flat template "This text is about {label}."
under-entails on loose topic-membership) or a REAL mislabel signal?

For a sample of FBs it runs the SAME DeBERTa NLI pair TWICE:
  premise        = FB definition (truncated, identical to nli_label_audit.py)
  hypothesis_flat = "This text is about {label}."
  hypothesis_def  = the canonical `definition` from taxonomy_v5.yaml (D2570/P1)

If hypothesis_def systematically yields HIGHER entail than hypothesis_flat on
broad/catch-all labels, the flat template is the confound (anomaly C) and the
per-label rates in `taxonomy.semantic_error_rate_max.per_label` must be
re-derived with definition-bearing hypotheses before D2547 cost-weighting.

Read-only w.r.t. the DB. Writes `governance/nli_definition_control.json`.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import yaml  # noqa: E402

from pipeline.io_guard import safe_write  # noqa: E402
from pipeline.pipeline_paths import (  # noqa: E402
    DB_PATH,
    S5_NLI_MAX_PREMISE_CHARS,
    S5_NLI_PASS_THRESHOLD,
)
from pipeline.stage5_verify import NLIInferenceError, _nli_pair_scores  # noqa: E402

_TAXONOMY_PATH = _ROOT / "config" / "taxonomy_v5.yaml"
_JSON_FILE = _ROOT / "governance" / "nli_definition_control.json"
_FLAT_TEMPLATE = "This text is about {label}."
_DEFAULT_SAMPLE = 500  # C20: sample size (2 NLI pairs each -> 2*N inferences)


def _load_definitions() -> dict[str, str]:
    tax = yaml.safe_load(open(_TAXONOMY_PATH, encoding="utf-8"))
    out: dict[str, str] = {}
    for section in ("domains", "disciplines"):
        for e in tax.get(section, []):
            if e.get("definition"):
                out[e["canonical"]] = e["definition"].strip()
    return out


def _iter_fbs(conn: sqlite3.Connection, n: int):
    """Yield (fb_id, definition, discipline, domains_json) for a random sample."""
    cur = conn.execute(
        "SELECT fb_id, definition, discipline, domains FROM fbs "
        "WHERE definition IS NOT NULL AND definition != '' "
        "ORDER BY RANDOM() LIMIT ?",
        (n,),
    )
    for row in cur.fetchall():
        yield row[0], row[1], row[2], row[3]


def _parse_domains(raw: str | None) -> list[str]:
    if not raw:
        return []
    s = raw.strip()
    if s.startswith("["):
        try:
            return [str(x).strip() for x in json.loads(s) if str(x).strip()]
        except (json.JSONDecodeError, TypeError):
            pass
    return [x.strip() for x in s.split("|") if x.strip()]


def _score(premise: str, hypothesis: str) -> float | None:
    try:
        entail, _neutral, _contra = _nli_pair_scores(premise, hypothesis, raise_on_error=True)
        return round(entail, 4)
    except NLIInferenceError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Definition-bearing NLI control (D2571).")
    ap.add_argument("--db", default=str(DB_PATH))
    ap.add_argument("--sample", type=int, default=_DEFAULT_SAMPLE)
    args = ap.parse_args()

    defs = _load_definitions()
    print(f"loaded {len(defs)} canonical definitions", file=sys.stderr)

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    flat_entails: list[float] = []
    def_entails: list[float] = []
    per_label: dict[str, dict[str, list[float]]] = {}
    rows: list[dict] = []
    n_pairs = 0
    n_errors = 0

    for fb_id, fb_def, discipline, domains_json in _iter_fbs(conn, args.sample):
        premise = fb_def[:S5_NLI_MAX_PREMISE_CHARS]
        labels = [discipline] + _parse_domains(domains_json)
        for label in labels:
            if not label or label == "emerging":
                continue
            flat_hyp = _FLAT_TEMPLATE.format(label=label)
            def_hyp = defs.get(label)
            flat = _score(premise, flat_hyp)
            deft = _score(premise, def_hyp) if def_hyp else None
            n_pairs += 1
            if flat is not None:
                flat_entails.append(flat)
            else:
                n_errors += 1
            if deft is not None:
                def_entails.append(deft)
            else:
                n_errors += 1
            pl = per_label.setdefault(label, {"flat": [], "def": []})
            if flat is not None:
                pl["flat"].append(flat)
            if deft is not None:
                pl["def"].append(deft)
            rows.append({"fb_id": fb_id, "label": label,
                         "flat_entail": flat, "def_entail": deft})

    conn.close()

    def _mean(xs: list[float]) -> float | None:
        return round(sum(xs) / len(xs), 4) if xs else None

    summary = {
        "n_fbs_sampled": args.sample,
        "n_pairs": n_pairs,
        "n_errors": n_errors,
        "flat_mean_entail": _mean(flat_entails),
        "def_mean_entail": _mean(def_entails),
        "flat_pass_rate": round(sum(1 for e in flat_entails if e >= S5_NLI_PASS_THRESHOLD) / len(flat_entails), 4) if flat_entails else None,
        "def_pass_rate": round(sum(1 for e in def_entails if e >= S5_NLI_PASS_THRESHOLD) / len(def_entails), 4) if def_entails else None,
    }
    top = sorted(
        per_label.items(),
        key=lambda kv: _mean(kv[1]["flat"]) if kv[1]["flat"] else 1.0,
    )[:20]
    per_label_out = [
        {"label": lbl, "n": len(v["flat"]), "flat_mean": _mean(v["flat"]),
         "def_mean": _mean(v["def"])}
        for lbl, v in top
    ]

    safe_write(_JSON_FILE, json.dumps(
        {"summary": summary, "per_label_top": per_label_out, "rows": rows},
        indent=2, ensure_ascii=False) + "\n")

    print(f"=== DEF-BEARING NLI CONTROL (sample {args.sample}) ===")
    print(f"flat  mean entail {summary['flat_mean_entail']} | pass rate {summary['flat_pass_rate']}")
    print(f"def   mean entail {summary['def_mean_entail']} | pass rate {summary['def_pass_rate']}")
    print(f"n_pairs={n_pairs} n_errors={n_errors}")
    print("--- lowest flat-entail labels (flat vs def) ---")
    for r in per_label_out[:12]:
        print(f"  {r['label']:<28} n={r['n']:<4} flat={r['flat_mean']}  def={r['def_mean']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
