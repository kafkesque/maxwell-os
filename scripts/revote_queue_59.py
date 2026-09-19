#!/usr/bin/env python3
"""revote_queue_59.py — D2629 follow-up: reliable-pair 3-axis vote on the 59 queue rows.

The 108 d2615-principle rows were kept OUT of the frozen 216 anchor (D2619) and
re-verified on content_type (D2629): 59 remain principle, 49 are non-principle.
The 59 principle rows still carry depth=None / discipline=None / domains=[] (only
silver `golden-silver`/`p5:claude` references). To GROW the anchor beyond 216 by
at most +59, these 59 rows must gain honest depth + discipline + domains from the
reliable pair (DeepSeek-v4-pro + Qwen3.8-27B) — the same pair that voted
content_type + depth (D2612) and discipline + domain (D2618 P1).

Policy (D2610 v2 — unanimous-else-abstain, NEVER fabricate):
  - depth:      both voters return the SAME canonical 4-way depth          -> agreed
  - discipline: both voters return the SAME canonical 61-way discipline    -> agreed
  - domains:    both voters return the SAME non-empty 43-way SET           -> agreed
  - any disagreement / missing voter -> ABSTAIN on that axis (empty), never a
    fabricated label. Each axis is aggregated independently so a partial
    agreement (e.g. depth+discipline but contested domains) is preserved.

Target set: the 59 fb_ids in governance/content_type_reverify_108.json with
content_type == "principle", joined with governance/expansion_queue_108.jsonl
for the silver references + maxwell.db for name/definition/mechanism/boundary.

Output (resumable, deduplicated checkpoint — C23/C6, atomic fsync+replace):
  governance/queue_59_vote_checkpoint.jsonl

Usage:
  python3 scripts/revote_queue_59.py --list
  python3 scripts/revote_queue_59.py --run --preflight
  python3 scripts/revote_queue_59.py --run --limit 2
  python3 scripts/revote_queue_59.py --report
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
from typing import Any, Dict, List, Optional, Tuple

import certifi
import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.json_fixer import parse_json_robust  # noqa: E402
from pipeline.omlx_call import call_omlx_json  # noqa: E402
from pipeline.pipeline_paths import PIPELINE_COMMIT, SCHEMA_VERSION  # noqa: E402

# ── C12/C20: named constants (no hardcode, no magic numbers) ───────────────
TAXONOMY = Path(os.environ.get("TAXONOMY_YAML", ROOT / "config" / "taxonomy_v5.yaml"))
QUEUE = Path(os.environ.get("EXPANSION_QUEUE", ROOT / "governance" / "expansion_queue_108.jsonl"))
REVERIFY = Path(os.environ.get(
    "CT_REVERIFY", ROOT / "governance" / "content_type_reverify_108.json"))
DB = Path(os.environ.get("MAXWELL_DB", ROOT / "knowledge pipeline" / "maxwell.db"))
OUT_CHECKPOINT = Path(os.environ.get(
    "QUEUE_59_CHECKPOINT", ROOT / "governance" / "queue_59_vote_checkpoint.jsonl"))

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
MAX_TOKENS = 192          # {"depth":..,"discipline":..,"domains":[..]} ~ 60 tokens
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

VALID_DEPTHS = ("universal", "cross-domain", "domain", "specialized")
DEPTH_GLOSS = {
    "universal": "applies to ALL systems (physics, cooking, poetry)",
    "cross-domain": "bridges 2+ DISTINCT disciplines via a SHARED mechanism",
    "domain": "operates within ONE field / a cluster of adjacent fields",
    "specialized": "narrow sub-technique within a sub-field or tool-specific skill",
}


def _canonical_defs() -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    data = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8")) or {}
    disc = [(d["canonical"], d.get("definition", "")) for d in data.get("disciplines", [])]
    dom = [(d["canonical"], d.get("definition", "")) for d in data.get("domains", [])]
    return disc, dom


DISCIPLINES, DOMAINS = _canonical_defs()
DISC_NAMES = [c for c, _ in DISCIPLINES]
DOM_NAMES = [c for c, _ in DOMAINS]


def _raw_alias_map() -> Tuple[Dict[str, str], Dict[str, str]]:
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


def _short(defn: str) -> str:
    s = (defn or "").split(".")[0].strip()
    return s[:60] if len(s) > 60 else s


def _ontology_text() -> str:
    depth_lines = "\n".join(f"- {k}: {v}" for k, v in DEPTH_GLOSS.items())
    disc_lines = "\n".join(f"- {c}: {_short(d)}" for c, d in DISCIPLINES)
    dom_lines = "\n".join(f"- {c}: {_short(d)}" for c, d in DOMAINS)
    return (
        "DEPTH (choose EXACTLY ONE):\n" + depth_lines +
        "\n\nDISCIPLINE (choose EXACTLY ONE canonical label):\n" + disc_lines +
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
    """Return the 59 queue rows still principle, joined with DB text + silver refs."""
    reverify = json.loads(REVERIFY.read_text(encoding="utf-8"))
    principle_ids = {
        v["fb_id"] for v in reverify.get("verdicts", [])
        if v.get("content_type") == "principle"
    }
    queue = [json.loads(l) for l in QUEUE.open(encoding="utf-8") if l.strip()]
    targets = [r for r in queue if r["fb_id"] in principle_ids]
    targets.sort(key=lambda r: r["fb_id"])

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    text: Dict[str, Dict[str, Any]] = {}
    try:
        for r in targets:
            row = con.execute(
                "SELECT name, definition, mechanism, boundary FROM fbs WHERE fb_id=?",
                (r["fb_id"],),
            ).fetchone()
            if row is not None:
                text[r["fb_id"]] = dict(row)
    finally:
        con.close()

    rows = []
    for r in targets:
        t = text.get(r["fb_id"], {})
        rows.append({
            "fb_id": r["fb_id"],
            "name": r.get("name") or t.get("name") or "",
            "definition": t.get("definition") or "",
            "mechanism": t.get("mechanism") or "",
            "boundary": t.get("boundary") or "",
            "silver_depth": r.get("depth"),
            "silver_discipline": r.get("discipline"),
            "silver_domains": r.get("domains"),
        })
    return rows[:limit] if limit else rows


def _prompt(fb: Dict[str, Any]) -> str:
    body = (
        f"Name: {fb.get('name') or ''}\n"
        f"Definition: {fb.get('definition') or ''}\n"
        f"Mechanism: {fb.get('mechanism') or ''}\n"
        f"Boundary: {fb.get('boundary') or ''}\n"
    )
    return (
        "You are labeling a Foundation Block (a reusable design principle) on THREE axes. "
        'Return ONLY a JSON object (no markdown, no prose): '
        '{"depth": "...", "discipline": "...", "domains": ["...", ...]}.\n\n'
        + _ontology_text()
        + "\n\nFB:\n" + body
    )


def _parse(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, list):
        raw = raw[0] if raw else {}
    if not isinstance(raw, dict):
        return {"depth": None, "discipline": None, "domains": None}

    depth = str(raw.get("depth", "")).strip().lower() if raw.get("depth") else None
    depth_canon = depth if depth in VALID_DEPTHS else None

    disc = str(raw.get("discipline", "")).strip().lower() if raw.get("discipline") else None
    disc_canon = disc if disc in DISC_NAMES else DISC_ALIAS.get(disc)

    doms_raw = raw.get("domains") or []
    if isinstance(doms_raw, str):
        doms_raw = [doms_raw]
    doms = [str(d).strip().lower() for d in doms_raw if isinstance(d, str)]
    dom_canon = sorted({d if d in DOM_NAMES else DOM_ALIAS.get(d) for d in doms if
                        (d in DOM_NAMES or d in DOM_ALIAS)})

    return {"depth": depth_canon, "discipline": disc_canon, "domains": dom_canon}


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
    parsed = [votes.get(m) for m in reliable if isinstance(votes.get(m), dict)]

    depths = [v.get("depth") for v in parsed if v.get("depth") in VALID_DEPTHS]
    depth_unanimous = len(depths) == len(reliable) and len(set(depths)) == 1

    discs = [v.get("discipline") for v in parsed if v.get("discipline") in DISC_NAMES]
    disc_unanimous = len(discs) == len(reliable) and len(set(discs)) == 1

    dom_sets = [frozenset(v["domains"]) for v in parsed if isinstance(v.get("domains"), list) and v["domains"]]
    dom_unanimous = len(dom_sets) == len(reliable) and len(dom_sets) > 0 and len(set(dom_sets)) == 1

    agreed = depth_unanimous and disc_unanimous and dom_unanimous
    return {
        "depth": depths[0] if depth_unanimous else ABSTAIN,
        "discipline": discs[0] if disc_unanimous else ABSTAIN,
        "domains": sorted(dom_sets[0]) if dom_unanimous else [],
        "depth_agreed": depth_unanimous,
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
        "silver_depth": fb.get("silver_depth"),
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


def preflight(key: str) -> None:
    """Probe both voters + report target count BEFORE any row is voted (C16)."""
    targets = select_targets()
    print(f"preflight: {len(targets)} target rows (expect 59)")
    try:
        _call_deepseek('Return ONLY JSON: {"depth":"domain","discipline":"engineering","domains":["science & research"]}',
                       key, DEFAULT_RELIABLE[0])
        print(f"preflight: DeepSeek {DEFAULT_RELIABLE[0]} OK")
    except Exception as exc:  # noqa: BLE001
        print(f"preflight: DeepSeek FAILED {type(exc).__name__}: {exc}")
    try:
        _call_omlx('Return ONLY JSON: {"depth":"domain","discipline":"engineering","domains":["science & research"]}',
                   DEFAULT_RELIABLE[1])
        print(f"preflight: OMLX {DEFAULT_RELIABLE[1]} OK")
    except Exception as exc:  # noqa: BLE001
        print(f"preflight: OMLX FAILED {type(exc).__name__}: {exc}")


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
    d_ag = sum(1 for r in recs if r.get("depth_agreed"))
    disc_ag = sum(1 for r in recs if r.get("discipline_agreed"))
    dom_ag = sum(1 for r in recs if r.get("domains_agreed"))
    print(f"total voted: {len(recs)} | 3-axis agreed: {agreed} | abstain(any axis): {len(recs) - agreed}")
    print(f"depth unanimous: {d_ag} | discipline unanimous: {disc_ag} | domains unanimous: {dom_ag}")
    print(f"depth distribution:", dict(Counter(r["depth"] for r in recs if r.get("depth"))))
    print(f"discipline distribution:", dict(Counter(r["discipline"] for r in recs if r.get("discipline"))))


def main() -> None:
    ap = argparse.ArgumentParser(description="D2629 follow-up: reliable-pair 3-axis vote on the 59 queue rows.")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    ap.add_argument("--key", default=os.environ.get("DEEPSEEK_API_KEY", ""))
    args = ap.parse_args()

    if args.list:
        targets = select_targets(args.limit)
        print(f"{len(targets)} principle queue rows (expect 59)")
        for t in targets[:20]:
            print(f"  {t['fb_id'][:12]}  {t['name'][:55]}")
        return
    if args.report:
        report()
        return
    if args.preflight:
        if not args.key:
            raise SystemExit("DEEPSEEK_API_KEY required (C22 opt-in)")
        preflight(args.key)
        return
    if args.run:
        if not args.key:
            raise SystemExit("DEEPSEEK_API_KEY required (C22 opt-in)")
        run(args.limit, args.workers, args.key)
        return
    ap.print_help()


if __name__ == "__main__":
    main()
