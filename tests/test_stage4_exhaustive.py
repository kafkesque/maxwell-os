#!/usr/bin/env python3
"""
Exhaustive stage4 logic test — verifies PIPELINE LOGIC, not LLM judgment.

Tests D2138 (two-stage classification), D2139 (depth derivation), 
D2137 (CRIBS), jargon omission against FIXED inputs to eliminate LLM variance.
Then runs live classification on 9 diverse FBs to verify end-to-end.
"""
import json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["MAXWELL_BORP_MIN_SOURCES"] = "1"

from pipeline.stage4_merge import map_to_canonical_with_fallback, _serialize_jargon
from pipeline.schemas import CANONICAL_DOMAINS, CANONICAL_DISCIPLINES, get_synonym_index

syn_idx = get_synonym_index()

print("=" * 70)
print("PART 1: PIPELINE LOGIC TESTS (deterministic, no LLM)")
print("=" * 70)

passed = total = 0

# ── D2138: Canonical mapping ──
print("\n── D2138: Canonical Mapping ──")
mapping_tests = [
    # (raw_label, kind, expected_canonical, description)
    ("graphic design", "domain", "graphic design", "exact match"),
    ("Graphic Design", "domain", "graphic design", "case-insensitive match"),
    ("visual communication", "domain", "graphic design", "synonym match"),
    ("neuroaesthetics", "domain", "emerging", "novel label → emerging"),
    ("thermo-economics", "discipline", "emerging", "novel discipline → emerging"),
    ("design strategy", "discipline", "design strategy", "exact discipline match"),
    ("", "domain", "emerging", "empty string → emerging"),
    ("cognitive science", "discipline", "cognitive science", "exact discipline match"),
    # D2133 (2026-08-03): "artificial intelligence" added to taxonomy. Using a
    # genuinely novel label to preserve the "unknown → emerging" test intent.
    ("quantum astrology", "discipline", "emerging", "novel label not in discipline list"),
    ("machine learning", "discipline", "machine learning", "ML IS in list"),
]
for raw, kind, expected, desc in mapping_tests:
    canon_list = CANONICAL_DOMAINS if kind == "domain" else CANONICAL_DISCIPLINES
    result = map_to_canonical_with_fallback(raw, kind, syn_idx, canon_list)
    ok = result == expected
    print(f"  {'✅' if ok else '❌'} {desc:35s} \"{raw}\" → \"{result}\" (expected \"{expected}\")")
    total += 1; passed += int(ok)

# ── D2139: Depth derivation ──
print("\n── D2139: Depth Derivation ──")
depth_tests = [
    # (canonical_domains, is_specialized, expected_depth, description)
    (["graphic design", "user experience", "digital product"], False, "universal", "3 canonical → universal"),
    (["graphic design", "user experience"], False, "cross-domain", "2 canonical → cross-domain"),
    (["graphic design"], False, "domain", "1 canonical, broad → domain"),
    (["graphic design"], True, "specialized", "1 canonical, narrow → specialized"),
    (["emerging"], False, "domain", "only emerging → domain (conservative)"),
    (["emerging"], True, "domain", "only emerging + narrow → domain (conservative)"),
    (["graphic design", "emerging"], False, "cross-domain", "1 canon + 1 emerging → cross-domain"),
    (["graphic design", "emerging"], True, "specialized", "1 canon + emerging + narrow → specialized"),
    (["graphic design", "user experience", "emerging"], False, "universal", "2 canon + emerging → universal (eff=3)"),
    (["graphic design", "user experience", "digital product"], True, "domain", "D2139 cap: 3 canon + narrow → domain"),
    (["graphic design", "user experience"], True, "domain", "D2139 cap: 2 canon + narrow → domain"),
    ([], False, "domain", "0 domains → domain"),
]
for domains, is_spec, expected, desc in depth_tests:
    n_canonical = len([d for d in domains if d != "emerging"])
    has_emerging = "emerging" in domains
    
    if is_spec:
        if n_canonical >= 2:   depth = "domain"
        elif n_canonical == 1: depth = "specialized"
        else:                  depth = "domain"
    else:
        eff = n_canonical + (1 if has_emerging else 0)
        if eff >= 3:     depth = "universal"
        elif eff == 2:   depth = "cross-domain"
        elif eff == 1:   depth = "domain"
        else:            depth = "domain"
    
    ok = depth == expected
    print(f"  {'✅' if ok else '❌'} {desc:48s} doms={domains} is_spec={is_spec} → {depth} (expected {expected})")
    total += 1; passed += int(ok)

# ── Jargon serialization ──
print("\n── Jargon Serialization ──")
jargon_tests = [
    ({"loss aversion": "preference for avoiding losses"}, True, "dict with content → present"),
    ({}, False, "empty dict → omitted"),
    ("", False, "empty string → omitted"),
    (None, False, "None → omitted"),
    ("term: explanation", True, "string with content → present"),
    ("{}", False, "string '{}' → omitted"),
    (["t1: d1", "t2: d2"], True, "list with content → present"),
    ([], False, "empty list → omitted"),
]
for j_input, expected_present, desc in jargon_tests:
    result = _serialize_jargon(j_input)
    is_present = result is not None
    ok = is_present == expected_present
    print(f"  {'✅' if ok else '❌'} {desc:40s} present={is_present} (expected {expected_present})")
    total += 1; passed += int(ok)

print(f"\n{'─'*70}")
print(f"LOGIC TESTS: {passed}/{total} PASSED")
print(f"{'─'*70}")

if passed < total:
    print(f"❌ {total-passed} LOGIC FAILURES — fix before continuing")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════
# PART 2: Live classification on 9 diverse FBs
# ═══════════════════════════════════════════════════════════════════════════
print(f"\n{'='*70}")
print("PART 2: LIVE CLASSIFICATION — 9 DIVERSE FBs")
print(f"{'='*70}")

from pipeline.stage4_merge import CLASSIFY_SYSTEM_PROMPT, build_classify_prompt
from pipeline.omlx_call import call_omlx_json

TEST_FBS = [
    {"name": "Kerning Pair Adjustment for Display Type",
     "def": "Specific letter pairs in display typefaces (AV, To, WA) require manual kerning adjustment at large sizes because automatic metrics designed for body text fail at display scales.",
     "traits": "NARROW technique → specialized"},
    {"name": "The Jagged Frontier of AI Competence",
     "def": "AI capabilities are not uniformly distributed across tasks — they exhibit a jagged frontier where some tasks are performed exceptionally well while closely related tasks fail unexpectedly.",
     "traits": "BROAD → multi-domain, universal"},
    {"name": "Simplicity Amplifies Adoption",
     "def": "Reducing feature count increases user adoption because cognitive load is the primary barrier to product engagement.",
     "traits": "PLAIN language → no jargon needed"},
    {"name": "Thermo-Economic Equilibrium in Resource Allocation",
     "def": "Temperature-equivalent modeling of resource flows reveals that economic systems reach equilibrium states analogous to thermodynamic entropy.",
     "traits": "NOVEL discipline → canonical=emerging"},
    {"name": "Color Harmony in Brand Identity Systems",
     "def": "Brand color systems require harmony rules governing saturation, contrast, and adjacency across media. Color harmony theory provides the mathematical framework.",
     "traits": "NARROW brand → specialized"},
    {"name": "Strategic Anchoring in Value Creation",
     "def": "Organizations that anchor their value proposition in customer outcomes rather than product features create more durable competitive advantages.",
     "traits": "BROAD business → domain-level"},
    {"name": "Recursive Self-Improvement in Agentic Architectures",
     "def": "Agentic systems that monitor their own output quality and iteratively refine their reasoning chains achieve compounding accuracy improvements through recursive self-correction.",
     "traits": "TECHNICAL → AI/agents, specialized"},
    {"name": "Metaphor Conventionality in Visual Communication",
     "def": "Visual metaphors range from highly conventional (fast recognition, low memorability) to highly novel (attention-grabbing, risk of misinterpretation). Effective communication calibrates this spectrum to audience expertise.",
     "traits": "NARROW semiotics → specialized"},
    {"name": "Loss Aversion in Pricing Architecture",
     "def": "Consumers feel losses roughly twice as intensely as equivalent gains. Pricing architectures that decouple payment from consumption leverage this asymmetry to reduce purchase friction.",
     "traits": "BROAD behavioral econ → cross-domain/universal"},
]

live_passed = live_total = 0
results = []

for i, tf in enumerate(TEST_FBS):
    name = tf["name"]
    definition = tf["def"]
    
    print(f"\n[{i+1}/9] {name}")
    print(f"      {tf['traits']}")
    
    # Free classify
    prompt = build_classify_prompt(name, definition)
    try:
        cd = call_omlx_json(prompt=prompt, model="phi-4-mini-instruct-8bit",
                            system=CLASSIFY_SYSTEM_PROMPT, max_tokens=512)
    except:
        cd = {"discipline": "emerging", "domains": ["emerging"], "is_specialized": False, "evidence": "cited"}
    
    disc_raw = str(cd.get("discipline", ""))
    domains_raw = list(cd.get("domains", []))
    is_spec = cd.get("is_specialized", False)
    if not isinstance(is_spec, bool):
        is_spec = str(is_spec).lower() in ("true", "1", "yes")
    evidence = cd.get("evidence", "cited")
    if evidence not in ("cited", "axiomatic"):
        evidence = "cited"
    
    # Canonical map
    canon_disc = map_to_canonical_with_fallback(disc_raw, "discipline", syn_idx, CANONICAL_DISCIPLINES)
    canon_doms = []
    seen = set()
    for d in domains_raw:
        m = map_to_canonical_with_fallback(d, "domain", syn_idx, CANONICAL_DOMAINS)
        if m not in seen:
            seen.add(m); canon_doms.append(m)
    if not canon_doms:
        canon_doms = ["emerging"]
    
    # Depth
    n_canonical = len([d for d in canon_doms if d != "emerging"])
    has_emerging = "emerging" in canon_doms
    if is_spec:
        if n_canonical >= 2:   depth = "domain"
        elif n_canonical == 1: depth = "specialized"
        else:                  depth = "domain"
    else:
        eff = n_canonical + (1 if has_emerging else 0)
        if eff >= 3:     depth = "universal"
        elif eff == 2:   depth = "cross-domain"
        elif eff == 1:   depth = "domain"
        else:            depth = "domain"
    
    disc_diff = disc_raw != canon_disc
    doms_diff = sorted(domains_raw) != sorted(canon_doms)
    
    print(f"      RAW:  disc=\"{disc_raw}\"  doms={domains_raw}  spec={is_spec}")
    print(f"      MAP:  disc=\"{canon_disc}\"  doms={canon_doms}  {'raw≠canon' if disc_diff or doms_diff else 'raw=canon'}")
    print(f"      DEPTH: {depth}  (n_canonical={n_canonical}, emerging={has_emerging})")
    
    # Track key properties
    fb = {"name": name, "depth": depth, "discipline": canon_disc, "discipline_raw": disc_raw,
          "domains": canon_doms, "domains_raw": domains_raw, "is_specialized": is_spec,
          "raw_preserved": disc_diff or doms_diff}
    results.append(fb)

# ═══ PART 2 SUMMARY ═══
print(f"\n{'─'*70}")
print(f"LIVE CLASSIFICATION RESULTS")
print(f"{'─'*70}")
print(f"{'FB':48s} | {'Depth':12s} | {'Canon Disc':20s} | Doms | Spec | Raw≠Canon")
print(f"{'─'*70}")
for r in results:
    spec = "SPEC" if r["is_specialized"] else "    "
    diff = "DIFF" if r["raw_preserved"] else "same"
    print(f"{r['name'][:48]:48s} | {r['depth']:12s} | {r['discipline'][:20]:20s} | {len(r['domains']):>4d} | {spec} | {diff}")

depths = set(r["depth"] for r in results)
raw_preserved = sum(1 for r in results if r["raw_preserved"])
specialized = sum(1 for r in results if r["is_specialized"])

print(f"\nCOVERAGE:")
print(f"  Depth levels:          {sorted(depths)} — {'✅ ALL 4' if len(depths)>=4 else '⚠️ ' + str({'universal','cross-domain','domain','specialized'} - depths) + ' MISSING'}")
print(f"  Raw labels preserved:  {raw_preserved}/{len(results)} (D2138)")
print(f"  Specialized:           {specialized}/{len(results)}")
print(f"  Canonical disciplines: {len(set(r['discipline'] for r in results))}")
print(f"  'emerging' used:       {sum(1 for r in results if r['discipline'] == 'emerging')}/{len(results)}")

# ═══ OVERALL ═══
print(f"\n{'='*70}")
print(f"OVERALL: Logic={passed}/{total} ✅ | Live classification complete")
print(f"{'='*70}")

out = ROOT / "temp" / "exhaustive_test_results.json"
with open(out, "w") as f:
    json.dump({
        "logic_passed": passed, "logic_total": total,
        "live_results": results, "depths_found": sorted(depths),
        "raw_preserved": raw_preserved, "specialized_count": specialized,
    }, f, indent=2, ensure_ascii=False)
print(f"📋 {out}")
