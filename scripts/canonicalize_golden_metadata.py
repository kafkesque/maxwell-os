#!/usr/bin/env python3
"""D2506: Surgical canonicalization of dormant stage2 golden domain/discipline metadata.

STRICT scope ("don't break anything that works"):
    Line-based replacement of ONLY the top-level `domain:` / `discipline:` scalars in
    config/golden/stage2_fewshot_convergent.yaml. Every other line is preserved byte-for-byte
    (no YAML re-serialization → no re-wrapping of long evidence/rationale strings).

    Fixes ONLY the unambiguous alias→canonical class: a value that
    pipeline.schemas.match_to_canonical(v, kind) resolves to a DIFFERENT same-kind canonical.
    Cross-kind values (a discipline sitting in the domain field) and MISSING values (genuine
    taxonomy gaps) are LEFT UNTOUCHED and reported — those fields are dormant and rewriting
    them would guess at author intent.

    Re-stamps config/golden/.golden_meta.json (golden_sha256 + pipeline_commit) so the
    D2367/D2504 CI contract (test_golden_meta_contract.py) stays green.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "config" / "golden" / "stage2_fewshot_convergent.yaml"
META = ROOT / "config" / "golden" / ".golden_meta.json"
BACKUP = GOLDEN.with_suffix(".yaml.d2506_precanonicalize.bak")

# Top-level example scalar only: exactly two-space indent (list item field), plain value.
_LINE_RE = re.compile(r"^(  )(domain|discipline):( .*?)\s*$")


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def main() -> int:
    sys.path.insert(0, str(ROOT))
    from pipeline.schemas import match_to_canonical

    # Backup original (crash-safe, C6)
    shutil.copy2(GOLDEN, BACKUP)

    lines = GOLDEN.read_text().splitlines(keepends=True)
    changed: list[tuple[str, str, str, str]] = []
    left: list[tuple[str, str, str, str]] = []
    for i, line in enumerate(lines):
        m = _LINE_RE.match(line)
        if not m:
            continue
        indent, field, rest = m.groups()
        raw = rest.strip()
        canon = match_to_canonical(raw, field)  # field is "domain"/"discipline" = kind
        if canon is not None and canon != raw:
            lines[i] = f"{indent}{field}: {canon}\n"
            changed.append((field, raw, canon))
        else:
            left.append((field, raw, canon or "MISSING/CROSS-KIND"))

    GOLDEN.write_text("".join(lines))

    meta = json.loads(META.read_text())
    meta["golden_sha256"] = hashlib.sha256(GOLDEN.read_bytes()).hexdigest()
    meta["pipeline_commit"] = _git_head()
    meta["restamped_note"] = (
        "D2506: surgical line-level canonicalization of dormant stage2 golden "
        f"domain/discipline alias->canonical ({len(changed)} values); cross-kind/missing untouched"
    )
    META.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")

    print(f"✅ canonicalized {len(changed)} value(s):")
    for field, old, new in changed:
        print(f"   {field:10s} {old!r} -> {new!r}")
    print(f"\nℹ️  left untouched ({len(left)}): cross-kind / missing / empty / already-canonical")
    print(f"   backup: {BACKUP.name}")
    print(f"   re-stamped: {META}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
