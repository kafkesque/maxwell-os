"""S2 contamination audit — visually examinable + persistent output.

Read-only diagnostic. Runs the PRODUCTION single-source path against a curated
passage set spanning all 5 content_type roles + the `empirical_pattern` boundary +
negative controls. For each passage it runs BOTH:

  1. BASELINE: `SINGLE_SOURCE_SYSTEM` with NO golden few-shot (old behavior)
  2. WIRED:    `SINGLE_SOURCE_SYSTEM` + the balanced single-source golden (BUG-152)

and reports role/form/route + a contamination verdict. Results are ALSO written to
a timestamped JSONL (machine-readable) and Markdown (human-readable) report under
`audit_output/`, so the operator can open and inspect the full segments, extracted
properties, and metadata per object type.

Usage:
    python3 tools/s2_contamination_audit.py
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from pipeline.stage2_extract import (
    SINGLE_SOURCE_SYSTEM,
    _normalize_role_fields,
    call_llm,
    format_golden_fewshot_single_source,
    load_golden_single_source,
    validate_fb_output,
)
from pipeline.pipeline_paths import (
    GEN_MODEL,
    S2_GOLDEN_SINGLE_SOURCE_MAX,
    S2_GOLDEN_SINGLE_SOURCE_NEGATIVE,
    S2_GOLDEN_SINGLE_SOURCE_PATH,
)
from pipeline.content_types import CONTENT_TYPES, EXTRACTION_TYPES

OUT_DIR = Path("audit_output")

# ── Curated passages: expected role + the contamination each is probing ────
SAMPLES: list[dict] = [
    {
        "label": "principle",
        "expect": "principle",
        "probe": "reusable concept — should be FB in BOTH prompts",
        "text": "Once a small habit is established, it compounds. Marginal gains of one "
        "percent per day accumulate into roughly thirty-seven times improvement over a "
        "year because each increment builds on the last rather than adding linearly.",
    },
    {
        "label": "process_template",
        "expect": "process_template",
        "probe": "repeatable human method — must emit PT, NOT principle",
        "text": "Pilots remember critical information using three techniques: first they "
        "write it down, second they enter it into their equipment as it is read so minimal "
        "memory is required, and third they remember selectively, holding only the few items "
        "needed in the next few minutes.",
    },
    {
        "label": "tool_instruction",
        "expect": "tool_instruction",
        "probe": "code/API — must emit TI, NOT PT (BUG-147)",
        "text": "Load a persisted index from disk with: index = faiss.read_index(\"data/my_index.index\"). "
        "This lets you reuse the index across sessions instead of rebuilding it from scratch each time.",
    },
    {
        "label": "process_instance",
        "expect": "process_instance",
        "probe": "case study — must emit PI",
        "text": "To prove the point the researchers ran the scam at a local cafe on the top "
        "floor of a mall on Oxford Street in London. Once out of sight the accomplice headed "
        "quickly for the parking garage; it did not take long for the mark to realize her bag "
        "was gone.",
    },
    {
        "label": "growth_edge",
        "expect": "growth_edge",
        "probe": "speculative 'what if' — must emit GE, NOT principle (BUG-147)",
        "text": "What if it were possible for autism—for mind-blindness—to be a temporary "
        "condition instead of a chronic one? Could that explain why otherwise normal people "
        "sometimes reach conclusions that are socially tone-deaf?",
    },
    {
        "label": "empirical_pattern_ambiguous",
        "expect": "growth_edge OR principle",
        "probe": "correlation w/o cause — THE ambiguity (form/role boundary)",
        "text": "Across firms, employee engagement scores and quarterly revenue are observed to "
        "rise and fall together year over year, though the passages do not establish which one "
        "drives the other.",
    },
    {
        "label": "tool_vs_template",
        "expect": "tool_instruction",
        "probe": "algorithm described as steps — BUG-147's 62% mislabel case",
        "text": "Depth-first search visits a graph by pushing the start node onto a stack, then "
        "repeatedly popping a node, marking it visited, and pushing each unvisited neighbor back "
        "onto the stack until the stack is empty.",
    },
    {
        "label": "NEGATIVE_CONTROL",
        "expect": "NULL",
        "probe": "pure factual description — must NULL (overfire check)",
        "text": "The 1950s saw the rise of modernist institutional advertising in the United "
        "States. The Container Corporation of America produced some of the most progressive "
        "institutional advertising of that era.",
    },
]


def _run(prompt: str, system: str, few_shot: str | None) -> dict | None:
    raw = call_llm(prompt, system, GEN_MODEL, "omlx", few_shot=few_shot)
    if not isinstance(raw, dict):
        return None
    result = _normalize_role_fields(dict(raw))
    is_valid, errors = validate_fb_output(result)
    result["_valid"] = is_valid
    result["_errors"] = errors
    return result


def _role(r: dict | None) -> str:
    if r is None:
        return "NONE"
    return str(r.get("content_type", "")).strip() or "NULL"


def _verdict(baseline: dict | None, wired: dict | None, expected: str) -> str:
    br, wr = _role(baseline), _role(wired)
    # Wired (golden) must produce the correct role or NULL.
    if expected == "NULL":
        if wr != "NULL":
            return "🟠 OVERFIRE — wired extracted a negative control instead of NULL"
        return "✅ OK (NULL)"
    # Wired must NOT NULL a genuine object of the expected role.
    if expected != "NULL" and wr == "NULL":
        return "🟠 MISS — wired NULL'd a genuine object"
    # Wired must match the expected role.
    if expected not in ("growth_edge OR principle",) and wr != expected:
        return f"🔴 WRONG ROLE — wired emitted '{wr}', expected '{expected}'"
    # Ambiguous case: either is acceptable, but note divergence.
    if expected == "growth_edge OR principle":
        return f"✅ OK (ambiguous — wired chose '{wr}')"
    # Compare against baseline to show whether the golden changed anything.
    if br != wr:
        return f"✅ FIXED — baseline '{br}' → wired '{wr}'"
    return f"✅ OK ({wr})"


def main() -> None:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    OUT_DIR.mkdir(exist_ok=True)
    jsonl_path = OUT_DIR / f"s2_contamination_audit_{ts}.jsonl"
    md_path = OUT_DIR / f"s2_contamination_audit_{ts}.md"

    ss_pos, ss_neg, _ = load_golden_single_source(
        S2_GOLDEN_SINGLE_SOURCE_PATH, S2_GOLDEN_SINGLE_SOURCE_NEGATIVE, S2_GOLDEN_SINGLE_SOURCE_MAX
    )
    ss_few_shot = format_golden_fewshot_single_source(ss_pos, ss_neg)

    print("=" * 88)
    print("S2 CONTAMINATION AUDIT — baseline (no golden) vs wired (single-source golden)")
    print(f"model={GEN_MODEL}  temp=0.0  provider=omlx")
    print(f"golden: {len(ss_pos)} pos roles + {len(ss_neg)} neg  ({len(ss_few_shot)} chars)")
    print("=" * 88)

    md_lines: list[str] = [
        "# S2 Contamination Audit",
        "",
        f"- model: `{GEN_MODEL}`",
        f"- temp: `0.0`, provider: `omlx`",
        f"- golden injected (wired): {len(ss_pos)} positives + {len(ss_neg)} negatives",
        f"- timestamp: `{ts}`",
        "",
        "Legend: 🔴=wrong role  🟠=overfire/miss  ✅=clean. "
        "`role` = content_type, `form` = extraction_type.",
        "",
        "---",
        "",
    ]

    records: list[dict] = []
    for s in SAMPLES:
        label, expect, probe, text = s["label"], s["expect"], s["probe"], s["text"]
        prompt = f"Text passage:\n{text[:2000]}\n\nSource: audit-{label}"

        baseline = _run(prompt, SINGLE_SOURCE_SYSTEM, None)
        wired = _run(prompt, SINGLE_SOURCE_SYSTEM, ss_few_shot)
        verdict = _verdict(baseline, wired, expect)

        records.append({
            "label": label,
            "expected_role": expect,
            "probe": probe,
            "input_text": text,
            "baseline": baseline,
            "wired": wired,
            "verdict": verdict,
        })

        print(f"\n{'─' * 88}")
        print(f"▶ {label.upper()}  (expected: {expect})")
        print(f"  probe: {probe}")
        print(f"  baseline: role={_role(baseline):<16} wired: role={_role(wired):<16}")
        print(f"  verdict: {verdict}")

        md_lines.append(f"## {label}  (expected `{expect}`)")
        md_lines.append("")
        md_lines.append(f"- probe: {probe}")
        md_lines.append(f"- **verdict: {verdict}**")
        md_lines.append("")
        md_lines.append("| | role (content_type) | form (extraction_type) | route | is_summary | valid |")
        md_lines.append("|---|---|---|---|---|---|")
        for tag, r in (("baseline", baseline), ("wired", wired)):
            if r is None:
                md_lines.append(f"| {tag} | NONE | — | — | — | — |")
                continue
            md_lines.append(
                f"| {tag} | {r.get('content_type','')} | {r.get('extraction_type','')} "
                f"| {r.get('route','')} | {r.get('is_summary','')} | {r.get('_valid','')} |"
            )
        md_lines.append("")
        md_lines.append(f"**input:** {text}")
        md_lines.append("")
        for tag, r in (("baseline", baseline), ("wired", wired)):
            if not r:
                continue
            md_lines.append(f"<details><summary>{tag} full record</summary>")
            md_lines.append("")
            md_lines.append("```json")
            md_lines.append(json.dumps(r, indent=2, ensure_ascii=False))
            md_lines.append("```")
            md_lines.append("</details>")
            md_lines.append("")

    with open(jsonl_path, "w") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    with open(md_path, "w") as f:
        f.write("\n".join(md_lines) + "\n")

    print(f"\n{'=' * 88}")
    print("Persistent outputs:")
    print(f"  JSONL: {jsonl_path}")
    print(f"  MD:    {md_path}")
    print("Legend: 🔴=contamination  🟠=overfire/miss  ✅=clean. "
          "Open the MD to inspect full segments/properties/metadata per type.")
    print("=" * 88)


if __name__ == "__main__":
    main()
