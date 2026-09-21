# R1 — Closed menu frozen (D-279, 2026-09-20)

The canonical classification menu is rendered from `config/taxonomy_v5.yaml` +
`config/content_types.yaml` by `pipeline/closed_menu.py`, with `none` as a FIRST-CLASS
abstention value (D-275b/D-277). A label is only trustworthy if it is traceable to the
exact menu it was classified against — that trace is the `menu_hash`.

- **menu_hash (sha256):** `73597ee2b1bb1eb92edb08e743ffa0654c1e5994edcd3535d814c7942a89df6f`
- content_types: 8 (5 roles + 2 dispositions + `none`)
- extraction_types: 4
- disciplines: 62 (61 canonicals + `emerging`)
- domains: 44 (43 canonicals + `emerging`)
- abstention value: `none`

## Artifacts

- `config/closed_menu_v5.json` — the frozen menu (canonical JSON).
- `config/closed_menu_v5.sha256` — the provenance hash stamped onto every FB.
- `pipeline/closed_menu.py` — the renderer (single source of truth).

## Content types

| value | description |
|---|---|
| `principle` | Conceptual knowledge — why/when something works. The Foundation Block. D275b/D283 (2026-09-20): a PRINCIPLE is a single  |
| `process_template` | Repeatable how-to method with steps. Layer-2 product primitive (FB→PT→PI→Recipe). D275b (2026-09-20): a process_template |
| `process_instance` | Concrete case study of a PT actually executed — the proof it works. |
| `tool_instruction` | Tool/software-specific command or feature. Knowledge object (NOT a live callable binding). |
| `growth_edge` | Speculative/unresolved insight — idea inbox upstream of verified knowledge. POSITIVE ENTRY CRITERION (BUG-230): MUST art |
| `noise_drop` | descriptive/historical summary or fact — no prescriptive filter, no template, no named method-execution, no transferable |
| `quarantine` | carries SOME value but no clean role (ambiguous) → HOLD for later identification (does it carry steps? a method? an appl |
| `none` | first-class abstention (R1/D-279): does not fit any closed-menu value |

## Regeneration

Any change to `config/taxonomy_v5.yaml` or `config/content_types.yaml` MUST be followed by:

```
python3 scripts/render_closed_menu.py
```

and the new `menu_hash` must be carried into the next pipeline run (stamped by `stage4_merge.py`).
Labels stamped with an OLD menu_hash are traceable to the OLD menu and must be re-derived (D-277:
re-derive from source, never trust the old post-hoc stamps).

*Generated 2026-09-20T17:09:09.778497+00:00.*
