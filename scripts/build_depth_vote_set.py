#!/usr/bin/env python3
"""build_depth_vote_set.py — D2577: clean depth training set via 3-model vote.

The gpt-oss silver depth labels OVER-ASSIGN the rare classes (D2576: universal
~2/3 wrong, cross-domain ~4/5 wrong). The depth classifier baseline (trained on
those silver labels, macro-F1 0.4796, universal F1 0.000) is therefore
DATA-NOISE-LIMITED. Per D2577 the fix is a dedicated clean set: re-vote depth on
every universal/cross-domain FB (the over-assigned classes) plus ~200 domain/
specialized controls, keep labels where >=2/3 voters agree, fail-closed to domain.

Voters (config label_vote.models, 2026-09-10 user override):
  deepseek-v4-pro (cloud, C22 opt-in via DEEPSEEK_API_KEY / --key)
  Qwen3.8-27B-MLX-4bit (local OMLX)
  Qwen3-Coder-30B-A3B-Instruct-MLX-4bit (local OMLX, single-shot)
Phi-4-mini + gemma were ruled unreliable and REMOVED from the voter list.

Output:
  governance/depth_vote_checkpoint.jsonl  (resumable — one JSON object per FB)
  governance/depth_vote_training_set.yaml (golden-style, feeds train_depth_classifier.py
                                           via GOLDEN_YAML)

Usage:
    python3 scripts/build_depth_vote_set.py --list            # show target set
    python3 scripts/build_depth_vote_set.py --run --limit 20  # vote on 20 FBs
    python3 scripts/build_depth_vote_set.py --run             # vote on all targets
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import ssl
import sys
import tempfile
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import certifi
import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.omlx_call import call_omlx_json  # noqa: E402
from pipeline.pipeline_paths import PIPELINE_COMMIT, SCHEMA_VERSION  # noqa: E402
from pipeline.schemas import DEPTH_LITERAL  # noqa: E402

# ── C20 named constants ──────────────────────────────────────────────────────
VALID_DEPTHS: Tuple[str, ...] = tuple(DEPTH_LITERAL.__args__)  # type: ignore[attr-defined]
MAJORITY_THRESHOLD: int = 2          # >=2 of 3 voters agree (D2577)
FAIL_CLOSED_DEPTH: str = "domain"    # disagreement -> conservative domain (D2577)
CONTROL_DOMAIN: int = 100            # domain controls to sample
CONTROL_SPECIALIZED: int = 100       # specialized controls to sample
MAX_TOKENS: int = 256
RECOVERY_SLEEP: float = 1.0
TIMEOUT: int = 120

DB = Path(os.environ.get("MAXWELL_DB", ROOT / "knowledge pipeline" / "maxwell.db"))
OUT_CHECKPOINT = ROOT / "governance" / "depth_vote_checkpoint.jsonl"
OUT_TRAINING = ROOT / "governance" / "depth_vote_training_set.yaml"

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

DEPTH_ONTOLOGY: str = (
    "DEPTH (choose EXACTLY ONE):\n"
    "- universal    = applies to ALL systems (physics, cooking, poetry)\n"
    "- cross-domain = bridges 2+ DISTINCT disciplines via a SHARED mechanism\n"
    "- domain       = operates within ONE field / a cluster of adjacent fields\n"
    "- specialized  = narrow sub-technique within a sub-field or tool-specific skill\n"
)


def _load_voters() -> List[Dict[str, str]]:
    """Return the configured voter list from config/pipeline_config.yaml (C12)."""
    cfg = yaml.safe_load((ROOT / "config" / "pipeline_config.yaml").read_text(encoding="utf-8")) or {}
    return [dict(v) for v in (cfg.get("label_vote", {}).get("models") or [])]


def select_targets(limit: int = 0) -> List[Dict[str, Any]]:
    """Select the depth-vote target set from the DB.

    All universal + cross-domain FBs (the over-assigned rare classes) plus
    `CONTROL_DOMAIN` + `CONTROL_SPECIALIZED` deterministic controls.

    Args:
        limit: Cap the returned list (0 = all). Deterministic ordering.

    Returns:
        Flat rows {fb_id, name, definition, mechanism, boundary, depth}.
    """
    try:
        con = sqlite3.connect(str(DB))
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        rare = cur.execute(
            "SELECT fb_id, name, definition, mechanism, boundary, depth FROM fbs "
            "WHERE depth IN ('universal','cross-domain') AND definition IS NOT NULL "
            "ORDER BY fb_id"
        ).fetchall()
        dom = cur.execute(
            "SELECT fb_id, name, definition, mechanism, boundary, depth FROM fbs "
            "WHERE depth='domain' AND definition IS NOT NULL "
            "ORDER BY fb_id LIMIT ?", (CONTROL_DOMAIN,)
        ).fetchall()
        spec = cur.execute(
            "SELECT fb_id, name, definition, mechanism, boundary, depth FROM fbs "
            "WHERE depth='specialized' AND definition IS NOT NULL "
            "ORDER BY fb_id LIMIT ?", (CONTROL_SPECIALIZED,)
        ).fetchall()
        con.close()
    except sqlite3.Error as exc:
        raise ValueError(f"Failed to query {DB}: {exc}") from exc

    rows = [dict(r) for r in (rare + dom + spec)]
    if limit:
        rows = rows[:limit]
    return rows


def _depth_prompt(fb: Dict[str, Any]) -> str:
    """Build a depth-only single-FB label prompt."""
    body = (
        f"Name: {fb.get('name') or ''}\n"
        f"Definition: {fb.get('definition') or ''}\n"
        f"Mechanism: {fb.get('mechanism') or ''}\n"
        f"Boundary: {fb.get('boundary') or ''}\n"
    )
    return (
        "You are labeling the ontological DEPTH of a Foundation Block (a reusable "
        "design principle). Assign EXACTLY ONE depth and return ONLY a JSON object "
        '(no markdown, no prose): {"depth": "..."}\n\n'
        + DEPTH_ONTOLOGY
        + "\nFB:\n" + body
    )


def _parse_depth(raw: Any) -> Optional[str]:
    """Normalize a voter's output to a canonical depth or None (unmappable)."""
    if isinstance(raw, list):
        raw = raw[0] if raw else {}
    if not isinstance(raw, dict):
        return None
    depth = str(raw.get("depth", "")).strip().lower() if raw.get("depth") else None
    return depth if depth in VALID_DEPTHS else None


def _call_deepseek(prompt: str, key: str, model: str) -> Optional[str]:
    """Call DeepSeek (cloud) for a single-FB depth vote; return canonical depth or None.

    Raises:
        RuntimeError: On a non-2xx response or missing key (fail loud — C16).
    """
    if not key:
        raise RuntimeError("DeepSeek voter requires --key / DEEPSEEK_API_KEY (C22 opt-in)")
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a precise JSON-only ontology labeler."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    ctx = ssl.create_default_context(cafile=certifi.where())
    req = urllib.request.Request(
        DEEPSEEK_URL, data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"DeepSeek HTTP {exc.code}: {exc.read()[:200]!r}") from exc
    content = data["choices"][0]["message"]["content"]
    try:
        return _parse_depth(json.loads(content))
    except json.JSONDecodeError:
        return _parse_depth(content)


def _call_omlx(prompt: str, model: str) -> Optional[str]:
    """Call a local OMLX voter; return canonical depth or None."""
    return _parse_depth(call_omlx_json(prompt, model=model, max_tokens=MAX_TOKENS))


def vote_once(fb: Dict[str, Any], voters: List[Dict[str, str]], key: str) -> Dict[str, Any]:
    """Run all voters on one FB and aggregate depth (>=2/3, fail-closed to domain).

    Args:
        fb: Target FB row.
        voters: Configured voters [{model, provider}].
        key: DeepSeek API key (empty string disables the deepseek provider).

    Returns:
        Record {fb_id, votes: {model: depth}, depth, agreed, n_voters}.
    """
    prompt = _depth_prompt(fb)
    votes: Dict[str, Optional[str]] = {}
    for v in voters:
        model = v.get("model", "")
        provider = v.get("provider", "omlx")
        try:
            if provider == "deepseek":
                votes[model] = _call_deepseek(prompt, key, model)
            else:
                votes[model] = _call_omlx(prompt, model)
        except Exception as exc:  # noqa: BLE001 — record per-voter failure, never silent (C16)
            votes[model] = f"__ERROR__:{exc}"

    valid = [d for d in votes.values() if isinstance(d, str) and d in VALID_DEPTHS]
    counts = Counter(valid)
    (winner, top_count) = counts.most_common(1)[0] if counts else ("", 0)
    agreed = top_count >= MAJORITY_THRESHOLD
    depth = winner if agreed else FAIL_CLOSED_DEPTH
    return {
        "fb_id": fb["fb_id"],
        "name": fb.get("name", ""),
        "definition": fb.get("definition", ""),
        "mechanism": fb.get("mechanism", ""),
        "boundary": fb.get("boundary", ""),
        "silver_depth": fb.get("depth", ""),
        "votes": votes,
        "depth": depth,
        "agreed": bool(agreed),
        "n_voters": len(valid),
    }


def _load_checkpoint() -> Dict[str, Dict[str, Any]]:
    """Load prior records keyed by fb_id (resumable — C23)."""
    if not OUT_CHECKPOINT.exists():
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for line in OUT_CHECKPOINT.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            out[rec["fb_id"]] = rec
        except (json.JSONDecodeError, KeyError):
            continue
    return out


def _atomic_write(path: Path, text: str) -> None:
    """Crash-safe atomic write (C6)."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def to_training_yaml(records: List[Dict[str, Any]]) -> str:
    """Render voted records as a golden-style YAML for train_depth_classifier.py."""
    examples = []
    for r in records:
        examples.append({
            "id": r["fb_id"],
            "input_fb": {
                "name": r.get("name", ""),
                "definition": r.get("definition", ""),
                "mechanism": r.get("mechanism", ""),
                "boundary": r.get("boundary", ""),
            },
            "expected_classification": {"depth": r["depth"]},
        })
    manifest = {
        "meta": {
            "source": "depth_vote_set (D2577 clean set)",
            "voters": [m for m in {k for rec in records for k in rec.get("votes", {})}],
            "majority_threshold": MAJORITY_THRESHOLD,
            "fail_closed_depth": FAIL_CLOSED_DEPTH,
            "n_examples": len(examples),
            # R14 stamps.
            "schema_version": SCHEMA_VERSION,
            "gen_model": "3-model-vote (deepseek-v4-pro + Qwen3.8-27B + Qwen3-Coder-30B)",
            "pipeline_commit": PIPELINE_COMMIT,
            "created": datetime.now(timezone.utc).isoformat(),
        },
        "examples": examples,
    }
    return yaml.safe_dump(manifest, sort_keys=False, default_flow_style=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="print target set and exit")
    ap.add_argument("--run", action="store_true", help="vote on the target set")
    ap.add_argument("--limit", type=int, default=0, help="cap target FBs (0 = all)")
    ap.add_argument("--key", default=os.environ.get("DEEPSEEK_API_KEY", ""), help="DeepSeek API key")
    ap.add_argument("--voters", default="", help="comma-separated model names (default: config)")
    args = ap.parse_args()

    targets = select_targets(args.limit)
    print(f"target set: {len(targets)} FBs "
          f"(universal/cross-domain + {CONTROL_DOMAIN} domain + {CONTROL_SPECIALIZED} specialized controls)")

    if args.list:
        c = Counter(t["depth"] for t in targets)
        print("silver depth distribution:", dict(c))
        return 0

    if not args.run:
        print("\nDRY-RUN — pass --run to vote (or --list to inspect).")
        return 0

    voters = _load_voters()
    if args.voters:
        names = {n.strip() for n in args.voters.split(",") if n.strip()}
        voters = [v for v in voters if v.get("model") in names]
    print(f"voters: {[v['model'] for v in voters]}")

    done = _load_checkpoint()
    with OUT_CHECKPOINT.open("a", encoding="utf-8") as fh:
        for i, fb in enumerate(targets):
            if fb["fb_id"] in done:
                continue
            rec = vote_once(fb, voters, args.key)
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            print(f"[{i + 1}/{len(targets)}] {fb['fb_id']} silver={fb['depth']} "
                  f"-> {rec['depth']} (agreed={rec['agreed']}, n={rec['n_voters']})",
                  flush=True)

    records = list(_load_checkpoint().values())
    agreed = sum(1 for r in records if r["agreed"])
    print(f"\ndone: {len(records)} voted, {agreed} agreed (>=2/3), "
          f"{len(records) - agreed} fail-closed to {FAIL_CLOSED_DEPTH}")
    final_depth = Counter(r["depth"] for r in records)
    print("final depth distribution:", dict(final_depth))

    _atomic_write(OUT_TRAINING, to_training_yaml(records))
    print(f"wrote {OUT_TRAINING.name} ({len(records)} examples)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
