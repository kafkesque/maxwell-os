#!/usr/bin/env python3
"""scripts/review_aliases.py — D2568 alias quality review (Phase 1: Qwen3.8 proposals).

The D2566/D2567 alias extension accepted mappings only when Qwen3.8 (generator)
and gpt-oss-20b (verifier) AGREED — but two models can share a training bias, so
agreement is necessary but not sufficient. This script re-reviews the SINGLE-VALUE
aliases (list-valued aliases are deterministic compound splits and skipped) with
Qwen3.8-27B as the WORKER: for each raw→canonical alias it flags any it believes
is WRONG and proposes a corrected canonical.

Phase 2 (separate step) sends Qwen3.8's proposals to an independent verifier
(DeepSeek, cross-family) and accepts only agreement — mirroring R5.

Read-only w.r.t. alias_map.yaml and the DB. Writes proposals to a JSONL checkpoint
so a long run can resume.

Run:
    python3 scripts/review_aliases.py                    # review all single-value aliases
    python3 scripts/review_aliases.py --limit 40         # smoke-test on a subset
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import yaml  # noqa: E402

from pipeline.omlx_call import call_omlx  # noqa: E402

_ALIAS = _ROOT / "config" / "alias_map.yaml"
_TAXONOMY = _ROOT / "config" / "taxonomy_v5.yaml"
_OUT = _ROOT / "temp" / "alias_review_qwen38.jsonl"

# C20 named constants — model routing mirrors extend_alias_index.py (R5 worker).
_REVIEW_MODEL = "Qwen3.8-27B-MLX-4bit"
_SYSTEM = "You are a precise taxonomy reviewer. Return ONLY valid JSON. No markdown, no explanation."
_TIMEOUT = 600
_MAX_TOKENS = 4000
_BATCH = 120  # C20: aliases per LLM call (compact single-line format)


def _load_single_aliases() -> list[tuple[str, str, str]]:
    """Return [(kind, raw, target)] for all single-value (non-list) aliases."""
    a = yaml.safe_load(open(_ALIAS, encoding="utf-8"))
    out: list[tuple[str, str, str]] = []
    for kind in ("domain_aliases", "discipline_aliases"):
        for raw, target in (a.get(kind) or {}).items():
            if isinstance(target, str):
                out.append((kind, str(raw), str(target)))
    return out


def _canonicals() -> dict[str, list[str]]:
    tax = yaml.safe_load(open(_TAXONOMY, encoding="utf-8"))
    return {
        "domain": [d["canonical"] for d in tax["domains"]],
        "discipline": [d["canonical"] for d in tax["disciplines"]],
    }


def _prompt(items: list[tuple[int, tuple[str, str, str]]], canon: dict[str, list[str]]) -> str:
    lines = []
    for gidx, (kind, raw, target) in items:
        lines.append(f"{gidx}||{kind}||{raw}||{target}")
    axis = "domain" if items[0][1][0] == "domain_aliases" else "discipline"
    canon_list = canon["domain"] if axis == "domain" else canon["discipline"]
    return (
        "You are reviewing a synonym alias index for a design-knowledge taxonomy. "
        "Each line is: index||kind||raw_label||canonical_target. "
        f"The valid canonical {axis} labels are exactly: {json.dumps(canon_list)}.\n"
        "For each line, judge whether 'raw_label -> canonical_target' is SEMANTICALLY CORRECT. "
        "Flag ONLY the mappings you believe are WRONG (raw label does not belong to that canonical).\n"
        "Return ONLY a JSON object of the form {\"wrong\": [{\"i\": <int index>, \"corrected\": \"<canonical>\"}]}. "
        "Omit correct mappings entirely. Use ONLY labels from the canonical list for 'corrected'.\n\n"
        + "\n".join(lines)
    )


def _parse_json(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```")[1]
        if t.startswith("json"):
            t = t[4:]
    start, end = t.find("{"), t.rfind("}")
    return json.loads(t[start:end + 1]) if start >= 0 and end >= 0 else {}


def _load_checkpoint() -> set[int]:
    if not _OUT.exists():
        return set()
    done: set[int] = set()
    for line in _OUT.read_text(encoding="utf-8").splitlines():
        try:
            done.add(int(json.loads(line)["i"]))
        except (json.JSONDecodeError, KeyError, ValueError) as exc:  # C16: log, don't swallow
            print(f"  ⚠️  checkpoint: skipping malformed line {line[:80]!r} ({exc})", file=sys.stderr)
            continue
    return done


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0, help="Review only the first N aliases.")
    args = ap.parse_args()

    entries = _load_single_aliases()
    canon = _canonicals()
    if args.limit:
        entries = entries[: args.limit]
    done = _load_checkpoint()
    todo = [(i, e) for i, e in enumerate(entries) if i not in done]
    print(f"single-value aliases: {len(entries)}, to review: {len(todo)}")

    proposals: list[dict] = []
    for start in range(0, len(todo), _BATCH):
        chunk = todo[start:start + _BATCH]
        idxs = [i for i, _ in chunk]
        batch = [e for _, e in chunk]
        # group by axis for a coherent canonical list
        for axis in ("domain_aliases", "discipline_aliases"):
            sub = [(i, e) for i, e in chunk if e[0] == axis]
            if not sub:
                continue
            prompt = _prompt(sub, canon)
            text = call_omlx(
                prompt=prompt,
                model=_REVIEW_MODEL,
                system=_SYSTEM,
                max_tokens=_MAX_TOKENS,
                timeout=_TIMEOUT,
            )
            try:
                resp = _parse_json(text)
            except (json.JSONDecodeError, ValueError) as exc:
                print(f"  ⚠️  parse error on batch (indices {sub[0][0]}..{sub[-1][0]}): {exc}")
                print(f"      raw response head: {text[:200]!r}")
                continue
            for w in resp.get("wrong", []):
                try:
                    i = int(w["i"])
                    corrected = str(w["corrected"]).strip()
                except (KeyError, ValueError, TypeError):
                    continue
                kind, raw, target = entries[i]
                proposals.append({
                    "i": i, "kind": kind, "raw": raw, "target": target,
                    "corrected": corrected,
                })
                with open(_OUT, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"i": i, "kind": kind, "raw": raw,
                                        "target": target, "corrected": corrected}) + "\n")
        print(f"  … reviewed up to index {min(idxs[-1] + 1, len(entries))}; "
              f"{len(proposals)} proposals so far")

    print(f"\n✅ Qwen3.8 proposed {len(proposals)} corrections → {_OUT.name}")
    for p in proposals:
        print(f"  {p['kind'][:8]:8s} {p['raw']!r} -> {p['target']!r}  ✗→ {p['corrected']!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
