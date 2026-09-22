#!/usr/bin/env python3
"""F-11 three-way disagreement worksheet: human vs two independent LLM coders (D-329).

Locates WHERE the ruler's human labels diverge, and in which way:

  consensus divergence  both coders agree with each other, the human differs  -> candidate RULER defect
  model split           the two coders disagree; the human matches one of them -> genuine row ambiguity
  three-way             all three differ                                        -> taxonomy cannot carry the row

Read-only analysis: writes governance/f11_disagreement_3way_<date>.{md,json}, changes nothing else.
Config-driven (C12): menus, sheet and aliases come from config/f11_llm_coder.yaml.
"""
from __future__ import annotations

import csv
import json
import pathlib
import sys
import time
from collections import Counter, defaultdict
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import yaml  # noqa: E402
from f11_llm_coder import _canon, _kappa  # noqa: E402
from pipeline.io_guard import safe_write  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
AXES = {"content_type": "CT (1-7)", "discipline": "DISC (1-62)", "extraction_type": "FORM (1-4)"}


def _jsonl(path: pathlib.Path) -> dict[str, dict[str, Any]]:
    """Parse a coder answer file (bare JSONL; a .md extension is tolerated, not a format)."""
    out: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("{"):
            obj = json.loads(line)
            out[str(obj["item_id"])] = obj
    return out


def main(argv: list[str]) -> int:
    """Write the three-way worksheet; exit 0 unless the inputs are unusable."""
    if len(argv) != 3:
        print("usage: f11_disagreement_3way.py <coder_a.jsonl> <coder_b.jsonl>", file=sys.stderr)
        return 2
    cfg = yaml.safe_load((ROOT / "config/f11_llm_coder.yaml").read_text(encoding="utf-8"))
    aliases = {_canon(a["as_written"], {}): _canon(a["canonical"], {}) for a in cfg["declared_aliases"]}
    sheet = {r["item_id"]: r for r in csv.DictReader((ROOT / cfg["sheet"]).open(encoding="utf-8"))}
    pa, pb = (pathlib.Path(p).resolve() for p in argv[1:3])
    a, b = _jsonl(pa), _jsonl(pb)
    both = sorted(set(a) & set(b) & set(sheet))
    if not both:
        raise SystemExit("no common rows between the two coder files and the sheet")
    rep: dict[str, Any] = {"schema_version": "1.0", "decision": "D-329", "date": time.strftime("%Y-%m-%d"),
                           "tier": "llm-attested (advisory — cannot unfreeze eval floors, F-11)", "n_rows": len(both),
                           "coder_a": {"file": str(pa), "rows": len(a)}, "coder_b": {"file": str(pb), "rows": len(b)},
                           "axes": {}}
    md = [f"# F-11 three-way disagreement worksheet — human vs two LLM coders (n={len(both)})",
          "", f"coders: `{pa.name}` (n={len(a)}) and `{pb.name}` (n={len(b)}) — tier **llm-attested / advisory**.",
          "Classes: **consensus divergence** = both coders agree, human differs (ruler suspect); "
          "**model split** = coders disagree, human matches one (real ambiguity); **three-way** = all differ.", ""]
    for ax, col in AXES.items():
        rows = [(i, _canon(sheet[i][col], aliases), _canon(a[i][ax], aliases), _canon(b[i][ax], aliases)) for i in both]
        def _cls(h: str, m: str, n: str) -> str:
            """Classify one row: unanimous / consensus divergence / three-way / model split."""
            if h == m == n:
                return "unanimous"
            if m == n:
                return "consensus divergence"
            if h != m and h != n:
                return "three-way"
            return "model split"

        cls = Counter(_cls(h, m, n) for _, h, m, n in rows)
        pairs = Counter((h, m) if m == n else (h, f"{m} | {n}") for _, h, m, n in rows if not (h == m == n))
        ids = defaultdict(list)
        for i, h, m, n in rows:
            if not (h == m == n):
                ids[_cls(h, m, n)].append(i)
        rep["axes"][ax] = {"column": col, "classes": dict(cls), "n_divergent": sum(cls.values()),
                           "top_pairs": [[list(k), v] for k, v in pairs.most_common(12)],
                           "ids": {k: v for k, v in ids.items()}}
        md += [f"## {ax}  ({col})", f"unanimous {len(rows) - sum(cls.values())}/{len(rows)} · "
               + " · ".join(f"{k} {v}" for k, v in cls.most_common()), "",
               "| count | human said | both coders said |", "|---|---|---|"]
        md += [f"| {v} | {k[0]} | {k[1]} |" for k, v in pairs.most_common(12)] + [""]
    stamp = time.strftime("%Y%m%d")
    safe_write(ROOT / f"governance/f11_disagreement_3way_{stamp}.md", "\n".join(md) + "\n", force_shrink=True)
    safe_write(ROOT / f"governance/f11_disagreement_3way_{stamp}.json", json.dumps(rep, indent=2) + "\n",
               force_shrink=True)
    print(f"✅ governance/f11_disagreement_3way_{stamp}.md/.json  (n={len(both)})")
    for ax, d in rep["axes"].items():
        print(f"  {ax:16} divergent {d['n_divergent']:3}  {d['classes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
