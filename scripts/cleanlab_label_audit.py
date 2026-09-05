#!/usr/bin/env python3
"""scripts/cleanlab_label_audit.py — D2571 Confident Learning label-noise audit.

Third independent mislabel instrument (alongside k-NN topical-coherence and
T-NLI entailment). Uses cleanlab's Confident Learning (Northcutt et al., JAIR
2021) on the DISCIPLINE axis: TF-IDF features of the FB `definition`, a
cross-validated LogisticRegression to get out-of-sample predicted probabilities
(psx), then `cleanlab.filter.find_label_issues` to flag likely mislabels.

Why a third instrument: k-NN measures topical neighbourhood coherence (not
correctness) and T-NLI measures definition-label entailment (under-entails on
broad labels). Confident Learning is a principled, calibrated label-noise
estimator that needs neither neighbour agreement nor NLI — it flags labels the
classifier itself is confidently *against*.

Read-only w.r.t. the DB. Writes `governance/cleanlab_label_audit.json` + `.md`.
Requires: cleanlab, scikit-learn (framework Python).
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import numpy as np  # noqa: E402
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.model_selection import cross_val_predict  # noqa: E402
from sklearn.preprocessing import LabelEncoder  # noqa: E402

from cleanlab.filter import find_label_issues  # noqa: E402

from pipeline.io_guard import safe_write  # noqa: E402
from pipeline.pipeline_paths import DB_PATH  # noqa: E402

_JSON_FILE = _ROOT / "governance" / "cleanlab_label_audit.json"
_MD_FILE = _ROOT / "governance" / "cleanlab_label_audit.md"

_CV_FOLDS = 5                # C20: cross-validation folds for out-of-sample psx
_MIN_SAMPLES = 5             # C20: ignore labels with fewer samples than this
_MD_TOP_N = 30               # C20: surfaced flagged rows in the report
_RANDOM_STATE = 42           # C20: reproducibility


def _load_fbs(conn: sqlite3.Connection) -> tuple[list[str], list[str], list[str]]:
    """Return (fb_ids, definitions, disciplines) for non-emerging, non-empty FBs."""
    rows = conn.execute(
        "SELECT fb_id, definition, discipline FROM fbs "
        "WHERE definition IS NOT NULL AND definition != '' "
        "AND discipline IS NOT NULL AND discipline != '' AND discipline != 'emerging'"
    ).fetchall()
    return [r[0] for r in rows], [r[1] for r in rows], [r[2] for r in rows]


def main() -> int:
    ap = argparse.ArgumentParser(description="Confident Learning label-noise audit (D2571).")
    ap.add_argument("--db", default=str(DB_PATH))
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    fb_ids, defs, disciplines = _load_fbs(conn)
    conn.close()

    labels = np.asarray(disciplines)
    print(f"loaded {len(fb_ids)} FBs across {len(set(disciplines))} disciplines", file=sys.stderr)

    # cleanlab requires zero-indexed integer labels; encode + remember the mapping.
    enc = LabelEncoder()
    labels_int = enc.fit_transform(labels)
    class_names = enc.classes_

    # TF-IDF features + cross-validated predicted probabilities (out-of-sample).
    X = TfidfVectorizer(max_features=20000, ngram_range=(1, 2)).fit_transform(defs)
    clf = LogisticRegression(max_iter=1000, random_state=_RANDOM_STATE, n_jobs=-1)
    psx = cross_val_predict(clf, X, labels_int, method="predict_proba",
                            cv=_CV_FOLDS, n_jobs=-1)

    issues = find_label_issues(labels_int, psx, return_indices_ranked_by="self_confidence")

    # collapse to per-FB flags, dropping labels under MIN_SAMPLES from the report
    label_counts: dict[str, int] = {}
    for lbl in labels:
        label_counts[lbl] = label_counts.get(lbl, 0) + 1

    flagged = [fb_ids[i] for i in issues if label_counts.get(labels[i], 0) >= _MIN_SAMPLES]

    summary = {
        "n_fbs": len(fb_ids),
        "n_labels": len(set(disciplines)),
        "n_flagged": int(len(issues)),
        "n_flagged_report": len(flagged),
        "pct_flagged": round(len(issues) / len(fb_ids), 4) if fb_ids else None,
        "method": "TF-IDF + CV-LogisticRegression -> cleanlab Confident Learning",
        "cv_folds": _CV_FOLDS,
    }

    per_label: dict[str, int] = {}
    for i in issues:
        lbl = labels[i]
        per_label[lbl] = per_label.get(lbl, 0) + 1
    top = sorted(per_label.items(), key=lambda kv: kv[1], reverse=True)[:15]

    safe_write(_JSON_FILE, json.dumps(
        {"summary": summary, "flagged_fb_ids": flagged,
         "per_label_top": [{"label": k, "n": v} for k, v in top]},
        indent=2, ensure_ascii=False) + "\n")

    md_lines = [
        "# CLEANLAB LABEL AUDIT — Confident Learning (D2571)",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| FBs audited | {summary['n_fbs']} |",
        f"| Labels | {summary['n_labels']} |",
        f"| Flagged (all) | {summary['n_flagged']} ({summary['pct_flagged']}) |",
        f"| Flagged (report, ≥{_MIN_SAMPLES} samples) | {summary['n_flagged_report']} |",
        "",
        "## Top flagged labels",
        "",
    ]
    for k, v in top:
        md_lines.append(f"- `{k}`: {v}")
    md_lines.append("")
    safe_write(_MD_FILE, "\n".join(md_lines))

    print(f"flagged {len(issues)}/{len(fb_ids)} ({summary['pct_flagged']}) — "
          f"report subset {len(flagged)}")
    for k, v in top[:10]:
        print(f"  {k:<30} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
