#!/usr/bin/env python3
"""Update golden YAML: stale disciplines → current 48 canonical taxonomy (D2133)."""

import yaml
from pathlib import Path

YAML_PATH = Path(__file__).resolve().parent / "golden_classification_edge_cases.yaml"  # D2439: C12

# ── Stale → Canonical Mapping (case-by-case with rationale) ──
DISCIPLINE_MAP = {
    # ai engineering (6 cases) → disambiguate by content
    "B02_two_domains_orthogonal": {
        "expected_discipline": "machine learning",
        "_note": "ML bias in healthcare — machine learning is the canonical parent"
    },
    "B05_domain_partial_emerging": {
        "expected_discipline": "design systems",
        "_note": "Neuro-symbolic design systems — design systems is the canonical fit"
    },
    "G03_case_study_narrative": {
        "expected_discipline": "machine learning",
        "_note": "Netflix recommendation engine — canonical ML discipline"
    },
    "I02_conflicting_domain_signals": {
        "expected_discipline": "generative ai",
        "_note": "AI art authorship — generative ai is the precise canonical match"
    },
    "J03_injection_attempt": {
        "expected_discipline": "machine learning",
        "_note": "Adversarial ML robustness — machine learning is canonical"
    },
    "L04_baseline_ai_engineering": {
        "expected_discipline": "machine learning",
        "_note": "ML embedding drift — machine learning is canonical"
    },
    # data science (2 cases) → research methodology
    "F02_jargon_heavy_academic": {
        "expected_discipline": "research methodology",
        "_note": "Heteroscedasticity correction — econometric/statistical methodology"
    },
    "L06_baseline_data_science": {
        "expected_discipline": "research methodology",
        "_note": "Causal inference — research methodology is canonical for statistical reasoning"
    },
    # engineering practice (3 cases) → disambiguate
    "E05_name_with_special_chars": {
        "expected_discipline": "systems engineering",
        "_note": "System transformation function — systems engineering is canonical"
    },
    "H02_domains_with_duplicates": {
        "expected_discipline": "software engineering",
        "_note": "Dedup/code cleanliness — software engineering is canonical"
    },
    "L08_baseline_engineering_practice": {
        "expected_discipline": "software engineering",
        "_note": "TDD methodology — software engineering is canonical"
    },
    # graphic design (4 cases) → disambiguate by sub-field
    "C03_depth_domain": {
        "expected_discipline": "typography",
        "_note": "Baseline grid systems — typography is canonical"
    },
    "C04_depth_specialized": {
        "expected_discipline": "typography",
        "_note": "Kerning pair adjustment — typography is canonical"
    },
    "G02_tool_specific_instruction": {
        "expected_discipline": "design systems",
        "_note": "Figma auto-layout — design systems is canonical for tool/system design"
    },
    "L07_baseline_graphic_design": {
        "expected_discipline": "visual perception",
        "_note": "F-pattern, contrast hierarchy — visual perception is canonical"
    },
    # user research (2 cases) → design psychology
    "L10_baseline_user_research": {
        "expected_discipline": "design psychology",
        "_note": "Observed behavior vs self-report — design psychology is canonical for UX research"
    },
    "L13_baseline_ethnography": {
        "expected_discipline": "design psychology",
        "_note": "Contextual inquiry/ethnographic UX — design psychology is canonical"
    },
}

# ── Ambiguous cases: add accept_any_of_discipline for equally valid picks ──
# These are cases where multiple canonical disciplines are genuinely valid.
# The YAML expected discipline stays the same (best fit), but we accept the alternative.
AMBIGUOUS_DISCIPLINES = {
    # systems thinking vs strategic thinking — many systems FBs fit both
    "C01_depth_universal": {
        "accept_any_of_discipline": ["systems thinking"],
        "_note": "Feedback loop convergence: strategic thinking OR systems thinking both valid"
    },
    "F03_definition_is_negation": {
        "accept_any_of_discipline": ["systems thinking"],
        "_note": "Anti-fragility: strategic thinking OR systems thinking both valid"
    },
    "F04_meta_principle": {
        "accept_any_of_discipline": ["systems thinking"],
        "_note": "Principle decay: strategic thinking OR systems thinking both valid"
    },
    "I03_everything_everywhere": {
        "accept_any_of_discipline": ["systems thinking"],
        "_note": "Entropy: strategic thinking OR systems thinking both valid"
    },
    "I04_counterintuitive_cross_domain": {
        "accept_any_of_discipline": ["systems thinking", "design strategy"],
        "_note": "Mycelial network org design: multiple valid disciplines"
    },
    "K01_full_maximal_everything": {
        "accept_any_of_discipline": ["systems thinking"],
        "_note": "Supply chain resilience: strategic thinking OR systems thinking both valid"
    },
    "L09_baseline_strategic_thinking": {
        "accept_any_of_discipline": ["systems thinking"],
        "_note": "Second-order effects: strategic thinking OR systems thinking both valid"
    },
    "L15_baseline_universal_principle": {
        "accept_any_of_discipline": ["systems thinking"],
        "_note": "Feedback delay: strategic thinking OR systems thinking both valid"
    },
    # Philosophy-adjacent FBs
    "D02_evidence_axiomatic": {
        "accept_any_of_discipline": ["philosophy"],
        "_note": "Completeness/Contradiction: strategic thinking OR philosophy (Gödel) both valid"
    },
    "F06_self_referential": {
        "accept_any_of_discipline": ["philosophy", "creative process"],
        "_note": "Design is Design: circular definition, philosophy or creative process valid"
    },
    # Behavioral vs Strategic boundary
    "E01_very_short_name": {
        "accept_any_of_discipline": ["behavioral economics"],
        "_note": "Trust Decays: strategic thinking OR behavioral economics both valid"
    },
    "E08_name_with_numbers": {
        "accept_any_of_discipline": ["systems thinking", "behavioral economics"],
        "_note": "80/20 Principle: strategic thinking OR systems thinking OR behavioral economics all valid"
    },
    # Design discipline boundaries
    "D03_evidence_ambiguous": {
        "accept_any_of_discipline": ["design psychology"],
        "_note": "Simplicity Amplifies Adoption: design strategy OR design psychology both valid"
    },
    "E06_name_non_english_terms": {
        "accept_any_of_discipline": ["design psychology", "cultural design"],
        "_note": "Wabi-Sabi: design strategy OR design psychology OR cultural design all valid"
    },
    "F05_emotionally_charged_topic": {
        "accept_any_of_discipline": ["behavioral economics", "design psychology"],
        "_note": "Moral Licensing: design strategy OR behavioral economics OR design psychology all valid"
    },
    # Invented/emerging discipline boundaries
    "A04_discipline_edge_case_emerging": {
        "accept_any_of_discipline": ["complex adaptive systems"],
        "_note": "Bioelectric morphogenesis: emerging OR complex adaptive systems both valid"
    },
}

# ── Evidence: add accept_any where both cited/axiomatic are reasonable ──
AMBIGUOUS_EVIDENCE = {
    # Cases where the definition is stated axiomatically but references observation
    "L02_baseline_software_engineering": {
        "accept_any_of_evidence": ["axiomatic"],
        "_note": "Immutable infrastructure: stated as principle, could be either"
    },
    "L05_baseline_cognitive_science": {
        "accept_any_of_evidence": ["axiomatic"],
        "_note": "Chunking: well-established cognitive science, could be either"
    },
    "L08_baseline_engineering_practice": {
        "accept_any_of_evidence": ["axiomatic"],
        "_note": "TDD: stated as methodology principle, could be either"
    },
    "L12_baseline_design_psychology": {
        "accept_any_of_evidence": ["axiomatic"],
        "_note": "Hick's Law: named principle, could be either"
    },
    "L14_baseline_interaction_design": {
        "accept_any_of_evidence": ["axiomatic"],
        "_note": "Affordances: Gibsonian principle, could be either"
    },
}

# ── Stale domains → canonical domain fix ──
DOMAIN_FIXES = {
    # Cases using 'digital product' that should also include it (domain list fixes)
    # Most domain mismatches are secondary — the taxonomy drift is mainly discipline
}

def main():
    with open(YAML_PATH) as f:
        data = yaml.safe_load(f)

    updated = 0
    for case in data["golden_cases"]:
        cid = case["id"]

        # ── Fix 1: Stale discipline → canonical ──
        if cid in DISCIPLINE_MAP:
            old = case.get("expected_discipline", "")
            new = DISCIPLINE_MAP[cid]["expected_discipline"]
            if old != new:
                case["expected_discipline"] = new
                updated += 1
                print(f"  DISCIPLINE: {cid}: {old} → {new}")
                note = DISCIPLINE_MAP[cid].get("_note", "")
                if note:
                    print(f"    {note}")

        # ── Fix 2: Add accept_any_of_discipline for ambiguous cases ──
        if cid in AMBIGUOUS_DISCIPLINES:
            accept = AMBIGUOUS_DISCIPLINES[cid].get("accept_any_of_discipline", [])
            if accept:
                existing = case.get("accept_any_of_discipline", []) or []
                merged = list(set(existing + accept))
                if merged != existing:
                    case["accept_any_of_discipline"] = merged
                    updated += 1
                    print(f"  ACCEPT_ANY_DISC: {cid}: +{accept}")
                    note = AMBIGUOUS_DISCIPLINES[cid].get("_note", "")
                    if note:
                        print(f"    {note}")

        # ── Fix 3: Add accept_any_of_evidence for ambiguous evidence ──
        if cid in AMBIGUOUS_EVIDENCE:
            accept = AMBIGUOUS_EVIDENCE[cid].get("accept_any_of_evidence", [])
            if accept:
                existing = case.get("accept_any_of_evidence", []) or []
                merged = list(set(existing + accept))
                if merged != existing:
                    case["accept_any_of_evidence"] = merged
                    updated += 1
                    print(f"  ACCEPT_ANY_EVID: {cid}: +{accept}")
                    note = AMBIGUOUS_EVIDENCE[cid].get("_note", "")
                    if note:
                        print(f"    {note}")

    # Write updated YAML
    with open(YAML_PATH, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False, width=120)

    print(f"\n✅ Updated {updated} fields across {len(data['golden_cases'])} cases")

    # Verify no stale disciplines remain
    from pipeline.schemas import CANONICAL_DISCIPLINES
    stale = set()
    for case in data["golden_cases"]:
        exp = case.get("expected_discipline", "")
        if exp and exp not in CANONICAL_DISCIPLINES and exp != "emerging":
            stale.add(exp)
    if stale:
        print(f"\n⚠️  STILL STALE: {sorted(stale)}")
    else:
        print("✅ All expected_disciplines now canonical (or 'emerging')")


if __name__ == "__main__":
    main()
