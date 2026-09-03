#!/usr/bin/env python3
"""
recover_bug198_singletons.py — D2517 (BUG-198 recovery, part 1 of 2)

BUG-198: 6 S2 singleton principles were emitted with `application: None` and
dropped at S4 (D2371 application-is-required, fail-closed). The 6 records are
intact in stage2_extract/t11/{singleton_fbs,checkpoint}.jsonl.

Part 1 (this script, deterministic): locate the 6 records, backfill the single
missing `application` field (cross-family filled via gemma — the exact field
that caused the D2371 drop), and emit a re-injection manifest:
    knowledge pipeline/stage2_extract/t11/recovered_singletons.jsonl

Part 2 (NOT automated here — needs the live generator + DeBERTa NLI): run the
manifest through S4 (classify domains/discipline/depth/evidence/context) →
S5 (NLI verify) → S6 (commit). This is a targeted 6-record mini-run, NOT a
full S0-S6 rerun. We deliberately do NOT INSERT unverified rows directly.

Run: /usr/local/bin/python3 scripts/recover_bug198_singletons.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
T11 = ROOT / "knowledge pipeline" / "stage2_extract" / "t11"
OUT = T11 / "recovered_singletons.jsonl"

# gemma cross-family single-field fill (Generator != Verifier, R5)
APPLICATIONS: dict[str, str] = {
    "1b123adb": "Practitioners enhance clarity and logical structure in expressions and proofs by using alphabet-start letters for given quantities and alphabet-end letters for unknowns.",
    "14978863": "Scientists, engineers, and economists apply probability methods to previously inaccessible problems by determining priors using the maximum-entropy principle.",
    "2cae771b": "Practitioners induce light trance states to facilitate recall of buried memories by using rhythmic hand movements that increase subject suggestibility and reduce cognitive filtering.",
    "b4899671": "In recipe combinations, a predictable framework emerges when the number of possible selections follows the Fibonacci sequence, where each count is the sum of the prior two.",
    "2b8ceef5": "Practitioners confirm that matrices constructed with Fibonacci numbers in specific arrangements always yield zero determinants due to linear dependence among adjacent columns.",
    "f11b8327": "Solutions to Partial Differential Equations are probabilistically approximated by launching numerous random walks from a grid point, whose boundary proportions approximate the true solution.",
}

PREFIXES = tuple(APPLICATIONS)


def main() -> None:
    found: dict[str, dict] = {}
    for path in (T11 / "singleton_fbs.jsonl", T11 / "checkpoint.jsonl"):
        if not path.exists():
            continue
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                for pre in PREFIXES:
                    if pre in line:
                        try:
                            rec = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        fid = rec.get("fb_id", "")
                        if fid.startswith(pre):
                            found[fid] = rec

    n = 0
    with open(OUT, "w") as out:
        for fid, rec in found.items():
            rec["application"] = APPLICATIONS[fid[:8]]
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    print(f"✅ wrote {n} recovered singleton(s) -> {OUT}")
    for fid in found:
        print(f"   {fid[:12]}  application={APPLICATIONS[fid[:8]][:60]}...")
    missing = [p for p in PREFIXES if not any(f.startswith(p) for f in found)]
    if missing:
        print(f"⚠️  MISSING prefixes (not found): {missing}")


if __name__ == "__main__":
    main()
