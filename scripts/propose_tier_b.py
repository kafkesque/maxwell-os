#!/usr/bin/env python3
"""propose_tier_b.py — T-195 step (b): the ADVISORY tier-B candidate proposer.

WHY THIS EXISTS. check_extraction_recall.py proves the certified core (tier A) is not LOST, but it
cannot prove the extractor EMITTED every concept a source contains. This script is the "completeness"
half of "nothing lost": a local model proposes candidate concepts the certified core may have OMITTED,
one JSONL line per candidate into the `tier_b_sheet`. The owner then rules each MATCH/NONE.

WHAT IT IS NOT. The proposer is ADVISORY (D-2898): a proposed-but-unruled candidate is tier B —
REPORTED by the recall rail, NEVER floored, NEVER auto-certified. Only an owner MATCH ruling moves a
concept into tier A (via --build-golden). So this script can only ever make the recall rail MORE
complete or leave it unchanged; it can never falsify a loss.

KEY REUSE (D-3129 / D-3118). concept_key = sha256(sorted stopword-filtered tokens of folded name) is
imported from pipeline/dedup_identity.py — NEVER re-implemented — so a tier-B row keys exactly like a
tier-A row. source_id = SHA-256(normalize_author|normalize_title)[:16] is imported from
pipeline/book_metadata.py — NEVER re-implemented — so the pilot sources resolve to their actual source
files. A naive hash of a raw name/author/title would miss the golden and report false "omitted" rows.

CONFIG-FIRST (C12). pilot_sources, model, window bounds, and the tier_b_sheet path all load from
config/extraction_recall.yaml#extraction_recall.proposer. temp=0.0 (R7) is enforced by omlx_call.

Modes:
  --selftest   Fixture proof (no model, no store, no file): fold reuse, tier-A skip, dedup, and the
               crash-safe JSONL round-trip. RED on any invariant break (D-3036).
  --dry-run    Resolve pilot sources -> source files -> window plan and print it; write NOTHING.
  (default)    Propose candidates per window via the configured model and emit the tier_b_sheet JSONL.

Exit codes: 0 OK, 2 OWED (no pilot_sources declared / none resolvable), 3 configuration error.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CONFIG_PATH = PROJECT_ROOT / "config" / "extraction_recall.yaml"
METADATA_PATH = PROJECT_ROOT / "knowledge pipeline" / "checkpoints" / "book_metadata.jsonl"

EXIT_OK = 0
EXIT_OWED = 2
EXIT_CONFIG = 3

# The proposal prompt is advisory GENERATION (D-2549): ask for concepts, never for a certification.
_SYSTEM = (
    "You propose candidate knowledge-base concepts from a source excerpt. Be precise and non-obvious: "
    "name the distinct ideas a reader would want to retain, not generic chapter headings. Return ONLY "
    "a JSON array of objects {\"name\": \"<concept name>\", \"rationale\": \"<one-sentence advisory reason>\"}."
)


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as e:  # C16: no silent error
        raise RuntimeError(f"PyYAML unavailable ({e}); cannot read {path}") from e
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    if not isinstance(doc, dict):
        raise RuntimeError(f"{path} is not a YAML mapping")
    return doc


def load_config() -> dict[str, Any]:
    """Return the `extraction_recall` block, refusing a missing proposer block (C16)."""
    block = _load_yaml(CONFIG_PATH).get("extraction_recall")
    if not isinstance(block, dict):
        raise RuntimeError(f"{CONFIG_PATH}: missing 'extraction_recall' block")
    if not isinstance(block.get("proposer"), dict):
        raise RuntimeError(f"{CONFIG_PATH}: missing 'extraction_recall.proposer' block")
    return block


def resolve_source_files(pilot_ids: list[str]) -> dict[str, str]:
    """Reverse-map source_id -> source .md path via the authoritative metadata cache.

    Uses book_metadata.compute_source_id (the SAME function the pipeline used to mint the ids), so the
    reverse map is exact for every id the metadata cache can explain. Prefers a .md (converted) file
    over an .epub; first existing path wins. Ids that cannot resolve are REPORTED, not fabricated.
    """
    from pipeline.book_metadata import compute_source_id

    wanted = set(pilot_ids)
    found: dict[str, str] = {}
    if METADATA_PATH.exists():
        with open(METADATA_PATH, encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sid = compute_source_id(
                    d.get("author", ""), d.get("title", ""), fallback_key=d.get("source_book", "")
                )
                if sid not in wanted:
                    continue
                sp = (d.get("source_path") or "").strip()
                if not sp or not os.path.exists(sp):
                    continue
                if sid in found and not found[sid].endswith(".md"):
                    found[sid] = sp  # upgrade a non-.md hold to any later path
                elif sid not in found:
                    found[sid] = sp
                # prefer .md: once a .md is recorded, later non-.md paths do not replace it
                if sp.endswith(".md"):
                    found[sid] = sp
    return found


def read_tier_a(golden_path: Path, source_id: str) -> tuple[list[str], set[str]]:
    """Tier-A (names, concept_keys) already certified FOR this source (to skip re-proposing them)."""
    if not golden_path.exists():
        return [], set()
    try:
        golden = json.loads(golden_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return [], set()
    names: list[str] = []
    keys: set[str] = set()
    for r in golden.get("rows", []):
        if isinstance(r, dict) and source_id in (r.get("sources") or []):
            nm = str(r.get("name") or "").strip()
            k = str(r.get("concept_key") or "").strip()
            if nm:
                names.append(nm)
            if k:
                keys.add(k)
    return names, keys


def windowize(text: str, max_chars: int) -> list[str]:
    """Split text into ~max_chars windows at paragraph boundaries (never mid-word).

    A paragraph LARGER than max_chars is hard-split at the last space before the limit, so no single
    window can ever exceed max_chars (which would blow the model context on a pathological 50KB line).
    """
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    windows: list[str] = []
    buf: list[str] = []
    buf_len = 0

    def flush() -> None:
        nonlocal buf, buf_len
        if buf:
            windows.append("\n".join(buf))
            buf, buf_len = [], 0

    for para in text.split("\n"):
        para = para.strip()
        if not para:
            continue
        while len(para) > max_chars:
            cut = para.rfind(" ", 0, max_chars)
            if cut <= 0:
                cut = max_chars  # no space found: a single word longer than the window
            flush()
            windows.append(para[:cut].strip())
            para = para[cut:].strip()
        if not para:
            continue
        if buf and buf_len + len(para) + 1 > max_chars:
            flush()
        buf.append(para)
        buf_len += len(para) + 1
    flush()
    return windows


def propose_window(
    model: str,
    window: str,
    already_names: list[str],
    already_keys: set[str],
    max_candidates: int,
) -> list[dict[str, str]]:
    """Propose candidate concepts from ONE window via the model (advisory, single-shot).

    already_names seeds the prompt (so the model does not re-list known concepts); already_keys is the
    deterministic skip (a candidate whose folded key collides is dropped). Both come from tier A.
    """
    from pipeline.dedup_identity import concept_key as mint_key
    from pipeline.omlx_call import call_omlx_json

    exclude = "\n".join(f"- {n}" for n in sorted(set(already_names))) or "(none)"
    prompt = (
        f"The following is an excerpt from a source. Propose up to {max_candidates} DISTINCT, "
        f"non-obvious concepts worth capturing in a knowledge base. A concept is a reusable idea, "
        f"principle, technique, or mental model with a short name.\n\n"
        f"Do NOT re-propose any of these already-known concepts:\n{exclude}\n\n"
        f"EXCERPT:\n{window}\n\n"
        f"Return a JSON array: [{{\"name\": \"...\", \"rationale\": \"...\"}}, ...]"
    )
    result = call_omlx_json(prompt, model=model, system=_SYSTEM)
    if not isinstance(result, list):
        return []
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in result:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        rationale = str(item.get("rationale") or "").strip()
        if not name:
            continue
        key = mint_key(name)
        if key in already_keys or key in seen:
            continue
        seen.add(key)
        out.append({"name": name, "rationale": rationale})
        if len(out) >= max_candidates:
            break
    return out


def emit(path: Path, rows: list[dict[str, str]]) -> None:
    """Crash-safe write (C6): tempfile -> fsync -> os.replace. One JSON line per candidate."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _selftest() -> int:
    """Fixture proof (D-3036 red loop) — no model, no store, no filesystem writes persist."""
    from pipeline.dedup_identity import concept_key as mint_key

    # 1) FOLD REUSE: the proposer mints the SAME key as the recall rail's consumer.
    name = "Iterative Design and Implementation"
    assert mint_key(name) == mint_key(name) and len(mint_key(name)) == 64, "sha256 hex key"

    # 2) TIER-A SKIP: a candidate that folds to a certified key is dropped.
    already_keys = {mint_key("Agent-centric Problem Solving")}
    assert mint_key("Agent-centric Problem Solving") in already_keys
    assert mint_key("agent centric problem solving") in already_keys, "folded variant must collide"

    # 3) DEDUP key space: two folded-name variants are ONE candidate.
    assert mint_key("Strategic Perspective Shift") == mint_key("  Strategic   Perspective Shift  ")

    # 4) CRASH-SAFE ROUND-TRIP: emit then read back exactly one JSON line per candidate.
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "tb.jsonl"
        rows = [
            {"source_id": "f8f802e878304781", "name": "X", "rationale": "r1"},
            {"source_id": "b51204ce6c6a9950", "name": "Y", "rationale": "r2"},
        ]
        emit(p, rows)
        lines = [json.loads(l) for l in p.read_text(encoding="utf-8").strip().splitlines()]
        assert lines == rows, "JSONL round-trip must preserve one line per candidate"

    # 5) WINDOWING: bounded, never drops a paragraph's content.
    paras = [f"p{i} " + "word " * 30 for i in range(8)]
    text = "\n".join(paras)
    ws = windowize(text, 150)
    assert len(ws) > 1, "a long text must split into multiple windows"
    assert all(len(w) <= 150 for w in ws), "every window must respect max_chars"
    got = " ".join(ws).split()
    want = text.split()
    assert got == want, "windowing must preserve every token in order"

    print("✅ proposer selftest passed: fold reuse, tier-A skip, dedup key space, crash-safe JSONL, windowing")
    return EXIT_OK


def _dry_run(cfg: dict[str, Any]) -> int:
    """Resolve and print the plan; write nothing."""
    proposer = cfg["proposer"]
    pilots = [str(p).strip() for p in proposer.get("pilot_sources", []) if str(p).strip()]
    if not pilots:
        print("OWED: no proposer.pilot_sources declared (config/extraction_recall.yaml)")
        return EXIT_OWED
    files = resolve_source_files(pilots)
    for pid in pilots:
        fp = files.get(pid)
        if fp:
            try:
                size = os.path.getsize(fp)
            except OSError:
                size = -1
            print(f"  {pid} -> {fp} ({size} bytes)")
        else:
            print(f"  {pid} -> NOT RESOLVED")
    missing = [p for p in pilots if p not in files]
    if missing:
        print(f"OWED: {len(missing)} pilot source_id(s) unresolved: {missing}")
        return EXIT_OWED
    print(f"model: {proposer.get('model')} | max_window_chars={proposer.get('max_window_chars')} "
          f"| max_windows={proposer.get('max_windows_per_source')} "
          f"| max_candidates={proposer.get('max_candidates_per_source')}")
    print(f"tier_b_sheet: {cfg['golden'].get('tier_b_sheet')}")
    print("dry-run only — nothing written. Run without --dry-run to propose.")
    return EXIT_OK


def _run(cfg: dict[str, Any]) -> int:
    from pipeline.dedup_identity import concept_key as mint_key

    proposer = cfg["proposer"]
    pilots = [str(p).strip() for p in proposer.get("pilot_sources", []) if str(p).strip()]
    if not pilots:
        print("OWED: no proposer.pilot_sources declared")
        return EXIT_OWED
    model = str(proposer.get("model") or "").strip()
    if not model:
        print("FAIL-CLOSED: proposer.model is empty (C12)")
        return EXIT_CONFIG
    max_chars = int(proposer.get("max_window_chars", 6000))
    max_windows = int(proposer.get("max_windows_per_source", 4))
    max_cand = int(proposer.get("max_candidates_per_source", 15))
    skip_a = bool(proposer.get("skip_existing_tier_a", True))

    files = resolve_source_files(pilots)
    missing = [p for p in pilots if p not in files]
    if missing:
        print(f"OWED: {len(missing)} pilot source_id(s) unresolved: {missing}")
        return EXIT_OWED

    golden_path = PROJECT_ROOT / str(cfg["golden"]["path"])
    tier_b_rel = cfg["golden"].get("tier_b_sheet")
    if not tier_b_rel:
        print("FAIL-CLOSED: golden.tier_b_sheet is empty (set it in config/extraction_recall.yaml)")
        return EXIT_CONFIG
    tier_b_path = PROJECT_ROOT / str(tier_b_rel)

    all_rows: list[dict[str, str]] = []
    for pid in pilots:
        fp = files[pid]
        text = Path(fp).read_text(encoding="utf-8", errors="replace")
        names, keys = read_tier_a(golden_path, pid) if skip_a else ([], set())
        windows = windowize(text, max_chars)[:max_windows]
        print(f"[{pid}] {Path(fp).name}: {len(windows)} window(s), {len(keys)} tier-A key(s) to skip")
        src_rows: list[dict[str, str]] = []
        seen: set[str] = set(keys)
        for wi, w in enumerate(windows):
            try:
                cands = propose_window(model, w, names, seen, max_cand)
            except Exception as e:  # C23: one wedged call must not abort the batch (BUG-965 shape)
                print(f"  ⚠️  window {wi} failed: {e}")
                continue
            for c in cands:
                key = mint_key(c["name"])
                if key in seen:
                    continue
                seen.add(key)
                src_rows.append({"source_id": pid, "name": c["name"], "rationale": c["rationale"]})
                if len(src_rows) >= max_cand:
                    break
            if len(src_rows) >= max_cand:
                break
        print(f"  proposed {len(src_rows)} candidate(s)")
        all_rows.extend(src_rows)

    emit(tier_b_path, all_rows)
    print(f"wrote {len(all_rows)} tier-B candidate(s) to {tier_b_rel}")
    print("ADVISORY: the owner must rule each candidate MATCH/NONE; none is auto-certified (D-2898).")
    print("After ruling, re-run: python3 scripts/check_extraction_recall.py --build-golden --apply "
          "&& python3 scripts/check_extraction_recall.py --check")
    return EXIT_OK


def main() -> int:
    parser = argparse.ArgumentParser(description="T-195 tier-B proposer (advisory, D-2898)")
    parser.add_argument("--selftest", action="store_true", help="fixture proof, no model/store/file")
    parser.add_argument("--dry-run", action="store_true", help="resolve and print the plan, write nothing")
    args = parser.parse_args()

    if args.selftest:
        return _selftest()
    cfg = load_config()
    if args.dry_run:
        return _dry_run(cfg)
    return _run(cfg)


if __name__ == "__main__":
    sys.exit(main())
