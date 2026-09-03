"""D2451 — S4 classification golden set conformance against content_types.yaml.

Verifies config/golden/stage4_golden.yaml:
  1. Every example's `input_fb` carries the S2 core skeleton S4 receives
     (name/definition/mechanism/boundary).
  2. Every `expected_classification` uses ONLY valid ontology labels:
       depth ∈ {universal, cross-domain, domain, specialized}
       evidence ∈ {cited, axiomatic}
       discipline ∈ canonical disciplines (pipeline/schemas.py)
       domains ⊆ canonical domains, 1..MAX_DOMAINS_PER_FB
       is_specialized is bool
  3. The set spans all 4 depth levels (so few-shot covers the full axis).

This is the deterministic guarantee that S4 golden labels are ontologically and
pragmatically accurate — the wiring into S4 prompts (D2452) is a separate step.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from pipeline.pipeline_paths import MAX_DOMAINS_PER_FB
from pipeline.schemas import (
    CANONICAL_DISCIPLINES,
    CANONICAL_DOMAINS,
)

GOLDEN_PATH = Path(__file__).resolve().parent.parent / "config" / "golden" / "stage4_golden.yaml"

VALID_DEPTHS = {"universal", "cross-domain", "domain", "specialized"}
VALID_EVIDENCE = {"cited", "axiomatic"}
CORE_SKELETON = ("name", "definition", "mechanism", "boundary")


def _load() -> dict:
    if not GOLDEN_PATH.exists():
        pytest.skip("stage4_golden.yaml not present")
    with open(GOLDEN_PATH) as f:
        return yaml.safe_load(f)


def test_s4_golden_conforms_to_ontology() -> None:
    golden = _load()
    examples = golden.get("examples", [])
    assert examples, "S4 golden must have at least one example"

    seen_depths: set[str] = set()
    for ex in examples:
        eid = ex.get("id", "?")
        fb = ex.get("input_fb", {})
        exp = ex.get("expected_classification", {})

        # 1. S2 core skeleton present (what S4 actually receives).
        for field in CORE_SKELETON:
            assert fb.get(field), f"{eid}: input_fb missing non-empty {field!r}"

        # 2. Ontologically valid labels only.
        depth = exp.get("depth")
        assert depth in VALID_DEPTHS, f"{eid}: invalid depth {depth!r}"
        seen_depths.add(depth)

        evidence = exp.get("evidence")
        assert evidence in VALID_EVIDENCE, f"{eid}: invalid evidence {evidence!r}"

        discipline = exp.get("discipline")
        assert discipline in CANONICAL_DISCIPLINES, (
            f"{eid}: discipline {discipline!r} not in canonical taxonomy"
        )

        domains = exp.get("domains", [])
        assert isinstance(domains, list) and domains, f"{eid}: domains must be non-empty list"
        assert len(domains) <= MAX_DOMAINS_PER_FB, f"{eid}: too many domains"
        for d in domains:
            assert d in CANONICAL_DOMAINS, f"{eid}: domain {d!r} not in canonical taxonomy"

        assert isinstance(exp.get("is_specialized"), bool), f"{eid}: is_specialized must be bool"

    # 3. Full depth-axis coverage.
    assert seen_depths == VALID_DEPTHS, (
        f"S4 golden must span all 4 depth levels, found {sorted(seen_depths)}"
    )


def test_s4_golden_ids_unique() -> None:
    golden = _load()
    ids = [e.get("id") for e in golden.get("examples", [])]
    assert len(ids) == len(set(ids)), "S4 golden ids must be unique"


def test_s4_golden_axis_disjointness() -> None:
    """D2532: the few-shot must never teach cross-axis contamination (BUG-197).

    A contaminated golden (a DOMAIN label filed as `discipline`, or a discipline
    filed as a `domain`) would propagate the exact leak this golden exists to fix.
    Assert full disjointness between the two axes and forbid the `emerging`
    placeholder in either field. NOTE: CANONICAL_DISCIPLINES/CANONICAL_DOMAINS
    each still contain `emerging` as a legal placeholder, so the plain
    `in CANONICAL_*` check above alone would NOT catch an `emerging` golden —
    these explicit guards do.
    """
    from pipeline.schemas import normalize_label

    golden = _load()
    domain_norms = {normalize_label(d) for d in CANONICAL_DOMAINS}
    discipline_norms = {normalize_label(d) for d in CANONICAL_DISCIPLINES}

    for ex in golden.get("examples", []):
        eid = ex.get("id", "?")
        exp = ex.get("expected_classification", {})
        disc = exp.get("discipline", "")
        domains = exp.get("domains", [])
        disc_norm = normalize_label(disc)

        # discipline must not be a canonical domain (cross-axis leak).
        assert disc_norm not in domain_norms, (
            f"{eid}: discipline {disc!r} is a canonical DOMAIN (cross-axis leak)"
        )
        # discipline must not be the emerging placeholder.
        assert disc != "emerging", f"{eid}: discipline must not be 'emerging'"

        for d in domains:
            d_norm = normalize_label(d)
            # domain must not be a canonical discipline (reverse leak).
            assert d_norm not in discipline_norms, (
                f"{eid}: domain {d!r} is a canonical DISCIPLINE (reverse leak)"
            )
            # domain must not be the emerging placeholder.
            assert d != "emerging", f"{eid}: domain must not be 'emerging'"
            # no label may appear in BOTH axes.
            assert d_norm != disc_norm, (
                f"{eid}: {d!r} appears in both discipline and domains (disjointness)"
            )


def test_s4_golden_no_raw_axis_fields() -> None:
    """D2532: the golden's expected_classification must carry ONLY canonical labels.

    Raw (LLM free-text) discipline/domains do not belong in the few-shot — the
    prompt renders the *expected* canonical output, so any `discipline_raw` /
    `domains_raw` key would inject unvetted labels into the classifier. Forbid it.
    """
    golden = _load()
    for ex in golden.get("examples", []):
        exp = ex.get("expected_classification", {})
        assert "discipline_raw" not in exp, f"{ex.get('id')}: unexpected discipline_raw"
        assert "domains_raw" not in exp, f"{ex.get('id')}: unexpected domains_raw"


def test_s4_golden_not_silently_truncated() -> None:
    """D2501: config golden_max_examples must not truncate authored examples.

    S4-GOLD-005 (the D2482 cross-domain boundary example) was silently dropped
    because golden_max_examples=4 while the file carries 5 examples (and the
    D2483 A/B benchmark used all 5). This guard fails if the config truncates.
    """
    from pipeline.pipeline_paths import S4_GOLDEN_MAX_EXAMPLES
    examples = _load().get("examples", [])
    assert S4_GOLDEN_MAX_EXAMPLES >= len(examples), (
        f"golden_max_examples={S4_GOLDEN_MAX_EXAMPLES} truncates {len(examples)} "
        f"authored examples — dropped: {[e['id'] for e in examples[S4_GOLDEN_MAX_EXAMPLES:]]}"
    )
