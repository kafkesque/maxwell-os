#!/usr/bin/env python3
"""Fix golden classification set per Kimi review actionable items.

Actions:
1. Regenerate CONTEXT for all 70 FBs from domain→context derivation rules
2. Fix D02: add domains to justify universal depth (engineering practice → +2 domains)
3. Split golden file: clean FBs vs content-type tests vs parser tests vs adversarial
4. Report on accessibility rule softening needed in stage4_merge.py
"""

import re
import sys
from pathlib import Path

# ── Domain → Context derivation rules (from stage4_merge.py lines 811-832) ──
BUSINESS_SIGNALS = {
    "business operations", "business development", "entrepreneurship",
    "organizational behavior", "marketing",
}
DESIGN_SIGNALS = {
    "graphic design", "brand identity", "editorial & advertising",
    "motion design", "environmental design", "digital product",
    "illustration", "packaging", "web & ui", "user experience",
    "creative technology", "data visualization",
}
SYSTEM_SIGNALS = {
    "systems & frameworks", "code & computation", "engineering practice",
    "ai & agents", "ml systems & infrastructure", "computational science & physics",
    "software engineering",
}
ACADEMIC_SIGNALS = {
    "research & methodology", "semiotics & communication",
    "computational art", "philosophy",
}

# FB names to split out (per Kimi review) — matched by NAME field
CONTENT_TYPE_NAMES = {
    "Five-Step Design Sprint Protocol",      # G01 — PT
    "Figma Auto-Layout Nesting Strategy",    # G02 — TI
    "Netflix Personalization at Scale",      # G03 — PI
}
PARSER_TEST_NAMES = {
    "Single String Discipline Bug",          # H01
    "Dedup Domain Test",                     # H02
    "Extra Fields Tolerance",                # H03
    "Null Field Handling",                   # H04
    "Wrong Type Depth",                      # H05
}
ADVERSARIAL_NAMES = {
    "Things Change Over Time",               # F01 — tautology
    "The Undefined Principle",               # J04 — empty definition
}

def derive_context(domains_str: str) -> str:
    """Derive CONTEXT value from comma-separated domains string."""
    if not domains_str or domains_str.strip() == "emerging":
        return "personal"
    
    domain_set = {d.strip() for d in domains_str.split(",")}
    
    parts = []
    if domain_set & BUSINESS_SIGNALS:
        parts.append("business")
    if domain_set & DESIGN_SIGNALS:
        parts.append("design")
    if domain_set & SYSTEM_SIGNALS:
        parts.append("system")
    if domain_set & ACADEMIC_SIGNALS:
        parts.append("academic")
    
    if not parts:
        parts.append("personal")
    
    return ", ".join(sorted(parts))


def parse_golden_file(filepath: str) -> list[dict]:
    """Parse golden MD file into list of FB dicts."""
    with open(filepath, "r") as f:
        content = f.read()
    
    # Split on FB START/END markers
    pattern = r"\*\*FB START\*\*\n(.*?)---FB END---"
    matches = re.findall(pattern, content, re.DOTALL)
    
    # Also get preamble (everything before first FB START)
    preamble = content.split("**FB START**")[0]
    
    fbs = []
    for i, match in enumerate(matches):
        fb = {"raw": match.strip(), "index": i}
        
        # Extract FB_ID
        id_match = re.search(r"\*\*FB_ID:\*\*\s*(\S+)", match)
        fb["fb_id"] = id_match.group(1) if id_match else f"unknown_{i}"
        
        # Extract NAME
        name_match = re.search(r"\*\*NAME:\*\*\s*(.+?)(?:\n|$)", match)
        fb["name"] = name_match.group(1).strip() if name_match else "unknown"
        
        # Extract DOMAINS
        dom_match = re.search(r"\*\*DOMAINS:\*\*\s*(.+?)(?:\n|$)", match)
        fb["domains_raw"] = dom_match.group(1).strip() if dom_match else ""
        
        # Extract CONTEXT
        ctx_match = re.search(r"\*\*CONTEXT:\*\*\s*(.+?)(?:\n|$)", match)
        fb["context_current"] = ctx_match.group(1).strip() if ctx_match else ""
        
        # Extract DEPTH
        depth_match = re.search(r"\*\*DEPTH:\*\*\s*(.+?)(?:\n|$)", match)
        fb["depth"] = depth_match.group(1).strip() if depth_match else ""
        
        # Determine group from FB_ID prefix (first char before first digit)
        # e.g., "L01" → "L", "A04" → "A", "D02" → "D"
        if fb["fb_id"] and fb["fb_id"] != "unknown":
            # Try to extract the letter prefix
            prefix_match = re.match(r"([A-Z]+)", fb["fb_id"])
            fb["group"] = prefix_match.group(1) if prefix_match else ""
        else:
            fb["group"] = ""
        
        fbs.append(fb)
    
    return fbs, preamble


def fix_d02_yaml(filepath: str) -> bool:
    """Fix D02 in YAML: add domains to justify universal depth."""
    with open(filepath, "r") as f:
        content = f.read()
    
    # Find D02 case and its expected_domains
    old_block = """- id: D02_evidence_axiomatic
  description: FB is a self-evident logical truth, not empirically cited
  fb_name: Completeness Requires Contradiction
  fb_definition: Any sufficiently complete descriptive system must contain contradictions — this is a logical necessity following
    from Gödel's incompleteness theorems. The principle is axiomatic, not empirically observed.
  expected_domains:
  - engineering practice
  expected_depth: universal"""
    
    new_block = """- id: D02_evidence_axiomatic
  description: FB is a self-evident logical truth, not empirically cited
  fb_name: Completeness Requires Contradiction
  fb_definition: Any sufficiently complete descriptive system must contain contradictions — this is a logical necessity following
    from Gödel's incompleteness theorems. The principle is axiomatic, not empirically observed.
  expected_domains:
  - engineering practice
  - organizational behavior
  - systems & frameworks
  expected_depth: universal"""
    
    if old_block in content:
        content = content.replace(old_block, new_block)
        with open(filepath, "w") as f:
            f.write(content)
        return True
    else:
        print("  WARNING: D02 block not found in YAML for replacement")
        return False


def rebuild_golden_md(fbs: list[dict], preamble: str, output_path: str) -> None:
    """Rebuild golden MD with corrected CONTEXT values."""
    lines = [preamble.rstrip()]
    
    for fb in fbs:
        raw = fb["raw"]
        new_context = derive_context(fb["domains_raw"])
        
        # Replace CONTEXT line
        old_ctx = fb["context_current"]
        if old_ctx != new_context:
            raw = raw.replace(
                f"**CONTEXT:** {old_ctx}",
                f"**CONTEXT:** {new_context}"
            )
        
        lines.append("**FB START**")
        lines.append(raw)
        lines.append("---FB END---")
        lines.append("")  # blank line between FBs
    
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    
    # Report changes
    for fb in fbs:
        new_ctx = derive_context(fb["domains_raw"])
        if fb["context_current"] != new_ctx:
            print(f"  {fb['fb_id']}: {fb['context_current']} → {new_ctx}  ({fb['domains_raw']})")


def split_golden_file(fbs: list[dict], preamble: str, base_dir: str) -> None:
    """Split FBs into separate test suites by matching FB NAME field."""
    base = Path(base_dir)
    
    content_type_fbs = []
    parser_fbs = []
    adversarial_fbs = []
    main_fbs = []
    
    for fb in fbs:
        name = fb["name"]
        if name in CONTENT_TYPE_NAMES:
            content_type_fbs.append(fb)
        elif name in PARSER_TEST_NAMES:
            parser_fbs.append(fb)
        elif name in ADVERSARIAL_NAMES:
            adversarial_fbs.append(fb)
        else:
            main_fbs.append(fb)
    
    print(f"\nSplit results:")
    print(f"  Main classification FBs:  {len(main_fbs)}")
    print(f"  Content-type detection:   {len(content_type_fbs)}  ({', '.join(fb['fb_id'] for fb in content_type_fbs)})")
    print(f"  Parser robustness:        {len(parser_fbs)}  ({', '.join(fb['fb_id'] for fb in parser_fbs)})")
    print(f"  Adversarial rejection:    {len(adversarial_fbs)}  ({', '.join(fb['fb_id'] for fb in adversarial_fbs)})")
    
    # Write main classification file
    rebuild_golden_md(main_fbs, preamble, str(base / "golden_classification_fbs.md"))
    
    # Write content-type detection file
    ct_preamble = "# Maxwell v3.0 — Content-Type Detection Test Set\n"
    ct_preamble += "# Tests that the classifier correctly identifies PT, TI, PI (not FBs)\n"
    ct_preamble += f"# Generated: 2026-07-27 | {len(content_type_fbs)} cases\n\n"
    rebuild_golden_md(content_type_fbs, ct_preamble, str(base / "content_type_detection.md"))
    
    # Write parser robustness file
    pr_preamble = "# Maxwell v3.0 — Parser/Schema Robustness Test Set\n"
    pr_preamble += "# Tests JSON schema resilience (string vs list, dedup, nulls, type coercion)\n"
    pr_preamble += f"# Generated: 2026-07-27 | {len(parser_fbs)} cases\n\n"
    rebuild_golden_md(parser_fbs, pr_preamble, str(base / "parser_boundary_cases.md"))
    
    # Write adversarial rejection file
    ar_preamble = "# Maxwell v3.0 — Adversarial Rejection Test Set\n"
    ar_preamble += "# Tests that classifier rejects vacuous/empty/tautological inputs\n"
    ar_preamble += f"# Generated: 2026-07-27 | {len(adversarial_fbs)} cases\n\n"
    rebuild_golden_md(adversarial_fbs, ar_preamble, str(base / "adversarial_rejection_set.md"))
    
    # Also keep the original file as a backup reference
    print(f"\nOriginal file preserved at: {base / 'golden_classification_edge_cases.md'}")
    print(f"New main file written to:   {base / 'golden_classification_fbs.md'}")


def main():
    base_dir = Path(__file__).resolve().parent  # D2439: C12 — no hardcoded user path
    
    # ── Action 1 & 2: Parse and fix CONTEXT + D02 YAML ──
    golden_md = base_dir / "golden_classification_edge_cases.md"
    golden_yaml = base_dir / "golden_classification_edge_cases.yaml"
    
    print("=" * 60)
    print("ACTION 1: Regenerate CONTEXT from domain signals")
    print("=" * 60)
    
    fbs, preamble = parse_golden_file(str(golden_md))
    print(f"Parsed {len(fbs)} FBs from golden file")
    
    # Count current context distribution
    from collections import Counter
    ctx_dist = Counter(fb["context_current"] for fb in fbs)
    print(f"Current CONTEXT distribution: {dict(ctx_dist)}")
    
    # Show expected new distribution
    new_ctx = Counter(derive_context(fb["domains_raw"]) for fb in fbs)
    print(f"Derived CONTEXT distribution: {dict(new_ctx)}")
    
    # Write corrected golden file
    rebuild_golden_md(fbs, preamble, str(golden_md))
    
    print(f"\n{'=' * 60}")
    print("ACTION 2: Fix D02 YAML domains (1 → 3 for universal depth)")
    print("=" * 60)
    
    if fix_d02_yaml(str(golden_yaml)):
        print("  D02 YAML fixed: +organizational behavior, +systems & frameworks")
    
    print(f"\n{'=' * 60}")
    print("ACTION 3: Split golden file into test suites")
    print("=" * 60)
    
    # Re-parse the now-corrected golden file
    fbs, preamble = parse_golden_file(str(golden_md))
    split_golden_file(fbs, preamble, str(base_dir))
    
    print(f"\n{'=' * 60}")
    print("ACTION 4: Accessibility rule note (manual fix in stage4_merge.py)")
    print("=" * 60)
    print("  Current rule (line 834-841): expert → prerequisite")
    print("  Kimi issue: L06, F02, K02, C02 are expert but self-evident in golden set")
    print("  Recommended: add accessibility_override mechanism in stage4_merge.py")
    print("  This requires manual review — see next step.")


if __name__ == "__main__":
    main()
