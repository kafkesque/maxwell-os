#!/usr/bin/env python3
"""gate_duplicate_candidates.py — owner-gate ledger generator (D-2738).

Merges the two READ-ONLY detector outputs into ONE owner-adjudication ledger:
  * title_rename_candidates.json   (D-2736, near-dup titles, jaccard >= 0.60)
  * same_work_content_candidates.json (D-2737, full-text same-work, Jaccard >= 0.50)

Deterministic, advisory-only machine hints help the owner triage, but the generator
NEVER sets a verdict: every pair is PENDING until the owner writes MERGE (same work,
alias the duplicate) or KEEP_SEPARATE (distinct work / series volume / false positive).

Future-proofing (drift safety): re-runs PRESERVE existing owner verdicts. A
regenerated ledger carries `verdict`/`owner_note` forward by `pair_id`, so re-running
the detectors can never wipe an owner decision.

Exit codes: 0 = wrote ledger; 1 = read error; 2 = --selftest failure.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import yaml  # noqa: E402

CONFIG_REL = "config/eval_integrity.yaml"
_DEFAULTS: dict[str, Any] = {
    "ledger_file": "governance/duplicate_adjudication.json",
    "title_candidates_file": "governance/title_rename_candidates.json",
    "content_candidates_file": "governance/same_work_content_candidates.json",
    "apply_threshold": 0.50,
}

_VALID_VERDICTS = ("PENDING", "MERGE", "KEEP_SEPARATE")
_VOLUME_RE = re.compile(r"\bvolume\s*(\d+)\b")
_NOISE_MARKERS = (
    "(z-lib.org)", "z-lib", "_clean", "(for true epub)", "(true epub)", "for true epub",
)
_SPLIT_SEPS = (" \u2014 ", "\u2014", " \u2013 ", " - ")


def _load_config() -> dict[str, Any]:
    """Load the `duplicate_gate` block from eval_integrity.yaml (C12 config home)."""
    cfg_path = _PROJECT_ROOT / CONFIG_REL
    if not cfg_path.exists():
        return dict(_DEFAULTS)
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    block = data.get("duplicate_gate") or {}
    merged = dict(_DEFAULTS)
    merged.update({k: v for k, v in block.items() if k in _DEFAULTS})
    return merged


def _pair_id(a_id: str, b_id: str) -> str:
    """Deterministic pair key: sha256 of the sorted id pair, truncated to 16 hex."""
    lo, hi = (a_id, b_id) if a_id <= b_id else (b_id, a_id)
    return hashlib.sha256(f"{lo}|{hi}".encode("utf-8")).hexdigest()[:16]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _split_label(label: str) -> tuple[str, str]:
    """Split a detector display string 'author \u2014 title' into (author, title)."""
    for sep in _SPLIT_SEPS:
        if sep in label:
            a, t = label.split(sep, 1)
            return a.strip(), t.strip()
    return "", label.strip()


def _hint(a_label: str, b_label: str) -> str:
    """Advisory, deterministic triage hint. NEVER a verdict."""
    a_author, a_title = _split_label(a_label)
    b_author, b_title = _split_label(b_label)
    at, bt = _norm(a_title), _norm(b_title)

    av = _VOLUME_RE.search(at)
    bv = _VOLUME_RE.search(bt)
    if av and bv and av.group(1) != bv.group(1):
        return "series_volume"  # DANGER: distinct volumes, never merge

    a_toks = set(at.split())
    b_toks = set(bt.split())
    aa = set(_norm(a_author).split())
    ba = set(_norm(b_author).split())

    # BUG-604 signature: title words leaked into the other side's author field.
    if (aa and b_toks and (aa & b_toks)) or (ba and a_toks and (ba & a_toks)):
        return "author_leak"

    if any(m in (a_label + " " + b_label).lower() for m in _NOISE_MARKERS):
        return "noise_suffix"

    if a_toks and b_toks:
        overlap = len(a_toks & b_toks) / min(len(a_toks), len(b_toks))
        if overlap < 0.5:
            return "title_rename"  # genuinely different titles (Systemantics == Systems Bible)
        if at and (at in bt or bt in at):
            return "subtitle_or_edition"

    return "review"


def _merge_candidates(title_cands: list[dict], content_cands: list[dict]) -> list[dict]:
    """Combine + dedup the two detector outputs into one pair set, sorted by similarity."""
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for src, cands in (("title", title_cands), ("content", content_cands)):
        for c in cands:
            a_id = str(c["a_id"])
            b_id = str(c["b_id"])
            key = tuple(sorted((a_id, b_id)))
            rec = merged.get(key)
            if rec is None:
                rec = {
                    "a_id": a_id,
                    "b_id": b_id,
                    "a": str(c.get("a", "")),
                    "b": str(c.get("b", "")),
                    "detectors": [],
                    "max_similarity": 0.0,
                }
                merged[key] = rec
            rec["detectors"].append(src)
            rec["max_similarity"] = max(rec["max_similarity"], float(c.get("similarity", 0.0)))

    pairs: list[dict[str, Any]] = []
    for (a_id, b_id), rec in merged.items():
        rec["pair_id"] = _pair_id(a_id, b_id)
        rec["hint"] = _hint(rec["a"], rec["b"])
        rec["verdict"] = "PENDING"
        rec["owner_note"] = ""
        pairs.append(rec)

    pairs.sort(key=lambda p: p["max_similarity"], reverse=True)
    return pairs


def _preserve_verdicts(prev: dict[str, Any] | None, pairs: list[dict]) -> None:
    """Carry forward owner verdicts from a prior ledger, keyed by pair_id."""
    if not prev:
        return
    by_id = {p["pair_id"]: p for p in prev.get("pairs", [])}
    for p in pairs:
        old = by_id.get(p["pair_id"])
        if old and old.get("verdict") in _VALID_VERDICTS:
            p["verdict"] = old["verdict"]
            p["owner_note"] = old.get("owner_note", "")


def _crash_safe_write(path: Path, payload: dict[str, Any]) -> None:
    """C6: tempfile -> fsync -> os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".dup_gate_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _selftest() -> int:
    fails: list[str] = []

    # Control 1: pair_id is order-independent and distinct for distinct pairs.
    if _pair_id("aaa", "bbb") != _pair_id("bbb", "aaa"):
        fails.append("pair_id not order-independent")
    if _pair_id("aaa", "bbb") == _pair_id("aaa", "ccc"):
        fails.append("pair_id collision on distinct pairs")

    # Control 2: series volumes -> series_volume (never merge).
    h = _hint("Shane Parrish \u2014 The Great Mental Models, Volume 2: Physics",
              "Shane Parrish \u2014 The Great Mental Models, Volume 3: Systems")
    if h != "series_volume":
        fails.append(f"series volume not flagged: {h}")

    # Control 3: BUG-604 author leak -> author_leak.
    h = _hint("Totalitarianism Mattias Desmet \u2014 The Psychology of",
              "Mattias Desmet \u2014 The Psychology of Totalitarianism")
    if h != "author_leak":
        fails.append(f"author leak not flagged: {h}")

    # Control 4: genuine title rename (zero title overlap) -> title_rename.
    h = _hint("John Gall \u2014 Systemantics", "John Gall \u2014 The Systems Bible")
    if h != "title_rename":
        fails.append(f"title rename not flagged: {h}")

    if fails:
        print("FAIL gate_duplicate_candidates selftest: " + " | ".join(fails))
        return 2
    print("ok gate_duplicate_candidates selftest: 4/4 (order-indep id, series_volume, author_leak, title_rename)")
    return 0


def _run() -> int:
    cfg = _load_config()
    root = _PROJECT_ROOT
    title_path = root / cfg["title_candidates_file"]
    content_path = root / cfg["content_candidates_file"]
    ledger_path = root / cfg["ledger_file"]

    if not title_path.exists():
        print(f"error: missing title candidates {title_path}", file=sys.stderr)
        return 1
    if not content_path.exists():
        print(f"error: missing content candidates {content_path}", file=sys.stderr)
        return 1

    title_cands = _load_json(title_path).get("candidates", [])
    content_cands = _load_json(content_path).get("candidates", [])

    prev = _load_json(ledger_path) if ledger_path.exists() else None
    pairs = _merge_candidates(title_cands, content_cands)
    _preserve_verdicts(prev, pairs)

    hint_counts: dict[str, int] = {}
    for p in pairs:
        hint_counts[p["hint"]] = hint_counts.get(p["hint"], 0) + 1

    adjudicated = sum(1 for p in pairs if p["verdict"] != "PENDING")
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "kind": "owner_adjudication_ledger",
        "policy": (
            "never auto-merge; owner sets MERGE (alias duplicate) or KEEP_SEPARATE "
            "(distinct work/series volume) per pair; MERGE applies post-run because "
            "a source_id change repins the live fingerprint"
        ),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_from": [cfg["title_candidates_file"], cfg["content_candidates_file"]],
        "apply_threshold": float(cfg["apply_threshold"]),
        "candidate_count": len(pairs),
        "adjudicated": adjudicated,
        "pending": len(pairs) - adjudicated,
        "hint_counts": hint_counts,
        "pairs": pairs,
    }
    _crash_safe_write(ledger_path, payload)
    print(
        f"wrote {ledger_path} ({len(pairs)} pairs, {adjudicated} adjudicated, "
        f"{len(pairs) - adjudicated} pending)"
    )
    return 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return _selftest()
    return _run()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
