#!/usr/bin/env python3
"""verify_source_identity.py — fail-closed rail for the canonical source_id invariant (D2176).

WHY THIS RAIL EXISTS (BUG-289 / D-273e): `source_diversity` used to count book
FILENAMES, so the same work ingested under two editions/download-sources counted as
TWO distinct sources. Measured: 29.1% of "convergence" (757/2597 rows) was the same
book twice, and 369 work-identities carried >1 filename. Because `source_diversity`
is the S1.5 merge criterion, that defect inflated `is_convergent` (the corpus's
headline quality claim) and produced the "20+ duplicate book sources" seen across
S1.5 / S2 / S4-d.

THE FIX (D2176 + D2308/D2315/D2507/D2509/D2449/D2459): source_diversity is now
computed over CANONICAL source_ids — SHA-256(normalized_author | normalized_title) —
via pipeline/book_metadata.resolve_source_ids(). Edition variants (subtitle split,
casing, co-author lists, unicode, piracy-site noise) collapse to one hash.

THIS RAIL enforces two things fail-closed:
  1. The canonicalization itself (known-answer controls): the same work under two
     filenames MUST resolve to one source_id, and two distinct works MUST NOT.
  2. The metadata cache resolves author+title for (effectively) every book, so the
     filename-fallback branch of compute_source_id() — which WOULD reintroduce
     filename-based divergence — is never the live path.

Exit codes:
  0  canonical source-identity invariant holds
  1  violation detected (fail loudly, C16)
  2  config misconfigured / unreadable
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

try:
    import yaml
except ImportError:  # pragma: no cover - diagnostic path
    yaml = None  # type: ignore[assignment]

from pipeline.book_metadata import (  # noqa: E402
    compute_source_id,
    is_sentinel_author,
    resolve_source_id,
    resolve_source_ids,
)


def _load_config() -> dict[str, Any]:
    """Load the source_identity block from config/eval_integrity.yaml (C12)."""
    if yaml is None:
        print("❌ PyYAML unavailable — cannot read config", file=sys.stderr)
        sys.exit(2)
    cfg_path = _PROJECT_ROOT / "config" / "eval_integrity.yaml"
    try:
        with open(cfg_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    except OSError as e:
        print(f"❌ cannot read {cfg_path}: {e}", file=sys.stderr)
        sys.exit(2)
    block = cfg.get("source_identity") or {}
    if not isinstance(block, dict):
        print("❌ source_identity block is malformed", file=sys.stderr)
        sys.exit(2)
    return block


# ── Known-answer controls (BUG-492): each is a (name, got, want) assertion ───
def _selftest() -> int:
    """Run the known-answer canonicalization controls. Returns exit code."""
    checks: list[tuple[str, str, str]] = []

    # 1. Same work, two edition filenames -> ONE source_id (the core D2176 fix).
    a = resolve_source_id("About Face The Essentials of Interaction Design (Alan Cooper) (z-lib).md")
    b = resolve_source_id("About Face. The Essentials of Interaction Design (Alan Cooper).md")
    checks.append(("same-work-2-editions-collapse", a, b))

    # 2. Two distinct works -> DISTINCT source_ids (no false merge).
    c = resolve_source_id("Design The Key Concepts (D. J. Huppatz).md")
    d = resolve_source_id("The Design of Everyday Things (Don Norman).md")
    checks.append(("distinct-works-stay-distinct", "distinct" if c != d else "equal", "distinct"))

    # 3. Subtitle split: colon edition == space-separated edition (D2507).
    e = compute_source_id("Malcolm Gladwell", "Blink: The Power of Thinking Without Thinking")
    f = compute_source_id("Malcolm Gladwell", "Blink The Power of Thinking Without Thinking")
    checks.append(("subtitle-split-collapses", e, f))

    # 4. Co-author list collapses to primary author (D2308).
    g = compute_source_id("Anthony Dunne, Fiona Raby", "Speculative Everything")
    h = compute_source_id("Anthony Dunne", "Speculative Everything")
    checks.append(("coauthor-collapses", g, h))

    # 5. Sentinel authors are filtered, never hashed into identity (D2459/BUG-175).
    if is_sentinel_author("Unknown") and is_sentinel_author("string") and not is_sentinel_author("Don Norman"):
        checks.append(("sentinel-author-filtered", "ok", "ok"))
    else:
        checks.append(("sentinel-author-filtered", "BAD", "ok"))

    # 6. resolve_source_ids is a SET: duplicate filenames collapse to one id.
    ids = resolve_source_ids([
        "About Face The Essentials of Interaction Design (Alan Cooper) (z-lib).md",
        "About Face. The Essentials of Interaction Design (Alan Cooper).md",
    ])
    checks.append(("source_ids-set-collapses", str(len(ids)), "1"))

    failures = 0
    for name, got, want in checks:
        ok = got == want
        status = "ok" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"  [{status}] {name}: got={got!r} want={want!r}")
    if failures:
        print(f"❌ selftest: {failures}/{len(checks)} controls FAILED — canonical source_id has REGRESSED")
        return 1
    print(f"ok source_identity selftest: {len(checks)}/{len(checks)} controls fired (D2176 canonicalization intact)")
    return 0


def _live_check() -> int:
    """Verify the metadata cache resolves author+title for (effectively) every book."""
    block = _load_config()
    cache_rel = block.get("metadata_cache_file") or "knowledge pipeline/checkpoints/book_metadata.jsonl"
    max_ratio = float(block.get("max_both_unknown_ratio", 0.0))
    cache_path = _PROJECT_ROOT / cache_rel
    if not cache_path.exists():
        print(f"❌ metadata cache not found: {cache_path}", file=sys.stderr)
        return 1

    total = 0
    both_unknown = 0
    with open(cache_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            sb = (rec.get("source_book") or rec.get("source_path") or "").strip()
            if not sb:
                continue
            total += 1
            author = (rec.get("author") or "").strip()
            title = (rec.get("title") or "").strip()
            author_unknown = (not author) or author in ("Unknown Author", "Unknown", "string") or is_sentinel_author(author)
            title_unknown = (not title) or title == "Unknown Title"
            if author_unknown and title_unknown:
                both_unknown += 1

    ratio = both_unknown / total if total else 0.0
    if total == 0:
        print("❌ metadata cache empty — cannot verify source-identity coverage", file=sys.stderr)
        return 1
    if ratio > max_ratio:
        print(
            f"❌ source_identity: {both_unknown}/{total} books ({ratio:.4f}) resolve to "
            f"BOTH-UNKNOWN metadata — the filename-fallback branch of compute_source_id() is "
            f"live and can reintroduce filename-based divergence (BUG-289). Threshold {max_ratio}."
        )
        return 1
    print(
        f"ok source_identity live (D2176): {total} metadata records, {both_unknown} both-unknown "
        f"({ratio:.4f}) ≤ {max_ratio} — canonical SHA-256(author|title) is the live source_id path, "
        f"filename-fallback is not"
    )
    return 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return _selftest()
    return _live_check()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
