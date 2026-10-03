#!/usr/bin/env python3
"""Consolidate the ANCHOR-208 anchor into ONE canonical artifact.

Merges the two per-axis artifacts (depth-corrected + discipline-normalized)
with the owner's 9 discipline finalizations into a single 208-row file carrying
BOTH axes, keyed by item_id (the stable key; the 208-view `name` column is
truncated to 45 chars and is NOT authoritative — full names come from the
depth-corrected artifact, which was joined from maxwell.db).

Golden eligibility (deterministic, no LLM):
  * depth_golden_eligible      = depth_source in {canonical_adjudicated, owner_finalized}
                                 (excludes the 58 lower-provenance 'mapped' extras + R021 noise_drop)
  * discipline_golden_eligible = discipline != 'emerging' and not noise_drop
                                 (excludes the 4 'emerging' catchall rows R040/R053/R080/R091
                                  + the noise_drop row R021)

Rationale (senior RAG engineer): 'emerging' is an abstention/catch-all bucket, not a
positive exemplar — it teaches no boundary and pulls few-shot classifiers toward the
catch-all (contamination). It stays in the OUTPUT label space (menu) but is excluded
from golden few-shot exemplars and routed to a refinement queue instead.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEPTH = ROOT / "governance" / "ANCHOR_208_DEPTH_CORRECTED_20261002.json"
DISC = ROOT / "governance" / "ANCHOR_208_DISCIPLINE_NORMALIZED_20261002.json"
OUT = ROOT / "governance" / "ANCHOR_208_CONSOLIDATED_20261002.json"
OWNER9 = ROOT / "governance" / "discipline_finalization_owner_9.json"

# Owner finalizations for the 9 discipline review rows (verbatim from owner message).
OWNER_DISCIPLINE = {
    "R040": "emerging",
    "R042": "human-computer interaction",
    "R052": "design thinking",
    "R080": "emerging",
    "R086": "behavioral economics",
    "R091": "emerging",
    "R092": "research methodology",
    "R100": "organizational theory",
    "R117": "behavioral economics",
}
OWNER_VERBATIM = {
    "R040": "stay emerging",
    "R042": "agree with your suggestion (human-computer interaction)",
    "R052": "agree with your suggestion (design thinking)",
    "R080": "stay emerging",
    "R086": "behavioral economics",
    "R091": "cant decide therefore emerging",
    "R092": "agree with your suggestion (research methodology)",
    "R100": "agree with your suggestion (organizational theory)",
    "R117": "agree with your suggestion (behavioral economics)",
}
OWNER9_IDS = set(OWNER_DISCIPLINE)

DEPTH_GOLDEN_SOURCES = {"canonical_adjudicated", "owner_finalized"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL
        ).decode().strip()[:12]
    except Exception:
        return "unknown"


def _norm_name(s: str) -> str:
    return s.replace("\xa0", " ").strip()


def main() -> int:
    depth_rows = json.loads(DEPTH.read_text())
    disc = json.loads(DISC.read_text())["rows"]

    depth = {r["item_id"]: r for r in depth_rows}
    disc_by_id = {r["item_id"]: r for r in disc}

    assert set(depth) == set(disc_by_id), "item_id sets diverge"

    out_rows: list[dict] = []
    for iid in sorted(depth):
        d = depth[iid]
        n = disc_by_id[iid]
        discipline = n["discipline"]
        dstatus = n["discipline_status"]
        dsource = n["discipline_source"]

        if iid in OWNER9_IDS:
            discipline = OWNER_DISCIPLINE[iid]
            dstatus = "owner_finalized"
            dsource = "owner_finalized"

        # Noise detection must survive the R021 resolution (D-2813): the sentinel moved
        # from depth_label="noise_drop" to depth_source="owner_finalized_noise_drop"
        # (depth_label is now null). Check BOTH forms so the chain stays reproducible.
        is_noise = (
            d["depth_label"] == "noise_drop"
            or "noise_drop" in str(d.get("depth_source", ""))
        )
        is_emerging = discipline == "emerging"
        if is_noise:
            # A noise-dispositioned row carries no discipline label on any axis (D-2813):
            # null it out so the consolidated artifact never emits a false canonical label.
            discipline = None
            dstatus = "noise_drop"
            dsource = "noise_drop"
        out_rows.append({
            "item_id": iid,
            "name": _norm_name(d["name"]),
            # depth axis
            "depth": d["depth"],
            "depth_label": d["depth_label"],
            "depth_source": d["depth_source"],
            "depth_golden_eligible": d["depth_source"] in DEPTH_GOLDEN_SOURCES,
            # discipline axis
            "discipline": discipline,
            "discipline_status": dstatus,
            "discipline_source": dsource,
            "discipline_golden_eligible": (not is_emerging) and (not is_noise),
            # overall (a noise-dispositioned row is a valid exemplar on NO axis)
            "golden_eligible": (not is_emerging) and (not is_noise),
            # domain axis (reference)
            "domain": n["domain"],
            "primary_domain": n["primary_domain"],
        })

    stamp = {
        "schema_version": "1.0",
        "gen_model": "none",
        "generated_by": "scripts/consolidate_anchor_208.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "depth": str(DEPTH.relative_to(ROOT)) + f" ({_sha256(DEPTH)})",
            "discipline": str(DISC.relative_to(ROOT)) + f" ({_sha256(DISC)})",
        },
        "pipeline_commit": _commit(),
        "golden_eligibility": {
            "depth_golden_eligible": "depth_source in {canonical_adjudicated, owner_finalized} (149 human-provenanced rows; excludes 58 mapped + R021 noise_drop)",
            "discipline_golden_eligible": "discipline != 'emerging' and not noise_drop (excludes 4 catchall rows R040/R053/R080/R091 + R021 noise_drop)",
        },
        "name_note": "full names joined from maxwell.db via depth artifact; 208-view `name` column was truncated to 45 chars and R039 carried a non-breaking space (normalized).",
    }

    artifact = {"_provenance": stamp, "rows": out_rows}
    OUT.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n")

    # owner's 9 finalizations provenance
    owner9 = {
        "_provenance": {
            "schema_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "owner message 2026-10-02",
        },
        "finalizations": {
            iid: {"label": OWNER_DISCIPLINE[iid], "verbatim": OWNER_VERBATIM[iid]}
            for iid in sorted(OWNER9_IDS)
        },
    }
    OWNER9.write_text(json.dumps(owner9, indent=2, ensure_ascii=False) + "\n")

    from collections import Counter
    dl = Counter(r["depth_label"] for r in out_rows)
    dd = Counter(r["discipline"] for r in out_rows)
    dge = sum(1 for r in out_rows if r["depth_golden_eligible"])
    cge = sum(1 for r in out_rows if r["discipline_golden_eligible"])
    em = [r["item_id"] for r in out_rows if r["discipline"] == "emerging"]

    print(f"consolidated {len(out_rows)} rows -> {OUT.name}")
    print(f"depth labels: {dict(dl)}")
    print(f"depth_golden_eligible: {dge}")
    print(f"discipline_golden_eligible: {cge}")
    print(f"remaining emerging (excluded from golden): {em}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
