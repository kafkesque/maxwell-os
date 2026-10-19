#!/usr/bin/env python3
"""Build the semantic re-attachment map: 251 gold anchors -> live principles (D-3106/D-3107).

WHY: fb_id = sha256(name|definition) is generation-sensitive (D-2949/F-19), so corpus re-generation
orphaned the golden anchor (governance/gold_4axis.jsonl, 251 rows) — 0/251 resolve in the live DB
(pipeline_commit 32321c9). This computes the D-3107 generation-invariant re-attachment: embed anchor
(name + definition) and live principle (name + definition) with bge-m3, cosine-match, and emit a
PROPOSED map + the delta still needing owner adjudication. It shrinks a full 251-row re-adjudication
into a small human-review delta. The map is PROPOSED ONLY — applying it is owner-gated (D-3106).

Outputs (under --out-dir, default governance/):
  gold_reattach_map.jsonl   — PROPOSED matches (old fb_id -> live fb_id, similarity, name, tier)
  gold_reattach_delta.jsonl — anchors with NO confident match (owner must re-adjudicate)
Prints a compact summary. Embeddings are cached to temp/ so a re-run is cheap.

The cosine threshold (--sim), cache path (--cache) and output dir (--out-dir) are argv-overridable; the
one value that is a JUDGEMENT (the cosine threshold) is a named constant with its rationale, not a magic number.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
GOLD = REPO / "governance" / "gold_4axis.jsonl"
DB = REPO / "knowledge pipeline" / "maxwell.db"
LIVE_COMMIT = "32321c9"
OLLAMA = "http://localhost:11434/api/embed"
EMBED_MODEL = "bge-m3:latest"
# A judgement, stated: matched concepts re-worded across generations sit ~0.7+; unrelated concepts sit
# ~0.3-0.5 under bge-m3 (name+definition). 0.6 is the conservative "proposed match" floor — below it the
# anchor goes to the delta and the OWNER decides (fail-closed on identity, D-3106).
PROPOSE_SIM = 0.60
BATCH = 64
# D-3107 one-to-one uniqueness pass (BUG-946 root cause): a live principle may be claimed by AT MOST ONE
# anchor, because each anchor and each live principle are distinct concepts. A genuine 2-anchor fusion
# (near-same) is RARE and is the OWNER's call (gold_reattach_many_to_one_ADJUDICATION.csv), never a silent
# auto-merge. A contended live row keeps its single strongest claim; the rest are demoted to tier "many-to-one".
EXACT_PRIORITY = 2     # exact-name identity outranks any cosine similarity (max 1.0)
SEMANTIC_PRIORITY = 1  # cosine-confidence claim


def embed(texts: list[str]) -> np.ndarray:
    """Batch-embed via Ollama /api/embed and return a (n, dim) float32 array."""
    out: list[np.ndarray] = []
    for i in range(0, len(texts), BATCH):
        chunk = texts[i:i + BATCH]
        req = urllib.request.Request(
            OLLAMA, data=json.dumps({"model": EMBED_MODEL, "input": chunk}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            arr = json.load(r)["embeddings"]
        out.append(np.asarray(arr, dtype=np.float32))
    return np.vstack(out)


def norm(x: np.ndarray) -> np.ndarray:
    d = np.linalg.norm(x, axis=1, keepdims=True)
    d[d == 0] = 1.0
    return x / d


def norm_name(s: str) -> str:
    return " ".join(str(s).lower().split())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", type=float, default=PROPOSE_SIM)
    ap.add_argument("--cache", default=str(REPO / "temp" / "anchor_reattach_emb.npz"))
    ap.add_argument("--out-dir", default=str(REPO / "governance"),
                    help="directory for the 3 output artifacts (default governance/)")
    a = ap.parse_args()
    out_dir = Path(a.out_dir)

    anchors = [json.loads(l) for l in GOLD.read_text(encoding="utf-8").splitlines() if l.strip()]
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    live = con.execute(
        "SELECT fb_id, name, definition FROM fbs WHERE content_type='principle' "
        "AND pipeline_commit=? AND definition IS NOT NULL AND definition != ''",
        (LIVE_COMMIT,)).fetchall()
    con.close()

    # Name-only first pass: the NAME is the strongest generation-invariant identity signal and keeps the
    # run fast (definitions avg 207 chars x 6587 ~= 50x the tokens). A definition-refinement pass is the
    # documented second step if this first pass leaves too large a delta (D-3107 mechanism, not a one-shot).
    a_text = [str(x["name"]).strip() for x in anchors]
    l_text = [str(n).strip() for _, n, d in live]
    live_ids = [r[0] for r in live]

    cache = Path(a.cache)
    A = L = None
    if cache.exists():
        data = np.load(cache)
        A, L = data["A"], data["L"]
        # Cache-staleness guard (BUG-946 follow-up / D-3107): the cache is keyed by the ORDERED live
        # fb_id list. Any change to the live principle set — count, content, or query order — invalidates
        # it, because a stale L would let best_idx exceed len(live) and IndexError (the observed crash).
        # A count-only check misses a same-size swap; keying by content is the fail-closed form (C16).
        cached_ids = data["live_ids"] if "live_ids" in data else None
        if (A.shape[0] != len(a_text) or L.shape[0] != len(live_ids)
                or cached_ids is None
                or not np.array_equal(np.asarray(cached_ids), np.asarray(live_ids))):
            print(f"cache stale (A {A.shape[0]}/{len(a_text)} anchors, "
                  f"L {L.shape[0]}/{len(live_ids)} live) — re-embedding", file=sys.stderr)
            A = L = None
    if A is None:
        t0 = time.time()
        A = norm(embed(a_text))
        L = norm(embed(l_text))
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache, A=A, L=L, live_ids=np.asarray(live_ids))
        print(f"embedded {len(a_text)}+{len(l_text)} in {time.time()-t0:.1f}s -> {cache}", file=sys.stderr)

    sim = A @ L.T  # (n_anchors, n_live)
    best_idx = sim.argmax(axis=1)
    best_sim = sim.max(axis=1)

    live_names = [r[1] for r in live]
    name_index = {norm_name(n): i for i, n in enumerate(live_names)}

    # Tentative best per anchor: an exact-name identity outranks the cosine argmax.
    best_i: list[int] = []
    tier: list[str] = []
    for k, x in enumerate(anchors):
        nn = norm_name(x["name"])
        if nn in name_index:
            best_i.append(name_index[nn])
            tier.append("exact-name")
        else:
            best_i.append(int(best_idx[k]))
            tier.append("high" if float(best_sim[k]) >= a.sim else "low")

    # D-3107 one-to-one uniqueness pass (BUG-946 root cause): a live principle may be claimed by AT MOST
    # ONE anchor. For each contended live row keep the single strongest claim (exact-name > semantic, then
    # higher cosine, then deterministic fb_id order) and demote the rest to "many-to-one" — surfaced for the
    # owner, never silently merged. This makes the PROPOSED map injective.
    claims: dict[int, list[tuple[int, float, int]]] = {}
    for k in range(len(anchors)):
        if tier[k] == "low":
            continue
        prio = EXACT_PRIORITY if tier[k] == "exact-name" else SEMANTIC_PRIORITY
        claims.setdefault(best_i[k], []).append((prio, float(best_sim[k]), k))

    losers: set[int] = set()
    for i, v in claims.items():
        v = sorted(v, key=lambda t: (-t[0], -t[1], anchors[t[2]]["fb_id"]))
        for t in v[1:]:
            losers.add(t[2])

    proposed, delta = [], []
    for k, x in enumerate(anchors):
        old = x["fb_id"]
        s = round(float(best_sim[k]), 4)
        if tier[k] == "low":
            delta.append((old, live_ids[best_i[k]], live_names[best_i[k]], s, "low"))
        elif k in losers:
            delta.append((old, live_ids[best_i[k]], live_names[best_i[k]], s, "many-to-one"))
        else:
            proposed.append((old, live_ids[best_i[k]], live_names[best_i[k]], s, tier[k]))

    # Many-to-one record (owner-adjudicated fusion candidates): contended live rows with ALL claimants
    # (winner + demoted), so the owner marks each SAME / DIFFERENT.
    merges: list[dict] = []
    for i, v in sorted(claims.items()):
        if len(v) < 2:
            continue
        v = sorted(v, key=lambda t: (-t[0], -t[1], anchors[t[2]]["fb_id"]))
        merges.append({
            "live_fb_id": live_ids[i],
            "live_name": live_names[i],
            "anchors": [
                {"old_fb_id": anchors[k]["fb_id"], "name": anchors[k]["name"],
                 "similarity": round(float(best_sim[k]), 4)}
                for _prio, _s, k in v
            ],
        })

    out_dir.mkdir(parents=True, exist_ok=True)
    map_path = out_dir / "gold_reattach_map.jsonl"
    del_path = out_dir / "gold_reattach_delta.jsonl"
    merge_path = out_dir / "gold_reattach_many_to_one.jsonl"
    map_path.write_text("\n".join(json.dumps(
        {"old_fb_id": o, "live_fb_id": li, "live_name": ln, "similarity": s, "tier": t})
        for o, li, ln, s, t in proposed) + "\n", encoding="utf-8")
    del_path.write_text("\n".join(json.dumps(
        {"old_fb_id": o, "live_fb_id": li, "live_name": ln, "similarity": s, "tier": t})
        for o, li, ln, s, t in delta) + "\n", encoding="utf-8")
    merge_path.write_text("\n".join(json.dumps(m) for m in merges) + "\n", encoding="utf-8")

    exact = sum(1 for p in proposed if p[4] == "exact-name")
    high = sum(1 for p in proposed if p[4] == "high")
    many = sum(1 for d in delta if d[4] == "many-to-one")
    print(f"anchors {len(anchors)} | proposed {len(proposed)} (exact-name {exact}, high {high}) | "
          f"delta {len(delta)} (low {len(delta)-many}, many-to-one {many}) | "
          f"merges {len(merges)} | wrote {map_path.name}, {del_path.name}, {merge_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
