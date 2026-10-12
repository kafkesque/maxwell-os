# Layer-2 Retrieval Contract — All Four Non-Principle Content Types
Status: decision-layer spec (D-2923). No code. Grounded in `config/content_types.yaml` `extension_fields`.

## Why this doc exists
D-2922 established that PT/TI are Layer-2 skill references keyed by *intent*, NOT discipline. This doc
completes that contract to **all four** non-principle content types (process_template, process_instance,
tool_instruction, growth_edge) and records each type's retrieval key + the linkage graph. GE and PI were
under-specified in D-2922; this closes that gap.

## Single invariant (the anti-drift rule)
- `principle` → keyed by **discipline / domain / depth / status** (epistemic-claim routing). UNCHANGED.
- `process_template` / `process_instance` / `tool_instruction` / `growth_edge` → keyed by **intent +
  linkage** (functional-role routing). **NEVER discipline/domain.**
- Rationale (D2323): `content_type` is a functional *ROLE*. Only `principle` carries a discipline/domain
  epistemology. The four non-principle roles carry their own retrieval surface, already declared in
  `content_types.yaml` `extension_fields`. Forcing them through the 48-discipline taxonomy is an
  ontological mismatch — do not do it.

## Per-type retrieval key map (sourced from content_types.yaml extension_fields)

| content_type | PRIMARY key (intent/linkage) | SECONDARY keys | Linkage | NOT keyed by |
|---|---|---|---|---|
| process_template | `trigger` (intent-vector) | `done_condition` (gate), `steps`, `fb_query_domain` + `fb_query_intent` (FB grounding query) | `consulted_fbs` → FB | discipline/domain |
| process_instance | `parent_pt_id` (instance-of, navigational) | `instance_text` + `domain_context` (context-vector), `outcome_metric`/`outcome_qualitative` (evidence) | `parent_pt_id` → PT | discipline/domain |
| tool_instruction | `tool_name` (exact/prefix) + `description` (intent-vector) | `syntax` + `parameters` (signature), `example`, `alternatives` (SEE-ALSO) | `alternatives` → TI | discipline/domain |
| growth_edge | `body` (open-tension vector) + `status` (promotion filter) | `category` + `tags` + `priority`, `parent_fb_ids` (which FB it extends), `contested` (retention flag) | `parent_fb_ids` → FB, `parent_pt_id` → PT, `promoted_to_type`/`promoted_to_id` → promoted object | discipline/domain |

Notes:
- PI retrieval is **instance-of** (navigational): "given a PT, find proven instances that work" → `parent_pt_id` is the join key.
- GE retrieval is **status-filtered** by the promotion pipeline (`open → investigating → implementing → promoted | archived`) — a growth edge is a *work item*, not a settled claim.
- TI retrieval is **signature + intent**: `tool_name` exact/prefix for lookup, `description` vector for "what achieves this".

## Linkage graph (Layer-2 orchestration substrate)
```
FB(principle) ──fb_query_domain/fb_query_intent, consulted_fbs──▶ PT
PT ──parent_pt_id──▶ PI
FB ──parent_fb_ids──▶ GE ──promoted_to_type/promoted_to_id──▶ promoted object (FB/PT/TI)
TI ──alternatives──▶ TI
```
This graph is the skill-orchestration substrate. Retrieval must expose it (`retrieve.py` already declares a
`graph-aware` mode — it needs per-type join keys, not discipline).

## Retrieval surface delta (what must change, in order)
Current: `fbs_fts` FTS5 = (name, definition, keywords, jargon); `vec_fbs` = definition_embedding float[512];
`retrieve.py` keyword facets = discipline/domains/depth/status + FTS + vector; NO content_type facet.
Target:
1. `content_type` = **first-class facet** in `retrieve.py` (filter + facet), alongside discipline/domains/depth/status.
2. Per-type FTS + vector columns:
   - PT: FTS(`trigger`, `done_condition`, `steps`), vector(`trigger` + `done_condition`)
   - PI: `parent_pt_id` exact index, FTS(`instance_text`, `outcome_qualitative`), vector(`instance_text` + `domain_context`)
   - GE: FTS(`body`, `category`, `tags`), vector(`body`), `status` + `category` facet
   - TI: `tool_name` exact/prefix index, FTS(`description`, `syntax`, `example`), vector(`description`)
3. Commit + index **all 5 types** (today: principle 6,577 + TI 14 committed; PT/PI/GE = 0 rows; TI retrieval fields unindexed).

## NEW GAP — flagged, needs its own decision (do NOT resolve inline)
GE `category` + `tags` imply a **skill/capability ontology that does not exist**. The 48-discipline
taxonomy does NOT cover the open-tension / capability-growth space. Do NOT force GE into discipline.
Required: a new decision (candidate **D-2924**) defining the growth_edge `category` facet (closed
vocabulary + provenance + calibration), before Stage R emits GE in volume — otherwise GE rows will carry
ad-hoc `category`/`tags` strings and reintroduce the same drift the taxonomy was built to prevent.

## Blocked / unblocked
- Decision layer (this doc): **NOT blocked — DONE**.
- Wiring (`retrieve.py` + `fbs_fts` + `vec_fbs` + `stage6_commit`): **blocked on rows** — Stage R must emit PT/PI/GE/TI in volume first (today 0/0/0/14).
- Stage R typed extraction (emit PT/PI/GE/TI): **unblocked implementation — next**, but gated on D-2924 (GE category) first to avoid ad-hoc strings.
