#!/usr/bin/env python3
"""scripts/menu_merge_map.py — measure the discipline tail-merge map (D-348).

For each tail label named by config/menu_routing.yaml, compute its stored-row
centroid in the vec_fbs representation and rank every closed-menu candidate by
cosine. Propose merge_into_parent only when the winner beats the runner-up by the
declared margin; otherwise keep_label. Writes the evidence artifact and the
proposal config (C6 atomic, C16 fail-closed).
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import tempfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml

_ROOT = Path(__file__).resolve().parent.parent
_CFG = yaml.safe_load((_ROOT / "config" / "menu_merge_map.yaml").read_text(encoding='utf-8'))
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def canon(text: str) -> str:
    """Canonicalise a label for menu/store comparison."""
    return _NON_ALNUM.sub("", str(text).lower())


def load_knr():
    """Import the proven vec_fbs reader (knn_arm_eval) without executing main."""
    spec = importlib.util.spec_from_file_location("knr", _ROOT / _CFG["knn_arm_module"])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def label_of(rec: dict, axis: str) -> str | None:
    """Pull the axis label out of a meta record (the reader nests labels under a labels key)."""
    labels = rec.get("labels") or {}
    for key in (axis, axis + "_final"):
        if labels.get(key):
            return str(labels[key])
    return None


def centroids(rowids, mat, meta, axis) -> dict[str, tuple[np.ndarray, int]]:
    """Return {canon_label: (unit centroid, n_rows)} for the declared axis."""
    acc: dict[str, list[np.ndarray]] = defaultdict(list)
    for i, rid in enumerate(rowids):
        lab = label_of(meta.get(rid, {}), axis)
        if lab:
            acc[canon(lab)].append(mat[i])
    out = {}
    for lab, vecs in acc.items():
        m = np.mean(np.vstack(vecs), axis=0)
        nrm = float(np.linalg.norm(m))
        out[lab] = (m / nrm if nrm else m, len(vecs))
    return out


def write_atomic(path: Path, text: str) -> None:
    """C6 crash-safe write: tempfile -> fsync -> os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    with os.fdopen(fd, "w") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def main() -> int:
    """Measure the map, write evidence + proposal config."""
    routing = yaml.safe_load((_ROOT / _CFG["routing_config"]).read_text(encoding='utf-8'))
    axis_cfg = routing["axes"][_CFG["axis"]]
    tails = [q["label"] for q in axis_cfg.get("queue", [])]
    if not tails:
        raise SystemExit("routing config names no tail labels - refusing (C16)")
    menu = json.loads((_ROOT / _CFG["closed_menu"]).read_text(encoding='utf-8'))
    candidates = [d["value"] for d in menu["disciplines"]
                  if canon(d["value"]) not in {canon(t) for t in tails}
                  and d["value"] not in _CFG["excluded_candidates"]]
    groups = {d["value"]: d.get("group", "") for d in menu["disciplines"]}

    knr = load_knr()
    rowids, mat = knr.load_vectors(knr.load_cfg())
    meta = knr.load_meta(knr.load_cfg())
    if mat.shape[1] != _CFG["dim"]:
        raise SystemExit(f"vector dim {mat.shape[1]} != declared {_CFG['dim']} - refusing (C16)")
    cents = centroids(rowids, mat, meta, _CFG["axis"])

    rows, md = [], ["# MENU MERGE MAP — discipline tail labels, measured (D-348)", "",
                    f"Reader: {_CFG['knn_arm_module']} over {_CFG['db']} "
                    f"(vec_fbs, dim {_CFG['dim']}, {len(rowids)} rows). "
                    f"Candidates: {len(candidates)} closed-menu disciplines. "
                    f"Rule: parent = nearest stored-row centroid; merge proposed only if it beats the "
                    f"runner-up by >= {_CFG['runner_up_margin']}.", "",
                    "| tail label | rows | proposed parent | cos | runner-up | cos | gap | action | group |",
                    "|---|---|---|---|---|---|---|---|---|"]
    ranked_out = {}
    for tail in tails:
        ck = canon(tail)
        if ck not in cents:
            raise SystemExit(f"tail label {tail!r} has no stored rows - refusing (C16)")
        vec, n_rows = cents[ck]
        scores = sorted(((float(np.dot(vec, cents[canon(c)][0])), c) for c in candidates if canon(c) in cents),
                        reverse=True)
        top = scores[0]
        second = scores[1] if len(scores) > 1 else (0.0, "none")
        gap = top[0] - second[0]
        if n_rows < _CFG["min_label_rows"]:
            action, parent, reason = "keep_label", None, f"only {n_rows} rows - centroid is noise"
        elif gap >= _CFG["runner_up_margin"]:
            action, parent, reason = "merge_into_parent", top[1], f"beats runner-up by {round(gap, 4)}"
        else:
            action, parent, reason = "keep_label", None, f"ambiguous: gap {round(gap, 4)} < {_CFG['runner_up_margin']}"
        row = {"tail_label": tail, "n_rows": n_rows, "action": action, "parent": parent,
               "parent_group": groups.get(parent, "") if parent else "", "reason": reason,
               "best": {"label": top[1], "cos": round(top[0], 4)},
               "runner_up": {"label": second[1], "cos": round(second[0], 4)}, "gap": round(gap, 4)}
        rows.append(row)
        ranked_out[tail] = row
        md.append("| " + " | ".join([tail, str(n_rows), str(parent or "-"), str(round(top[0], 4)),
                                     str(second[1]), str(round(second[0], 4)), str(round(gap, 4)), action,
                                     groups.get(parent, "") if parent else "-"]) + " |")
    n_merge = sum(1 for r in rows if r["action"] == "merge_into_parent")
    md += ["", f"{n_merge} of {len(rows)} tail labels have an unambiguous measured parent; the rest are "
               f"returned keep_label rather than forced (C16: no invented parent).",
           "", _CFG["qualifier"], ""]
    art = {"schema_version": "1.0", "decision": _CFG["decision"], "axis": _CFG["axis"],
           "reader": _CFG["knn_arm_module"], "db": _CFG["db"], "dim": _CFG["dim"], "n_rows": len(rowids),
           "runner_up_margin": _CFG["runner_up_margin"], "min_label_rows": _CFG["min_label_rows"],
           "n_tail": len(rows), "n_merge": n_merge, "qualifier": _CFG["qualifier"], "map": rows}
    write_atomic(_ROOT / _CFG["output_json"], json.dumps(art, indent=2) + chr(10))
    write_atomic(_ROOT / _CFG["output_md"], chr(10).join(md))
    prop = ["# config/menu_v6_merge_map.yaml — measured discipline merge map (D-348, PROPOSAL)",
            "# Generated by scripts/menu_merge_map.py from governance/MENU_MERGE_MAP_20260923.json.",
            "# NOT IN FORCE. Adopting it is the versioned v5.6 -> v6 menu change (D-346): the labeler must",
            "# be re-run and the ruler re-scored. Until then the current menu keeps every label below.",
            "schema_version: '1.0'", "decision: D-348", "status: proposal", "axis: discipline",
            "evidence: governance/MENU_MERGE_MAP_20260923.json",
            "merge_map:"]
    for r in rows:
        if r["action"] == "merge_into_parent":
            prop.append(f"  - {{tail: {r['tail_label']}, parent: {r['parent']}, cos: {r['best']['cos']}, gap: {r['gap']}}}")
    prop.append("keep_label:")
    for r in rows:
        if r["action"] != "merge_into_parent":
            prop.append("  - {tail: " + r["tail_label"] + ", reason: " + repr(r["reason"]) + "}")
    write_atomic(_ROOT / _CFG["output_config"], chr(10).join(prop) + chr(10))
    for r in rows:
        print(f"{r['tail_label']:32s} n={r['n_rows']:5d} -> {str(r['parent']):24s} cos={r['best']['cos']:.4f} "
              f"runner={r['runner_up']['label']}({r['runner_up']['cos']:.4f}) gap={r['gap']:.4f} {r['action']}")
    print(f"wrote {_CFG['output_json']} {_CFG['output_md']} {_CFG['output_config']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
