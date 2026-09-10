#!/usr/bin/env python3
"""scripts/deepseek_p5_review.py — DeepSeek-v4-pro discipline/domain adjudication of the 69-FB P5 queue.

The local-LLM challenger vote splits (Qwen3.8-27B / gemma-4-E4B / Phi-4-mini)
CONFLATE domain and discipline labels (e.g. proposing "urban planning" — a DOMAIN
— as a discipline), which discredits their recommendations. This script replaces
that signal with an independent DeepSeek-v4-pro (frontier, C22 opt-in) adjudication
that STRICTLY separates:

  DISCIPLINE = academic field of study (EXACTLY ONE from the closed 61-list)
  DOMAIN     = application area / industry / context (multi-label, closed 43-list)

It also POST-VALIDATES DeepSeek's output against the closed sets and flags any
cross-contamination (a domain emitted as a discipline or vice-versa) fail-closed.

Output is a SIGNAL, not proof — the human remains arbiter (D2595).

Usage:
    python3 scripts/deepseek_p5_review.py --key sk-... [--model deepseek-v4-pro] [--batch 20]
"""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.request
from pathlib import Path
from typing import Any

import certifi
import yaml

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "governance" / "p5_freeze_plan.json"
TAXONOMY = ROOT / "config" / "taxonomy_v5.yaml"
OUT_JSON = ROOT / "governance" / "p5_deepseek_review.json"
OUT_MD = ROOT / "governance" / "p5_deepseek_review.md"

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


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


def load_taxonomy() -> tuple[list[str], list[str]]:
    tax = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8")) or {}
    return _canonicals(tax.get("disciplines", [])), _canonicals(tax.get("domains", []))


def build_prompt(objects: list[dict[str, Any]], disc: list[str], doms: list[str]) -> str:
    lines = [
        "You are a senior ontology/knowledge-graph labeler. Assign each object a canonical "
        "DISCIPLINE and DOMAINS with STRICT separation.",
        "",
        "DEFINITIONS (critical — do NOT conflate the two axes):",
        "- DISCIPLINE = the academic field of study / theoretical lens (e.g. cognitive science, "
        "urban design, physics, semiotics). Pick EXACTLY ONE from the DISCIPLINE list.",
        "- DOMAIN = the application area / industry / real-world context (e.g. urban planning, "
        "education, healthcare, graphic design). Pick ZERO OR MORE from the DOMAIN list.",
        "- A domain name (urban planning, education, graphic design, brand identity, …) is NEVER a "
        "discipline. A discipline name (cognitive science, semiotics, economics, …) is NEVER a domain.",
        "",
        f"DISCIPLINE list ({len(disc)}): {', '.join(disc)}",
        "",
        f"DOMAIN list ({len(doms)}): {', '.join(doms)}",
        "",
        "For EACH object return EXACTLY this JSON shape:",
        "{",
        '  "example_id": "...",',
        '  "discipline": "one from DISCIPLINE list",',
        '  "domains": ["zero or more from DOMAIN list"],',
        '  "confidence": "high|medium|low",',
        '  "reason": "one sentence"',
        "}",
        "",
        "The object's current silver labels are shown but may be WRONG (a prior weak model conflated "
        "the axes) — determine the correct labels from the definition/mechanism, not the current labels.",
        "",
        "OBJECTS:",
    ]
    for o in objects:
        lines.append(json.dumps({
            "example_id": o["example_id"],
            "name": o.get("name", ""),
            "definition": o.get("definition", ""),
            "mechanism": (o.get("mechanism") or "")[:500],
            "current_discipline": o.get("current_discipline", ""),
            "current_domains": o.get("current_domains", []),
        }, ensure_ascii=False))
    lines.append("")
    lines.append("Return ONLY a JSON array of these objects, nothing else.")
    return "\n".join(lines)


def call_deepseek(prompt: str, key: str, model: str) -> list[dict[str, Any]]:
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a precise JSON-only ontology labeler. Return only valid JSON arrays."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    ctx = ssl.create_default_context(cafile=certifi.where())
    req = urllib.request.Request(
        DEEPSEEK_URL, data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=300, context=ctx) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    content = data["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    if isinstance(parsed, dict):
        for v in parsed.values():
            if isinstance(v, list):
                return v
    return parsed if isinstance(parsed, list) else []


def validate(verdict: dict[str, Any], disc: set[str], doms: set[str]) -> list[str]:
    """Return contamination flags: domain-as-discipline / discipline-as-domain / non-canonical."""
    flags: list[str] = []
    d = verdict.get("discipline", "")
    if d and d not in disc:
        if d in doms:
            flags.append(f"domain '{d}' emitted as discipline")
        else:
            flags.append(f"non-canonical discipline '{d}'")
    for dom in verdict.get("domains", []):
        if dom not in doms:
            if dom in disc:
                flags.append(f"discipline '{dom}' emitted as domain")
            else:
                flags.append(f"non-canonical domain '{dom}'")
    return flags


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=os.environ.get("DEEPSEEK_API_KEY", ""))
    ap.add_argument("--model", default="deepseek-v4-pro")
    ap.add_argument("--batch", type=int, default=15)
    args = ap.parse_args()
    if not args.key:
        print("ERROR: no API key. Pass --key or set DEEPSEEK_API_KEY.", file=sys.stderr)
        return 2

    queue = json.loads(QUEUE.read_text(encoding="utf-8"))["review_queue"]
    disc, doms = load_taxonomy()
    disc_set, doms_set = set(disc), set(doms)
    print(f"loaded {len(queue)} FBs | {len(disc)} disciplines | {len(doms)} domains", file=sys.stderr)

    verdicts: dict[str, dict[str, Any]] = {}
    for i in range(0, len(queue), args.batch):
        chunk = queue[i:i + args.batch]
        prompt = build_prompt(chunk, disc, doms)
        try:
            res = call_deepseek(prompt, args.key, args.model)
        except Exception as e:  # noqa: BLE001
            print(f"batch {i}-{i+len(chunk)} FAILED: {e}", file=sys.stderr)
            continue
        for r in res:
            if isinstance(r, dict) and r.get("example_id"):
                r["contamination"] = validate(r, disc_set, doms_set)
                verdicts[r["example_id"]] = r
        print(f"batch {i}-{i+len(chunk)}: got {len(res)} verdicts", file=sys.stderr)

    OUT_JSON.write_text(json.dumps(verdicts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    contaminated = [eid for eid, v in verdicts.items() if v.get("contamination")]
    md = [
        "# DeepSeek-v4-pro P5 Review — discipline/domain adjudication (69 FBs)",
        "",
        f"**Model:** {args.model} (frontier, C22 opt-in)  |  **Adjudicated:** {len(verdicts)}/{len(queue)}",
        "",
        "Replaces the local-LLM vote splits that conflated domain/discipline. "
        "Strict separation: discipline = field of study (61-list), domain = application area (43-list).",
        "",
        f"**Contamination flags:** {len(contaminated)} (fail-closed — review these first)",
        "",
        "| example_id | discipline | domains | confidence | reason |",
        "|---|---|---|---|---|",
    ]
    for eid in sorted(verdicts):
        v = verdicts[eid]
        mark = " ⚠️" if v.get("contamination") else ""
        md.append(
            f"| {eid}{mark} | `{v.get('discipline','?')}` | "
            f"{', '.join(v.get('domains',[])) or '(none)'} | {v.get('confidence','?')} | {v.get('reason','')} |"
        )
    md.append("")
    md.append("> SIGNAL NOT PROOF — human remains arbiter (D2595). Contamination flags must be re-adjudicated.")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    print(f"wrote {OUT_JSON.name} + {OUT_MD.name} ({len(verdicts)} verdicts, {len(contaminated)} contaminated)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
