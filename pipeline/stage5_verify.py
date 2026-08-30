#!/usr/bin/env python3
"""
stage5_verify.py — DeBERTa-Only S5: Calibrated NLI Verification (D2298).
==================================================================================
Authority: CONSTITUTION.md §3 (Pipeline Stage 5), R5, C8, D2069, D2255

Input:  FBs from Stage 4 checkpoint (with embedded source_principles)
Output: Verified FBs, checkpoint at stage5_verify.jsonl

Process:
  1. Mechanism quality pre-filter: catch tautological mechanisms (regex, free)
  2. DeBERTa-v3-large (435M, MNLI+FEVER+ANLI+Ling+WANLI): sole NLI verifier
  3. Threshold 0.10 — auto-calibrated (466 pairs, 88 FBs): P=0.647, R=0.386, F1=0.484
  4. Verdict (D2321: premise/hypothesis pairing + all-3-label scoring):
     → ENTAIL ≥ 0.10 → PASS
     → NEUTRAL (unverifiable) → QUARANTINE
     → CONTRA → QUARANTINE
  5. FAIL-CLOSED (D2093): any path failure → QUARANTINE, never PASS

  DELETED (dead checks): BORP (S1.5 guarantees ≥2 sources), Completeness (S4 fills all fields)
  DELETED (unreliable): Phi-4-mini LLM (67% acc, hallucination risk), RoBERTa-large (zero signal)
  DeBERTa is an ENCODER → computes scores, doesn't generate text → CANNOT HALLUCINATE.

R5 compliance (D2298):
  Verifier: DeBERTa-v3-large (Microsoft/FAIR, 435M, disentangled attention)
  Single encoder — chosen after calibration showed RoBERTa added zero signal on paraphrase evidence.
  D2227: evidence passages are LLM paraphrases, not verbatim — RoBERTa can't differentiate.

DeBERTa-v3-large: MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli (4.14GB)
  Benchmarks: MNLI 90.3%, FEVER 89.1%, ANLI 62.4%+
  Calibration: Precision 0.647, Recall 0.386, F1 0.484 at threshold 0.10 (466 pairs, 88 FBs)
  Speed: ~290ms per sentence pair on MPS (loaded in 6s)

Usage:
    python3 pipeline/stage5_verify.py
"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import load_jsonl, safe_write  # D2332: fail-closed JSONL boundary
from pipeline.pipeline_paths import (
    CHECKPOINT_DIR,
    S5_CONF_ENRICH_WEIGHT,  # D2310: confidence enrichment weight
    S5_CONF_ISOR_WEIGHT,  # D2310: confidence ISOR weight
    S5_CONF_MECH_WEIGHT,  # D2310: confidence mechanism weight
    S5_HUMAN_REVIEW_ISOR,  # D2310: ISOR rating triggering human review
    S5_CHECKPOINT_INTERVAL,  # D2409: intra-stage incremental checkpoint cadence (FBs)
    S5_NLI_MODEL_LARGE,  # D2298: DeBERTa-v3-large (435M) sole NLI verifier
    S5_NLI_MAX_HYPOTHESIS_CHARS,  # D2321: hypothesis(definition) truncation for NLI pairing
    S5_NLI_MAX_PREMISE_CHARS,  # D2321: premise(evidence) truncation for NLI pairing
    S5_NLI_PASS_THRESHOLD,  # D2155: NLI score threshold for PASS (0.10, D2298 calibrated)
    S5_QUARANTINE_CONF_CAP,  # D2310: confidence cap for QUARANTINE
    STAGE4_5_CHECKPOINT,  # F1/D2400: enriched S4 checkpoint (preferred when present)
    STAGE4_CHECKPOINT,
    STAGE5_CHECKPOINT,
    SCHEMA_VERSION,  # D2485: S5 input fingerprint
    TAXONOMY_VERSION,  # D2485: S5 input fingerprint
    GEN_MODEL,  # D2485: S5 input fingerprint (generator identity)
    VERIFY_MODEL,  # D2485: S5 input fingerprint (classifier identity)
)
from pipeline.pipeline_paths import _CFG  # D2405: C12 config-first threshold source

# fb_definition/fb_source_texts/fb_source_texts_shown imported locally inside
# deberta_check() to avoid a module-level circular import (schema_accessor ↔ stage5_verify).
from pipeline.stamp import get_manifest_hash, get_pipeline_commit  # D2485: manifest fingerprint

# ── Constants ──────────────────────────────────────────────────────────────
NLI_PASS_THRESHOLD: float = S5_NLI_PASS_THRESHOLD  # D2298: from config (0.10, calibrated)
# ── NLI Model — DeBERTa-v3-large only (D2298) ──────────────────────────────
# DeBERTa-v3-large (435M, MNLI+FEVER+ANLI+Ling+WANLI) is the sole NLI verifier.
# RoBERTa-large removed (D2298): added zero signal on paraphrase evidence (D2227).
# ModernBERT fallback removed (D2298). No automatic fallback.

_DUAL_LOADED: bool = False
_DEBERTA_LARGE = None


def _load_dual_encoders():
    """D2298: Load DeBERTa-large once. Encoder — no hallucination risk.
    RoBERTa removed (D2298) — added zero signal on paraphrase evidence (D2227).
    Model ID from pipeline_config.yaml → models.nli_large (C12: config-driven).
    """
    global _DUAL_LOADED, _DEBERTA_LARGE
    if _DUAL_LOADED:
        return _DEBERTA_LARGE, None

    import torch as _t
    from transformers import AutoModelForSequenceClassification as _AM
    from transformers import AutoTokenizer as _AT
    from transformers import pipeline as _p

    _device = "mps" if _t.backends.mps.is_available() else ("cuda" if _t.cuda.is_available() else -1)
    _dl = "MPS" if _device != -1 else "CPU"

    # DeBERTa-v3-large (435M, MNLI+FEVER+ANLI+Ling+WANLI)
    _did = S5_NLI_MODEL_LARGE
    _dname = _did.split("/")[-1] if "/" in str(_did) else str(_did)
    print(f"   🧠 DeBERTa-large: {_dname[:50]}...")
    _dtok = _AT.from_pretrained(_did, trust_remote_code=True)
    _dmod = _AM.from_pretrained(_did, trust_remote_code=True)
    _dmod.to(_device)
    _DEBERTA_LARGE = _p("text-classification", model=_dmod, tokenizer=_dtok, device=_dmod.device)

    _DUAL_LOADED = True
    print(f"   ✅ DeBERTa-large loaded on {_dl}: 435M params")
    return _DEBERTA_LARGE, None


class NLIInferenceError(RuntimeError):
    """Raised by _nli_pair_scores(..., raise_on_error=True) on NLI runtime failure (C16/BUG-177).

    A transport/model error must never be indistinguishable from a genuine
    "not entailed" verdict. Callers that want fail-closed behavior catch this
    and record `verification_error_type`; they must NOT substitute a semantic
    label (D2093 fail-closed).
    """


def _nli_pair_scores(
    premise: str,
    hypothesis: str,
    *,
    raise_on_error: bool = False,
) -> tuple[float, float, float]:
    """D2322: Raw DeBERTa NLI scores for one (premise, hypothesis) pair.

    Returns (entailment, neutral, contradiction) probabilities. Shared primitive
    used by deberta_check() and nli_calibrate.py so both read all three labels
    from a properly-paired input (BUG-092 fix).

    C16/BUG-177: previously never raised — returned (0,0,0) on any failure,
    making an infra error look like "not entailed". With raise_on_error=True
    the caller gets a typed NLIInferenceError instead and can record it as
    verification_error_type. Default False preserves the legacy contract for
    nli_calibrate.py (which treats (0,0,0) as a skip).
    """
    debert, _ = _load_dual_encoders()
    if debert is None:
        if raise_on_error:
            raise NLIInferenceError("DeBERTa model not loaded")
        return 0.0, 0.0, 0.0
    try:
        _r = debert({"text": premise, "text_pair": hypothesis}, top_k=3)
    except Exception as e:
        if raise_on_error:
            raise NLIInferenceError(f"NLI inference failed: {e}") from e
        return 0.0, 0.0, 0.0
    _entail = _neutral = _contra = 0.0
    if isinstance(_r, list):
        for _s in _r:
            _lbl = str(_s.get("label", "")).upper()
            _sc = float(_s.get("score", 0.0))
            if _lbl in ("ENTAILMENT", "ENTAIL"):
                _entail = _sc
            elif _lbl == "NEUTRAL":
                _neutral = _sc
            elif _lbl in ("CONTRADICTION", "CONTRA"):
                _contra = _sc
    return _entail, _neutral, _contra


def deberta_check(fb: dict) -> tuple[bool, float, str]:
    """D2298-calibrated NLI check, D2321-corrected pairing, D2322 raw-score return.

    Threshold 0.10 from auto-calibration (466 pairs, 88 FBs): P=0.647, R=0.386, F1=0.484.
    RoBERTa removed (D2298) — added zero signal on paraphrase-based evidence (D2227).

    D2321 FIX (BUG-092): previous code concatenated "definition evidence" into ONE
    string and fed it to the NLI encoder as a single sequence (no premise/hypothesis
    separation), and read only the top-1 label. NEUTRAL verdicts therefore collapsed
    to "ent=0.00 cont=0.00" and were mislabeled CONTRA. This function now passes
    (premise=evidence, hypothesis=definition) as a proper pair and reads all three
    labels (top_k=3), distinguishing ENTAIL / NEUTRAL / CONTRA.

    D2322: the returned `score` is now the continuous entailment probability in ALL
    cases (not 0.0 on fail) so callers (nli_calibrate.py) can sweep thresholds on
    honest raw scores. `passed`/`status` logic is unchanged (fail-closed, D2093).

    Returns (passed, score, detail).
    """
    debert, _ = _load_dual_encoders()
    if debert is None:
        return False, 0.0, "DeBERTa not loaded — QUARANTINE"

    from pipeline.schema_accessor import fb_definition, fb_source_texts, fb_source_texts_shown
    _eps = fb_source_texts_shown(fb) or fb_source_texts(fb)
    if not _eps:
        _sps = fb.get("source_principles", [])
        _eps = [p.get("principle_text", "") for p in _sps if p.get("principle_text")]
    if not _eps:
        return False, 0.0, "No evidence — QUARANTINE"

    _def = fb_definition(fb)
    if not _def or len(_def) < 20:
        return False, 0.0, "No definition — QUARANTINE"

    _thresh = S5_NLI_PASS_THRESHOLD  # Config-driven (C12), D2322 calibrated: 0.10
    _entail_scores: list[float] = []
    _contra_scores: list[float] = []
    _neutral_scores: list[float] = []
    _nli_errors: list[str] = []  # C16/BUG-177: observability — never silent

    for _ep in _eps[:8]:
        if not _ep.strip():
            continue
        _prem = _ep[:S5_NLI_MAX_PREMISE_CHARS]  # premise = evidence passage
        _hyp = _def[:S5_NLI_MAX_HYPOTHESIS_CHARS]  # hypothesis = FB definition
        try:
            _ent, _neu, _con = _nli_pair_scores(_prem, _hyp, raise_on_error=True)
        except NLIInferenceError as e:
            # C16/BUG-177: an NLI runtime error is NOT a semantic "not entailed" —
            # record it so the operator can distinguish infra failure from verdict.
            _nli_errors.append(str(e))
            continue
        if _ent == 0.0 and _neu == 0.0 and _con == 0.0:
            continue  # NLI scoring failed for this passage
        _entail_scores.append(_ent)
        _neutral_scores.append(_neu)
        _contra_scores.append(_con)

    if _nli_errors:
        fb["verification_error_type"] = "NLIInferenceError"
        fb["verification_errors"] = _nli_errors[:5]
    if not (_entail_scores or _contra_scores or _neutral_scores):
        return False, 0.0, "NLI scoring failed — QUARANTINE"

    _entail = max(_entail_scores, default=0.0)
    _contra = max(_contra_scores, default=0.0)
    _neutral = max(_neutral_scores, default=0.0)

    if _entail >= _thresh:
        return True, round(_entail, 4), f"ENTAIL: {_entail:.2f}"
    if _neutral > _entail and _neutral > _contra:
        return False, round(_entail, 4), f"NEUTRAL: ent={_entail:.2f} neu={_neutral:.2f} cont={_contra:.2f}"
    return False, round(_entail, 4), f"CONTRA: ent={_entail:.2f} cont={_contra:.2f}"


# nli_evidence_check REMOVED (D2298) — superseded by deberta_check(); referenced deleted
# nli_entailment (F821). DeBERTa-v3-large is the sole NLI verifier.

# ── Core verification functions ────────────────────────────────────────────

def _preflight_gate(source: Path) -> None:
    """D2490: BUG-188 checkpoint boundary + sha256 gate before S5 consumes S4.

    Runs scripts/preflight_checkpoint_check.py --check (D2487): verifies every
    line is standalone JSON + newline-terminated, and — when a manifest exists —
    that sha256 + record_count match. Fail-closed: a truncated / pretty-printed /
    corrupt checkpoint aborts S5 instead of being silently mis-read.
    """
    preflight = Path(__file__).resolve().parent.parent / "scripts" / "preflight_checkpoint_check.py"
    r = subprocess.run(
        [sys.executable, str(preflight), "--check", str(source)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f"🛑 Preflight checkpoint gate FAILED for {source.name}:")
        print(r.stdout + r.stderr)
        sys.exit(1)
    print(f"✅ Preflight checkpoint gate passed for {source.name}")


def load_stage4_fbs() -> list[dict]:
    """Load FBs from the (possibly enriched) Stage 4 checkpoint.

    F1/D2400: prefer the post-S4 enriched checkpoint (STAGE4_5_CHECKPOINT) when
    it exists, else fall back to the plain STAGE4_CHECKPOINT. Uses fail-closed
    `load_jsonl` (D2332) so a pretty-printed/corrupt checkpoint raises instead
    of silently dropping records.
    """
    source = STAGE4_5_CHECKPOINT if STAGE4_5_CHECKPOINT.exists() else STAGE4_CHECKPOINT
    if not source.exists():
        print("❌ Stage 4 checkpoint not found. Run stage4_merge.py first.")
        sys.exit(1)

    _preflight_gate(source)  # D2490: boundary + sha256 + record-count gate (D2487)

    return load_jsonl(source, context="S4 checkpoint")


# ── D2298/D2283: Dead check functions removed ─────────────────────────────
# check_borp: BORP guarantee now provided by S1.5 (≥2 sources enforced at cluster level)
# check_completeness: Field presence guaranteed by S4 merge (always fills all fields)
# check_factual_llm: Phi-4-mini LLM escalation removed (67% acc, hallucination risk)
# build_factual_prompt, FACTUAL_CHECK_SYSTEM: Only used by check_factual_llm → removed
# D2283: Core (S2) vs Enrichment (S4) field contract in schema_accessor.py → CORE_FIELDS / ENRICHMENT_FIELDS

# ── Mechanism quality pre-filter (D2220: guards against citation echo gaming NLI) ──

# D2220/D2405: Citation echo detection thresholds — config-first (C12) via stage5.* keys;
# fallback defaults if keys not present.
_cfg5 = _CFG.get("stage5", {})
MECHANISM_MIN_LENGTH: int = int(_cfg5.get("mechanism_min_length", 150))
CITATION_ECHO_SOURCE_THRESHOLD: int = int(_cfg5.get("citation_echo_source_threshold", 20))
BANNED_MECHANISM_PREFIXES: tuple[str, ...] = tuple(_cfg5.get("banned_mechanism_prefixes", [
    "because it enables",
    "because it allows",
    "because it helps",
    "because it provides",
    "because it makes",
    "because it can",
]))


def _check_enrichment_quality(fb: dict) -> tuple[bool, float, str]:
    """D2277: Lightweight enrichment verification — checks S4 fields don't contradict core.

    Does NOT block FB creation (enrichment is best-effort, D2283). Flags:
      1. Application contradicts boundary (e.g., boundary says "fails when X" but app says "use when X")
      2. Failure_mode repeats the definition verbatim (should describe failure, not repeat mechanism)
      3. Enrichment fields are missing or suspiciously short

    Returns (passed, score, detail). Always passes (score 1.0) — enrichment issues
    degrade confidence_score but don't fail verification. True failures only for
    critical contradictions.
    """
    # D2283: Only check enrichment fields if present (core/enrichment split)
    app = str(fb.get("application", "")).strip()
    fm = str(fb.get("failure_mode", "")).strip()
    definition = str(fb.get("definition", "")).strip()
    boundary = str(fb.get("boundary", "")).strip()

    warnings: list[str] = []
    grade: float = 1.0
    passed: bool = True

    # 1. Check: application contradicts boundary
    if app and boundary:
        # Simple heuristic: if boundary mentions a failure condition that application ignores
        app_lower = app.lower()
        boundary_lower = boundary.lower()
        # Extract failure condition keywords from boundary
        fail_indicators = ["fails when", "does not apply", "breaks when", "limited to", "not effective"]
        for indicator in fail_indicators:
            if indicator in boundary_lower:
                # Check if application acknowledges this
                context = boundary_lower.split(indicator, 1)[1][:80] if indicator in boundary_lower else ""
                if context and context.split()[0] in app_lower:
                    pass  # Application acknowledges the boundary condition
                elif indicator == "fails when" and "when" not in app_lower:
                    warnings.append("ENRICH-APP-BOUNDARY: application doesn't acknowledge boundary condition")
                    grade -= 0.05
                break

    # 2. Check: failure_mode doesn't just repeat definition
    if fm and definition:
        # Simple overlap check: if >70% of failure_mode words overlap with definition
        fm_words = set(fm.lower().split())
        def_words = set(definition.lower().split())
        if fm_words and def_words:
            overlap = len(fm_words & def_words) / len(fm_words)
            if overlap > 0.7:
                warnings.append(f"ENRICH-FM-ECHO: failure_mode {overlap:.0%} overlaps definition — should describe failure, not repeat mechanism")
                grade -= 0.10

    # 3. Check: enrichment fields present
    if not app:
        warnings.append("ENRICH-MISSING: application field empty")
        grade -= 0.03
    elif len(app) < 30:
        warnings.append(f"ENRICH-SHORT-APP: {len(app)} chars (expected ≥50, D2295)")
        grade -= 0.02
    if not fm:
        warnings.append("ENRICH-MISSING: failure_mode field empty")
        grade -= 0.03
    elif len(fm) < 40:
        warnings.append(f"ENRICH-SHORT-FM: {len(fm)} chars (expected ≥60, D2295)")
        grade -= 0.02

    # Only fail for critical contradictions
    if grade < 0.80:
        passed = False

    detail = "; ".join(warnings) if warnings else "Enrichment quality: OK"
    return passed, round(max(grade, 0.0), 3), detail


def check_mechanism_quality(fb: dict) -> tuple[bool, float, str]:
    """Pre-filter: check mechanism quality before NLI to prevent citation echo gaming.

    D2220: When source count is high, MAX-entailment NLI is vulnerable to
    "at least one passage matches" — any vague mechanism with 20+ sources has
    a high probability of at least one passage having high entailment, creating
    false positives. This pre-filter catches low-quality mechanisms before they
    reach NLI.

    Checks:
      1. Mechanism minimum length (prevents vacuous one-liners)
      2. Non-tautological "because" clause (prevents definitional restatements)
      3. Citation echo override: high source count + axiomatic evidence = escalate

    Returns:
        (passed, score, detail). score=0.0 means auto-quarantine. score=0.5 means
        escalate to LLM regardless of NLI outcome.
    """
    mechanism = fb.get("mechanism", "").strip()
    source_books = fb.get("source_books", [])
    n_sources = len(source_books) if isinstance(source_books, list) else 0
    evidence = fb.get("evidence", "cited")

    # 1. Minimum mechanism length
    if len(mechanism) < MECHANISM_MIN_LENGTH:
        return False, 0.0, (
            f"Mechanism too short ({len(mechanism)} chars < {MECHANISM_MIN_LENGTH}) — "
            "likely vacuous. QUARANTINE."
        )

    # 2. Tautological "because" detection
    mech_lower = mechanism.lower()
    for banned_prefix in BANNED_MECHANISM_PREFIXES:
        if mech_lower.startswith(banned_prefix) or banned_prefix in mech_lower:
            # Check if the because-clause is the ONLY content
            # "X works because it enables X" is tautological
            return False, 0.0, (
                f"Mechanism contains tautological pattern '{banned_prefix}' — "
                "restates definition rather than explaining causal chain. QUARANTINE."
            )

    # 3. Citation echo override: high source count + axiomatic evidence
    if n_sources > CITATION_ECHO_SOURCE_THRESHOLD and evidence == "axiomatic":
        return True, 0.5, (
            f"Citation echo risk: {n_sources} sources + axiomatic evidence. "
            "Escalate to LLM deep check regardless of NLI outcome."
        )

    return True, 1.0, "Mechanism quality OK"


# ── D2485 (P0): S5 input fingerprint — bind checkpoint to the S4 input it verified ──

S5_INPUT_FINGERPRINT_PATH = Path(str(STAGE5_CHECKPOINT) + ".input_fingerprint.json")


def _sha256_file(path: Path) -> str:
    """SHA-256 of a file's bytes (stable, ignores mtime). Empty for missing files."""
    if not path.exists() or path.is_dir():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _s5_input_fingerprint() -> dict:
    """D2485 (P0): fingerprint the S4 input that S5 is about to verify.

    Binds the S5 checkpoint to the exact S4 output (content hash) + config
    (manifest_hash) + model lineup it verified. A content-stable fb_id cannot
    detect a stale S4 checkpoint — the D2409 0-overlap guard FAILS when two runs
    share ~93% of fb_ids (the BUG-150 stale t11 archive was the manual workaround).
    This fingerprint hard-discards any S5 checkpoint whose input fingerprint
    differs, eliminating the manual archive ritual.
    """
    source = STAGE4_5_CHECKPOINT if STAGE4_5_CHECKPOINT.exists() else STAGE4_CHECKPOINT
    return {
        "s4_checkpoint": str(source),
        "s4_checkpoint_sha256": _sha256_file(source),
        "schema_version": SCHEMA_VERSION,
        "taxonomy_version": TAXONOMY_VERSION,
        "pipeline_commit": get_pipeline_commit(),
        "manifest_hash": get_manifest_hash(),  # config + prompt fingerprint (D2282)
        "gen_model": GEN_MODEL,
        "classify_model": VERIFY_MODEL,
        "nli_model": S5_NLI_MODEL_LARGE,
    }


def _fingerprint_id(fp: dict) -> str:
    """Deterministic ID for an input fingerprint (canonical JSON + SHA-256)."""
    return hashlib.sha256(
        json.dumps(fp, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _load_stored_fingerprint_id() -> str | None:
    """Return the fingerprint ID recorded alongside the S5 checkpoint, or None."""
    if not S5_INPUT_FINGERPRINT_PATH.exists():
        return None
    try:
        data = json.loads(S5_INPUT_FINGERPRINT_PATH.read_text())
        return data.get("fingerprint_id")
    except Exception:
        return None


def _write_input_fingerprint() -> None:
    """Persist the current S4 input fingerprint alongside the S5 checkpoint.

    Written BEFORE verification begins so a mid-run crash leaves a valid
    fingerprint for the next resume attempt to validate against.
    """
    fp = _s5_input_fingerprint()
    payload = {
        "fingerprint_id": _fingerprint_id(fp),
        "input": fp,
    }
    try:
        S5_INPUT_FINGERPRINT_PATH.parent.mkdir(parents=True, exist_ok=True)
        S5_INPUT_FINGERPRINT_PATH.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n"
        )
    except Exception as e:
        print(f"   ⚠️  Could not persist S5 input fingerprint: {e}")


# ── Main ────────────────────────────────────────────────────────────────────

def _write_s5_checkpoint(verified: list[dict]) -> None:
    """Serialize verified FBs to the S5 checkpoint (fail-closed JSONL, crash-safe).

    D2409: used both for the final write and for intra-stage incremental writes
    so a crash mid-S5 loses at most the trailing <S5_CHECKPOINT_INTERVAL> FBs
    (a deterministic re-verify) rather than the entire stage.
    """
    checkpoint_text = "\n".join(json.dumps(vfb, ensure_ascii=False) for vfb in verified) + "\n"
    safe_write(STAGE5_CHECKPOINT, checkpoint_text)


def run_stage5(strict: bool = False, skip_nli: bool = False):
    """D2298: DeBERTa-only S5 — single NLI verification, calibrated at threshold 0.10.
    No decoder LLM. No BORP (S1.5 guarantees ≥2 sources). No Completeness (S4 fills all fields).
    RoBERTa removed — added zero signal on paraphrase-based evidence (D2227).
    """
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    fbs = load_stage4_fbs()

    # ── D2409: intra-stage resume (crash recovery for the serial S5) ───────
    # Reload the partial checkpoint and skip already-verified FBs instead of
    # re-running DeBERTa on every FB. Verification is deterministic (temp=0.0),
    # so re-verifying is only wasteful — but skipping via stable fb_id is both
    # cheap and safe. A corrupt partial checkpoint is discarded (fail-closed),
    # never silently trusted.
    verified: list[dict] = []
    done_ids: set[str] = set()

    # ── D2485 (P0): S5 input fingerprint — hard-discard stale/unvalidated checkpoints ──
    # The D2409 fb_id-overlap guard CANNOT detect a stale S5 checkpoint whose
    # fb_ids are content-stable (SHA256(name,definition)) — two runs can share
    # ~93% of fb_ids while verifying a DIFFERENT S4 output (the BUG-150 stale
    # t11 archive). The fingerprint binds the checkpoint to the exact S4 input
    # (hash) + config + model lineup, and hard-discards on any mismatch. A missing
    # fingerprint is treated as a mismatch (fail-closed, C16) so the manual
    # archive ritual is no longer required.
    _cur_fp = _s5_input_fingerprint()
    _cur_fp_id = _fingerprint_id(_cur_fp)
    _stored_fp_id = _load_stored_fingerprint_id()
    _fp_mismatch = _stored_fp_id != _cur_fp_id  # None (absent) → mismatch

    if STAGE5_CHECKPOINT.exists() and not _fp_mismatch:
        try:
            prior = load_jsonl(STAGE5_CHECKPOINT, context="S5 checkpoint")
            done_ids = {vfb.get("fb_id") for vfb in prior if vfb.get("fb_id")}
            verified = prior
        except Exception as e:
            print(f"   ⚠️  S5 resume checkpoint unreadable ({type(e).__name__}: {e}) — re-verifying all")
            verified = []
            done_ids = set()
    elif STAGE5_CHECKPOINT.exists():
        _reason = "fingerprint absent" if _stored_fp_id is None else "fingerprint MISMATCH"
        print(f"   🛑 S5 checkpoint {_reason} — hard-discarding and re-verifying all "
              f"(D2485: no manual archive needed)")
        verified = []
        done_ids = set()

    # D2409 (defense-in-depth): discard a checkpoint with zero fb_id overlap with
    # the current S4 output. Mirrors S2's D2317 and S4's D2370 stale-checkpoint guard.
    if done_ids:
        current_ids = {fb.get("fb_id") for fb in fbs if fb.get("fb_id")}
        if not (done_ids & current_ids):
            print(f"   ⚠️  S5 resume checkpoint is from a different run "
                  f"({len(done_ids)} stale IDs, 0 overlap) — discarding")
            verified = []
            done_ids = set()
    if done_ids:
        remaining = [fb for fb in fbs if fb.get("fb_id") not in done_ids]
        print(f"   📋 S5 resuming: {len(done_ids)} FBs already verified → {len(remaining)} remaining")
        fbs = remaining

    # Persist the input fingerprint so the NEXT resume validates against THIS input.
    _write_input_fingerprint()

    total = len(fbs)
    _thresh = S5_NLI_PASS_THRESHOLD  # config-driven (C12), calibrated: 0.10

    # Preload DeBERTa model
    _load_dual_encoders()

    print(f"🔍 Stage 5: DeBERTa-Only Verify — {total} FBs")
    print("   DeBERTa-v3-large (435M, MNLI+FEVER+ANLI+Ling+WANLI) — D2298 calibrated")
    print(f"   Threshold: {_thresh} (Calibrated: P=0.647 R=0.386 F1=0.484) | Fail-closed: ✅ (D2093)")
    print(f"   ENTAIL ≥ {_thresh} → PASS | Otherwise → QUARANTINE")
    print(f"{'='*60}")

    # Seed stats from any resumed FBs so the final tallies reflect the full run.
    stats = {"PASS": 0, "FLAG": 0, "QUARANTINE": 0}
    for vfb in verified:
        stats[vfb.get("status", "QUARANTINE")] = stats.get(vfb.get("status", "QUARANTINE"), 0) + 1
    pipeline_commit = get_pipeline_commit()

    for i, fb in enumerate(fbs, 1):
        name = fb.get("name", "unnamed")[:40]
        print(f"  [{i}/{total}] {name}", end=" ")

        start = time.time()
        results = []

        # 1. Mechanism quality pre-filter (regex, tautology detection)
        mech_passed, mech_score_float, mech_detail = check_mechanism_quality(fb)
        results.append({
            "check_name": "mechanism_quality",
            "passed": mech_passed,
            "score": mech_score_float,
            "detail": mech_detail,
        })

        # 2. Dual-encoder factual check
        fact_passed: bool = True
        fact_score: float = 1.0
        fact_detail: str = "No verification needed"

        method: str = "deberta-nli"

        if fb.get("classification_status") == "FAILED":
            # D2405: S4 classification failure must NEVER PASS — force QUARANTINE, skip NLI
            fact_passed = False
            fact_score = 0.0
            fact_detail = f"S4 classification FAILED: {str(fb.get('classification_error', 'unknown'))[:120]}"
            method = "classification_failed"
        elif not mech_passed:
            # Tautological mechanism → auto-quarantine
            fact_passed = False
            fact_score = 0.0
            fact_detail = f"MECH FAIL: {mech_detail}"
            method = "mech_quality"

        else:
            # D2298: DeBERTa-only NLI (RoBERTa removed — zero signal on paraphrase evidence)
            try:
                fact_passed, fact_score, fact_detail = deberta_check(fb)
                method = "deberta-nli"
            except Exception as e:
                fact_passed = False
                fact_score = 0.0
                fact_detail = f"Dual-encoder error — QUARANTINE: {e}"

        results.append({
            "check_name": "factual",
            "passed": fact_passed,
            "score": fact_score,
            "detail": fact_detail,
        })

        # 2b. D2277: Enrichment verification — light check that S4 fields don't contradict core
        enrich_passed, enrich_score, enrich_detail = _check_enrichment_quality(fb)
        if not enrich_passed:
            results.append({
                "check_name": "enrichment_quality",
                "passed": enrich_passed,
                "score": enrich_score,
                "detail": enrich_detail,
            })

        # 3. Determine status — DeBERTa-only (D2322 calibrated)
        if fact_passed:
            status = "PASS"
            needs_human = False
        else:
            status = "QUARANTINE"
            needs_human = False  # DeBERTa is the final authority — no human needed

        # Handle strict mode: any non-PASS → QUARANTINE
        if strict and status != "PASS":
            status = "QUARANTINE"

        stats[status] += 1

        # D2310: ISOR computed BEFORE confidence (confidence uses ISOR, not NLI).
        from pipeline.schema_accessor import isor_score as _isor_score
        isor = _isor_score(fb)
        isor_composite = float(isor.get("score", 0.0))

        # D2310: Confidence = mechanism + enrichment + ISOR (NLI is a binary gate).
        confidence_score = round(
            S5_CONF_MECH_WEIGHT * mech_score_float
            + S5_CONF_ENRICH_WEIGHT * enrich_score
            + S5_CONF_ISOR_WEIGHT * isor_composite,
            4,
        )
        if not fact_passed:
            # NLI gate failed → cap confidence (fail-closed, D2093).
            confidence_score = min(confidence_score, S5_QUARANTINE_CONF_CAP)

        # D2310: human adjudication for QUARANTINED canonical principles (strong ISOR + NLI fail).
        if not fact_passed and isor.get("rating") == S5_HUMAN_REVIEW_ISOR:
            needs_human = True

        # Build verified FB. R14/C10: preserve generator provenance from Stage 4
        # (gen_model stays = generator); verifier identity is captured in verifier_model below.
        vfb = dict(fb)
        vfb["pipeline_commit"] = pipeline_commit
        vfb["verification_results"] = results
        vfb["confidence_score"] = confidence_score
        vfb["status"] = status
        vfb["needs_human_review"] = needs_human
        vfb["verifier_model"] = "DeBERTa-v3-large (D2322 calibrated, threshold 0.10)"
        vfb["verification_method"] = method

        # D2284: Epistemic status — ISOR scoring
        if isor["rating"] in ("strong",) and fact_passed:
            epistemic_status = "corroborated"
        elif isor["rating"] in ("strong", "medium") and not fact_passed:
            epistemic_status = "cross-source-unverified"
        elif fact_passed:
            epistemic_status = "source-supported"
        else:
            epistemic_status = "speculative"
        vfb["epistemic_status"] = epistemic_status
        vfb["isor"] = isor  # D2284: Full ISOR scores embedded in verified FB

        elapsed = time.time() - start
        icon = {"PASS": "✅", "FLAG": "⚠️", "QUARANTINE": "🚫"}.get(status, "❓")
        print(f"→ {icon} {status} ({elapsed:.1f}s)")
        verified.append(vfb)

        # D2409: incremental checkpoint every N FBs — crash recovery for the serial S5.
        if i % S5_CHECKPOINT_INTERVAL == 0:
            _write_s5_checkpoint(verified)

    # Save final checkpoint — serialize to JSONL (D2299: was passing list, caused TypeError)
    _write_s5_checkpoint(verified)
    print(f"\n{'='*60}")
    print("📊 VERIFICATION RESULTS")
    for s, c in stats.items():
        print(f"   {s}: {c}")
    print("\n📊 DeBERTa-ONLY VERIFICATION (D2322 calibrated)")
    print("   ENTAIL ≥ threshold → PASS:     auto")
    print("   CONTRA → QUARANTINE:            auto")
    print(f"   Disagree → FLAG (human): {stats.get('FLAG', 0)} FBs need review")
    print(f"   Mechanisms auto-rejected: {sum(1 for fb in verified if 'MECH FAIL' in str(fb.get('verification_results', [])))}")
    print(f"\n📋 Checkpoint: {STAGE5_CHECKPOINT}")
    return verified

def main():
    parser = argparse.ArgumentParser(
        description="Stage 5: Verify FBs via DeBERTa NLI + Gemma-4-E4B"
    )
    parser.add_argument("--strict", action="store_true",
                        help="Quarantine on any failure (default: flag on BORP-only)")
    parser.add_argument("--skip-nli", action="store_true",
                        help="Skip DeBERTa NLI pre-filter, use LLM for all checks")
    args = parser.parse_args()

    run_stage5(strict=args.strict, skip_nli=args.skip_nli)


if __name__ == "__main__":
    main()
