#!/usr/bin/env python3
r"""One-shot repair: BUG-652..656 were appended as bare `| BUG-NNN |` table rows at the
BOTTOM of buglog.md, with NO `## BUG-NNN` heading section. bug_status.py's HEADER_RE only
sees `## / ### BUG-NNN` headings, so those five bugs are INVISIBLE to the canonical status
register (C15 undercount) and to the session_seed registry. Convert them to proper heading
sections (reordered 652..656) and append BUG-657 (the guard gap). Crash-safe write (C6).
"""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

BUGLOG = Path("governance/buglog.md")

NEW_SECTIONS = """## BUG-652 (RESOLVED, 2026-10-06) — scripts/rederive_anchor_axes_v6.py `--run-id` flag was DEAD (parsed but never used)

`--run-id` was parsed but never used (all path helpers + `finalize_manifest` artifact_id hardcoded `_run_id()`).
The `--finalize` error said "use --run-id for a new run" while the flag silently did nothing, blocking any same-day
re-mint behind the I2 mint-once guard. RESOLVED 2026-10-06 (D-2848): run_id threaded through path helpers +
`finalize_manifest` (default `_run_id()`) + fail-closed path-separator validation; `--selftest` passed before/after.

## BUG-653 (RESOLVED, 2026-10-06) — off-menu discipline rejection lacked a domain-axis hint + closest-discipline suggestion

Repeated owner off-menu trap: domain-only labels proposed as disciplines. After `design strategy`/`design system(s)`
(earlier), owner proposed `urban planning` as R183's discipline; menu-v6 has it ONLY on the domain axis (44), not
the discipline axis (65), so `--adjudicate` fail-closed C16 rejects it. Root cause: the off-menu rejection error
names the invalid label but does NOT check the domain axis nor suggest closest valid disciplines, forcing owner
round-trips. RESOLVED 2026-10-06: `validate_on_menu` now routes off-menu disciplines through `_off_menu_discipline_hint`,
which (a) detects when the label is a DOMAIN-axis value and calls out the axis confusion, (b) suggests the 4 closest
on-menu disciplines (token-overlap + difflib ratio, deterministic, no LLM), and (c) reminds of the `emerging`
abstention token. Selftest passes.

## BUG-654 (CLOSED, 2026-10-06) — D-2767 full-201 A/B FAILED (kappa 0.3181 < 0.800 floor); SUPERSEDED by BUG-655

The SAME gpt-oss-20b-MXFP4-Q8 model, SAME prompt, IDENTICAL input (202/202 definition match vs maxwell.db), run twice
against the SAME owner referee 20261006d produced kappa 0.7794 (D-2820 `--generate`, worklist 20261005
candidate_discipline) vs 0.3181 (A/B fresh re-run) — a 0.46 run-to-run swing at temp=0.0. SUPERSEDED 2026-10-06:
this was MISDIAGNOSED as model non-determinism — see BUG-655. The real root cause is a two-prompt measurement bug
(the rederive `_classify_prompt` vs the production `build_merged_prompt`), NOT residual CoT/non-determinism.
Deterministic settings were already in place (D-2637 server + config verifier levers); a 2-pass byte-identity check
confirms greedy temp=0.0 is deterministic.

## BUG-655 (OPEN, 2026-10-06) — the 0.46 "kappa swing" is a MEASUREMENT BUG (two prompts), NOT non-determinism

Re-audit: the two kappa numbers come from TWO DIFFERENT PROMPTS, not two runs of one prompt. (a) kappa 0.3181 =
`d2767_ab_eval.py` run_inference -> `merged_cribs_classify` -> `build_merged_prompt` (free-gen cribs path;
`definition_anchored_menu_enabled: false`). (b) kappa 0.7794 = rederive `--generate` -> `_classify_prompt` +
`definition_anchored_block()` (the flag-ON definition-anchored menu, the SAME block `_apply_definition_anchored_menu`
injects when the flag is true). They measure the OFF vs ON arms of the ONE `definition_anchored_menu_enabled` flag.
Deterministic settings ARE in place AND applied: D-2637 server (temp 0.0, cache on, guided_grammar on) + config
verifier (enable_thinking=false, thinking_budget 256/128, Reasoning:low prefix). Empirical: temp=0.0 greedy
byte-identical. REAL RESULT: flag-ON definition-anchored kappa = 0.7794 (158/201), emerging 6/201 = 0.03 — still 2pt
below the 0.800 floor, so the flip STILL does not happen, for a genuine classifier-vs-owner gap (~43 rows), NOT
determinism. OPEN (replaces BUG-654 as the A/B blocker).

## BUG-656 (OPEN, 2026-10-06) — the 0.7794 "flag-ON" kappa is the REDERIVE path, NOT the production gate arm

Re-audit: the two "flag-ON" prompts DIFFER — (a) rederive `--generate` -> `_classify_prompt` (discipline+domains
only, 2 output fields, menu in the USER prompt) = kappa 0.7794 / 43 disagreements; (b) production
`definition_anchored_menu_enabled: true` -> `_apply_definition_anchored_menu(MERGED_CRIBS_CLASSIFY_SYSTEM)` +
`build_merged_prompt` (full enrich+classify, 10 output fields, menu in the SYSTEM prompt) = the REAL D-2839 gate arm,
whose kappa was NOT what 0.7794 measured. Smoke test proved divergence: R001 agrees on the rederive path but predicts
'marketing' (a DOMAIN label leaking into discipline) on the production path. FIX: `d2767_ab_eval.py` now persists
per-row gold/pred/agree AND emits a beginner-friendly owner-review CSV (`*_disagreements.csv`) so the owner reviews
PRODUCTION-path rows. Determinism self-check 3/3 byte-identical. Definitive production-path kappa pending full-201 run
(governance/d2767_ab_flagon_20261006d.json). OPEN.

## BUG-657 (OPEN, 2026-10-06) — bare `| BUG-NNN |` table rows without a `## BUG-NNN` heading are INVISIBLE to bug_status.py

BUG-652..656 were appended to buglog.md as bare `| BUG-NNN |` table rows at the BOTTOM, with no `## BUG-NNN` heading
section. `bug_status.py` HEADER_RE matches only `^#{2,3} BUG-NNN` headings, so those five bugs never entered the
canonical status register (bug_status.json) — total_ids=390, open_n=145, highest=BUG-651 — while session_seed was
hand-bumped to highest_bug=BUG-656. Consequence: C15 handoff undercounts unresolved bugs (misses BUG-655/656 as OPEN)
and the session_seed registry drifts from the recomputable source. The coverage guard `check_buglog_coverage.py`
passes (532 blocks) because it only checks heading->parser, NOT the reverse (table-row->heading) — an asymmetric
blind spot (BUG-428 class). FIX: (1) convert BUG-652..656 to `## BUG-NNN` heading sections (done this session);
(2) extend `check_buglog_coverage.py` to fail-closed on any `| BUG-NNN |` summary-table row lacking a `## BUG-NNN`
heading; (3) re-sync session_seed registry from bug_status.json (recomputable, not hand-bumped). OPEN.
"""


def main() -> int:
    text = BUGLOG.read_text(encoding="utf-8")

    # Remove the 5 bare table rows (each is a single long line, reorder-insensitive).
    ids = ("652", "653", "654", "655", "656")
    lines = text.split("\n")
    kept: list[str] = []
    removed = 0
    for line in lines:
        m = re.match(r"^\| BUG-(65[2-6]) \|", line)
        if m:
            removed += 1
            continue
        kept.append(line)
    if removed != 5:
        raise SystemExit(f"expected 5 bare rows, removed {removed} — abort (no write)")

    # Re-join; this also collapses any now-dangling blank line before the block end.
    text = "\n".join(kept)

    # Insert the new sections immediately after the BUG-651 section's last line.
    # Anchor: the last line of BUG-651 prose ends with "rechunk-v4-20260929."
    anchor = "then re-run S5 on rechunk-v4-20260929."
    if anchor not in text:
        raise SystemExit("BUG-651 prose anchor not found — abort (no write)")
    insert_at = text.index(anchor) + len(anchor)
    # keep the trailing newline of the anchor line, then one blank line, then sections.
    text = text[:insert_at] + "\n\n" + NEW_SECTIONS.rstrip("\n") + "\n" + text[insert_at:]

    # Crash-safe write (C6).
    fd, tmp = tempfile.mkstemp(dir=str(BUGLOG.parent), prefix=".buglog.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, str(BUGLOG))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

    print(f"removed {removed} bare rows; wrote {len(NEW_SECTIONS.splitlines())} new section lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
