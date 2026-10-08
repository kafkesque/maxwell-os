#!/usr/bin/env python3
"""apply_owner_domain_rulings_v8.py — RETIRED as a writer (BUG-683 / Stage 2 place 6). It refuses to write.

WHY (BUG-683, the anti-REVERT / stale-contract limb). Until 2026-10-08 this script was D-2874's fold limb:
it read config/owner_domain_rulings_20261008.yaml["rows"] (a mapping item_id -> {domains, primary}) and
wrote the 8 owner-gated domain rulings INTO governance/discipline_anchor_rederived_v8_20261007.json - the
then-declared authority. The round-2 rewrite of that config replaced the `rows:` block with declarative
columns (primary_override / remove_domains / noise_drop_excluded / discipline_abstention / reinstated_rows),
so the script raises KeyError on its first line of work. Nothing in the ladder invokes it, so the break was
silent - and its docstring still claimed folding into the authority is how the rulings become real, which is
the half-true claim that made BUG-682 possible.

THE RULE NOW: the discipline/domain/primary_domain axis has ONE derivation and ONE authority -
    config/owner_domain_rulings_20261008.yaml + the pinned owner sheets
      -> scripts/apply_owner_domain_review.py --apply -> governance/DOMAIN_RULER_FROZEN_20261008.json
      -> scripts/apply_owner_domain_review.py --check   (re-derivation proof)
      -> scripts/apply_owner_domain_review.py --check-faces (cross-face divergence)
      -> scripts/project_ruler_to_views.py              (projection limb onto the five-axis views)
      -> scripts/apply_anchor_axis_authority.py         (write limb: axis registry -> consumers)

The frozen RULER is now the declared authority of record (config/anchor_family.yaml +
config/anchor_axis_authority.yaml + config/pipeline_config.yaml#discipline_anchor_path, flipped in place 6).
The old authority (discipline_anchor_rederived_v8_20261007.json) is a DOWNSTREAM face that FOLLOWS the ruler,
never a write target - folding a ruling into it would re-open the two-home error leak (D-2646/D-2649).

This module is kept (rather than deleted) so that any older reference resolves to an EXPLANATION instead of
a silent revert, and it exits non-zero so an automated re-run fails loudly (C16: no silent errors).
"""
from __future__ import annotations

import sys


def main() -> int:
    """Refuse to write: name the single derivation and the rails that prove it."""
    print("REFUSED: apply_owner_domain_rulings_v8.py is RETIRED as a writer (BUG-683 / Stage 2 place 6).")
    print("  It folded rulings into governance/discipline_anchor_rederived_v8_20261007.json - a face that")
    print("  is now a DOWNSTREAM CONSUMER of the frozen ruler, never a write target (D-2646/D-2649).")
    print("  Its input contract (config[\"rows\"]) no longer exists; it would raise KeyError.")
    print("  The ONE derivation is:  python3 scripts/apply_owner_domain_review.py --apply")
    print("  Proof/no-drift:         python3 scripts/apply_owner_domain_review.py --check")
    print("  Cross-face divergence:  python3 scripts/apply_owner_domain_review.py --check-faces")
    print("  Projection onto views:  python3 scripts/project_ruler_to_views.py")
    return 1


if __name__ == "__main__":
    sys.exit(main())
