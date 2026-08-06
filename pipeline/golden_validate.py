#!/usr/bin/env python3
"""Golden set validation gate — callable from CI or manual review.

Validates:
  1. No duplicate YAML keys (silent data loss prevention)
  2. All evidence_passages are verbatim substrings of cluster_segments (case-insensitive)
  3. Route/should_extract consistency (route=NULL iff should_extract=false)
  4. Author diversity: >=2 distinct sources per convergent example
  5. Example count matches meta header (if present)

Usage: python3 pipeline/golden_validate.py [path]

Exit 0 on pass, 1 on failure. Prints failures to stderr.
"""

import sys, re, yaml


def norm(text: str) -> str:
    """Normalize text for comparison: unicode quotes, whitespace."""
    text = str(text)
    for a, b in [
        ("‘", "'"), ("’", "'"),
        ("“", '"'), ("”", '"'),
        ("–", "-"), ("—", "-"),
        (" ", " "),
    ]:
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).strip()


class DuplicateKeyLoader(yaml.SafeLoader):
    """YAML loader that raises on duplicate mapping keys."""


def _construct_mapping(loader: yaml.Loader, node: yaml.nodes.MappingNode, deep: bool = False) -> dict:
    mapping: dict = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if isinstance(key, str) and key in mapping:
            raise ValueError(f"Duplicate YAML key {key!r} at line "
                           f"{key_node.start_mark.line + 1}:{key_node.start_mark.column + 1}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


DuplicateKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def validate(path: str) -> int:
    """Run all validations. Returns number of failures."""
    failures: list[str] = []

    # --- Load ---
    try:
        with open(path) as f:
            text = f.read()
    except FileNotFoundError:
        print(f"FAIL: File not found: {path}", file=sys.stderr)
        return 1

    # 1. Duplicate keys
    try:
        yaml.load(text, Loader=DuplicateKeyLoader)
    except ValueError as e:
        failures.append(f"DUPLICATE_KEYS: {e}")

    # Parse normally
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        print(f"FAIL: YAML parse error: {e}", file=sys.stderr)
        return 1

    examples = data.get("examples", [])
    if not examples:
        failures.append("NO_EXAMPLES: examples list is empty or missing")

    # 2. Meta count check
    meta = data.get("meta", {})
    declared_total = meta.get("total_examples")
    if declared_total is not None and declared_total != len(examples):
        failures.append(f"META_MISMATCH: meta says {declared_total} examples, actual {len(examples)}")

    # 3. Route / should_extract consistency
    for ex in examples:
        eid = ex.get("id", "?")
        ef = ex.get("expected_fb", {})
        fbs: list[dict] = ef if isinstance(ef, list) else [ef]
        routes = {fb.get("route") for fb in fbs}
        should_extract: bool = ex.get("should_extract", False)
        if should_extract and routes == {"NULL"}:
            failures.append(f"ROUTE_MISMATCH: {eid} should_extract=true but route=NULL")
        if not should_extract and "FB" in routes:
            failures.append(f"ROUTE_MISMATCH: {eid} should_extract=false but route=FB")

    # 4. Verbatim evidence (case-insensitive)
    for ex in examples:
        eid = ex.get("id", "?")
        segments = [norm(cs.get("text", "")) for cs in ex.get("cluster_segments", [])]
        segments = [s for s in segments if s and len(s) > 5]
        ef = ex.get("expected_fb", {})
        fbs = ef if isinstance(ef, list) else [ef]
        for fb in fbs:
            fb_name = fb.get("name", "?")
            for ep in fb.get("evidence_passages", []):
                epn = norm(ep)
                if not epn or len(epn) < 5:
                    continue
                if not any(epn.lower() in seg.lower() for seg in segments):
                    failures.append(
                        f"NON_VERBATIM: {eid} [{fb_name}] evidence: {epn[:80]}"
                    )

    # 5. Author/source diversity
    for ex in examples:
        if not ex.get("should_extract"):
            continue
        eid = ex.get("id", "?")
        books = [cs.get("source_book", "") for cs in ex.get("cluster_segments", [])]
        unique = set(b for b in books if b)
        if len(unique) < 2:
            failures.append(f"INSUFFICIENT_SOURCES: {eid} has only {len(unique)} distinct source(s)")

    # --- Report ---
    if failures:
        print(f"GOLDEN VALIDATION FAILED ({len(failures)} issue(s)):", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    print(f"GOLDEN VALIDATION PASSED: {len(examples)} examples, all checks ok")
    return 0


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else "config/golden/stage2_fewshot_convergent.yaml"
    sys.exit(validate(p))
