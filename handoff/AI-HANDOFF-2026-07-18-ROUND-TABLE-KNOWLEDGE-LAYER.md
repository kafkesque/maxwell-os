# Maxwell OS — Round Table Handoff: Knowledge Layer & Extraction System
> **Date:** 2026-07-18 | **Format:** Multi-LLM round table with cross-examination
> **Instruction:** Research the landscape, propose solutions, then cross-examine each other's proposals against Maxwell OS constraints. Do NOT accept the first proposal — challenge it.

---

## ROUND TABLE PROTOCOL

This handoff is designed for a multi-LLM round table. The expected flow:

1. **LLM-1 (Researcher):** Market research — survey the knowledge layer landscape
2. **LLM-2 (Architect):** Propose ultimate knowledge layer + extraction pipeline based on research
3. **LLM-3 (Critic):** Cross-examine LLM-2's proposal against Maxwell OS constraints. Identify gaps, risks, infeasibilities.
4. **LLM-2 (Revision):** Revise based on critique
5. **Output:** Final recommendation with dissent noted

If running with a single LLM: simulate all three roles sequentially. Clearly label which role is speaking.

---

## §1 — MAXWELL OS: WHAT IT IS

Maxwell OS is a sovereign, local-first knowledge extraction and agentic reasoning system. Its purpose is to transform a library of 863+ books into structured, source-grounded, retrievable principles (Foundation Blocks / FBs) that an LLM agent can use as guardrails for business operations.

**Scale:**
- 863 books in MD format, 505 EPUB, 673 PDF
- Target: 15,000–25,000 FBs
- Currently: pipeline stalled at 574 unconverged principles, 0 FBs generated

**Business goal:** Automate solopreneur operations — marketing, sales, project management, content creation, client management, administration — using LLM agents constrained by source-grounded principles from these books.

**The fundamental dependency chain:**
```
Extraction pipeline → FBs → Knowledge layer → Retrieval → Agentic loops → Business automation
     ⬆ STALLED          ⬆ 0     ⬆ undefined     ⬆ not built   ⬆ not built
```

---

## §2 — HARD CONSTRAINTS (NON-NEGOTIABLE)

### 2.1 Compute & Cost

- **Hardware:** Apple M1 Max, 10 cores (8P/2E), 64GB shared RAM, 105GB free disk (89% full)
- **Cost:** $0 marginal cost. All generation on local hardware. No cloud APIs for core pipeline.
- **VRAM budget:** ~50GB available for models. OMLX server runs locally. Can load 1 heavy model (~35-38GB) OR 2 medium models (~6-14GB each). Cannot run 2 heavy models concurrently.
- **Disk pressure:** 105GB free is tight. Any solution adding large indexes must account for this.

### 2.2 Sovereignty & Future-Proofing

- **No vendor lock-in.** Any storage format, database, or tool must have an open-source replacement path. If Company X goes bankrupt tomorrow, Maxwell OS must continue operating.
- **All data remains local.** No cloud sync required for core function.
- **No single-provider dependency.** Every component needs an alternative.
- **Transferable/migratable.** FBs must be movable between storage backends without data loss or schema breakage. Format must be readable in 10 years.

### 2.3 Technical Constraints

- **temp=0.0** on all generation. No creativity in extraction.
- **Generator ≠ Verifier.** Different model family for generation vs verification.
- **Every persistent object stamped:** schema_version, gen_model, pipeline_commit.
- **Crash-safe writes:** tempfile → fsync → os.replace.
- **All imports must be in requirements.txt.**
- **Never hardcode paths.**

### 2.4 Local Models Available

| Model | RAM | Purpose |
|-------|-----|---------|
| Qwen3.6-35B-A3B-4bit | ~14GB | Primary generator |
| Gemma-4-26B-A4B | ~6GB | Cross-family verifier |
| Phi-4-mini-instruct-8bit | ~4GB | Light verify, triage |
| nomic-embed-text | 274MB | Embeddings (via Ollama) |
| Qwen2.5-Coder-7B | ~8GB | Code generation |

---

## §3 — THE PAIN POINTS (WHAT HAS FAILED)

### 3.1 The Pipeline Has Never Completed a Run

Maxwell OS has an 8-stage pipeline (S1→S8). With the current architecture (post-D1055-D1058 taxonomy changes), **zero FBs have been generated.** The pipeline is stuck at S3a with 574 unconverged principles across 9 domains. S3c verification, S5 generation, S6 validation, S7 human gate, and S8 Anytype push have never been reached.

### 3.2 The Pipeline Architecture Has Become Unstable

The pipeline has undergone multiple mid-flight architectural changes:

- **D1055:** Eliminated separate classification scripts, moved to S3a inline classification
- **D1056:** Changed output folder structure based on classification labels
- **D1055-FIX:** Three-channel contamination fix — domain labels were being silently overwritten

Each change was applied to a pipeline that had never completed. The architecture was being redesigned without a proven baseline.

### 3.3 19,770 "Validated" FBs Are Dead Data

The pipeline status reports 19,770 validated FBs. These are from an OLD pipeline run with previous taxonomy, previous schemas, and no current stamps (R14). They are incompatible with the current 25-domain/47-discipline taxonomy. They cannot be pushed to Anytype without migration. They create a false sense of progress.

### 3.4 Massive Infrastructure Built Around a Non-Functional Core

23 tools (9,837 LOC) of automation infrastructure were built:
- Guardian daemon, circuit breaker, monitor dashboard, TUI, IPC server
- Semantic cache, intent router, parallel consensus, consensus voting
- Self-healing, security audit, resource monitor

All of this assumes a working pipeline exists to automate, monitor, and protect. The pipeline doesn't work. The guardian is guarding nothing.

### 3.5 Governance Drift

- 22 LIVING decisions have phantom file claims (29% of all LIVING decisions)
- Decisions reference tools and files that don't exist on disk
- Decision lifecycle has no IMPLEMENTATION-VERIFIED state — decisions go from PROPOSED → LIVING without filesystem verification

### 3.6 The Current Pipeline Cannot Deliver What Maxwell Needs

The stated requirements for FBs:
- 100% factually and pragmatically accurate
- Convergent and applicable (BORP: ≥2 distinct book sources)
- Agentic-proof (structured enough for LLM retrieval and reasoning)
- Ontologically precise indexing (unambiguous domain/discipline classification)
- Transferable between storage backends
- Multi-modal ready (future: images, audio, video)

The current pipeline has not demonstrated it can produce FBs meeting any of these criteria, because it has never produced an FB under the current architecture.

### 3.7 The Knowledge Layer Was Never Defined

The pipeline was built to feed Anytype. Anytype is a proprietary knowledge management tool. It was chosen as the destination without evaluating:
- Whether it's the right canonical store
- What happens if Anytype becomes unavailable
- How FBs migrate to another system
- Whether its retrieval API is sufficient for agentic use
- Whether it supports the indexing precision Maxwell needs

The pipeline was built to serve a destination that was never validated as the right destination.

---

## §4 — MAXWELL'S INTENTIONS (WHAT HE WANTS TO BUILD)

### 4.1 The End State

Maxwell wants an LLM agent (Goose or future harness) that can run business operations autonomously within source-grounded constraints:

- "Write a marketing plan for this product" → retrieves marketing FBs, generates within those principles
- "Price this service" → retrieves pricing/positioning FBs, applies them
- "Handle this client objection" → retrieves negotiation/communication FBs
- "Create content about X" → retrieves domain FBs, generates within them

The LLM must operate within a **framework** of principles extracted from books. Without this framework, the LLM is just improvising — which is what Maxwell is trying to escape.

### 4.2 The Three Layers Maxwell Needs

```
3. LOOPS      — Well-defined automation cycles: trigger → retrieve FBs → reason → act → verify
2. FRAMEWORK  — Structured, source-grounded principles constraining the LLM
1. PIPELINE   — Extraction system that builds the framework from books
```

### 4.3 What Maxwell Is Asking You to Solve

**First:** Define the ultimate knowledge layer — the canonical storage, indexing, and retrieval system for FBs. This must satisfy all constraints in §2. It must be future-proof, agentic-grade, ontologically precise, and transferable.

**Second:** Define the extraction pipeline that feeds this knowledge layer. The pipeline must produce FBs that are 100% factually accurate, BORP-grounded, and properly classified.

**Third:** Cross-examine every proposal against the failures documented in §3. If a proposal would repeat the same patterns (over-engineering before proof, building around a non-functional core, governance without verification), call it out.

### 4.4 Cognitive Profile (How Maxwell Thinks)

Maxwell has a "cognitive sentinel perfectionist" profile. This means:
- He will find the flaw in any proposal. Don't try to hide weaknesses — surface them.
- He values precision over speed. A slower but correct system beats a fast but sloppy one.
- He rejects solutions that feel like patches. He wants the right foundation.
- He has been burned by over-engineering. Proposals must be minimal and provable.
- He wants to understand WHY a recommendation is correct, not just WHAT to build.

---

## §5 — MARKET RESEARCH QUESTIONS

These are the questions each LLM role should investigate. Answer with specific technologies, versions, benchmarks, and trade-offs.

### 5.1 Knowledge Layer

1. **What is the most future-proof, sovereign storage format for structured knowledge with vector embeddings?** Compare Parquet, Lance, JSON, SQLite, Arrow, and any emerging formats. Consider: 10-year readability, schema evolution, compression, incremental writes, tool ecosystem.

2. **What vector database best fits local-only, single-machine deployment with 15K-25K vectors of 768-1024 dimensions?** Compare LanceDB, ChromaDB, FAISS, DuckDB VSS, sqlite-vec, Qdrant (local mode). Consider: query latency, memory usage, disk footprint, filtering capabilities, migration path.

3. **What embedding model gives the best retrieval quality for principle-level text (1-3 sentences) at minimal resource cost?** Compare nomic-embed-text, BGE series, GTE series, Jina embeddings. Consider: MTEB retrieval score, model size, inference speed on M1 Max, license.

4. **What retrieval architecture works best for agentic use?** An agent needs to query FBs by: semantic similarity, structured filters (domain/discipline/depth/BORP count), relationship traversal (supports/contradicts), and hybrid combinations. Compare: basic vector search, hybrid search, HyDE, multi-vector, GraphRAG, ColBERT, re-ranking.

5. **How should FB relationships be modeled and stored?** FBs can support, contradict, extend, or contextualize other FBs. Options: property graph (Neo4j-style), RDF triples, JSON-LD, adjacency lists in Parquet.

### 5.2 Extraction Pipeline

6. **What extraction architecture minimizes pipeline stages while maximizing principle quality?** The current 8-stage pipeline (S1→S8) has never completed. What's the minimum viable pipeline that can produce BORP-grounded FBs?

7. **How should BORP (≥2 distinct book sources per principle) be enforced?** Options: inline in generation prompt, post-hoc verification, multi-pass clustering across books.

8. **How should domain/discipline classification be done to achieve ontological precision?** The current system uses 25 domains and 47 disciplines with LLM inline classification. It has contamination problems (labels being silently overwritten).

9. **What's the simplest end-to-end pipeline that can prove the concept works?** Design a pipeline that takes ONE book and produces 5-10 FBs meeting all quality criteria. This is the Minimum Viable Pipeline — prove it works once before scaling.

### 5.3 Cross-Cutting

10. **What existing open-source projects solve similar problems?** Are there knowledge extraction pipelines, knowledge graph builders, or agentic retrieval systems that Maxwell OS could adopt or learn from instead of building from scratch?

11. **What is the simplest stack that satisfies all constraints?** Not the most powerful. Not the most elegant. The simplest thing that actually works on M1 Max with 64GB RAM and 105GB free disk.

---

## §6 — CROSS-EXAMINATION RULES

When LLM-3 cross-examines LLM-2's proposal, it must ask:

1. **Falsifiability:** How would we know if this solution is wrong? What measurable failure would prove it?
2. **Failure modes from §3:** Does this proposal repeat any of the documented failures? (Over-engineering, building around non-functional core, governance without verification)
3. **Constraint violations:** Does it violate any constraint in §2? Be specific.
4. **Hidden complexity:** What's the simplest version of this that works? What would we strip out?
5. **Migration risk:** If this component dies, how do we move to an alternative? What data is lost?
6. **The 10-year test:** Will this still work in 2036? On whatever hardware and OS exists then?

---

## §7 — EXPECTED OUTPUT FORMAT

```
### ROLE: RESEARCHER (LLM-1)
[M market research findings for questions 1-11]

### ROLE: ARCHITECT (LLM-2)
[Proposed knowledge layer architecture]
[Proposed extraction pipeline architecture]
[Rationale for each choice, citing research]

### ROLE: CRITIC (LLM-3)
[Cross-examination using §6 rules]
[Specific risks, gaps, infeasibilities]
[Alternative approaches worth considering]

### ROLE: ARCHITECT REVISION (LLM-2)
[Revised proposal addressing critique]
[Dissent noted where disagreement persists]

### FINAL RECOMMENDATION
[Recommended knowledge layer]
[Recommended extraction pipeline]
[Minimum viable first step]
[Dissent and open questions]
```

---

## §8 — CONTEXT APPENDIX

### 8.1 Current Pipeline Architecture (for reference only — do NOT feel bound by this)

```
S1: extractive.py — chunk books, embed chunks (nomic-embed-text)
S1.5: cluster.py — FAISS clustering of chunks
S3a: s3_converge_local.py — LLM extracts principles per cluster (Qwen3.6)
S3c: s3c_verify.py — cross-family verification (Phi-4-mini / Gemma-4)
S5: s5_bridge.py → s5_generate_local.py — generate FBs from principles (Gemma-4)
S6: s6_pipeline.py — validate FBs, check BORP, normalize names
S7: pipeline_gate.py --gate G7 — human review of n=30 sample
S8: push_anytype.py + space_router.py — push to Anytype
```

### 8.2 Current Taxonomy

25 domains: graphic design, brand identity, editorial & advertising, motion design, environmental design, digital product, data visualization, creative technology, web & UI, user experience, illustration, packaging, business operations, business development, entrepreneurship, organizational behavior, AI & agents, AI systems, engineering practice, computational art, code & computation, computational science & physics, systems & frameworks, semiotics & communication, research & methodology

47 disciplines: visual perception, visual semiotics, cultural design, semiotics, multimodal metaphor, typography, color theory, composition & layout, geometry & proportion, motion & time, iconography, design psychology, information architecture, narrative design, design systems, design strategy, creative process, cognitive science, behavioral economics, decision making, psychology, linguistics, leadership, strategic thinking, project management, risk management, personal productivity, marketing, systems thinking, complex adaptive systems, systems engineering, research methodology, operations research, prompt engineering, agentic architecture, machine learning, generative AI, software engineering, creative coding, generative design, computational physics & simulation, computational geometry, game design, social engineering, political economy, philosophy, privacy & surveillance

### 8.3 Current FB Schema (from D1055-FIX)

```
domain — LLM raw output, preserved forever
discipline — LLM raw output
domain_canonical — validated taxonomy label or "emerging"
discipline_canonical — validated taxonomy label or "emerging"
domain_raw — model's non-canonical label for folder grouping
discipline_raw — model's non-canonical label
s3_original_domain — immutable crawl provenance
domain_canonical_multi — multi-domain (max 3 for cross-domain/universal)
```

### 8.4 What's Already Installed

DuckDB 1.5.4, LanceDB 0.33.0, ChromaDB 1.5.8, FAISS 1.13.2, PyArrow 23.0.1, RDFlib 7.1.4, sqlite-vec 0.1.9, sentence-transformers 5.6.0, Ollama (nomic-embed-text), OMLX (Qwen3.6, Gemma-4, Phi-4-mini)

---

*This handoff provides context and asks questions. It does NOT propose solutions. That is the LLMs' job.*
