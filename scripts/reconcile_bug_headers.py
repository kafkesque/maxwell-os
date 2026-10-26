#!/usr/bin/env python3
"""T-104 limb (b) reconciliation PROPOSAL — dry-run, read-only.

Reads the authoritative 98 UNLABELLED open bugs (gov_sync.severity_census) and the
event-aware register (bug_status.scan), then proposes, per bug, ONE of:

  PROMOTE   - authoritative body carries a **Severity:** label  -> lift it to the heading slot
  CLOSE     - authoritative body carries a **Status:** FIXED/RESOLVED/TOMBSTONED label
  AMBIGUOUS - neither label on the authoritative body -> needs owner/delegate judgement

Writes NOTHING to the buglog. Emits temp/t104_limb_b_reconciliation.json + a table.
The --apply step (which rewrites headings) is a SEPARATE, owner-gated implementation;
this module is the read-only face of it, so it is safe to run at any time.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import bug_status  # noqa: E402  (reuse its HEADER_RE / scan / classify — never re-parse)
import gov_sync  # noqa: E402

CFG = yaml.safe_load(open(ROOT / "config" / "gov_sync.yaml", encoding="utf-8"))
BS = json.load(open(ROOT / "governance" / "bug_status.json", encoding="utf-8"))
LOG = (ROOT / "governance" / "buglog.md").read_text(encoding="utf-8")
LINES = LOG.splitlines()

open_ids = [b["id"] for b in BS["open"]]
_sev, unlabelled = gov_sync.severity_census(CFG, open_ids)
scan = bug_status.scan(LINES)

# Every heading line (0-based) across every event, for exact body-span delimiting.
all_heads = sorted(e["line"] - 1 for rec in scan.values() for e in rec["events"])

# Legacy body labels: "**Severity:** medium", "**severity**: HIGH", "**Status:** FIXED", "**Status: FIXED**".
# The colon may sit INSIDE or OUTSIDE the bold, and "**" may sit between the colon and the token.
SEV_LABEL = re.compile(r"\bseverity\b[^:\n]{0,3}[:：][^A-Za-z]{0,4}([A-Za-z]+)", re.I)

# T-104 limb (b) is SEVERITY backfill ONLY. Closure is a SEPARATE concern governed by D-2642:
# the HEADER status slot is the event, and only the parser's own CLOSE_WORDS may close a bug.
# bug_status.scan already folds each bug's status correctly (last header event wins, negated/reopened
# precedence); this tool must NOT re-derive closure. The vocabulary gap — headers that declare
# TOMBSTONED/LANDED, which the parser's CLOSE_WORDS does not recognise — is a SEPARATE bug
# (registered separately), not a thing a severity tool patches around.
def authoritative_body(uid: str) -> str:
    """Body of the bug's FIRST event (authoritative), up to the next heading."""
    rec = scan[uid]
    first = rec["line"] - 1
    nxt = next((h for h in all_heads if h > first), len(LINES))
    return "\n".join(LINES[first + 1 : nxt])


# Body labels may spell MEDIUM / MED; config severity_tokens uses MED. Normalise to the token
# vocabulary BEFORE promoting; an unknown word is a NON-promotion (never auto-promote garbage).
SEV_NORM = {"CRITICAL": "CRITICAL", "HIGH": "HIGH", "MEDIUM": "MED", "MED": "MED", "LOW": "LOW"}

promote: list[tuple[str, str]] = []
ambiguous: list[str] = []
for uid in unlabelled:
    body = authoritative_body(uid)
    sm = SEV_LABEL.search(body)
    if sm and (norm := SEV_NORM.get(sm.group(1).upper())):
        promote.append((uid, norm))
    else:
        ambiguous.append(uid)

promote.sort()
ambiguous.sort()

record = {
    "unlabelled": len(unlabelled),
    "promote": [{"id": u, "severity": s} for u, s in promote],
    "ambiguous": ambiguous,
    "multi_event_unlabelled": [u for u in unlabelled if len(scan[u]["events"]) > 1],
    # The parser's folded status for each unlabelled id, REPORTED not acted on — so an owner can see a
    # bug that is ALREADY closed-per-parser (should not get a severity) alongside the severity decision.
    "parser_status": {u: scan[u]["status"] for u in unlabelled},
}
(ROOT / "temp" / "t104_limb_b_reconciliation.json").write_text(
    json.dumps(record, indent=2) + "\n", encoding="utf-8"
)
# Source text for the AMBIGUOUS ids, dumped for delegated classification (gemma, WITH source).
(ROOT / "temp" / "t104_limb_b_ambiguous_bodies.json").write_text(
    json.dumps({u: authoritative_body(u) for u in ambiguous}, indent=2) + "\n", encoding="utf-8"
)

print(f"UNLABELLED {len(unlabelled)} of {len(open_ids)} open  (severity_grandfathered={CFG['severity_grandfathered']})")
print(f"PROMOTE   (body declares severity) : {len(promote)}")
print(f"AMBIGUOUS (needs judgement)         : {len(ambiguous)}")
print()
print("=== PROMOTE (deterministic severity backfill) ===")
for uid, tok in promote:
    print(f"  {uid} -> {tok}")
print()
print("=== AMBIGUOUS (needs owner/delegate) ===")
print("  " + " ".join(ambiguous))
print()
print(f"multi-event among the 98: {record['multi_event_unlabelled']}")
print("WROTE temp/t104_limb_b_reconciliation.json")
