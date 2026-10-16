#!/usr/bin/env python3
"""apply_provider_flip.py — governed, backup-first edit of the harness home (config/agent_context.yaml#homes).

Implements the D-3023/D-3024 provider inversion in the SAFE order. There is no silent partial write: every edit
is a REGEX substitution that must match exactly ONCE, the file is backed up before the first write, the written
file is READ BACK (parsed) to prove the assignment is in effect, and `--rollback` restores the newest backup.
Default is `--dry-run` (no writes).

THREE FACTS ABOUT THIS WRITER, MEASURED 2026-10-16 (T-174/T-175, BUG-850/BUG-851/BUG-852):

  1. THE HOME IS DECLARED, NOT CONSTRUCTED. The client's home path used to be CONSTRUCTED here - a second answer
     to a question `config/agent_context.yaml#homes.harness_config` already answers. It is now RESOLVED from that
     declaration, and the client's own override variable (which the owner may set to point this writer at a
     fixture home) is kept as the one deliberate override. The same rule applies to the VALUES: nothing here
     restates a provider or a model name - those are pointers into
     config/engine.yaml#harnesses.goose_provider_id and config/model_assignments.yaml#harness_roles, so a swap
     moves the declaration and this writer follows. `--selftest` proves it by reading its own bytes.

  3. THIS FILE MOVED TO ITS DECLARED HOME (T-175/D-3046, MEASURED 2026-10-16). It lived in `pipeline/` - the
     deterministic core - while it edits ONE named client's configuration home, and the adapter surface's own
     rule says a harness-specific file belongs under `adapter.roots` or nowhere. The surface therefore reported
     it as an OWED binding site whose remedy was "read the home from the declared pointer": the reading landed,
     and the whole-file remedy was the move. The register now declares NO owed site at all, so the count the
     ladder prints is a MEASUREMENT rather than a promise - and this file may name its own client, which is
     exactly what an adapter home is for (D-3037/C12).

  2. ALREADY-APPLIED IS NOT DRIFT. The writer refused with "matched 0 time(s)" on a file that was ALREADY in
     the state it produces (two of four edits had been applied in an earlier session), so the honest state was
     unreadable. It now classifies each edit as PENDING / APPLIED / DRIFTED and refuses only on DRIFTED — an
     ambiguous anchor or a file in neither state. A writer over the owner's own home that cannot tell "done"
     from "broken" is a writer nobody can trust with a revert.

Phases:
  now  (safe, no flip): disable nvidia.enabled, lower GOOSE_THINKING_EFFORT.
  flip (owner's word):  pin the declared agent-loop model, then flip active_provider to the declared provider.

Usage:
  python3 apply_provider_flip.py                 # dry-run: print the plan, write nothing
  python3 apply_provider_flip.py --apply-now     # the safe phase only
  python3 apply_provider_flip.py --apply-flip    # the provider binding (T-174)
  python3 apply_provider_flip.py --apply-all     # both, in order
  python3 apply_provider_flip.py --rollback      # restore the newest backup
  python3 apply_provider_flip.py --selftest      # known-answer controls on a FIXTURE home (writes nothing of yours)

Exit: 0 ok | 1 FATAL (unreadable declaration, a DRIFTED anchor, an unreadable home) | --selftest 0/1.
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]   # agent/adapters/<client>/ -> the repository root
AGENT_CONTEXT = REPO / "config/agent_context.yaml"

#: WHAT THIS WRITER MAY SET — declared once, as POINTERS into the homes that own the facts (C12). A provider or
#: model name written here would be a second copy that silently disagrees the moment the declaration moves.
PROVIDER_POINTER = "@config/engine.yaml#harnesses.goose_provider_id"
AGENT_MODEL_POINTER = "@config/model_assignments.yaml#harness_roles.AGENT_LOOP_SHORT.model"
#: The two values that belong to THIS script's own safe phase (no config home declares them, and neither is a
#: provider or a model): the cloud accelerator is switched off and the thinking effort is lowered, because the
#: engine that answers locally does not bill per thought.
SAFE_NVIDIA_ENABLED = "false"
SAFE_THINKING_EFFORT = "medium"

CONTROL_LABELS = (
    "a_pending_edit_is_applied_and_changes_exactly_one_block",
    "an_already_applied_edit_is_NOT_reported_as_drift",
    "an_ambiguous_anchor_is_drift_and_refuses_the_write",
    "a_file_in_neither_state_is_drift_and_the_home_must_exist",
    "the_backup_is_written_before_the_first_byte_changes",
    "a_rollback_restores_the_bytes_the_edit_replaced",
    "the_writer_restates_no_provider_or_model_name_of_its_own",
    "the_written_file_is_read_back_and_the_assignment_is_in_effect",
)


def declared_home(env: dict[str, str] | None = None) -> Path:
    """The client home this writer edits, RESOLVED from its one declared home (T-175/BUG-850).

    An unreadable declaration is FATAL, never a default (C16/D-2644). `GOOSE_CONFIG` is a deliberate, explicit
    override — it exists so a control or a second client home can be pointed at — and it is the only reason a path
    literal may appear here at all.
    """
    override = (env if env is not None else os.environ).get("GOOSE_CONFIG")
    if override:
        return Path(override).expanduser()
    import yaml

    try:
        home = yaml.safe_load(AGENT_CONTEXT.read_text(encoding="utf-8"))["homes"]["harness_config"]
    except Exception as exc:  # noqa: BLE001 — any failure means this writer cannot know the home
        raise SystemExit(f"FATAL: {AGENT_CONTEXT}#homes.harness_config cannot be read "
                         f"({type(exc).__name__}: {exc}) — this writer must not guess the client home") from exc
    return Path(str(home)).expanduser()


def pointers() -> tuple[str, str]:
    """(provider id, agent-loop model) resolved from their declared homes — never restated (C12)."""
    sys.path.insert(0, str(REPO))
    from pipeline.harness_env import (
        resolve,  # the ONE pointer resolver (D-2646: never re-implement)
    )

    return resolve(PROVIDER_POINTER), resolve(AGENT_MODEL_POINTER)


def declared_edits(provider: str, model: str) -> list[tuple[str, str, str, str]]:
    """The edit list: (label, pattern, replacement, phase).

    The OLD side of an edit is a PATTERN, so the value being replaced is read from the file rather than copied
    into this script; the NEW side is the declared value. Both sides of the "now" phase are this writer's own
    policy constants (see SAFE_* above).
    """
    return [
        (f"pin {provider}.model to the declared agent_loop model",
         rf"(?m)^(  {re.escape(provider)}:\n(?:    [^\n]*\n)*?    model: )\S+$", rf"\g<1>{model}", "flip"),
        (f"flip active_provider to the declared provider ({provider})",
         r"(?m)^active_provider: .+$", f"active_provider: {provider}", "flip"),
        ("disable nvidia.enabled",
         r"(?m)^(  nvidia:\n(?:    [^\n]*\n)*?    enabled: )\S+$", rf"\g<1>{SAFE_NVIDIA_ENABLED}", "now"),
        ("lower GOOSE_THINKING_EFFORT",
         r"(?m)^(GOOSE_THINKING_EFFORT: ).+$", rf"\g<1>{SAFE_THINKING_EFFORT}", "now"),
    ]


def classify(content: str, edits: list[tuple[str, str, str, str]]) -> tuple[list[tuple[str, str, str]], list[str]]:
    """Per-edit state against the bytes on disk: PENDING, APPLIED, or DRIFTED (see the module docstring)."""
    pending: list[tuple[str, str, str]] = []
    problems: list[str] = []
    for label, pattern, replacement, _phase in edits:
        matches = len(re.findall(pattern, content))
        if matches == 0:
            problems.append(f"edit '{label}': the block it targets is NOT in the home - neither the state this "
                            f"edit expects nor the state it writes")
            continue
        if matches > 1:
            problems.append(f"edit '{label}': its anchor matches {matches} times - an ambiguous anchor is a "
                            f"drift, not a choice")
            continue
        if re.sub(pattern, replacement, content, count=1) == content:
            continue  # APPLIED: the home already says what this edit declares, and nothing is rewritten
        pending.append((label, pattern, replacement))
    return pending, problems


def _newest_backup(cfg: Path) -> Path | None:
    """Return the newest config.yaml.bak.* beside `cfg`, or None."""
    backups = sorted(cfg.parent.glob(f"{cfg.name}.bak.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    return backups[0] if backups else None


def _backup(cfg: Path) -> Path:
    """Copy the current config to a timestamped .bak and return its path."""
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    dst = cfg.parent / f"{cfg.name}.bak.{stamp}"
    dst.write_bytes(cfg.read_bytes())
    return dst


def _write(cfg: Path, content: str) -> None:
    """tempfile -> fsync -> os.replace (C6 crash-safe write)."""
    fd, tmp = tempfile.mkstemp(dir=str(cfg.parent), prefix=f"{cfg.name}.tmp.")
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, cfg)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def verify(cfg: Path, applied: list[tuple[str, str, str]]) -> list[str]:
    """READ THE WRITTEN FILE BACK: it must still parse, and every applied edit must be IN EFFECT.

    "In effect" is decided by the edit itself, not by a copy of the expected value: substituting the edit's own
    pattern with its own replacement must now be a NO-OP (the same test that classifies an edit as APPLIED). A
    write that is never read back is a claim, not a fact (D-3034) — and this writer edits the home a whole
    session's behaviour depends on, so the reading is part of the act.
    """
    import yaml

    text = cfg.read_text(encoding="utf-8")
    try:
        yaml.safe_load(text)
    except Exception as exc:  # noqa: BLE001 — an unparseable client home is the fault this check exists for
        return [f"the written home does not parse as YAML ({type(exc).__name__}: {exc})"]
    faults: list[str] = []
    for label, pattern, replacement in applied:
        matches = len(re.findall(pattern, text))
        if matches != 1 or re.sub(pattern, replacement, text, count=1) != text:
            faults.append(f"edit '{label}' is NOT in effect after the write ({matches} anchor(s) matched, "
                          f"substitution {'changed nothing' if matches == 1 else 'was not attempted'})")
    return faults


def binding_faults(cfg: Path, provider: str, model: str) -> list[str]:
    """The strong reading for the FLIP phase: the home must say the DECLARED provider and agent-loop model."""
    import yaml

    try:
        doc = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001
        return [f"the written home does not parse as YAML ({type(exc).__name__}: {exc})"]
    faults: list[str] = []
    if str(doc.get("active_provider")) != provider:
        faults.append(f"active_provider is {doc.get('active_provider')!r}, not the declared {provider!r}")
    pinned = str(((doc.get("providers") or {}).get(provider) or {}).get("model") or "")
    if pinned != model:
        faults.append(f"providers.{provider}.model is {pinned!r}, not the declared agent-loop model {model!r}")
    return faults


def apply_edits(edits: list[tuple[str, str, str, str]], dry_run: bool = False,
                cfg: Path | None = None, expect_binding: bool = False) -> int:
    """Apply (or plan) `edits` against the harness home. Refuses ONLY on a DRIFTED edit."""
    cfg = cfg or declared_home()
    if not cfg.exists():
        print(f"FATAL: {cfg} does not exist.", file=sys.stderr)
        return 1
    content = cfg.read_text()
    pending, problems = classify(content, edits)
    for problem in problems:
        print(f"FATAL: {problem}. Refusing to write.", file=sys.stderr)
    if problems:
        return 1
    if dry_run:
        print(f"DRY-RUN on {cfg}: {len(pending)} edit(s) to apply, {len(edits) - len(pending)} already applied:")
        for label, _pattern, _replacement in pending:
            print(f"  - {label}")
        return 0
    if not pending:
        print(f"OK: nothing to do — {cfg} already says what all {len(edits)} edit(s) declare.")
        return 0
    backup = _backup(cfg)
    print(f"backup: {backup}")
    for label, pattern, replacement in pending:
        content = re.sub(pattern, replacement, content, count=1)
        print(f"applied: {label}")
    _write(cfg, content)
    reading = verify(cfg, pending)
    if expect_binding:
        reading += binding_faults(cfg, *pointers())
    for fault in reading:
        print(f"FATAL (read back): {fault}", file=sys.stderr)
    if reading:
        print(f"the backup is intact: python3 {Path(__file__).name} --rollback", file=sys.stderr)
        return 1
    print(f"OK: {len(pending)} edit(s) applied to {cfg} and READ BACK in effect.")
    return 0


def rollback(cfg: Path | None = None) -> int:
    """Restore the newest backup beside `cfg`."""
    cfg = cfg or declared_home()
    backup = _newest_backup(cfg)
    if backup is None:
        print(f"FATAL: no backup beside {cfg} to roll back to.", file=sys.stderr)
        return 1
    _write(cfg, backup.read_text())
    print(f"OK: restored {cfg} from {backup.name}.")
    return 0


def _warn_flip() -> None:
    print("NOTE: the FLIP phase binds the everyday path to the engine that owns the models (T-174, owner word "
          "2026-10-16). What REMAINS open is T-137: the agent-loop model PIN and the tiered-cache A/B, which "
          "protect the per-turn BUDGET rather than the binding. Roll back in one command: "
          "--rollback.", file=sys.stderr)


def selftest() -> int:
    """Known-answer controls over a FIXTURE home — the writer is never exercised on the owner's file."""
    failures: list[tuple[str, str]] = []

    def mark(label: str, detail: str) -> None:
        failures.append((label, detail))

    old = "active_provider: vendor_a\n"
    new = "active_provider: vendor_b\n"
    edits = [("flip the provider", r"(?m)^active_provider: .+$", "active_provider: vendor_b", "flip")]
    body = "providers:\n  vendor_b:\n    enabled: true\n" + old
    with tempfile.TemporaryDirectory(prefix="provider_flip_") as tmp:
        cfg = Path(tmp) / "config.yaml"
        cfg.write_text(body, encoding="utf-8")
        if apply_edits(edits, dry_run=True, cfg=cfg) != 0:
            mark(CONTROL_LABELS[0], "a clean dry-run did not return 0")
        if cfg.read_text(encoding="utf-8") != body:
            mark(CONTROL_LABELS[0], "a DRY-RUN wrote to the home")
        if apply_edits(edits, dry_run=False, cfg=cfg) != 0:
            mark(CONTROL_LABELS[0], "the apply returned non-zero on a pending edit")
        text = cfg.read_text(encoding="utf-8")
        if text.count(new) != 1 or old in text:
            mark(CONTROL_LABELS[0], "the applied home does not carry the new block exactly once")

        # MEASURED 2026-10-16: this is the state the writer used to report as DRIFT (it was already applied).
        if apply_edits(edits, dry_run=False, cfg=cfg) != 0:
            mark(CONTROL_LABELS[1], "an ALREADY APPLIED edit was reported as drift")
        if cfg.read_text(encoding="utf-8") != text:
            mark(CONTROL_LABELS[1], "a no-op apply rewrote the home")

        ambiguous = Path(tmp) / "ambiguous.yaml"
        ambiguous.write_text(body + old, encoding="utf-8")
        before = ambiguous.read_text(encoding="utf-8")
        if apply_edits(edits, dry_run=False, cfg=ambiguous) == 0:
            mark(CONTROL_LABELS[2], "an anchor matching TWICE was applied")
        if ambiguous.read_text(encoding="utf-8") != before:
            mark(CONTROL_LABELS[2], "a refused write still changed the file")

        drifted = Path(tmp) / "drifted.yaml"
        drifted.write_text("providers: {}\n", encoding="utf-8")
        if apply_edits(edits, dry_run=False, cfg=drifted) == 0:
            mark(CONTROL_LABELS[3], "a home in NEITHER state was written")
        if apply_edits(edits, dry_run=True, cfg=Path(tmp) / "nope.yaml") == 0:
            mark(CONTROL_LABELS[3], "an ABSENT home did not refuse (a blind write)")

        backups = sorted(Path(tmp).glob("config.yaml.bak.*"))
        if len(backups) != 1:
            mark(CONTROL_LABELS[4], f"expected exactly one backup, found {len(backups)}")
        elif backups[0].read_text(encoding="utf-8") != body:
            mark(CONTROL_LABELS[4], "the backup does not hold the bytes that were replaced")
        if rollback(cfg=cfg) != 0 or cfg.read_text(encoding="utf-8") != body:
            mark(CONTROL_LABELS[5], "a rollback did not restore the pre-edit bytes")
        if rollback(cfg=Path(tmp) / "no_backups_here" / "config.yaml") == 0:
            mark(CONTROL_LABELS[5], "a rollback with no backup beside the home did not refuse")

        own = Path(__file__).read_text(encoding="utf-8")
        live_provider, live_model = pointers()   # the DECLARED facts, never a name written into this control
        leaks = [name for name in (live_provider, live_model)
                 if re.search(rf"['\"]{re.escape(name)}", own)]
        if leaks:
            mark(CONTROL_LABELS[6], f"the writer restates a declared provider or model name: {leaks}")
        for pointer in (PROVIDER_POINTER, AGENT_MODEL_POINTER):
            if pointer not in own:
                mark(CONTROL_LABELS[6], f"the declared pointer {pointer} is not what this writer resolves")

        pinned = Path(tmp) / "pinned.yaml"
        pinned.write_text("active_provider: vendor_b\nproviders:\n  vendor_b:\n    model: wrong-model\n",
                          encoding="utf-8")
        if not binding_faults(pinned, "vendor_b", "right-model"):
            mark(CONTROL_LABELS[7], "an assignment that is NOT in effect passed the read-back")
        pinned.write_text("active_provider: vendor_b\nproviders:\n  vendor_b:\n    model: right-model\n",
                          encoding="utf-8")
        if binding_faults(pinned, "vendor_b", "right-model"):
            mark(CONTROL_LABELS[7], "a correct assignment was reported as not in effect")
        broken = Path(tmp) / "broken.yaml"
        broken.write_text("active_provider: [unclosed\n", encoding="utf-8")
        if not binding_faults(broken, "vendor_b", "right-model"):
            mark(CONTROL_LABELS[7], "an unparseable home passed the read-back")
        in_effect = Path(tmp) / "in_effect.yaml"
        in_effect.write_text("active_provider: vendor_b\n", encoding="utf-8")
        if verify(in_effect, [("flip the provider", r"(?m)^active_provider: .+$", "active_provider: vendor_b")]):
            mark(CONTROL_LABELS[7], "an edit that IS in effect failed the generic read-back")
        if not verify(cfg, [("flip the provider", r"(?m)^active_provider: .+$", "active_provider: vendor_b")]):
            mark(CONTROL_LABELS[7], "an edit that is NOT in effect passed the generic read-back")
        if not verify(cfg, [("flip the provider", r"(?m)^active_provider: .+$", "active_provider: vendor_b")]):
            mark(CONTROL_LABELS[7], "an edit that is NOT in effect passed the generic read-back")

    failed = {label for label, _ in failures}
    for label in CONTROL_LABELS:
        print(f"  {'FAIL' if label in failed else 'ok  '} {label}")
    for label, detail in failures:
        print(f"CONTROL FAILED [{label}]: {detail}", file=sys.stderr)
    if failures:
        return 1
    print(f"selftest: {len(CONTROL_LABELS)}/{len(CONTROL_LABELS)} controls green")
    return 0


def main(argv: list[str]) -> int:
    mode = argv[0] if argv else "--dry-run"
    if mode == "--selftest":
        return selftest()
    if mode == "--rollback":
        return rollback()
    edits = declared_edits(*pointers())
    if mode == "--apply-now":
        return apply_edits([e for e in edits if e[3] == "now"], dry_run=False)
    if mode == "--apply-flip":
        _warn_flip()
        return apply_edits([e for e in edits if e[3] == "flip"], dry_run=False, expect_binding=True)
    if mode == "--apply-all":
        _warn_flip()
        return apply_edits(edits, dry_run=False, expect_binding=True)
    if mode in ("--dry-run", "-h", "--help"):
        print("DRY-RUN / usage:")
        print("  --apply-now   the safe phase (nvidia off, thinking effort lowered)")
        print("  --apply-flip  the provider binding (T-174)")
        print("  --apply-all   both, in order")
        print("  --rollback    restore the newest backup")
        print("  --selftest    known-answer controls on a FIXTURE home")
        return apply_edits(edits, dry_run=True)
    print(f"FATAL: unknown mode '{mode}'.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
