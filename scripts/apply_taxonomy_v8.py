#!/usr/bin/env python3
"""apply_taxonomy_v8.py — promote the validated taxonomy_v8.yaml to LIVE + sync config consumers (D-2865).

Precondition: scripts/validate_taxonomy_partition.py reports CLEAN on config/taxonomy_v8.yaml.
This script is the "separate apply step" promised by build_taxonomy_v8.py. Every write is C6
crash-safe (tempfile -> fsync -> os.replace). Idempotent. Surgical text edits (never load+dump)
so YAML comments/formatting are preserved.

Actions:
  1. promote config/taxonomy_v8.yaml -> config/taxonomy.yaml (LIVE source; renderer + validator
     read this path hardcoded — the 'v5' filename is a historical artifact, content now v8).
  2. config/version.yaml taxonomy_version v7 -> v8.
  3. config/normalization_map.yaml: drop 'social science: social sciences' (canonical demoted).
  4. config/pipeline_config.yaml: drop per_label 'science & research' + 'social sciences'; max_domains 43 -> 41.
  5. scripts/menu_axis_hashes.py: repoint MENU closed_menu_v7.json -> closed_menu_v8.json.
  6. config/menu_axis_groups.yaml: repoint source -> closed_menu_v8.json.

Fail-closed (C16): every replacement must change the text exactly once, else abort before writing.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
V8 = ROOT / "config" / "taxonomy_v8.yaml"
LIVE = ROOT / "config" / "taxonomy.yaml"
VERSION = ROOT / "config" / "version.yaml"
NORM_MAP = ROOT / "config" / "normalization_map.yaml"
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
    if not V8.exists():
        print("FAIL: config/taxonomy_v8.yaml missing — run scripts/build_taxonomy_v8.py first", file=sys.stderr)
        return 1

    v8_text = V8.read_text(encoding="utf-8")
    tax = yaml.safe_load(v8_text)
    assert tax["version"] == "v8", tax["version"]
    n_dom = len(tax["domains"])
    n_disc = len(tax["disciplines"])

    # 1. promote -> LIVE
    _atomic(LIVE, v8_text)
    print(f"[1] promoted {V8.name} -> {LIVE.name}  (domains={n_dom} disciplines={n_disc})")

    # 2. version.yaml
    v = VERSION.read_text(encoding="utf-8")
    _atomic(VERSION, _replace_once(v, "taxonomy_version: v7", "taxonomy_version: v8", "version.yaml"))
    print("[2] version.yaml taxonomy_version v7 -> v8")

    # 3. normalization_map
    nm = NORM_MAP.read_text(encoding="utf-8")
    _atomic(NORM_MAP, _drop_line(nm, "  social science: social sciences", "normalization_map"))
    print("[3] normalization_map: dropped 'social science: social sciences'")

    # 4. pipeline_config (surgical)
    pc = PIPE_CFG.read_text(encoding="utf-8")
    pc = _drop_line(pc, "      science & research: 0.0211", "pipeline_config per_label")
    pc = _drop_line(pc, "      social sciences: 0.2061", "pipeline_config per_label")
    pc = _replace_once(pc, "  max_domains: 43", f"  max_domains: {n_dom}", "pipeline_config max_domains")
    _atomic(PIPE_CFG, pc)
    print(f"[4] pipeline_config: dropped per_label science & research + social sciences; max_domains -> {n_dom}")

    # 5. menu_axis_hashes.py
    t = HASHES_SCRIPT.read_text(encoding="utf-8")
    _atomic(HASHES_SCRIPT, _replace_once(t, 'closed_menu_v7.json"', 'closed_menu_v8.json"', "menu_axis_hashes.py"))
    print("[5] menu_axis_hashes.py MENU -> closed_menu_v8.json")

    # 6. menu_axis_groups.yaml
    g = GROUPS.read_text(encoding="utf-8")
    _atomic(GROUPS, _replace_once(g, "source: config/closed_menu_v7.json",
                                   "source: config/closed_menu_v8.json", "menu_axis_groups.yaml"))
    print("[6] menu_axis_groups.yaml source -> closed_menu_v8.json")

    print("DONE. Next: python3 scripts/render_closed_menu.py --mint-version 8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
