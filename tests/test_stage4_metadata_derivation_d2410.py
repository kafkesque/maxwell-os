"""D2410 regression tests — S4 metadata derivation correctness.

Covers the three audit fixes from the canary deep audit:
  1. temporal_scope: boundary-aware keyword matching (no stopword-like "all" /
     substring "now" false-hits) + contemporary-first ordering.
  2. difficulty_level: config-first depth→difficulty mapping with domain
     cardinality (single→expert, multi→intermediate).
  3. context: "general" is a valid routing label for unmatched domains.

These are pure derivation units — no LLM/OMLX required.
"""

from __future__ import annotations

from pipeline.intimacy_lattice import derive_context
from pipeline.pipeline_paths import S4_DIFFICULTY_MAP, S4_TEMPORAL_SIGNALS
from pipeline.schemas import CONTEXT_LITERAL
from pipeline.stage4_merge import _derive_difficulty_level, _temporal_signal_hit


# ── Fix 1: temporal_scope ──────────────────────────────────────────────────
def test_temporal_signal_boundary_no_substring_false_hits() -> None:
    """"now" must not match inside "knowledge"/"renowed"; "all" is not a signal."""
    timeless = S4_TEMPORAL_SIGNALS.get("timeless", [])
    contemporary = S4_TEMPORAL_SIGNALS.get("contemporary", [])

    # "renowed" contains "now" but is NOT a contemporary decay signal.
    assert not _temporal_signal_hit("always renowed principle", contemporary)
    # "knowledge" contains "now" but is NOT contemporary.
    assert not _temporal_signal_hit("the knowledge is fundamental", contemporary)
    # "allocation" contains "all" — "all" is no longer a timeless signal.
    assert not _temporal_signal_hit("resource allocation", timeless)
    # Standalone "now" IS contemporary.
    assert _temporal_signal_hit("this holds now", contemporary)
    # Year prefix "2024" is caught by the numeric "202" signal.
    assert _temporal_signal_hit("in 2024 the model", contemporary)


def test_temporal_scope_contemporary_first_when_both_present() -> None:
    """A decay signal should beat a timeless signal ("always now" → contemporary)."""
    timeless = S4_TEMPORAL_SIGNALS.get("timeless", [])
    contemporary = S4_TEMPORAL_SIGNALS.get("contemporary", [])

    def resolve(text: str) -> str:
        if _temporal_signal_hit(text, contemporary):
            return "contemporary"
        if _temporal_signal_hit(text, timeless):
            return "timeless"
        return "timeless"  # default

    assert resolve("always universal now") == "contemporary"
    assert resolve("always universal fundamental") == "timeless"
    assert resolve("no temporal signal here") == "timeless"


def test_temporal_signals_no_bare_all_signal() -> None:
    """Config regression: bare "all" must be absent from timeless signals."""
    assert "all" not in S4_TEMPORAL_SIGNALS.get("timeless", [])


# ── Fix 2: difficulty_level ────────────────────────────────────────────────
def test_difficulty_map_is_config_first_and_complete() -> None:
    """The live config map must expose all five derivation keys."""
    assert set(S4_DIFFICULTY_MAP) == {
        "specialized",
        "universal",
        "cross-domain",
        "domain_single",
        "domain_multi",
    }
    assert S4_DIFFICULTY_MAP["specialized"] == "expert"
    assert S4_DIFFICULTY_MAP["universal"] == "beginner"
    assert S4_DIFFICULTY_MAP["cross-domain"] == "intermediate"
    assert S4_DIFFICULTY_MAP["domain_single"] == "expert"
    assert S4_DIFFICULTY_MAP["domain_multi"] == "intermediate"


def test_derive_difficulty_level_parity() -> None:
    """Behavior parity with the prior hardcoded branch."""
    assert _derive_difficulty_level("specialized", 1) == "expert"
    assert _derive_difficulty_level("universal", 1) == "beginner"
    assert _derive_difficulty_level("cross-domain", 2) == "intermediate"
    assert _derive_difficulty_level("domain", 1) == "expert"  # single → expert
    assert _derive_difficulty_level("domain", 3) == "intermediate"  # multi → intermediate
    assert _derive_difficulty_level("weird", 1) == "intermediate"  # conservative fallback


# ── Fix 3: context "general" ───────────────────────────────────────────────
def test_context_literal_includes_general() -> None:
    """Schema drift fix: "general" is a valid context routing label."""
    assert "general" in CONTEXT_LITERAL.__args__


def test_derive_context_general_for_unmatched_domains() -> None:
    """Unmatched domains must route to "general" (neutral), never "personal"."""
    assert derive_context({"domains": ["totally-unrecognized-domain"]}) == "general"
    assert derive_context({"domains": []}) == "general"
    assert "personal" not in derive_context({"domains": ["totally-unrecognized-domain"]})
