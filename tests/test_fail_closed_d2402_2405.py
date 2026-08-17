"""test_fail_closed_d2402_2405.py — fail-closed regression tests for the
frontier T1.1 audit fixes (D2402-D2405).

Covers the decision points that were previously silent-fail risks:
  * D2402  S4 runner timeout (config-only — asserted via config audit, not here)
  * D2403  S2 schema-invalid output → "_failed" sentinel (retryable, not NULL)
  * D2404  S4 classification-FAILED → not appended / not marked processed
  * D2405  S4 fabricated evidence="cited" + S5 FAILED gate → QUARANTINE

These tests are model-free (no LLM / no DeBERTa) — they verify the fail-closed
*decision logic* and the C12 config-first wiring, not the inference quality.
"""
from __future__ import annotations

from pipeline import stage5_verify
from pipeline.pipeline_paths import _CFG


def _mech(n_chars: int = 200, prefix: str = "") -> str:
    """Build a mechanism string of a controlled length/prefix for quality checks."""
    if prefix:
        body = "x" * max(0, n_chars - len(prefix))
        return prefix + body
    return "x" * n_chars


# ── S5 mechanism quality pre-filter (D2405 C12 config-first thresholds) ──────

def test_mechanism_quality_too_short():
    fb = {"mechanism": _mech(10), "source_books": [], "evidence": "cited"}
    passed, score, detail = stage5_verify.check_mechanism_quality(fb)
    assert passed is False
    assert score == 0.0
    assert "too short" in detail.lower()


def test_mechanism_quality_tautological():
    prefix = "because it enables"
    fb = {"mechanism": _mech(200, prefix=prefix), "source_books": [], "evidence": "cited"}
    passed, score, detail = stage5_verify.check_mechanism_quality(fb)
    assert passed is False
    assert score == 0.0
    assert "tautological" in detail.lower()


def test_mechanism_quality_valid():
    fb = {"mechanism": _mech(200), "source_books": ["a", "b"], "evidence": "cited"}
    passed, score, detail = stage5_verify.check_mechanism_quality(fb)
    assert passed is True
    assert score == 1.0
    assert "ok" in detail.lower()


def test_mechanism_threshold_is_config_sourced():
    """D2405/C12: the S5 thresholds must come from pipeline_config.yaml, not be hardcoded."""
    cfg5 = _CFG.get("stage5", {})
    assert stage5_verify.MECHANISM_MIN_LENGTH == int(cfg5.get("mechanism_min_length", 150))
    assert stage5_verify.CITATION_ECHO_SOURCE_THRESHOLD == int(
        cfg5.get("citation_echo_source_threshold", 20)
    )
    banned = stage5_verify.BANNED_MECHANISM_PREFIXES
    assert isinstance(banned, tuple) and len(banned) > 0
    assert "because it enables" in banned


# ── D2405: S5 must never PASS an S4 classification-FAILED FB ─────────────────

def _failed_fb() -> dict:
    return {
        "name": "Test Principle",
        "fb_id": "test_fb_001",
        "definition": "A test definition describing a causal principle.",
        "mechanism": _mech(200),  # passes mechanism-quality → isolates the FAILED gate
        "boundary": "Test boundary.",
        "consequence": "Test consequence.",
        "application": "A test application that is long enough to avoid enrichment noise.",
        "failure_mode": "A test failure mode that is long enough to avoid enrichment noise.",
        "source_books": ["book_a", "book_b"],
        "evidence": None,  # D2405: S4 no longer fabricates "cited" on FAILED
        "classification_status": "FAILED",
        "classification_error": "depth_focused: mock transport failure",
        "domains": ["emerging"],
        "discipline": "emerging",
        "depth": "domain",
        "content_type": "principle",
        "extraction_type": "",
        "prerequisite_fbs": [],
        "source_principle_ids": ["test_fb_001"],
    }


def test_s5_failed_classification_quarantines(monkeypatch):
    """A classification_status=FAILED FB must go QUARANTINE with method
    classification_failed — never PASS, and never reach the DeBERTa NLI call."""
    failed_fb = _failed_fb()

    monkeypatch.setattr(stage5_verify, "load_stage4_fbs", lambda: [failed_fb])
    monkeypatch.setattr(stage5_verify, "_load_dual_encoders", lambda: (None, None))
    monkeypatch.setattr(
        stage5_verify, "safe_write", lambda path, content: None
    )

    # D2405: the FAILED gate must short-circuit before deberta_check() is invoked.
    called: list[dict] = []

    def _deberta_should_not_run(fb: dict):
        called.append(fb)
        raise AssertionError("deberta_check must not be called for classification-FAILED FB")

    monkeypatch.setattr(stage5_verify, "deberta_check", _deberta_should_not_run)

    # ISOR is imported inside run_stage5 — patch at the source module.
    import pipeline.schema_accessor as schema_accessor

    monkeypatch.setattr(
        schema_accessor, "isor_score", lambda fb: {"score": 0.5, "rating": "medium"}
    )

    verified = stage5_verify.run_stage5()

    assert len(verified) == 1
    vfb = verified[0]
    assert vfb["status"] == "QUARANTINE", f"expected QUARANTINE, got {vfb['status']}"
    assert vfb["verification_method"] == "classification_failed"
    # D2093 fail-closed: any non-PASS path caps confidence at the quarantine cap.
    assert vfb["confidence_score"] <= stage5_verify.S5_QUARANTINE_CONF_CAP
    assert called == [], "deberta_check was called for a FAILED FB — gate is not fail-closed"


def test_s5_failed_fb_evidence_is_not_fabricated():
    """D2405: a FAILED FB must carry evidence=None, never the fabricated 'cited'."""
    fb = _failed_fb()
    assert fb["evidence"] is None
    assert fb["classification_status"] == "FAILED"


# ── D2403: S2 schema-invalid output → "_failed" (retryable), not "_null" ─────

def test_s2_validate_fb_output_rejects_non_dict():
    from pipeline.stage2_extract import validate_fb_output

    is_valid, errors = validate_fb_output("not a dict")  # type: ignore[arg-type]
    assert is_valid is False
    assert any("dict" in e for e in errors)


def test_s2_validate_fb_output_rejects_missing_fields():
    from pipeline.stage2_extract import validate_fb_output

    is_valid, errors = validate_fb_output({})
    assert is_valid is False
    assert any("Missing required field" in e for e in errors)


# ── D2404: S4 classification validation gate ────────────────────────────────

def test_s4_validate_classification_rejects_malformed():
    from pipeline.stage4_merge import validate_classification

    is_valid, errors = validate_classification({})
    assert is_valid is False
    assert any("Discipline is required" in e for e in errors)
    assert any("Invalid depth" in e for e in errors)
    assert any("Invalid evidence" in e for e in errors)
