"""axis_authority.py — single source of truth for 4-axis authoritative provenance sets.

D2626 (2026-09-14): the authoritative-provenance sets were previously duplicated
across `scripts/merge_4axis_adjudication.py` (as CT_ORIG/CT_FILL/CT_SPOT etc.) and
`scripts/build_4axis_tiers.py` (as CT_AUTH/DEPTH_AUTH/DISC_AUTH/DOM_AUTH). The
forensic audit (D2625, finding #2) showed the two copies could drift apart —
a bug class that silently corrupts tier placement. This module is the ONE place
the sets are defined; both consumers import from here, so drift is impossible by
construction.

Layout (one per axis):
  *_AUTH   = the post-merge authoritative set (what a "spotless" row may cite)
  *_ORIG   = the pre-merge verified subset (never overwritten; already authoritative)
  *_FILL   = *_AUTH - *_ORIG  (sources THIS merge/adjudication may write)

Invariant (asserted at import): *_AUTH == *_ORIG | *_FILL, and *_ORIG ⊆ *_AUTH.

No magic strings: every value here is a provenance source label from the merge
and tier contracts. If a new human-adjudication source is added to the pipeline,
add it to the relevant *_AUTH set HERE (and nowhere else).
"""
from __future__ import annotations

# ── content_type (7-way) ────────────────────────────────────────────────────
CT_ORIG = frozenset({"human", "joint-vote", "298-human"})
CT_FILL = frozenset({
    "p5:human-frontier69", "p5:human", "p5:human-d2615",
    # D2631 (2026-09-14): single-model Qwen3.8 content_type re-verify (D2629) is
    # the gate admitting the 59 expansion-queue rows as "principle"; cross-checked
    # against the original d2615 human label (depth/disc/domains are reliable-pair).
    "p5:qwen38-ct-D2629",
})

# ── depth (4-way) ───────────────────────────────────────────────────────────
DP_ORIG = frozenset({"human", "joint-vote", "298-human", "n/a-non-principle"})
DP_FILL = frozenset({
    "p5:human-frontier69", "p5:human-d2615",
    "p5:reliable-pair-D2619-revote", "p5:human-locked",
    "p5:reliable-pair-D2631-revote",
})

# ── discipline (61-way, singular) ───────────────────────────────────────────
DISC_ORIG = frozenset({"p5:claude+human", "p5:human"})
DISC_FILL = frozenset({
    "p5:human-D2618p1", "p5:reliable-pair-D2618p1", "p5:human-frontier69",
    "p5:human", "p5:human-emerging-gap", "p5:human-locked",
    "p5:reliable-pair-D2619-revote",
    "p5:reliable-pair-D2631-revote",
})

# ── domains (43-way, multi-label) ───────────────────────────────────────────
DOM_ORIG = frozenset({"p5:claude+human", "p5:human"})
DOM_FILL = frozenset({
    "p5:human-D2618p1", "p5:human-frontier69", "p5:human", "p5:human-locked",
    # D2633 (2026-09-14, user ruling): reliable-pair domain UNION (overlap->union,
    # always incl. DeepSeek) is authoritative for the D2631 queue re-vote rows.
    "p5:reliable-pair-D2631-revote",
})

# ── Derived authoritative sets (post-merge) ─────────────────────────────────
CT_AUTH = CT_ORIG | CT_FILL
DEPTH_AUTH = DP_ORIG | DP_FILL
DISC_AUTH = DISC_ORIG | DISC_FILL
DOM_AUTH = DOM_ORIG | DOM_FILL

# ── Self-check (fail-fast at import; C16: no silent drift) ─────────────────
# The pre-merge verified subset (*_ORIG) must never fall OUT of the post-merge
# authoritative set — a row that was already authoritative must stay spotless.
# (ORIG ∩ FILL may legitimately overlap: p5:human appears in both DISC_ORIG and
# DISC_FILL because it is a pre-existing verified source AND a fill source.)
def _assert_orig_subset(name: str, orig: frozenset, auth: frozenset) -> None:
    missing = orig - auth
    if missing:
        raise AssertionError(
            f"axis_authority: {name}_ORIG has sources outside {name}_AUTH: {sorted(missing)}"
        )


_assert_orig_subset("CT", CT_ORIG, CT_AUTH)
_assert_orig_subset("DP", DP_ORIG, DEPTH_AUTH)
_assert_orig_subset("DISC", DISC_ORIG, DISC_AUTH)
_assert_orig_subset("DOM", DOM_ORIG, DOM_AUTH)
