#!/usr/bin/env python3
"""scripts/extend_alias_index.py — D2566 bulk alias extension (unblocks enrichment + Track B).

Maps high-frequency UNMAPPED raw labels (``domains_raw`` / ``discipline_raw``) to
canonical domains / disciplines, extending the retrieval alias index so that:

  * cross-domain enrichment (~1,850 FBs, D2565) unblocks — a raw label that maps
    to a canonical domain can be ADDED to an FB's ``domains`` array;
  * emerging resolution (Track B, D2532) unblocks — a raw label that maps to a
    canonical discipline lets the re-classifier lift ``discipline='emerging'``.

R5 (generator != verifier, different model families):
    generator = Qwen3.8-27B-MLX-4bit   (proposes raw -> canonical, bulk)
    verifier  = gpt-oss-20b-MXFP4-Q8   (independently re-maps the same batch)
    A mapping is ACCEPTED only when both models agree on the same canonical.

Deterministic pass runs FIRST (no LLM): canonical-self, Unicode/dash fold, and
compound split ("marketing & advertising" -> map each token). The LLM pass only
sees labels that survive deterministic mapping.

Output: ``config/alias_map.yaml`` (``domain_aliases`` + ``discipline_aliases``).
Default is DRY-RUN. ``--apply`` requires a timestamped config backup + atomic
replace (C6/C13). No silent errors (C16).

Usage:
  python3 scripts/extend_alias_index.py --top-domains 300 --top-disciplines 200
  python3 scripts/extend_alias_index.py --top-domains 300 --top-disciplines 200 --apply
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import yaml  # noqa: E402

from pipeline.pipeline_paths import DB_PATH  # noqa: E402
from pipeline.omlx_call import call_omlx  # noqa: E402
from pipeline.schemas import (  # noqa: E402
    CANONICAL_DISCIPLINES,
    CANONICAL_DOMAINS,
    get_synonym_index,
)

_ALIAS_MAP = _ROOT / "config" / "alias_map.yaml"

# ── Config-driven tunables (C12: no hardcoded magic numbers) ────────────────
_GEN_MODEL = "Qwen3.8-27B-MLX-4bit"
_VERIFY_MODEL = "gpt-oss-20b-MXFP4-Q8"
_LABELS_PER_BATCH = 50
_LLM_TIMEOUT = 600
_LLM_MAX_TOKENS = 3000

# Compound separators: a raw label with these is co-occurrence, not one category.
_COMPOUND_RE = re.compile(r"\s*(?:&|\+|/|\band\b|\bvs\.?\b|,)\s*", re.IGNORECASE)

# Deterministic suffix-strip: "user experience research" -> "user experience" is a
# safe re-try against the index BEFORE the LLM is consulted.
_SUFFIXES = ("research", "studies", "practice", "design", "development", "management",
             "engineering", "production", "theory", "analysis", "analytics", "methodology")


def _fold(label: str) -> str:
    """NFKC + dash/quote fold + whitespace collapse (mirrors schemas.normalize_label)."""
    s = unicodedata.normalize("NFKC", label or "")
    for ch in "\u2010\u2011\u2012\u2013\u2014\u2015\u2212\uFE58\uFE63\uFF0D":
        s = s.replace(ch, "-")
    for ch in "\u2018\u2019\u201A\u201B\u201C\u201D":
        s = s.replace(ch, "'")
    return re.sub(r"\s+", " ", s.strip().lower())


def _parse_raw(v: str | None) -> list[str]:
    """Parse a raw-label column (JSON array or pipe-delimited) into strings."""
    if not v:
        return []
    s = v.strip()
    if s.startswith("["):
        try:
            return [str(x).strip() for x in json.loads(s) if str(x).strip()]
        except (json.JSONDecodeError, TypeError):
            return []
    return [x.strip() for x in s.split("|") if x.strip()]


def _load_existing_aliases() -> tuple[set[str], set[str]]:
    """Return (domain_keys, discipline_keys) already curated in alias_map.yaml.

    These are human-approved overrides (D2498 et al.) and MUST be preserved —
    the LLM pass is not allowed to re-map or overwrite them (regression guard).
    """
    dom_keys: set[str] = set()
    disc_keys: set[str] = set()
    if _ALIAS_MAP.exists():
        data = yaml.safe_load(open(_ALIAS_MAP, encoding="utf-8")) or {}
        dom_keys = {_fold(k) for k in (data.get("domain_aliases", {}) or {})}
        disc_keys = {_fold(k) for k in (data.get("discipline_aliases", {}) or {})}
    return dom_keys, disc_keys


def _extract_unmapped(where_col: str, exclude: set[str], kind: str) -> Counter:
    """Return unmapped raw labels (folded) ranked by frequency, for one column.

    Excludes labels already in the KIND-constrained synonym index (domain raw
    labels must not be excluded by a same-named *discipline* alias, D2133) AND
    already-curated alias_map entries (exclude) — neither is eligible for
    re-mapping.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    idx = get_synonym_index(kind)  # canonical-self + taxonomy raw + synonym_map + alias_map
    counter: Counter = Counter()
    try:
        for r in conn.execute(f"SELECT {where_col} FROM fbs"):
            for x in _parse_raw(r[0]):
                key = _fold(x)
                if key and key not in idx and key not in exclude:
                    counter[key] += 1
    finally:
        conn.close()
    return counter


def _deterministic_map(label: str, idx: dict[str, str], canon: set[str]) -> str | list[str] | None:
    """Deterministic raw->canonical resolution (self + fold + compound). No LLM.

    Returns the canonical (or list of canonicals for a compound), or None.
    """
    key = _fold(label)
    if key in idx:
        return idx[key]
    toks = [t for t in _COMPOUND_RE.split(key) if t]
    if len(toks) > 1:
        mapped: list[str] = []
        for t in toks:
            if t in idx:
                mapped.append(idx[t])
            elif t in canon:
                mapped.append(t)
        if mapped:
            # de-dup, keep canonical order
            return list(dict.fromkeys(mapped))
    # suffix strip re-try
    for suf in _SUFFIXES:
        if key.endswith(" " + suf):
            stem = key[: -(len(suf) + 1)].strip()
            if stem in idx:
                return idx[stem]
    return None


def _bulk_map(labels: list[str], canon: list[str], model: str) -> dict[str, str | list[str]]:
    """One-shot bulk map of labels -> canonicals (single JSON output).

    Uses the pipeline's `call_omlx` (not raw requests) so reasoning-model
    cold-reloads that return only `reasoning_content` are retried instead of
    crashing (D2359), and the circuit breaker / retry backoff apply.
    """
    prompt = (
        "Map each RAW LABEL to the SINGLE best canonical from the list. "
        "If a label genuinely spans two canonicals (e.g. \"marketing & branding\"), "
        "return a JSON array of 1-2 canonicals. If NO canonical fits well, return null. "
        "Return ONLY JSON: {\"mappings\": {\"<raw label>\": <canonical-or-array-or-null>}}\n\n"
        f"CANONICALS:\n{', '.join(canon)}\n\n"
        f"RAW LABELS:\n{json.dumps(labels)}"
    )
    content = call_omlx(
        prompt=prompt,
        model=model,
        system="You are a precise JSON generator. Return ONLY valid JSON. No markdown, no explanation.",
        max_tokens=_LLM_MAX_TOKENS,
        timeout=_LLM_TIMEOUT,
    )
    # tolerate a leading/trailing prose or code fence
    m = re.search(r"\{.*\}", content, re.DOTALL)
    if not m:
        raise ValueError(f"no JSON object in model output: {content[:120]!r}")
    data = json.loads(m.group(0))
    mappings = data.get("mappings", {})
    out: dict[str, str | list[str]] = {}
    canon_set = set(canon)
    for raw, target in mappings.items():
        if target is None:
            continue
        if isinstance(target, list):
            target = [t for t in target if t in canon_set]
            if target:
                out[_fold(raw)] = target
        elif isinstance(target, str) and target in canon_set:
            out[_fold(raw)] = target
    return out


def _normalize_target(t: str | list[str]) -> str | list[str]:
    return t if isinstance(t, list) else [t]


def main() -> int:
    parser = argparse.ArgumentParser(description="D2566 bulk alias extension.")
    parser.add_argument("--top-domains", type=int, default=300)
    parser.add_argument("--top-disciplines", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=_LABELS_PER_BATCH)
    parser.add_argument("--apply", action="store_true", help="write to alias_map.yaml")
    args = parser.parse_args()

    canon_dom = [c for c in CANONICAL_DOMAINS if c != "emerging"]
    canon_disc = [c for c in CANONICAL_DISCIPLINES if c != "emerging"]
    idx_dom = get_synonym_index("domain")
    idx_disc = get_synonym_index("discipline")
    dom_existing, disc_existing = _load_existing_aliases()

    dom_unmapped = _extract_unmapped("domains_raw", dom_existing, "domain")
    disc_unmapped = _extract_unmapped("discipline_raw", disc_existing, "discipline")
    print(f"unmapped domains_raw: {len(dom_unmapped)} labels / {sum(dom_unmapped.values())} occurrences")
    print(f"unmapped discipline_raw: {len(disc_unmapped)} labels / {sum(disc_unmapped.values())} occurrences")

    # ── deterministic pass ──────────────────────────────────────────────────
    dom_det: dict[str, str | list[str]] = {}
    for lbl in list(dom_unmapped):
        m = _deterministic_map(lbl, idx_dom, set(canon_dom))
        if m:
            dom_det[lbl] = m
            del dom_unmapped[lbl]
    disc_det: dict[str, str | list[str]] = {}
    for lbl in list(disc_unmapped):
        m = _deterministic_map(lbl, idx_disc, set(canon_disc))
        if m:
            disc_det[lbl] = m
            del disc_unmapped[lbl]
    print(f"deterministic: domain {len(dom_det)} / discipline {len(disc_det)} mapped")

    # ── LLM pass: top-N by frequency, generator + verifier agreement ────────
    def llm_pass(unmapped: Counter, canon: list[str], top_n: int) -> dict[str, str | list[str]]:
        labels = [lbl for lbl, _ in unmapped.most_common(top_n)]
        agreed: dict[str, str | list[str]] = {}
        for i in range(0, len(labels), args.batch_size):
            chunk = labels[i:i + args.batch_size]
            gen = _bulk_map(chunk, canon, _GEN_MODEL)
            ver = _bulk_map(chunk, canon, _VERIFY_MODEL)
            for lbl in chunk:
                g, v = gen.get(lbl), ver.get(lbl)
                if g is None or v is None:
                    continue
                if set(_normalize_target(g)) == set(_normalize_target(v)):
                    agreed[lbl] = g
            print(f"  batch {i // args.batch_size + 1}: {len(agreed)} agreed so far")
        return agreed

    print(f"\nLLM pass (generator={_GEN_MODEL} vs verifier={_VERIFY_MODEL}):")
    dom_llm = llm_pass(dom_unmapped, canon_dom, args.top_domains)
    disc_llm = llm_pass(disc_unmapped, canon_disc, args.top_disciplines)
    print(f"LLM-agreed: domain {len(dom_llm)} / discipline {len(disc_llm)}")

    # ── merge accepted (deterministic + LLM-agreed) ─────────────────────────
    dom_new = {k: _normalize_target(v) for k, v in {**dom_det, **dom_llm}.items()}
    disc_new = {k: _normalize_target(v) for k, v in {**disc_det, **disc_llm}.items()}
    print(f"\nTOTAL accepted new aliases: domain {len(dom_new)} / discipline {len(disc_new)}")

    if not args.apply:
        print("\n🔍 DRY-RUN — no write. Re-run with --apply to persist.")
        for lbl in sorted(dom_new)[:40]:
            print(f"  [domain] {lbl!r} -> {dom_new[lbl]}")
        for lbl in sorted(disc_new)[:40]:
            print(f"  [discipline] {lbl!r} -> {disc_new[lbl]}")
        return 0

    # ── write alias_map.yaml (backup + atomic replace, C6/C13) ──────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = _ALIAS_MAP.with_name(f"alias_map.yaml.bak_{ts}_pre_extend")
    shutil.copy2(_ALIAS_MAP, bak)
    with open(bak, "rb") as f:
        os.fsync(f.fileno())
    print(f"  🔒 Backup: {bak}")

    existing = yaml.safe_load(open(_ALIAS_MAP, encoding="utf-8")) or {}
    da = dict(existing.get("domain_aliases", {}) or {})
    di = dict(existing.get("discipline_aliases", {}) or {})
    # Add-only: never overwrite a curated alias (regression guard, D2566).
    for k, v in dom_new.items():
        if k not in da:
            da[k] = v[0] if len(v) == 1 else v
    for k, v in disc_new.items():
        if k not in di:
            di[k] = v[0] if len(v) == 1 else v
    existing["domain_aliases"] = da
    existing["discipline_aliases"] = di

    tmp = _ALIAS_MAP.with_name(f"alias_map.yaml.tmp_{ts}")
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.safe_dump(existing, f, sort_keys=False, allow_unicode=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, _ALIAS_MAP)  # C6: atomic replace
    print(f"✅ wrote {len(dom_new)} domain + {len(disc_new)} discipline aliases to alias_map.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
