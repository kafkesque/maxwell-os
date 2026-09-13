#!/usr/bin/env python3
"""build_discipline_domain_vote.py — D2618 P1: reliable-pair discipline+domain vote.

The reliable pair (DeepSeek-v4-pro + Qwen3.8-27B) has voted content_type + depth
on the whole corpus (D2612) but has NEVER voted the discipline/domain axes — those
carry gpt-oss golden-silver labels or single-model p5:* spot-checks. This script
runs the pair on the two missing axes for the verified core (the 216 principle
rows of governance/verified_core.jsonl), closing the only axis-gap blocking an
honest 4-axis claim.

Policy (D2610 v2, identical to build_joint_vote_set.py):
  - reliable voters must be UNANIMOUS on BOTH discipline (61-way, single) and
    domains (43-way, 1-5 multi-label) -> agreed, high confidence.
  - any disagreement / missing voter -> ABSTAIN (empty discipline, empty domains,
    needs_review=true). A fabricated label is NEVER written (C16 spirit).
  - advisory voters recorded but never decisive.

Target set: the principle rows of governance/verified_core.jsonl (216 rows). Text
(name/definition/mechanism/boundary) is joined from maxwell.db by fb_id.

Output (resumable, deduplicated checkpoint — C23/C6):
  governance/discipline_domain_vote_checkpoint.jsonl

Usage:
  python3 scripts/build_discipline_domain_vote.py --list              # show target set
  python3 scripts/build_discipline_domain_vote.py --run --limit 10    # vote 10 rows
  python3 scripts/build_discipline_domain_vote.py --run --preflight    # full run
  python3 scripts/build_discipline_domain_vote.py --report             # summarize
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sqlite3
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import certifi
import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.json_fixer import parse_json_robust  # noqa: E402
from pipeline.omlx_call import call_omlx_json  # noqa: E402
from pipeline.pipeline_paths import PIPELINE_COMMIT, SCHEMA_VERSION  # noqa: E402

# ── C12/C20: named constants ────────────────────────────────────────────────
TAXONOMY = Path(os.environ.get("TAXONOMY_YAML", ROOT / "config" / "taxonomy_v5.yaml"))
VERIFIED_CORE = Path(os.environ.get("VERIFIED_CORE", ROOT / "governance" / "verified_core.jsonl"))
DB = Path(os.environ.get("MAXWELL_DB", ROOT / "knowledge pipeline" / "maxwell.db"))
OUT_CHECKPOINT = Path(os.environ.get(
    "DISC_DOM_CHECKPOINT", ROOT / "governance" / "discipline_domain_vote_checkpoint.jsonl"))

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
MAX_TOKENS = 128          # OMLX answer is ~40 tokens ({"discipline":..,"domains":[..]})
DEEPSEEK_MAX_TOKENS = 4096  # v4-pro burns reasoning tokens before the JSON
RECOVERY_SLEEP = 1.0
TIMEOUT = 120
DEFAULT_WORKERS = 3
DEEPSEEK_RETRIES = 3
DEEPSEEK_BACKOFF = 2.0
RETRYABLE_HTTP = frozenset({408, 429, 500, 502, 503, 504})

DEFAULT_RELIABLE = ("deepseek-v4-pro", "Qwen3.8-27B-MLX-4bit")
POLICY_VERSION = "v2"
ABSTAIN = ""  # never fabricate a label

# ── ontology (loaded once from taxonomy_v5.yaml) ────────────────────────────


def _canonical_defs() -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    data = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8")) or {}
    disc = [(d["canonical"], d.get("definition", "")) for d in data.get("disciplines", [])]
    dom = [(d["canonical"], d.get("definition", "")) for d in data.get("domains", [])]
    return disc, dom


DISCIPLINES, DOMAINS = _canonical_defs()
DISC_NAMES = [c for c, _ in DISCIPLINES]
DOM_NAMES = [c for c, _ in DOMAINS]


def _raw_alias_map() -> Tuple[Dict[str, str], Dict[str, str]]:
    """Build lowercase raw-alias -> canonical maps (normalize near-miss labels)."""
    data = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8")) or {}
    disc_map: Dict[str, str] = {}
    dom_map: Dict[str, str] = {}
    for d in data.get("disciplines", []):
        for a in d.get("raw", []):
            disc_map[str(a).strip().lower()] = d["canonical"]
    for d in data.get("domains", []):
        for a in d.get("raw", []):
            dom_map[str(a).strip().lower()] = d["canonical"]
    return disc_map, dom_map


DISC_ALIAS, DOM_ALIAS = _raw_alias_map()


def _ontology_text() -> str:
    # Truncate definitions to their first sentence (cap ~60 chars) — the full
    # 61+43 taxonomy with full definitions made the prompt ~3.2K tokens and the
    # OMLX prefill ~96s/row. A short gloss preserves disambiguation at ~2K tokens.
    def _short(defn: str) -> str:
        s = (defn or "").split(".")[0].strip()
        return s[:60] if len(s) > 60 else s

    disc_lines = "\n".join(f"- {c}: {_short(d)}" for c, d in DISCIPLINES)
    dom_lines = "\n".join(f"- {c}: {_short(d)}" for c, d in DOMAINS)
    return (
        "DISCIPLINE (choose EXACTLY ONE canonical label):\n" + disc_lines +
        "\n\nDOMAIN (choose 1-5 canonical labels that apply):\n" + dom_lines
    )


def _load_policy() -> Dict[str, Any]:
    cfg = yaml.safe_load((ROOT / "config" / "pipeline_config.yaml").read_text(encoding="utf-8")) or {}
    lv = cfg.get("label_vote", {}) or {}
    return {
        "reliable": [str(m) for m in (lv.get("reliable_voters") or list(DEFAULT_RELIABLE))],
        "advisory": [str(m) for m in (lv.get("advisory_voters") or [])],
    }


def _load_voters() -> List[Dict[str, str]]:
    cfg = yaml.safe_load((ROOT / "config" / "pipeline_config.yaml").read_text(encoding="utf-8")) or {}
    return [dict(v) for v in (cfg.get("label_vote", {}).get("models") or [])]


def select_targets(limit: int = 0) -> List[Dict[str, Any]]:
    """Return the principle rows of the verified core, joined with DB text."""
    core = [json.loads(line) for line in VERIFIED_CORE.open(encoding="utf-8") if line.strip()]
    principle = [r for r in core if r.get("content_type") == "principle"]
    fb_ids = [r["fb_id"] for r in principle]
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    text: Dict[str, Dict[str, Any]] = {}
    try:
        for fb in fb_ids:
            row = con.execute(
                "SELECT name, definition, mechanism, boundary FROM fbs WHERE fb_id=?", (fb,)
            ).fetchone()
            if row is not None:
                text[fb] = dict(row)
    finally:
        con.close()

    rows = []
    for r in principle:
        t = text.get(r["fb_id"], {})
        rows.append({
            "fb_id": r["fb_id"],
            "name": r.get("name") or t.get("name") or "",
            "definition": t.get("definition") or "",
            "mechanism": t.get("mechanism") or "",
            "boundary": t.get("boundary") or "",
            "silver_discipline": r.get("discipline"),
            "silver_domains": r.get("domains"),
        })
    rows.sort(key=lambda r: r["fb_id"])
    return rows[:limit] if limit else rows


def _prompt(fb: Dict[str, Any]) -> str:
    body = (
        f"Name: {fb.get('name') or ''}\n"
        f"Definition: {fb.get('definition') or ''}\n"
        f"Mechanism: {fb.get('mechanism') or ''}\n"
        f"Boundary: {fb.get('boundary') or ''}\n"
    )
    return (
        "You are labeling a Foundation Block (a reusable design principle) on TWO axes. "
        'Return ONLY a JSON object (no markdown, no prose): {"discipline": "...", "domains": ["...", ...]}.\n\n'
        + _ontology_text()
        + "\n\nFB:\n" + body
    )


def _parse(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, list):
        raw = raw[0] if raw else {}
    if not isinstance(raw, dict):
        return {"discipline": None, "domains": None}
    disc = str(raw.get("discipline", "")).strip().lower() if raw.get("discipline") else None
    doms_raw = raw.get("domains") or []
    if isinstance(doms_raw, str):
        doms_raw = [doms_raw]
    doms = [str(d).strip().lower() for d in doms_raw if isinstance(d, str)]
    # Canonicalize: exact canonical, else raw-alias -> canonical, else drop (fail-closed).
    disc_canon = disc if disc in DISC_NAMES else DISC_ALIAS.get(disc)
    dom_canon = [d if d in DOM_NAMES else DOM_ALIAS.get(d) for d in doms]
    dom_canon = sorted({d for d in dom_canon if d in DOM_NAMES})
    return {
        "discipline": disc_canon,
        "domains": dom_canon,
    }


def _call_deepseek(prompt: str, key: str, model: str) -> Dict[str, Any]:
    if not key:
        raise RuntimeError("DeepSeek voter requires --key / DEEPSEEK_API_KEY (C22 opt-in)")
    ctx = ssl.create_default_context(cafile=certifi.where())
    last_err: Optional[str] = None
    for attempt in range(1, DEEPSEEK_RETRIES + 1):
        use_json = attempt == 1
        body = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a precise JSON-only ontology labeler."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "max_tokens": DEEPSEEK_MAX_TOKENS,
            **({"response_format": {"type": "json_object"}} if use_json else {}),
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
                last_err = "empty content"
                time.sleep(DEEPSEEK_BACKOFF * attempt)
                continue
            raise RuntimeError("DeepSeek empty content after retries")
        out = _parse(parse_json_robust(content))
        if out.get("discipline") is not None:
            return out
        if attempt < DEEPSEEK_RETRIES:
            last_err = f"no valid discipline in {content[:80]!r}"
            time.sleep(DEEPSEEK_BACKOFF * attempt)
            continue
        raise RuntimeError(f"DeepSeek returned no valid discipline: {content[:120]!r}")
    raise RuntimeError(f"DeepSeek failed after retries: {last_err}")


def _call_omlx(prompt: str, model: str) -> Dict[str, Any]:
    return _parse(call_omlx_json(prompt, model=model, max_tokens=MAX_TOKENS))


def aggregate(votes: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    reliable = list(policy["reliable"])
    discs = [votes.get(m, {}).get("discipline") for m in reliable if isinstance(votes.get(m), dict)]
    doms = [votes.get(m, {}).get("domains") for m in reliable if isinstance(votes.get(m), dict)]

    disc_ok = [d for d in discs if d in DISC_NAMES]
    disc_unanimous = len(disc_ok) == len(reliable) and len(set(disc_ok)) == 1

    # domains unanimous: identical SET, and each voter returned >=1 canonical domain
    dom_sets = [frozenset(d) for d in doms if isinstance(d, list) and d]
    dom_unanimous = (
        len(dom_sets) == len(reliable) and len(dom_sets) > 0 and len(set(dom_sets)) == 1
    )

    agreed = disc_unanimous and dom_unanimous
    discipline = disc_ok[0] if disc_unanimous else ABSTAIN
    domains = sorted(dom_sets[0]) if dom_unanimous else []
    return {
        "discipline": discipline,
        "domains": domains,
        "discipline_agreed": disc_unanimous,
        "domains_agreed": dom_unanimous,
        "needs_review": not agreed,
        "agreed": agreed,
    }


def vote_once(fb: Dict[str, Any], voters: List[Dict[str, str]], key: str,
              policy: Dict[str, Any],
              prior_votes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    prompt = _prompt(fb)
    votes: Dict[str, Any] = dict(prior_votes or {})
    # Only the RELIABLE pair decides (D2610); advisory voters are never consulted
    # here (their $0-compute vote adds nothing to a unanimous-pair policy).
    reliable_models = set(policy["reliable"])
    for v in voters:
        model = v.get("model", "")
        if model not in reliable_models:
            continue
        provider = v.get("provider", "omlx")
        existing = votes.get(model)
        if isinstance(existing, dict) and "error" not in existing and existing.get("discipline") is not None:
            continue
        try:
            votes[model] = (_call_deepseek(prompt, key, model) if provider == "deepseek"
                            else _call_omlx(prompt, model))
        except Exception as exc:  # noqa: BLE001 — per-voter failure recorded (C16)
            votes[model] = {"error": f"{type(exc).__name__}: {exc}"}
        time.sleep(RECOVERY_SLEEP)

    verdict = aggregate(votes, policy)
    return {
        "fb_id": fb["fb_id"],
        "name": fb.get("name", ""),
        "silver_discipline": fb.get("silver_discipline"),
        "silver_domains": fb.get("silver_domains"),
        "votes": votes,
        "policy": "reliable_pair_agreement",
        "policy_version": POLICY_VERSION,
        "schema_version": SCHEMA_VERSION,
        "gen_model": " + ".join(policy["reliable"]),
        "pipeline_commit": PIPELINE_COMMIT,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **verdict,
    }


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


def run(limit: int, workers: int, key: str) -> None:
    policy = _load_policy()
    voters = _load_voters()
    targets = select_targets(limit)
    cp = _load_checkpoint()
    todo = [fb for fb in targets if fb["fb_id"] not in cp]
    print(f"targets: {len(targets)} | already voted: {len(targets) - len(todo)} | todo: {len(todo)}")

    if not todo:
        print("nothing to do")
        return

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(vote_once, fb, voters, key, policy): fb for fb in todo}
        for fut in as_completed(futs):
            fb = futs[fut]
            try:
                rec = fut.result()
            except Exception as exc:  # noqa: BLE001
                print(f"FAILED {fb['fb_id']}: {type(exc).__name__}: {exc}", flush=True)
                continue
            cp[rec["fb_id"]] = rec
            done += 1
            if done % 5 == 0 or done == len(todo):
                _atomic_write(OUT_CHECKPOINT, "".join(
                    json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in cp.values()))
                print(f"progress {done}/{len(todo)} (flushed checkpoint)", flush=True)

    _atomic_write(OUT_CHECKPOINT, "".join(
        json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in cp.values()))
    print(f"done {done}/{len(todo)}")


def report() -> None:
    if not OUT_CHECKPOINT.exists():
        print("no checkpoint yet")
        return
    recs = list(_load_checkpoint().values())
    agreed = sum(1 for r in recs if r.get("agreed"))
    print(f"total voted: {len(recs)} | agreed: {agreed} | abstain: {len(recs) - agreed}")
    print(f"discipline distribution (agreed):",
          dict(Counter(r["discipline"] for r in recs if r.get("discipline"))))
    disc_agree = sum(1 for r in recs if r.get("discipline_agreed"))
    dom_agree = sum(1 for r in recs if r.get("domains_agreed"))
    print(f"discipline unanimous: {disc_agree} | domains unanimous: {dom_agree}")


def main() -> None:
    ap = argparse.ArgumentParser(description="D2618 P1: reliable-pair discipline+domain vote on the verified core.")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    ap.add_argument("--key", default=os.environ.get("DEEPSEEK_API_KEY", ""))
    args = ap.parse_args()

    if args.list:
        targets = select_targets(args.limit)
        print(f"{len(targets)} principle rows in the verified core")
        for t in targets[:20]:
            print(f"  {t['fb_id'][:12]}  {t['name'][:50]}")
        return
    if args.report:
        report()
        return
    if args.run:
        if not args.key:
            raise SystemExit("DEEPSEEK_API_KEY required (C22 opt-in)")
        run(args.limit, args.workers, args.key)
        return
    ap.print_help()


if __name__ == "__main__":
    main()
