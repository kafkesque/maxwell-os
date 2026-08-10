#!/usr/bin/env python3
"""Append D2234 to DECISION-LOG.md and update aggregated_remaining_tasks.md"""
from pathlib import Path

# Update DECISION-LOG.md
log_path = Path("DECISION-LOG.md")
log_text = log_path.read_text()

d2234 = """
### D2234 — Author Concentration Cap & Extraction Type Expansion (2026-08-10)

**Context:** Cross-examination audit (D2227-D2232) flagged that Kahneman appeared in 7
golden set examples (risk of priming), and extraction types were severely imbalanced
(25/41 causal_mechanism vs 4-7 each for other types).

**Decision:** Cap all authors at ≤3 examples by editing cluster_segments to use
diverse sources. Reclassify 7 mislabeled FBs. Add 10 new examples targeting
under-represented extraction types.

**What changed:**
- **Author cap (T-009):** Kahneman 7→3, Taleb 5→3, James Clear 4→3, Gladwell 4→3.
  Done via surgical cluster_segment replacement (not example deletion):
  - CONV-006: Kahneman→Thaler/Sunstein (System 2→analytical deliberation)
  - CONV-026: Kahneman→Sull/Eisenhardt (attribute substitution in professional judgment)
  - CONV-034: Kahneman→Gary Klein (premortem properly attributed)
  - CONV-037: Kahneman→Dobelli (availability heuristic)
  - CONV-038: Taleb→Barabási (power-law distributions)
  - NEG-002: Clear→Tony Robbins (platitude example)
  - NEG-013: Gladwell→Nate Silver (spurious correlation)
  - NEG-020: Taleb trilogy→Pinker trilogy (same-author echo)
- **Reclassifications (T-015):** 7 FBs corrected from causal_mechanism:
  CONV-011→empirical_pattern, CONV-013→normative_heuristic,
  CONV-015→empirical_pattern, CONV-016→normative_heuristic,
  CONV-021→empirical_pattern, CONV-028→descriptive_model, CONV-040→normative_heuristic
- **New examples:** CONV-041 (Dunning-Kruger, EP), CONV-042 (Zipf's Law, EP),
  CONV-043 (Group Development Stages, DM), CONV-044 (Johari Window, DM),
  CONV-045 (Eisenhower Matrix, NH), CONV-046 (Five Whys, NH),
  CONV-047 (Parkinson's Law, NH), CONV-048 (Rubber Duck Debugging, NH),
  CONV-049 (Maslow's Hierarchy, DM), CONV-050 (Hanlon's Razor, NH)

**Result:**
- Author concentration: All 4 capped at ≤3 ✓
- Extraction types: EP 7→12, NH 4→12, DM 5→9, CM 46→39
- Golden set: 60→70 examples, 41→72 FBs (v4.3)
- Evidence verbatim: 178/178 (100%)
- Validation: golden_validate.py PASS

**Impact:** Training data diversity significantly improved. Non-causal FB types
better represented. Remaining gap: DM at 9 (target 12+), can be addressed in
future expansion cycle.
"""

# Find insertion point — before the last decision or at end
if "### D2233" in log_text:
    # Insert after D2233
    idx = log_text.find("---", log_text.find("### D2233"))
    if idx < 0:
        idx = len(log_text)
else:
    idx = len(log_text)

new_log = log_text[:idx] + d2234 + "\n" + log_text[idx:]
log_path.write_text(new_log)
print("✅ Updated DECISION-LOG.md with D2234")

# Update aggregated_remaining_tasks.md
tasks_path = Path("governance/aggregated_remaining_tasks.md")
tasks_text = tasks_path.read_text()

# Update T-009 and T-015 status
tasks_text = tasks_text.replace("T-009 (P1): ❌", "T-009 (P1): ✅ DONE D2234")
tasks_text = tasks_text.replace("T-015 (P1): ❌", "T-015 (P1): ✅ DONE D2234 (DM at 9, target 12)")

tasks_path.write_text(tasks_text)
print("✅ Updated aggregated_remaining_tasks.md")
