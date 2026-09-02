# S5 Remap Ordering Dependency (D2485 fingerprint)

> Logged 2026-08-31. Authority: `stage5_verify.py::_s5_input_fingerprint` (D2485).

## Dependency (must not be violated)
Any post-S4 **remap** of taxonomy labels (e.g., the alias-fix that rewrites
`discipline` / `domains` from `emerging` → an existing canonical) MUST run
**BEFORE S5 verify**.

## Why
S5 computes an **input fingerprint** (D2485) binding the S4 checkpoint to:
- checkpoint **sha256**
- `schema_version`
- `taxonomy_version`
- `manifest_hash` (config + prompt fingerprint, D2282)
- gen / classify / nli model identity

A remap changes the checkpoint content → **new sha256**. If the remap runs *after*
S5 already persisted the fingerprint, the stored `fingerprint_id` no longer matches
the remapped checkpoint → S5's stale-checkpoint gate **hard-discards** it (fail-closed).

## Correct order
```
S4 (classify → `emerging` + raw preserved)
  → REMAP (alias → existing canonical)
  → S5 (NLI verify + fingerprint)
  → S6 (commit + taxonomy_manager promote/demote)
```

## Constraint
The alias-fix maps raw → **EXISTING** canonicals, so it does **NOT** bump
`taxonomy_version` (no `taxonomy_v6`). Only a genuine promote/demote (new canonical
slot) bumps the version, and that happens in S6 / `taxonomy_manager` **post-commit**,
never pre-S5.
