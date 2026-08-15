#!/usr/bin/env python3
"""Apply depth relabels to golden YAML via SURGICAL line edits (no reformat).

Unlike a ruamel round-trip (which reflowed ~5k lines), this changes ONLY the
targeted depth: lines, leaving the rest byte-identical. Relabel decisions are
read from the vote JSON (C12: data, not code). Verifies the change count matches
expectations and that the result still parses.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

VOTE_JSON = PROJECT_ROOT / "governance" / "depth_bias_relabel_vote.json"


def main() -> int:
    import yaml
    from pipeline.pipeline_paths import S2_GOLDEN_PATH

    golden = PROJECT_ROOT / S2_GOLDEN_PATH
    vote = json.loads(VOTE_JSON.read_text())
    relabels = {r["id"]: r["recommend"] for r in vote if r.get("recommend")}

    lines = golden.read_text().splitlines()
    id_re = re.compile(r"^\s*- id: (\S+)\s*$")
    depth_re = re.compile(r"^(\s*)depth:\s*(domain|cross-domain|universal|specialized)\s*$")

    current_id = None
    changed = 0
    for i, line in enumerate(lines):
        m = id_re.match(line)
        if m:
            current_id = m.group(1)
            continue
        if current_id in relabels:
            m2 = depth_re.match(line)
            if m2:
                lines[i] = f"{m2.group(1)}depth: {relabels[current_id]}"
                print(f"  {current_id}: {m2.group(2)} -> {relabels[current_id]}")
                changed += 1

    golden.write_text("\n".join(lines) + "\n")

    # verify parse + distribution
    d = yaml.safe_load(golden.read_text())
    from collections import Counter
    dist = Counter(e["expected_fb"].get("depth") for e in d["examples"]
                   if isinstance(e.get("expected_fb"), dict) and e["expected_fb"].get("depth"))
    print(f"changed {changed} depth lines (expected {len(relabels)})")
    print(f"new depth distribution: {dict(dist)}")
    return 0 if changed == len(relabels) else 1


if __name__ == "__main__":
    sys.exit(main())
