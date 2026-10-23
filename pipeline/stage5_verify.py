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
  3. Aggregation: OR-entail + AND-no-contra (D-2822); PASS threshold 0.5 (D-2863): P=0.852, R=0.414
  4. Verdict (D2321: premise/hypothesis pairing + all-3-label scoring):
     → OR-entail (≥1 entail ≥ 0.5 AND 0 contra) → PASS
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
  Calibration: D-2863 or-entail PASS threshold 0.5 (P=0.852, R=0.414); supersedes D-2298 majority@0.10 (P=0.647, R=0.386, F1=0.484)
  Speed: ~290ms per sentence pair on MPS (loaded in 6s)

Usage:
    python3 pipeline/stage5_verify.py
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.io_guard import load_jsonl, safe_write  # D2332: fail-closed JSONL boundary
from pipeline.pipeline_paths import (
    _CFG,  # D2405: C12 config-first threshold source
    CHECKPOINT_DIR,
    GEN_MODEL,  # D2485: S5 input fingerprint (generator identity)
    PROJECT_ROOT,  # D-330: repo root for the path-scoped S5 fingerprint
    S5_CHECKPOINT_INTERVAL,  # D2409: intra-stage incremental checkpoint cadence (FBs)
    S5_EVIDENCE_CONTAMINATION_RATIO,  # D2545: D2496/BUG-181#1 severe evidence-contamination threshold (C12 config-first)
    S5_NLI_MAX_HYPOTHESIS_CHARS,  # D2321: hypothesis(definition) truncation for NLI pairing
    S5_NLI_MAX_PREMISE_CHARS,  # D2321: premise(evidence) truncation for NLI pairing
    S5_NLI_MODEL_LARGE,  # D2298: DeBERTa-v3-large (435M) sole NLI verifier
    S5_NLI_PASS_THRESHOLD,  # D2155: NLI score threshold for PASS (0.10, D2298 calibrated)
    S5_QUARANTINE_CONF_CAP,  # noqa: F401  re-exported: tests/test_fail_closed_d2402_2405.py asserts against it  # D2310: confidence cap for QUARANTINE
    SCHEMA_VERSION,  # D2485: S5 input fingerprint
    STAGE4_5_CHECKPOINT,  # F1/D2400: enriched S4 checkpoint (preferred when present)
    STAGE4_CHECKPOINT,
    STAGE5_CHECKPOINT,
    TAXONOMY_VERSION,  # D2485: S5 input fingerprint
    VERIFY_MODEL,  # D2485: S5 input fingerprint (classifier identity)
)

# fb_definition/fb_source_texts/fb_source_texts_shown imported locally inside
# deberta_check() to avoid a module-level circular import (schema_accessor ↔ stage5_verify).
from pipeline.stamp import get_manifest_hash, get_pipeline_commit  # D2485: manifest fingerprint

# classify_practicality / derive_* are NO LONGER IMPORTED HERE: they are asked by the ONE home of the
# per-record sequence (pipeline/verify_record.py, T-196/D-3136). S5 imports the home, not the rules.

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


def _is_garbage_passage(text: str) -> bool:
    """D2506/B2: deterministic heuristic for non-evidence fragments (captions/titles/UI).

    Conservative — only flags UNAMBIGUOUS garbage so legitimate short quotes are not
    dropped: (1) too few words to be a claim, (2) underscore placeholders ("Data ____
    stories"), (3) symbol-dense non-prose (figure captions, arrow diagrams). Applied in
    deberta_check() BEFORE NLI scoring so contradiction/neutral verdicts are never
    computed from garbage premises.
    """
    t = (text or "").strip()
    if not t:
        return True
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", t)
    if not words:
        return True
    if len(words) < EVIDENCE_GARBAGE_MIN_WORDS:
        return True  # "Time 3 minutes", "Data ____ stories"
    if t.count("_") > EVIDENCE_GARBAGE_MAX_UNDERSCORE:
        return True  # title placeholder with underscore runs
    alpha_chars = sum(len(w) for w in words)
    if alpha_chars / max(len(t), 1) < EVIDENCE_GARBAGE_MIN_ALPHA_RATIO:
        return True  # punctuation/symbol-dense fragment
    return False


def _b2_majority_verdict(
    entail_scores: list[float],
    contra_scores: list[float],
    neutral_scores: list[float],
    thresh: float,
) -> tuple[bool, float, str]:
    """D2507 (B2): cross-passage majority aggregation (pure, model-free).

    OLD (weak max-entailment): `max(entail)` let a SINGLE passage pass the whole FB
    and a single contradicting passage was ignored when max-entail cleared `thresh`
    first. NEW: majority vote over CLEAN passages — PASS requires a strict majority
    to entail, CONTRA requires a strict majority to contradict, else NEUTRAL.

    The returned score remains `max(entail)` (the continuous entailment probability)
    so `nli_calibrate.py`'s threshold sweep is unaffected; only the DECISION changes.

    Args:
        entail_scores: Per-passage entailment probabilities (aligned 1:1).
        contra_scores: Per-passage contradiction probabilities.
        neutral_scores: Per-passage neutral probabilities.
        thresh: Entailment threshold (a passage "entails" if entail >= thresh).

    Returns:
        (passed, score, detail) — same contract as deberta_check().
    """
    _max_entail = max(entail_scores, default=0.0)
    _n_clean = len(entail_scores)
    _n_entail = sum(1 for s in entail_scores if s >= thresh)
    _n_contra = sum(
        1 for (e, c, u) in zip(entail_scores, contra_scores, neutral_scores, strict=True)
        if c > e and c > u
    )
    _entail_ratio = _n_entail / _n_clean if _n_clean else 0.0
    _contra_ratio = _n_contra / _n_clean if _n_clean else 0.0

    if _entail_ratio > B2_MAJORITY_RATIO:
        return True, round(_max_entail, 4), (
            f"ENTAIL (majority {_n_entail}/{_n_clean}): ent={_entail_ratio:.2f} max={_max_entail:.2f}"
        )
    if _contra_ratio > B2_MAJORITY_RATIO:
        return False, round(_max_entail, 4), (
            f"CONTRA (majority {_n_contra}/{_n_clean}): ent={_entail_ratio:.2f} cont={_contra_ratio:.2f}"
        )
    return False, round(_max_entail, 4), (
        f"NEUTRAL (ent {_n_entail}/{_n_clean}, cont {_n_contra}/{_n_clean}): max={_max_entail:.2f}"
    )


def _or_entail_and_no_contra_verdict(
    entail_scores: list[float],
    contra_scores: list[float],
    neutral_scores: list[float],
    thresh: float,
) -> tuple[bool, float, str]:
    """D-2822 (Gate A(d)): OR-entail + AND-no-contradiction aggregation (pure, model-free).

    A convergent FB is VERIFIED only when the evidence set OR-entails the claim (at least
    ONE clean passage entails, i.e. `entail >= thresh`) AND no passage contradicts it
    (AND-no-contra: ZERO passages where contradiction is the top label).

    Rationale (D-2822): the D2507/B2 majority rule can HIDE a supported claim (the D272g
    re-derivation counted 1,514 NEUTRAL and 506 ENTAIL-majority rows where a single strong
    entailment was buried under neutral passages) and can PASS a claim carrying BOTH
    entailment and contradiction. Support is existential (OR), contradiction is universal
    (AND-NOT).

    The returned score remains `max(entail)` so `nli_calibrate.py`'s threshold sweep is
    unaffected; only the DECISION changes. Because a claim now survives on ONE entail, the
    per-passage threshold must be re-calibrated (D-2822 step 2) before enabling this mode.

    Args:
        entail_scores: Per-passage entailment probabilities (aligned 1:1).
        contra_scores: Per-passage contradiction probabilities.
        neutral_scores: Per-passage neutral probabilities.
        thresh: Entailment threshold (a passage "entails" if entail >= thresh).

    Returns:
        (passed, score, detail) — same contract as deberta_check().
    """
    _max_entail = max(entail_scores, default=0.0)
    _n_clean = len(entail_scores)
    _n_entail = sum(1 for s in entail_scores if s >= thresh)
    _n_contra = sum(
        1 for (e, c, u) in zip(entail_scores, contra_scores, neutral_scores, strict=True)
        if c > e and c > u
    )
    if _n_entail >= 1 and _n_contra == 0:
        return True, round(_max_entail, 4), (
            f"ENTAIL (OR-entail + AND-no-contra): {_n_entail}/{_n_clean} entail, "
            f"0 contra, max={_max_entail:.2f}"
        )
    if _n_contra >= 1:
        return False, round(_max_entail, 4), (
            f"CONTRA (AND-no-contra veto): {_n_contra}/{_n_clean} contra, "
            f"{_n_entail}/{_n_clean} entail, max={_max_entail:.2f}"
        )
    return False, round(_max_entail, 4), (
        f"NEUTRAL (no entailing passage): {_n_entail}/{_n_clean} entail, "
        f"{_n_contra}/{_n_clean} contra, max={_max_entail:.2f}"
    )


def _aggregate_verdict(
    entail_scores: list[float],
    contra_scores: list[float],
    neutral_scores: list[float],
    thresh: float,
) -> tuple[bool, float, str]:
    """D-2822: dispatch the cross-passage aggregation primitive by config (C12)."""
    if NLI_AGGREGATION == "or_entail_and_no_contra":
        return _or_entail_and_no_contra_verdict(
            entail_scores, contra_scores, neutral_scores, thresh
        )
    return _b2_majority_verdict(entail_scores, contra_scores, neutral_scores, thresh)


def _paraphrase_similarity(definition: str, evidence_passages: list[str]) -> float:
    """D-B (BUG-705): max STS cosine between the FB definition and its CLEAN evidence
    passages via the repo embedding (bge-m3 → 512d L2-normalized).

    Fail-closed: returns 0.0 on empty input, unknown backend, or any embed/import
    failure, so the similarity path can never flip a NEUTRAL to PASS on a broken
    signal. Vectors are L2-normalized, so cosine == dot product (pure Python — this
    module has no numpy dependency). C21: the backend is selected by `paraphrase_model`;
    add a branch here to swap the embedding primitive.
    """
    if not definition or not evidence_passages:
        return 0.0
    if PARAPHRASE_MODEL != "bge-m3":
        return 0.0  # C21 seam: only bge-m3 is wired today; unknown backend → fail-closed
    try:
        from pipeline.embeddings import embed_texts_bge_m3
    except Exception:
        return 0.0
    _def = definition[:PARAPHRASE_MAX_CHARS]
    _eps = [p[:PARAPHRASE_MAX_CHARS] for p in evidence_passages]
    try:
        _vecs = embed_texts_bge_m3([_def] + _eps)
    except Exception:
        return 0.0
    if _vecs is None or len(_vecs) < 2:
        return 0.0
    _def_v = list(_vecs[0])
    _best = 0.0
    for _row in _vecs[1:]:
        _cos = sum(_a * _b for _a, _b in zip(_def_v, list(_row), strict=True))
        _best = max(_best, _cos)
    return _best


def deberta_check(fb: dict) -> tuple[bool, float, str]:
    """D2298-calibrated NLI check, D2321-corrected pairing, D2322 raw-score return.

    Threshold 0.5 from D-2863 or-entail recalibration: P=0.852, R=0.414 (supersedes D-2298 majority@0.10 P=0.647 R=0.386 F1=0.484).
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
    _garbage_skipped: int = 0  # D2506/B2: non-evidence fragments excluded from NLI
    _clean_eps: list[str] = []  # D-B (BUG-705): clean premises for the similarity pass

    for _ep in _eps[:8]:
        if not _ep.strip():
            continue
        if _is_garbage_passage(_ep):
            _garbage_skipped += 1
            continue  # D2506/B2: never score NLI against a caption/title/UI fragment
        _prem = _ep[:S5_NLI_MAX_PREMISE_CHARS]  # premise = evidence passage
        _hyp = _def[:S5_NLI_MAX_HYPOTHESIS_CHARS]  # hypothesis = FB definition
        _clean_eps.append(_prem)  # D-B (BUG-705): retain clean premise for the similarity pass
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
    if _garbage_skipped:
        fb["evidence_garbage_skipped"] = _garbage_skipped  # D2506/B2: observability
    if not (_entail_scores or _contra_scores or _neutral_scores):
        if _garbage_skipped:
            return False, 0.0, (
                f"All {_garbage_skipped} evidence passages are non-evidence fragments — "
                "QUARANTINE (no clean premise for NLI)"
            )
        return False, 0.0, "NLI scoring failed — QUARANTINE"

    # D2507/D-2822: cross-passage aggregation (majority OR or-entail+AND-no-contra, C12).
    _passed, _score, _detail = _aggregate_verdict(
        _entail_scores, _contra_scores, _neutral_scores, _thresh
    )
    # D-B (BUG-705): paraphrase-aware grounding — RECALL path. Gated so it can ONLY flip a
    # NEUTRAL to PASS (never downgrade a PASS). Inert unless PARAPHRASE_PATH_ENABLED.
    if not _passed and PARAPHRASE_PATH_ENABLED:
        _n_entail = sum(1 for s in _entail_scores if s >= PARAPHRASE_ENTAIL_THRESHOLD)
        _n_contra = sum(
            1 for (e, c, u) in zip(_entail_scores, _contra_scores, _neutral_scores, strict=True)
            if c > e and c > u
        )
        _no_contra_ok = (not PARAPHRASE_REQUIRE_NO_CONTRA) or (_n_contra == 0)
        if _n_entail >= PARAPHRASE_MIN_ENTAIL and _no_contra_ok:
            _sim = _paraphrase_similarity(_def, _clean_eps)
            if _sim >= PARAPHRASE_SIMILARITY_THRESHOLD:
                return True, round(_sim, 4), (
                    f"PARAPHRASE (STS {_sim:.3f} >= {PARAPHRASE_SIMILARITY_THRESHOLD}): "
                    f"faithful reworded-true claim ({_n_entail}/{len(_entail_scores)} entail, "
                    f"0 contra)"
                )
    return _passed, _score, _detail


# nli_evidence_check REMOVED (D2298) — superseded by deberta_check(); referenced deleted
# nli_entailment (F821). DeBERTa-v3-large is the sole NLI verifier.

# ── Core verification functions ────────────────────────────────────────────

def _load_expected_fb_count(source: Path) -> int | None:
    """D2496: read the authoritative expected FB count S4 persisted at completion.

    Looked up next to the source checkpoint first (S4.5 enrichment output), then next
    to the plain S4 checkpoint (enrichment preserves record count). Returns None when
    absent so the preflight degrades to the manifest-only check (no hard failure on
    legacy checkpoints that predate the sidecar).
    """
    candidates = [Path(str(source) + ".expected_count.json")]
    if source != STAGE4_CHECKPOINT:
        candidates.append(Path(str(STAGE4_CHECKPOINT) + ".expected_count.json"))
    for c in candidates:
        if c.exists():
            try:
                return int(json.loads(c.read_text(encoding="utf-8")).get("expected_fb_count"))
            except (ValueError, TypeError, KeyError, json.JSONDecodeError) as e:
                print(f"   ⚠️  Expected-count sidecar unreadable {c.name}: {e} (C16)", file=sys.stderr)
                return None
    return None


def _load_failed_cluster_ids(source: Path) -> list[dict]:
    """D-2817 Gate B(c): read the failed-cluster receipt S4 persisted (legacy -> empty)."""
    candidates = [Path(str(source) + ".expected_count.json")]
    if source != STAGE4_CHECKPOINT:
        candidates.append(Path(str(STAGE4_CHECKPOINT) + ".expected_count.json"))
    for c in candidates:
        if c.exists():
            try:
                return json.loads(c.read_text(encoding="utf-8")).get("failed_cluster_ids") or []
            except Exception:
                continue
    return []


def _load_declared_failed_count(source: Path) -> int:
    """D-2817: read the declared failed/quarantined cluster count S4 persisted."""
    candidates = [Path(str(source) + ".expected_count.json")]
    if source != STAGE4_CHECKPOINT:
        candidates.append(Path(str(STAGE4_CHECKPOINT) + ".expected_count.json"))
    for c in candidates:
        if c.exists():
            try:
                return int(json.loads(c.read_text(encoding="utf-8")).get("declared_failed_count") or 0)
            except Exception:
                continue
    return 0


def _preflight_gate(source: Path) -> None:
    """D2490: BUG-188 checkpoint boundary + sha256 gate before S5 consumes S4.

    Runs scripts/preflight_checkpoint_check.py --check (D2487): verifies every
    line is standalone JSON + newline-terminated, and — when a manifest exists —
    that sha256 + record_count match. D2496: also asserts on-disk count == the
    authoritative S2-derived expected count (independent of the self-referential
    manifest) so a silent S4-side record DROP fails closed. Fail-closed: a
    truncated / pretty-printed / corrupt / short checkpoint aborts S5.
    """
    preflight = Path(__file__).resolve().parent.parent / "scripts" / "preflight_checkpoint_check.py"
    cmd = [sys.executable, str(preflight), "--check", str(source)]
    expected_count: int | None = _load_expected_fb_count(source)
    if expected_count is not None:
        cmd += ["--expect-count", str(expected_count)]
    declared_failed: int = _load_declared_failed_count(source)
    if declared_failed:
        cmd += ["--declared-failed", str(declared_failed)]
    failed_cluster_ids: list[dict] = _load_failed_cluster_ids(source)
    if failed_cluster_ids:
        cmd += ["--failed-cluster-ids", json.dumps(failed_cluster_ids)]
    r = subprocess.run(cmd, capture_output=True, text=True)
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

# ── D2506/B2: deterministic evidence-passage garbage filter (config-first, C12) ──
# EPUB→MD evidence_passages frequently carry figure captions, book/chapter titles, and
# UI strings ("Time 3 minutes", "Data ____ stories", "The cloud template…") that are NOT
# verbatim source prose. Verifying against them yields meaningless NLI scores (validated
# false-CONTRA in the D2506 stratified sample — claude0041/chatgpt0041).
EVIDENCE_GARBAGE_MIN_WORDS: int = int(_cfg5.get("evidence_garbage_min_words", 6))
EVIDENCE_GARBAGE_MAX_UNDERSCORE: int = int(_cfg5.get("evidence_garbage_max_underscore", 2))
EVIDENCE_GARBAGE_MIN_ALPHA_RATIO: float = float(_cfg5.get("evidence_garbage_min_alpha_ratio", 0.5))

# ── D2507 (B2): cross-passage majority-aggregation threshold (config-first, C12) ──
# Strict majority (> 0.5) of CLEAN evidence passages must entail to PASS, and a strict
# majority must contradict to veto. Replaces the weak single-passage max-entailment rule
# (ChatGPT B2 / MTR task 32). Read at import time alongside the other stage5.* keys.
B2_MAJORITY_RATIO: float = float(_cfg5.get("b2_majority_ratio", 0.5))

# ── D-2822 (Gate A(d)): S5 cross-passage NLI aggregation mode (config-first, C12) ──
# 'majority' = D2507/B2 strict-majority (current, calibrated). 'or_entail_and_no_contra' =
# D-2822 Gate A(d): a convergent FB is VERIFIED only when at least ONE clean passage entails
# (OR-entail) AND ZERO passages contradict (AND-no-contra). FLIP ONLY after D-2822 threshold
# recalibration — the new rule lets a claim survive on ONE entail, so the per-passage
# threshold must be re-swept (nli_calibrate.py) first. Unknown value → fail-closed (C16).
NLI_AGGREGATION: str = str(_cfg5.get("nli_aggregation", "majority")).strip()
_AGGREGATION_MODES: tuple[str, ...] = ("majority", "or_entail_and_no_contra")
if NLI_AGGREGATION not in _AGGREGATION_MODES:
    raise ValueError(
        f"C16: unknown stage5.nli_aggregation={NLI_AGGREGATION!r}; "
        f"expected one of {_AGGREGATION_MODES}"
    )

# ── D-2858: fail-closed guard — or-entail mode requires a matching calibration stamp ──
# A flip to 'or_entail_and_no_contra' is REFUSED (C16) unless config stage5.nli_calibration carries a
# stamp that (a) names the SAME aggregation mode, (b) records a threshold equal to the live
# nli_pass_threshold, and (c) names the decision id that minted the recalibration. This is the
# machine-enforced form of "do NOT flip before recalibration" (D-2822 step 2 / D-2858 step 4): the
# D-2842 code limb is inert by default, and no config edit alone can flip the semantics without the
# freshly re-minted calibration stamp (D-353 rule — a re-pin is a re-mint, never a quiet re-hash).
_NLI_CAL: dict = _cfg5.get("nli_calibration") or {}
if NLI_AGGREGATION == "or_entail_and_no_contra":
    _cal_agg = str(_NLI_CAL.get("aggregation", "")).strip()
    _cal_threshold = _NLI_CAL.get("threshold")
    _cal_decision = str(_NLI_CAL.get("decision", "")).strip()
    _cal_ok = (
        _cal_agg == "or_entail_and_no_contra"
        and _cal_threshold is not None
        and float(_cal_threshold) == float(NLI_PASS_THRESHOLD)
        and bool(_cal_decision)
    )
    if not _cal_ok:
        raise ValueError(
            "C16/D-2858: stage5.nli_aggregation='or_entail_and_no_contra' requires a matching "
            "stage5.nli_calibration stamp {aggregation, threshold, decision} where aggregation equals "
            "the mode, threshold equals nli_pass_threshold, and decision names the minting decision id. "
            "Recalibrate (pipeline/nli_calibrate.py) and re-mint the threshold under a NEW decision id "
            "BEFORE flipping this flag."
        )

# ── D-B (BUG-705): paraphrase-aware grounding — RECALL path (fail-closed, inert by default) ──
# A parallel SECOND signal that can ONLY flip a NEUTRAL to PASS (never downgrade a PASS).
# Gated on n_entail >= paraphrase_min_entail AND n_contra == 0 AND STS cosine >= threshold.
# Inert unless paraphrase_path_enabled=true, which is REFUSED (C16) without a matching
# paraphrase_calibration stamp (D-2858-style). D-2822/or-entail is the PRECISION path; this
# is the RECALL path that recovers faithful reworded-true claims (max entail 0.13–0.46 < 0.5).
PARAPHRASE_PATH_ENABLED: bool = bool(_cfg5.get("paraphrase_path_enabled", False))
PARAPHRASE_SIMILARITY_THRESHOLD: float = float(_cfg5.get("paraphrase_similarity_threshold", 0.85))
PARAPHRASE_MODEL: str = str(_cfg5.get("paraphrase_model", "bge-m3")).strip()
PARAPHRASE_MIN_ENTAIL: int = int(_cfg5.get("paraphrase_min_entail", 1))
# BUG-705-threshold: WEAK-entail pre-filter (NOT the pass threshold). Counting at the pass
# threshold (0.5) made the RECALL path a silent no-op — every target row has max entail < 0.5.
PARAPHRASE_ENTAIL_THRESHOLD: float = float(_cfg5.get("paraphrase_entail_threshold", 0.10))
PARAPHRASE_REQUIRE_NO_CONTRA: bool = bool(_cfg5.get("paraphrase_require_no_contra", True))
PARAPHRASE_MAX_CHARS: int = int(_cfg5.get("paraphrase_max_chars", 1500))
_PARAPHRASE_CAL: dict = _cfg5.get("paraphrase_calibration") or {}
# BUG-705-threshold: structural invariant — the weak-entail pre-filter MUST sit strictly below
# the NLI pass threshold. If it ever equals/exceeds it, the RECALL path silently fires on zero
# rows (the exact no-op this guard exists to prevent). Always-on (not gated on enabled).
if PARAPHRASE_ENTAIL_THRESHOLD >= S5_NLI_PASS_THRESHOLD:
    raise ValueError(
        "C16/D-B: stage5.paraphrase_entail_threshold must be strictly below "
        "stage5.nli_pass_threshold (weak-entail pre-filter, not the pass bar); "
        f"got {PARAPHRASE_ENTAIL_THRESHOLD} >= {S5_NLI_PASS_THRESHOLD}."
    )
if PARAPHRASE_PATH_ENABLED:
    _pcal_decision = str(_PARAPHRASE_CAL.get("decision", "")).strip()
    _pcal_threshold = _PARAPHRASE_CAL.get("threshold")
    _pcal_ok = (
        bool(_pcal_decision)
        and _pcal_threshold is not None
        and float(_pcal_threshold) == float(PARAPHRASE_SIMILARITY_THRESHOLD)
    )
    if not _pcal_ok:
        raise ValueError(
            "C16/D-B: stage5.paraphrase_path_enabled=true requires a matching "
            "stage5.paraphrase_calibration stamp {decision, threshold} where threshold equals "
            "paraphrase_similarity_threshold and decision names the minting decision id. "
            "Calibrate (scripts/paraphrase_calibrate.py) and re-mint the threshold under a NEW "
            "decision id BEFORE enabling this flag."
        )


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
S5_LOCK_PATH = Path(str(STAGE5_CHECKPOINT) + ".lock")  # BUG-361 single-writer


def _sha256_file(path: Path) -> str:
    """SHA-256 of a file's bytes (stable, ignores mtime). Empty for missing files."""
    if not path.exists() or path.is_dir():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _s5_code_fingerprint() -> str:
    """D-330 (BUG-362): sha256 over ONLY the S5-relevant source files.

    The file list is config-owned (C12: stage5.fingerprint_files). An empty list is
    refused (C16, fail-closed): fingerprinting nothing would silently accept ANY code.
    """
    files = list(_CFG.get("stage5", {}).get("fingerprint_files") or [])
    if not files:
        raise RuntimeError("stage5.fingerprint_files is empty — refusing to fingerprint nothing (C16)")
    h = hashlib.sha256()
    for rel in sorted(files):
        f = PROJECT_ROOT / rel
        if not f.exists():
            raise RuntimeError(f"D-330: stage5.fingerprint_files entry missing: {rel} (C16)")
        h.update(rel.encode())
        h.update(b"\0")
        h.update(f.read_bytes())
        h.update(b"\0")
    return h.hexdigest()[:16]


def _s5_config_fingerprint() -> str:
    """D-330: sha256 of the stage5 config slice ONLY (S5's own thresholds, not the manifest)."""
    return hashlib.sha256(
        json.dumps(_CFG.get("stage5", {}) or {}, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]


def _load_stored_fingerprint() -> dict:
    """Return the stored fingerprint's input dict ({} when absent or unreadable)."""
    if not S5_INPUT_FINGERPRINT_PATH.exists():
        return {}
    try:
        return (json.loads(S5_INPUT_FINGERPRINT_PATH.read_text()) or {}).get("input") or {}
    except Exception as e:
        print(f"   ⚠️  stored S5 fingerprint unreadable ({type(e).__name__}: {e}) — treated as absent")
        return {}


def _acquire_single_writer_lock() -> None:
    """BUG-361: at most ONE S5 writer may hold a checkpoint.

    An interleaved writer is worse than a crash: on 2026-09-21 two runs wrote the same
    checkpoint within 4 minutes and the io_guard shrink guard caught the rollback only by
    luck. Fail-closed: refuse to start while a LIVE holder exists, reclaim a dead one.
    Disable via config (stage5.single_writer_lock) when consciously re-driving a stage.
    """
    import os
    if not bool(_CFG.get("stage5", {}).get("single_writer_lock", True)):
        print("   ⚠️  single-writer lock DISABLED by config — two writers can corrupt this checkpoint")
        return
    if S5_LOCK_PATH.exists():
        try:
            held = int(S5_LOCK_PATH.read_text().split()[0])
        except Exception:
            held = -1
        alive = False
        if held > 0:
            try:
                os.kill(held, 0)
                alive = True
            except OSError:
                alive = False
        if alive:
            raise SystemExit(
                f"🛑 BUG-361: another S5 writer is LIVE (pid {held}, lock {S5_LOCK_PATH.name}) — refusing to "
                f"start a second one. Wait for it, or stop it deliberately (kill {held}) if you are sure it is "
                f"a leftover; the lock is reclaimed automatically once that pid is gone."
            )
        print(f"   ⚠️  reclaiming stale S5 lock (pid {held} is gone)")
        S5_LOCK_PATH.unlink(missing_ok=True)
    S5_LOCK_PATH.write_text(f"{os.getpid()} {time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
    import atexit
    atexit.register(lambda: S5_LOCK_PATH.unlink(missing_ok=True))
    print(f"   🔒 S5 single-writer lock held (pid {os.getpid()})")


def _adopt_fingerprint() -> int:
    """D-330 migration: re-stamp the stored fingerprint under the new scheme, but ONLY if every substantive S5 input is byte-identical.

    This is the BUG-362 migration, and it is deliberately not automatic: it prints the old
    and new ids and refuses if ANY substantive input (S4 checkpoint content, schema,
    taxonomy, models, NLI model) changed. A pure code/config-scheme change is exactly the
    case it exists for; anything else must re-verify.
    """
    cur, stored = _s5_input_fingerprint(), _load_stored_fingerprint()
    if not stored:
        print("   nothing to adopt (no stored fingerprint beside this checkpoint)")
        return 0
    substantive = ("s4_checkpoint", "s4_checkpoint_sha256", "schema_version", "taxonomy_version",
                   "gen_model", "classify_model", "nli_model")
    bad = {k: {"stored": stored.get(k), "current": cur.get(k)} for k in substantive
           if stored.get(k) != cur.get(k)}
    if bad:
        print("🛑 REFUSING to adopt (D-330): substantive S5 inputs differ — this checkpoint is NOT about the same input")
        for k, v in bad.items():
            print(f"     {k}: stored={v['stored']!r} current={v['current']!r}")
        print("   → the checkpoint must re-verify (run without --adopt-fingerprint).")
        return 1
    changed = sorted(k for k in set(stored) | set(cur) if stored.get(k) != cur.get(k))
    print(f"   📌 fingerprint migration: {_load_stored_fingerprint_id()} → {_fingerprint_id(cur)}")
    print(f"      all {len(substantive)} substantive inputs identical; changed keys (informational/scheme): {changed}")
    _write_input_fingerprint()
    print("   ✅ adopted — the existing checkpoint stays valid")
    return 0


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
        # D-330 (BUG-362): bind ONLY what determines S5 behaviour. Global HEAD and the
        # whole-config manifest_hash moved on governance-only commits and hard-discarded a
        # live 1,250-row checkpoint; they are now recorded as INFORMATION, not as identity.
        "s5_code_sha256": _s5_code_fingerprint(),
        "s5_config_sha256": _s5_config_fingerprint(),
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
        "informational": {  # D-330: recorded for audit, deliberately NOT part of the identity
            "pipeline_commit": get_pipeline_commit(),
            "manifest_hash": get_manifest_hash(),
            "written_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        },
    }
    try:
        S5_INPUT_FINGERPRINT_PATH.parent.mkdir(parents=True, exist_ok=True)
        S5_INPUT_FINGERPRINT_PATH.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n"
        )
    except Exception as e:
        print(f"   ⚠️  Could not persist S5 input fingerprint: {e}")


# ── Main ────────────────────────────────────────────────────────────────────

# D2496/BUG-181#1: severe evidence-contamination threshold — matches the
# scripts/audit_evidence_cleanliness.py "severe" cutoff (artifact-char ratio > 0.15).
EVIDENCE_CONTAMINATION_RATIO: float = S5_EVIDENCE_CONTAMINATION_RATIO  # D2545: from config (C12)


def _evidence_cleanliness_gate(fbs: list[dict]) -> set[str]:
    """D2496/BUG-181#1: quarantine FBs whose evidence_passages carry EPUB→MD
    conversion artifacts (CSS fragments, {=html} markers, image placeholders).

    S5 DeBERTa NLI verifies against evidence_passages; verifying against garbage
    yields meaningless scores and lets contaminated records PASS into S6. Severe
    contamination must QUARANTINE instead. Returns the set of fb_ids to quarantine.
    """
    scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        import audit_evidence_cleanliness as _evc  # noqa: PLC0415 — deferred, standalone audit tool
    except Exception as e:  # BUG-202: fail-CLOSED — a missing gate must abort S5, never verify against possibly-contaminated evidence blind
        raise RuntimeError(
            f"BUG-181#1 evidence-cleanliness gate unavailable — aborting S5 (fail-closed): "
            f"{type(e).__name__}: {e}"
        ) from e
    contaminated: set[str] = set()
    for fb in fbs:
        for ep in fb.get("evidence_passages") or []:
            _matched, ratio = _evc.classify_passage(ep)
            if ratio > EVIDENCE_CONTAMINATION_RATIO:
                contaminated.add(fb.get("fb_id", ""))
                break
    if contaminated:
        print(f"   🧼 BUG-181#1 evidence gate: {len(contaminated)} FB(s) with severe "
              f"EPUB→MD evidence contamination → QUARANTINE (no NLI)")
    return contaminated


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

    # D2496/BUG-181#1: evidence-cleanliness gate — quarantine severe EPUB→MD
    # evidence contamination before any NLI (verifying against garbage is meaningless).
    severe_evidence_ids: set[str] = _evidence_cleanliness_gate(fbs)

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

    _acquire_single_writer_lock()  # BUG-361: no second writer may touch this checkpoint

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
        _stored_fp = _load_stored_fingerprint()
        _diff_keys = sorted(k for k in set(_stored_fp) | set(_cur_fp) if _stored_fp.get(k) != _cur_fp.get(k))
        _reason = ("fingerprint absent" if _stored_fp_id is None
                   else f"fingerprint MISMATCH on {_diff_keys}")
        print(f"   🛑 S5 checkpoint {_reason} — hard-discarding and re-verifying all "
              f"(D2485: no manual archive needed)")
        # D2507 (BUG-206): archive the stale checkpoint BEFORE re-verifying. The
        # io_guard.safe_write shrink guard refuses a >10% smaller first incremental
        # write over the stale 100MB file (reads as a partial-state overwrite), so
        # the "hard-discard" path must move the old file aside rather than rely on
        # in-place overwrite. R-D410-safe: RENAME (never delete) to a timestamped
        # .stale_* backup so the old verdicts remain recoverable.
        _stale_ts = time.strftime("%Y%m%d_%H%M%S")
        try:
            _stale_ckpt = Path(str(STAGE5_CHECKPOINT) + f".stale_{_stale_ts}")
            STAGE5_CHECKPOINT.replace(_stale_ckpt)
            _stale_fp = Path(str(STAGE5_CHECKPOINT) + ".input_fingerprint.json")
            if _stale_fp.exists():
                _stale_fp.replace(str(_stale_fp) + f".stale_{_stale_ts}")
        except OSError as e:
            print(f"   🛑 could not archive stale S5 checkpoint ({type(e).__name__}: {e}) — aborting (fail-closed)")
            raise
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
    _thresh = S5_NLI_PASS_THRESHOLD  # config-driven (C12), calibrated: 0.5 (D-2863)

    # Preload DeBERTa model
    _load_dual_encoders()

    print(f"🔍 Stage 5: DeBERTa-Only Verify — {total} FBs")
    print("   DeBERTa-v3-large (435M, MNLI+FEVER+ANLI+Ling+WANLI) — D2298 calibrated")
    _cal_p = _NLI_CAL.get("precision")
    _cal_r = _NLI_CAL.get("recall")
    if _cal_p is not None and _cal_r is not None:
        _cal_f1 = round(2.0 * float(_cal_p) * float(_cal_r) / (float(_cal_p) + float(_cal_r)), 3)
        _cal_note = f"P={_cal_p} R={_cal_r} F1={_cal_f1}"
    else:
        _cal_note = f"see {_NLI_CAL.get('decision', 'D-2298')}"
    print(f"   Threshold: {_thresh} ({_NLI_CAL.get('decision', 'D-2298')} Calibrated: {_cal_note}) | Fail-closed: ✅ (D2093)")
    print(f"   ENTAIL ≥ {_thresh} → PASS | Otherwise → QUARANTINE")
    print(f"{'='*60}")

    # Seed stats from any resumed FBs so the final tallies reflect the full run.
    # BUG-203/D2504: S5 is DeBERTa-only (D2322) — it emits only PASS/QUARANTINE.
    # `FLAG` (human-adjudication) was removed from S5; a legacy resumed record
    # with status FLAG is tallied dynamically below via .get(status, 0).
    stats = {"PASS": 0, "QUARANTINE": 0}
    for vfb in verified:
        stats[vfb.get("status", "QUARANTINE")] = stats.get(vfb.get("status", "QUARANTINE"), 0) + 1
    pipeline_commit = get_pipeline_commit()

    for i, fb in enumerate(fbs, 1):
        name = fb.get("name", "unnamed")[:40]
        print(f"  [{i}/{total}] {name}", end=" ")

        start = time.time()

        # T-196/D-3136 (MEASURED 2026-10-23): this loop body WAS the rule, and three other writers copied it —
        # four copies, four behaviours (BUG-978 holes 1-6, BUG-979, BUG-980, BUG-981). The sequence now has ONE
        # home and S5 asks it like every other writer does. `run_stage5` owns only what is S5-specific: the
        # evidence-cleanliness population, the `--strict` posture, the per-record progress line and the
        # checkpoint. Imported INSIDE the function: `verify_record` imports this module for the instruments, so a
        # module-level import here would be a cycle.
        from pipeline.verify_record import verify_one_record

        outcome = verify_one_record(fb, severe_evidence_ids=severe_evidence_ids, strict=strict)
        status = outcome.status
        stats[status] += 1

        # Build verified FB. R14/C10: preserve generator provenance from Stage 4
        # (gen_model stays = generator); verifier identity is captured in verifier_model by the home.
        vfb = dict(fb)
        vfb["pipeline_commit"] = pipeline_commit
        vfb.update(outcome.checkpoint_cells())

        elapsed = time.time() - start
        icon = {"PASS": "✅", "QUARANTINE": "🚫"}.get(status, "❓")
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
    print(f"   Quarantined needing human review: {sum(1 for fb in verified if fb.get('needs_human_review'))}")
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
    parser.add_argument("--adopt-fingerprint", action="store_true",
                        help="D-330 migration: re-stamp the stored fingerprint under the current scheme "
                             "ONLY if every substantive S5 input is identical (BUG-362)")
    args = parser.parse_args()
    if getattr(args, "adopt_fingerprint", False):
        return _adopt_fingerprint()

    run_stage5(strict=args.strict, skip_nli=args.skip_nli)


if __name__ == "__main__":
    main()
