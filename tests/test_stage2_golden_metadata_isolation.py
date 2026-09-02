"""D2501/D2502 — stage2 golden `domain`/`discipline` metadata isolation guard.

The stage2 few-shot golden files (`stage2_fewshot_*.yaml`) carry a top-level
`domain`/`discipline` field per example that predates the canonical taxonomy and
contains ~108 cross-kind / non-canonical labels (e.g. `domain: typography`,
`domain: software engineering` — both are DISCIPLINE canonicals in the DOMAIN
slot). These are *dormant metadata*: verified safe today ONLY because no S2
few-shot formatter consumes them.

This guard fails if any formatter starts emitting those fields, which would turn
a dormant drift into live prompt contamination. It is a cheaper + more robust
defense than rewriting ~108 curated labels that nothing reads.
"""
from __future__ import annotations

from pipeline.stage2_extract import (
    format_golden_fewshot,
    format_golden_fewshot_single_source,
)

# Cross-kind sentinels: a discipline canonical in the `domain` slot and a domain
# canonical in the `discipline` slot. If either appears in formatter output, the
# metadata has leaked into the prompt.
_SENTINEL_DOMAIN = "typography"        # discipline canonical, wrongly in `domain`
_SENTINEL_DISCIPLINE = "graphic design"  # domain canonical, wrongly in `discipline`


def _synthetic_example() -> dict:
    return {
        "id": "META-ISOLATION-TEST",
        "domain": _SENTINEL_DOMAIN,
        "discipline": _SENTINEL_DISCIPLINE,
        "source_books": ["Synthetic Book A"],
        "rationale": "synthetic isolation probe",
        "expected_fb": {
            "name": "Synthetic Isolation Probe",
            "definition": "A probe whose name/definition deliberately omit the sentinel labels.",
            "mechanism": "mechanism",
            "boundary": "boundary",
            "consequence": "consequence",
            "is_summary": False,
            "extraction_type": "causal_mechanism",
            "content_type": "principle",
            "evidence_passages": ["ep"],
            "route": "FB",
        },
    }


def test_convergent_fewshot_does_not_emit_domain_discipline_metadata() -> None:
    """The convergent formatter must never surface `domain`/`discipline` metadata."""
    txt = format_golden_fewshot([_synthetic_example()])
    assert _SENTINEL_DOMAIN not in txt, (
        "convergent few-shot leaked `domain` metadata — dormant cross-kind labels "
        "are now live prompt contamination"
    )
    assert _SENTINEL_DISCIPLINE not in txt, (
        "convergent few-shot leaked `discipline` metadata"
    )


def test_single_source_fewshot_does_not_emit_domain_discipline_metadata() -> None:
    """The single-source formatter must never surface `domain`/`discipline` metadata."""
    txt = format_golden_fewshot_single_source([_synthetic_example()])
    assert _SENTINEL_DOMAIN not in txt, (
        "single-source few-shot leaked `domain` metadata"
    )
    assert _SENTINEL_DISCIPLINE not in txt, (
        "single-source few-shot leaked `discipline` metadata"
    )


if __name__ == "__main__":
    test_convergent_fewshot_does_not_emit_domain_discipline_metadata()
    test_single_source_fewshot_does_not_emit_domain_discipline_metadata()
    print("stage2 golden metadata isolation tests OK")
