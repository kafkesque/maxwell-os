"""Visual smoke test for D2417 (BUG-145/BUG-146) single-source extraction.

Runs the FIXED single-source prompt + normalization + content_type-aware gate
against one representative passage per content_type, and prints the result in
an examineable form so the operator can verify the two-axis separation before
committing to a full single-source rerun.

Usage:
    python3 tools/s2_d2417_visual_test.py

No pipeline state is written — this is a read-only diagnostic.
"""

from __future__ import annotations

import json

from pipeline.stage2_extract import (
    SINGLE_SOURCE_SYSTEM,
    _normalize_role_fields,
    call_llm,
)
from pipeline.pipeline_paths import GEN_MODEL
from pipeline.content_types import CONTENT_TYPES, EXTRACTION_TYPES

# One representative verbatim passage per content_type (extracted from the t11
# corpus; these were observed as gated/failed in the real run).
SAMPLES: list[dict] = [
    {
        "label": "principle",
        "expect": "a reusable concept (why/when something works)",
        "text": "Once this kind of thinking takes over, it's easy to let good habits fall "
        "by the wayside. But in order to make a meaningful difference, habits need to "
        "persist long enough to break through this plateau—what I call the Plateau of "
        "Latent Potential. Change can take years—before it happens all at once.",
    },
    {
        "label": "process_template",
        "expect": "a repeatable how-to method with steps",
        "text": "How do pilots remember? Pilots use three major techniques: 1. They write "
        "down the critical information. 2. They enter it into their equipment as it is "
        "told to them, so minimal memory is required. 3. They remember selectively, "
        "holding only the few items they will need in the next few minutes.",
    },
    {
        "label": "process_instance",
        "expect": "a concrete case study of a method actually executed",
        "text": "To prove our point we set up the scam at a local cafe. The cafe was on "
        "the top floor of a mall on Oxford Street in London. Once out of sight, Alex "
        "headed quickly for the parking garage. It didn't take long for her to realize "
        "her bag was gone. Instantly, she began to panic.",
    },
    {
        "label": "growth_edge",
        "expect": "a speculative/unresolved insight (open question)",
        "text": "What if it were possible for autism—for mind-blindness—to be a temporary "
        "condition instead of a chronic one? Could that explain why sometimes otherwise "
        "normal people come to conclusions that are socially tone-deaf?",
    },
    {
        "label": "tool_instruction",
        "expect": "a tool/software-specific command",
        "text": "Load the index from a file: index = faiss.read_index(\"data/my_index_file.index\"). "
        "This way, you can persist your index across different sessions instead of "
        "rebuilding it from scratch every time.",
    },
    {
        "label": "NEGATIVE_CONTROL",
        "expect": "a pure factual description → should be NULL/gated",
        "text": "The 1950s saw the rise of modernist institutional advertising in the "
        "United States. The Container Corporation of America produced some of the most "
        "progressive institutional advertising of that era.",
    },
]


def main() -> None:
    non_principle = CONTENT_TYPES - {"principle"}
    print("=" * 78)
    print("D2417 SINGLE-SOURCE VISUAL TEST — fixed prompt + normalization + gate")
    print(f"model={GEN_MODEL}  temp=0.0")
    print("=" * 78)

    for s in SAMPLES:
        label = s["label"]
        print(f"\n{'─' * 78}")
        print(f"▶ {label.upper()}  (expected: {s['expect']})")
        print(f"{'─' * 78}")
        print(f"INPUT: {s['text'][:160]}...")

        prompt = f"Text passage:\n{s['text'][:2000]}\n\nSource: visual-test-{label}"
        raw = call_llm(prompt, SINGLE_SOURCE_SYSTEM, GEN_MODEL, "omlx")

        if raw is None:
            print("  ❌ LLM returned None")
            continue

        # Normalize + gate decision, mirroring the fixed pipeline path.
        result = dict(raw) if isinstance(raw, dict) else raw
        if isinstance(result, dict):
            result = _normalize_role_fields(result)
            route = str(result.get("route", "FB")).strip().upper()
            is_summary = bool(result.get("is_summary", False))
            content_type = str(result.get("content_type", "principle")).strip()
            gated = is_summary and content_type not in non_principle

            print(f"  name            : {result.get('name', '')}")
            print(f"  definition      : {result.get('definition', '')[:200]}")
            print(f"  mechanism       : {result.get('mechanism', '')[:140]}")
            print(f"  route           : {route}")
            print(f"  is_summary      : {is_summary}")
            print(f"  extraction_type : {result.get('extraction_type', '')}  "
                  f"(valid={result.get('extraction_type','') in EXTRACTION_TYPES})")
            print(f"  content_type    : {content_type}  "
                  f"(valid={content_type in CONTENT_TYPES})")
            if gated:
                print(f"  → GATED (summary, principle role)")
            elif route == "NULL":
                print(f"  → NULL (no extractable object)")
            else:
                print(f"  → FORWARDED to S4 as {content_type}")
        else:
            print(f"  RAW: {json.dumps(raw, ensure_ascii=False)[:300]}")

    print(f"\n{'=' * 78}")
    print("Done. Examine extraction_type (epistemic form) vs content_type (role).")
    print("=" * 78)


if __name__ == "__main__":
    main()
