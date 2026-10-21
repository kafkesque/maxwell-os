#!/usr/bin/env python3
"""W2 - HAS THIS MODEL ALREADY BEEN TESTED? (read-only census, no network, no LLM)

The question that stops a wasted download is not "is it good" but "have we already measured
it". This workstream answers that from the repo's OWN artefacts: every temp/ and governance/
json, log and markdown is scanned for each candidate name, and each hit is classified
MEASURED (the file carries a numeric reading: tokens, seconds, tps, budget) versus MENTIONED
(the name appears but no reading does). MEASURED is evidence that a bench ran; MENTIONED is
only a lookup, which is exactly what a market scan produces.

Usage: python3 pipeline/research/ws_prior_tests.py --report <10_report.md> [--json-out f.json]
Appends STEP/TERMINAL lines, so pipeline/research_run.py stops waiting the moment it is done.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.lib import artifact_encoding  # noqa: E402
SCAN_DIRS = ("temp", "governance", "config", "pipeline", "scripts")
SCAN_EXT = (".json", ".md", ".log", ".yaml", ".txt", ".py")
# MEASURED means the line carries a READING, not merely a number:
#   - a rate or a duration with its unit  (9.88 tps, 479.3 tok/s, 54.7 s, 196.94s)
#   - a bench artefact key               (prompt_tokens, cap_s, warmup_s, budget_s, decode_tps)
# A download count, a "GB" or a "likes=" is NEITHER, and counting it as one produced a false
# "ALREADY TESTED" on 2026-10-15 (BUG-811).
READING = re.compile(r"(\d+(\.\d+)?\s*(tps|tok/?s|s\b|ms\b|seconds)|prompt_tokens|completion_tokens|cap_s|warmup_s|budget_s|decode_tps)", re.I)
SKIP_PARTS = ("/runs/", "/.git/", "node_modules", "_backup", ".bak")


def candidates() -> list[str]:
    """Read the candidate set from config/engine.yaml (the one home - C12)."""
    import yaml
    conf = yaml.safe_load((ROOT / "config" / "engine.yaml").read_text())
    cand = conf["candidates"]
    return list(cand["probe"]) + list(cand["served_now"])


def scan(names: list[str]) -> dict:
    """Classify every mention of every name as MEASURED or MENTIONED."""
    out: dict = {n: {"measured": [], "mentioned": []} for n in names}
    for d in SCAN_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in SCAN_EXT:
                continue
            sp = str(path)
            if any(part in sp for part in SKIP_PARTS):
                continue
            try:
                if path.stat().st_size > 4_000_000:
                    continue
                text = artifact_encoding.open_artifact(path, ROOT).read()
            except Exception:
                continue
            low = text.lower()
            for name in names:
                short = name.split("/")[-1].lower()
                if short not in low:
                    continue
                measured = any(READING.search(l) for l in text.splitlines() if short in l.lower())
                rel = str(path.relative_to(ROOT))
                (out[name]["measured"] if measured else out[name]["mentioned"]).append(rel)
    return out


def main(argv: list[str]) -> int:
    """Run the census and append the verdict to the run's report."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--json-out")
    args = ap.parse_args(argv)
    report = pathlib.Path(args.report)
    names = candidates()

    def emit(line: str) -> None:
        with open(report, "a") as fh:
            fh.write(line.rstrip() + chr(10))
            fh.flush()

    emit("")
    emit("## W2 prior-test census - has this model already been measured?")
    emit("STEP 1: " + str(len(names)) + " candidate names from config/engine.yaml; scanning " + ", ".join(SCAN_DIRS))
    res = scan(names)
    emit("| model | previously MEASURED | only MENTIONED | verdict |")
    emit("|---|---|---|---|")
    summary = {}
    for name in names:
        m, ment = sorted(set(res[name]["measured"])), sorted(set(res[name]["mentioned"]))
        if m:
            verdict, why = "ALREADY TESTED - do not re-buy", str(len(m)) + " artefact(s) with a numeric reading"
        elif ment:
            verdict, why = "LOOKED UP ONLY - never benched", str(len(ment)) + " prose mention(s), no reading"
        else:
            verdict, why = "UNKNOWN TO THIS REPO", "no mention anywhere"
        summary[name] = {"verdict": verdict, "measured": m, "mentioned": ment}
        emit("| " + name + " | " + (", ".join(m) or "-") + " | " + (", ".join(ment[:4]) or "-") + " | " + verdict + " |")
        emit("  - " + why)
        emit("STEP: " + name + " -> " + verdict)
    if args.json_out:
        pathlib.Path(args.json_out).write_text(json.dumps(summary, indent=1))
    emit("STEP final: census complete")
    emit("TERMINAL: DONE - every candidate classified as measured, mentioned or unknown")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
