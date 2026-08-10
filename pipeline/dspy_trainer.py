#!/usr/bin/env python3
"""
DSPy Fine-Tuning Harness for Maxwell OS S2 Extraction Stage (T-007).

Trains the S2 extractor (Qwen3-Coder) to produce convergent Foundation Blocks
from multi-source book segment clusters using the v4.3 golden set (70 examples,
72 FBs).

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

DSPY_MODEL = _cfg.get("models", {}).get("generator", "lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-MLX-4bit")
DSPY_PROVIDER = _cfg.get("models", {}).get("generator_provider", "omlx")
DSPY_TEMPERATURE = 0.0
DSPY_MAX_TOKENS = _cfg.get("stage2", {}).get("max_tokens", 2048)
OMLX_PORT = int(_cfg.get("omlx", {}).get("port", 11435))
RANDOM_SEED = int(_cfg.get("pipeline", {}).get("random_seed", 42))

# Extraction types and depths for validation
EXTRACTION_TYPES = {"causal_mechanism", "empirical_pattern", "normative_heuristic", "descriptive_model"}
DEPTHS = {"universal", "cross-domain", "domain", "specialized"}


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
            consequence, extraction_type, depth, evidence_passages, route
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
    depth: str = dspy.OutputField(
        desc="universal | cross-domain | domain | specialized"
    )
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
                depth=fb.get("depth", "domain"),
                evidence_passages=evidence_json,
                route="FB" if should_extract and fb.get("route", "NULL") != "NULL" else "NULL",
            )

            # Attach metadata (not used by DSPy directly, but needed for split/metric)
            dspy_ex.golden_id = eid + (f"[{i}]" if len(fbs) > 1 else "")
            dspy_ex.authors = frozenset(authors)
            dspy_ex.is_positive = should_extract
            dspy_ex.fb_name = fb.get("name", "")

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
    At 72 examples with many multi-author pairings, clean author separation
    is mathematically infeasible.

    For the DSPy pilot, we accept some author leakage and rely on the diverse
    source material (40+ distinct authors across 70 examples) to provide
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


# ──────────────────────────────────────────────────────────────────────
# 4. Evaluation Metric
# ──────────────────────────────────────────────────────────────────────

def extraction_metric(
    gold: dspy.Example,
    pred: dspy.Example,
    trace: Any = None,
) -> float:
    """
    Score a prediction against the golden FB.

    Scoring dimensions (0.0–1.0):
    - convergence_correct: ±0.30  (heavily penalize FP/FN)
    - name_similarity: ±0.10
    - type_correct: ±0.15
    - depth_correct: ±0.10
    - mechanism_nonempty: ±0.10
    - evidence_present: ±0.10
    - boundary_present: ±0.05
    - consequence_present: ±0.05
    - route_correct: ±0.05

    Total: 1.0 for perfect match.

    False positives (pred says extract, gold says don't) are heavily penalized:
    max score for FP = 0.20 (only partial credit for correct rejection fields).
    """
    score = 0.0

    gold_should = gold.is_positive
    pred_should = pred.route == "FB" if hasattr(pred, "route") else bool(getattr(pred, "name", ""))

    # ── Convergence detection (P0: 30% weight) ──
    if gold_should == pred_should:
        score += 0.30
        if gold_should:
            # Both agree it should be extracted — evaluate quality
            pass
        else:
            # Both agree it should NOT be extracted — perfect for negative
            return 1.0
    else:
        if pred_should and not gold_should:
            # FALSE POSITIVE — maximum penalty, cap score
            return max(0.0, score - 0.20)
        else:
            # FALSE NEGATIVE — missed extraction
            return max(0.0, score + 0.10)  # partial credit for no hallucination

    # ── Extraction type (P1: 15%) ──
    gold_type = gold.extraction_type
    pred_type = getattr(pred, "extraction_type", "causal_mechanism")
    if gold_type == pred_type:
        score += 0.15
    elif gold_type in EXTRACTION_TYPES and pred_type in EXTRACTION_TYPES:
        score += 0.05  # wrong type but valid

    # ── Depth (P1: 10%) ──
    gold_depth = gold.depth
    pred_depth = getattr(pred, "depth", "domain")
    if gold_depth == pred_depth:
        score += 0.10
    elif gold_depth in DEPTHS and pred_depth in DEPTHS:
        # Partial credit for adjacent depths
        depth_order = ["specialized", "domain", "cross-domain", "universal"]
        try:
            g_idx = depth_order.index(gold_depth)
            p_idx = depth_order.index(pred_depth)
            if abs(g_idx - p_idx) == 1:
                score += 0.05
        except ValueError:
            pass

    # ── Name similarity (10%) ──
    gold_name = (gold.name or "").lower().strip()
    pred_name = getattr(pred, "name", "").lower().strip()
    if gold_name and pred_name:
        # Simple token overlap
        gold_tokens = set(gold_name.split())
        pred_tokens = set(pred_name.split())
        if gold_tokens and pred_tokens:
            overlap = len(gold_tokens & pred_tokens) / max(len(gold_tokens), len(pred_tokens))
            score += overlap * 0.10

    # ── Mechanism quality (10%) ──
    pred_mech = getattr(pred, "mechanism", "")
    if pred_mech and len(pred_mech.strip()) > 30:
        score += 0.10
    elif pred_mech and len(pred_mech.strip()) > 10:
        score += 0.05

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
# 5. OMLX LM Backend for DSPy
# ──────────────────────────────────────────────────────────────────────

class OMLXLM(dspy.LM):
    """DSPy LM backend for OMLX OpenAI-compatible API."""

    def __init__(
        self,
        model: str = DSPY_MODEL,
        base_url: str = f"http://localhost:{OMLX_PORT}/v1",
        temperature: float = DSPY_TEMPERATURE,
        max_tokens: int = DSPY_MAX_TOKENS,
    ):
        super().__init__(
            model=model,
            api_base=base_url,
            api_key="not-needed",  # OMLX doesn't require auth
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def __call__(self, prompt: str, **kwargs) -> list[str]:
        """Generate from OMLX. Returns list of completions."""
        import requests
        url = f"{self.api_base}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        payload.update(kwargs)
        try:
            resp = requests.post(url, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return [content]
        except Exception as e:
            print(f"[OMLXLM] Error: {e}")
            return [""]


# ──────────────────────────────────────────────────────────────────────
# 6. DSPy Pilot Training
# ──────────────────────────────────────────────────────────────────────

def configure_dspy(model: str = DSPY_MODEL, verbose: bool = True) -> dspy.LM:
    """Configure DSPy with OMLX backend."""
    lm = OMLXLM(model=model)
    dspy.configure(lm=lm)
    if verbose:
        print(f"DSPy configured: model={model}, provider=OMLX, port={OMLX_PORT}")
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

    # Configure optimizer
    optimizer = dspy.MIPROv2(
        metric=extraction_metric,
        num_threads=4,
        auto="light",  # Light hyperparameter search for pilot
    )

    if verbose:
        print(f"Optimizer: MIPROv2 (auto=light, {len(train_examples)} trainset)")
        print("Starting optimization...")

    optimized = optimizer.compile(
        program,
        trainset=train_examples,
        valset=dev_examples,
        max_bootstrapped_demos=2,
        max_labeled_demos=2,
        requires_permission_to_run=False,
    )

    if verbose:
        print(f"✅ Pilot complete. Optimized program ready.")

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

    if verbose:
        print(f"\n── Test Set Results ──")
        print(f"  Score: {results:.3f}")
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
        print(f"\n── Per-Type Scores ──")
        for t, scores in sorted(type_scores.items()):
            avg = sum(scores) / len(scores) if scores else 0
            print(f"  {t}: {avg:.3f} ({len(scores)} examples)")
        print(f"\n── Error Analysis ──")
        print(f"  False Positives: {fp_count}")
        print(f"  False Negatives: {fn_count}")

    return {
        "overall_score": float(results) if results else 0.0,
        "fp_count": fp_count,
        "fn_count": fn_count,
        "type_scores": {t: sum(s) / len(s) if s else 0.0 for t, s in type_scores.items()},
    }


# ──────────────────────────────────────────────────────────────────────
# 7. Main Entry Points
# ──────────────────────────────────────────────────────────────────────

def cmd_dry_run(verbose: bool = True) -> None:
    """Validate golden set conversion and split without training."""
    examples = golden_to_examples(verbose=verbose)
    train, dev, test = stratified_random_split(examples, verbose=verbose)

    # Print statistics
    print(f"\n── Golden Set Statistics ──")
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
    print(f"\n── Extraction Types ──")
    for t in ["causal_mechanism", "empirical_pattern", "normative_heuristic", "descriptive_model"]:
        print(f"  {t}: {type_counts.get(t, 0)}")

    # Depth stats
    depth_counts = defaultdict(int)
    for ex in pos:
        depth_counts[ex.depth] += 1
    print(f"\n── Depths ──")
    for d in ["universal", "cross-domain", "domain", "specialized"]:
        print(f"  {d}: {depth_counts.get(d, 0)}")

    print(f"\n✅ Dry run complete. {len(examples)} examples ready for DSPy training.")
    print(f"   Train: {len(train)} | Dev: {len(dev)} | Test: {len(test)}")


def cmd_pilot(verbose: bool = True) -> None:
    """Run a 10-example pilot to validate the pipeline end-to-end."""
    examples = golden_to_examples(verbose=False)
    train, dev, test = stratified_random_split(examples, verbose=verbose)

    # Use small subset for pilot
    pilot_train = train[:8] if len(train) >= 8 else train
    pilot_dev = dev[:4] if len(dev) >= 4 else dev

    program = run_dspy_pilot(pilot_train, pilot_dev, verbose=verbose)

    if test:
        evaluate_on_test(program, test[:4], verbose=verbose)


def cmd_full(verbose: bool = True) -> None:
    """Run full DSPy training on all examples."""
    examples = golden_to_examples(verbose=False)
    train, dev, test = stratified_random_split(examples, verbose=verbose)

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

    args = parser.parse_args()
    verbose = not args.quiet

    if args.pilot:
        cmd_pilot(verbose=verbose)
    elif args.full:
        cmd_full(verbose=verbose)
    else:
        # Default: dry run
        cmd_dry_run(verbose=verbose)


if __name__ == "__main__":
    main()
