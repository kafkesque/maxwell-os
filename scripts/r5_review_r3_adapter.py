#!/usr/bin/env python3
"""R5 review of the R3 held-out ADAPTER before any measurement is taken (D2549 routing: gemma-4-E4B).

Why: the adapter decides WHICH rows, WHICH truth labels and WHICH menu the R3 number is computed
from, so an adapter defect can manufacture a passing R3. Generator (this session) != verifier (gemma).
The review is advisory evidence for the D-311 pre-registration; it does not replace the D-300 bar.

C12: model id, endpoint and paths come from config (pipeline.pipeline_paths + eval_integrity.yaml).
Nothing is hardcoded. temp 0.0 (R7), single-shot (DELEGATE-002).

Usage:  python3 scripts/r5_review_r3_adapter.py [--out governance/R5_REVIEW_R3_ADAPTER_20260921.md]
"""
from __future__ import annotations

import argparse
import json
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


def main() -> int:
    """Send the adapter to the R5 verifier model and write the verdict artifact."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="governance/R5_REVIEW_R3_ADAPTER_20260921.md")
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
    out = ROOT / args.out
    out.write_text("# R5 review - R3 held-out adapter (gemma-4-E4B, temp 0.0, "
                   + model + ")\n\n" + content + "\n", encoding="utf-8")
    print(content)
    print("\nwrote " + args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
