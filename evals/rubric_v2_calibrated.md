 # Depth Classification Rubric v2 — Calibrated
## Applied 2026-05-21

> **⚠️ SUPERSEDED** by `guardrails/classification-protocol-v2.2.md` as of 2026-05-22.
> The "no counterexample" test is now a secondary validation step within v2.2's framework.
> Primary Universal definition: pattern applies to non-human systems.
> Do NOT delete — referenced by existing `classification_version` values.

### universal
No counterexample exists within target class. The principle describes a structural cognitive/perceptual feature that holds universally.
Test: "Can you name ANY context where this does NOT apply?" If yes → NOT universal.

### cross-domain  
Principles transfer across 2+ fields but have boundary conditions. They describe mechanisms that hold across multiple disciplines but fail in edge cases.
Test: "Strip domain-specific entities — does the mechanism still hold?" If yes → cross-domain.
Test: "Does it apply in emergency/high-stress contexts?" If no → cross-domain, not universal.

### domain
Principles are bound to a specific professional practice or field. They don't generalize outside their field.

### specialized
Principles name a specific tool, API, library, or technology. If the tool disappeared, the principle would be meaningless.
