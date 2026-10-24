#!/usr/bin/env python3
"""T-195 step (d): MULTI-MODEL ADVISORY MATCH/NONE adjudication of the unruled tier-B candidates.

WHY (D-3137 clause 2 + the owner's 2026-10-23 ask): the owner wants to minimize manual ruling
by having several INDEPENDENT local models each emit an advisory MATCH/NONE on the unruled
tier-B candidates, then review only the rows where the models DISAGREE. This is ADVISORY ONLY:
it records model opinions, certifies NOTHING (D-2658), floors NOTHING, and never writes the
owner's ruling (D-2898). The owner's MATCH/NONE in the ruling sheet stays the ONLY authority.

The PROPOSER (Qwen3-Coder-30B) is EXCLUDED (R5: asking it to confirm its own proposals measures
agreement with itself — BUG-053/D-2658). Phi-4-mini is EXCLUDED (BUG-053 open-ended
hallucination). DeepSeek is not served locally (parked bytes gone, BUG-808; cloud violates
C3 + DELEGATE-001). The panel is declared in config/extraction_recall.yaml#tier_b_adjudication.

Every candidate is judged WITH its source reading and closest store rows (the same decorrelated
grounding tier_b_evidence.py measured) — a grounded classification, never an open-ended one.
temp=0.0 is enforced by pipeline/omlx_call.py (R7). Output: a stamped advisory envelope, a full
CSV (all 43), and a disagreement-only CSV (non-unanimous rows) carrying fb_id / name / definition
/ application for the closest stored row plus the models' own proposed definition/application.

  --selftest   fixture proof of the vote aggregation + CSV writer (no model, no store, no file)
  --dry-run    print the panel + counts + prompt sizes, call NO model, write NO file
  --limit N    (debug) run only the first N candidates, not the whole 43
  (default)    adjudicate every unruled candidate with every panel model; write the 3 artifacts
"""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

# The script lives in scripts/ but imports pipeline.* (omlx_call). Make the project root importable
# regardless of CWD / invocation dir (same guard the proven build_depth_vote_set.py uses).
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA_VERSION = "1"
ARTIFACT_ID = "EXTRACTION-RECALL-TIER-B-ADJUDICATION"
EXIT_OK = 0
EXIT_FATAL = 1

_SYSTEM = (
    "You are a precise knowledge-curation classifier. You decide, for each candidate concept, "
    "whether it should be extracted from a source book as a distinct, standalone knowledge unit. "
    "Return STRICT JSON only — a JSON array, no markdown, no explanation outside the JSON."
)

_PANEL_EXCLUDED = ("Qwen3-Coder-30B-A3B-Instruct-MLX-4bit", "Phi-4-mini-instruct-8bit")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


def _deepseek_key() -> str:
    import os
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if key:
        return key
    p = Path(".env")
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith("DEEPSEEK_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _call_deepseek(prompt: str, model: str, max_tokens: int) -> Any:
    """Cloud DeepSeek vote (C22 opt-in, D-3023 'never silent' — the owner asked for it).

    deepseek-v4-pro / deepseek-flash are REASONING models: they emit chain-of-thought in
    `reasoning_content` and the FINAL answer in `content` (the DELEGATE-001 trap — parse ONLY
    `content`, never CoT). Reasoning token burn scales with batch size, so callers must chunk
    (config tier_b_adjudication.chunk_size). Empty `content` (truncated reasoning) is a LOUD
    fault, never a silent empty vote (C16).
    """
    import ssl
    import urllib.error
    import urllib.request
    key = _deepseek_key()
    if not key:
        raise RuntimeError("no DEEPSEEK_API_KEY (env or .env) — C22 opt-in required")
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": _SYSTEM},
                     {"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except Exception:  # pragma: no cover — certifi optional, fall back to system trust
        ctx = ssl.create_default_context()
    req = urllib.request.Request(DEEPSEEK_URL, data=payload, method="POST", headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300, context=ctx) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"DeepSeek HTTP {exc.code}: {exc.read()[:200]!r}") from exc
    content = (data["choices"][0]["message"].get("content") or "").strip()
    if not content:
        raise RuntimeError("DeepSeek returned empty content (reasoning truncated by max_tokens — chunk smaller)")
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:]
    start, end = content.find("["), content.rfind("]")
    if start == -1 or end == -1:
        raise RuntimeError(f"DeepSeek content has no JSON array: {content[:200]!r}")
    return json.loads(content[start:end + 1])


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as e:  # pragma: no cover
        raise SystemExit(f"FAIL-CLOSED: PyYAML not importable: {e}") from e
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except Exception:  # pragma: no cover
        return "unknown"


def load_config() -> dict[str, Any]:
    data = _load_yaml(Path("config/extraction_recall.yaml"))
    er = data.get("extraction_recall") or {}
    block = er.get("tier_b_adjudication") or {}
    for key in ("models", "path", "csv_path", "disagree_csv_path"):
        if key not in block:
            raise SystemExit(f"FAIL-CLOSED: extraction_recall.tier_b_adjudication.{key} is NOT declared (C12)")
    models = [str(m).strip() for m in (block.get("models") or [])]
    if not models:
        raise SystemExit("FAIL-CLOSED: extraction_recall.tier_b_adjudication.models is empty (C12)")
    for m in models:
        if m in _PANEL_EXCLUDED:
            raise SystemExit(f"FAIL-CLOSED: '{m}' is excluded from the panel (proposer R5 / Phi-4-mini BUG-053)")
    out: dict[str, Any] = dict(block)
    out["models"] = models
    out["max_tokens"] = int(block.get("max_tokens", 2500))
    out["chunk_size"] = int(block.get("chunk_size", 4))
    golden = er.get("golden") or {}
    out["_proposal_sheet"] = golden.get("tier_b_sheet")
    out["_ruling_sheet"] = golden.get("tier_b_ruling_sheet")
    out["_evidence_path"] = (er.get("tier_b_evidence") or {}).get("path")
    out["_store_db"] = er.get("store")
    out["_reference_band"] = (er.get("tier_b_evidence") or {}).get("semantic_near_threshold")
    return out


def read_jsonl(path: str) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def load_unruled(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    proposed = read_jsonl(cfg["_proposal_sheet"])
    ruled = read_jsonl(cfg["_ruling_sheet"])
    ruled_keys = {(r["source_id"], r["name"]) for r in ruled}
    return [p for p in proposed if (p["source_id"], p["name"]) not in ruled_keys]


def load_evidence(cfg: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    p = Path(cfg["_evidence_path"])
    if not p.exists():
        return {}
    d = json.loads(p.read_text(encoding="utf-8"))
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for row in d.get("rows", []):
        out[(row["source_id"], row["name"])] = row
    return out


def build_candidate_prompt(idx: int, cand: dict[str, Any], ev: dict[str, Any]) -> str:
    lines: list[str] = [f"[{idx}] name: {cand['name']!r}"]
    lines.append(f"    rationale: {cand.get('rationale', '')}")
    g = ev.get("grounding") or {}
    kind = g.get("excerpt_kind", "none")
    reading = (g.get("excerpt") or "").strip()
    lines.append(f"    reading({kind}): \"{reading}\"")
    store = ev.get("store_best") or []
    if store:
        parts = []
        for s in store[:3]:
            parts.append(f"{s.get('cos', 0.0):.4f} {s.get('name', '')!r}")
        lines.append(f"    store(cos name): {'; '.join(parts)}")
    else:
        lines.append("    store: (no stored rows for this source)")
    return "\n".join(lines)


def build_prompt(cands: list[tuple[dict[str, Any], dict[str, Any]]], band: float | None) -> str:
    rules = [
        "You are classifying candidate concepts extracted from a source book.",
        "",
        "For EACH candidate decide MATCH or NONE:",
        "  MATCH = the source genuinely teaches this as a distinct, named principle/technique/mental "
        "model worth extracting on its own, AND it is not already covered by the store rows listed for it.",
        "  NONE  = the concept is not actually present in the source, is too vague/trivial to be a "
        "distinct unit, or is already covered by a listed store row.",
    ]
    if band is not None:
        rules.append(f"  (a store cosine >= {band} means 'already semantically near' an existing row -> lean NONE.)")
    rules += [
        "",
        "Return a JSON ARRAY with one object per candidate, in the SAME order, each object:",
        '  {"index": <int>, "verdict": "MATCH"|"NONE", "confidence": <0.0-1.0>, "reason": "<one sentence>",',
        '   "definition": "<one-sentence definition of the concept>", "application": "<one-sentence application>"}',
        "",
        "Candidates:",
    ]
    body = "\n".join(rules)
    for idx, (cand, ev) in enumerate(cands):
        body += "\n" + build_candidate_prompt(idx, cand, ev)
    return body


def _band_from_method(cfg: dict[str, Any]) -> float | None:
    band = cfg.get("_reference_band")
    if isinstance(band, (int, float)):
        return float(band)
    return None


def parse_votes(result: Any, n: int) -> list[dict[str, Any]]:
    """Map a model's JSON back to per-candidate vote dicts by 'index' (fallback: list order)."""
    votes: list[dict[str, Any]] = [{} for _ in range(n)]
    # D-3137: a reasoning model run one candidate at a time (chunk_size=1) may emit a
    # single BARE object instead of a one-element array. Normalize it before mapping.
    if isinstance(result, dict):
        result = [result]
    if not isinstance(result, list):
        return votes
    for obj in result:
        if not isinstance(obj, dict):
            continue
        idx = obj.get("index")
        if isinstance(idx, int) and 0 <= idx < n:
            votes[idx] = obj
    # fallback: if no index field survived, map by order
    if all(not v for v in votes) and len(result) <= n:
        for i, obj in enumerate(result):
            if isinstance(obj, dict):
                votes[i] = obj
    return votes


def adjudicate_source(model: str, cands: list[tuple[dict[str, Any], dict[str, Any]]],
                      band: float | None, max_tokens: int) -> list[dict[str, Any]]:
    prompt = build_prompt(cands, band)
    if model.lower().startswith("deepseek"):
        raw = _call_deepseek(prompt, model, max_tokens)
        return parse_votes(raw, len(cands))
    from pipeline.omlx_call import call_omlx_json
    raw = call_omlx_json(prompt, model=model, system=_SYSTEM, max_tokens=max_tokens)
    return parse_votes(raw, len(cands))


def _normalize_vote(vote: dict[str, Any]) -> dict[str, Any]:
    verdict = str(vote.get("verdict", "")).strip().upper()
    if verdict not in ("MATCH", "NONE"):
        return {"error": "missing/unknown verdict", "raw": str(vote)[:200]}
    conf = vote.get("confidence")
    try:
        conf = round(float(conf), 3)
    except (TypeError, ValueError):
        conf = None
    return {
        "verdict": verdict,
        "confidence": conf,
        "reason": str(vote.get("reason", "")).strip(),
        "definition": str(vote.get("definition", "")).strip(),
        "application": str(vote.get("application", "")).strip(),
    }


def aggregate(cands: list[tuple[dict[str, Any], dict[str, Any]]],
              model_votes: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, (cand, ev) in enumerate(cands):
        votes: dict[str, Any] = {}
        match = none = err = 0
        for model in model_votes:
            v = _normalize_vote(model_votes[model][i])
            votes[model] = v
            if "error" in v:
                err += 1
            elif v["verdict"] == "MATCH":
                match += 1
            else:
                none += 1
        voting = match + none
        if err > 0:
            agree = "INCOMPLETE"
        elif match == 0:
            agree = "UNANIMOUS NONE"
        elif none == 0:
            agree = "UNANIMOUS MATCH"
        elif match == 3:
            agree = "MAJORITY MATCH (3-1)"
        elif none == 3:
            agree = "MAJORITY NONE (1-3)"
        else:
            agree = "SPLIT (2-2)"
        rows.append({
            "source_id": cand["source_id"],
            "name": cand["name"],
            "concept_key": ev.get("concept_key", ""),
            "rationale": cand.get("rationale", ""),
            "votes": votes,
            "match": match,
            "none": none,
            "error": err,
            "agreement": agree,
            "needs_review": agree != "UNANIMOUS MATCH" and agree != "UNANIMOUS NONE",
            "store_best": ev.get("store_best") or [],
            "reading": ((ev.get("grounding") or {}).get("excerpt") or "").strip(),
            "reading_kind": (ev.get("grounding") or {}).get("excerpt_kind", "none"),
        })
    return rows


def _store_detail(cfg: dict[str, Any], fb_ids: list[str]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    if not fb_ids:
        return out
    db = cfg["_store_db"]
    try:
        conn = sqlite3.connect(db)
    except Exception:  # pragma: no cover
        return out
    try:
        qmarks = ",".join("?" for _ in fb_ids)
        cur = conn.execute(
            f"SELECT fb_id, name, definition, application FROM fbs WHERE fb_id IN ({qmarks})",
            fb_ids,
        )
        for fb_id, name, definition, application in cur.fetchall():
            out[fb_id] = {"name": name, "definition": definition or "", "application": application or ""}
    finally:
        conn.close()
    return out


def first_defined(votes: dict[str, Any], key: str) -> str:
    for v in votes.values():
        s = v.get(key)
        if s:
            return s
    return ""


def _model_short(model: str) -> str:
    return model.replace("-", "_").replace(".", "").replace(" ", "_")


def write_csv(path: str, rows: list[dict[str, Any]], models: list[str]) -> None:
    header = ["source_id", "name", "concept_key", "agreement",
              *[_model_short(m) for m in models], "match", "none"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for r in rows:
            w.writerow([
                r["source_id"], r["name"], r["concept_key"], r["agreement"],
                *[f"{r['votes'][m].get('verdict', 'ERR')}({r['votes'][m].get('confidence', '')})" for m in models],
                r["match"], r["none"],
            ])


def write_disagree_csv(path: str, rows: list[dict[str, Any]], models: list[str], cfg: dict[str, Any]) -> None:
    fb_ids = [s["fb_id"] for r in rows for s in r["store_best"][:1] if s.get("fb_id")]
    detail = _store_detail(cfg, fb_ids)
    header = ["source_id", "name", "concept_key", "agreement", "match", "none",
              *[_model_short(m) for m in models],
              "closest_fb_id", "closest_fb_name", "closest_fb_definition", "closest_fb_application",
              "candidate_definition", "candidate_application", "reading_kind", "reading"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for r in rows:
            top = r["store_best"][0] if r["store_best"] else {}
            fb_id = top.get("fb_id", "")
            d = detail.get(fb_id, {})
            w.writerow([
                r["source_id"], r["name"], r["concept_key"], r["agreement"], r["match"], r["none"],
                *[f"{r['votes'][m].get('verdict', 'ERR')}({r['votes'][m].get('confidence', '')})" for m in models],
                fb_id, d.get("name", top.get("name", "")),
                d.get("definition", ""), d.get("application", ""),
                first_defined(r["votes"], "definition"), first_defined(r["votes"], "application"),
                r["reading_kind"], r["reading"],
            ])


def write_envelope(path: str, cfg: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    envelope = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": ARTIFACT_ID,
        "gen_model": f"panel {cfg['models']} — ADVISORY model opinions only",
        "pipeline_commit": _git_commit(),
        "authority": ("ADVISORY EVIDENCE ONLY (D-2658/D-2898/D-3137): records model opinions, "
                      "certifies nothing, floors nothing, and never writes the owner's ruling."),
        "models": cfg["models"],
        "reference_band": _band_from_method(cfg),
        "rows": rows,
    }
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(envelope, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def _selftest() -> int:
    """Known-answer controls (D-3036 red loop) for aggregation + CSV, with NO model / store / file."""
    cands = [({"source_id": "s1", "name": f"c{i}", "rationale": "r"}, {"concept_key": f"k{i}", "store_best": []}) for i in range(4)]
    model_votes = {
        "A": [{"verdict": "MATCH", "confidence": 0.9}, {"verdict": "MATCH", "confidence": 0.8},
              {"verdict": "NONE", "confidence": 0.7}, {"verdict": "MATCH", "confidence": 0.6}],
        "B": [{"verdict": "MATCH", "confidence": 0.9}, {"verdict": "MATCH", "confidence": 0.8},
              {"verdict": "NONE", "confidence": 0.7}, {"verdict": "NONE", "confidence": 0.6}],
        "C": [{"verdict": "MATCH", "confidence": 0.9}, {"verdict": "MATCH", "confidence": 0.8},
              {"verdict": "NONE", "confidence": 0.7}, {"verdict": "MATCH", "confidence": 0.6}],
        "D": [{"verdict": "MATCH", "confidence": 0.9}, {"verdict": "MATCH", "confidence": 0.8},
              {"verdict": "NONE", "confidence": 0.7}, {"verdict": "NONE", "confidence": 0.6}],
    }
    rows = aggregate(cands, model_votes)
    assert [r["agreement"] for r in rows] == ["UNANIMOUS MATCH", "UNANIMOUS MATCH", "UNANIMOUS NONE", "SPLIT (2-2)"], rows
    assert [r["needs_review"] for r in rows] == [False, False, False, True]
    assert [r["match"] for r in rows] == [4, 4, 0, 2]
    # parser: map by index
    votes = parse_votes([{"index": 1, "verdict": "NONE"}, {"index": 0, "verdict": "MATCH"}], 2)
    assert votes[0]["verdict"] == "MATCH" and votes[1]["verdict"] == "NONE"
    # parser: fallback order + unknown verdict -> error
    votes = parse_votes([{"verdict": "MATCH"}, {"verdict": "MAYBE"}], 2)
    assert votes[0]["verdict"] == "MATCH" and _normalize_vote(votes[1]).get("error")
    print("✅ adjudicator selftest passed: vote counting (4-0/0-4/2-2), needs_review, index+fallback parsing, unknown->error")
    return EXIT_OK


def _dry_run(cfg: dict[str, Any], cands: list[tuple[dict[str, Any], dict[str, Any]]]) -> int:
    print(f"panel models: {cfg['models']}")
    print(f"unruled candidates: {len(cands)}")
    band = _band_from_method(cfg)
    from collections import Counter
    by_src = Counter(c["source_id"] for c, _ in cands)
    for sid, n in by_src.items():
        subset = [(c, e) for c, e in cands if c["source_id"] == sid]
        print(f"  source {sid}: {n} candidates, prompt ~{len(build_prompt(subset, band))} chars")
    print("DRY RUN: no model called, no file written.")
    return EXIT_OK


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Multi-model advisory MATCH/NONE adjudication of tier-B candidates.")
    parser.add_argument("--selftest", action="store_true", help="fixture proof, no model/store/file")
    parser.add_argument("--dry-run", action="store_true", help="print panel + counts + prompt sizes, call nothing")
    parser.add_argument("--limit", type=int, default=None, help="debug: adjudicate only the first N candidates")
    parser.add_argument("--models", type=str, default=None,
                        help="comma-separated subset of panel models to run (default: all)")
    args = parser.parse_args(argv)

    if args.selftest:
        return _selftest()

    cfg = load_config()
    unruled = load_unruled(cfg)
    evidence = load_evidence(cfg)
    if not unruled:
        print("nothing unruled — every tier-B candidate already has an owner ruling.")
        return EXIT_OK
    if args.limit:
        unruled = unruled[: args.limit]
    cands = [(c, evidence.get((c["source_id"], c["name"]), {})) for c in unruled]
    missing_ev = [c["name"] for c, e in cands if not e]
    if missing_ev:
        print(f"WARN: {len(missing_ev)} candidate(s) have NO evidence row (grounding blank): {missing_ev[:5]}")

    if args.dry_run:
        return _dry_run(cfg, cands)

    band = _band_from_method(cfg)
    # Iterate sources in the SAME order they appear in `cands` (proposal-sheet source-major order),
    # so the concatenated per-source votes align exactly with the candidate order `aggregate()` reads.
    # A sorted() here would misalign the f8f8…/b51204… blocks (D-3036: the CSV must not be corrupted).
    source_order: list[str] = []
    for c, _ in cands:
        if c["source_id"] not in source_order:
            source_order.append(c["source_id"])
    if "chunk_size" not in cfg:  # C12c: a value read with a code default has a SECOND home
        raise SystemExit("FAIL-CLOSED: tier_b_adjudication.chunk_size missing in config (C12)")
    chunk_size = max(1, int(cfg["chunk_size"]))
    single_models = set(cfg.get("single_candidate_models") or [])
    model_votes: dict[str, list[dict[str, Any]]] = {}
    run_models = cfg["models"]
    if args.models:
        wanted = {m.strip() for m in args.models.split(",") if m.strip()}
        run_models = [m for m in cfg["models"] if m in wanted]
        unknown = wanted - set(cfg["models"])
        if unknown:
            raise SystemExit(f"FAIL-CLOSED: --models names not in panel: {sorted(unknown)} (C12)")
    for model in run_models:
        m_chunk = 1 if model in single_models else chunk_size
        print(f"\n=== model: {model} === (chunk {m_chunk})", flush=True)
        for source_id in source_order:
            subset = [(c, e) for c, e in cands if c["source_id"] == source_id]
            print(f"  source {source_id}: {len(subset)} candidates (chunk {m_chunk}) ...", flush=True)
            for lo in range(0, len(subset), m_chunk):
                chunk = subset[lo:lo + chunk_size]
                try:
                    votes = adjudicate_source(model, chunk, band, cfg["max_tokens"])
                    # pad votes to len(chunk) if the model returned fewer
                    while len(votes) < len(chunk):
                        votes.append({})
                    model_votes.setdefault(model, []).extend(votes)
                    ok = sum(1 for v in votes if _normalize_vote(v).get("verdict"))
                    print(f"    [{lo}:{lo + len(chunk)}] -> {ok}/{len(chunk)} parsed verdicts", flush=True)
                except Exception as e:  # noqa: BLE001 — record the fault, keep going (C16/C23)
                    print(f"    [{lo}:{lo + len(chunk)}] !! model call failed: {e}", flush=True)
                    model_votes.setdefault(model, []).extend([{} for _ in chunk])

    # reorder model_votes to match the candidate order (they are appended in source-major order == cands order)
    rows = aggregate(cands, model_votes)

    write_envelope(cfg["path"], cfg, rows)
    write_csv(cfg["csv_path"], rows, cfg["models"])
    disagree = [r for r in rows if r["needs_review"]]
    write_disagree_csv(cfg["disagree_csv_path"], disagree, cfg["models"], cfg)

    unanimous = sum(1 for r in rows if not r["needs_review"])
    print(f"\nDONE: {len(rows)} candidates | {unanimous} unanimous | {len(disagree)} need review")
    from collections import Counter
    print("agreement:", dict(Counter(r["agreement"] for r in rows)))
    print(f"envelope: {cfg['path']}")
    print(f"full csv: {cfg['csv_path']}")
    print(f"disagreement csv: {cfg['disagree_csv_path']} ({len(disagree)} rows)")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
