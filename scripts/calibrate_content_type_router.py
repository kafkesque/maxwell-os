#!/usr/bin/env python3
"""scripts/calibrate_content_type_router.py — TWO-SIDED calibration of the deterministic router (BUG-712).

WHY THIS EXISTS. `scripts/diff_bug712_reroute.py` reports how many stored rows DISAGREE with
`pipeline.content_types.reroute_content_type`. A diff alone cannot decide what to do with them:
it says nothing about whether the MOVES are correct (precision) or whether rows that should move
are MISSED (recall). BUG-712's remaining item is exactly that calibration, and applying a
governed re-stamp on an uncalibrated diff would write the router's errors into the store.

WHAT IT MEASURES (read-only, deterministic, LLM-FREE — D-343 forbids an LLM anywhere near
content_type, so the instrument carries no model either):

  SIDE A — PRECISION on the proposed moves.
    For every `principle -> growth_edge` move it locates the token that fired `_OPEN_TENSION` and
    classifies the USAGE in the sentence that contains it:
      claim_status   — the token is predicated of the CLAIM ITSELF ("the evidence is contested",
                       "findings remain unverified"): the tier-2 rule's intended meaning.
      subject_matter — the token describes the OBJECTS the FB is about ("contradictory
                       information", "contested identity"): a FALSE POSITIVE.
    A move is only a store defect if it is claim_status. Anything else is the router mislabelling
    a first-order predicate — the same defect class D-2949 fixed in `_DONE_CONDITION` (bare
    "until"/"gate") but did NOT fix in its sibling `_OPEN_TENSION`.

  SIDE B — RECALL on the rows the router leaves alone.
    Over the rows the router does NOT move, it counts how many carry a claim-status construction
    from a WIDER vocabulary than `_OPEN_TENSION` can express ("no consensus", "mixed evidence",
    "inconclusive", "preliminary", "speculative", ...). Those are rows the tier-2 rule MISSES:
    the recall cost of a token list this narrow.

VERDICT it supports: re-stamp NOW only if SIDE A is overwhelmingly claim_status. When it is not,
the ordering is router-precision first (owner-gated — content_type is S4-owned ontology, D-2933),
re-stamp second.

Usage:
    python3 scripts/calibrate_content_type_router.py            # human-readable, with samples
    python3 scripts/calibrate_content_type_router.py --json     # machine receipt
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.content_types import (  # noqa: E402 — the ONE router (C21) + its two SIDES
    principle_tension_hit,
    reroute_content_type,
)
from pipeline.pipeline_paths import DB_PATH  # noqa: E402

# The keys `_principle_form_violation` actually reads — kept IDENTICAL to it, including `name`
# (the diff instrument omitted `name`; measured 0 manifest effect on 2026-10-12, but a diff
# computed on a truncated haystack is not evidence).
_BODY_KEYS: tuple[str, ...] = ("definition", "mechanism", "boundary", "consequence", "elaboration")
_TYPE_BODY_KEYS: tuple[str, ...] = ("tool_name", "syntax", "parameters", "contested")

# The tokens `_OPEN_TENSION` can fire on, one regex each, so a move can name its own cause.
_OPEN_TENSION_TOKENS: dict[str, str] = {
    "contested": r"\bcontested\b",
    "contradict": r"\bcontradict\w*",
    "disputed": r"\bdisputed\b",
    "unverified": r"\bunverified\b",
    "unresolved": r"\bunresolved\b",
    "open question": r"\bopen question\b",
    "debated": r"\bdebated\b",
    "not_established": r"\bnot (yet )?(established|verified|proven)\b",
    "unknown whether": r"\bunknown whether\b",
    "correlation unproven": r"\bcorrelation .{0,20} unproven\b",
}

# CLAIM-STATUS constructions: the token is predicated of the claim/evidence, not of its subject.
_CLAIM_STATUS = re.compile(
    r"\b(is|are|was|were|remains?|seems?|appears?|becomes?)\s+(still\s+|widely\s+|highly\s+|"
    r"increasingly\s+)?(contested|disputed|unresolved|unverified|debated|uncertain|ambiguous)\b"
    r"|\b(claim|claims|evidence|finding|findings|result|results|consensus|literature|research|"
    r"study|studies|theory|hypothesis|knowledge|assumption|causal link|correlation)\b"
    r"[^.]{0,48}\b(contested|disputed|unresolved|unverified|debated|not (yet )?(established|verified|proven))\b",
    re.IGNORECASE,
)

# A WIDER epistemic vocabulary the token list cannot express — used to size the recall gap.
_WIDER_EPISTEMIC: dict[str, str] = {
    "no consensus": r"\bno (clear |general |broad )?consensus\b",
    "mixed evidence": r"\b(mixed|conflicting|inconsistent|inconclusive|contradictory) (evidence|findings|results|data)\b",
    "inconclusive": r"\binconclusive\b",
    "preliminary": r"\bpreliminary (evidence|findings|results|data)\b",
    "speculative": r"\bspeculative\b",
    "unproven": r"\bunproven\b",
    "disputed claim": r"\bdisputed (claim|finding|result|theory|hypothesis)\b",
    "open question": r"\bopen question\b",
    "not established": r"\bnot (yet )?(established|verified|proven)\b",
    "uncertain evidence": r"\b(evidence|evidence base|findings) (is|are|remains?) (uncertain|unclear|weak|thin)\b",
}


def _fb_from_row(row: sqlite3.Row) -> dict:
    """Reconstruct the S2-shaped dict the router expects — FAITHFUL to `_principle_form_violation`."""
    fb: dict = {"fb_id": row["fb_id"], "name": row["name"] or "", "content_type": row["content_type"]}
    for key in _BODY_KEYS:
        fb[key] = row[key] or ""
    if row["type_body"]:
        try:
            body = json.loads(row["type_body"])
        except (json.JSONDecodeError, TypeError):
            body = {}
        if isinstance(body, dict):
            for key in _TYPE_BODY_KEYS:
                if key in body:
                    fb[key] = body[key]
    return fb


def _haystack(fb: dict) -> str:
    """The exact haystack `_principle_form_violation` builds (definition + name/mechanism/...)."""
    return (
        str(fb.get("definition") or "")
        + " "
        + " ".join(str(fb.get(k) or "") for k in ("name", "mechanism", "boundary", "consequence", "elaboration"))
    ).lower()


def _sentence(text: str, start: int, end: int) -> str:
    """The full sentence around a match, for a human-checkable reason string."""
    left = max(text.rfind(".", 0, start), text.rfind("\n", 0, start))
    right = text.find(".", end)
    return text[left + 1 : right if right != -1 else min(len(text), end + 120)].strip()


# The vocabulary D-2949/D-2955 RETIRED ('system'/'framework' name software ARTIFACTS). Declared here as
# the instrument's KNOWN-ANSWER CONTROL — the same role the selftest controls play in
# scripts/check_config_duplicate_keys.py. It drives NOTHING; it exists so this side can state the full
# blast radius of the old rule (10 rows) beside the live one, instead of measuring only the survivors.
_RETIRED_KEYWORDS: tuple[str, ...] = ("system", "framework")


def side_c_ti_tier(rows: list[sqlite3.Row]) -> dict:
    """SIDE C — the tier-3 TI->process_template promotion, measured BOTH ways (D-2955/BUG-729).

    A name is a PRIOR; this side answers how many promotions survive when the BODY must also
    evidence a procedure. 'name_only' is the historical rule, 'with_evidence' the configured one.
    """
    from pipeline.content_types import TI_TO_PT_KEYWORDS, has_procedure_evidence  # noqa: PLC0415

    candidates = 0
    by_keyword: dict[str, int] = {}
    evidence = 0
    moves_name_only = 0
    moves_with_evidence = 0
    retired_hits = 0
    retired_with_evidence = 0
    for row in rows:
        if (row["content_type"] or "").strip() != "tool_instruction":
            continue
        fb = _fb_from_row(row)
        name = str(fb.get("tool_name") or "").strip().lower()
        # A DELETED keyword cannot fire, so the retired control is counted for EVERY TI row rather than
        # only for rows the live vocabulary matches — otherwise it would measure 0 and under-report the
        # very defect it exists to remember.
        if any(k in name for k in _RETIRED_KEYWORDS):
            retired_hits += 1
            if has_procedure_evidence(fb):
                retired_with_evidence += 1
        fired = [k for k in TI_TO_PT_KEYWORDS if k in name]
        if not fired:
            continue
        candidates += 1
        for key in fired:
            by_keyword[key] = by_keyword.get(key, 0) + 1
        moves_name_only += 1
        if has_procedure_evidence(fb):
            evidence += 1
            moves_with_evidence += 1
    return {
        "tool_instruction_rows": sum(1 for r in rows if (r["content_type"] or "").strip() == "tool_instruction"),
        "name_prior_candidates": candidates,
        "by_keyword": dict(sorted(by_keyword.items())),
        "body_evidence_pass": evidence,
        "moves_name_only": moves_name_only,
        "moves_with_evidence": moves_with_evidence,
        "retired_vocabulary_hits": retired_hits,
        "retired_with_body_evidence": retired_with_evidence,
    }


def side_d_token_field(rows: list[sqlite3.Row]) -> dict:
    """SIDE D — WHICH FIELD the tier-2 token sits in, and the strict form's residual leak.

    A boundary field exists to state where a claim does NOT hold, so an epistemic word there is
    structural to an honest principle rather than evidence that the record IS an open tension.
    This side sizes that leak so the next narrowing is a measurement, not a guess.
    """
    from pipeline.content_types import _OPEN_TENSION  # noqa: PLC0415

    fields = ("definition", "name", "mechanism", "boundary", "consequence", "elaboration")
    distribution: dict[str, int] = {}
    boundary_only = 0
    strict_survivors = 0
    strict_boundary_only = 0
    strict_names: list[str] = []
    for row in rows:
        fb = _fb_from_row(row)
        if not principle_tension_hit(fb, strict=False):
            continue
        where = [k for k in fields if _OPEN_TENSION.search(str(fb.get(k) or "").lower())]
        if where == ["boundary"]:
            distribution["boundary-only"] = distribution.get("boundary-only", 0) + 1
            boundary_only += 1
        elif "boundary" in where:
            distribution["boundary+other"] = distribution.get("boundary+other", 0) + 1
        else:
            distribution["elsewhere"] = distribution.get("elsewhere", 0) + 1
        if principle_tension_hit(fb, strict=True):
            strict_survivors += 1
            if where == ["boundary"]:
                strict_boundary_only += 1
            strict_names.append(str(row["name"]))
    return {
        "loose_fires": sum(distribution.values()),
        "distribution": distribution,
        "boundary_only": boundary_only,
        "strict_survivors": strict_survivors,
        "strict_boundary_only": strict_boundary_only,
        "strict_names": strict_names,
    }


def measure(conn: sqlite3.Connection) -> dict:
    """Run both calibration sides over the live store. Pure reads."""
    cols = ["fb_id", "name", "content_type", *_BODY_KEYS, "type_body"]
    rows = list(conn.execute(f"SELECT {', '.join(cols)} FROM fbs"))

    moves: list[dict] = []
    token_census: dict[str, int] = {}
    usage: dict[str, int] = {}
    samples: dict[str, list] = {"claim_status": [], "subject_matter": []}
    recall_hits: dict[str, int] = {}
    recall_samples: list[dict] = []

    for row in rows:
        fb = _fb_from_row(row)
        before = (row["content_type"] or "").strip()
        after = reroute_content_type(fb)
        hay = _haystack(fb)

        if after == before:
            # SIDE B — rows the router leaves alone: how many carry a MISSED epistemic signal?
            # GATED, and the gate IS the finding: a bare token is precisely the defect SIDE A
            # diagnoses, so a recall candidate must ALSO be a claim-status construction. Without
            # this gate the instrument repeats the router's error — the ungated run counted 77
            # "speculative" hits, nearly all of them ordinary adjectives ("over-investment in
            # speculative capabilities") and even a data-encoding term ("mixed data").
            for label, pattern in _WIDER_EPISTEMIC.items():
                match = re.search(pattern, hay, re.IGNORECASE)
                if not match:
                    continue
                sentence = _sentence(hay, match.start(), match.end())
                if not _CLAIM_STATUS.search(sentence):
                    continue
                recall_hits[label] = recall_hits.get(label, 0) + 1
                if len(recall_samples) < 8:
                    recall_samples.append({
                        "fb_id": row["fb_id"],
                        "name": row["name"],
                        "stored": before,
                        "signal": match.group(0),
                        "sentence": sentence,
                    })
            continue

        entry: dict = {"fb_id": row["fb_id"], "name": row["name"], "before": before, "after": after}
        if before == "principle" and after == "growth_edge":
            fired = None
            for label, pattern in _OPEN_TENSION_TOKENS.items():
                match = re.search(pattern, hay, re.IGNORECASE)
                if match:
                    fired = label
                    token_census[label] = token_census.get(label, 0) + 1
                    sentence = _sentence(hay, match.start(), match.end())
                    kind = "claim_status" if _CLAIM_STATUS.search(sentence) else "subject_matter"
                    entry.update({"token": label, "usage": kind, "sentence": sentence})
                    if len(samples[kind]) < 6:
                        samples[kind].append({"name": row["name"], "token": label, "sentence": sentence})
                    break
            usage[entry.get("usage", "no_token")] = usage.get(entry.get("usage", "no_token"), 0) + 1
            entry.setdefault("token", fired or "none")
        moves.append(entry)

    transitions: dict[str, int] = {}
    for move in moves:
        key = f"{move['before']}->{move['after']}"
        transitions[key] = transitions.get(key, 0) + 1

    principle_to_ge = [m for m in moves if m["before"] == "principle" and m["after"] == "growth_edge"]
    claim = usage.get("claim_status", 0)
    return {
        "rows": len(rows),
        "moves_total": len(moves),
        "transitions": dict(sorted(transitions.items())),
        "precision": {
            "principle_to_growth_edge": len(principle_to_ge),
            "claim_status": claim,
            "subject_matter": usage.get("subject_matter", 0),
            "false_positive_rate": round(1 - claim / max(1, len(principle_to_ge)), 3),
            "token_census": dict(sorted(token_census.items(), key=lambda x: -x[1])),
        },
        "recall": {
            "missed_rows_by_signal": dict(sorted(recall_hits.items(), key=lambda x: -x[1])),
            "total_missed": sum(recall_hits.values()),
        },
        "samples": samples,
        "recall_samples": recall_samples,
        "side_c_ti_tier": side_c_ti_tier(rows),
        "side_d_token_field": side_d_token_field(rows),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Two-sided calibration of the content_type router (BUG-712, read-only).")
    ap.add_argument("--json", action="store_true", help="machine-readable receipt")
    args = ap.parse_args()

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        out = measure(conn)
    finally:
        conn.close()

    if args.json:
        print(json.dumps(out, indent=2, default=str))
        return 0

    p = out["precision"]
    print(f"rows: {out['rows']} | proposed moves: {out['moves_total']}  {out['transitions']}")
    print(f"\nSIDE A — PRECISION of principle->growth_edge moves ({p['principle_to_growth_edge']}):")
    print(f"  claim_status (the rule's intended meaning): {p['claim_status']}")
    print(f"  subject_matter (FALSE POSITIVE):            {p['subject_matter']}")
    print(f"  false-positive rate: {p['false_positive_rate']:.1%}")
    print(f"  firing tokens: {p['token_census']}")
    for kind in ("subject_matter", "claim_status"):
        for sample in out["samples"][kind][:3]:
            print(f"    [{kind}] {str(sample['name'])[:40]!r} token={sample['token']}\n        ...{sample['sentence'][:130]}")
    print(f"\nSIDE B — RECALL: rows the router leaves alone that carry a wider epistemic signal ({out['recall']['total_missed']}):")
    for label, count in out["recall"]["missed_rows_by_signal"].items():
        print(f"  {count:5}  {label}")
    for sample in out["recall_samples"][:4]:
        print(f"    missed  {str(sample['name'])[:40]!r} signal={sample['signal']!r}\n        ...{sample['sentence'][:130]}")

    c = out["side_c_ti_tier"]
    print(f"\nSIDE C — TI->process_template tier (D-2955/BUG-729), measured BOTH ways:")
    print(f"  tool_instruction rows: {c['tool_instruction_rows']} | name-prior candidates: {c['name_prior_candidates']} {c['by_keyword']}")
    print(f"  body proves a procedure: {c['body_evidence_pass']}")
    print(f"  RETIRED vocabulary (control): {c['retired_vocabulary_hits']} row(s) named an artifact; "
          f"{c['retired_with_body_evidence']} of them would have survived the evidence gate")
    print(f"  promotions  name-only (gate OFF): {c['moves_name_only']}  ->  with body evidence (gate ON): {c['moves_with_evidence']}")
    d = out["side_d_token_field"]
    print(f"\nSIDE D — WHICH FIELD the tier-2 token sits in ({d['loose_fires']} loose fires): {d['distribution']}")
    print(f"  boundary-ONLY fires: {d['boundary_only']} (a boundary states where the claim does NOT hold)")
    print(f"  strict survivors: {d['strict_survivors']} of which boundary-only: {d['strict_boundary_only']}")
    for name in d["strict_names"][:6]:
        print(f"    strict survivor: {name[:56]!r}")
    print("\nVERDICT INPUT: re-stamp is justified only when claim_status dominates. Otherwise router precision comes first (owner-gated, D-2933).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
