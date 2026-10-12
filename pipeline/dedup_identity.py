"""pipeline/dedup_identity.py — deterministic FB identity + duplicate classification (D-2950).

Root cause (D-2949): fb_id = SHA-256(name + definition) is definition-sensitive, so two
extractions of the SAME concept with slightly different definitions produced different
fb_ids and both survived commit. The fix is a deterministic, LLM-free identity model:

  GROUPING key  = (normalize_name(name), source_id)  -> candidate duplicates
  MERGE gate    = semantic divergence of the body     -> convergent  => same concept
                  (merge, keep richer); divergent => distinct concepts sharing a name inside
                  ONE source (keep both, disambiguate).

No LLM anywhere in this module (D-343). All thresholds load from
config/dedup_identity.yaml (C12); the in-file values are fail-safe defaults only.
"""
from __future__ import annotations

import json
import re
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "dedup_identity.yaml"


@lru_cache(maxsize=1)
def _config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"dedup_identity: missing config {CONFIG_PATH} — fail-closed (C12/C16)"
        )
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "divergence" not in data:
        raise ValueError(f"dedup_identity: config {CONFIG_PATH} missing 'divergence' block (C12)")
    return data


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def normalize_name(name: str) -> str:
    """Deterministic concept-name folding (NFKC+NFKD, lowercase, alnum-only tokens)."""
    return re.sub(r"[^a-z0-9]+", " ", _fold((name or "").lower())).strip()


def source_set(value: object) -> frozenset[str]:
    """Coerce a source-identity cell to a set — the ONE home for that shape (C21).

    The store holds `source_ids` as JSON text (``'["c2a742fc6061fab8"]'``) while the S5
    checkpoint holds a real list, and `frozenset(<str>)` silently explodes a JSON string into
    its CHARACTERS — which would make two rows from the same work read as different works, or
    worse, as a same-work group by accident. Every caller goes through here.
    """
    if not value:
        return frozenset()
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return frozenset()
        try:
            parsed = json.loads(text)
        except (ValueError, TypeError):
            return frozenset({text})
        if isinstance(parsed, (list, tuple, set, frozenset)):
            return frozenset(str(v) for v in parsed if str(v).strip())
        return frozenset({str(parsed)}) if str(parsed).strip() else frozenset()
    if isinstance(value, (list, tuple, set, frozenset)):
        return frozenset(str(v) for v in value if str(v).strip())
    return frozenset({str(value)})


def body_tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def jaccard(a: str, b: str) -> float:
    ta, tb = body_tokens(a), body_tokens(b)
    if not ta | tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def seq_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


def body_text(member: dict) -> str:
    return f"{member.get('definition', '')} {member.get('mechanism', '')}"


def _pair_divergent(a: str, b: str, j_min: float, s_min: float, require_both: bool) -> bool:
    """Divergence of ONE body pair: below threshold on EITHER metric, or on BOTH if required."""
    j = jaccard(a, b)
    s = seq_ratio(a, b)
    if require_both:
        return j < j_min and s < s_min
    return j < j_min or s < s_min


def is_divergent(members: list[dict]) -> bool:
    """True when the same-name+same-work rows describe DIFFERENT concepts (keep both).

    Evaluated over EVERY pair, and divergent if ANY pair diverges. Comparing only the first
    two members (the pre-D-2951 form) made the verdict depend on ROW ORDER for a group of 3+,
    and a transitive-looking group (A~B, B~C, A~C divergent) is not one concept. The rule is
    deliberately one-sided: a false "divergent" keeps two rows (visible, recoverable), while a
    false "convergent" links a distinct concept out of serving — so doubt goes to keep-both.
    """
    cfg = _config()["divergence"]
    j_min = float(cfg["merge_jaccard_min"])
    s_min = float(cfg["merge_seq_min"])
    require_both = bool(cfg.get("require_both", False))
    if len(members) < 2:
        return False
    bodies = [body_text(m) for m in members]
    for i in range(len(bodies)):
        for k in range(i + 1, len(bodies)):
            if _pair_divergent(bodies[i], bodies[k], j_min, s_min, require_both):
                return True
    return False


def _same_work(sources: list[frozenset[str]]) -> bool:
    """True when every member's source identity OVERLAPS every other's.

    "Which work" is decided by OVERLAP, not set equality: a concept extracted twice from one
    book can carry different convergence evidence (row A {s1}, row B {s1, s2}). Equality would
    call that a name collision and keep a duplicate alive instead of merging it. EVERY pair must
    overlap — a mixed group is not one work, and mixed falls back to keep-both.
    """
    for i in range(len(sources)):
        for k in range(i + 1, len(sources)):
            if not (sources[i] & sources[k]):
                return False
    return True


def classify_group(members: list[dict]) -> str:
    """Classify a same-normalized-name group of FB rows.

    Returns one of:
      'merge'               same name + same work, convergent body -> merge (keep richer)
      'same_source_collide' same name + same work, divergent body  -> keep both (disambiguate)
      'name_collide'        same name, >1 work (or a mixed group)  -> keep both (distinct works)
      'no_source'           ANY member missing source_ids -> owner review (never auto-merge)
      'unique'              single row -> not a duplicate

    EVERY member must carry a source identity before ANY same-work verdict: a row whose
    provenance is unknown cannot be merged on the strength of its neighbour's source, so one
    blank source fails the whole group closed to owner review (C16).
    """
    if len(members) < 2:
        return "unique"
    sources = [source_set(m.get("source_ids")) for m in members]
    if any(not s for s in sources):
        return "no_source"
    if _same_work(sources):
        return "same_source_collide" if is_divergent(members) else "merge"
    return "name_collide"
