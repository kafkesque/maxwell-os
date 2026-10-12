# Knowledge-Layer Primitives Deployment — Deep Market Research (2026-10-12)

**Question (owner):** before committing, is our plan to deploy the knowledge-layer primitives
(FB / PT / PI / GE / TI) into the everyday agent harness the most sophisticated/effective approach —
or are there better, more profoundly effective ways to keep a local *or* frontier LLM grounded,
drift-proof, and accurate through the primitives in graph/mesh/loop engineering and in everyday
back-and-forth conversation?

**Method.** Live web research (DuckDuckGo, 2026-10-12) across three axes: (1) context engineering /
grounding, (2) knowledge-graph–augmented generation, (3) agent-memory architectures + skill-library
drift. Every claim below carries a citation; internal comparisons cite the owning decision/artifact,
not a restated value (anti-drift rule 1).

---

## 1. Verdict up front

**The current plan's direction is correct, and in its ontology it is *ahead* of the 2026 frontier —
but it is deployed incompletely.** The industry has converged on a **four-tier memory taxonomy**
(working / episodic / semantic / procedural), and Maxwell's five `content_type` roles map onto it
almost one-to-one. The single most important defect is **not** a retrieval or classification bug: it
is that Maxwell currently runs with **only its semantic tier populated** — procedural (PT/TI) and
episodic (PI) tiers are at 0 committed rows (BUG-712), and the trust-ledger signal that makes
procedural memory *safe* has no rows to track. The 2026 literature states the lesson Maxwell is
mid-way through learning: *"collapsing [memory tiers] into one mechanism is the most common
architectural mistake."*

So: **not a pivot — a completion.** The plan is right; the gap is (a) empty procedural/episodic
tiers, (b) a relation graph that exists but is asymmetric and unused for logical grounding, (c) an
MCP surface that is retrieval-first rather than context-compilation-first, and (d) no
outcome-driven lifecycle gate wired to the trust ledger.

---

## 2. The converged 2026 landscape (what the frontier actually does)

| # | Method / paper | Core claim | Maps to Maxwell |
|---|---|---|---|
| 1 | **Context Engineering** — Anthropic *Effective Context Engineering for AI Agents* (2025) + *A Survey of Context Engineering for LLMs* (arXiv **2507.13334**) | The discipline is not "retrieve more" but *"find the smallest set of high-signal tokens that maximize the likelihood of the desired outcome."* | The end-state of the MCP harness should be a **primitives context compiler**, not a query tool. |
| 2 | **KAG — Knowledge Augmented Generation** (Ant Group / OpenSPG, arXiv **2409.13731**, ACM Web 2025) | RAG's text-similarity misses *logical* connections; KAG bidirectionally enhances LLM↔KG via **logical-form-guided reasoning** + richer semantic symbols that reduce redundancy. | Maxwell already owns the structured relations (`related_fbs`, `prerequisite_fbs`, `contradicts_fbs`, `source_principle_ids`, `consulted_fbs`, `parent_pt_id`, `parent_fb_ids`) but never uses them for logical-form grounding — only `graph_expand`/`agentic_search`. |
| 3 | **Four-tier agent memory** — *Memory for Autonomous LLM Agents* (arXiv **2603.07670**), *Synapse* (arXiv **2601.02744**), multiple 2026 engineering guides | working / episodic / semantic / procedural tiers; **do not collapse them**; procedural memory = verified code patterns + skills. | See §3 — this *is* Maxwell's ontology. |
| 4 | **Library Drift** — arXiv **2605.19576**, OpenReview `EkGZ7V71HU` (2026) | Self-evolving skill libraries fail *silently* without **outcome-driven lifecycle management**: unbounded skill accumulation → retrieval degradation + false-positive injection. LLM-authored skills = **+0.0pp**, human-curated = **+16.2pp** (SkillsBench). | The sharpest warning for the `growth_edge` / self-evolution ambition. The trust ledger (`fb_reliability`) is the prescribed fix, but it is **not yet wired to a promotion gate**. |
| 5 | **Memory-Induced Tool-Drift** — arXiv **2605.24941**, ICML 2026 | Personality/biases stored in long-term memory *silently* bias tool-call selection. | New risk for Maxwell: the reliability signal itself must be a **rank signal with a confidence interval**, never a deterministic gate. |
| 6 | **Ontology-guided GraphRAG** — arXiv **2511.05991**, **2504.19667** (Tripartite-GraphRAG), EMNLP 2025 `main.1293` | Ontology-guided KGs + chunk info reach **90%** vs LLM-generated ontologies; GraphRAG's top risk is *noisy relation retrieval*. | Validates "taxonomy earns itself" + human-gated ontology; warns against LLM-authored `category`/`tags` (exactly the D-2924 gap). Also explains the cost of BUG-274 (56.8% asymmetric edges). |

---

## 3. Ontological mapping — Maxwell primitives ↔ the converged taxonomy

The industry's four tiers are, in Maxwell's terms, already expressible as `content_type` (functional
ROLE) + `extraction_type` (epistemic FORM). The plan's role/form separation (D-2933, D-2922/2923) is
**more precise than the industry's flat "memory" word** — and this is the project's genuine edge.

| Industry tier | Maxwell primitive (`content_type`) | Retrieval key (per `research/LAYER2_RETRIEVAL_CONTRACT_20261011.md`) | Today's committed rows (served run) |
|---|---|---|---|
| **semantic** (declarative knowledge) | `principle` (FB) | discipline / domain / depth / status | **6,577** ✅ |
| **procedural** (skills) | `process_template` + `tool_instruction` | intent + linkage (trigger / tool_name) | **0 + 14(mislabelled)** ❌ |
| **episodic** (what happened) | `process_instance` | `parent_pt_id` (instance-of) | **0** ❌ |
| **consolidation** (episodic→semantic learning) | `growth_edge` | `body` (open-tension) + `status` | **0** ❌ |
| **working** (per-turn payload) | — (not a store object) | the context-compiler payload itself | n/a |

**The sharp conclusion:** BUG-712 (0 PT / 0 PI / 0 GE) is the *architectural* defect, not a wiring
tick. The convergent S2 path was instructed to emit only `principle` (`stage2_extract.py:414`), and
the deterministic corrector (`reroute_content_type`, D-2747/D-275b) computed 100 growth_edge + 1
process_template rows that were then **discarded** at `stage4_merge.py:2352`. So Maxwell knows,
deterministically, that it has procedural/episodic material — it just never persists it.

---

## 4. Gap analysis vs the current plan (dug from the archive)

| # | Gap | Evidence | Severity | Owner of the truth |
|---|---|---|---|---|
| G1 | **Procedural + episodic tiers empty** — "the bridge from knowledge to action" (MISSION.md Layer 2) has no procedural rows to bridge *to*. | BUG-712, §10 of `RETRIEVAL_TRUTH_AND_UTILIZATION_20261011.md`; D2590 scoped-S6 build | **Critical** | D2590 (owner-gated C **approved**) |
| G2 | **`tool_instruction` mis-populated** — 14 rows are code excerpts, not "how an agent uses a tool". | BUG-714 | High | BUG-714 contract (owner) |
| G3 | **Relation graph asymmetric + unused for logical grounding** — KAG-style logical-form reasoning is absent; relations are 56.8% one-way. | BUG-274; KAG §2.2 | High | D-271c (concept_id / authority control, not yet built) |
| G4 | **MCP surface is retrieval-first** — 3 tools (`query_knowledge`, `get_fb_detail`, `get_fb_reliability`) return *lists*, not a compiled grounding payload. | `maxwell_mcp_server.py` | High | D2205 P2; no decision yet for the compiler shape |
| G5 | **No outcome-driven lifecycle gate on the trust ledger** — `fb_reliability` exists but nothing reads it to promote/retire a primitive. | MISSION.md Layer 2 "Trust Ledger"; Library Drift §2.4 | High | D-2924 (GE `category` ontology, flagged, not decided) |
| G6 | **`content_type` is not a first-class facet** in `retrieve.py`; `_rank_sql()` returns a dead `borp_score` constant (D-2537). | §12.3 of the retrieval-truth audit; `retrieve.py` | Medium | D-2922/2923 (ratified, not wired) |
| G7 | **GE `category`/`tags` imply a skill ontology that does not exist** — LLM-authored category strings would reintroduce drift. | `LAYER2_RETRIEVAL_CONTRACT` "NEW GAP"; Ontology-guided GraphRAG §2.6 | Medium | candidate D-2924 |

---

## 5. The ultimate most-effective utilization approach (recommended target)

Not "retrieve, then let the LLM improvise" — **compile, then verify, then act.** A single
**primitives context compiler** that, per conversational turn, assembles the minimal high-signal
grounding payload from all four tiers and sizes it to the context budget (Context Engineering §2.1):

```
turn query
  → intent route  (principle = epistemic  |  PT/PI/GE/TI = functional)   [D-2922/2923]
  → semantic tier:  top-k principles + confidence + source_diversity
  → procedural tier: matching process_template(s) + correctly-typed tool_instruction(s)
  → episodic tier:   proven process_instances for the matched PT (parent_pt_id join)
  → consolidation:   open growth_edges on those principles (what is contested)
  → logical-form pass: traverse related/prerequisite/contradicts edges (KAG-style), drop asymmetric edges (BUG-274)
  → trust signal:    fb_reliability as a *rank-with-interval*, not a gate (Tool-Drift §2.5)
  → emit: smallest grounding payload + per-claim citation, sized to budget
```

This is *more profound* than the current plan only in three specific ways, each cheap to adopt:

1. **Frame the harness as a context compiler, not a query tool** (Context Engineering). The MCP tool
   should return a *payload object* (principles + template + instance + evidence + trust), not a bare
   result list. This is a presentation/contract change over the same retrieval core.
2. **Use the existing relations for logical-form grounding** (KAG). `graph_expand` already exists;
   the missing piece is pruning the 56.8% asymmetric edges and adding logical operators
   (prerequisite ⇒ must-before, contradicts ⇒ mutual-exclusion) to the expand step.
3. **Wire the trust ledger to an outcome-driven lifecycle gate** (Library Drift). Promotion/retirement
   of a primitive must be gated on *measured outcome*, with the human-curation asymmetry (+16.2pp vs
   +0.0pp) as the justification for keeping promotion **owner-gated** (D-2898 already rules this —
   the literature confirms it).

---

## 6. Adopt / Reference / Reject (same discipline as `MARKET_RESEARCH_20260917.md`)

**ADOPT (change the plan):**
- **A1 — Context-compiler contract** for the MCP harness (smallest high-signal payload, per-turn,
  budget-sized). Falsifiable locally: does a compiled payload beat a bare top-k list on the
  `--self-retrieval` and semantic goldens for *answer quality* (not just recall)?
- **A2 — Logical-form relation pass** over the existing graph (prune BUG-274 asymmetric edges; add
  `prerequisite`/`contradicts` operators to `graph_expand`). Falsifiable: multi-hop probe recall
  before/after pruning.
- **A3 — Outcome-driven lifecycle gate** binding `fb_reliability` → promotion/retirement, **owner-gated
  per D-2898**. This is the direct antidote to Library Drift and is already half-specified in MISSION.md
  "Trust Ledger".

**REFERENCE (read, do not integrate yet):**
- **KAG / OpenSPG** — the logical-form engine is heavyweight; adopt its *operators*, not its engine
  (C2/C4 no-lock-in; C1 $0). `2609.18099` (structure pricing) already rules: keep the graph flat and
  cheap until a measured gain appears.
- **Synapse / HippoRAG** — brain-inspired episodic-semantic graphs; revisit only after PI tier has rows.
- **Context-engineering survey 2507.13334** — the taxonomy of context layers; use as the vocabulary for
  the compiler design.

**REJECT (do not re-propose):**
- **LLM-authored skill libraries without a lifecycle gate** — Library Drift (+0.0pp) is the measured
  counter-argument; Maxwell's owner-gated promotion is the correct posture.
- **LLM-authored `category`/`tags` for GE** (the D-2924 gap) — Ontology-guided GraphRAG shows LLM
  ontologies underperform; the GE category vocabulary must be a closed, calibrated, human-owned set.
- **Trust ledger as a hard gate** — Tool-Drift (ICML 2026) shows memory can bias tool selection; keep
  it a rank signal with a confidence interval.
- **Frontier-API judges/cloud eval** — unchanged from `MARKET_RESEARCH_20260917.md` C.

---

## 7. Next critical steps (consequential order)

*(Owner-gated = needs a human; unblocked = machine work I can run.)*

| # | step | blocked by | class |
|---|---|---|---|
| 1 | **D2590 scoped-S6 build** — persist the 100 GE + 1 PT the corrector already computed, ingest the 1,052 non-principle sidecar rows (PT 774 / PI 156 / GE 27 / TI 95) into ONE `type_body` JSON column; wire `S6_COMMIT_NON_FB`; add `content_type` first-class facet. **Read-only diff first, C13 backup, code-review delegate before `--apply`.** | owner already approved C; needs diff+review | task (G1) |
| 2 | **BUG-714** — retype the 14 mislabelled `tool_instruction` rows + settle the real tool_instruction contract for the harness. | owner on contract | bug/decision (G2) |
| 3 | **D-2924** — define the `growth_edge` `category` vocabulary (closed, calibrated, human-owned) *before* Stage R emits GE in volume. | owner decision | decision (G7) |
| 4 | **A2 — BUG-274** — prune asymmetric relation edges + add `prerequisite`/`contradicts` operators to `graph_expand`. | nothing | task (G3) |
| 5 | **A1 — context-compiler contract** for the MCP harness (payload object, not bare list). | #1 (needs non-principle rows to compile) | task (G4) |
| 6 | **A3 — outcome-driven lifecycle gate** binding `fb_reliability` → promotion/retirement. | #1 + #3 | task/decision (G5) |
| 7 | **BUG-715 attribution** — attribute the 7 unexplained S2→S4 drops, then re-run `scripts/audit_sidecar_commit.py`. | nothing | bug |
| 8 | **Independent golden anchors** (not sourced from the candidate leg) → settle retrieval.method + D-2537 `borp_score` defect. | owner hours (semantic re-sign) | decision |

---

## 8. Governance sync owed (do not do silently)

- This research lives in `research/` (advisory, alongside `LAYER2_RETRIEVAL_CONTRACT` and
  `SURGICAL_KNOWLEDGE_EXTRACTION`). A one-line pointer belongs in `governance/CONTEXT_INDEX.md`
  knowledge-source map — needs the session-plan `may_touch` gate widened first.
- **D-2924** should be minted (via `scripts/recompute_decision_summary.py --mint`, sequential
  single-record) once the commit-frontier rail clears; it is currently only a *flag* inside
  `LAYER2_RETRIEVAL_CONTRACT`.
- No config values were restated here (anti-drift rule 1); all internal facts cite their artifact.
