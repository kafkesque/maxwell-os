#!/usr/bin/env python3
"""apply_taxonomy_v9.py — promote validated taxonomy_v9.yaml to LIVE + sync config consumers (D-2897).

Precondition: scripts/validate_taxonomy_partition.py reports CLEAN on config/taxonomy_v9.yaml.
Every write is C6 crash-safe (tempfile -> fsync -> os.replace). Idempotent. Surgical text edits
(never load+dump) so YAML comments/formatting are preserved. Fail-closed (C16): every replacement
must change the text exactly once, else abort before writing.

Actions:
  1. promote config/taxonomy_v9.yaml -> config/taxonomy.yaml (LIVE source; renderer + validator
     read this path hardcoded — the 'v5' filename is a historical artifact, content now v9).
  2. config/version.yaml taxonomy_version v8 -> v9.
  3. config/pipeline_config.yaml: drop per_label 'information retrieval' + 'visual semiotics'
     (merged canonicals). NOTE: max_disciplines is left untouched (pre-existing 61 vs actual count;
     semantics ambiguous — flagged in the D-2899 audit, not mutated here).
  4. scripts/menu_axis_hashes.py: repoint MENU closed_menu_v8.json -> closed_menu_v9.json.
  5. config/menu_axis_groups.yaml: repoint source -> closed_menu_v9.json.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
V9 = ROOT / "config" / "taxonomy_v9.yaml"
LIVE = ROOT / "config" / "taxonomy.yaml"
VERSION = ROOT / "config" / "version.yaml"
PIPE_CFG = ROOT / "config" / "pipeline_config.yaml"
HASHES_SCRIPT = ROOT / "scripts" / "menu_axis_hashes.py"
GROUPS = ROOT / "config" / "menu_axis_groups.yaml"


def _atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"FAIL {label}: expected exactly 1 occurrence of {old!r}, found {n}")
    return text.replace(old, new)


def _drop_line(text: str, line: str, label: str) -> str:
    if text.count(line) != 1:
        raise SystemExit(f"FAIL {label}: expected exactly 1 line {line!r}, found {text.count(line)}")
    return text.replace(line + "\n", "")


def main() -> int:
    if not V9.exists():
        print("FAIL: config/taxonomy_v9.yaml missing — run scripts/build_taxonomy_v9.py first", file=sys.stderr)
        return 1

    v9_text = V9.read_text(encoding="utf-8")
    tax = yaml.safe_load(v9_text)
    assert tax["version"] == "v9", tax["version"]
    n_dom = len(tax["domains"])
    n_disc = len(tax["disciplines"])

    # 1. promote -> LIVE
    _atomic(LIVE, v9_text)
    print(f"[1] promoted {V9.name} -> {LIVE.name}  (domains={n_dom} disciplines={n_disc})")

    # 2. version.yaml
    v = VERSION.read_text(encoding="utf-8")
    _atomic(VERSION, _replace_once(v, "taxonomy_version: v8", "taxonomy_version: v9", "version.yaml"))
    print("[2] version.yaml taxonomy_version v8 -> v9")

    # 3. pipeline_config: drop merged per_label weights
    pc = PIPE_CFG.read_text(encoding="utf-8")
    pc = _drop_line(pc, "      information retrieval: 0.125", "pipeline_config per_label IR")
    pc = _drop_line(pc, "      visual semiotics: 0.0714", "pipeline_config per_label visual semiotics")
    _atomic(PIPE_CFG, pc)
    print("[3] pipeline_config: dropped per_label information retrieval + visual semiotics")

    # 4. menu_axis_hashes.py
    t = HASHES_SCRIPT.read_text(encoding="utf-8")
    _atomic(HASHES_SCRIPT, _replace_once(t, 'closed_menu_v8.json"', 'closed_menu_v9.json"', "menu_axis_hashes.py"))
    print("[4] menu_axis_hashes.py MENU -> closed_menu_v9.json")

    # 5. menu_axis_groups.yaml
    g = GROUPS.read_text(encoding="utf-8")
    _atomic(GROUPS, _replace_once(g, "source: config/closed_menu_v8.json",
                                   "source: config/closed_menu_v9.json", "menu_axis_groups.yaml"))
    print("[5] menu_axis_groups.yaml source -> closed_menu_v9.json")

    print("DONE. Next: python3 scripts/render_closed_menu.py --mint-version 9")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
