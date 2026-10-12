"""Guard the `taxonomy.semantic_error_rate_max.per_label` config block (D2547/D2569).

The 96-entry per-label block is written by `scripts/populate_semantic_error_thresholds.py`
via a regex block-replacement. It is the ONLY config block in `pipeline_config.yaml`
that is machine-rewritten in place (not hand-authored), so a malformed write could
silently corrupt rates. This test is a second oracle (it does NOT import the populate
script) and fails if:

  * any key is not a canonical domain/discipline from `taxonomy.yaml`,
  * any value is not a numeric float in [0, 1] (e.g. YAML turned `0.3914` into `"0.3914"`),
  * the block does not round-trip through `yaml.safe_dump` → `yaml.safe_load`.

It mirrors `tests/test_decision_summary_sync.py` in style: pure read-only, no
pipeline imports, so it can run in any Python without touching OMLX/DB.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_YAML = ROOT / "config" / "pipeline_config.yaml"
TAXONOMY_YAML = ROOT / "config" / "taxonomy.yaml"

# Current expected count = 53 disciplines + 40 domains = 93 (v9 menu, post-RATIFY-2
# D2547 re-calibration — BUG-695). The re-population (scripts/bug695_recalibrate.py)
# now writes an EMPIRICAL rate for every canonical label with >= min_sample (10)
# corpus presence. 63 disciplines -> 53 (10 below min-sample: design psychology,
# creative coding, generative design, privacy & surveillance, entrepreneurship
# studies, robotics, and 4 more thin labels) + 41 domains -> 40 ('design systems'
# has 9 fbs, below min-sample). Re-base only WITH a DECISION-LOG reason (D-2908).
EXPECTED_LABEL_COUNT = 93
EXPECTED_DOMAIN_COUNT = 40  # 41 v9 domains minus 'design systems' (9 fbs < min_sample 10)
BELOW_MIN_SAMPLE_DOMAINS = frozenset({"design systems"})  # 9 fbs < min_sample (10)


def _canonical_labels() -> tuple[set[str], set[str]]:
    """Return (disciplines, domains) canonical sets from taxonomy.yaml."""
    data = yaml.safe_load(TAXONOMY_YAML.read_text(encoding="utf-8")) or {}

    def _names(key: str) -> set[str]:
        out: set[str] = set()
        for entry in data.get(key, []) or []:
            if isinstance(entry, dict):
                if "canonical" in entry:
                    out.add(entry["canonical"])
            else:
                out.add(entry)
        return out

    return _names("disciplines"), _names("domains")


def _per_label() -> dict:
    cfg = yaml.safe_load(CONFIG_YAML.read_text(encoding="utf-8")) or {}
    block = (cfg.get("taxonomy") or {}).get("semantic_error_rate_max") or {}
    return block.get("per_label") or {}


def test_per_label_is_populated_dict() -> None:
    pl = _per_label()
    assert isinstance(pl, dict), "per_label must be a dict"
    assert len(pl) == EXPECTED_LABEL_COUNT, (
        f"per_label has {len(pl)} entries, expected {EXPECTED_LABEL_COUNT}. "
        "If a re-population legitimately changed this, update EXPECTED_LABEL_COUNT "
        "and record the reason in DECISION-LOG."
    )


def test_per_label_keys_are_canonical() -> None:
    disciplines, domains = _canonical_labels()
    canon = disciplines | domains
    assert len(disciplines) and len(domains), "taxonomy.yaml canonical sets empty"
    pl = _per_label()
    non_canonical = sorted(k for k in pl if k not in canon)
    assert not non_canonical, f"per_label has non-canonical keys: {non_canonical}"
    composite = sorted(k for k in pl if "|" in k)
    assert not composite, f"per_label must be single labels, got composite keys: {composite}"


def test_per_label_all_domains_present() -> None:
    _, domains = _canonical_labels()
    pl = _per_label()
    missing = sorted(
        d for d in domains if d not in pl and d not in BELOW_MIN_SAMPLE_DOMAINS
    )
    assert not missing, (
        f"all {EXPECTED_DOMAIN_COUNT} canonical domains with >= min_sample must have "
        f"a per_label rate; missing: {missing}"
    )


def test_per_label_values_numeric_in_range() -> None:
    pl = _per_label()
    bad: list[tuple[str, object]] = []
    for k, v in pl.items():
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            bad.append((k, v))
            continue
        if not (0.0 <= float(v) <= 1.0):
            bad.append((k, v))
    assert not bad, f"per_label values must be numeric floats in [0,1]: {bad}"


def test_per_label_yaml_round_trip() -> None:
    """The block must survive yaml.safe_dump → yaml.safe_load unchanged (type-safe)."""
    pl = _per_label()
    dumped = yaml.safe_dump({"per_label": pl}, sort_keys=True)
    reloaded = (yaml.safe_load(dumped) or {}).get("per_label") or {}
    assert reloaded == pl, "per_label block does not round-trip through YAML"
    # Every value must round-trip as a number, not a string.
    for k, v in reloaded.items():
        assert isinstance(v, (int, float)), f"after round-trip, {k!r} became {type(v).__name__}"
