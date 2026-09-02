#!/usr/bin/env python3
"""remap_emerging.py — Phase 0a/0b post-S4 taxonomy remap (BUG-150 recurrence guard).

Reduces the `discipline == "emerging"` rate (and full domain collapse) WITHOUT
touching raw labels, fb_id, or taxonomy_version. Two phases:

    Phase 0a (Unicode fold): NFKC-normalize + fold Unicode dash/quote variants
        (e.g. 'human\u2013computer interaction' → 'human-computer interaction'),
        then re-match against the canonical set + kind-constrained synonym index.

    Phase 0b (alias map): for raw labels that still do not match, look up
        config/alias_map.yaml (curated mappings to EXISTING canonicals only).

Invariants (hard-failed):
    - discipline_raw / domains_raw are preserved VERBATIM (D2378/D2399).
    - fb_id is never touched (D2350).
    - taxonomy_version is NOT bumped (D2485: alias-only remap).
    - Any alias target that is not a canonical label → hard error at load.

Input default:  checkpoint_deduped.jsonl (dedup_fb_id.py output) else STAGE4_CHECKPOINT.
Output default: STAGE4_5_CHECKPOINT (the slot gate_emerging_rate + S5 prefer).

Usage:
    python3 scripts/remap_emerging.py [--input PATH] [--output PATH] [--dry-run]
Exit codes:
    0  success
    2  input checkpoint missing/unreadable, or alias target invalid
"""
from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import load_jsonl, safe_write, safe_write_jsonl
from pipeline.pipeline_paths import STAGE4_CHECKPOINT, STAGE4_5_CHECKPOINT, get_run_id
from pipeline.schemas import CANONICAL_DOMAINS, CANONICAL_DISCIPLINES, get_synonym_index

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALIAS_MAP_PATH = PROJECT_ROOT / "config" / "alias_map.yaml"
DEDUPED_CHECKPOINT = STAGE4_CHECKPOINT.parent / "checkpoint_deduped.jsonl"

# Unicode dash/quote folding (Phase 0a). NFKC alone does not fold all dashes.
_DASHES = "\u2010\u2011\u2012\u2013\u2014\u2015\u2212\uFE58\uFE63\uFF0D"
_QUOTES = "\u2018\u2019\u201A\u201B\u201C\u201D\u201E\u201F\u2032\u2033\u00B4\u02BC\uFF07"


def fold_label(label: str) -> str:
    """Phase 0a: NFKC + Unicode dash/quote fold + lowercase. Idempotent."""
    if not label:
        return ""
    s = unicodedata.normalize("NFKC", str(label))
    for ch in _DASHES:
        s = s.replace(ch, "-")
    for ch in _QUOTES:
        s = s.replace(ch, "'")
    return s.strip().lower()


def load_alias_map() -> dict[str, dict[str, str]]:
    """Load config/alias_map.yaml; validate every target is a canonical label."""
    import yaml
    if not ALIAS_MAP_PATH.exists():
        return {"discipline": {}, "domain": {}}
    with open(ALIAS_MAP_PATH) as f:
        data = yaml.safe_load(f) or {}
    disc_aliases = data.get("discipline_aliases", {}) or {}
    dom_aliases = data.get("domain_aliases", {}) or {}

    disc_canon = {c.lower() for c in CANONICAL_DISCIPLINES}
    dom_canon = {c.lower() for c in CANONICAL_DOMAINS}

    def _validate(aliases: dict, canon_set: set, kind: str) -> dict[str, str]:
        out: dict[str, str] = {}
        for raw, target in aliases.items():
            t = str(target).lower().strip()
            if t not in canon_set:
                print(f"❌ alias_map.yaml: {kind} alias {raw!r} → {target!r} "
                      f"is NOT a canonical {kind}.", file=sys.stderr)
                sys.exit(2)
            out[fold_label(raw)] = str(target).strip()
        return out

    return {
        "discipline": _validate(disc_aliases, disc_canon, "discipline"),
        "domain": _validate(dom_aliases, dom_canon, "domain"),
    }


def resolve(raw_label: str, kind: str, aliases: dict[str, str],
            syn_index: dict[str, str]) -> tuple[str | None, str | None]:
    """Resolve a raw label to a canonical label. Returns (canonical, method)."""
    folded = fold_label(raw_label)
    if not folded:
        return None, None
    canon_list = CANONICAL_DOMAINS if kind == "domain" else CANONICAL_DISCIPLINES
    for c in canon_list:
        if folded == c.lower():
            return c, "exact"
    if folded in syn_index:
        return syn_index[folded], "synonym"
    if folded in aliases:
        return aliases[folded], "alias"
    return None, None


def _write_expected_count_sidecar(dst: Path, count: int) -> None:
    """Refresh <dst>.expected_count.json to the post-dedup+remap count.

    D2496: S5's authoritative record-count check (preflight_checkpoint_check.py
    --expect-count) hard-fails on any mismatch. dedup legitimately merges
    duplicate fb_ids (reduces count) and remap never adds/drops records, so the
    S4-written expected count must be refreshed — otherwise S5 fails closed on a
    false-positive mismatch. Carries forward s2_input_fingerprint for provenance.
    """
    import json as _json
    import time as _time
    sidecar = Path(str(dst) + ".expected_count.json")
    src_sidecar = Path(str(STAGE4_CHECKPOINT) + ".expected_count.json")
    data: dict = {"expected_fb_count": count}
    if src_sidecar.exists():
        try:
            src = _json.loads(src_sidecar.read_text(encoding="utf-8"))
            data["s2_input_fingerprint"] = src.get("s2_input_fingerprint")
            data["s4_expected_fb_count"] = src.get("expected_fb_count")
        except (OSError, ValueError):
            pass
    data["pipeline_run_id"] = get_run_id()
    data["written_at"] = _time.time()
    safe_write(sidecar, _json.dumps(data, indent=2))


def remap_fb(fb: dict, disc_aliases: dict[str, str], dom_aliases: dict[str, str],
             disc_syn: dict[str, str], dom_syn: dict[str, str]) -> tuple[bool, bool]:
    """Rewrite canonical discipline/domains from raw labels in-place.

    Returns (discipline_changed, domains_changed).
    """
    disc_changed = False
    dom_changed = False

    # ── Discipline ──
    if fb.get("discipline") == "emerging" and fb.get("discipline_raw"):
        canon, method = resolve(fb["discipline_raw"], "discipline", disc_aliases, disc_syn)
        if canon and canon != "emerging":
            fb["discipline"] = canon
            fb["taxonomy_match_method"] = method
            disc_changed = True

    # ── Domains (full/partial collapse — replace 'emerging' entries) ──
    # Conservative: keep the 'emerging' placeholder if ANY raw domain still
    # fails to resolve, so no raw label is silently dropped from the canonical
    # representation (raw labels remain in domains_raw regardless).
    domains = fb.get("domains") or []
    if "emerging" in domains:
        raw_list = fb.get("domains_raw") or []
        resolved: list[str] = []
        unresolved = 0
        for raw in raw_list:
            if not isinstance(raw, str):
                continue
            canon, _ = resolve(raw, "domain", dom_aliases, dom_syn)
            if canon and canon != "emerging":
                resolved.append(canon)
            else:
                unresolved += 1
        if resolved:
            new_domains = [d for d in domains if d != "emerging"] + resolved
            if unresolved > 0:
                new_domains.append("emerging")
            fb["domains"] = sorted(set(new_domains))
            dom_changed = True

    return disc_changed, dom_changed


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 0a/0b post-S4 emerging remap (BUG-150)")
    ap.add_argument("--input", type=Path, default=None,
                    help="checkpoint to remap (default: checkpoint_deduped.jsonl else STAGE4_CHECKPOINT)")
    ap.add_argument("--output", type=Path, default=None,
                    help="output checkpoint (default: STAGE4_5_CHECKPOINT)")
    ap.add_argument("--dry-run", action="store_true", help="measure only, do not write")
    args = ap.parse_args()

    src = args.input or (DEDUPED_CHECKPOINT if DEDUPED_CHECKPOINT.exists() else STAGE4_CHECKPOINT)
    dst = args.output or STAGE4_5_CHECKPOINT

    if not src.exists():
        print(f"❌ remap input checkpoint not found: {src}", file=sys.stderr)
        return 2

    aliases = load_alias_map()
    disc_syn = get_synonym_index("discipline")
    dom_syn = get_synonym_index("domain")

    fbs = load_jsonl(src, context="S4 checkpoint (remap)")
    n = len(fbs)
    disc_before = sum(1 for fb in fbs if fb.get("discipline") == "emerging")
    dom_before = sum(1 for fb in fbs if fb.get("domains") == ["emerging"])

    disc_remapped = 0
    dom_remapped = 0
    by_method: dict[str, int] = {}
    for fb in fbs:
        dc, dm = remap_fb(fb, aliases["discipline"], aliases["domain"], disc_syn, dom_syn)
        if dc:
            disc_remapped += 1
            m = fb.get("taxonomy_match_method", "?")
            by_method[m] = by_method.get(m, 0) + 1
        if dm:
            dom_remapped += 1

    disc_after = sum(1 for fb in fbs if fb.get("discipline") == "emerging")
    dom_after = sum(1 for fb in fbs if fb.get("domains") == ["emerging"])

    print("=" * 60)
    print("🔁 PHASE 0a/0b EMERGING REMAP")
    print(f"   input:  {src}")
    print(f"   total:  {n}")
    print("-" * 60)
    print(f"   discipline 'emerging': {disc_before} → {disc_after} "
          f"({disc_before/n:.1%} → {disc_after/n:.1%})")
    print(f"   discipline remapped:   {disc_remapped}  by_method={dict(by_method)}")
    print(f"   domains ['emerging']:  {dom_before} → {dom_after} "
          f"({dom_before/n:.1%} → {dom_after/n:.1%})")
    print(f"   domains cleaned:        {dom_remapped} (full/partial collapse)")
    print("=" * 60)

    if not args.dry_run:
        safe_write_jsonl(dst, fbs)
        _write_expected_count_sidecar(dst, len(fbs))
        print(f"✅ wrote {dst}")
    else:
        print("(dry-run — nothing written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
