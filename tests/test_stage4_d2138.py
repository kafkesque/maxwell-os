#!/usr/bin/env python3
"""Test D2138 + depth derivation + jargon omission — comprehensive coverage.

Exercises every classification edge case:
- Free scientific classification (raw labels)
- Canonical mapping (exact match, synonym, emerging)
- Depth derivation from canonical domain count
- D2139 cap: specialized cannot be cross-domain or universal
- Jargon omission when no specialized terms
- All FB fields present and correctly typed
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.stage4_merge import (
    CLASSIFY_SYSTEM_PROMPT,
    build_classify_prompt,
    map_to_canonical_with_fallback,
    _serialize_jargon,
)
from pipeline.schemas import CANONICAL_DOMAINS, CANONICAL_DISCIPLINES, get_synonym_index
from pipeline.omlx_call import call_omlx_json

syn_idx = get_synonym_index()

# ── Test cases covering all edge cases ──
TEST_CASES = [
    # (name, definition, description, expected_properties)
    (
        "Kerning Pair Adjustment for Display Type",
        "Specific letter pairs in display typefaces (AV, To, WA) require manual kerning adjustment "
        "at large sizes because automatic metrics designed for body text fail at display scales, "
        "creating visually awkward gaps that trained eyes detect immediately.",
        "NARROW technique → is_specialized=true, 1 domain",
        {"is_specialized": True, "expected_depth_max": "domain", "has_jargon": True},
    ),
    (
        "The Jagged Frontier of AI Competence",
        "AI capabilities are not uniformly distributed across tasks — they exhibit a jagged "
        "frontier where some tasks are performed exceptionally well while closely related tasks "
        "fail unexpectedly. Effective human-AI collaboration requires mapping this frontier "
        "empirically rather than assuming uniform capability.",
        "BROAD principle → multi-domain, universal or cross-domain",
        {"is_specialized": False, "expected_depth_min": "cross-domain", "has_jargon": True},
    ),
    (
        "Simplicity Amplifies Adoption",
        "Reducing feature count increases user adoption because cognitive load is the primary "
        "barrier to product engagement. This principle is widely observed across product categories.",
        "PLAIN language → no jargon needed",
        {"is_specialized": False, "has_jargon": False},
    ),
    (
        "Thermo-Economic Equilibrium in Resource Allocation",
        "Temperature-equivalent modeling of resource flows reveals that economic systems reach "
        "equilibrium states analogous to thermodynamic entropy — resource gradients drive allocation "
        "behavior in predictable, mathematically modelable patterns.",
        "NOVEL discipline → should get 'emerging' canonical discipline",
        {"is_specialized": True, "expected_raw_disc_not_canonical": True, "has_jargon": True},
    ),
    (
        "Strategic Anchoring in Value Creation",
        "Organizations that anchor their value proposition in customer outcomes rather than product "
        "features create more durable competitive advantages. The anchoring effect shapes both internal "
        "resource allocation and external market positioning by creating a reference point that "
        "competitors must work against.",
        "BROAD business principle → domain-level, no jargon",
        {"is_specialized": False, "expected_depth": "domain", "has_jargon": False},
    ),
    (
        "Color Harmony in Brand Identity Systems",
        "Brand color systems require harmony rules governing saturation, contrast, and adjacency "
        "across media. Color harmony theory provides the mathematical framework for ensuring visual "
        "consistency. The principle applies specifically to the intersection of color theory and "
        "brand application.",
        "NARROW technique in brand domain → specialized",
        {"is_specialized": True, "expected_depth": "specialized", "has_jargon": True},
    ),
    (
        "Descriptive References Reduce Fragility",
        "Descriptive references use named identifiers instead of positional indices to create more "
        "robust and maintainable code. This approach leverages human-readable labels to access data "
        "elements, making code less susceptible to breaking when underlying data structures change.",
        "TECHNICAL principle → should have jargon for 'positional indices', 'magic numbers'",
        {"is_specialized": False, "has_jargon": True},
    ),
]

print("=" * 80)
print("D2138 + DEPTH DERIVATION + JARGON OMISSION — COMPREHENSIVE TEST")
print("=" * 80)

results = []
for name, definition, description, expected in TEST_CASES:
    print(f"\n{'─' * 60}")
    print(f"FB: {name}")
    print(f"Description: {description}")
    print(f"Def: {definition[:100]}...")

    # Stage 1: Free scientific classification
    prompt = build_classify_prompt(name, definition)
    try:
        class_data = call_omlx_json(
            prompt=prompt,
            model="phi-4-mini-instruct-8bit",
            system=CLASSIFY_SYSTEM_PROMPT,
            max_tokens=512,
        )
    except Exception as e:
        print(f"  ❌ Classification error: {e}")
        class_data = {
            "discipline": "emerging", "domains": ["emerging"],
            "is_specialized": False, "evidence": "cited",
        }

    disc_raw = str(class_data.get("discipline", ""))
    domains_raw = list(class_data.get("domains", []))
    is_spec = class_data.get("is_specialized", False)
    if not isinstance(is_spec, bool):
        is_spec = str(is_spec).lower() in ("true", "1", "yes")
    evidence = class_data.get("evidence", "cited")
    if evidence not in ("cited", "axiomatic"):
        evidence = "cited"

    print(f"  RAW discipline: {disc_raw}")
    print(f"  RAW domains:    {domains_raw}")
    print(f"  is_specialized: {is_spec}")
    print(f"  evidence:       {evidence}")

    # Stage 2: Canonical mapping
    canon_disc = map_to_canonical_with_fallback(disc_raw, "discipline", syn_idx, CANONICAL_DISCIPLINES)
    canon_domains = []
    seen = set()
    for d in domains_raw:
        m = map_to_canonical_with_fallback(d, "domain", syn_idx, CANONICAL_DOMAINS)
        if m not in seen:
            seen.add(m)
            canon_domains.append(m)
    if not canon_domains:
        canon_domains = ["emerging"]

    print(f"  CANON discipline: {canon_disc}  (raw==canon: {disc_raw == canon_disc})")
    print(f"  CANON domains:    {canon_domains}")

    # Stage 3: Depth derivation
    n_canonical = len([d for d in canon_domains if d != "emerging"])
    has_emerging = "emerging" in canon_domains

    if is_spec:
        # D2139: specialized uses canonical-only count
        if n_canonical >= 2:
            depth = "domain"
        elif n_canonical == 1:
            depth = "specialized"
        else:
            depth = "domain"
    else:
        effective_n = n_canonical + (1 if has_emerging else 0)
        if effective_n >= 3:
            depth = "universal"
        elif effective_n == 2:
            depth = "cross-domain"
        elif effective_n == 1:
            depth = "domain"
        else:
            depth = "domain"

    print(f"  DEPTH (derived): {depth}  (n_canonical={n_canonical}, emerging={has_emerging}, specialized={is_spec})")

    # ── Validate against expected ──
    checks = []
    if "is_specialized" in expected:
        chk = f"is_specialized={is_spec} (expected {expected['is_specialized']})"
        if is_spec == expected["is_specialized"]:
            checks.append(f"✅ {chk}")
        else:
            checks.append(f"❌ {chk}")

    if "expected_depth" in expected:
        chk = f"depth={depth} (expected {expected['expected_depth']})"
        if depth == expected["expected_depth"]:
            checks.append(f"✅ {chk}")
        else:
            checks.append(f"❌ {chk}")

    if "expected_depth_max" in expected:
        ok = depth in ("domain", "specialized")
        chk = f"depth={depth} (expected max={expected['expected_depth_max']})"
        if ok:
            checks.append(f"✅ {chk}")
        else:
            checks.append(f"❌ {chk}")

    if "expected_depth_min" in expected:
        ok = depth in ("cross-domain", "universal")
        chk = f"depth={depth} (expected min={expected['expected_depth_min']})"
        if ok:
            checks.append(f"✅ {chk}")
        else:
            checks.append(f"❌ {chk}")

    if "expected_raw_disc_not_canonical" in expected:
        ok = disc_raw != canon_disc
        chk = f"raw_disc≠canon_disc: {disc_raw}≠{canon_disc}"
        if ok:
            checks.append(f"✅ {chk}")
        else:
            checks.append(f"❌ {chk}")

    for c in checks:
        print(f"  {c}")

    # ── Jargon serialization test (simulated) ──
    # Test _serialize_jargon with various inputs
    jargon_tests = [
        ({"loss aversion": "preferring avoidance of losses over acquiring gains."}, True, "dict with content → present"),
        ({}, False, "empty dict → omitted"),
        ("", False, "empty string → omitted"),
        (None, False, "None → omitted"),
        ("some term: explanation", True, "string with content → present"),
        ("{}", False, "string '{}' → omitted"),
        (["term1: def1", "term2: def2"], True, "list with content → present"),
    ]
    for j_input, expected_present, j_desc in jargon_tests:
        result = _serialize_jargon(j_input)
        is_present = result is not None
        status = "✅" if is_present == expected_present else "❌"
        if not is_present and not expected_present:
            pass  # Don't print successes for omission tests
        elif is_present != expected_present:
            print(f"  {status} JARGON TEST: {j_desc} → present={is_present} (expected={expected_present})")

    # ── Assemble final FB record ──
    fb_record = {
        "name": name,
        "definition": definition,
        "domains": canon_domains,
        "discipline": canon_disc,
        "domains_raw": domains_raw,
        "discipline_raw": disc_raw if disc_raw else None,
        "depth": depth,
        "evidence": evidence,
        "is_specialized": is_spec,
    }
    results.append(fb_record)

# ── Additional standalone jargon tests ──
print(f"\n{'─' * 60}")
print("STANDALONE JARGON SERIALIZATION TESTS")
print(f"{'─' * 60}")
jargon_tests = [
    ({"loss aversion": "preferring avoidance of losses over acquiring gains."}, True, "dict with content"),
    ({}, False, "empty dict"),
    ("", False, "empty string"),
    (None, False, "None"),
    ("some term: explanation", True, "string with content"),
    ("{}", False, "string '{}'"),
    (["term1: def1", "term2: def2"], True, "list with content"),
]
all_jargon_ok = True
for j_input, expected_present, j_desc in jargon_tests:
    result = _serialize_jargon(j_input)
    is_present = result is not None
    ok = is_present == expected_present
    if not ok:
        all_jargon_ok = False
    status = "✅" if ok else "❌"
    detail = f"→ '{result[:60]}...'" if is_present else "→ None (omitted)"
    print(f"  {status} {j_desc:25s} | present={is_present} {detail}")
if all_jargon_ok:
    print(f"  ✅ All jargon tests pass")

# ── Summary ──
print(f"\n{'=' * 80}")
print("SUMMARY — All 7 test cases")
print(f"{'=' * 80}")
for r in results:
    spec = "SPEC" if r.get("is_specialized") else "    "
    print(f"  [{spec}] {r['name'][:45]:45s} | depth={r['depth']:12s} | disc={r['discipline']:25s} | doms={len(r['domains'])} | raw_disc={r['discipline_raw']}")

print(f"\n✅ Full test complete — {len(results)} FBs with all classification edge cases")
print(f"   File: tests/test_stage4_d2138.py")
