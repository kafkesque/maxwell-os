"""pipeline/dedup_gate.py — commit-time dedup DECISION (pure, deterministic, LLM-free).

Companion to pipeline/dedup_identity.py (D-2950). dedup_identity CLASSIFIES a group;
this module DECIDES what to do with ONE incoming candidate fb and APPLIES nothing itself.

Two vocabularies, one hop apart (keep them straight when reading a receipt):

  classify_group (identity)      candidate_kind (commit disposition)
  merge                     ->   merge_convergent        same name + same work, convergent
                                                         body -> LINK (enforce) or insert
  same_source_collide       ->   keep_both_divergent     one work, two concepts, one name
  name_collide              ->   keep_both_cross_source  two works, one name
  no_source                 ->   review                  provenance unknown -> owner
  (no members)              ->   insert                  nothing to collide with

CommitDedupGate (D-2951) is the wired form of that decision at the S6 boundary:
  mode=report   every decision is computed, recorded in checkpoint/dedup_gate_receipt.json,
                and NOTHING is changed (the default: evidence before enforcement).
  mode=enforce  additionally EXECUTES "mark duplicate_of + QUARANTINE, NEVER delete"
                (D2625/D2630) for a convergent re-extraction whose incumbent is the richer
                row. A candidate richer than the incumbent is reported as a supersede
                candidate instead (a commit never rewrites an existing row — D-2933 rule V).

richness() implements the owner's "keep richer" rule deterministically: more filled
body fields + higher confidence + more source diversity wins. No LLM anywhere (D-343).
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from pipeline.dedup_identity import (
    body_text,
    classify_group,
    jaccard,
    normalize_name,
    seq_ratio,
    source_set,
)

# Owner-named body fields that count toward "richer text" (BUG-725/duplicate ruling).
BODY_FIELDS = (
    "definition", "mechanism", "consequence", "boundary",
    "failure_mode", "elaboration", "jargon", "evidence_passages",
)

# The commit disposition vocabulary — ONE home (C21). dedup_identity.classify_group answers in
# ITS vocabulary ("merge"/"same_source_collide"/...) and candidate_kind translates. Spelling a
# disposition as a literal anywhere else is how a receipt silently reported 0 advisories while
# its own `kinds` block reported 2 (measured 2026-10-12 by scripts/simulate_commit_dedup_gate).
DISPOSITION_INSERT = "insert"
DISPOSITION_MERGE = "merge_convergent"
DISPOSITION_DIVERGENT = "keep_both_divergent"
DISPOSITION_CROSS_SOURCE = "keep_both_cross_source"
DISPOSITION_REVIEW = "review"

# classify_group -> candidate_kind (the single translation table)
_IDENTITY_TO_DISPOSITION = {
    "merge": DISPOSITION_MERGE,
    "same_source_collide": DISPOSITION_DIVERGENT,
    "name_collide": DISPOSITION_CROSS_SOURCE,
    "no_source": DISPOSITION_REVIEW,
}


def _nonempty(value: object) -> bool:
    if value is None:
        return False
    s = str(value).strip()
    return s not in ("", "[]", "{}", "null", "None")


def richness(fb: dict) -> int:
    """Deterministic 'richer text' score: filled body fields + diversity + confidence."""
    score = 0
    for field in BODY_FIELDS:
        if _nonempty(fb.get(field)):
            score += 1
    if _nonempty(fb.get("source_diversity")):
        score += 1
    if fb.get("confidence_score") is not None:
        score += 1
    return score


def candidate_kind(candidate: dict, existing: list[dict]) -> str:
    """Decide the commit-time disposition of `candidate` against `existing` committed rows.

    `existing` must be the committed rows whose normalize_name(name) equals the
    candidate's (the gate computes the group key upstream). Returns one of the five
    decision strings documented at module top.
    """
    if not existing:
        return DISPOSITION_INSERT
    kind = classify_group(list(existing) + [candidate])
    return _IDENTITY_TO_DISPOSITION.get(kind, DISPOSITION_REVIEW)


def pick_richer(candidate: dict, existing: list[dict]) -> dict:
    """Return the richer row among a convergent-merge group (candidate + existing).

    Ties (equal richness) resolve to the EXISTING row (stability: never churn a
    committed row for an equal-score re-extraction).
    """
    pool = list(existing) + [candidate]
    best = max(pool, key=lambda fb: (richness(fb), fb.get("confidence_score") or 0))
    return best


def group_key(name: str, source_ids: frozenset[str]) -> tuple[str, frozenset[str]]:
    """The commit-time dedup grouping key = (normalized name, source identity set)."""
    return (normalize_name(name), frozenset(source_ids or frozenset()))


# ── the marker column's ONE shape (BUG-498 class: a claim the code cannot keep) ─────────────

def duplicate_marker(value: object) -> str | None:
    """Normalize a stored `duplicate_of` cell to ONE shape: a fb_id, or None.

    The writer has always mapped an absent marker to `''` (`_safe_str(None)` -> `""`), so the
    predicate DOCUMENTED by D-271d — `duplicate_of IS NULL` — matched ZERO rows: every row read
    as "marked". Readers go through here, so `''` and `NULL` mean the same thing (absent) for a
    row written before or after the D-2951 writer fix, and the column can become load-bearing
    without a two-shape store.
    """
    if value is None:
        return None
    text = str(value).strip()
    return text or None


IDENTITY_COLUMNS: tuple[str, ...] = (
    "fb_id", "name", "definition", "mechanism",
    "source_ids", "source_diversity", "confidence_score",
)


def load_committed_index(conn: Any) -> dict[str, list[dict]]:
    """Index the committed store by normalize_name(name) — the gate's "existing" side.

    `conn` is anything with `.execute(sql)` yielding sequences (a sqlite3 connection, or a double
    in tests): the gate stays independent of the store's driver (C21) and of its row_factory.
    """
    cursor = conn.execute(f"SELECT {', '.join(IDENTITY_COLUMNS)} FROM fbs")
    names = [d[0] for d in cursor.description]
    index: dict[str, list[dict]] = {}
    for values in cursor:
        row = dict(zip(names, values))
        index.setdefault(normalize_name(str(row["name"] or "")), []).append(row)
    return index


class CommitDedupGate:
    """The commit-time dedup gate: ONE deterministic decision per incoming candidate FB.

    "Existing" has TWO sides — the committed store (loaded once) and the rows this batch has
    already accepted — so a collision created WITHIN one run is caught as well as a collision
    with the store (D-2949 #4: stage1 dedups segments, nothing dedups NAMES at commit).

    Pure, deterministic and LLM-free (D-343); every threshold comes from
    config/dedup_identity.yaml (C12). The gate only ever DECIDES; the caller applies.
    """

    MODES: tuple[str, ...] = ("report", "enforce")

    def __init__(self, committed: dict[str, list[dict]], mode: str = "report") -> None:
        if mode not in self.MODES:
            raise ValueError(
                f"dedup gate: unknown mode {mode!r} — expected one of {self.MODES} (C16 fail-closed)"
            )
        self.mode = mode
        self._store: dict[str, list[dict]] = {k: list(v) for k, v in committed.items()}
        self._stored_rows = sum(len(v) for v in self._store.values())
        self._accepted: dict[str, list[dict]] = {}
        self.decisions: list[dict] = []

    @property
    def stored_rows(self) -> int:
        """Committed rows the index holds."""
        return self._stored_rows

    @property
    def stored_names(self) -> int:
        """Distinct normalized names the index holds."""
        return len(self._store)

    def _existing(self, norm: str) -> list[dict]:
        return list(self._store.get(norm, [])) + list(self._accepted.get(norm, []))

    def decide(self, fb: dict) -> dict:
        """Classify ONE incoming candidate and return its decision record.

        `action` is what the CALLER must do under the configured mode; `would` is what
        `enforce` would do, so a report-mode receipt states the enforcement it is declining.
        A candidate richer than the incumbent is NEVER linked: demoting the store's richer row
        is a supersession act and stays an owner call (D-2933 rule V / D-2950 pending ruling).
        """
        norm = normalize_name(str(fb.get("name") or ""))
        existing = self._existing(norm)
        kind = candidate_kind(fb, existing)
        canonical = pick_richer(fb, existing) if kind == "merge_convergent" else None
        candidate_richer = bool(canonical is fb) if canonical is not None else False
        linkable = kind == "merge_convergent" and not candidate_richer
        decision: dict[str, Any] = {
            "fb_id": str(fb.get("fb_id") or ""),
            "name": str(fb.get("name") or ""),
            "normalized_name": norm,
            "kind": kind,
            "mode": self.mode,
            "action": "link_duplicate" if (linkable and self.mode == "enforce") else "insert",
            "would": "link_duplicate" if linkable else ("supersede_review" if candidate_richer else "insert"),
            "existing_count": len(existing),
            "candidate_richer": candidate_richer,
            "canonical_fb_id": str(canonical.get("fb_id") or "") if canonical is not None else None,
            "status_in": str(fb.get("status") or ""),
        }
        if canonical is not None:
            a, b = body_text(fb), body_text(canonical)
            decision["evidence"] = {
                "jaccard": round(jaccard(a, b), 4),
                "seq_ratio": round(seq_ratio(a, b), 4),
                "richness_candidate": richness(fb),
                "richness_canonical": richness(canonical),
            }
        self.decisions.append(decision)
        return decision

    def observe(self, fb: dict) -> None:
        """Record a row that IS now in the store, so later candidates see it (batch side)."""
        norm = normalize_name(str(fb.get("name") or ""))
        self._accepted.setdefault(norm, []).append({
            "fb_id": fb.get("fb_id"),
            "name": fb.get("name"),
            "definition": fb.get("definition", ""),
            "mechanism": fb.get("mechanism", ""),
            "source_ids": source_set(fb.get("source_ids")),
            "source_diversity": fb.get("source_diversity"),
            "confidence_score": fb.get("confidence_score"),
        })

    def receipt(self) -> dict:
        """The auditable summary of this run's decisions (C16: no silent verdict).

        Advisories are the decisions that need a HUMAN: a divergent same-name pair (disambiguate
        the names — owner-gated, D-271a), a candidate richer than the incumbent (supersede), and
        a blank-source group (unjudgeable). Linking needs no owner, and is listed for audit only.
        """
        kinds = Counter(d["kind"] for d in self.decisions)
        actions = Counter(d["action"] for d in self.decisions)
        linked = [d for d in self.decisions if d["action"] == "link_duplicate"]
        return {
            "gate": "commit_dedup_gate",
            "decision": "D-2951",
            "mode": self.mode,
            "identity_model": "D-2950 (normalize_name, source_ids) + body-divergence merge gate",
            "store_rows_indexed": self._stored_rows,
            "store_names_indexed": len(self._store),
            "candidates": len(self.decisions),
            "kinds": dict(sorted(kinds.items())),
            "actions": dict(sorted(actions.items())),
            "linked_duplicates": linked,
            "advisories": {
                DISPOSITION_DIVERGENT: [d for d in self.decisions if d["kind"] == DISPOSITION_DIVERGENT],
                DISPOSITION_CROSS_SOURCE: [d for d in self.decisions if d["kind"] == DISPOSITION_CROSS_SOURCE],
                DISPOSITION_REVIEW: [d for d in self.decisions if d["kind"] == DISPOSITION_REVIEW],
                "supersede_candidates": [d for d in self.decisions if d["candidate_richer"]],
            },
        }
