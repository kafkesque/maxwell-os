#!/usr/bin/env python3
"""scripts/check_r5_verdicts.py - THE R5 COMMIT RAIL (BUG-1106, option a).

WHY (what was RATIFIED vs what actually FIRED). config/r5_review_gate.yaml declares the DEEP reviewer
(gpt-oss-20b-MXFP4-Q8, PROMOTED_20261027 by D-3168) and maps `scripts/*`, `pipeline/*`, `tools/*` to the deep
tier. R5 is an IRON RULE ("Generator != Verifier - different model family for each"). Yet the ONLY live
per-file invocation was config/engine.yaml's `draft-then-verify` done_check `--no-llm` (deterministic layers
ONLY, and its own note says the LLM verdict is "never the decider"), and
config/rail_registry.yaml#commit_boundary.must_contain named only the four deterministic rails. A generated
deep-tier file could therefore land with NO verifier: the iron rule had zero mechanical teeth (BUG-1106).

WHAT THIS IS. A COMMIT-BOUNDARY rail (deterministic, ZERO LLM calls in the commit path): for every STAGED
file whose declared tier is DEEP it computes the file's sha256 (first 16 hex chars - the identity a verdict and
a receipt share, D-2962) over the STAGED blob, and refuses the commit unless governance/r5_reviews.jsonl
already holds an APPROVE verdict from the DECLARED deep reviewer for that exact file+digest. The LLM call stays
a PRE-STEP the agent runs (`python3 scripts/r5_review_gate.py --file <file>`); this rail only VERIFIES the
verdict exists, so a commit never blocks on a model being served - it blocks on the verdict's ABSENCE, which is
the agreement. The tier rule and the config are imported from scripts/r5_review_gate.py (ONE home), never
restated (D-2646/C12).

OVERSIZED FILES. A deep-tier file whose size exceeds the declared tier cap (max_source_chars) can never carry a
whole-file APPROVE (the gate refuses to send it, BUG-746), so it is REFUSED with a message naming the declared
remedy (T-221: split it into R5-reviewable modules), never silently passed.

EXIT: 0 every reviewable deep-tier staged file carries an APPROVE from the deep reviewer | 1 at least one lacks
it, is oversized, or the config/git state is unreadable (refuse the commit, fail closed, C16).
--selftest: known-answer controls, no git, no LLM, no network (BUG-492).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

# ONE home for the tier rule and the config (D-2646/C12): never re-implement the tier decision here.
from r5_review_gate import load_config, tier_for  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def digest16(data: bytes) -> str:
    """First 16 hex chars of the sha256 - the identity a verdict and a receipt share (D-2962).

    Must equal scripts/r5_review_gate.py#digest for the same bytes: that function hashes a Path's bytes, this
    hashes bytes directly, and for identical bytes the two produce the identical 16-char prefix.
    """
    return hashlib.sha256(data).hexdigest()[:16]


def approve_keys(journal: Path, deep_reviewer: str) -> set[tuple[str, str]]:
    """{(file, sha256_16)} for every APPROVE verdict the DECLARED deep reviewer recorded in the journal.

    A malformed line is not a verdict and must not stop the scan (C16). A verdict from any OTHER reviewer (gemma
    fast-tier, or the retired Qwen3.8 advisory auditor) is deliberately NOT an APPROVE for the deep tier.
    """
    out: set[tuple[str, str]] = set()
    if not journal.exists():
        return out
    for line in journal.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry: dict = json.loads(line)
        except Exception:  # noqa: BLE001 - a malformed line is not a verdict, and must not stop the scan
            continue
        if str(entry.get("verdict")) == "APPROVE" and str(entry.get("reviewer")) == deep_reviewer:
            out.add((str(entry.get("file")), str(entry.get("sha256_16"))))
    return out


def classify(rel: str, digest: str, size: int, cap: int, approved: set[tuple[str, str]]) -> str:
    """'ok' | 'oversized' | 'no_approve' - the ONE decision, pure (both modes share it, D-3036)."""
    if size > cap:
        return "oversized"
    if (rel, digest) in approved:
        return "ok"
    return "no_approve"


def staged_paths() -> list[str]:
    """The STAGED added/copied/modified/renamed paths (never deletions), read from git's own answer."""
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise SystemExit("FAIL-CLOSED: git diff --cached failed: " + (proc.stderr or "").strip())
    return [p for p in proc.stdout.splitlines() if p.strip()]


def staged_blob(rel: str) -> bytes:
    """The STAGED content of a path (the blob that would be committed), from the index, never the worktree."""
    proc = subprocess.run(["git", "cat-file", "blob", ":" + rel], capture_output=True)
    if proc.returncode != 0:
        raise SystemExit("FAIL-CLOSED: git cat-file blob :" + rel + " failed: "
                         + (proc.stderr or b"").decode(errors="replace").strip())
    return proc.stdout


def check_staged() -> int:
    """The live commit-boundary reading: every staged deep-tier file must carry a deep-reviewer APPROVE."""
    cfg = load_config()
    deep: dict = cfg["tiers"]["deep"]
    reviewer: str = str(deep["reviewer"])
    cap: int = int(deep["max_source_chars"])
    journal: Path = REPO / str(cfg["verdict_journal"])
    approved: set[tuple[str, str]] = approve_keys(journal, reviewer)
    problems: list[tuple[str, str, str]] = []
    checked: int = 0
    for rel in staged_paths():
        if tier_for(rel, cfg) != "deep":
            continue
        checked += 1
        blob: bytes = staged_blob(rel)
        digest: str = digest16(blob)
        verdict: str = classify(rel, digest, len(blob), cap, approved)
        if verdict != "ok":
            problems.append((rel, digest, verdict))
    if problems:
        print("FAIL R5 commit rail: " + str(len(problems)) + " of " + str(checked)
              + " staged deep-tier file(s) lack a deep-reviewer APPROVE (R5, BUG-1106):")
        for rel, digest, verdict in problems:
            if verdict == "oversized":
                print("  - " + rel + "  OVERSIZED (" + str(len(staged_blob(rel))) + " bytes > declared cap "
                      + str(cap) + "): no whole-file APPROVE is possible (BUG-746). Split it into R5-reviewable "
                      + "modules (T-221), then re-review the parts.")
            else:
                print("  - " + rel + "  no APPROVE from " + reviewer + " @sha256_16=" + digest
                      + "  -> run: python3 scripts/r5_review_gate.py --file " + rel)
        return 1
    print("ok R5 commit rail: " + str(checked) + " staged deep-tier file(s) carry an APPROVE from " + reviewer)
    return 0


def selftest() -> int:
    """Known-answer controls (D-355): a control must assert the state it is in. No git, no LLM, no network."""
    results: list[bool] = []

    def check(label: str, ok: bool, got: object) -> None:
        results.append(ok)
        print(("  PASS  " if ok else "  FAIL  ") + label + "  (" + str(got) + ")")

    check("digest16 is the first 16 hex chars of sha256 (matches the gate's identity)",
          digest16(b"abc") == hashlib.sha256(b"abc").hexdigest()[:16], digest16(b"abc"))

    # tier_for is imported (ONE home) - prove the declared mapping holds against the live config.
    cfg = load_config()
    check("scripts/* resolves to DEEP", tier_for("scripts/check_r5_verdicts.py", cfg) == "deep",
          tier_for("scripts/check_r5_verdicts.py", cfg))
    check("pipeline/* resolves to DEEP", tier_for("pipeline/stage2_extract.py", cfg) == "deep",
          tier_for("pipeline/stage2_extract.py", cfg))
    check("tools/* resolves to DEEP", tier_for("tools/relabel_depth_bias.py", cfg) == "deep",
          tier_for("tools/relabel_depth_bias.py", cfg))
    check("config/* resolves to FAST (catch-all)", tier_for("config/r5_review_gate.yaml", cfg) == "fast",
          tier_for("config/r5_review_gate.yaml", cfg))
    check("the declared deep reviewer is present in the config", bool(str(cfg["tiers"]["deep"]["reviewer"]).strip()),
          cfg["tiers"]["deep"]["reviewer"])

    # approve_keys over a synthetic journal (approve/reject/wrong-reviewer/malformed).
    reviewer = str(cfg["tiers"]["deep"]["reviewer"])
    tmp = Path(tempfile.mkdtemp(prefix="r5_commit_rail_selftest_")) / "journal.jsonl"
    tmp.write_text(
        json.dumps({"verdict": "APPROVE", "reviewer": reviewer, "file": "scripts/a.py", "sha256_16": "d1"}) + "\n"
        + json.dumps({"verdict": "REJECT", "reviewer": reviewer, "file": "scripts/b.py", "sha256_16": "d2"}) + "\n"
        + json.dumps({"verdict": "APPROVE", "reviewer": "gemma-4-E4B-it-MLX-4bit", "file": "scripts/c.py",
                      "sha256_16": "d3"}) + "\n"
        + "{not json}\n",
        encoding="utf-8")
    keys = approve_keys(tmp, reviewer)
    check("an APPROVE from the deep reviewer is a key", ("scripts/a.py", "d1") in keys, sorted(keys))
    check("a REJECT from the deep reviewer is NOT a key", ("scripts/b.py", "d2") not in keys, sorted(keys))
    check("an APPROVE from the FAST reviewer is NOT a deep key (no tier laundering)",
          ("scripts/c.py", "d3") not in keys, sorted(keys))
    check("a malformed journal line does not stop the scan (C16)", len(keys) == 1, sorted(keys))

    # classify: the pure decision shared by both modes.
    appr = {("scripts/a.py", "d1")}
    check("a matching APPROVE is 'ok'", classify("scripts/a.py", "d1", 1000, 100000, appr) == "ok",
          classify("scripts/a.py", "d1", 1000, 100000, appr))
    check("a changed digest is 'no_approve' (re-review owed)", classify("scripts/a.py", "dX", 1000, 100000, appr)
          == "no_approve", classify("scripts/a.py", "dX", 1000, 100000, appr))
    check("over the cap is 'oversized' (T-221), never silently passed",
          classify("pipeline/stage4_merge.py", "d9", 152966, 100000, appr) == "oversized",
          classify("pipeline/stage4_merge.py", "d9", 152966, 100000, appr))
    check("at/under the cap is reviewable (not oversized)",
          classify("scripts/a.py", "d9", 100000, 100000, appr) != "oversized",
          classify("scripts/a.py", "d9", 100000, 100000, appr))

    print("  controls " + str(sum(results)) + "/" + str(len(results)) + " held")
    return 0 if all(results) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--staged", action="store_true", help="the commit-boundary reading (staged deep-tier files)")
    ap.add_argument("--selftest", action="store_true", help="known-answer controls, no git, no LLM")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.staged:
        ap.error("one of --staged or --selftest is required")
    return check_staged()


if __name__ == "__main__":
    sys.exit(main())
