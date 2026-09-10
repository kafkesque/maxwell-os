#!/usr/bin/env python3
"""build_depth_vote_set.py — D2577/D2610: clean depth label set via a reliable-pair vote.

The gpt-oss silver depth labels OVER-ASSIGN the rare classes (D2576: universal
~2/3 wrong, cross-domain ~4/5 wrong). A 3-model majority vote was the first fix
(D2577), but measurement (D2610, 2026-09-10) showed the 3rd voter is NOT a
tie-breaker but a coin flip:

  * DeepSeek-v4-pro vs Qwen3.8-27B agree on 678/982 = 69.0% of co-voted FBs
  * Qwen3-Coder-30B matches that reliable-pair consensus on only 303/678 = 44.7%,
    and because 2-of-3 wins it can never overturn the pair — it only DECIDES the
    304 rows where the pair disagrees (the hardest 31%). Those "2/3 majorities"
    are coin flips.
  * fail-closed-to-`domain` fabricated a label for the 8.1% of FBs with no
    majority, injecting error straight into the default class (the encoder scores
    0.300 accuracy on exactly those rows).

POLICY v2 (config label_vote, D2610):
  1. reliable voters must be UNANIMOUS — agreement -> label + depth_confidence: high
  2. no agreement / missing voter -> ABSTAIN: depth "" + depth_confidence: low +
     needs_review: true. A fabricated label is never written (C16 spirit).
  3. advisory voters are recorded for the audit trail but never decide the label.
  4. the checkpoint is upserted (one record per fb_id), never appended twice (BUG-234).

Outputs:
  governance/depth_vote_checkpoint.jsonl  (resumable, deduplicated — C23/C6)
  governance/depth_vote_training_set.yaml (confident labels only -> train_depth_classifier.py)
  governance/depth_review_queue.yaml      (abstained FBs for adjudication)

Usage:
    python3 scripts/build_depth_vote_set.py --list             # show target set
    python3 scripts/build_depth_vote_set.py --run              # vote (resumable)
    python3 scripts/build_depth_vote_set.py --retry-failures   # re-vote errored voters only
    python3 scripts/build_depth_vote_set.py --rederive         # re-apply the policy to stored votes (NO calls)
    python3 scripts/build_depth_vote_set.py --report           # voter reliability vs the consensus
    python3 scripts/build_depth_vote_set.py --compact          # rewrite the checkpoint deduplicated
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import ssl
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
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
CONTROL_DOMAIN: int = 100            # domain controls to sample
CONTROL_SPECIALIZED: int = 100       # specialized controls to sample
MAX_TOKENS: int = 256
DEEPSEEK_MAX_TOKENS: int = 2048   # v4-pro burns ~315 reasoning tokens before the 8-token answer
RECOVERY_SLEEP: float = 1.0
TIMEOUT: int = 120
DEFAULT_WORKERS: int = 6          # network-bound DeepSeek retry: concurrent calls
ABSTAIN_DEPTH: str = ""           # policy v2: never fabricate a label (BUG-235)
CONF_HIGH: str = "high"
CONF_LOW: str = "low"
DEFAULT_POLICY: str = "reliable_pair_agreement"
DEFAULT_RELIABLE: Tuple[str, ...] = ("deepseek-v4-pro", "Qwen3.8-27B-MLX-4bit")
POLICY_VERSION: str = "v2"        # D2610

DB = Path(os.environ.get("MAXWELL_DB", ROOT / "knowledge pipeline" / "maxwell.db"))
OUT_CHECKPOINT = Path(os.environ.get("DEPTH_VOTE_CHECKPOINT", ROOT / "governance" / "depth_vote_checkpoint.jsonl"))
OUT_TRAINING = Path(os.environ.get("DEPTH_VOTE_TRAINING", ROOT / "governance" / "depth_vote_training_set.yaml"))
OUT_REVIEW = Path(os.environ.get("DEPTH_VOTE_REVIEW", ROOT / "governance" / "depth_review_queue.yaml"))

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


def _load_policy() -> Dict[str, Any]:
    """Return the D2610 label policy from config/pipeline_config.yaml (C12).

    Returns:
        {policy, reliable: [model...], advisory: [model...], abstain: bool}.

    Raises:
        ValueError: if the reliable-voter list is empty (fail loud — a vote with no
            reliable voter would silently abstain on every FB).
    """
    cfg = yaml.safe_load((ROOT / "config" / "pipeline_config.yaml").read_text(encoding="utf-8")) or {}
    lv = cfg.get("label_vote", {}) or {}
    reliable = [str(m) for m in (lv.get("reliable_voters") or list(DEFAULT_RELIABLE))]
    advisory = [str(m) for m in (lv.get("advisory_voters") or [])]
    if not reliable:
        raise ValueError("label_vote.reliable_voters is empty — refusing to run (C16)")
    return {
        "policy": str(lv.get("policy", DEFAULT_POLICY)),
        "reliable": reliable,
        "advisory": advisory,
        "abstain": bool(lv.get("abstain_on_disagreement", True)),
    }


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
        "max_tokens": DEEPSEEK_MAX_TOKENS,  # headroom for v4-pro reasoning_content + final JSON
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
    msg = data["choices"][0]["message"]
    # v4-pro emits chain-of-thought in `reasoning_content` and the FINAL answer in
    # `content`. Parse ONLY `content` (never CoT — that is the DELEGATE-001 trap).
    content = (msg.get("content") or "").strip()
    if not content:
        raise RuntimeError("DeepSeek returned empty content (truncated reasoning?)")
    try:
        return _parse_depth(json.loads(content))
    except json.JSONDecodeError:
        return _parse_depth(content)


def _call_omlx(prompt: str, model: str) -> Optional[str]:
    """Call a local OMLX voter; return canonical depth or None."""
    return _parse_depth(call_omlx_json(prompt, model=model, max_tokens=MAX_TOKENS))


def aggregate(votes: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    """Apply the D2610 policy to a per-model vote map (pure — no calls).

    Rule: every reliable voter must have voted and they must be UNANIMOUS.
    Anything else abstains (depth "", confidence low, needs_review) — the labeler
    never fabricates a value, and advisory voters never decide (BUG-235/236).

    Args:
        votes: {model_name: canonical depth | "__ERROR__:..."}.
        policy: output of `_load_policy()`.

    Returns:
        {depth, depth_confidence, needs_review, agreed, n_reliable_ok, consensus}.
    """
    reliable = list(policy["reliable"])
    got = {m: votes.get(m) for m in reliable}
    ok = [d for d in got.values() if isinstance(d, str) and d in VALID_DEPTHS]
    unanimous = len(ok) == len(reliable) and len(set(ok)) == 1
    if unanimous:
        return {"depth": ok[0], "depth_confidence": CONF_HIGH, "needs_review": False,
                "agreed": True, "n_reliable_ok": len(ok), "consensus": ok[0]}
    if not policy.get("abstain", True):
        raise ValueError("policy abstain disabled but no reliable consensus (C16)")
    return {"depth": ABSTAIN_DEPTH, "depth_confidence": CONF_LOW, "needs_review": True,
            "agreed": False, "n_reliable_ok": len(ok), "consensus": ""}


def vote_once(fb: Dict[str, Any], voters: List[Dict[str, str]], key: str,
              policy: Dict[str, Any],
              prior_votes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run every voter on one FB and apply the D2610 policy.

    Args:
        fb: Target FB row.
        voters: Configured voters [{model, provider}].
        key: DeepSeek API key (empty string disables the deepseek provider).
        policy: Output of `_load_policy()`.
        prior_votes: Optional prior per-model votes; a voter with a valid prior
            vote is NOT re-called (used by --retry-failures to re-vote only the
            voters that errored).

    Returns:
        Record {fb_id, ..., votes, depth, depth_confidence, needs_review, agreed,
        n_voters, policy, policy_version}.
    """
    prompt = _depth_prompt(fb)
    votes: Dict[str, Any] = dict(prior_votes or {})
    for v in voters:
        model = v.get("model", "")
        provider = v.get("provider", "omlx")
        existing = votes.get(model)
        if isinstance(existing, str) and existing in VALID_DEPTHS:
            continue  # keep the prior successful vote (don't re-pay)
        try:
            if provider == "deepseek":
                votes[model] = _call_deepseek(prompt, key, model)
            else:
                votes[model] = _call_omlx(prompt, model)
        except Exception as exc:  # noqa: BLE001 — record per-voter failure, never silent (C16)
            votes[model] = f"__ERROR__:{exc}"

    verdict = aggregate(votes, policy)
    return {
        "fb_id": fb["fb_id"],
        "name": fb.get("name", ""),
        "definition": fb.get("definition", ""),
        "mechanism": fb.get("mechanism", ""),
        "boundary": fb.get("boundary", ""),
        "silver_depth": fb.get("depth", ""),
        "votes": votes,
        "n_voters": len([d for d in votes.values() if isinstance(d, str) and d in VALID_DEPTHS]),
        "policy": policy["policy"],
        "policy_version": POLICY_VERSION,
        **verdict,
    }


def rederive(rec: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    """Re-apply the current policy to a checkpointed record (no model calls).

    Args:
        rec: A checkpoint record (must carry the original per-model `votes`).
        policy: Output of `_load_policy()`.

    Returns:
        The record with depth/confidence/flags recomputed by the current policy.
    """
    votes = rec.get("votes") or {}
    out = dict(rec)
    out["n_voters"] = len([d for d in votes.values() if isinstance(d, str) and d in VALID_DEPTHS])
    out["policy"] = policy["policy"]
    out["policy_version"] = POLICY_VERSION
    out.update(aggregate(votes, policy))
    return out


def _all_voters_ok(rec: Dict[str, Any], voters: List[Dict[str, str]]) -> bool:
    """True if every configured voter produced a valid depth in this record."""
    votes = rec.get("votes", {})
    for v in voters:
        d = votes.get(v.get("model", ""))
        if not (isinstance(d, str) and d in VALID_DEPTHS):
            return False
    return True


def _load_checkpoint() -> Dict[str, Dict[str, Any]]:
    """Load prior records keyed by fb_id (resumable — C23). Later lines win."""
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


def save_checkpoint(records: Dict[str, Dict[str, Any]]) -> int:
    """Rewrite the checkpoint as one JSON line per fb_id (upsert — BUG-234).

    Args:
        records: {fb_id: record}.

    Returns:
        Number of records written.
    """
    body = "\n".join(json.dumps(records[k], ensure_ascii=False) for k in sorted(records))
    _atomic_write(OUT_CHECKPOINT, body + "\n")
    return len(records)


def confirmed(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter to records carrying a confident (non-abstained) depth label."""
    return [r for r in records if r.get("depth") in VALID_DEPTHS]


def to_training_yaml(records: List[Dict[str, Any]], policy: Dict[str, Any]) -> str:
    """Render the CONFIRMED records as a golden-style YAML for the depth trainer.

    Abstained records are NOT written here (they carry no label) — they go to the
    review queue instead (D2610).
    """
    ok = confirmed(records)
    examples = []
    for r in ok:
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
            "source": "depth_vote_set (D2577 clean set, D2610 reliable-pair policy)",
            "policy": policy["policy"],
            "policy_version": POLICY_VERSION,
            "reliable_voters": policy["reliable"],
            "advisory_voters": policy["advisory"],
            "abstain_on_disagreement": policy["abstain"],
            "n_examples": len(examples),
            "n_abstained": len(records) - len(examples),
            # R14 stamps.
            "schema_version": SCHEMA_VERSION,
            "gen_model": "vote: " + " + ".join(policy["reliable"]),
            "pipeline_commit": PIPELINE_COMMIT,
            "created": datetime.now(timezone.utc).isoformat(),
        },
        "examples": examples,
    }
    return yaml.safe_dump(manifest, sort_keys=False, default_flow_style=False, allow_unicode=True)


def to_review_yaml(records: List[Dict[str, Any]], policy: Dict[str, Any]) -> str:
    """Render the abstained records as an adjudication queue (D2610, BUG-235)."""
    rows = [r for r in records if r.get("needs_review")]
    examples = []
    for r in rows:
        examples.append({
            "id": r["fb_id"],
            "input_fb": {
                "name": r.get("name", ""),
                "definition": r.get("definition", ""),
                "mechanism": r.get("mechanism", ""),
                "boundary": r.get("boundary", ""),
            },
            "silver_depth": r.get("silver_depth", ""),
            "votes": r.get("votes", {}),
            "reason": "no reliable-voter consensus (D2610 abstain)",
        })
    manifest = {
        "meta": {
            "source": "depth_vote review queue (D2610)",
            "policy": policy["policy"],
            "policy_version": POLICY_VERSION,
            "n_examples": len(examples),
            "schema_version": SCHEMA_VERSION,
            "gen_model": "vote: " + " + ".join(policy["reliable"]),
            "pipeline_commit": PIPELINE_COMMIT,
            "created": datetime.now(timezone.utc).isoformat(),
        },
        "examples": examples,
    }
    return yaml.safe_dump(manifest, sort_keys=False, default_flow_style=False, allow_unicode=True)


def report(records: List[Dict[str, Any]], policy: Dict[str, Any]) -> None:
    """Print voter reliability vs the reliable-pair consensus (governance evidence)."""
    reliable = policy["reliable"]
    recs = [r for r in records if all(
        isinstance((r.get("votes") or {}).get(m), str) and (r.get("votes") or {}).get(m) in VALID_DEPTHS
        for m in reliable)]
    print(f"rows with all reliable voters: {len(recs)}/{len(records)}")
    if len(reliable) >= 2:
        a, b = reliable[0], reliable[1]
        agree = [r for r in recs if (r["votes"] or {}).get(a) == (r["votes"] or {}).get(b)]
        print(f"reliable-pair agreement ({a} vs {b}): {len(agree)}/{len(recs)} "
              f"({100 * len(agree) / max(1, len(recs)):.1f}%)")
    for m in policy["advisory"] + reliable:
        n = sum(1 for r in records if (r.get("votes") or {}).get(m) in VALID_DEPTHS)
        if not n:
            print(f"  {m}: no votes")
            continue
        match = sum(1 for r in records if (r.get('votes') or {}).get(m) in VALID_DEPTHS
                    and (r.get('votes') or {}).get(m) == r.get("consensus"))
        role = "advisory" if m in policy["advisory"] else "reliable"
        print(f"  {m} [{role}]: {n} votes, {match} match the reliable consensus "
              f"({100 * match / n:.1f}%)")
    c = Counter(r.get("depth") or "(abstain)" for r in records)
    print("policy outcome distribution:", dict(c))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="print target set and exit")
    ap.add_argument("--run", action="store_true", help="vote on the target set")
    ap.add_argument("--limit", type=int, default=0, help="cap target FBs (0 = all)")
    ap.add_argument("--key", default=os.environ.get("DEEPSEEK_API_KEY", ""), help="DeepSeek API key")
    ap.add_argument("--voters", default="", help="comma-separated model names (default: config)")
    ap.add_argument("--retry-failures", action="store_true",
                    help="re-vote ONLY the voters that errored on already-checkpointed FBs")
    ap.add_argument("--rederive", action="store_true",
                    help="re-apply the current policy to stored votes (no model calls)")
    ap.add_argument("--report", action="store_true", help="voter reliability vs the consensus")
    ap.add_argument("--compact", action="store_true", help="rewrite the checkpoint deduplicated")
    ap.add_argument("--workers", type=int, default=1, help="concurrent FBs (network-bound)")
    args = ap.parse_args()

    policy = _load_policy()
    print(f"policy: {policy['policy']} {POLICY_VERSION} | reliable: {policy['reliable']} | "
          f"advisory: {policy['advisory']} | abstain_on_disagreement: {policy['abstain']}")
    done = _load_checkpoint()

    if args.report:
        n = save_checkpoint(done)
        print(f"checkpoint: {n} unique FBs")
        report(list(done.values()), policy)
        return 0

    if args.rederive:
        if not done:
            raise RuntimeError(f"no checkpoint at {OUT_CHECKPOINT} to re-derive (C16)")
        records = {k: rederive(v, policy) for k, v in done.items()}
        n = save_checkpoint(records)
        recs = list(records.values())
        ok = confirmed(recs)
        _atomic_write(OUT_TRAINING, to_training_yaml(recs, policy))
        _atomic_write(OUT_REVIEW, to_review_yaml(recs, policy))
        print(f"re-derived {n} records under {policy['policy']} {POLICY_VERSION}: "
              f"{len(ok)} confirmed / {len(recs) - len(ok)} abstained -> review queue")
        print("confirmed depth distribution:", dict(Counter(r['depth'] for r in ok)))
        print(f"wrote {OUT_TRAINING.name} + {OUT_REVIEW.name}")
        report(recs, policy)
        return 0

    if args.compact:
        n = save_checkpoint(done)
        print(f"compacted checkpoint: {n} unique FBs")
        return 0

    targets = select_targets(args.limit)
    print(f"target set: {len(targets)} FBs "
          f"(universal/cross-domain + {CONTROL_DOMAIN} domain + {CONTROL_SPECIALIZED} specialized controls)")

    if args.list:
        print("silver depth distribution:", dict(Counter(t["depth"] for t in targets)))
        return 0

    if not args.run:
        print("\nDRY-RUN — pass --run to vote (or --list to inspect).")
        return 0

    voters = _load_voters()
    if args.voters:
        names = {n.strip() for n in args.voters.split(",") if n.strip()}
        voters = [v for v in voters if v.get("model") in names]
    print(f"voters: {[v['model'] for v in voters]}")

    # Build the work list: new FBs, plus (in retry mode) FBs missing any voter.
    work: List[Tuple[Dict[str, Any], Optional[Dict[str, Any]]]] = []
    for fb in targets:
        prior = done.get(fb["fb_id"])
        if prior is None:
            work.append((fb, None))
        elif args.retry_failures and not _all_voters_ok(prior, voters):
            work.append((fb, prior.get("votes", {})))
    print(f"work list: {len(work)} FBs "
          f"({sum(1 for _, p in work if p is None)} new, "
          f"{sum(1 for _, p in work if p is not None)} retry)")

    if not work:
        print("nothing to do — all voters complete.")
    else:
        write_lock = threading.Lock()
        done_count = 0
        with OUT_CHECKPOINT.open("a", encoding="utf-8") as fh:
            def _handle(fb: Dict[str, Any], prior_votes: Optional[Dict[str, Any]]) -> Dict[str, Any]:
                return vote_once(fb, voters, args.key, policy, prior_votes)

            def _emit(rec: Dict[str, Any]) -> None:
                nonlocal done_count
                with write_lock:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    fh.flush()
                done_count += 1
                print(f"[{done_count}/{len(work)}] {rec['fb_id'][:10]} "
                      f"-> {rec['depth'] or '(abstain)'} (confidence={rec['depth_confidence']}, "
                      f"n={rec['n_voters']})", flush=True)

            if args.workers > 1:
                with ThreadPoolExecutor(max_workers=args.workers) as pool:
                    futures = {pool.submit(_handle, fb, pv): fb for fb, pv in work}
                    for fut in as_completed(futures):
                        _emit(fut.result())
            else:
                for fb, pv in work:
                    _emit(_handle(fb, pv))

    # Compact (upsert) after every run so the checkpoint never accumulates
    # duplicate records (BUG-234).
    records = _load_checkpoint()
    n = save_checkpoint(records)
    recs = list(records.values())
    ok = confirmed(recs)
    print(f"\ncheckpoint compacted: {n} unique FBs | {len(ok)} confirmed, "
          f"{len(recs) - len(ok)} abstained ({100 * (len(recs) - len(ok)) / max(1, len(recs)):.1f}%)")
    print("confirmed depth distribution:", dict(Counter(r["depth"] for r in ok)))
    report(recs, policy)

    _atomic_write(OUT_TRAINING, to_training_yaml(recs, policy))
    _atomic_write(OUT_REVIEW, to_review_yaml(recs, policy))
    print(f"wrote {OUT_TRAINING.name} ({len(ok)} examples) + {OUT_REVIEW.name} "
          f"({len(recs) - len(ok)} to adjudicate)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
