#!/usr/bin/env python3
"""build_joint_vote_set.py — D2612 joint content_type + depth vote (one pass, two axes).

Why this exists
===============
D2612 scoped the 7,995-row depth relabel to the "confirmed-principle subset
(~6,600-6,900)". That number was a PROJECTION, not an identified set — production
`fbs.content_type` is 99.6% unverified `principle` (Qwen3-Coder silver), and the
measured true non-principle rate is 13-17% (BUG-238). Depth is downstream of
content_type: a depth label on a noise_drop/quarantine row is meaningless.

This script votes BOTH axes in ONE call (the models already read definition /
mechanism / boundary), so the confirmed-principle subset is IDENTIFIED (not
projected) and depth is produced in the same pass:

  * content_type = 7-way (D2587: 5 roles + 2 dispositions), reliable-pair unanimous
    else abstain.
  * depth        = 4-way (D2577), reliable-pair unanimous else abstain — but ONLY
    evaluated when the confirmed content_type is `principle` (non-principles carry
    no depth; it is forced empty).

The reliable-pair policy (D2610) is identical to build_depth_vote_set.py: reliable
voters must be unanimous; advisory voters are recorded but never decide; a label is
NEVER fabricated (abstain -> needs_review). Checkpoint is one JSON line per fb_id
(resumable — C23, upserted — BUG-234).

Usage
=====
    python3 scripts/build_joint_vote_set.py --list --limit 20
    python3 scripts/build_joint_vote_set.py --run --limit 200 --seed 42
    python3 scripts/build_joint_vote_set.py --report
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sqlite3
import ssl
import sys
import tempfile
import threading
import time
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

from pipeline.content_types import CONTENT_TYPES_ALL  # noqa: E402
from pipeline.json_fixer import parse_json_robust  # noqa: E402
from pipeline.omlx_call import (  # noqa: E402
    assert_omlx_no_cache,
    call_omlx_json,
    check_omlx_health,
    stress_test_omlx,
)
from pipeline.pipeline_paths import PIPELINE_COMMIT, SCHEMA_VERSION  # noqa: E402
from pipeline.schemas import DEPTH_LITERAL  # noqa: E402

# ── C20 named constants ──────────────────────────────────────────────────────
VALID_DEPTHS: Tuple[str, ...] = tuple(DEPTH_LITERAL.__args__)  # type: ignore[attr-defined]
CONTENT_TYPES: Tuple[str, ...] = tuple(sorted(CONTENT_TYPES_ALL))
MAX_TOKENS: int = 256
DEEPSEEK_MAX_TOKENS: int = 2048  # v4-pro burns ~315 reasoning tokens before the answer
RECOVERY_SLEEP: float = 1.0
TIMEOUT: int = 120
ABSTAIN_CT: str = ""            # policy v2: never fabricate (BUG-235)
ABSTAIN_DEPTH: str = ""
CONF_HIGH: str = "high"
CONF_LOW: str = "low"
DEPTH_NA: str = "n/a"           # depth confidence for non-principles
DEFAULT_POLICY: str = "reliable_pair_agreement"
DEFAULT_RELIABLE: Tuple[str, ...] = ("deepseek-v4-pro", "Qwen3.8-27B-MLX-4bit")
POLICY_VERSION: str = "v2"
# ── Resilience (D2612 hardening) ────────────────────────────────────────────
# DeepSeek is cloud + reasoning (v4-pro). Transient empty-content / 429 / 5xx /
# network errors MUST be retried with backoff, or they become PERMANENT poison
# (the pilot showed 6/200 empty-content rows with no recovery path — BUG-240).
DEEPSEEK_RETRIES: int = 3
DEEPSEEK_BACKOFF: float = 2.0
RETRYABLE_HTTP: frozenset[int] = frozenset({408, 429, 500, 502, 503, 504})

DB = Path(os.environ.get("MAXWELL_DB", ROOT / "knowledge pipeline" / "maxwell.db"))
OUT_CHECKPOINT = Path(os.environ.get(
    "JOINT_VOTE_CHECKPOINT", ROOT / "governance" / "joint_vote_checkpoint.jsonl"))
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

CONTENT_TYPE_ONTOLOGY: str = (
    "CONTENT_TYPE (choose EXACTLY ONE — is this a reusable principle, or not?):\n"
    "- principle        = a single transferable prescriptive claim / reusable rule (a "
    "one-sentence heuristic acting as a filter across 3+ domains, OR a deep single-domain "
    "principle). ALSO: a reusable matrix/methodology with NO explicit steps.\n"
    "- process_template = step-by-step method — needs >=2 steps AND a gate/done-condition.\n"
    "- process_instance = a specific NAMED case / execution of a method (a study, project, product).\n"
    "- tool_instruction = a command / API / feature for a specific tool or software.\n"
    "- noise_drop       = a descriptive / historical summary or fact — no prescriptive filter, "
    "no template, no named method-execution, no transferable value.\n"
    "- growth_edge      = speculative / unresolved insight — an OPEN TENSION or UNVERIFIED "
    "CORRELATION (not a dump for failed depth-tests, not a bare utilizable fact).\n"
    "- quarantine       = carries SOME value but no clean role (ambiguous) — hold.\n"
)

DEPTH_ONTOLOGY: str = (
    "DEPTH (choose EXACTLY ONE, or \"\" if content_type is NOT principle):\n"
    "- universal    = applies to ALL systems (physics, cooking, poetry)\n"
    "- cross-domain = bridges 2+ DISTINCT disciplines via a SHARED mechanism\n"
    "- domain       = operates within ONE field / a cluster of adjacent fields\n"
    "- specialized  = narrow sub-technique within a sub-field or tool-specific skill\n"
)


def _load_policy() -> Dict[str, Any]:
    """Return the D2610 label policy from config/pipeline_config.yaml (C12)."""
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


def _load_voters() -> List[Dict[str, str]]:
    cfg = yaml.safe_load((ROOT / "config" / "pipeline_config.yaml").read_text(encoding="utf-8")) or {}
    return [dict(v) for v in (cfg.get("label_vote", {}).get("models") or [])]


def select_sample(limit: int, seed: int) -> List[Dict[str, Any]]:
    """Select a seeded random sample of production `principle`-labelled rows.

    The population is the rows we would relabel: fbs WHERE content_type='principle'.
    """
    try:
        con = sqlite3.connect(str(DB))
        con.row_factory = sqlite3.Row
        ids = [r["fb_id"] for r in con.execute(
            "SELECT fb_id FROM fbs WHERE content_type='principle' AND definition IS NOT NULL "
            "ORDER BY fb_id")]
        con.close()
    except sqlite3.Error as exc:
        raise ValueError(f"Failed to query {DB}: {exc}") from exc

    rng = random.Random(seed)
    chosen = sorted(rng.sample(ids, min(limit, len(ids)))) if ids else []
    if not chosen:
        return []
    placeholders = ",".join("?" for _ in chosen)
    con = sqlite3.connect(str(DB))
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        f"SELECT fb_id, name, definition, mechanism, boundary, depth FROM fbs "
        f"WHERE fb_id IN ({placeholders}) ORDER BY fb_id", chosen)]
    con.close()
    return rows


def _joint_prompt(fb: Dict[str, Any]) -> str:
    body = (
        f"Name: {fb.get('name') or ''}\n"
        f"Definition: {fb.get('definition') or ''}\n"
        f"Mechanism: {fb.get('mechanism') or ''}\n"
        f"Boundary: {fb.get('boundary') or ''}\n"
    )
    return (
        "You are labeling a candidate Foundation Block on TWO axes and return ONLY a JSON "
        'object (no markdown, no prose): {"content_type": "...", "depth": "..."}\n\n'
        + CONTENT_TYPE_ONTOLOGY
        + "\n"
        + DEPTH_ONTOLOGY
        + "\nIf content_type is NOT principle, set depth to the empty string \"\".\n\n"
        + "FB:\n" + body
    )


def _parse_joint(raw: Any) -> Dict[str, Optional[str]]:
    if isinstance(raw, list):
        raw = raw[0] if raw else {}
    if not isinstance(raw, dict):
        return {"content_type": None, "depth": None}
    ct = str(raw.get("content_type", "")).strip().lower() if raw.get("content_type") else None
    depth = str(raw.get("depth", "")).strip().lower() if raw.get("depth") else None
    return {
        "content_type": ct if ct in CONTENT_TYPES else None,
        "depth": depth if depth in VALID_DEPTHS else ("" if depth == "" else None),
    }


def _call_deepseek(prompt: str, key: str, model: str) -> Dict[str, Optional[str]]:
    """Call DeepSeek (cloud) for a joint vote with retry + backoff.

    v4-pro is a reasoning model: it burns ~315 reasoning tokens BEFORE the final
    JSON, and occasionally returns empty `content` under `response_format:
    json_object` (the DELEGATE-001 trap). Retry empty-content / transient HTTP /
    network errors; on the final attempt, fall back to free JSON parsed by
    parse_json_robust (handles fences, trailing commas, truncation).

    Raises:
        RuntimeError: After DEEPSEEK_RETRIES exhausted (fail loud, C16).
    """
    if not key:
        raise RuntimeError("DeepSeek voter requires --key / DEEPSEEK_API_KEY (C22 opt-in)")
    ctx = ssl.create_default_context(cafile=certifi.where())
    last_err: Optional[str] = None
    for attempt in range(1, DEEPSEEK_RETRIES + 1):
        use_json_mode = attempt == 1  # first try constrained; later tries free JSON
        body = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a precise JSON-only ontology labeler."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "max_tokens": DEEPSEEK_MAX_TOKENS,
            **({"response_format": {"type": "json_object"}} if use_json_mode else {}),
        }).encode("utf-8")
        req = urllib.request.Request(
            DEEPSEEK_URL, data=body, method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in RETRYABLE_HTTP and attempt < DEEPSEEK_RETRIES:
                last_err = f"HTTP {exc.code}"
                time.sleep(DEEPSEEK_BACKOFF * attempt)
                continue
            raise RuntimeError(f"DeepSeek HTTP {exc.code}: {exc.read()[:200]!r}") from exc
        except (urllib.error.URLError, TimeoutError, ssl.SSLError) as exc:
            if attempt < DEEPSEEK_RETRIES:
                last_err = f"{type(exc).__name__}"
                time.sleep(DEEPSEEK_BACKOFF * attempt)
                continue
            raise RuntimeError(f"DeepSeek network error: {exc}") from exc

        content = (data["choices"][0]["message"].get("content") or "").strip()
        if not content:
            if attempt < DEEPSEEK_RETRIES:
                last_err = "empty content (truncated reasoning?)"
                time.sleep(DEEPSEEK_BACKOFF * attempt)
                continue
            raise RuntimeError(f"DeepSeek empty content after {DEEPSEEK_RETRIES} attempts")

        out = _parse_joint(parse_json_robust(content))
        if out.get("content_type") is not None:
            return out
        if attempt < DEEPSEEK_RETRIES:
            last_err = f"no valid content_type in {content[:80]!r}"
            time.sleep(DEEPSEEK_BACKOFF * attempt)
            continue
        raise RuntimeError(f"DeepSeek returned no valid content_type: {content[:120]!r}")
    raise RuntimeError(f"DeepSeek failed after {DEEPSEEK_RETRIES} attempts: {last_err}")


def _call_omlx(prompt: str, model: str) -> Dict[str, Optional[str]]:
    return _parse_joint(call_omlx_json(prompt, model=model, max_tokens=MAX_TOKENS))


def aggregate(votes: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    """Apply the D2610 policy to BOTH axes (pure — no calls).

    content_type: reliable unanimous -> label; else abstain.
    depth:        only meaningful when content_type == principle; reliable
                  unanimous -> label; else abstain. Non-principle -> forced "".
    """
    reliable = list(policy["reliable"])
    ct_vals = [votes.get(m, {}).get("content_type") for m in reliable
               if isinstance(votes.get(m), dict)]
    dp_vals = [votes.get(m, {}).get("depth") for m in reliable
               if isinstance(votes.get(m), dict)]

    ct_ok = [v for v in ct_vals if v in CONTENT_TYPES]
    ct_unanimous = len(ct_ok) == len(reliable) and len(set(ct_ok)) == 1

    content_type = ct_ok[0] if ct_unanimous else ABSTAIN_CT
    ct_confidence = CONF_HIGH if ct_unanimous else CONF_LOW

    if content_type == "principle":
        dp_ok = [v for v in dp_vals if v in VALID_DEPTHS]
        dp_unanimous = len(dp_ok) == len(reliable) and len(set(dp_ok)) == 1
        depth = dp_ok[0] if dp_unanimous else ABSTAIN_DEPTH
        depth_confidence = CONF_HIGH if dp_unanimous else CONF_LOW
    else:
        depth = ABSTAIN_DEPTH  # non-principle -> no depth label
        depth_confidence = DEPTH_NA

    needs_review = (not ct_unanimous) or (content_type == "principle" and depth == ABSTAIN_DEPTH)
    return {
        "content_type": content_type,
        "content_type_confidence": ct_confidence,
        "content_type_agreed": ct_unanimous,
        "depth": depth,
        "depth_confidence": depth_confidence,
        "needs_review": needs_review,
        "agreed": not needs_review,
    }


def vote_once(fb: Dict[str, Any], voters: List[Dict[str, str]], key: str,
              policy: Dict[str, Any],
              prior_votes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run every voter on one FB and apply the D2610 policy to both axes.

    prior_votes (from a checkpoint) lets --retry-failures re-vote ONLY the voters
    that errored, never re-paying a valid prior vote.
    """
    prompt = _joint_prompt(fb)
    votes: Dict[str, Any] = dict(prior_votes or {})
    for v in voters:
        model = v.get("model", "")
        provider = v.get("provider", "omlx")
        existing = votes.get(model)
        if (isinstance(existing, dict) and "error" not in existing
                and existing.get("content_type") is not None):
            continue  # keep a prior successful vote (don't re-pay)
        try:
            votes[model] = (_call_deepseek(prompt, key, model) if provider == "deepseek"
                            else _call_omlx(prompt, model))
        except Exception as exc:  # noqa: BLE001 — record per-voter failure (C16)
            votes[model] = {"error": f"{type(exc).__name__}: {exc}"}
        time.sleep(RECOVERY_SLEEP)

    verdict = aggregate(votes, policy)
    return {
        "fb_id": fb["fb_id"],
        "name": fb.get("name", ""),
        "definition": fb.get("definition", ""),
        "mechanism": fb.get("mechanism", ""),
        "boundary": fb.get("boundary", ""),
        "silver_depth": fb.get("depth", ""),
        "votes": votes,
        "policy": policy["policy"],
        "policy_version": POLICY_VERSION,
        # R14: every persistent object stamped (schema_version, gen_model, pipeline_commit)
        "schema_version": SCHEMA_VERSION,
        "gen_model": " + ".join(policy["reliable"]),
        "pipeline_commit": PIPELINE_COMMIT,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **verdict,
    }


def _all_voters_ok(prior: Dict[str, Any], voters: List[Dict[str, str]],
                   policy: Dict[str, Any]) -> bool:
    """True if every reliable voter already has a non-error, non-None vote."""
    votes = prior.get("votes") or {}
    reliable = set(policy["reliable"])
    for v in voters:
        model = v.get("model", "")
        if model not in reliable:
            continue
        vv = votes.get(model)
        if not isinstance(vv, dict) or "error" in vv or vv.get("content_type") is None:
            return False
    return True


def _atomic_write(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _load_checkpoint() -> Dict[str, Dict[str, Any]]:
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


def report(records: List[Dict[str, Any]], policy: Dict[str, Any]) -> None:
    ct = Counter((r.get("content_type") or "(abstain)") for r in records)
    print("content_type distribution:", dict(ct))
    princ = [r for r in records if r.get("content_type") == "principle"]
    dep = Counter((r.get("depth") or "(abstain)") for r in princ)
    print(f"depth distribution (among {len(princ)} principle):", dict(dep))
    print(f"needs_review: {sum(1 for r in records if r.get('needs_review'))}/{len(records)} "
          f"({100 * sum(1 for r in records if r.get('needs_review')) / max(1, len(records)):.1f}%)")
    reliable = policy["reliable"]
    if len(reliable) >= 2:
        a, b = reliable[0], reliable[1]
        ct_agree = sum(1 for r in records
                       if (r["votes"].get(a, {}).get("content_type")
                           == r["votes"].get(b, {}).get("content_type")
                           and r["votes"].get(a, {}).get("content_type") in CONTENT_TYPES))
        print(f"reliable-pair content_type agreement ({a} vs {b}): {ct_agree}/{len(records)} "
              f"({100 * ct_agree / max(1, len(records)):.1f}%)")


def preflight(key: str, deepseek_model: str, omlx_model: str) -> None:
    """Preflight checks before a long run (fail loud, C16).

    Verifies the things a full 7,995-row run depends on that a 200-row pilot can
    hide: DeepSeek key + API reachability + model acceptance + balance (a 402
    mid-run would poison every subsequent row), the OMLX cache gate (D2460 thrash
    guard), OMLX health, and a LIVE chat completion on the exact reliable voter
    (the /v1/models endpoint lies — it reports resident models, not that chat
    completions work).
    """
    print("=== PREFLIGHT ===")
    if not key:
        raise RuntimeError("preflight FAILED: no DeepSeek key (pass --key / DEEPSEEK_API_KEY)")
    # 1. DeepSeek live probe (validates model name, balance, and JSON path)
    try:
        _call_deepseek(
            'Return ONLY the JSON object: {"content_type": "principle", "depth": "domain"}',
            key, deepseek_model)
        print(f"  ✅ DeepSeek reachable + model '{deepseek_model}' accepted + JSON parse OK")
    except Exception as exc:
        raise RuntimeError(f"preflight FAILED: DeepSeek probe: {exc}") from exc
    # 2. OMLX cache gate (D2460: refuse to run if paged-SSD cache thrash is enabled)
    assert_omlx_no_cache()
    # 3. OMLX health + live chat on the reliable voter
    if not check_omlx_health():
        raise RuntimeError("preflight FAILED: OMLX /v1/models unreachable")
    st = stress_test_omlx(model=omlx_model, prompt_sizes=[50, 2000, 6000], timeout=60)
    print(f"  OMLX stress ({omlx_model}): verdict={st['verdict']}, healthy={st['healthy']}")
    if not st["healthy"]:
        raise RuntimeError(f"preflight FAILED: OMLX stress test unhealthy: {st['results']}")
    # 4. Target population (so the run size is known up front, not a surprise)
    con = sqlite3.connect(str(DB))
    n = con.execute(
        "SELECT COUNT(*) FROM fbs WHERE content_type='principle' AND definition IS NOT NULL"
    ).fetchone()[0]
    con.close()
    print(f"  ✅ target population: {n} principle-labelled rows with definition")
    print("=== PREFLIGHT PASS ===")


def main() -> int:
    ap = argparse.ArgumentParser(description="D2612 joint content_type + depth vote")
    ap.add_argument("--list", action="store_true", help="print sample and exit")
    ap.add_argument("--run", action="store_true", help="vote on the sample")
    ap.add_argument("--limit", type=int, default=200, help="sample size")
    ap.add_argument("--seed", type=int, default=42, help="sampling seed (deterministic)")
    ap.add_argument("--key", default=os.environ.get("DEEPSEEK_API_KEY", ""), help="DeepSeek API key")
    ap.add_argument("--workers", type=int, default=4, help="concurrent FBs")
    ap.add_argument("--reliable-only", action="store_true",
                    help="run only the reliable voters (skip advisory — pilot mode)")
    ap.add_argument("--retry-failures", action="store_true",
                    help="re-vote ONLY the voters that errored on already-checkpointed FBs")
    ap.add_argument("--checkpoint", default="", help="checkpoint path (default: env/…/joint_vote_checkpoint.jsonl)")
    ap.add_argument("--preflight", action="store_true", help="run preflight checks and exit (unless --run)")
    ap.add_argument("--report", action="store_true", help="report on the existing checkpoint")
    args = ap.parse_args()

    global OUT_CHECKPOINT
    if args.checkpoint:
        OUT_CHECKPOINT = Path(args.checkpoint)

    policy = _load_policy()
    print(f"policy: {policy['policy']} {POLICY_VERSION} | reliable: {policy['reliable']} | "
          f"advisory: {policy['advisory']} | content_types: {len(CONTENT_TYPES)} values")

    if args.report:
        done = _load_checkpoint()
        print(f"checkpoint: {len(done)} FBs")
        report(list(done.values()), policy)
        return 0

    voters = _load_voters()
    if args.reliable_only:
        voters = [v for v in voters if v.get("model") in set(policy["reliable"])]
    deepseek_model = next((v["model"] for v in voters if v.get("provider") == "deepseek"),
                          policy["reliable"][0])
    omlx_model = next((v["model"] for v in voters if v.get("provider") == "omlx"),
                      policy["reliable"][-1])

    if args.preflight:
        preflight(args.key, deepseek_model, omlx_model)
        if not args.run:
            return 0

    targets = select_sample(args.limit, args.seed)
    print(f"sample: {len(targets)} production principle-labelled rows (seed={args.seed})")
    if args.list:
        print("silver depth distribution:", dict(Counter(t["depth"] for t in targets)))
        return 0

    if not args.run:
        print("\nDRY-RUN — pass --run to vote.")
        return 0

    print(f"voters: {[v['model'] for v in voters]}")

    done = _load_checkpoint()
    work: List[Tuple[Dict[str, Any], Optional[Dict[str, Any]]]] = []
    for fb in targets:
        prior = done.get(fb["fb_id"])
        if prior is None:
            work.append((fb, None))
        elif args.retry_failures and not _all_voters_ok(prior, voters, policy):
            work.append((fb, prior.get("votes", {})))
    print(f"work list: {len(work)} FBs "
          f"({sum(1 for _, p in work if p is None)} new, "
          f"{sum(1 for _, p in work if p is not None)} retry; "
          f"{len(done)} already checkpointed)")

    if work:
        lock = threading.Lock()
        n = 0
        with OUT_CHECKPOINT.open("a", encoding="utf-8") as fh:
            def _handle(fb: Dict[str, Any], pv: Optional[Dict[str, Any]]) -> Dict[str, Any]:
                return vote_once(fb, voters, args.key, policy, pv)

            def _emit(rec: Dict[str, Any]) -> None:
                nonlocal n
                with lock:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    fh.flush()
                n += 1
                print(f"[{n}/{len(work)}] {rec['fb_id'][:10]} ct={rec['content_type'] or '(abstain)'} "
                      f"depth={rec['depth'] or '(none)'} review={rec['needs_review']}", flush=True)

            if args.workers > 1:
                with ThreadPoolExecutor(max_workers=args.workers) as pool:
                    futures = {pool.submit(_handle, fb, pv): fb for fb, pv in work}
                    for fut in as_completed(futures):
                        _emit(fut.result())
            else:
                for fb, pv in work:
                    _emit(_handle(fb, pv))

    records = _load_checkpoint()
    recs = list(records.values())
    print(f"\ncheckpoint: {len(recs)} unique FBs")
    report(recs, policy)

    # persist a compact evidence JSON (R14-stamped) named after the checkpoint
    # so pilot vs production artifacts never clobber each other.
    evidence = {
        "schema_version": SCHEMA_VERSION,
        "gen_model": "joint vote: " + " + ".join(policy["reliable"]),
        "pipeline_commit": PIPELINE_COMMIT,
        "created": datetime.now(timezone.utc).isoformat(),
        "policy": policy["policy"],
        "policy_version": POLICY_VERSION,
        "checkpoint": str(OUT_CHECKPOINT),
        "n": len(recs),
        "content_type_distribution": dict(Counter(r.get("content_type") or "(abstain)" for r in recs)),
        "depth_distribution_principle": dict(Counter(
            r.get("depth") or "(abstain)" for r in recs if r.get("content_type") == "principle")),
        "needs_review": sum(1 for r in recs if r.get("needs_review")),
        "voter_error_rows": sum(
            1 for r in recs
            if any(isinstance(v, dict) and "error" in v for v in (r.get("votes") or {}).values())),
    }
    evidence_path = OUT_CHECKPOINT.with_name(OUT_CHECKPOINT.stem.replace("checkpoint", "evidence") + ".json")
    _atomic_write(evidence_path, json.dumps(evidence, ensure_ascii=False, indent=1))
    print(f"wrote {evidence_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
