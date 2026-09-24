#!/usr/bin/env python3
"""vote_anchor_domains.py — the 150-row ANCHOR domain axis, coded by the reliable pair (D2618-P0 pattern).

WHY: the anchor family owns content_type (150/150), discipline (150/150) and depth (the owner's pass, 150/150) but
has NO domain axis. The owner ruled that absence is an OMISSION (work owed), not a design deferral. This script
produces that axis as MACHINE EVIDENCE with the SAME instrument that produced the 216-row domain cohort, so the two
cohorts stay comparable:

    reliable pair = the config-declared reliable voters (DeepSeek-v4-pro over the API + Qwen3.8-27B over OMLX),
    policy = D2610 v2 via the shared vote_once()/aggregate() in scripts/build_discipline_domain_vote.py
    (unanimous domain SET -> agreed; disagreement or missing voter -> ABSTAIN + needs_review).

BLIND BY CONSTRUCTION: the input is governance/frontier_pack_20260924/BLIND_INPUT_150.csv — row text only, no
CT/DISC/FORM/DEPTH/conf_depth, and no BOUNDARY (boundary encodes scope, which would leak the depth axis). The same
file is the frontier pack's input, so every coder reads one identical artifact.

DECLARED DEVIATIONS from the 216-row prompt (prompt_id `anchor_domains_v1`):
  1. domains-only — the anchor's content_type and discipline are HUMAN-owned in ANCHOR-3; re-coding them here would
     invite a second, non-owner series for axes the owner has already decided.
  2. input fields name/definition/application/mechanism — the 216 run used boundary instead of application, since
     BOUNDARY is blind-excluded on this sheet.
  The canonical domain vocabulary is read from config by the shared helper (C12), never written down here.

This NEVER writes `domains_final` and never writes to the ANCHOR sheet: adjudication is the owner's (p5:human),
exactly as on the 216 cohort.

Usage:
  python3 scripts/vote_anchor_domains.py --dry-run              # print the prompt + voter config, no calls
  python3 scripts/vote_anchor_domains.py --limit 3 --allow-api   # pilot
  python3 scripts/vote_anchor_domains.py --run --allow-api       # full 150, resumable
  python3 scripts/vote_anchor_domains.py --report
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import build_discipline_domain_vote as bddv  # noqa: E402  (the shared instrument, not a copy of it)

BLIND_INPUT = REPO / "governance" / "frontier_pack_20260924" / "BLIND_INPUT_150.csv"
CHECKPOINT = REPO / "governance" / "anchor4_domain_vote_checkpoint.jsonl"
SCHEMA_VERSION = "1.0"
PROMPT_ID = "anchor_domains_v1"


def load_blind_rows() -> list[dict[str, str]]:
    """Return the 150 blind anchor rows (text columns only) in sheet order."""
    with BLIND_INPUT.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for r in rows:
        out.append({
            "fb_id": (r.get("item_id") or "").strip(),          # bddv keys its record by fb_id; here it is R###
            "item_id": (r.get("item_id") or "").strip(),
            "name": (r.get("name") or "").strip(),
            "definition": (r.get("DEFINITION") or "").strip(),
            "application": (r.get("APPLICATION") or "").strip(),
            "mechanism": (r.get("MECHANISM") or "").strip(),
        })
    return out


def _domain_section() -> str:
    """Canonical DOMAIN section only, read from config (C12).

    The shared _ontology_text() emits BOTH menus; a domains-only instrument must not ship the 65-discipline menu
    (it costs tokens and invites an answer on an axis the owner already owns in ANCHOR-3).
    """
    first, second = bddv._canonical_defs()
    doms = first if all(n in bddv.DOM_NAMES for n, _ in first) else second
    return "DOMAIN (choose 1-5 canonical labels that apply):\n" + "\n".join(f"- {n}: {d}" for n, d in doms)


def prompt_for(row: dict[str, str]) -> str:
    """The anchor domains-only prompt: same JSON contract + same config vocabulary as the 216 run."""
    body = (
        f"Name: {row.get('name') or ''}\n"
        f"Definition: {row.get('definition') or ''}\n"
        f"Application: {row.get('application') or ''}\n"
        f"Mechanism: {row.get('mechanism') or ''}\n"
    )
    return (
        "You are labeling a Foundation Block (a reusable design principle) on its DOMAINS. "
        'Return ONLY a JSON object (no markdown, no prose): {"domains": ["...", ...]}.\n\n'
        + _domain_section()
        + "\n\nFB:\n" + body
    )


def resolve_key(explicit: str) -> str:
    """API key from --key, the environment, or .env (never printed)."""
    if explicit:
        return explicit
    if os.environ.get("DEEPSEEK_API_KEY"):
        return os.environ["DEEPSEEK_API_KEY"]
    env = REPO / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip().startswith("DEEPSEEK_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def pipeline_commit() -> str:
    """Short git revision, for R14 stamping."""
    try:
        return subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def atomic_append(path: pathlib.Path, text: str) -> None:
    """Crash-safe append (C6): write the whole file to a temp sibling, fsync, os.replace."""
    body = path.read_text(encoding="utf-8") if path.exists() else ""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp_", suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(body + text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def load_done() -> dict[str, dict[str, Any]]:
    """Resume set: item_id -> record already in the checkpoint."""
    if not CHECKPOINT.exists():
        return {}
    done: dict[str, dict[str, Any]] = {}
    for line in CHECKPOINT.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            done[str(rec.get("item_id"))] = rec
    return done


def vote_row(row: dict[str, str], voters: list[dict[str, str]], key: str,
             policy: dict[str, Any]) -> dict[str, Any]:
    """Run the reliable pair on one anchor row and normalise the record. A failed voter is recorded, never faked (C16)."""
    res = bddv.vote_once(dict(row), voters, key, policy)
    votes = res.get("votes") or {}
    per = {m: (v.get("domains") if isinstance(v, dict) else None) for m, v in votes.items()}
    return {
        "schema_version": SCHEMA_VERSION,
        "prompt_id": PROMPT_ID,
        "artifact_id": "ANCHOR-DOMAIN-VOTE",
        "item_id": row["item_id"],
        "name": row["name"],
        "domains": res.get("domains"),                 # silver consensus; None on abstention
        "agreed": bool(res.get("agreed")),
        # vote_once() never returns n_voters, so derive the count from the voters that actually
        # answered (BUG-434: a declared field must not be null while the truth sits beside it).
        "n_voters": sum(1 for v in votes.values() if isinstance(v, dict) and not v.get("error")),
        "needs_review": bool(res.get("needs_review", True)),
        "per_voter_domains": per,
        "votes": votes,
        "coder_models": policy.get("reliable"),
        "policy": res.get("policy"),
        "policy_version": res.get("policy_version"),
        "gen_model": res.get("gen_model"),
        "gen_temperature": 0.0,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pipeline_commit": pipeline_commit(),
        "authority": "MACHINE-ADVISORY-ONLY",          # never p5:human; the owner adjudicates
    }


def run(limit: int, workers: int, key: str, allow_api: bool) -> int:
    """Vote the anchor rows, resumably, and report the tally."""
    voters = bddv._load_voters()
    policy = bddv._load_policy()
    need_api = any(v.get("provider") == "deepseek" for v in voters if v.get("model") in set(policy["reliable"]))
    if need_api and not key:
        print("REFUSED: the reliable pair needs the DeepSeek arm and no key was resolvable (C22 opt-in).")
        return 2
    if need_api and not allow_api:
        print("REFUSED: DeepSeek API arm is an explicit opt-in — pass --allow-api (C22).")
        return 2
    rows = load_blind_rows()
    done = load_done()
    todo = [r for r in rows if r["item_id"] not in done]
    if limit:
        todo = todo[:limit]
    print(f"reliable pair: {policy['reliable']} | voters: {[v.get('model') for v in voters]}")
    print(f"rows {len(rows)} | already voted {len(done)} | to vote now {len(todo)} | prompt {PROMPT_ID}")
    if not todo:
        return 0
    n_ok = n_abstain = n_err = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(vote_row, r, voters, key, policy): r for r in todo}
        for fut in as_completed(futs):
            r = futs[fut]
            try:
                rec = fut.result()
            except Exception as exc:  # noqa: BLE001 — recorded, never silently dropped (C16)
                rec = {"schema_version": SCHEMA_VERSION, "prompt_id": PROMPT_ID, "item_id": r["item_id"],
                       "name": r["name"], "agreed": False, "needs_review": True,
                       "error": f"{type(exc).__name__}: {exc}",
                       "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       "pipeline_commit": pipeline_commit(), "authority": "MACHINE-ADVISORY-ONLY"}
                n_err += 1
            else:
                if rec["agreed"]:
                    n_ok += 1
                else:
                    n_abstain += 1
            atomic_append(CHECKPOINT, json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"  {rec['item_id']:>4} {'AGREED' if rec.get('agreed') else 'ABSTAIN'} "
                  f"{rec.get('domains') if rec.get('domains') is not None else rec.get('error', '')}")
    print(f"done: agreed {n_ok} | abstain {n_abstain} | error {n_err} -> {CHECKPOINT.relative_to(REPO)}")
    return 0


def report() -> int:
    """Summarise the checkpoint: joinable rows, agreement, abstention reasons."""
    done = load_done()
    if not done:
        print("checkpoint empty")
        return 0
    rows = load_blind_rows()
    agree = sum(1 for r in done.values() if r.get("agreed"))
    print(f"checkpoint {CHECKPOINT.relative_to(REPO)}: {len(done)}/{len(rows)} anchor rows voted")
    print(f"  agreed (pair unanimous on the domain SET) {agree} | abstain {len(done) - agree}")
    from collections import Counter
    print("  domains tally:", dict(Counter(d for r in done.values() for d in (r.get("domains") or [])).most_common()))
    print("  models:", sorted({m for r in done.values() for m in (r.get("per_voter_domains") or {})}))
    return 0


def main() -> int:
    """CLI."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--key", default="")
    ap.add_argument("--allow-api", action="store_true", help="C22: explicit opt-in for the DeepSeek API arm")
    a = ap.parse_args()
    if a.report:
        return report()
    if a.dry_run:
        voters = bddv._load_voters()
        policy = bddv._load_policy()
        print("reliable:", policy["reliable"], "| advisory:", policy.get("advisory"))
        print("voters:", json.dumps(voters, ensure_ascii=False)[:300])
        print("key resolvable:", bool(resolve_key(a.key)), "| rows:", len(load_blind_rows()))
        print("---- prompt for row 1 ----")
        print(prompt_for(load_blind_rows()[0]))
        return 0
    if a.run:
        return run(a.limit, a.workers, resolve_key(a.key), a.allow_api)
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
