#!/usr/bin/env python3
"""scripts/deepseek_frontier_audit.py — R5 cross-family frontier audit of the 69 frontier-Qwen3.8 objects.

DeepSeek-v4-pro (frontier, remote — C22 API opt-in, user-approved) acts as a
SECOND-OPINION verifier on the 69 golden objects that frontier Qwen3.8 already
labelled (depth / discipline / domains). It does TWO things per object:
  (1) VERIFY the existing depth/domain/discipline labels (agree/override + flag);
  (2) PROPOSE content_type (the unlabelled axis) + confidence + reason.

Output is a SIGNAL, not proof — humans remain the arbiter (per D2595 + the
D2585 forensic addendum: "frontier verdicts = prioritisation signals, not proof").

API key: passed via --key (or DEEPSEEK_API_KEY env). C1/C3 sovereignty note:
this is the explicit C22 opt-in path; do NOT run without user approval.

Usage:
    python3 scripts/deepseek_frontier_audit.py --key sk-... [--model deepseek-v4-pro] [--batch 20]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import urllib.request  # noqa: E402

OBJECTS = ROOT / "governance" / "frontier_qwen38_69_objects.json"
TAXONOMY = ROOT / "config" / "taxonomy_v5.yaml"
OUT_JSON = ROOT / "governance" / "deepseek_frontier69_audit.json"
OUT_MD = ROOT / "governance" / "deepseek_frontier69_audit.md"

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

# D2587 content_type rules + choices (self-contained for the model)
CONTENT_TYPE_RULES = """CONTENT-TYPE (5 roles + 2 dispositions):
- principle: general truth / reusable rule. A SINGLE transferable prescriptive claim (one-sentence heuristic acting as a filter across 3+ domains, OR a deep single-domain principle) is principle.
- process_template: step-by-step method — needs a SEQUENCE of >=2 steps AND a gate/done-condition. A single instruction is NOT a template.
- process_instance: a specific NAMED case / execution of a method (a study, project, product).
- growth_edge: open / unproven / speculative or a loose correlation (an articulated open tension, not a dump for failed depth-tests).
- tool_instruction: command / API / feature for a specific tool.
- noise_drop: just describes a fact / history / summary — no transferable value.
- quarantine: carries SOME value but no clean role — hold.
RULES: descriptive/historical summary -> noise_drop; named method-execution -> process_instance; reusable matrix/methodology with NO explicit steps -> principle (not process_template); ambiguous value -> quarantine."""

DEPTHS = ["universal", "cross-domain", "domain", "specialized"]


def load_taxonomy() -> dict[str, Any]:
    import yaml  # noqa: E402
    return yaml.safe_load(TAXONOMY.read_text(encoding="utf-8")) or {}


def _canonicals(entries: list[Any]) -> list[str]:
    out: list[str] = []
    for e in entries:
        if isinstance(e, dict):
            c = e.get("canonical")
            if c:
                out.append(str(c))
        elif isinstance(e, str):
            out.append(e)
    return out


def build_discipline_domain_lists(tax: dict[str, Any]) -> tuple[list[str], list[str]]:
    disc = _canonicals(tax.get("disciplines", []))
    doms = _canonicals(tax.get("domains", []))
    return disc, doms


def build_prompt(objects: list[dict[str, Any]], disc: list[str], doms: list[str]) -> str:
    lines = [
        "You are a senior RAG/ontology verifier. For EACH object below, return a JSON object.",
        "",
        CONTENT_TYPE_RULES,
        "",
        f"DEPTH values (pick one): {', '.join(DEPTHS)}",
        f"DISCIPLINE values (pick one from): {', '.join(disc[:80])}",
        f"DOMAIN values (multi-label, pick from): {', '.join(doms[:80])}",
        "",
        "For each object, return ONLY this JSON shape (no prose):",
        "{",
        '  "example_id": "...",',
        '  "depth_verdict": "agree|override", "depth": "...",',
        '  "discipline_verdict": "agree|override", "discipline": "...",',
        '  "domains_verdict": "agree|override", "domains": ["..."],',
        '  "content_type": "principle|process_template|process_instance|growth_edge|tool_instruction|noise_drop|quarantine",',
        '  "confidence": "high|medium|low",',
        '  "reason": "one sentence"',
        "}",
        "",
        "Return a JSON ARRAY of these objects. The existing labels are frontier-Qwen3.8 proposals —",
        "verify them independently; OVERRIDE if wrong. content_type is UNLABELLED — you must propose it.",
        "",
        "OBJECTS:",
    ]
    for o in objects:
        lines.append(json.dumps({
            "example_id": o["example_id"],
            "definition": o.get("definition", ""),
            "existing_depth": o.get("final_depth", ""),
            "existing_discipline": o.get("final_discipline", ""),
            "existing_domains": o.get("final_domains", []),
        }, ensure_ascii=False))
    lines.append("")
    lines.append("Return ONLY the JSON array, nothing else.")
    return "\n".join(lines)


def call_deepseek(prompt: str, key: str, model: str) -> list[dict[str, Any]]:
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a precise JSON-only verifier. Return only valid JSON arrays."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    import ssl  # noqa: E402
    import certifi  # noqa: E402
    ctx = ssl.create_default_context(cafile=certifi.where())
    req = urllib.request.Request(
        DEEPSEEK_URL, data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=300, context=ctx) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    content = data["choices"][0]["message"]["content"]
    # DeepSeek may wrap in {"objects": [...]} given response_format json_object
    parsed = json.loads(content)
    if isinstance(parsed, dict):
        for v in parsed.values():
            if isinstance(v, list):
                return v
    return parsed if isinstance(parsed, list) else []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=os.environ.get("DEEPSEEK_API_KEY", ""))
    ap.add_argument("--model", default="deepseek-v4-pro")
    ap.add_argument("--batch", type=int, default=20)
    args = ap.parse_args()
    if not args.key:
        print("ERROR: no API key. Pass --key or set DEEPSEEK_API_KEY.", file=sys.stderr)
        return 2

    objs = json.loads(OBJECTS.read_text(encoding="utf-8"))
    tax = load_taxonomy()
    disc, doms = build_discipline_domain_lists(tax)
    print(f"loaded {len(objs)} objects | {len(disc)} disciplines | {len(doms)} domains", file=sys.stderr)

    verdicts: dict[str, dict[str, Any]] = {}
    for i in range(0, len(objs), args.batch):
        chunk = [{"example_id": k, **v} for k, v in objs.items()][i:i + args.batch]
        prompt = build_prompt(chunk, disc, doms)
        try:
            res = call_deepseek(prompt, args.key, args.model)
        except Exception as e:  # noqa: BLE001
            print(f"batch {i}-{i+args.batch} FAILED: {e}", file=sys.stderr)
            continue
        for r in res:
            if isinstance(r, dict) and r.get("example_id"):
                verdicts[r["example_id"]] = r
        print(f"batch {i}-{i+args.batch}: got {len(res)} verdicts", file=sys.stderr)

    OUT_JSON.write_text(json.dumps(verdicts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Markdown summary
    md = [
        "# DeepSeek Frontier Audit — 69 Frontier-Qwen3.8 Objects",
        "",
        f"**Model:** {args.model} (frontier, C22 opt-in)  |  **Objects:** {len(verdicts)}/{len(objs)}",
        "",
        "| example_id | depth | discipline | domains | content_type | confidence |",
        "|---|---|---|---|---|---|",
    ]
    for eid in sorted(verdicts):
        v = verdicts[eid]
        d = f"{v.get('depth_verdict','?')}:{v.get('depth','?')}"
        di = f"{v.get('discipline_verdict','?')}:{v.get('discipline','?')}"
        do = f"{v.get('domains_verdict','?')}:{','.join(v.get('domains',[]))}"
        md.append(f"| {eid} | {d} | {di} | {do} | `{v.get('content_type','?')}` | {v.get('confidence','?')} |")
    md.append("")
    md.append("> SIGNAL NOT PROOF — human remains arbiter (D2595).")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    print(f"wrote {OUT_JSON.name} + {OUT_MD.name} ({len(verdicts)} verdicts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
