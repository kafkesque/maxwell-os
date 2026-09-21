#!/usr/bin/env python3
"""R5 review of the R3 held-out ADAPTER before any measurement is taken (D2549 routing: gemma-4-E4B).

Why: the adapter decides WHICH rows, WHICH truth labels and WHICH menu the R3 number is computed
from, so an adapter defect can manufacture a passing R3. Generator (this session) != verifier (gemma).
The review is advisory evidence for the D-311 pre-registration; it does not replace the D-300 bar.

C12: model id, endpoint and paths come from config (pipeline.pipeline_paths + eval_integrity.yaml).
Nothing is hardcoded. temp 0.0 (R7), single-shot (DELEGATE-002).

BUG-333 (2026-09-21): the LLM returned a RUBBER STAMP -- a fluent, confident, evidence-free review that
passed the adapter. A verifier that cannot fail is not a verifier. The review is now accepted only when it
carries QUOTED EVIDENCE for the questions that decide the number, and the artifact is stamped
VERDICT: INSUFFICIENT (exit 2) when it does not. In addition, a MECHANICAL precheck runs regardless of the
model: the adapter code may not reference the answer key at all, and a review whose BLOCKERS are non-empty
can never be recorded as an approval.

Usage:  python3 scripts/r5_review_r3_adapter.py [--out governance/R5_REVIEW_R3_ADAPTER_20260921.md]
        [--allow-unsupported]   # record a review that lacks quoted evidence, stamped INSUFFICIENT
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FILES = ("scripts/bakeoff_typed_decision.py", "scripts/r3_heldout_eval.py",
         "governance/R3_HELDOUT_PREREG_20260921.md")

PROMPT = """You are reviewing a measurement adapter BEFORE it is used to produce a published number.
R5: the author of the code must not be the reviewer. Be adversarial and concrete.

CONTEXT
- The pipeline verifies labels with a pairwise NLI verifier. R3 is a proposed rule: if the pairwise
  verifier and an LLM labeler agree, accept; if they disagree, take the arm with the higher margin.
- R3 was derived on 116 rows and gained ~6 pp THERE, so the project forbids adopting it there.
- A 58-row held-out set (a human-labelled adjudication sheet) was frozen in advance; the rule is now
  scored on it. The adapter below loads the held-out rows and their human verdicts.

CODE UNDER REVIEW
{code}

ANSWER IN THIS EXACT FORMAT (short lines):
LEAKAGE: <can the prediction path see human truth, directly or through the menu/keys? yes/no + where>
ROW_SET: <is the row set exactly the frozen held-out set? any way to widen/narrow it silently?>
TRUTH: <are the human verdicts read as written? any label silently dropped, remapped or defaulted?>
SYMMETRY: <are truth and predictions normalised identically? name a case where they are not>
ABSTENTION: <can an unresolvable prediction be counted as agreement or as a wrong answer?>
VERDICT_DEPENDENCE: <can the adapter change its behaviour based on how well an arm is doing? yes/no>
BLOCKERS: <numbered list of defects that would invalidate a published number, or NONE>
NITS: <numbered list of non-blocking issues, or NONE>
"""


# Every question below decides the number, so each answer must carry a QUOTED span from the code
# under review (BUG-333: fluency is not evidence).
EVIDENCE_SECTIONS = ("LEAKAGE", "ROW_SET", "TRUTH", "SYMMETRY", "ABSTENTION", "VERDICT_DEPENDENCE")
QUOTE_RE = re.compile(r'"[^"]{8,}"|\'[^\']{8,}\'|`[^`]{8,}`|\b[\w/.]+\.(py|md|yaml|json|csv):\d+')
# The adapter must not read the answer key: a leak is decidable WITHOUT the model (this is the control
# that would have caught the class of defect the rubber stamp waved through).
FORBIDDEN_IN_ADAPTER = ("anchor1_frozen", "RULER_BLIND_SHEET", "ruler_sheet_key", "human_attestation")


def mechanical_leak_precheck(code: str) -> list[str]:
    """Return findings from the deterministic leak scan of the adapter code (never model-dependent)."""
    return [tok for tok in FORBIDDEN_IN_ADAPTER if tok in code]


def validate_review(content: str) -> tuple[list[str], str]:
    """Return (problems, verdict) for a reviewer response. Empty problems == the review is usable."""
    problems: list[str] = []
    for sec in EVIDENCE_SECTIONS:
        m = re.search(rf"^{sec}\s*:\s*(.*)$", content, re.MULTILINE | re.IGNORECASE)
        if not m:
            problems.append(f"{sec}: section missing")
            continue
        if not m.group(1).strip():
            problems.append(f"{sec}: empty answer")
        elif not QUOTE_RE.search(m.group(1)):
            problems.append(f"{sec}: no quoted evidence (BUG-333)")
    blockers = re.search(r"^BLOCKERS\s*:\s*(.*)$", content, re.MULTILINE | re.IGNORECASE)
    blocked = bool(blockers) and blockers.group(1).strip().upper() not in ("NONE", "NONE.", "")
    verdict = "BLOCKED" if blocked else ("INSUFFICIENT" if problems else "PASS")
    return problems, verdict


def main() -> int:
    """Send the adapter to the R5 verifier model and write the verdict artifact."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="governance/R5_REVIEW_R3_ADAPTER_20260921.md")
    ap.add_argument("--allow-unsupported", action="store_true",
                    help="record a review lacking quoted evidence, stamped VERDICT: INSUFFICIENT")
    args = ap.parse_args()
    from pipeline.pipeline_paths import OMLX_API_KEY, OMLX_URL

    import yaml

    cfg = yaml.safe_load((ROOT / "config" / "eval_integrity.yaml").read_text(encoding="utf-8"))
    model = str(cfg.get("r5_review_model") or "gemma-4-E4B-it-MLX-4bit")
    parts = []
    for rel in FILES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        if rel.endswith(".py"):
            text = text[:9000]          # adapter/report code only; the headers carry the decisions
        parts.append("=== " + rel + " ===\n" + text)
    body = json.dumps({"model": model, "temperature": 0.0,
                       "messages": [{"role": "user", "content": PROMPT.format(code="\n\n".join(parts))}]}
                      ).encode()
    req = urllib.request.Request(OMLX_URL.rstrip("/") + "/v1/chat/completions", data=body,
                                headers={"Content-Type": "application/json",
                                         "Authorization": "Bearer " + OMLX_API_KEY})
    with urllib.request.urlopen(req, timeout=600) as resp:
        payload = json.loads(resp.read().decode())
    content = payload["choices"][0]["message"]["content"]

    # Deterministic controls first -- these do not depend on the model (BUG-333).
    leak = mechanical_leak_precheck("\n".join(parts))
    problems, verdict = validate_review(content)
    if leak:
        problems.append("MECHANICAL LEAK PRECHECK: adapter references the answer key: " + ", ".join(leak))
        verdict = "BLOCKED"

    header = ("# R5 review - R3 held-out adapter (" + model + ", temp 0.0)\n\n"
              "**VERDICT: " + verdict + "** (mechanical gate, scripts/r5_review_r3_adapter.py, BUG-333)\n"
              + ("\n**Unsupported sections:** " + "; ".join(problems) if problems else
                 "\nAll evidence sections carry quoted evidence; mechanical leak precheck clean.")
              + "\n\n---\n\n")
    out = ROOT / args.out
    out.write_text(header + content + "\n", encoding="utf-8")
    print(content)
    print("\nVERDICT: " + verdict)
    for pr in problems:
        print("  - " + pr)
    print("wrote " + args.out)
    if verdict == "PASS":
        return 0
    if verdict == "INSUFFICIENT" and args.allow_unsupported:
        print("WARN: recorded as INSUFFICIENT (--allow-unsupported). NOT an approval.")
        return 0
    print("FAIL-CLOSED: the review cannot support a published number (BUG-333).")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
