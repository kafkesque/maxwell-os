#!/usr/bin/env python3
"""Mine universal/specialized depth examples from the stage1_chunk corpus (D2378).

C12 config-first: seeds + noise patterns come from
config/golden/depth_mining_seeds.yaml; corpus path from pipeline_paths
(STAGE1_CHECKPOINT). Streaming, memory-bounded (one JSONL line at a time).

Two modes:
  --discover   Extract clean verbatim passages per seed (>= min_books distinct
               books). Writes config/golden/_depth_mined_candidates.json.
  --generate   For candidates in the discover output, generate FB drafts via a
               local model (call_omlx_json). Writes
               config/golden/_depth_mined_drafts.json.

Never auto-commits to the golden set — human review is required (C8-G2).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SEEDS_PATH = PROJECT_ROOT / "config" / "golden" / "depth_mining_seeds.yaml"
CANDIDATES_PATH = PROJECT_ROOT / "config" / "golden" / "_depth_mined_candidates.json"
DRAFTS_PATH = PROJECT_ROOT / "config" / "golden" / "_depth_mined_drafts.json"


def load_seeds() -> dict:
    import yaml
    with open(SEEDS_PATH) as f:
        return yaml.safe_load(f)


def _noise_re(patterns: list[str]) -> re.Pattern:
    return re.compile("|".join(re.escape(p) for p in patterns), re.IGNORECASE)


def _is_clean(text: str, noise_re: re.Pattern) -> bool:
    if noise_re.search(text):
        return False
    # Too short = no substance; too long = likely a table/code dump.
    if len(text) < 180 or len(text) > 650:
        return False
    return True


# Definitional cue words that signal a passage is *about* a concept, not merely
# mentioning it in passing (D2378). Combined with term-position to rank passages.
_DEF_CUES = re.compile(
    r"\b(is|are|means|refers to|defined|occurs when|happens when|happens because|"
    r"describes|the (law|concept|principle|phenomenon) of|in general|across all)\b",
    re.IGNORECASE,
)


def _score_passage(text: str, term_lower: str) -> float:
    """Rank a passage by how much it is *about* the term (higher = more on-topic)."""
    tlow = text.lower()
    idx = tlow.find(term_lower)
    # +1.0 for the term appearing early (topic-sentence region)
    early = 1.0 if 0 <= idx < len(tlow) * 0.4 else 0.0
    # +1.0 for a definitional cue
    cue = 1.0 if _DEF_CUES.search(text) else 0.0
    # +0.5 for term appearing 2+ times (sustained discussion)
    multi = 0.5 if tlow.count(term_lower) >= 2 else 0.0
    return early + cue + multi


def discover(seeds: dict, corpus_path: Path) -> dict:
    """Stream corpus, find seed terms across distinct books, extract clean passages."""
    noise_re = _noise_re(seeds.get("noise_patterns", []))
    # term -> depth -> list of (book, text)
    hits: dict[str, dict[str, list[tuple[str, str]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    term_index: dict[str, tuple[str, str]] = {}  # term -> (name, depth)

    for depth_key in ("universal", "specialized"):
        for seed in seeds.get(depth_key, []):
            for term in seed["terms"]:
                term_index[term.lower()] = (seed["name"], depth_key)

    with open(corpus_path) as f:
        for line in f:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = d.get("text", "")
            book = d.get("source_book", "")
            if not book or not _is_clean(text, noise_re):
                continue
            tlow = text.lower()
            for term, (name, depth) in term_index.items():
                if term in tlow:
                    hits[name][depth].append((book, text, term))
                    break  # one term match per segment

    candidates: dict[str, dict] = {}
    for name, by_depth in hits.items():
        for depth, trips in by_depth.items():
            # dedupe passages by book, keep the HIGHEST-scoring clean one
            best: dict[str, tuple[float, str]] = {}
            for book, text, term in trips:
                score = _score_passage(text, term)
                if book not in best or score > best[book][0]:
                    best[book] = (score, text)
            if len(best) >= 2:
                candidates[name] = {
                    "depth": depth,
                    "books": len(best),
                    "passages": [
                        {"book": b, "text": t}
                        for b, (_, t) in sorted(best.items(), key=lambda kv: -kv[1][0])
                    ],
                }
    return candidates


def _gen_prompt(depth: str, passages: list[dict]) -> str:
    lines = []
    for i, p in enumerate(passages, 1):
        lines.append(f"[{i}] ({p['book']}): {p['text']}")
    return (
        "You are generating a golden few-shot example for a convergent-principle "
        "extraction pipeline. The passages below are verbatim quotes from DIFFERENT "
        "books that converge on the SAME principle. They are the ONLY ground truth — "
        "do NOT introduce facts, mechanisms, boundaries, or consequences that are not "
        f"stated or directly implied by the passages.\n\n"
        f"TARGET DEPTH: {depth}\n"
        f"(universal = a law of nature/mathematics applying everywhere, e.g. entropy, power laws; "
        f"specialized = a narrow sub-technique requiring field-specific expertise, e.g. optical kerning)\n\n"
        "PASSAGES:\n" + "\n\n".join(lines) + "\n\n"
        'Return ONLY a JSON object with keys: name, definition, mechanism, boundary, '
        'consequence, extraction_type, depth. '
        'extraction_type is one of causal_mechanism|empirical_pattern|normative_heuristic|descriptive_model — '
        'choose HONESTLY (causal_mechanism only if a cause→effect chain is demonstrated). '
        'If the passages do NOT genuinely support the target depth, set depth to the honest value instead. '
        'mechanism may state "This is an empirical/descriptive pattern, not a causal mechanism" when no causal chain is shown.'
    )


def generate(candidates: dict, model: str) -> dict:
    from pipeline.omlx_call import call_omlx_json
    drafts: dict = {}
    for name, c in candidates.items():
        depth = c["depth"]
        passages = c["passages"][:3]  # at most 3 books
        try:
            out = call_omlx_json(
                prompt=_gen_prompt(depth, passages),
                model=model,
                system="You are a precise JSON generator. Return ONLY valid JSON.",
                max_tokens=1200,
            )
            drafts[name] = {
                "depth_target": depth,
                "passages": passages,
                "draft": out,
            }
            print(f"  ✓ {name}: depth={out.get('depth')} type={out.get('extraction_type')}")
        except Exception as e:
            drafts[name] = {"depth_target": depth, "passages": passages, "error": f"{type(e).__name__}: {e}"}
            print(f"  ✗ {name}: {e}")
    return drafts


def main() -> int:
    import yaml
    from pipeline.pipeline_paths import STAGE1_CHECKPOINT

    parser = argparse.ArgumentParser(description="Mine depth golden examples (D2378)")
    parser.add_argument("--discover", action="store_true", help="Extract candidate passages")
    parser.add_argument("--generate", action="store_true", help="Generate FB drafts from candidates")
    parser.add_argument("--model", default="gemma-4-E4B-it-MLX-4bit", help="Local model for --generate")
    args = parser.parse_args()

    seeds = load_seeds()

    if args.discover:
        candidates = discover(seeds, STAGE1_CHECKPOINT)
        CANDIDATES_PATH.write_text(json.dumps(candidates, indent=2, ensure_ascii=False))
        print(f"✅ {len(candidates)} candidates -> {CANDIDATES_PATH.name}")
        for name, c in candidates.items():
            print(f"  {name}: depth={c['depth']} books={c['books']}")
        return 0

    if args.generate:
        candidates = json.loads(CANDIDATES_PATH.read_text())
        drafts = generate(candidates, args.model)
        DRAFTS_PATH.write_text(json.dumps(drafts, indent=2, ensure_ascii=False))
        print(f"✅ {len(drafts)} drafts -> {DRAFTS_PATH.name}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
