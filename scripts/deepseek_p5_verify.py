#!/usr/bin/env python3
"""scripts/deepseek_p5_verify.py — independent R5 cross-verification of the DeepSeek-v4-pro P5 claims.

Generator != verifier (R5): DeepSeek-v4-pro PROPOSED discipline/domains for the
69-FB P5 queue; this script uses DeepSeek-v4-flash (a DIFFERENT model) to VERIFY
each claim against the object's definition, returning agree/override + a corrected
label where it disagrees. Disagreements = the claims a human should scrutinize first.

C22 opt-in (frontier API). Output is a signal, not proof.

Usage:
    python3 scripts/deepseek_p5_verify.py --key sk-... [--batch 20]
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
PROPOSAL = ROOT / "governance" / "p5_deepseek_review.json"
TAXONOMY = ROOT / "config" / "taxonomy_v5.yaml"
OUT_JSON = ROOT / "governance" / "p5_deepseek_verify.json"
OUT_MD = ROOT / "governance" / "p5_deepseek_verify.md"

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
        "You are a senior ontology verifier. For EACH object, you are given its definition and a "
        "PROPOSED discipline + domains. VERIFY the proposal independently; OVERRIDE where it is wrong.",
        "",
        "DISCIPLINE = academic field of study / theoretical lens (pick EXACTLY ONE). "
        "DOMAIN = application area / industry / context (zero or more). Do NOT conflate the two axes.",
        "",
        f"DISCIPLINE list ({len(disc)}): {', '.join(disc)}",
        "",
        f"DOMAIN list ({len(doms)}): {', '.join(doms)}",
        "",
        "For EACH object return EXACTLY this JSON shape:",
        "{",
        '  "example_id": "...",',
        '  "discipline_verdict": "agree|override", "discipline": "one from DISCIPLINE list",',
        '  "domains_verdict": "agree|override", "domains": ["zero or more from DOMAIN list"],',
        '  "confidence": "high|medium|low",',
        '  "reason": "one sentence (why agree, or why override)"',
        "}",
        "",
        "OBJECTS:",
    ]
    for o in objects:
        lines.append(json.dumps({
            "example_id": o["example_id"],
            "definition": o.get("definition", ""),
            "mechanism": (o.get("mechanism") or "")[:400],
            "proposed_discipline": o.get("discipline", ""),
            "proposed_domains": o.get("domains", []),
        }, ensure_ascii=False))
    lines.append("")
    lines.append("Return ONLY a JSON array, nothing else.")
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=os.environ.get("DEEPSEEK_API_KEY", ""))
    ap.add_argument("--model", default="deepseek-v4-flash")
    ap.add_argument("--batch", type=int, default=20)
    args = ap.parse_args()
    if not args.key:
        print("ERROR: no API key.", file=sys.stderr)
        return 2

    queue = json.loads(QUEUE.read_text(encoding="utf-8"))["review_queue"]
    prop = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    byid = {r["example_id"]: r for r in queue}
    disc, doms = load_taxonomy()

    objs = []
    for r in queue:
        p = prop.get(r["example_id"], {})
        objs.append({
            "example_id": r["example_id"],
            "definition": r.get("definition", ""),
            "mechanism": r.get("mechanism", ""),
            "discipline": p.get("discipline", ""),
            "domains": p.get("domains", []),
        })

    verdicts: dict[str, dict[str, Any]] = {}
    for i in range(0, len(objs), args.batch):
        chunk = objs[i:i + args.batch]
        prompt = build_prompt(chunk, disc, doms)
        try:
            res = call_deepseek(prompt, args.key, args.model)
        except Exception as e:  # noqa: BLE001
            print(f"batch {i}-{i+len(chunk)} FAILED: {e}", file=sys.stderr)
            continue
        for r in res:
            if isinstance(r, dict) and r.get("example_id"):
                verdicts[r["example_id"]] = r
        print(f"batch {i}-{i+len(chunk)}: got {len(res)}", file=sys.stderr)

    OUT_JSON.write_text(json.dumps(verdicts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    disc_overrides = [eid for eid, v in verdicts.items() if v.get("discipline_verdict") == "override"]
    dom_overrides = [eid for eid, v in verdicts.items() if v.get("domains_verdict") == "override"]

    md = [
        "# P5 DeepSeek cross-verification (v4-flash vs v4-pro)",
        "",
        f"**Verifier:** {args.model} (independent of deepseek-v4-pro)  |  **Verified:** {len(verdicts)}/{len(objs)}",
        "",
        f"- **discipline overrides:** {len(disc_overrides)}",
        f"- **domains overrides:** {len(dom_overrides)}",
        "",
        "| example_id | disc verdict | discipline | dom verdict | domains | confidence |",
        "|---|---|---|---|---|---|",
    ]
    for eid in sorted(verdicts):
        v = verdicts[eid]
        md.append(
            f"| {eid} | {v.get('discipline_verdict','?')} | `{v.get('discipline','?')}` | "
            f"{v.get('domains_verdict','?')} | {', '.join(v.get('domains',[])) or '(none)'} | {v.get('confidence','?')} |"
        )
    md.append("")
    md.append("> Disagreements = claims to scrutinize first. Signal not proof.")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    print(f"wrote {OUT_JSON.name} + {OUT_MD.name}: {len(verdicts)} verified, "
          f"{len(disc_overrides)} disc overrides, {len(dom_overrides)} dom overrides")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
