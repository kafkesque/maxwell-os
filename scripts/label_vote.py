#!/usr/bin/env python3
"""scripts/label_vote.py — 3-model label vote (D2577 + D2580). RETIRED TO SPOT-CHECK (P6).

RETIRED (D2585 P6, 2026-09-06): the full-corpus 3-model vote is SUPERSEDED as the
label-quality solution by the weak-supervision label model (Dawid-Skene over
{T-NLI + cleanlab + limited generative challenger} LFs -> ModernBERT classifier).
This script's only remaining role is OCCASIONAL SPOT-CHECKS on small target sets
(e.g. a human wants a 3-model second opinion on a handful of FBs). Do NOT run it
full-corpus as a label-quality gate.

The P3 challenger run (135 high-suspicion FBs) has already completed; its output
(`temp/label_vote_high_suspicion.jsonl`) is consumed by `build_label_model.py`.

Purpose
=======
For each FB in a target set, ask THREE INDEPENDENT (cross-family) models to
independently assign ``(discipline, domains, depth)``, then aggregate via
majority vote (>= ``label_vote.majority_threshold`` of 3 agree), failing CLOSED
on disagreement. Per D2580 the aggregation must also FLAG:

  (a) MISSING close domains  — a voter proposes a domain that is absent from the
      FB's current domain set (a candidate omission error);
  (b) CATCH-ALL disciplines   — the winning discipline is a catch-all such as
      ``interdisciplinary studies`` (25 FBs) that should resolve to a specific
      field.

Model independence (R5)
=======================
The three voters MUST be cross-family and MUST NOT include ``gpt-oss-20b`` — the
S4 teacher whose silver labels this vote exists to VERIFY (voting with the
teacher is circular). D2577 specified Qwen3.8-27B + DeepSeek-v4-pro + gemma;
DeepSeek-v4-pro is CLOUD (violates C1 $0-marginal-cost + C3 sovereignty) and
carries the DELEGATE-001 ``reasoning_content`` passthrough bug, so the DEFAULT
third voter is Phi-4-mini-instruct-8bit (local). The voter list is config-driven
(``config/pipeline_config.yaml`` → ``label_vote.models``) — C12, no hardcoding.

BUG-224 (workload shaping)
==========================
ONE FB per call (no batching) with a short ``recovery_sleep_seconds`` between
calls; the wedge-recovery added in D2581 (``omlx_call`` read-timeout +
recovery sleep) handles the rest. Output is a checkpointed, crash-safe JSONL
sidecar — resumable by ``fb_id`` (C23/C6).

Usage
=====
    python3 scripts/label_vote.py                     # dry-run: list target FBs
    python3 scripts/label_vote.py --run --limit 10    # vote on 10 FBs
    python3 scripts/label_vote.py --run --where "depth='universal'" --output temp/vote.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import yaml  # noqa: E402

from pipeline.omlx_call import call_omlx_json  # noqa: E402
from pipeline.pipeline_paths import DB_PATH, MAX_DOMAINS_PER_FB  # noqa: E402
from pipeline.model_lazyload import PINNED_MODELS, unload_model  # noqa: E402
from pipeline.schemas import CANONICAL_DISCIPLINES, CANONICAL_DOMAINS  # noqa: E402

# ── Config (C12: no hardcoding — all from pipeline_config.yaml) ──────────
_CFG = yaml.safe_load((_ROOT / "config" / "pipeline_config.yaml").read_text())
_VOTE = _CFG.get("label_vote", {})

VOTERS: list[dict[str, str]] = _VOTE.get("models", [])
MAJORITY_THRESHOLD: int = int(_VOTE.get("majority_threshold", 2))
FAIL_CLOSED_DISCIPLINE: str = _VOTE.get("fail_closed_discipline", "emerging")
FAIL_CLOSED_DEPTH: str = _VOTE.get("fail_closed_depth", "domain")
CATCH_ALL_DISCIPLINES: set[str] = {str(d) for d in _VOTE.get("catch_all_disciplines", [])}

# D2610 LABEL POLICY v2 (2026-09-10): the reliable voters must be UNANIMOUS to
# produce a label; anything else ABSTAINS (empty + needs_review) instead of
# fabricating a fail-closed label (BUG-235/236). Advisory voters are recorded
# for the audit trail but never decide. Supersedes the legacy 2-of-3 majority.
RELIABLE_VOTERS: list[str] = [str(v) for v in _VOTE.get("reliable_voters", [])]
ADVISORY_VOTERS: list[str] = [str(v) for v in _VOTE.get("advisory_voters", [])]
POLICY: str = str(_VOTE.get("policy", "reliable_pair_agreement"))
ABSTAIN_ON_DISAGREEMENT: bool = bool(_VOTE.get("abstain_on_disagreement", True))
RECOVERY_SLEEP: float = float(_VOTE.get("recovery_sleep_seconds", 1.0))
CHECKPOINT_INTERVAL: int = int(_VOTE.get("checkpoint_interval", 25))
MAX_TOKENS: int = int(_VOTE.get("max_tokens", 256))
TIMEOUT: int = int(_VOTE.get("timeout", 120))
DEEPSEEK_MAX_TOKENS: int = 2048  # v4-pro burns ~315 reasoning tokens before the answer
DEEPSEEK_URL: str = "https://api.deepseek.com/v1/chat/completions"

_VALID_DEPTHS: tuple[str, ...] = ("universal", "cross-domain", "domain", "specialized")

_DEPTH_ONTOLOGY: str = (
    "DEPTH (choose EXACTLY ONE):\n"
    "- universal    = applies to ALL systems (physics, cooking, poetry)\n"
    "- cross-domain = bridges 2+ DISTINCT disciplines via a SHARED mechanism\n"
    "- domain       = operates within ONE field / a cluster of adjacent fields\n"
    "- specialized  = narrow sub-technique within a sub-field or tool-specific skill\n"
)


def _canonical(kind: str) -> list[str]:
    """Return the canonical label list for an axis (discipline | domain)."""
    return list(CANONICAL_DISCIPLINES) if kind == "discipline" else list(CANONICAL_DOMAINS)


def build_label_prompt(fb: dict[str, Any]) -> str:
    """Construct the single-FB label prompt for a voter.

    Constrains each voter to the canonical ontology (discipline singular,
    domains 1..MAX_DOMAINS_PER_FB, depth 4-way) and requests a single JSON
    object so the response can be parsed deterministically.
    """
    disciplines = ", ".join(_canonical("discipline"))
    domains = ", ".join(_canonical("domain"))
    body = (
        f"Name: {fb.get('name') or ''}\n"
        f"Definition: {fb.get('definition') or ''}\n"
        f"Mechanism: {fb.get('mechanism') or ''}\n"
    )
    return (
        "You are labeling a Foundation Block (a reusable design principle).\n\n"
        "Assign THREE labels and return ONLY a JSON object (no markdown, no prose):\n"
        '{"discipline": "...", "domains": [...], "depth": "..."}\n\n'
        f"DISCIPLINE — choose EXACTLY ONE from:\n{disciplines}\n\n"
        f"DOMAINS — choose 1..{MAX_DOMAINS_PER_FB} from:\n{domains}\n\n"
        + _DEPTH_ONTOLOGY
        + "\nFB:\n" + body
    )


def parse_voter_output(raw: Any) -> dict[str, Any]:
    """Normalize a voter's JSON output into (discipline, domains, depth).

    Handles the list-vs-dict and nested-key variations that ``call_omlx_json``
    can return. Unmappable labels are preserved as raw strings for the
    aggregation to fail-closed on (never silently dropped — C16).
    """
    if isinstance(raw, list):
        raw = raw[0] if raw else {}
    if not isinstance(raw, dict):
        return {"discipline": None, "domains": [], "depth": None}

    disc = raw.get("discipline")
    if isinstance(disc, list):
        disc = disc[0] if disc else None
    disc = str(disc).strip() if disc else None

    doms = raw.get("domains") or raw.get("domain") or []
    if isinstance(doms, str):
        doms = [d.strip() for d in doms.replace(";", ",").split(",") if d.strip()]
    else:
        doms = [str(d).strip() for d in doms if str(d).strip()]
    doms = list(dict.fromkeys(doms))[: MAX_DOMAINS_PER_FB]

    depth = str(raw.get("depth", "")).strip().lower() if raw.get("depth") else None
    if depth not in _VALID_DEPTHS:
        depth = None

    return {"discipline": disc, "domains": doms, "depth": depth}


def _majority(counter: Counter, key: str) -> str:
    """Legacy majority key or fail-closed default on disagreement (D2577)."""
    if not counter:
        return key
    (winner, count) = counter.most_common(1)[0]
    return winner if count >= MAJORITY_THRESHOLD else key


def _aggregate_legacy(votes: list[dict[str, Any]]) -> dict[str, Any]:
    """Legacy 2-of-3 majority + fail-closed (D2577), kept for old checkpoints."""
    discs = Counter(v["discipline"] for v in votes if v.get("discipline"))
    depths = Counter(v["depth"] for v in votes if v.get("depth"))

    domain_counts: Counter = Counter()
    for v in votes:
        domain_counts.update(v.get("domains", []))

    kept_domains = [d for d, c in domain_counts.most_common() if c >= MAJORITY_THRESHOLD]

    return {
        "discipline": _majority(discs, FAIL_CLOSED_DISCIPLINE),
        "domains": kept_domains,
        "depth": _majority(depths, FAIL_CLOSED_DEPTH),
        "discipline_votes": dict(discs),
        "domain_votes": dict(domain_counts),
        "depth_votes": dict(depths),
    }


def _unanimous(values: list[Any]) -> Any:
    """Return the value if every element is identical AND non-empty, else None."""
    vals = [v for v in values if v not in (None, "", [])]
    if not vals or len(vals) != len(values):
        return None
    return vals[0] if len(set(str(v) for v in vals)) == 1 else None


def _aggregate_reliable_pair(votes: list[dict[str, Any]]) -> dict[str, Any]:
    """D2610 policy v2: reliable unanimity → label, else abstain (never fabricate).

    discipline/depth → all RELIABLE voters must agree on the same value, else None.
    domains          → intersection of all reliable voters' domain sets (a domain
                       is kept only if every reliable voter proposed it).
    Advisory voters  → recorded in ``advisory_votes`` but never decide.
    Any abstain sets ``needs_review`` True and ``agreed`` False.
    """
    reliable = [v for v in votes if v.get("model") in RELIABLE_VOTERS and not v.get("error")]
    advisory = [v for v in votes if v.get("model") in ADVISORY_VOTERS and not v.get("error")]

    discipline = _unanimous([v.get("discipline") for v in reliable])
    depth = _unanimous([v.get("depth") for v in reliable])

    domain_sets = [set(v.get("domains") or []) for v in reliable]
    kept_domains = sorted(set.intersection(*domain_sets)) if domain_sets else []

    agreed = discipline is not None and depth is not None and bool(kept_domains)

    # Full-vote record for the audit trail (all voters, reliable + advisory).
    discs = Counter(v["discipline"] for v in votes if v.get("discipline"))
    depths = Counter(v["depth"] for v in votes if v.get("depth"))
    domain_counts: Counter = Counter()
    for v in votes:
        domain_counts.update(v.get("domains", []))

    return {
        "discipline": discipline,
        "domains": kept_domains,
        "depth": depth,
        "needs_review": not agreed,
        "agreed": agreed,
        "policy": POLICY,
        "discipline_votes": dict(discs),
        "domain_votes": dict(domain_counts),
        "depth_votes": dict(depths),
        "reliable_voters": RELIABLE_VOTERS,
        "advisory_votes": {
            v["model"]: {"discipline": v.get("discipline"), "domains": v.get("domains"),
                         "depth": v.get("depth")}
            for v in advisory
        },
    }


def aggregate_votes(votes: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate N voter labels under the configured label policy.

    D2610 ``reliable_pair_agreement`` (default) → reliable unanimity + abstain.
    Legacy ``majority`` → 2-of-3 + fail-closed (D2577).
    """
    if POLICY == "reliable_pair_agreement":
        return _aggregate_reliable_pair(votes)
    return _aggregate_legacy(votes)


def flag_issues(fb: dict[str, Any], votes: list[dict[str, Any]], agg: dict[str, Any]) -> list[str]:
    """Emit D2580 flags: (a) missing close domains, (b) catch-all disciplines.

    TODO(D2580-close-domains): "close" currently means "proposed by >=1 voter
    but absent from BOTH the FB's current domain set and the consensus set".
    Upgrade to embedding-similarity closeness (e.g. bge-m3 cosine vs the FB's
    existing domain centroids) so only genuinely-adjacent omissions are flagged.
    """
    flags: list[str] = []

    if agg["discipline"] in CATCH_ALL_DISCIPLINES:
        flags.append(f"catch_all_discipline:{agg['discipline']}")

    current = set(fb.get("domains") or [])
    consensus = set(agg["domains"])
    for v in votes:
        for d in v.get("domains", []):
            if d not in current and d not in consensus:
                flags.append(f"missing_close_domain:{d}")

    return list(dict.fromkeys(flags))


def _safe_write(path: Path, text: str) -> None:
    """Crash-safe atomic write: tempfile → fsync → os.replace (C6)."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _load_high_suspicion(path: Path) -> set[str]:
    """Return the example-id set flagged high-suspicion by build_label_model.py.

    Reads the per-FB JSONL emitted by scripts/build_label_model.py and selects
    the rows in the `both` / `nli_only` tiers (the P3 challenger / GOLD-A seed).
    """
    ids: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if r.get("tier") in ("both", "nli_only"):
            ids.add(r.get("example_id") or r.get("fb_id"))
    return ids


def load_target_fbs(db_path: Path, where: str, limit: int | None) -> list[dict[str, Any]]:
    """Load FBs to vote on. ``where`` is an optional SQL predicate (default: all)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    q = "SELECT fb_id, name, definition, mechanism, discipline, domains, depth FROM fbs"
    if where:
        q += f" WHERE {where}"
    q += " ORDER BY fb_id"
    if limit:
        q += f" LIMIT {limit}"
    rows = [dict(r) for r in conn.execute(q)]
    conn.close()
    for r in rows:
        r["domains"] = json.loads(r["domains"]) if r.get("domains") else []
    return rows


def load_target_fbs_from_golden(golden_path: Path, limit: int | None) -> list[dict[str, Any]]:
    """Load the mined golden training set (D2577) as vote targets.

    Maps each golden example's ``input_fb`` + ``expected_classification`` to the
    same dict shape ``load_target_fbs`` produces, keyed by the example ``id``
    (so the checkpoint JSONL lines up 1:1 with the training set). ``current_*``
    in the output are therefore the gpt-oss TEACHER silver labels the vote
    exists to verify.
    """
    doc = yaml.safe_load(golden_path.read_text()) or {}
    examples = doc.get("examples", []) if isinstance(doc, dict) else []
    rows: list[dict[str, Any]] = []
    for ex in examples:
        if not isinstance(ex, dict):
            continue
        input_fb = ex.get("input_fb") or {}
        expected = ex.get("expected_classification") or {}
        rows.append(
            {
                "fb_id": str(ex.get("id") or f"golden-{len(rows)}"),
                "name": input_fb.get("name") or "",
                "definition": input_fb.get("definition") or "",
                "mechanism": input_fb.get("mechanism") or "",
                "discipline": expected.get("discipline"),
                "domains": list(expected.get("domains") or []),
                "depth": expected.get("depth"),
            }
        )
    if limit:
        rows = rows[:limit]
    return rows


def load_checkpoint(path: Path) -> dict[str, Any]:
    """Load prior votes keyed by fb_id (resume)."""
    if not path.exists():
        return {}
    try:
        return {r["fb_id"]: r for r in json.loads(path.read_text())}
    except (json.JSONDecodeError, KeyError):
        print(f"⚠️  checkpoint {path} unreadable — starting fresh", file=sys.stderr)
        return {}


def _call_deepseek_json(prompt: str, key: str, model: str) -> Any:
    """Call DeepSeek (cloud, C22 opt-in) for one FB; return the parsed JSON object.

    Parses ONLY ``content`` (never ``reasoning_content`` — the DELEGATE-001 trap).
    """
    import re
    import ssl
    import urllib.error
    import urllib.request

    import certifi

    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a precise JSON-only ontology labeler."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": DEEPSEEK_MAX_TOKENS,
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
    content = (data["choices"][0]["message"].get("content") or "").strip()
    if not content:
        raise RuntimeError("DeepSeek returned empty content (truncated reasoning?)")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", content, re.DOTALL)
        return json.loads(m.group(0)) if m else {}


def _call_voter(voter: dict[str, str], prompt: str, key: str) -> Any:
    """Route a voter by provider: deepseek → cloud HTTP, else local OMLX (C21)."""
    provider = str(voter.get("provider") or "omlx").lower()
    model = voter["model"]
    if provider == "deepseek":
        if not key:
            raise RuntimeError("DeepSeek voter requires DEEPSEEK_API_KEY (C22 opt-in)")
        return _call_deepseek_json(prompt, key, model)
    return call_omlx_json(prompt, model=model, max_tokens=MAX_TOKENS, timeout=TIMEOUT)


def vote_one_fb(fb: dict[str, Any], key: str = "") -> dict[str, Any]:
    """Run all voters on one FB (single-FB calls, BUG-224 workload shaping)."""
    prompt = build_label_prompt(fb)
    votes: list[dict[str, Any]] = []
    for voter in VOTERS:
        model = voter["model"]
        try:
            raw = _call_voter(voter, prompt, key)
            votes.append({"model": model, **parse_voter_output(raw)})
        except Exception as e:  # noqa: BLE001 — per-FB capture, fail-loud below (C16)
            print(f"  ⚠️  voter {model} FAILED on {fb['fb_id'][:12]}: {type(e).__name__}: {e}",
                  file=sys.stderr)
            votes.append({"model": model, "discipline": None, "domains": [], "depth": None,
                          "error": f"{type(e).__name__}: {e}"})
        time.sleep(RECOVERY_SLEEP)
        # Residency fix (D2585 / Claude finding): sequential CALLS do not imply
        # sequential RESIDENCY. Unload each non-pinned voter so only ONE
        # generative voter is resident at a time (memory budget D2496).
        if model not in PINNED_MODELS:
            unload_model(model)
    agg = aggregate_votes(votes)
    return {
        "fb_id": fb["fb_id"],
        "name": fb.get("name"),
        "current_discipline": fb.get("discipline"),
        "current_domains": fb.get("domains"),
        "current_depth": fb.get("depth"),
        "votes": votes,
        "consensus": agg,
        "flags": flag_issues(fb, votes, agg),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="3-model label vote (D2577/D2580)")
    parser.add_argument("--db", default=str(DB_PATH), help="Path to maxwell.db")
    parser.add_argument(
        "--golden",
        default=None,
        help="Path to a mined golden YAML (config/golden/stage4_golden_mined.yaml) to vote on instead of the DB",
    )
    parser.add_argument(
        "--high-suspicion",
        default=None,
        metavar="JSONL",
        help="Restrict to high-suspicion FBs (output of scripts/build_label_model.py); pairs with --golden",
    )
    parser.add_argument("--where", default=None, help="SQL predicate selecting FBs (DB source only)")
    parser.add_argument("--limit", type=int, default=None, help="Cap FBs (deterministic ORDER BY fb_id)")
    parser.add_argument("--output", default="temp/label_vote.jsonl", help="Checkpoint JSONL path")
    parser.add_argument("--key", default=os.environ.get("DEEPSEEK_API_KEY", ""),
                        help="DeepSeek API key (C22 opt-in; empty disables the deepseek voter)")
    parser.add_argument("--run", action="store_true", help="Actually call voters (default = dry-run)")
    args = parser.parse_args()

    db_path = Path(args.db)
    out_path = Path(args.output)
    if args.golden:
        fbs = load_target_fbs_from_golden(Path(args.golden), args.limit)
    else:
        fbs = load_target_fbs(db_path, args.where, args.limit)
    if args.high_suspicion:
        hs_ids = _load_high_suspicion(Path(args.high_suspicion))
        fbs = [fb for fb in fbs if fb["fb_id"] in hs_ids]
        print(f"   high-suspicion filter → {len(fbs)} FBs")
    print(f"🎯 3-model vote: {len(fbs)} FBs | voters={[v['model'] for v in VOTERS]} | "
          f"majority>={MAJORITY_THRESHOLD}/3 | output={out_path}")

    if not args.run:
        print("   DRY-RUN (no model calls). Re-run with --run to execute votes.")
        for fb in fbs[:10]:
            print(f"   {fb['fb_id'][:16]}  disc={fb.get('discipline')!r} depth={fb.get('depth')!r}")
        if len(fbs) > 10:
            print(f"   ... and {len(fbs) - 10} more")
        return 0

    done = load_checkpoint(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    for i, fb in enumerate(fbs, 1):
        if fb["fb_id"] in done:
            continue
        done[fb["fb_id"]] = vote_one_fb(fb, args.key)
        if i % CHECKPOINT_INTERVAL == 0 or i == len(fbs):
            _safe_write(out_path, json.dumps(list(done.values()), ensure_ascii=False, indent=1))
            print(f"   {i}/{len(fbs)} voted | {len(done)} records | {time.time() - t0:.0f}s")

    print(f"✅ DONE: {len(done)} votes in {time.time() - t0:.0f}s → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
