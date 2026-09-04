#!/usr/bin/env python3
"""nli_label_audit.py — T-NLI entailment audit (D2540/D2541/D2542).

Measures label<->content consistency across the corpus using DeBERTa-v3-large
NLI as an INDEPENDENT label verifier (extends R5 generator!=verifier beyond the
Stage-5 evidence check). For every FB that carries a canonical discipline/domain
label, run a single NLI pairing:

    premise     = FB definition (truncated to S5_NLI_MAX_PREMISE_CHARS)
    hypothesis  = "This text is about {label}."

then record entailment / neutral / contradiction probabilities.

Interpretation (model-free, mirroring stage5_verify._b2_majority_verdict):
  * contradiction-dominant (contra > entail AND contra > neutral) => the
    definition appears to CONTRADICT its own label => likely mislabel.
  * weak support (entail < S5_NLI_PASS_THRESHOLD) => label not backed by text.

This is a READ-ONLY measurement script: it writes governance reports but never
mutates the DB.

Outputs (via C6 crash-safe safe_write):
  governance/nli_label_audit.json  — aggregate + flagged lists
  governance/nli_label_audit.md    — human-readable report
  governance/nli_label_audit.checkpoint.jsonl — incremental resume checkpoint

Usage:
  python3 pipeline/nli_label_audit.py --axis both            # full audit
  python3 pipeline/nli_label_audit.py --axis both --sample 100
  python3 pipeline/nli_label_audit.py --axis both --resume   # continue after crash
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import yaml  # noqa: E402

from pipeline.io_guard import safe_write  # noqa: E402  (C6 crash-safe writes)
from pipeline.pipeline_paths import (  # noqa: E402
    DB_PATH,
    S5_NLI_MAX_PREMISE_CHARS,
    S5_NLI_PASS_THRESHOLD,
)
from pipeline.stage5_verify import NLIInferenceError, _nli_pair_scores  # noqa: E402

_HYPOTHESIS_TEMPLATE = "This text is about {label}."  # C20: named NL template
_TAXONOMY_PATH = _ROOT / "config" / "taxonomy_v5.yaml"  # C12: config-first source
_CHECKPOINT_INTERVAL = 100  # C20: flush checkpoint every N audited FBs
_ERROR_MSG_MAX_LEN = 200  # C20: truncate NLI error strings in the report
_MD_TOP_N = 30  # C20: how many contradict-label rows to surface in the .md
_CHECKPOINT_FILE = _ROOT / "governance" / "nli_label_audit.checkpoint.jsonl"
_JSON_FILE = _ROOT / "governance" / "nli_label_audit.json"
_MD_FILE = _ROOT / "governance" / "nli_label_audit.md"


def _load_canonicals() -> tuple[set[str], set[str]]:
    """Load canonical discipline/domain sets from taxonomy_v5.yaml (C12)."""
    tax = yaml.safe_load(open(_TAXONOMY_PATH, encoding="utf-8"))
    discs = {d["canonical"] for d in tax.get("disciplines", [])}
    doms = {d["canonical"] for d in tax.get("domains", [])}
    return discs, doms


def _parse_domains(raw: str | None) -> set[str]:
    """Parse the `domains` column (JSON array string) into a domain set."""
    if not raw:
        return set()
    s = raw.strip()
    if s.startswith("["):
        try:
            return {str(x).strip() for x in json.loads(s) if str(x).strip()}
        except (json.JSONDecodeError, TypeError):
            pass
    return {x.strip() for x in s.split("|") if x.strip()}


def _load_checkpoint() -> tuple[set[tuple[str, str, str]], list[dict]]:
    """Return (done_keys, prior_results) from the checkpoint JSONL.

    Tolerates a torn final line (partial write on crash) by skipping malformed
    records — the resume never crashes on a corrupted tail (C16 loud on errors,
    but a checkpoint is a progress log, not a final artifact).
    """
    done: set[tuple[str, str, str]] = set()
    prior: list[dict] = []
    if not _CHECKPOINT_FILE.exists():
        return done, prior
    for line in _CHECKPOINT_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            done.add((str(rec["fb_id"]), str(rec["axis"]), str(rec["label"])))
            prior.append(rec)
        except (json.JSONDecodeError, KeyError):
            # C16: log the skip loudly — never silently drop a checkpoint record.
            print(f"  ⚠️  checkpoint: skipping malformed line {line[:80]!r}", file=sys.stderr)
            continue
    return done, prior


def _audit_pair(
    fb_id: str, axis: str, label: str, definition: str
) -> dict:
    """Run one NLI pairing and return a normalized result record."""
    premise = definition[:S5_NLI_MAX_PREMISE_CHARS]
    hypothesis = _HYPOTHESIS_TEMPLATE.format(label=label)
    try:
        entail, neutral, contra = _nli_pair_scores(premise, hypothesis, raise_on_error=True)
    except NLIInferenceError as e:
        # C16: record infra/model errors loudly, never fold into a semantic verdict.
        return {"fb_id": fb_id, "axis": axis, "label": label,
                "entail": None, "neutral": None, "contra": None,
                "error": str(e)[:_ERROR_MSG_MAX_LEN]}
    contra_dominant = contra > entail and contra > neutral
    weak = entail < S5_NLI_PASS_THRESHOLD
    return {"fb_id": fb_id, "axis": axis, "label": label,
            "entail": round(entail, 4), "neutral": round(neutral, 4),
            "contra": round(contra, 4),
            "contra_dominant": contra_dominant, "weak": weak}


def _build_md(summary: dict, contradicts: list[dict], weak: list[dict]) -> str:
    """Render the human-readable Markdown report (D2540 measure-first)."""
    lines = [
        "# NLI LABEL AUDIT — entailment consistency (D2540/D2541)",
        "",
        "> **Model:** DeBERTa-v3-large (local, D2298) · hypothesis = "
        f"\"{_HYPOTHESIS_TEMPLATE}\"",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| FBs audited | {summary['n_audited']} |",
        f"| Discipline pairings | {summary['n_discipline']} |",
        f"| Domain pairings | {summary['n_domain']} |",
        f"| Mean entail (discipline) | {summary['mean_entail_discipline']} |",
        f"| Mean entail (domain) | {summary['mean_entail_domain']} |",
        f"| Contradict-label (likely mislabel) | {summary['contradicts_label']} |",
        f"| Weak support (entail < {summary['weak_threshold']}) | {summary['weak_support']} |",
        f"| NLI errors (recorded, not silent) | {summary['n_errors']} |",
        "",
    ]
    if contradicts:
        lines += [f"## 🚩 Contradicts own label (top {_MD_TOP_N} — human-review candidates)", ""]
        for r in contradicts[:_MD_TOP_N]:
            lines.append(f"- `{r['fb_id']}` [{r['axis']}] `{r['label']}` "
                         f"— ent={r['entail']} contra={r['contra']}")
        lines.append("")
    else:
        lines += ["## 🚩 Contradicts own label", "", "_None_", ""]
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="T-NLI label-consistency audit (D2540/D2541).")
    parser.add_argument("--db", default=str(DB_PATH))
    parser.add_argument("--axis", choices=["discipline", "domain", "both"], default="both")
    parser.add_argument("--sample", type=int, default=0, help="Audit only N FBs (0 = all).")
    parser.add_argument("--resume", action="store_true", help="Skip already-checkpointed pairs.")
    args = parser.parse_args()

    discs, doms = _load_canonicals()
    if args.resume:
        done, results = _load_checkpoint()
        print(f"   ↻ resumed: {len(results)} prior pairs, {len(done)} keys")
    else:
        done, results = set(), []

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    rows = list(conn.execute(
        "SELECT fb_id, definition, discipline, domains FROM fbs "
        "WHERE definition IS NOT NULL AND definition != ''"
    ))
    conn.close()
    if args.sample:
        rows = rows[: args.sample]

    checkpoint_fh = None
    try:
        _CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Fresh run truncates the checkpoint; --resume appends to it.
        checkpoint_fh = open(_CHECKPOINT_FILE, "a" if args.resume else "w", encoding="utf-8")
        for i, r in enumerate(rows):
            fb_id = r["fb_id"]
            definition = r["definition"] or ""
            if args.axis in ("discipline", "both") and r["discipline"] in discs:
                key = (fb_id, "discipline", r["discipline"])
                if key not in done:
                    rec = _audit_pair(fb_id, "discipline", r["discipline"], definition)
                    results.append(rec)
                    checkpoint_fh.write(json.dumps(rec) + "\n")
            if args.axis in ("domain", "both"):
                for dom in sorted(_parse_domains(r["domains"]) & doms):
                    key = (fb_id, "domain", dom)
                    if key not in done:
                        rec = _audit_pair(fb_id, "domain", dom, definition)
                        results.append(rec)
                        checkpoint_fh.write(json.dumps(rec) + "\n")
            if (i + 1) % _CHECKPOINT_INTERVAL == 0:
                checkpoint_fh.flush()
                os.fsync(checkpoint_fh.fileno())  # C6: durable flush, not just OS buffer
                print(f"   … {i + 1}/{len(rows)} FBs audited", flush=True)
    finally:
        if checkpoint_fh is not None:
            checkpoint_fh.close()

    # Aggregate (skip error rows for score stats, but keep them counted).
    ok = [x for x in results if x.get("entail") is not None]
    errs = [x for x in results if x.get("entail") is None]
    disc_ok = [x for x in ok if x["axis"] == "discipline"]
    dom_ok = [x for x in ok if x["axis"] == "domain"]

    def _mean_entail(xs: list[dict]) -> float:
        return round(sum(x["entail"] for x in xs) / len(xs), 4) if xs else 0.0

    contradicts = sorted(
        [x for x in ok if x["contra_dominant"]],
        key=lambda x: (x["contra"] - x["entail"]),
        reverse=True,
    )
    weak = sorted(
        [x for x in ok if x["weak"] and not x["contra_dominant"]],
        key=lambda x: x["entail"],
    )

    summary = {
        "n_audited": len(results),
        "n_discipline": len(disc_ok),
        "n_domain": len(dom_ok),
        "mean_entail_discipline": _mean_entail(disc_ok),
        "mean_entail_domain": _mean_entail(dom_ok),
        "contradicts_label": len(contradicts),
        "weak_support": len(weak),
        "weak_threshold": S5_NLI_PASS_THRESHOLD,
        "n_errors": len(errs),
    }

    _JSON_FILE.parent.mkdir(parents=True, exist_ok=True)
    safe_write(_JSON_FILE, json.dumps(
        {"summary": summary, "contradicts_label": contradicts, "weak_support": weak},
        indent=2,
    ) + "\n", force_shrink=True)
    safe_write(_MD_FILE, _build_md(summary, contradicts, weak), force_shrink=True)

    print(f"✅ NLI label audit: {summary['n_audited']} pairs "
          f"(disc mean ent {summary['mean_entail_discipline']}, "
          f"dom mean ent {summary['mean_entail_domain']}), "
          f"{summary['contradicts_label']} contradict-label, "
          f"{summary['weak_support']} weak, {summary['n_errors']} errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
