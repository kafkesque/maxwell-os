"""D2449: singleton-builder schema parity with single-source/convergent.

Historically `_singleton_result_to_fb` forked from `_build_fb_from_result` and
dropped: `elaboration`, bibliographic provenance (source_authors/citation/
primary_source), and every R14 stamp (schema_version/gen_model/pipeline_commit/
taxonomy_version/manifest_hash/pipeline_run_id/created_at). This left singleton
FBs with `source_authors: null` even when the author was embedded in the source
filename, and un-stamped records violating R14.

These tests GUARANTEE the drift cannot silently return: they assert the singleton
record now carries the full canonical field set + clean (de-noised) source books.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.stage2_extract import _singleton_result_to_fb

_RESULT = {
    "name": "Optimal Stopping Rule",
    "definition": "A mathematical strategy for making decisions under uncertainty over a fixed set of options.",
    "mechanism": "Observe a 37% baseline, then commit to the first option exceeding it.",
    "boundary": "Applies to sequentially revealed options.",
    "consequence": "Minimizes the probability of missing the best option.",
    "elaboration": "The rule derives from the secretary problem and assumes i.i.d. options.",
    "is_summary": False,
    "extraction_type": "causal_mechanism",
    "content_type": "principle",
    "route": "FB",
}

_ITEM = {
    "text": "The secretary problem says observe 37% of options then commit.",
    "source_book": "Algorithms to Live By (Brian Christian, Tom Griffiths) (z-library.sk, 1lib.sk, z-lib.sk).md",
    "segment_id": "seg123",
    "singleton": {
        "cluster_id": "singleton_0",
        "source_books": [
            "Algorithms to Live By (Brian Christian, Tom Griffiths) (z-library.sk, 1lib.sk, z-lib.sk).md"
        ],
        "source_ids": ["abc123"],
    },
}

CANONICAL_CORE = {
    "fb_id", "name", "definition", "mechanism", "boundary", "consequence",
    "elaboration", "is_summary", "extraction_type", "content_type",
    "evidence_passages", "evidence_passages_shown", "route", "source_cluster",
    "source_books", "source_ids", "source_segments", "cluster_cohesion",
    "cluster_size", "source_diversity", "is_convergent", "is_singleton_fb",
}

CANONICAL_STAMPS = {
    "schema_version", "gen_model", "pipeline_commit", "taxonomy_version",
    "manifest_hash", "pipeline_run_id", "created_at",
}

CANONICAL_PROVENANCE = {"source_authors", "citation", "primary_source"}


def test_singleton_emits_full_core_schema():
    fb = _singleton_result_to_fb(_RESULT, _ITEM, gate_enabled=True)
    assert fb is not None and "_null" not in fb
    missing = CANONICAL_CORE - set(fb.keys())
    assert not missing, f"singleton FB missing core fields: {sorted(missing)}"


def test_singleton_emits_r14_stamps():
    fb = _singleton_result_to_fb(_RESULT, _ITEM, gate_enabled=True)
    missing = CANONICAL_STAMPS - set(fb.keys())
    assert not missing, f"singleton FB missing R14 stamps: {sorted(missing)}"
    assert fb["schema_version"]  # non-empty


def test_singleton_emits_bibliographic_provenance():
    fb = _singleton_result_to_fb(_RESULT, _ITEM, gate_enabled=True)
    missing = CANONICAL_PROVENANCE - set(fb.keys())
    assert not missing, f"singleton FB missing provenance: {sorted(missing)}"
    # The author WAS embedded in the filename — must be resolved, not null/empty.
    assert fb["source_authors"], "source_authors should be populated"
    assert any("Brian Christian" in (sa.get("author") or "") for sa in fb["source_authors"])


def test_singleton_preserves_elaboration():
    fb = _singleton_result_to_fb(_RESULT, _ITEM, gate_enabled=True)
    assert fb["elaboration"] == _RESULT["elaboration"], "elaboration must not be dropped"


def test_singleton_sanitizes_source_books():
    fb = _singleton_result_to_fb(_RESULT, _ITEM, gate_enabled=True)
    noise_tokens = ("z-library", "1lib", "z-lib")
    joined = " ".join(fb["source_books"]).lower()
    for tok in noise_tokens:
        assert tok not in joined, f"noise token {tok!r} leaked into source_books: {fb['source_books']}"
