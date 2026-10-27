"""artifact_tokens.py — the ONE definition of "a token that names a repo artifact" (D-3212, D-2642).

WHY THIS EXISTS AS A MODULE AND NOT AS TWO CONSTANTS. Two readers need this pattern for the SAME fact ("which
artifact does this text name"): the bug CENSUS (scripts/bug_status.py, which owns the parsing of
governance/buglog.md and therefore owns what a bug's evidence NAMES) and the ROUTE GRAPH
(scripts/resolve_route.py, which decides which capability owns an open item). A second copy of the pattern is the
two-homes defect (D-2642) and it is the copy that goes stale: the census would publish a token the rail does not
recognise, or the rail would recognise one the census never emits, and neither would report a disagreement — the
item would simply read as unrouted, which is a number no reader can tell from real debt.

The pattern is deliberately identical to the one resolve_route.py carried before D-3212 (byte-for-byte), so this
module changes no verdict on any text; it only moves the definition to a home both readers can import.
"""
from __future__ import annotations

import re

#: A path-shaped token ending in one of the repo's declared artifact extensions. NOT anchored to the repo root,
#: because evidence prose legitimately cites a bare basename (`feedback.py`) and the ownership declaration may own
#: it under a directory. Whether a token RESOLVES to an owner is the rail's judgement, never this pattern's.
ARTIFACT = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:py|ya?ml|json|md|sh|jsonl|txt)")


def tokens(text: str) -> list[str]:
    """Every DISTINCT artifact-shaped token in one text, sorted — sorted because a report that re-orders itself on
    an unchanged world is a report that cannot be compared with itself (BUG-597's lesson)."""
    return sorted(set(ARTIFACT.findall(text or "")))
