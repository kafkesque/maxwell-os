#!/usr/bin/env python3
"""
DSPy Fine-Tuning Harness for Maxwell OS S2 Extraction Stage (T-007).

Trains the S2 extractor (Qwen3-Coder) to produce convergent Foundation Blocks
from multi-source book segment clusters using the v4.4 golden set (75 examples,
77 FBs). Uses DirectOMLXLM (custom dspy.LM subclass) that bypasses litellm for all optimizers.

Architecture:
  1. ConvergentExtraction Signature → defines DSPy task I/O
  2. golden_to_examples() → converts golden YAML to dspy.Example[]
  3. stratified_random_split() → train/dev/test with pos/neg stratification
  4. extraction_metric() → penalizes false positives, depth errors, type errors
  5. run_dspy_pilot() → MIPROv2 optimizer on Qwen3-Coder MLX

Usage:
    python3 pipeline/dspy_trainer.py --dry-run         # validate conversion
    python3 pipeline/dspy_trainer.py --pilot           # run 10-example pilot
    python3 pipeline/dspy_trainer.py --full             # full training run

Requirements:
    pip install dspy-ai  (dspy >= 3.3.0)
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

# ── Config (C12: config-driven) ──────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_PATH = PROJECT_ROOT / "config" / "golden" / "stage2_fewshot_convergent.yaml"
CONFIG_PATH = PROJECT_ROOT / "config" / "pipeline_config.yaml"

# Load config for model settings
with open(CONFIG_PATH) as f:
    _cfg = yaml.safe_load(f)

# Resolve model name: generator is a dict {model, provider, temperature, max_tokens}
_gen = _cfg.get("models", {}).get("generator", {})
DSPY_MODEL = _gen.get("model", "Qwen3-Coder-30B-A3B-Instruct-MLX-4bit") if isinstance(_gen, dict) else str(_gen)
DSPY_TEMPERATURE = float(_gen.get("temperature", 0.0)) if isinstance(_gen, dict) else 0.0
DSPY_MAX_TOKENS = int(_cfg.get("s2", {}).get("dspy_max_tokens", 4096))  # D2304/C12: config-driven (was hardcoded 4096)
# T-007b/D2250: MIPROv2 demo counts — config-driven (C12). D2248 showed 2 demos =
# design-only (Cooper/Krug/Norman) while the golden pool spans 38 domains; 4 demos
# give the optimizer enough labeled coverage for positive-fidelity extraction.
DSPY_MAX_LABELED_DEMOS = int(_cfg.get("s2", {}).get("dspy_max_labeled_demos", 4))
DSPY_MAX_BOOTSTRAPPED_DEMOS = int(_cfg.get("s2", {}).get("dspy_max_bootstrapped_demos", 4))
OMLX_PORT = int(_cfg.get("omlx", {}).get("port", 11435))
RANDOM_SEED = int(_cfg.get("pipeline", {}).get("random_seed", 42))

# Extraction types for validation
# NOTE: Depth is now classified in Stage 4, not S2 (A-001/D2241).
# DEPTHS removed from S2 metric — see CONSTITUTION §2, D2241.
EXTRACTION_TYPES = {"causal_mechanism", "empirical_pattern", "normative_heuristic", "descriptive_model"}


# ──────────────────────────────────────────────────────────────────────
# 1. DSPy Signature
# ──────────────────────────────────────────────────────────────────────

try:
    import dspy
except ImportError:
    print("ERROR: dspy-ai not installed. Run: pip install dspy-ai")
    sys.exit(1)


class ConvergentExtraction(dspy.Signature):
    """
    Given 2-4 source segments from different books, determine whether they
    converge on a shared Foundation Block (FB) and extract it.

    Input: cluster_segments (list of source texts with authors)
    Output: is_convergent (bool), name, definition, mechanism, boundary,
            consequence, extraction_type, evidence_passages, route
    """

    cluster_segments: str = dspy.InputField(
        desc="2-4 source text segments from different books, each with source_book label"
    )
    is_convergent: bool = dspy.OutputField(
        desc="True if multiple independent sources describe the same principle/mechanism"
    )
    name: str = dspy.OutputField(
        desc="Short descriptive name for the Foundation Block (5-12 words)"
    )
    definition: str = dspy.OutputField(
        desc="One-paragraph definition stating WHAT the principle is"
    )
    mechanism: str = dspy.OutputField(
        desc="HOW it works — the causal chain, psychological process, or structural dynamic. For empirical_pattern/normative_heuristic/descriptive_model, explicitly state that this is NOT a causal mechanism"
    )
    boundary: str = dspy.OutputField(
        desc="WHEN it applies and when it fails — scope conditions and edge cases"
    )
    consequence: str = dspy.OutputField(
        desc="SO WHAT — the practical or theoretical implications of this principle"
    )
    extraction_type: str = dspy.OutputField(
        desc="causal_mechanism | empirical_pattern | normative_heuristic | descriptive_model"
    )
    # NOTE: Depth classification moved to Stage 4 (A-001/D2241).
    # S2 extracts principles; S4 classifies depth. See CONSTITUTION §2.
    evidence_passages: str = dspy.OutputField(
        desc="JSON array of verbatim passages from cluster_segments that support this FB (2-4 passages)"
    )
    route: str = dspy.OutputField(
        desc="'FB' if convergent extraction, 'NULL' if rejected"
    )


# ──────────────────────────────────────────────────────────────────────
# 2. Golden Set → dspy.Example Converter
# ──────────────────────────────────────────────────────────────────────

def _format_segments_for_prompt(segments: list[dict]) -> str:
    """Format cluster_segments into a single prompt string."""
    parts = []
    for i, seg in enumerate(segments, 1):
        source = seg.get("source_book", f"Source {i}")
        text = seg.get("text", "")
        parts.append(f"[SOURCE {i}: {source}]\n{text}")
    return "\n\n".join(parts)


def _extract_authors(example: dict) -> set[str]:
    """Extract unique author surnames from source_books and cluster_segments."""
    authors: set[str] = set()
    for book in example.get("source_books", []):
        # Extract last author name: "Title — Author1 & Author2"
        if " — " in book:
            author_part = book.split(" — ")[1]
            for a in author_part.split(" & "):
                a = a.strip()
                # Take last name
                parts = a.split()
                if len(parts) >= 2:
                    authors.add(parts[-1])
                else:
                    authors.add(a)
    # Fallback: check cluster_segments source_book
    for seg in example.get("cluster_segments", []):
        sb = seg.get("source_book", "")
        if " — " in sb:
            author_part = sb.split(" — ")[1]
            for a in author_part.split(" & "):
                authors.add(a.strip().split()[-1] if a.strip().split() else a.strip())
    return authors or {"unknown"}


def golden_to_examples(
    golden_path: Path = GOLDEN_PATH,
    verbose: bool = False,
) -> list[dspy.Example]:
    """
    Convert Maxwell OS golden set (YAML) to dspy.Example objects.

    Each golden example produces one dspy.Example. For 1:N examples (multiple FBs),
    each FB is a separate example with the same cluster_segments input.

    Returns:
        List of dspy.Example objects with .author, .is_positive, .fb_name metadata.
    """
    with open(golden_path) as f:
        data = yaml.safe_load(f)

    examples: list[dspy.Example] = []
    skipped = 0

    for ex in data.get("examples", []):
        eid = ex.get("id", f"unknown_{len(examples)}")
        should_extract = ex.get("should_extract", False)
        is_convergent = ex.get("is_convergent", False)
        segments = ex.get("cluster_segments", [])
        authors = _extract_authors(ex)

        if not segments:
            skipped += 1
            continue

        prompt_text = _format_segments_for_prompt(segments)

        # Handle both single FB and 1:N (multiple FBs per example)
        ef = ex.get("expected_fb", {})
        fbs: list[dict] = ef if isinstance(ef, list) else [ef]

        for i, fb in enumerate(fbs):
            if not isinstance(fb, dict):
                continue
            if not should_extract and not fb.get("name"):
                # Negative without FB details — use the FB fields as empty defaults
                pass

            # Build DSPy example
            evidence_json = json.dumps(fb.get("evidence_passages", [])[:4])

            dspy_ex = dspy.Example(
                cluster_segments=prompt_text,
                is_convergent=should_extract and is_convergent,
                name=fb.get("name", ""),
                definition=fb.get("definition", ""),
                mechanism=fb.get("mechanism", ""),
                boundary=fb.get("boundary", ""),
                consequence=fb.get("consequence", ""),
                extraction_type=fb.get("extraction_type", "causal_mechanism"),
                # Depth no longer in S2 (A-001/D2241) — classified in Stage 4
                evidence_passages=evidence_json,
                route="FB" if should_extract and fb.get("route", "NULL") != "NULL" else "NULL",
            )

            # Mark cluster_segments as the input; all other fields are labels
            dspy_ex = dspy_ex.with_inputs("cluster_segments")

            # Attach metadata (not used by DSPy directly, but needed for split/metric)
            dspy_ex.golden_id = eid + (f"[{i}]" if len(fbs) > 1 else "")
            dspy_ex.authors = frozenset(authors)
            dspy_ex.is_positive = should_extract
            dspy_ex.fb_name = fb.get("name", "")
            # D2304: D2286 tier-aware split — GOLD-A (train) / GOLD-B (dev) / CHALLENGE (test).
            # The golden YAML carries `tier` at the example level. Default to GOLD-A
            # (never treat an unlabeled example as adversarial; GOLD-A is the safe train bucket).
            dspy_ex.tier = ex.get("tier", "GOLD-A")

            examples.append(dspy_ex)

    if verbose:
        positives = sum(1 for e in examples if e.is_positive)
        negatives = sum(1 for e in examples if not e.is_positive)
        print(f"Converted {len(examples)} dspy.Examples ({positives} pos, {negatives} neg) from {len(data.get('examples',[]))} golden entries ({skipped} skipped)")

    return examples


# ──────────────────────────────────────────────────────────────────────
# 3. Author-Grouped Train/Dev/Test Split
# ──────────────────────────────────────────────────────────────────────

def stratified_random_split(
    examples: list[dspy.Example],
    train_frac: float = 0.70,
    dev_frac: float = 0.15,
    seed: int = RANDOM_SEED,
    verbose: bool = False,
) -> tuple[list[dspy.Example], list[dspy.Example], list[dspy.Example]]:
    """
    Stratified random split preserving positive/negative ratio across splits.

    Used as the default split strategy. Author-grouped split is ideal but
    requires a larger golden set (>200 examples) with cleaner author separation.
    At 75 examples with many multi-author pairings, clean author separation
    is mathematically infeasible.

    For the DSPy pilot, we accept some author leakage and rely on the diverse
    source material (40+ distinct authors across 75 examples) to provide
    sufficient generalization signal.

    Returns:
        (train, dev, test) lists of dspy.Example
    """
    random.seed(seed)

    # Separate positives and negatives for stratified sampling
    pos = [e for e in examples if e.is_positive]
    neg = [e for e in examples if not e.is_positive]

    random.shuffle(pos)
    random.shuffle(neg)

    def _split_list(lst: list, f1: float, f2: float) -> tuple[list, list, list]:
        n = len(lst)
        i1 = int(n * f1)
        i2 = int(n * (f1 + f2))
        return lst[:i1], lst[i1:i2], lst[i2:]

    pos_train, pos_dev, pos_test = _split_list(pos, train_frac, dev_frac)
    neg_train, neg_dev, neg_test = _split_list(neg, train_frac, dev_frac)

    train = pos_train + neg_train
    dev = pos_dev + neg_dev
    test = pos_test + neg_test

    random.shuffle(train)
    random.shuffle(dev)
    random.shuffle(test)

    if verbose:
        total = len(examples)
        print(f"Stratified random split: train={len(train)} ({len(train)/total:.0%}), "
              f"dev={len(dev)} ({len(dev)/total:.0%}), test={len(test)} ({len(test)/total:.0%})")
        print(f"  Train: {len(pos_train)} pos, {len(neg_train)} neg")
        print(f"  Dev:   {len(pos_dev)} pos, {len(neg_dev)} neg")
        print(f"  Test:  {len(pos_test)} pos, {len(neg_test)} neg")

        # Report author leakage for transparency
        train_authors = set()
        test_authors = set()
        for ex in train:
            train_authors.update(ex.authors)
        for ex in test:
            test_authors.update(ex.authors)
        leakage = train_authors & test_authors
        unique_authors = train_authors | test_authors
        if unique_authors:
            leak_pct = len(leakage) / len(unique_authors) * 100
            print(f"  Author leakage: {len(leakage)}/{len(unique_authors)} ({leak_pct:.0f}%) — acceptable for pilot")

    return train, dev, test


def tier_aware_split(
    examples: list[dspy.Example],
    verbose: bool = False,
) -> tuple[list[dspy.Example], list[dspy.Example], list[dspy.Example]]:
    """D2304/D2286: Tier-aware split — GOLD-A → train, GOLD-B → dev, CHALLENGE → test.

    The golden YAML carries `tier` per example (GOLD-A: 49, GOLD-B: 3, CHALLENGE: 23).
    D2286 defines the safety contract:
      - GOLD-A  = human-adjudicated, multi-source convergent → TRAIN DSPy
      - GOLD-B  = strong positives with minor ambiguity → DEV (evaluate), never train
      - CHALLENGE = hard negatives / edge cases / adversarial → TEST, NEVER train

    This split is the ONLY correct one for DSPy training: random split (stratified_random_split)
    leaks CHALLENGE hard negatives into train, which optimizes the prompt toward
    rejecting the very edge cases we need it to catch, and leaks GOLD-B into train
    (which D2286 explicitly forbids).

    Fallback: if no example carries a tier (should not happen — golden YAML v5.0 has
    full tier coverage), every example is treated as GOLD-A (train). This preserves
    the old behavior rather than silently dropping data.

    Returns:
        (train, dev, test) lists of dspy.Example, grouped by tier.
    """
    train: list[dspy.Example] = []
    dev: list[dspy.Example] = []
    test: list[dspy.Example] = []

    for ex in examples:
        tier = getattr(ex, "tier", "GOLD-A")
        if tier == "GOLD-B":
            dev.append(ex)
        elif tier == "CHALLENGE":
            test.append(ex)
        else:  # GOLD-A or unlabeled → train (safe default)
            train.append(ex)

    if verbose:
        total = max(len(examples), 1)
        print(f"Tier-aware split (D2286): train(GOLD-A)={len(train)} ({len(train)/total:.0%}), "
              f"dev(GOLD-B)={len(dev)} ({len(dev)/total:.0%}), "
              f"test(CHALLENGE)={len(test)} ({len(test)/total:.0%})")
        # Report tier counts for transparency
        from collections import Counter
        tiers = Counter(getattr(e, "tier", "GOLD-A") for e in examples)
        print(f"  Tier distribution: {dict(tiers)}")
        # Report author leakage for transparency (train vs test)
        train_authors: set[str] = set()
        test_authors: set[str] = set()
        for ex in train:
            train_authors.update(ex.authors)
        for ex in test:
            test_authors.update(ex.authors)
        leakage = train_authors & test_authors
        unique = train_authors | test_authors
        if unique:
            print(f"  Author leakage (train∩test): {len(leakage)}/{len(unique)} ({len(leakage)/len(unique)*100:.0f}%)")

    return train, dev, test


def load_optimized_program(path: Path | str | None = None) -> dspy.Module | None:
    """D2304: Load a previously serialized DSPy program (D2243 persistence).

    Args:
        path: Path to the serialized program JSON. Defaults to the config-driven
              D2243 save path. Returns None if the file does not exist.

    Returns:
        Loaded dspy.Module, or None if load fails.
    """
    from pipeline.pipeline_paths import DSPY_PROGRAM_PATH

    p = Path(path) if path is not None else DSPY_PROGRAM_PATH
    if not p.exists():
        return None

    try:
        # Define the program class (must match the one used at train time)
        class ExtractFB(dspy.Module):
            def __init__(self):
                super().__init__()
                self.extract = dspy.ChainOfThought(ConvergentExtraction)

            def forward(self, cluster_segments: str):
                return self.extract(cluster_segments=cluster_segments)

        program = ExtractFB()
        program.load(str(p))
        return program
    except Exception as e:
        print(f"⚠️  Could not load optimized program from {p}: {e}")
        return None


# ──────────────────────────────────────────────────────────────────────
# 4. Evaluation Metric
# ──────────────────────────────────────────────────────────────────────

def extraction_metric(
    gold: dspy.Example,
    pred: dspy.Example,
    trace: Any = None,
) -> float:
    """
    D2287: Hierarchical metric with hard gates before weighted quality.

    HARD GATES (any failure → score=0, prevents DSPy from optimizing toward dangerous behavior):
      1. evidence_invalid: pred says FB but evidence fabricated/empty → 0
      2. wrong_route: pred says FB but gold says NULL (false positive) → 0
      3. false_convergence: pred is_convergent but single-source evidence → 0

    If all gates pass → weighted quality:
      - convergence_correct: ±0.30
      - type_correct: ±0.20
      - name_similarity: ±0.12
      - mechanism_nonempty: ±0.13
      - evidence_present: ±0.10
      - boundary_present: ±0.05
      - consequence_present: ±0.05
      - route_correct: ±0.05

    Total: 1.0 for perfect match. Depth moved to Stage 4 (A-001/D2241).
    """
    gold_should = gold.is_positive
    pred_route = getattr(pred, "route", "")
    pred_should = pred_route == "FB" if pred_route else bool(getattr(pred, "name", ""))

    # ═══════════════════════════════════════════════════════════════
    # D2287: HARD GATES — any failure → score=0
    # These prevent DSPy from optimizing toward dangerous behavior
    # (e.g., fabricating evidence to boost the weighted quality score).
    # ═══════════════════════════════════════════════════════════════

    # GATE 1: evidence_invalid — pred claims FB but evidence is fabricated/empty
    if pred_should:
        pred_evidence = getattr(pred, "evidence_passages", "[]")
        try:
            ev_list = json.loads(pred_evidence) if isinstance(pred_evidence, str) else pred_evidence
        except (json.JSONDecodeError, TypeError):
            ev_list = []
        if not isinstance(ev_list, list) or len(ev_list) == 0:
            return 0.0  # HARD GATE: no evidence → score=0

    # GATE 2: wrong_route — pred says FB but gold says NULL (false positive)
    if pred_should and not gold_should:
        return 0.0  # HARD GATE: false positive → score=0

    # GATE 3: false_convergence — pred is_convergent but single-source evidence
    if pred_should:
        pred_is_conv = getattr(pred, "is_convergent", False)
        if pred_is_conv:
            try:
                ev_list_check = json.loads(pred_evidence) if isinstance(pred_evidence, str) else pred_evidence
            except (json.JSONDecodeError, TypeError):
                ev_list_check = []
            if isinstance(ev_list_check, list) and len(ev_list_check) < 2:
                return 0.0  # HARD GATE: false convergence → score=0

    # ═══════════════════════════════════════════════════════════════
    # All gates passed — compute weighted quality score
    # ═══════════════════════════════════════════════════════════════
    score = 0.0

    # ── Convergence detection (30%) ──
    if gold_should == pred_should:
        score += 0.30
        if not gold_should:
            # Both agree it should NOT be extracted — perfect negative
            return 1.0
    else:
        # FALSE NEGATIVE — pred says NULL but gold says FB
        return 0.0  # HARD GATE: false negative → score=0

    # ── Extraction type (P1: 20%) ──
    gold_type = gold.extraction_type
    pred_type = getattr(pred, "extraction_type", "causal_mechanism")
    if gold_type == pred_type:
        score += 0.20
    elif gold_type in EXTRACTION_TYPES and pred_type in EXTRACTION_TYPES:
        score += 0.05  # wrong type but valid

    # NOTE: Depth classification moved to Stage 4 (A-001/D2241).
    # The 15% depth weight is redistributed: type 15→20%, name 10→12%, mechanism 10→13%.

    # ── Name similarity (12%) ──
    gold_name = (gold.name or "").lower().strip()
    pred_name = getattr(pred, "name", "").lower().strip()
    if gold_name and pred_name:
        # Simple token overlap
        gold_tokens = set(gold_name.split())
        pred_tokens = set(pred_name.split())
        if gold_tokens and pred_tokens:
            overlap = len(gold_tokens & pred_tokens) / max(len(gold_tokens), len(pred_tokens))
            score += overlap * 0.12

    # ── Mechanism quality (13%) ──
    pred_mech = getattr(pred, "mechanism", "")
    if pred_mech and len(pred_mech.strip()) > 30:
        score += 0.13
    elif pred_mech and len(pred_mech.strip()) > 10:
        score += 0.06

    # ── Evidence passages (10%) ──
    pred_evidence = getattr(pred, "evidence_passages", "[]")
    try:
        ev_list = json.loads(pred_evidence) if isinstance(pred_evidence, str) else pred_evidence
        if isinstance(ev_list, list) and len(ev_list) >= 2:
            score += 0.10
        elif isinstance(ev_list, list) and len(ev_list) >= 1:
            score += 0.05
    except (json.JSONDecodeError, TypeError):
        pass

    # ── Boundary (5%) ──
    pred_boundary = getattr(pred, "boundary", "")
    if pred_boundary and len(pred_boundary.strip()) > 20:
        score += 0.05

    # ── Consequence (5%) ──
    pred_consequence = getattr(pred, "consequence", "")
    if pred_consequence and len(pred_consequence.strip()) > 20:
        score += 0.05

    # ── Route correctness (5%) ──
    if pred.route == gold.route:
        score += 0.05

    return min(1.0, score)


# ──────────────────────────────────────────────────────────────────────
# 5. Direct OMLX LM Backend (bypasses litellm)
# ──────────────────────────────────────────────────────────────────────
# dspy's built-in litellm integration has issues with custom OpenAI-
# compatible endpoints (MIPROv2 passes kwargs dict as model name).
# DirectOMLXLM makes raw HTTP calls to OMLX's /v1/chat/completions,
# bypassing litellm entirely. This works for ALL dspy optimizers.

class DirectOMLXLM(dspy.LM):
    """DSPy LM backend that calls OMLX directly, bypassing litellm.

    Avoids the litellm custom-endpoint bug where MIPROv2's instruction
    proposer passes the entire kwargs dict as the model parameter.
    """

    def __init__(
        self,
        model: str = DSPY_MODEL,
        api_base: str = f"http://localhost:{OMLX_PORT}/v1",
        api_key: str = "not-needed",
        temperature: float = DSPY_TEMPERATURE,
        max_tokens: int = DSPY_MAX_TOKENS,
        **kwargs,
    ):
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens, **kwargs)
        self.omlx_model = model
        self.omlx_url = f"{api_base}/chat/completions"
        self.omlx_key = api_key
        self.omlx_temperature = temperature
        self.omlx_max_tokens = max_tokens
        self.provider = "omlx"

    def __call__(self, prompt=None, messages=None, **kwargs):
        """Make direct HTTP POST to OMLX."""
        if messages:
            msgs = messages
        elif prompt:
            msgs = [{"role": "user", "content": prompt}]
        else:
            return [""]

        payload = {
            "model": self.omlx_model,
            "messages": msgs,
            "temperature": self.omlx_temperature,
            "max_tokens": self.omlx_max_tokens,
        }

        try:
            import requests
            resp = requests.post(
                self.omlx_url,
                json=payload,
                headers={"Authorization": f"Bearer {self.omlx_key}"},
                timeout=180,
            )
            resp.raise_for_status()
            return [resp.json()["choices"][0]["message"]["content"]]
        except Exception as e:
            print(f"[DirectOMLXLM] Error: {e}")
            return [""]


def configure_dspy(model: str = DSPY_MODEL, verbose: bool = True) -> dspy.LM:
    """Configure DSPy with DirectOMLXLM for all optimizers."""
    lm = DirectOMLXLM(model=model)
    dspy.configure(lm=lm)
    if verbose:
        print(f"DSPy configured: model={model}, backend=DirectOMLXLM (litellm bypassed)")
    return lm


def run_dspy_pilot(
    train_examples: list[dspy.Example],
    dev_examples: list[dspy.Example],
    model: str = DSPY_MODEL,
    verbose: bool = True,
) -> dspy.Module:
    """
    Run a DSPy pilot with MIPROv2 optimizer.

    Uses a small subset of examples to validate the pipeline before full training.
    """
    if verbose:
        print(f"\n{'='*60}")
        print(f"DSPy Pilot: {len(train_examples)} train, {len(dev_examples)} dev")
        print(f"{'='*60}")

    lm = configure_dspy(model=model, verbose=verbose)

    # Define the extraction program
    class ExtractFB(dspy.Module):
        def __init__(self):
            super().__init__()
            self.extract = dspy.ChainOfThought(ConvergentExtraction)

        def forward(self, cluster_segments: str):
            result = self.extract(cluster_segments=cluster_segments)
            return result

    program = ExtractFB()

    # D2239: MIPROv2 confirmed working with DirectOMLXLM.
    # The litellm bug only affects stock dspy.LM; DirectOMLXLM bypasses it.
    optimizer = dspy.MIPROv2(
        metric=extraction_metric,
        num_threads=1,  # Single thread for local MLX
        auto="light",   # 10 trials, light hyperparameter search
    )

    if verbose:
        print(f"Optimizer: MIPROv2 (auto=light, {len(train_examples)} train, {len(dev_examples)} val)")
        print("Starting optimization...")

    optimized = optimizer.compile(
        program,
        trainset=train_examples,
        valset=dev_examples,
        max_bootstrapped_demos=DSPY_MAX_BOOTSTRAPPED_DEMOS,  # T-007b/D2250: 2→4 (config-driven)
        max_labeled_demos=DSPY_MAX_LABELED_DEMOS,  # T-007b: D2248 showed 2 demos = design-only;
                                    # golden pool spans 38 domains — more demos → better coverage
        requires_permission_to_run=False,
    )

    # D2243: Persist the optimized program so it survives crashes/reboots.
    # Lost the first pilot to kernel panic + /tmp cleanup — never again.
    # D2304: config-driven path (C12) — was hardcoded /tmp/dspy_mipro_optimized.json.
    from pipeline.pipeline_paths import DSPY_PROGRAM_PATH
    save_path = DSPY_PROGRAM_PATH
    try:
        optimized.save(str(save_path))
        if verbose:
            print(f"💾 Optimized program saved: {save_path}")
    except Exception as e:
        if verbose:
            print(f"⚠️  Could not save optimized program: {e}")

    if verbose:
        print("✅ Pilot complete. Optimized program ready.")

    return optimized


def evaluate_on_test(
    program: dspy.Module,
    test_examples: list[dspy.Example],
    verbose: bool = True,
) -> dict[str, float]:
    """Evaluate optimized program on held-out test set."""
    evaluator = dspy.Evaluate(
        devset=test_examples,
        metric=extraction_metric,
        num_threads=4,
        display_progress=verbose,
    )

    results = evaluator(program)

    # dspy 3.x Evaluate() returns an EvaluationResult object (not float)
    if hasattr(results, "score"):
        results_score = float(results.score)
    elif isinstance(results, dict):
        results_score = float(results.get("score", 0.0))
    else:
        results_score = float(results) if results else 0.0

    if verbose:
        print("\n── Test Set Results ──")
        print(f"  Score: {results_score:.3f}")
        print(f"  Examples: {len(test_examples)}")

    # Per-type breakdown
    type_scores: dict[str, list[float]] = defaultdict(list)
    fp_count = 0
    fn_count = 0

    for ex in test_examples:
        try:
            pred = program(cluster_segments=ex.cluster_segments)
            score = extraction_metric(ex, pred)
            et = getattr(pred, "extraction_type", "unknown")
            type_scores[et].append(score)

            if ex.is_positive and pred.route != "FB":
                fn_count += 1
            if not ex.is_positive and pred.route == "FB":
                fp_count += 1
        except Exception as e:
            print(f"  ⚠️  Error evaluating {ex.golden_id}: {e}")

    if verbose:
        print("\n── Per-Type Scores ──")
        for t, scores in sorted(type_scores.items()):
            avg = sum(scores) / len(scores) if scores else 0
            print(f"  {t}: {avg:.3f} ({len(scores)} examples)")
        print("\n── Error Analysis ──")
        print(f"  False Positives: {fp_count}")
        print(f"  False Negatives: {fn_count}")

    return {
        "overall_score": results_score,
        "fp_count": fp_count,
        "fn_count": fn_count,
        "type_scores": {t: sum(s) / len(s) if s else 0.0 for t, s in type_scores.items()},
    }


# ──────────────────────────────────────────────────────────────────────
# 7. Main Entry Points
# ──────────────────────────────────────────────────────────────────────

def _split(examples: list[dspy.Example], strategy: str, verbose: bool):
    """D2304: dispatch split strategy — 'tier' (default, D2286) or 'random' (legacy)."""
    if strategy == "random":
        return stratified_random_split(examples, verbose=verbose)
    return tier_aware_split(examples, verbose=verbose)


def cmd_dry_run(verbose: bool = True, split: str = "tier") -> None:
    """Validate golden set conversion and split without training."""
    examples = golden_to_examples(verbose=verbose)
    # D2304: tier-aware split is the default (D2286). Random split leaks CHALLENGE→train.
    train, dev, test = _split(examples, split, verbose=verbose)

    # Print statistics
    print("\n── Golden Set Statistics ──")
    print(f"  Total dspy.Examples: {len(examples)}")
    pos = [e for e in examples if e.is_positive]
    neg = [e for e in examples if not e.is_positive]
    print(f"  Positives: {len(pos)} ({len(pos)/len(examples):.0%})")
    print(f"  Negatives: {len(neg)} ({len(neg)/len(examples):.0%})")

    # Author stats
    all_authors: set[str] = set()
    for ex in examples:
        all_authors.update(ex.authors)
    author_counts = defaultdict(int)
    for ex in examples:
        for a in ex.authors:
            author_counts[a] += 1
    over_3 = {a: c for a, c in author_counts.items() if c > 3}
    if over_3:
        print(f"  ⚠️  Authors over 3: {over_3}")
    else:
        print(f"  ✅ All {len(all_authors)} authors ≤3")

    # Type stats
    type_counts = defaultdict(int)
    for ex in pos:
        type_counts[ex.extraction_type] += 1
    print("\n── Extraction Types ──")
    for t in ["causal_mechanism", "empirical_pattern", "normative_heuristic", "descriptive_model"]:
        print(f"  {t}: {type_counts.get(t, 0)}")

    print(f"\n✅ Dry run complete. {len(examples)} examples ready for DSPy training.")
    print(f"   Train: {len(train)} | Dev: {len(dev)} | Test: {len(test)}")


def cmd_pilot(verbose: bool = True, split: str = "tier") -> None:
    """Run a 10-example pilot to validate the pipeline end-to-end."""
    examples = golden_to_examples(verbose=False)
    # D2304: tier-aware split (D2286). GOLD-A=train, GOLD-B=dev, CHALLENGE=test.
    train, dev, test = _split(examples, split, verbose=verbose)

    # Use small subset for pilot (BootstrapFewShot is expensive — ~12s/API call)
    # GOLD-B dev is small (3); pad pilot_dev from train if needed for a usable eval set.
    pilot_train = train[:3] if len(train) >= 3 else train
    pilot_dev = dev[:2] if len(dev) >= 2 else train[:2]

    program = run_dspy_pilot(pilot_train, pilot_dev, verbose=verbose)

    if test:
        evaluate_on_test(program, test[:4], verbose=verbose)


def cmd_full(verbose: bool = True, split: str = "tier") -> None:
    """Run full DSPy training on all examples."""
    examples = golden_to_examples(verbose=False)
    # D2304: tier-aware split (D2286). GOLD-A=train, GOLD-B=dev, CHALLENGE=test.
    train, dev, test = _split(examples, split, verbose=verbose)

    program = run_dspy_pilot(train, dev, verbose=verbose)

    if test:
        evaluate_on_test(program, test, verbose=verbose)


# ──────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="DSPy Fine-Tuning Harness for Maxwell OS S2 Extraction"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate conversion and split without training",
    )
    parser.add_argument(
        "--pilot",
        action="store_true",
        help="Run 10-example pilot training",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full training on all examples",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DSPY_MODEL,
        help=f"DSPy model to use (default: {DSPY_MODEL})",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="tier",
        choices=["tier", "random"],
        help="Split strategy: 'tier' (D2286 GOLD-A/B/CHALLENGE, default) or 'random' (legacy stratified)",
    )
    parser.add_argument(
        "--load",
        type=str,
        default=None,
        help="Load a previously serialized DSPy program and evaluate on the test split",
    )

    args = parser.parse_args()
    verbose = not args.quiet

    # D2304: --load evaluates a persisted program against the held-out tier.
    if args.load:
        program = load_optimized_program(args.load)
        if program is None:
            sys.exit(1)
        examples = golden_to_examples(verbose=False)
        _, _, test = _split(examples, args.split, verbose=verbose)
        evaluate_on_test(program, test, verbose=verbose)
    elif args.pilot:
        cmd_pilot(verbose=verbose, split=args.split)
    elif args.full:
        cmd_full(verbose=verbose, split=args.split)
    else:
        # Default: dry run (tier-aware split by default, D2304)
        cmd_dry_run(verbose=verbose, split=args.split)


if __name__ == "__main__":
    main()
