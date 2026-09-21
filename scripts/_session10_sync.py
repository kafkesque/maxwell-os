#!/usr/bin/env python3
"""Session-10 governance sync (one-shot, idempotent).

Records D-317 (owner SIGNED the human attestation) across the governance dependency chain:
DECISION-LOG.md, config/decisions.yaml, CONTEXT_INDEX.md, SEQUENCE_STATUS_20260917.md,
MASTER-TASK-REGISTER.md, and the HUMAN GATE REGISTER row.

Idempotent: every block is skipped if its marker is already present. Writes via tempfile ->
fsync -> os.replace where the file is rewritten in place (C6).
"""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MARK = "D-317"

DECISION_LOG = """
## D-317 (2026-09-21, RATIFIED) — The human attestation is SIGNED: "human-anchored" is now EVIDENCE

**Context.** Every model-accuracy number in this repo is measured against 150 blind human labels
(`governance/anchor1_frozen_20260920.json`, `0ec321a7…`). The labels were human-blind *by construction* and the
label conversion was verifiable (0 CT diffs, 0 substantive DISC/FORM diffs vs the workspace), but the link between
the labels and a human author rested on reconstruction. A signed, scoped, hash-cited statement was the one missing
element — and it was the reason no claim here could honestly be called "attested".

**Decision.** The owner signed the reserved line on 2026-09-21:

> `human_attestation: "these 150 labels are mine, made blind to pipeline output."`

It is recorded machine-readably in `config/eval_integrity.yaml:ruler_authority.human_attestation` together with the
scope (n=150, 100 stratum A + 50 stratum B), the signer and the date, and the sha256 of the artifact it attests
(`governance/anchor1_frozen_20260920.json`, `0ec321a7…`).

**What it converts.** "human-anchored" moves from *verified-by-reconstruction* to **ATTESTED**. The owner gate that
reserved the line is CLOSED. Live owner gates drop from three to two: (1) the benchmark-only laya-mlx install in an
isolated venv with a pinned revision; (2) the abstention operating point `t_low = p25` (`enabled: false`).
No published number moves: re-scoring from the authority reproduces CT 0.3533 / DISC 0.4741 / FORM 0.2828 exactly.

**What it does NOT convert.** Attestation is not independence. `second_coder_required_before_repointing: true` still
has no second coder behind it (F-11), so NO floor may be repointed: every floor in this repo is single-coder, and is
now single-coder-*attested* rather than single-coder-unattested. The gap is smaller; it is not closed.

**Rule added.** D-317: an attestation is a **dated, scoped, hash-cited record** naming the exact artifact it
attests, and it lives machine-readably (config-first, C12). Prose may say "attested" only when such a record exists;
a bare quoted sentence is not an attestation. Corollary: when a human gate is closed, the artifact that recorded the
gate must be updated in the same session — a gate left "open" in config after it was answered is a governance
contradiction, not a conservative default.

**Not closed.** F-11 (no second coder), BUG-312 (three divergent label snapshots), BUG-341 (live stage5 checkpoint
absent), BUG-343 (smoke test cannot show its own failure output), BUG-344 (declared pins were not enforced in the
scorer run path — see below).

**Also recorded (same session).** BUG-344: `authority_paths()` never read the `*_sha256` fields declared in
`config/eval_integrity.yaml`, so the annotation drift guard shipped as a config declaration that the run path did
not enforce — the artifact cited an EMPTY `annotation_sha256`. Fixed by wiring the declared pins into the run path
fail-closed (C16); the artifact is regenerated and now cites the hash it actually consumed.
"""

CONTEXT_INDEX = """
## 2026-09-21 (session 10) — D-317: the human attestation is SIGNED (the evidence base is now attested)

The owner signed the reserved line: `human_attestation: "these 150 labels are mine, made blind to pipeline output."`
(2026-09-21). Recorded in `config/eval_integrity.yaml:ruler_authority.human_attestation` with scope n=150 (100 A +
50 B) and the attested artifact `governance/anchor1_frozen_20260920.json` (sha256 `0ec321a7…`).
Effect: "human-anchored" is **ATTESTED**, not merely verified-by-reconstruction; that owner gate is CLOSED and live
owner gates drop to TWO (laya-mlx benchmark-only install; abstention `t_low = p25`). No published number moves
(CT 0.3533 / DISC 0.4741 / FORM 0.2828, reproduced bit-identical from the authority). Attestation ≠ independence:
F-11 (no second coder) still forbids repointing any floor, and D-317 now requires that a closed gate be reflected in
config in the same session. BUG-344 opened+fixed: the declared pin hashes in config were never read by the scorer, so
the annotation drift guard was INERT in the run path and the artifact cited an empty hash.
"""

SEQUENCE_STATUS = """
### Session 10 update (2026-09-21) — D-317: the human attestation is SIGNED (owner gate CLOSED)
- **D-317 RATIFIED.** Owner signed `human_attestation: "these 150 labels are mine, made blind to pipeline output."`
  Recorded in `config/eval_integrity.yaml:ruler_authority.human_attestation` with the scope (n=150; 100 A + 50 B) and
  the attested artifact sha256 (`governance/anchor1_frozen_20260920.json`, `0ec321a7…`). "human-anchored" is now
  **ATTESTED**, not verified-by-reconstruction. No published number moves.
- **HUMAN GATES — now TWO live** (the signature gate is CLOSED):
  1. laya-mlx benchmark-only install, isolated venv, pinned revision — unchanged.
  2. abstention operating point `t_low = p25` (error 0.4231 at a ~25% queue; `enabled: false`) — unchanged.
  Plus G2..G7 in the register below; G4's *labelling* is done and its attestation is now signed.
- **NOT converted:** attestation is not independence. F-11 (`second_coder_required_before_repointing: true`, no second
  coder) still forbids repointing any floor. Every floor is single-coder, now single-coder-ATTESTED.
- **BUG-344 opened + FIXED:** the `*_sha256` pins declared in config were never read by `authority_paths()`, so the
  annotation drift guard was inert in the run path and the artifact cited an EMPTY `annotation_sha256`; declared pins
  are now enforced fail-closed and the artifact cites the hash it consumed.
- Carried, not dropped: BUG-341 (live stage5 checkpoint absent), BUG-343, BUG-312, F-11, 46 `config/*.bak_*` +
  32 `governance/*.bak_*` housekeeping debt (the only recovery copies; owner pass).
"""

MTR = """
- [x] Session 10 (2026-09-21): D-317 human attestation SIGNED by owner (config-first, hash-cited); owner gates 3 -> 2; BUG-344 (declared pins not enforced) FIXED.
- [ ] BUG-341 (OPEN, HIGH): re-run stage5 on the current S4 input (hours) -- until then the R2 corpus meter borrows the Sep-4 snapshot.
- [ ] BUG-343 (OPEN): capture the smoke subprocess stderr so the failure is diagnosable.
- [ ] F-11 (OPEN, methodological): recruit a SECOND coder on the 150 rows -- until then no floor may be repointed.
- [ ] MENU_REPAIR_WORKSHEET_20260921.md (OWNER, 13 + N rows, A/B): untouched (0 answers) -- blocks the menu repair apply.
"""

DECISIONS_ENTRY = """- id: D317
  category: EVALS
  state: RATIFIED
  date: "2026-09-21"
  title: >-
    The human attestation is SIGNED -- "human-anchored" becomes ATTESTED evidence (n=150, authority 0ec321a7...)
  decision: >-
    The owner signed the reserved line: "these 150 labels are mine, made blind to pipeline output." Recorded
    machine-readably in config/eval_integrity.yaml:ruler_authority.human_attestation with signer, date, scope (n=150;
    100 stratum A + 50 stratum B) and the attested artifact governance/anchor1_frozen_20260920.json (sha256
    0ec321a7...). This converts "human-anchored" from verified-by-reconstruction to ATTESTED and CLOSES the owner gate
    that reserved the line. Live owner gates: laya-mlx benchmark-only install; abstention operating point t_low=p25.
    No published number moves: CT 0.3533 / DISC 0.4741 / FORM 0.2828 reproduce exactly from the authority.
  rule_added: >-
    D-317: an attestation is a dated, scoped, hash-cited record naming the exact artifact it attests, stored
    machine-readably (C12); prose may say "attested" only when such a record exists. Closing a human gate requires
    updating the artifact that recorded the gate in the SAME session -- a gate left open after it was answered is a
    governance contradiction. Attestation is NOT independence: F-11 (no second coder) still forbids repointing any floor.
  also_recorded: >-
    BUG-344 (opened + fixed same session): authority_paths() never read the *_sha256 pins declared in
    config/eval_integrity.yaml, so the annotation drift guard was INERT in the run path and the artifact cited an
    empty annotation_sha256. Declared pins are now enforced fail-closed (C16) and the artifact cites the hash consumed.
"""


def append_once(path: Path, marker: str, block: str) -> bool:
    """Append `block` to `path` unless `marker` already appears. Returns True when written."""
    text = path.read_text(encoding="utf-8")
    if marker in text:
        print(f"SKIP (already present): {path.name}")
        return False
    with path.open("a", encoding="utf-8") as fh:
        fh.write(block if text.endswith("\n") else "\n" + block)
    print(f"APPENDED: {path.name}")
    return True


def insert_decision_entry(path: Path) -> bool:
    """Insert the D317 YAML entry immediately before the `summary:` block (unique anchor)."""
    text = path.read_text(encoding="utf-8")
    if f"\n- id: D317\n" in text:
        print("SKIP (already present): decisions.yaml D317")
        return False
    anchor = "\nsummary:\n"
    idx = text.rindex(anchor)
    new = text[:idx] + "\n" + DECISIONS_ENTRY + text[idx:]
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".decisions.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(new)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    print(f"INSERTED D317 at line {new[:idx].count(chr(10)) + 2}: {path.name}")
    return True


def mark_gate_register(path: Path) -> bool:
    """Mark the human-gate register so a reader cannot mistake the signature gate for open."""
    text = path.read_text(encoding="utf-8")
    old = "| **G4** | **Blind-label the certified eval core**, n=100-150, concentrated on `content_type` + `discipline` + FORM | sheet to be generated (next) | 6-10 h | **every** model-accuracy claim, the retrain, the role decisions |"
    if old not in text:
        print("SKIP (G4 row already updated or not found): SEQUENCE_STATUS register")
        return False
    new = (
        "| **G4** | **Blind-label the certified eval core**, n=100-150, concentrated on `content_type` + `discipline` + FORM "
        "**— LABELLED; attestation SIGNED 2026-09-21 (D-317)** | `governance/anchor1_frozen_20260920.json` "
        "(`0ec321a7…`) | done | still blocks: nothing — it *enables* every model-accuracy claim. "
        "Independence remains open (F-11: no second coder) |"
    )
    with path.open("w", encoding="utf-8") as fh:
        fh.write(text.replace(old, new, 1))
    print(f"UPDATED G4 row: {path.name}")
    return True


def main() -> int:
    """Run the idempotent governance sync and report what changed."""
    append_once(REPO / "DECISION-LOG.md", MARK, DECISION_LOG)
    append_once(REPO / "governance" / "CONTEXT_INDEX.md", MARK, CONTEXT_INDEX)
    append_once(REPO / "governance" / "SEQUENCE_STATUS_20260917.md", MARK, SEQUENCE_STATUS)
    append_once(REPO / "MASTER-TASK-REGISTER.md", MARK, MTR)
    mark_gate_register(REPO / "governance" / "SEQUENCE_STATUS_20260917.md")
    insert_decision_entry(REPO / "config" / "decisions.yaml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
