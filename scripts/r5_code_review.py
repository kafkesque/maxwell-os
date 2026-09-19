#!/usr/bin/env python3
"""R5 code review: a DIFFERENT model family reviews a new script before it is applied.

WHY: C8/R5 - the generator of a change must not be its verifier. A review is only evidence if it
records the reviewer model, the file digest, the verdict and the concerns, so it lands as an
artifact instead of being remembered as a conversation.

    python3 scripts/r5_code_review.py --file scripts/purge_stale_rows.py --reviewer gemma-4-E4B-it-MLX-4bit
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REPO: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

from model_eval_suite import call  # noqa: E402

SYSTEM: str = (
    "You review Python scripts for correctness and safety. "
    "Judge only what the source supports; if the question cannot be decided from the code "
    "alone, the verdict MUST be \"INSUFFICIENT\". "
    "Reply with JSON only: {\"verdict\": \"APPROVE\" or \"REJECT\" or \"INSUFFICIENT\", "
    "\"concerns\": [\"...\"], \"confidence\": 0.0-1.0}"
)


def extract_verdict(raw: str) -> dict:
    """Pull the first balanced JSON object out of a reviewer reply.

    A reviewer may wrap the verdict in a ```json fence, or answer INSUFFICIENT with a long concern
    list that a naive find('{')/rfind('}') slice mangles into an unparseable blob (observed
    2026-09-17). Scan by brace depth instead, and never invent a verdict.
    """
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1] if len(text.split("```")) > 1 else text
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    start = text.find("{")
    if start < 0:
        return {"verdict": "UNPARSED", "concerns": [], "raw_head": raw[:200], "raw_len": len(raw)}
    depth = 0
    in_str = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_str:
            if escape:
                escape = False
            elif char == chr(92):
                escape = True
            elif char == '"':
                in_str = False
            continue
        if char == '"':
            in_str = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    parsed = json.loads(text[start:index + 1])
                    parsed.setdefault("verdict", "UNPARSED")
                    return parsed
                except Exception:
                    break
    return {"verdict": "UNPARSED", "concerns": [], "raw_head": raw[:200], "raw_len": len(raw)}


def review(path: Path, reviewer: str, task: str, max_tokens: int, context: list) -> dict:
    """Send the script to a different-family reviewer and parse the verdict."""
    text = path.read_text(encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    prompt = (
        "Reviewer question: " + task + chr(10) + chr(10)
        + "Judge the code AS WRITTEN against the purpose stated in its own docstring:" + chr(10)
        + "is it CORRECT for that purpose, and SAFE to run (no data loss, no irreversibility," + chr(10)
        + "no silent failure, and does it verify its own work)?" + chr(10)
        + "If the reviewer question cannot be answered from the source alone, answer INSUFFICIENT."
        + chr(10) + chr(10) + "SCRIPT " + path.name + " (sha256 " + digest + "):" + chr(10)
        + text
        + ("".join(chr(10) + chr(10) + "CONTEXT FILE " + name + ":" + chr(10) + body
                   for name, body in context))
    )
    raw = call(reviewer, SYSTEM, prompt, max_tokens)
    verdict: dict = extract_verdict(raw)
    verdict["reviewer"] = reviewer
    verdict["file"] = str(path.relative_to(REPO))
    verdict["sha256_16"] = digest
    return verdict


def main() -> int:
    """Run one review and write the artifact. Returns 0 on APPROVE, 1 otherwise."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", required=True)
    ap.add_argument("--reviewer", default="gemma-4-E4B-it-MLX-4bit")
    ap.add_argument("--task", default="does this script do what its docstring says, safely (generic review)")
    ap.add_argument("--out", default="governance/r5_reviews.jsonl")
    ap.add_argument("--context-file", action="append", default=[],
                    help="file the reviewer needs to judge this script (repeatable); a config-driven "
                         "script cannot be judged from its source alone and the reviewer will say INSUFFICIENT")
    ap.add_argument("--max-tokens", type=int, default=1400,
                    help="reviewer output budget; too small truncates the verdict JSON (UNPARSED)")
    args = ap.parse_args()

    path = REPO / args.file
    context = []
    for rel in args.context_file:
        candidate = REPO / rel
        if candidate.exists():
            context.append((rel, candidate.read_text(encoding="utf-8")[:6000]))
    verdict = review(path, args.reviewer, args.task, args.max_tokens, context)
    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"generated": time.strftime("%Y-%m-%dT%H:%M:%S"), **verdict}) + chr(10))
    print("  reviewer   " + str(verdict["reviewer"]))
    print("  file       " + str(verdict["file"]) + "  sha256_16=" + str(verdict["sha256_16"]))
    print("  VERDICT    " + str(verdict.get("verdict")))
    for c in (verdict.get("concerns") or [])[:6]:
        print("     concern: " + str(c)[:150])
    print("  artifact   " + str(out.relative_to(REPO)) + " (append-only)")
    answer = str(verdict.get("verdict")).upper()
    if answer == "APPROVE":
        return 0
    if answer in ("INSUFFICIENT", "UNPARSED"):
        print("  NOTE: the reviewer did not approve or reject — do not read this as approval")
        return 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
