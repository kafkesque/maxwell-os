"""transport_wall.py — the ONE derivation of a transport wall: a client may wait a little LONGER than the budget it
was given, never twice as long (BUG-1085, BUG-1088, D-3203 clause 5).

WHY THIS IS A MODULE AND NOT A LITERAL IN EACH CALLER. MEASURED 2026-10-27: `scripts/measure_subagent_loop.py` waited
`timeout=180` for a turn whose ratified budget was 90 s - exactly TWICE the wall - so a turn that ran 96.00 s was READ
as a turn and only the token allowance stopped it (BUG-1085). The same class was sitting one file away in
`pipeline/oneshot_ask.py:54`, which carried `timeout + 20`: a wall term that is TYPED, has no declared provenance and is
invisible to a caller reasoning about `--timeout` (BUG-1088). Paid twice because the first fix left the second path
alone, and the second path could not share the first's rule because the rule lived INSIDE a rail.

So the rule lives here, once (C12/D-2642): a wall is `budget + slack` with `0 < slack < budget`. The upper bound is the
whole point - a slack at or above the budget admits a turn that is 100% over its budget and still READ as a turn, which
is how 180 s became 2x a 90 s budget. The slack itself is not invented here: it is read from its declared home,
`config/agent_context.yaml#turn_budget.transport_slack_s`, whose comment records the measurement that set it (the
largest overshoot measured on this box is 6.0 s, and the slack is 2.5x that).

WHAT THIS IS NOT. It is not an allowance: it never grants tokens, never lengthens a turn, and never turns an exception
into a reading - a client that gives up at the wall reports NO reading (EXCEEDED), which is a fact about the client and
never a verdict about the model (D-3203).
"""
from __future__ import annotations

import pathlib
from typing import Any

REPO = pathlib.Path(__file__).resolve().parents[2]
CONFIG = REPO / "config/agent_context.yaml"


def config() -> dict[str, Any]:
    """The declared home of the transport wall, loaded here so a client cannot pass the WRONG config.

    MEASURED while landing BUG-1088: the first version took a caller-supplied dict, and `pipeline/oneshot_ask.py`
    - which loads `config/engine.yaml` for host/port - handed its ENGINE config to a reader looking for
    `turn_budget`, so the fail-closed branch fired for the wrong reason. A derivation that a caller can point at
    the wrong file is a derivation with a hole in it, so the home lives here and `read()` takes only the budget.
    """
    import yaml
    if not CONFIG.is_file():
        raise SystemExit(f"FATAL: {CONFIG.relative_to(REPO)} is absent - the transport wall's slack has no home to "
                         f"read (C12/C16)")
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}


def slack_s(cfg: dict[str, Any] | None = None) -> float:
    """The declared read-window, FAIL-CLOSED: a wall that cannot find its slack must not invent one (C12/C16)."""
    value = ((cfg if cfg is not None else config()).get("turn_budget") or {}).get("transport_slack_s")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise SystemExit("FATAL: config/agent_context.yaml#turn_budget.transport_slack_s is absent or not a "
                         "number - refusing to invent a transport wall (C12/C16, BUG-1085)")
    return float(value)


def wall(budget_s: float, slack: float) -> float:
    """`budget + slack`, and REFUSE a slack that is not strictly inside (0, budget) (BUG-1085/BUG-1088).

    The inequality is the part that cannot live in config: a config edit may change the slack, and this refuses any
    value that would restore a wall at or above twice the budget. A wall at 2x means a turn can be 100% over its
    budget and still be read as a turn - the fault both bugs are about.
    """
    try:
        budget_value, slack_value = float(budget_s), float(slack)
    except (TypeError, ValueError):
        raise SystemExit(f"FATAL: transport wall needs numeric budget and slack, got {budget_s!r} and {slack!r} - a "
                         f"wall derived from a non-number is not derived (C16)")
    if not (0 < slack_value < budget_value):
        raise SystemExit(f"FATAL: transport slack {slack_value:g}s is not inside (0, {budget_value:g}) - a slack "
                         f"that is not smaller than the budget reproduces BUG-1085's 180 s wall: a transport wall "
                         f"at 2x the budget means a turn can be 100% over its budget and still be READ as a turn")
    return budget_value + slack_value


def read(budget_s: float) -> float:
    """The wall for ONE completion, from the declared home - the call a client makes (BUG-1088).

    Takes ONLY the budget: the slack and the inequality come from their one home, so the two paths that used to
    disagree about how long a client may wait cannot disagree again.
    """
    return wall(budget_s, slack_s())
