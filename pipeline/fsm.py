"""pipeline/fsm.py — deterministic finite-state-machine core (D-2948).

Grounded in research/STATE_MACHINES_GUARDRAILS_20261012.md:
  - Determinism IN THE CORE, non-determinism AT THE EDGES.
  - Pure functions only: ``next_state(state, event, table) -> state``. No I/O,
    no hidden mutable state, no model call. The transition TABLE is YAML
    (C12 config-first), so behaviour is DATA, not code.
  - NO external FSM library (XState/LangGraph REJECTED): a ~70-line auditable
    core is drift-proof and vendor-free (C2/C21); importing a framework would
    add hidden state and a dependency surface for no benefit at this scale.
  - Known-answer controls (self-tests) prove determinism and fail-closed
    behaviour at import time (C16: no silent undefined transitions).

Usage:
    from pipeline.fsm import next_state, load_transition_table
    table = load_transition_table("config/fsm/example.yaml")
    assert next_state("idle", "start", table) == "running"

A transition is DECLARED, never inferred: ``next_state`` raises ``TransitionError``
on an undeclared (state, event) pair, so a missing edge is a bug, not a default.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent


class TransitionError(KeyError):
    """An (state, event) pair with no declared transition (fail-closed, C16)."""


@dataclass(frozen=True)
class TransitionTable:
    """A validated, immutable FSM transition table (states, initial, transitions).

    Frozen by construction so a table loaded once can be shared across
    threads/processes without drift (C23: resilient by design).
    """

    states: frozenset[str]
    initial: str
    transitions: dict[tuple[str, str], str]  # (state, event) -> next_state

    def next(self, state: str, event: str) -> str:
        """Deterministic single-step transition (pure function)."""
        return next_state(state, event, self)


def build_table(doc: dict[str, Any]) -> TransitionTable:
    """Construct a validated TransitionTable from a raw YAML dict (C16 loud)."""
    if not isinstance(doc, dict):
        raise ValueError("FSM table must be a mapping")
    states = {str(s) for s in (doc.get("states") or [])}
    initial = str(doc.get("initial") or "")
    if initial and initial not in states:
        raise ValueError(f"initial state {initial!r} not in states")
    transitions: dict[tuple[str, str], str] = {}
    for t in doc.get("transitions") or []:
        src = str(t.get("state") or t.get("from") or "").strip()
        evt = str(t.get("event") or t.get("on") or "").strip()
        dst = str(t.get("next") or t.get("to") or "").strip()
        if not src or not evt or not dst:
            raise ValueError(f"malformed transition: {t!r}")
        if src not in states or dst not in states:
            raise ValueError(f"transition {src}--{evt}->{dst} names an undeclared state")
        key = (src, evt)
        if key in transitions:
            raise ValueError(f"duplicate transition for {key}")
        transitions[key] = dst
    if not transitions:
        raise ValueError("FSM table has no transitions")
    return TransitionTable(states=frozenset(states), initial=initial, transitions=transitions)


def load_transition_table(path: str | Path) -> TransitionTable:
    """Load + validate a YAML transition table, failing closed on any defect."""
    return build_table(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def next_state(state: str, event: str, table: TransitionTable) -> str:
    """Return the next state for (state, event) — pure, deterministic, fail-closed."""
    key = (str(state), str(event))
    try:
        return table.transitions[key]
    except KeyError:
        raise TransitionError(
            f"undeclared transition: {state!r} --{event!r}-> ? "
            f"(states={sorted(table.states)})"
        ) from None


def _selftest() -> None:
    """Known-answer controls: determinism + fail-closed behaviour, proven at import."""
    table = build_table({
        "states": ["idle", "running", "done"],
        "initial": "idle",
        "transitions": [
            {"state": "idle", "event": "start", "next": "running"},
            {"state": "running", "event": "finish", "next": "done"},
            {"state": "running", "event": "fail", "next": "idle"},
        ],
    })
    assert table.initial == "idle"
    assert next_state("idle", "start", table) == "running"
    assert next_state("running", "finish", table) == "done"
    assert next_state("running", "fail", table) == "idle"
    for _ in range(3):  # determinism: repeated calls are identical
        assert next_state("idle", "start", table) == "running"
    try:  # fail-closed: an undeclared edge raises, never a silent default
        next_state("done", "start", table)
    except TransitionError:
        pass
    else:
        raise AssertionError("undeclared transition did not raise TransitionError")


_selftest()


if __name__ == "__main__":
    print("pipeline/fsm.py selftest: OK (determinism + fail-closed verified)")
