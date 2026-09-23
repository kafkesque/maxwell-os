#!/usr/bin/env python3
"""scripts/representability_sweep.py — is an axis CLASSIFIABLE as labelled? (D-343)

WHY (2026-09-23): every model-centric lever in this repo has been measured and closed —
content_type lift over the constant baseline -0.010 (F-17), R3 held-out arbitration gain
+0.00 pp (D-311/D-314), challenger -8.77 pp, and k-NN retired as a MISLABEL detector
(D2575: it measures topical coherence, not correctness). So the open question is not
"which model" but "which axes are separable AT ALL in the representation the pipeline
actually uses".

METHOD. For each axis, every labelled FB's k nearest neighbours in bge-m3 512d space are
looked up and the fraction of neighbours SHARING the row's label is averaged. The
reference is a SEEDED LABEL-PERMUTATION NULL: labels are shuffled across rows, which
preserves the label frequency distribution, so the null absorbs the constant-answer
baseline and class imbalance. lift_pp = (observed - null) * 100. An axis whose lift sits
inside the pre-registered chance margin is not classifiable as labelled, at any model
scale, and must be routed to the constant + a human queue instead of a classifier.

This is the RETAINED use of k-NN per D2575: coherence is not "correctness", but if
neighbours do not share the label then no classifier over this representation can
separate it, and that is exactly the deployability question.

Config-first (C12): every path, axis, threshold, seed and block size is read from
config/representability_sweep.yaml. Fail-closed (C16): a storage that cannot be parsed,
a corpus thinner than `min_rows`, or an embedding/row mismatch RAISES rather than
reporting a number it cannot stand behind.

Usage:
    python3 scripts/representability_sweep.py [--config config/representability_sweep.yaml]
Outputs: governance/REPRESENTABILITY_SWEEP_20260923.json + .md
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Sequence, Tuple

import numpy as np  # noqa: E402
import yaml  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = _ROOT / "config" / "representability_sweep.yaml"
_NORM_KEEP = frozenset("abcdefghijklmnopqrstuvwxyz0123456789")
_NORM_EPS = 1e-9


def atomic_write(path: Path, text: str) -> None:
    """Write text atomically: tempfile -> fsync -> os.replace (C6)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def load_config(path: Path) -> Dict[str, Any]:
    """Load and validate the sweep config; a missing required key is a hard error (C12/C16)."""
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    required = ("db", "dim", "k", "axes", "min_rows", "block_rows", "blinding_seed",
                "output_json", "output_md", "separable_min_pp", "chance_margin_pp")
    missing = [key for key in required if key not in cfg]
    if missing:
        raise KeyError(f"{path.name}: missing required key(s) {missing} (C12/C16)")
    return cfg


def normalise_label(value: str) -> str:
    """Normalise a label exactly as config/eval_integrity.yaml declares: lowercase, alphanumerics only."""
    return "".join(ch for ch in value.strip().lower() if ch in _NORM_KEEP)


def parse_labels(raw: Any, delimiters: Sequence[str]) -> FrozenSet[str]:
    """Parse one label cell into a normalised label set (multi-label aware)."""
    if raw is None:
        return frozenset()
    text = str(raw)
    for delim in delimiters:
        text = text.replace(delim, "\n")
    out = {normalise_label(part) for part in text.split("\n")}
    out.discard("")
    return frozenset(out)


def load_vectors(conn: sqlite3.Connection, cfg: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
    """Rebuild the vec0 shadow storage into (rowids, L2-normalised matrix).

    Reads the shadow tables directly so the vec0 SQL module is not required (the system
    python3 build cannot load it). Fail-closed: any byte-length, chunk, duplicate-rowid or
    coverage inconsistency RAISES — a kNN computed over a misassembled matrix would be a
    BUG-375-class check that cannot see what it claims to check.
    """
    dim = int(cfg["dim"])
    row_bytes = dim * 4
    cur = conn.cursor()
    chunks: Dict[int, np.ndarray] = {}
    cur.execute(f"SELECT rowid, vectors FROM {cfg['vec_shadow_chunks']}")
    for chunk_id, blob in cur.fetchall():
        blob = bytes(blob)
        if not blob or len(blob) % row_bytes:
            raise ValueError(f"vec chunk {chunk_id}: {len(blob)} bytes is not a positive multiple "
                             f"of {row_bytes} (cannot trust the vector store)")
        chunks[int(chunk_id)] = np.frombuffer(blob, dtype=np.float32).reshape(-1, dim)
    cur.execute(f"SELECT rowid, id, chunk_id, chunk_offset FROM {cfg['vec_shadow_rowids']}")
    rows = cur.fetchall()
    if not rows:
        raise RuntimeError("vec shadow rowids is empty — run pipeline/backfill_embeddings.py first")
    ids = np.empty(len(rows), dtype=np.int64)
    mat = np.empty((len(rows), dim), dtype=np.float32)
    seen: set[int] = set()
    for i, (rowid, declared, chunk_id, offset) in enumerate(rows):
        key = int(declared) if declared is not None else int(rowid)
        if int(chunk_id) not in chunks:
            raise KeyError(f"vec row {key} references missing chunk {chunk_id}")
        chunk = chunks[int(chunk_id)]
        if int(offset) >= chunk.shape[0]:
            raise IndexError(f"vec row {key}: offset {offset} outside chunk {chunk_id} "
                             f"({chunk.shape[0]} vectors)")
        mat[i] = chunk[int(offset)]
        ids[i] = key
        if key in seen:
            raise ValueError(f"duplicate vec rowid {key} in shadow rowids")
        seen.add(key)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    return ids, mat / np.maximum(norms, _NORM_EPS)


def fetch_labels(conn: sqlite3.Connection, cfg: Dict[str, Any], axis: str,
                 rowids: np.ndarray) -> Tuple[List[FrozenSet[str]], int]:
    """Return label sets aligned to `rowids` plus the number of vec rows with no fbs match."""
    spec = cfg["axes"][axis]
    delimiters = spec.get("multi_label_delimiters", [","])
    placeholders = ",".join("?" for _ in rowids)
    cur = conn.cursor()
    cur.execute(f"SELECT rowid, {spec['column']} FROM fbs WHERE rowid IN ({placeholders})",
                [int(r) for r in rowids])
    found = {int(rid): raw for rid, raw in cur.fetchall()}
    labels = [parse_labels(found.get(int(rid)), delimiters) for rid in rowids]
    return labels, len(rowids) - len(found)


def knn_agreement(labels: List[FrozenSet[str]], mat: np.ndarray, k: int, multi: bool,
                  block_rows: int) -> np.ndarray:
    """Per-row neighbour label agreement.

    Single-label: fraction of the k neighbours carrying the SAME label (exact match).
    Multi-label: mean recall of the row's own labels (|row ∩ neighbour| / |row|).
    """
    n = mat.shape[0]
    out = np.zeros(n, dtype=np.float64)
    for start in range(0, n, block_rows):
        stop = min(start + block_rows, n)
        sims = mat[start:stop] @ mat.T
        for offset in range(stop - start):
            sims[offset, start + offset] = -np.inf  # exclude self (cosine 1.0)
        top = np.argpartition(-sims, k, axis=1)[:, :k]
        for offset in range(stop - start):
            row = labels[start + offset]
            if not row:
                continue
            total = 0.0
            for neighbour in top[offset]:
                other = labels[int(neighbour)]
                total += (len(row & other) / len(row)) if multi else (1.0 if row == other else 0.0)
            out[start + offset] = total / k
    return out


def axis_report(axis: str, labels: List[FrozenSet[str]], mat: np.ndarray, cfg: Dict[str, Any],
                rng: np.random.Generator) -> Dict[str, Any]:
    """Measure one axis against its permutation null and route it."""
    k = int(cfg["k"])
    multi = bool(cfg["axes"][axis].get("multi_label", False))
    accepted = [i for i, lab in enumerate(labels) if lab]
    effective_n = len(accepted)
    if effective_n < int(cfg["min_rows"]):
        raise RuntimeError(f"axis '{axis}': effective n {effective_n} < min_rows "
                           f"{cfg['min_rows']} — refusing to publish a verdict (C16)")
    counts: Dict[FrozenSet[str], int] = {}
    for i in accepted:
        counts[labels[i]] = counts.get(labels[i], 0) + 1
    modal_set, modal_n = max(counts.items(), key=lambda kv: kv[1])
    modal_share = modal_n / effective_n

    observed = knn_agreement(labels, mat, k, multi, int(cfg["block_rows"]))
    permuted = list(labels)
    order = rng.permutation(len(permuted))
    permuted = [permuted[int(i)] for i in order]
    null = knn_agreement(permuted, mat, k, multi, int(cfg["block_rows"]))
    obs_mean = float(np.mean(observed[accepted]))
    null_mean = float(np.mean(null[accepted]))
    lift_pp = (obs_mean - null_mean) * 100.0

    # TWO references must both be beaten (2026-09-23, D-343): the permutation null
    # (is there ANY label signal?) and the constant-answer baseline (is the classifier
    # better than always emitting the modal label?). An axis that loses to the constant
    # must NOT be classified, however large its lift over the null happens to be.
    beats_constant = obs_mean > modal_share
    gain_over_constant_pp = (obs_mean - modal_share) * 100.0
    if not beats_constant:
        route = "constant_plus_human_queue"
    elif lift_pp >= float(cfg["separable_min_pp"]) and gain_over_constant_pp >= float(cfg["chance_margin_pp"]):
        route = "classify"
    elif lift_pp >= float(cfg["chance_margin_pp"]):
        route = "coarsen_or_classify_with_calibrated_abstention"
    else:
        route = "constant_plus_human_queue"

    per_label: List[Dict[str, Any]] = []
    if not multi:
        index: Dict[str, List[int]] = {}
        for i in accepted:
            label = next(iter(labels[i]))
            index.setdefault(label, []).append(i)
        for label, idx in index.items():
            if len(idx) < int(cfg["min_label_rows"]):
                continue
            per_label.append({"label": label, "rows": len(idx),
                              "knn_agreement": round(float(np.mean(observed[idx])), 4),
                              "global_share": round(len(idx) / effective_n, 4)})
    return {
        "axis": axis, "multi_label": multi, "effective_n": effective_n,
        "excluded_empty_label_rows": len(labels) - effective_n,
        "modal_share": round(modal_share, 4),
        "modal_label": sorted(modal_set) if multi else (next(iter(modal_set)) if modal_set else ""),
        "knn_agreement_observed": round(obs_mean, 4),
        "knn_agreement_permutation_null": round(null_mean, 4),
        "lift_over_null_pp": round(lift_pp, 2),
        "lift_over_constant_pp": round(gain_over_constant_pp, 2),
        "beats_constant_baseline": bool(beats_constant),
        "route": route,
        "worst_labels": sorted(per_label, key=lambda d: d["knn_agreement"])[:int(cfg["top_labels"])],
    }


def git_commit() -> str:
    """Return the current short commit (R14 stamp), or 'unknown' outside a repo."""
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=_ROOT, check=True,
                              capture_output=True, text=True).stdout.strip()
    except Exception:  # noqa: BLE001 — a missing commit must not fail a measurement
        return "unknown"


def render_markdown(result: Dict[str, Any], cfg: Dict[str, Any]) -> str:
    """Render the human-readable sweep report (routing table first)."""
    lines = [
        "# REPRESENTABILITY SWEEP — 2026-09-23 (D-343)",
        "",
        "**Question:** which axes can a classifier separate AT ALL in the representation the",
        "pipeline actually uses (bge-m3 512d)? **Reference:** a seeded label-permutation NULL,",
        "which preserves label frequencies and therefore absorbs the constant-answer baseline.",
        "",
        "| axis | effective n | modal share | kNN agreement | permutation null | lift over null | route |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in result["axes"]:
        lines.append(f"| {row['axis']} | {row['effective_n']} | {row['modal_share']} | "
                     f"{row['knn_agreement_observed']} | {row['knn_agreement_permutation_null']} | "
                     f"{row['lift_over_null_pp']:+} pp | `{row['route']}` |")
    lines += ["", "## Worst-performing labels per axis (the coarsen/retire queue)", ""]
    for row in result["axes"]:
        if not row["worst_labels"]:
            continue
        lines.append(f"### {row['axis']}")
        lines.append("")
        lines.append("| label | rows | kNN agreement | global share |")
        lines.append("|---|---|---|---|")
        for item in row["worst_labels"]:
            lines.append(f"| {item['label']} | {item['rows']} | {item['knn_agreement']} | "
                         f"{item['global_share']} |")
        lines.append("")
    lines += [
        "## Reading the routing table",
        "",
        "- `classify` — the embedding separates the labels; a classifier (any model) can work here.",
        "- `coarsen_or_classify_with_calibrated_abstention` — weak signal; only usable with a measured",
        "  selective-risk curve, never as a silent point label.",
        "- `constant_plus_human_queue` — no label signal in this representation at this granularity.",
        "  Deploying a classifier here is strictly worse than emitting the constant and queueing the",
        "  rest for review (D-275a/D-300). Fix the MENU, not the model.",
        "",
        "## Provenance",
        "",
        f"- decision: {cfg.get('decision')} | schema_version: {result['schema_version']}",
        f"- generator: {result['gen_model']} (deterministic, no LLM) | commit: {result['pipeline_commit']}",
        f"- corpus: {result['db']} ({result['n_vectors']} vectors, k={result['k']}, seed={result['seed']})",
        "- reference error rate (quoted, never re-derived — BUG-342): "
        f"{json.dumps(result['reference_stored_error'])}",
        "- control: the permutation null above IS the blinding control (R3 precedent).",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    """Run the sweep, print the routing table, write the JSON + MD artifacts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    cfg = load_config(Path(args.config))
    db_path = _ROOT / str(cfg["db"])
    if not db_path.exists():
        raise FileNotFoundError(f"db not found: {db_path} (C16)")
    conn = sqlite3.connect(str(db_path))
    ids, mat = load_vectors(conn, cfg)
    conn.execute("ATTACH DATABASE ? AS main_db", (str(db_path),)) if False else None
    rng = np.random.default_rng(int(cfg["blinding_seed"]))
    axes = []
    for axis in cfg["axes"]:
        labels, unmatched = fetch_labels(conn, cfg, axis, ids)
        row = axis_report(axis, labels, mat, cfg, rng)
        row["vec_rows_without_fbs_match"] = unmatched
        axes.append(row)
    conn.close()
    reference = {}
    try:
        integrity = yaml.safe_load((_ROOT / "config" / "eval_integrity.yaml").read_text(encoding="utf-8"))
        reference = integrity["ruler_measurement"]["measured_error_rate"]
    except Exception as exc:  # noqa: BLE001 — a missing reference is reported, never invented
        reference = {"error": f"unavailable: {exc}"}
    result: Dict[str, Any] = {
        "schema_version": "1.0",
        "gen_model": "deterministic-numpy",
        "pipeline_commit": git_commit(),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "decision": cfg.get("decision"),
        "db": str(cfg["db"]),
        "n_vectors": int(mat.shape[0]),
        "dim": int(mat.shape[1]),
        "k": int(cfg["k"]),
        "seed": int(cfg["blinding_seed"]),
        "reference_stored_error": reference,
        "axes": axes,
    }
    atomic_write(_ROOT / str(cfg["output_json"]), json.dumps(result, indent=2) + "\n")
    atomic_write(_ROOT / str(cfg["output_md"]), render_markdown(result, cfg))
    print(f"{'axis':<16}{'n':>6}{'modal':>8}{'knn':>8}{'null':>8}{'lift_pp':>10}  route")
    for row in axes:
        print(f"{row['axis']:<16}{row['effective_n']:>6}{row['modal_share']:>8}"
              f"{row['knn_agreement_observed']:>8}{row['knn_agreement_permutation_null']:>8}"
              f"{row['lift_over_null_pp']:>10}  {row['route']}")
    print(f"wrote {cfg['output_json']} + {cfg['output_md']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
