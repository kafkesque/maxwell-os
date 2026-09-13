#!/usr/bin/env python3
"""scripts/deepseek_frontier_audit.py — R5 cross-family ontology-bound audit (v4).

SECOND-OPINION verifier on golden objects, definition-grounded. Per-object it:
  (1) VERIFIES existing depth/discipline/domains/content_type labels (agree/override);
  (2) returns confidence + a reason citing the ontology definition/boundary.

v4 CHANGE — verifier swapped from DeepSeek-v4-pro to LOCAL Qwen3.8-27B (OMLX):
  DeepSeek-v4-pro is a reasoning model that intermittently returns EMPTY content
  ("empty content (truncated reasoning?)" — BUG-240/DELEGATE-001) on the complex
  multi-axis ontology prompt, and scales superlinearly (batch cliff at ~4 objects).
  Qwen3.8-27B is single-shot, local (C1/C3), a DIFFERENT family from the gpt-oss
  silver teacher (R5), and already the joint-vote's other reliable voter.

ONTOLOGY MECHANISM (D2570/D2613):
  1. Embed all 43 domain + 61 discipline DEFINITIONS once (bge-m3, local).
  2. Embed each principle's definition.
  3. Cosine → top-K candidates per axis (always UNION existing silver labels so
     the "agree" path stays testable).
  4. Inject ONLY those top-K candidates' definition+exclude (boundary) into the
     prompt — small, focused, definition-grounded.

Inputs (auto-detected by extension):
  - .json  → frontier-Qwen3.8 object map (governance/frontier_qwen38_69_objects.json)
  - .jsonl → Phase-0 extension rows (governance/phase0_extension_list.jsonl),
             definitions resolved from config/golden/stage4_golden_mined.yaml.

Output is a SIGNAL, not proof — humans remain the arbiter (D2595).

Usage:
    python3 scripts/deepseek_frontier_audit.py --objects governance/frontier_qwen38_69_objects.json \
        --out-json governance/deepseek_frontier69_audit_v2.json --out-md governance/deepseek_frontier69_audit_v2.md
    python3 scripts/deepseek_frontier_audit.py --objects governance/phase0_extension_list.jsonl \
        --out-json governance/deepseek_extension80_audit.json --out-md governance/deepseek_extension80_audit.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.json_fixer import parse_json_robust  # noqa: E402

OBJECTS = ROOT / "governance" / "frontier_qwen38_69_objects.json"
GOLDEN = ROOT / "config" / "golden" / "stage4_golden_mined.yaml"
TAXONOMY = ROOT / "config" / "taxonomy_v5.yaml"
EMBED_CACHE = ROOT / "governance" / ".taxonomy_emb_v5.npz"
OUT_JSON = ROOT / "governance" / "deepseek_frontier69_audit.json"
OUT_MD = ROOT / "governance" / "deepseek_frontier69_audit.md"

VERIFIER_MODEL = "Qwen3.8-27B-MLX-4bit"
VERIFIER_MAX_TOKENS: int = 4096

K_DISCIPLINE: int = 4   # single-label axis → few candidates
K_DOMAIN: int = 8       # multi-label axis → more headroom

CONTENT_TYPE_RULES = """CONTENT-TYPE (5 roles + 2 dispositions):
- principle: general truth / reusable rule. A SINGLE transferable prescriptive claim (one-sentence heuristic acting as a filter across 3+ domains, OR a deep single-domain principle) is principle.
- process_template: step-by-step method — needs a SEQUENCE of >=2 steps AND a gate/done-condition. A single instruction is NOT a template.
- process_instance: a specific NAMED case / execution of a method (a study, project, product).
- growth_edge: open / unproven / speculative or a loose correlation (an articulated open tension, not a dump for failed depth-tests).
- tool_instruction: command / API / feature for a specific tool.
- noise_drop: just describes a fact / history / summary — no transferable value.
- quarantine: carries SOME value but no clean role — hold.
RULES: descriptive/historical summary -> noise_drop; named method-execution -> process_instance; reusable matrix/methodology with NO explicit steps -> principle (not process_template); ambiguous value -> quarantine."""

DEPTH_DEFINITIONS = """DEPTH (pick exactly one, by transferable scope):
- universal: a general truth applying across >=3 distinct domains/fields (systems-level, laws, ubiquitous cognitive/heuristic truths).
- cross-domain: transferable across >=2 distinct domains — bridges fields but is not universal.
- domain: holds within ONE field or a cluster of adjacent/related domains (a field-level heuristic).
- specialized: deeply specific to ONE narrow domain/tool/context — low transferability."""


def load_taxonomy() -> dict[str, Any]:
    import yaml  # noqa: E402
    return yaml.safe_load(TAXONOMY.read_text(encoding="utf-8")) or {}


def _entry_map(entries: list[Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for e in entries:
        if not isinstance(e, dict):
            continue
        c = e.get("canonical")
        if not c:
            continue
        out[str(c)] = {
            "definition": (e.get("definition") or "").strip(),
            "exclude": [str(x).strip() for x in (e.get("exclude") or []) if str(x).strip()],
        }
    return out


def _entry_line(canonical: str, meta: dict[str, Any]) -> str:
    line = f"- {canonical}"
    if meta.get("definition"):
        line += f" — {meta['definition']}"
    if meta.get("exclude"):
        line += f"  [EXCLUDE: {', '.join(meta['exclude'])}]"
    return line


def _embed_definitions(texts: list[str]) -> "Any":
    import numpy as np  # noqa: E402
    from pipeline.embeddings import embed_texts_bge_m3  # noqa: E402
    return embed_texts_bge_m3(texts)


def build_taxonomy_index(tax: dict[str, Any]) -> dict[str, Any]:
    import numpy as np  # noqa: E402

    disc_map = _entry_map(tax.get("disciplines", []))
    dom_map = _entry_map(tax.get("domains", []))
    disc_names = list(disc_map)
    dom_names = list(dom_map)
    disc_texts = [disc_map[n]["definition"] or n for n in disc_names]
    dom_texts = [dom_map[n]["definition"] or n for n in dom_names]

    cache: dict[str, Any] | None = None
    if EMBED_CACHE.exists():
        try:
            z = np.load(EMBED_CACHE, allow_pickle=False)
            if list(z.get("disc_names", [])) == disc_names and list(z.get("dom_names", [])) == dom_names:
                cache = {
                    "disc_embs": z["disc_embs"], "dom_embs": z["dom_embs"],
                    "disc_names": list(z["disc_names"]), "dom_names": list(z["dom_names"]),
                }
        except Exception:  # noqa: BLE001
            cache = None

    if cache is None:
        disc_embs = _embed_definitions(disc_texts)
        dom_embs = _embed_definitions(dom_texts)
        np.savez_compressed(
            EMBED_CACHE, disc_embs=disc_embs, dom_embs=dom_embs,
            disc_names=np.asarray(disc_names), dom_names=np.asarray(dom_names),
        )
        cache = {"disc_embs": disc_embs, "dom_embs": dom_embs, "disc_names": disc_names, "dom_names": dom_names}

    return {
        "disciplines": disc_map, "domains": dom_map,
        "disc_embs": cache["disc_embs"], "dom_embs": cache["dom_embs"],
        "disc_names": cache["disc_names"], "dom_names": cache["dom_names"],
    }


def top_candidates(
    defn_emb: "Any", index: dict[str, Any], axis: str, k: int, existing: list[str],
) -> list[str]:
    embs = index[f"{axis}_embs"]
    names = index[f"{axis}_names"]
    sims = embs @ defn_emb
    order = sorted(range(len(names)), key=lambda i: -float(sims[i]))
    picks: list[str] = [names[i] for i in order[:k]]
    for e in existing:
        if e and e not in picks and e in set(names):
            picks.append(e)
    return picks


def load_golden_definitions() -> dict[str, str]:
    import yaml  # noqa: E402
    data = yaml.safe_load(GOLDEN.read_text(encoding="utf-8")) or {}
    examples = data.get("examples", [])
    out: dict[str, str] = {}
    for e in examples if isinstance(examples, list) else []:
        eid = e.get("id")
        fb = e.get("input_fb") or {}
        definition = (fb.get("definition") or "").strip()
        if eid and definition:
            out[str(eid)] = definition
    return out


def normalize_objects(raw: Any, src_path: Path) -> dict[str, dict[str, Any]]:
    gold_defs = load_golden_definitions()
    norm: dict[str, dict[str, Any]] = {}
    if src_path.suffix == ".jsonl":
        for line in src_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            eid = str(r.get("example_id", ""))
            if not eid:
                continue
            norm[eid] = {
                "definition": gold_defs.get(eid, ""),
                "existing_depth": r.get("silver_depth", ""),
                "existing_discipline": r.get("silver_discipline", ""),
                "existing_domains": r.get("silver_domains") or [],
                "existing_content_type": r.get("silver_content_type"),
            }
    else:
        if isinstance(raw, list):
            raw = {str(o.get("example_id") or o.get("id")): o for o in raw if isinstance(o, dict)}
        for eid, v in raw.items():
            if not isinstance(v, dict):
                continue
            norm[str(eid)] = {
                "definition": v.get("definition") or gold_defs.get(str(eid), ""),
                "existing_depth": v.get("final_depth", ""),
                "existing_discipline": v.get("final_discipline", ""),
                "existing_domains": v.get("final_domains") or [],
                "existing_content_type": v.get("final_content_type"),
            }
    return norm


def build_prompt(objects: list[tuple[str, dict[str, Any], dict[str, list[str]]]]) -> str:
    lines = [
        "You are a senior RAG/ontology verifier. For each object, classify ONLY against",
        "the provided candidate definitions and their EXCLUDE boundaries — the correct",
        "label is among the candidates.",
        "",
        DEPTH_DEFINITIONS,
        "",
        CONTENT_TYPE_RULES,
        "",
        "For each object, return ONLY this JSON shape (no prose):",
        "{",
        '  "example_id": "...",',
        '  "depth_verdict": "agree|override", "depth": "...",',
        '  "discipline_verdict": "agree|override", "discipline": "...",',
        '  "domains_verdict": "agree|override", "domains": ["..."],',
        '  "content_type": "principle|process_template|process_instance|growth_edge|tool_instruction|noise_drop|quarantine",',
        '  "confidence": "high|medium|low",',
        '  "reason": "one sentence citing the definition/boundary used"',
        "}",
        "",
        "Return a JSON object of the form {\"results\": [ ... ]} — one result object per input",
        "object. Existing labels are proposals — verify them independently against the candidate",
        "definitions; OVERRIDE if wrong.",
        "",
        "OBJECTS:",
    ]
    for eid, o, cands in objects:
        lines.append(json.dumps({
            "example_id": eid,
            "definition": o.get("definition", ""),
            "existing_depth": o.get("existing_depth", ""),
            "existing_discipline": o.get("existing_discipline", ""),
            "existing_domains": o.get("existing_domains", []),
            "existing_content_type": o.get("existing_content_type"),
            "candidate_disciplines": cands["disciplines"],
            "candidate_domains": cands["domains"],
        }, ensure_ascii=False))
    lines.append("")
    lines.append("Return ONLY the JSON object {\"results\": [...]}, nothing else.")
    return "\n".join(lines)


def call_verifier(prompt: str, model: str, max_tokens: int) -> list[dict[str, Any]]:
    """Local Qwen3.8-27B verifier via OMLX (single-shot, no reasoning burn)."""
    from pipeline.omlx_call import call_omlx_json  # noqa: E402

    out = call_omlx_json(
        prompt,
        model=model,
        system="You are a precise JSON-only verifier. Return only a valid JSON object.",
        max_tokens=max_tokens,
        timeout=600,
    )
    if isinstance(out, dict):
        for v in out.values():
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
        return [out] if out.get("example_id") else []
    if isinstance(out, list):
        return [x for x in out if isinstance(x, dict)]
    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=VERIFIER_MODEL)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--max-tokens", type=int, default=VERIFIER_MAX_TOKENS)
    ap.add_argument("--objects", type=Path, default=OBJECTS)
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    if not args.objects.exists():
        print(f"ERROR: objects file not found: {args.objects}", file=sys.stderr)
        return 2

    raw = json.loads(args.objects.read_text(encoding="utf-8")) if args.objects.suffix != ".jsonl" else None
    objs = normalize_objects(raw, args.objects)

    tax = load_taxonomy()
    index = build_taxonomy_index(tax)
    print(
        f"loaded {len(objs)} objects | ontology index: {len(index['disc_names'])} disciplines "
        f"| {len(index['dom_names'])} domains | verifier: {args.model} (local OMLX)",
        file=sys.stderr,
    )

    import numpy as np  # noqa: E402
    eids = sorted(objs)
    defns = [objs[e]["definition"] or objs[e].get("existing_discipline", "") or " " for e in eids]
    try:
        defn_embs = _embed_definitions(defns)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: embeddings unavailable ({e}) — aborting rather than degrading.", file=sys.stderr)
        return 3

    prepared: list[tuple[str, dict[str, Any], dict[str, list[str]]]] = []
    for i, eid in enumerate(eids):
        o = objs[eid]
        disc_names = top_candidates(defn_embs[i], index, "disc", K_DISCIPLINE, [o.get("existing_discipline") or ""])
        dom_names = top_candidates(defn_embs[i], index, "dom", K_DOMAIN, o.get("existing_domains") or [])
        prepared.append((
            eid, o, {
                "disciplines": [_entry_line(n, index["disciplines"].get(n, {})) for n in disc_names],
                "domains": [_entry_line(n, index["domains"].get(n, {})) for n in dom_names],
            },
        ))

    if args.limit:
        prepared = prepared[: args.limit]

    verdicts: dict[str, dict[str, Any]] = {}
    for i in range(0, len(prepared), args.batch):
        chunk = prepared[i:i + args.batch]
        prompt = build_prompt(chunk)
        try:
            res = call_verifier(prompt, args.model, args.max_tokens)
        except Exception as e:  # noqa: BLE001
            print(f"batch {i}-{i+args.batch} FAILED: {e}", file=sys.stderr)
            continue
        for r in res:
            if isinstance(r, dict) and r.get("example_id"):
                verdicts[str(r["example_id"])] = r
        print(f"batch {i}-{i+args.batch}: got {len(res)} verdicts ({len(verdicts)}/{len(prepared)} total)", file=sys.stderr)

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(verdicts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    md = [
        "# Ontology-Bound Audit (v4 — definition-grounded, bge-m3 pre-ranked, local verifier)",
        "",
        f"**Verifier:** {args.model} (local OMLX)  |  **Objects:** {len(verdicts)}/{len(prepared)}",
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
    args.out_md.write_text("\n".join(md), encoding="utf-8")

    print(f"wrote {args.out_json.name} + {args.out_md.name} ({len(verdicts)} verdicts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
