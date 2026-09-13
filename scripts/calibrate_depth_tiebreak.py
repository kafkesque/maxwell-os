#!/usr/bin/env python3
"""Calibrate the deterministic depth tie-breaker signal (D2612 follow-up).

Verify (don't assume) whether the bge-m3 domain-cosine signal can break a
reliable-pair DEPTH disagreement.  Depth classes are:
    universal / cross-domain / domain / specialized.

Hypothesis under test: a "count domains above cosine threshold" (or the shape
of the 43-domain similarity distribution) separates the 4 depth classes.

Ground-truth proxy: the Qwen3.8 ontology-bound re-audit depth labels for the
149-core (frontier69_v2 + extension80).  NOTE: these are model labels, NOT
hand-verified (BUG-241) — so this measures *agreement with the best available
label*, not absolute truth.  That is sufficient to decide if the deterministic
rule is a *useful tie-breaker* (reproducible + non-degenerate), which is all a
tie-breaker needs to be.

Read-only.  Prints a calibration report; writes nothing.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.embeddings import embed_texts_bge_m3  # noqa: E402

FRONTIER69 = ROOT / "governance" / "deepseek_frontier69_audit_v2.json"
EXTENSION80 = ROOT / "governance" / "deepseek_extension80_audit.json"
GOLDEN = ROOT / "config" / "golden" / "stage4_golden_mined.yaml"
TAXONOMY = ROOT / "config" / "taxonomy_v5.yaml"
EMBED_CACHE = ROOT / "governance" / ".taxonomy_emb_v5.npz"

DEPTHS = ("universal", "cross-domain", "domain", "specialized")


def load_definitions() -> dict[str, str]:
    data = yaml.safe_load(GOLDEN.read_text(encoding="utf-8")) or {}
    out: dict[str, str] = {}
    for e in data.get("examples", []):
        fb = e.get("input_fb") or {}
        text = " ".join(
            (fb.get(k) or "") for k in ("name", "definition", "mechanism", "boundary")
        ).strip()
        if e.get("id") and text:
            out[e["id"]] = text
    return out


def load_audits() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in (FRONTIER69, EXTENSION80):
        data = json.loads(path.read_text(encoding="utf-8"))
        for eid, v in data.items():
            rows.append({
                "id": eid,
                "depth": v.get("depth"),
                "domains": v.get("domains") or [],
                "content_type": v.get("content_type"),
            })
    return rows


def load_domain_index() -> tuple[np.ndarray, list[str]]:
    z = np.load(EMBED_CACHE, allow_pickle=False)
    return z["dom_embs"].astype(np.float32), list(z["dom_names"])


def main() -> int:
    defs = load_definitions()
    audits = load_audits()
    dom_embs, dom_names = load_domain_index()

    rows = [a for a in audits if a["id"] in defs and a["depth"] in DEPTHS]
    print(f"audit rows: {len(audits)} | with definition + known depth: {len(rows)}")
    if not rows:
        return 1

    texts = [defs[a["id"]] for a in rows]
    embs = embed_texts_bge_m3(texts)
    sims = embs @ dom_embs.T  # (n, 43) cosine

    # Per-object distribution stats.
    top1 = np.sort(sims, axis=1)[:, -1]
    top2 = np.sort(sims, axis=1)[:, -2]
    top3 = np.sort(sims, axis=1)[:, -3]
    # top-1 index = argmax
    top1_idx = np.argmax(sims, axis=1)

    print("\n=== similarity-distribution stats by audit depth ===")
    print(f"{'depth':13s} {'n':>3s} {'max':>6s} {'top2':>6s} {'top3':>6s} {'gap1':>6s} {'gap2':>6s}")
    by_depth: dict[str, list[int]] = defaultdict(list)
    for i, a in enumerate(rows):
        by_depth[a["depth"]].append(i)
    for d in DEPTHS:
        idx = by_depth.get(d, [])
        if not idx:
            continue
        mx = np.mean(top1[idx]); t2 = np.mean(top2[idx]); t3 = np.mean(top3[idx])
        g1 = np.mean(top1[idx] - top2[idx]); g2 = np.mean(top2[idx] - top3[idx])
        print(f"{d:13s} {len(idx):3d} {mx:6.3f} {t2:6.3f} {t3:6.3f} {g1:6.3f} {g2:6.3f}")

    print("\n=== count-above-threshold accuracy vs audit depth ===")
    # Map count -> depth (v3 rule) and measure agreement.
    def map_count(n: int) -> str:
        if n >= 3:
            return "universal"
        if n == 2:
            return "cross-domain"
        if n == 1:
            return "domain"
        return "specialized"

    for thr in (0.35, 0.40, 0.45, 0.50, 0.55, 0.60):
        agree = 0
        conf = Counter()
        for i, a in enumerate(rows):
            n = int((sims[i] >= thr).sum())
            pred = map_count(n)
            if pred == a["depth"]:
                agree += 1
            conf[(a["depth"], pred)] += 1
        print(f"thr={thr:.2f}: agree {agree}/{len(rows)} ({100*agree/len(rows):.1f}%)")

    print("\n=== confusion (thr=0.45, count->depth) ===")
    conf = Counter()
    for i, a in enumerate(rows):
        n = int((sims[i] >= 0.45).sum())
        conf[(a["depth"], map_count(n))] += 1
    for d in DEPTHS:
        row = {map_count(n): conf[(d, map_count(n))] for n in range(0, 6)}
        print(f"{d:13s} -> {dict(row)}")

    print("\n=== dominant-domain (argmax) vs audit domains overlap ===")
    hits = 0
    for i, a in enumerate(rows):
        dom = dom_names[top1_idx[i]]
        if a["domains"] and dom in a["domains"]:
            hits += 1
    print(f"argmax domain in audit domain list: {hits}/{len(rows)} ({100*hits/len(rows):.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
