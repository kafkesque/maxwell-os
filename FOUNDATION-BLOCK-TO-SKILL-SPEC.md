# Maxwell OS — FB → PT → Skill Orchestration Spec v1.1
## Updated: 2026-07-19 | Adds: FB Reliability, Zone 3 Gate, Project/MOC Assessment

---

## 1. CONTEXT: What Maxwell OS Is

**Maxwell OS** is a sovereign knowledge extraction and orchestration system. It runs on local hardware (M1 Max 64GB), uses local LLMs (Qwen3-Coder-30B via OMLX + Ollama), costs $0 marginal, and never sends data to the cloud.

### The Four-Layer Vision

```
Layer 0: Knowledge Extraction (BUILT — 6-stage pipeline, 14 FBs, 852 books available)
    ↓
Layer 1: Knowledge Reference Layer (IN PROGRESS — classification, raw preservation, synonym matching, provenance)
    ↓
Layer 2: Skill Orchestration (THIS SPEC — FB → PT → Recipe → Skill → Trust Ledger)
    ↓
Layer 3: Business Operations Loops (FUTURE — marketing, sales, design, project management)
```

### Core Constraints

| C1 | $0 marginal cost — all generation on local hardware |
| C3 | Sovereign — all data and compute remain local |
| R5 | Generator ≠ Verifier — different model family for each |
| R7 | temp=0.0 on all generation scripts |
| R14 | Every persistent object stamped: schema_version, gen_model, pipeline_commit, pipeline_run_id |

### Atomic Units

| Unit | Definition | Example |
|------|-----------|---------|
| **FB** | Atomic knowledge unit — verified, classified, cross-referenced principle | "The Jagged Frontier of AI Competence" |
| **PT** | Step-by-step procedure referencing FBs as ground truth | "Price a New Client Project" (7 steps, each citing FBs) |
| **PI** | One execution of a PT — goal + done_when + context | "Price Acme Corp website redesign" |
| **Project** | Container grouping related PTs/PIs toward a goal | "Launch Consulting Practice" |
| **MOC** | Navigational structure linking related FBs/PTs in a domain | "Marketing Strategy MOC" — 50 FBs + 5 PTs linked |

---

## 2. FB RELIABILITY: HOW FBs ARE MONITORED FOR APPLICABILITY

### 2.1 The Problem

An FB is extracted, verified, classified — and then sits in a database. How do you know if it's actually **useful** vs. **garbage**? How do you detect that an FB that sounded profound during extraction is actually irrelevant or contradicted in practice?

### 2.2 v1 Solution: `fb_reliability` — Cumulative Execution Tracking

Discovered in `tools/render_recipe.py` (1070 lines, built and proven in v1), this system tracks every FB every time it's used in a Process Instance:

```sql
CREATE TABLE fb_reliability (
    fb_canonical TEXT PRIMARY KEY,
    total_executions INTEGER DEFAULT 0,
    valid_count INTEGER DEFAULT 0,
    irrelevant_count INTEGER DEFAULT 0,
    contradicted_count INTEGER DEFAULT 0,
    insufficient_count INTEGER DEFAULT 0,
    model_error_count INTEGER DEFAULT 0,
    reliability_score REAL DEFAULT 0.0,
    last_used TEXT,
    last_failed TEXT
);
```

**Execution outcomes (logged per FB per PI step):**

| Outcome | Meaning | Reliability Impact |
|---------|---------|-------------------|
| `FB_VALID` | FB was applicable and correct for this step | +1 valid_count |
| `FB_IRRELEVANT` | FB didn't apply to the context / "not applicable" | +1 irrelevant_count |
| `FB_CONTRADICTED` | FB's advice was wrong for this situation | +1 contradicted_count |
| `FB_INSUFFICIENT` | FB was relevant but not enough to solve the problem | +1 insufficient_count |
| `FB_UNVERIFIED` | Couldn't determine applicability | +1 model_error_count |

**How outcomes are determined:**
After each PI step executes, the Verifier (Gemma-4, cross-family per R5) evaluates each consulted FB:
- "Did the FB's principle actually apply to this step?"
- "Was the FB's advice followed? If so, was the outcome correct?"
- "If the FB was contradicted by context, flag it."

This happens automatically during recipe execution — not a separate manual review step.

### 2.3 Reliability Score Calculation

```
reliability_score = valid_count / total_executions

Thresholds:
  ≥ 0.85 → STABLE — FB is reliable, use confidently
  0.50-0.84 → WATCH — FB needs more testing, flag in output
  < 0.50 → UNSTABLE — FB is unreliable, consider archival
  < 0.20 AND total_executions ≥ 10 → GARBAGE — propose archive
```

**FB lifecycle based on reliability:**
```
EXTRACTED → CLASSIFIED → VERIFIED → [PI executions accumulate]
  ↓                                    ↓
  STABLE (>0.85, 10+ runs)          UNSTABLE (<0.50, 5+ runs)
  ↓                                    ↓
  Used in recipes confidently        Flagged for human review
                                     ↓
                                   GARBAGE (<0.20, 10+ runs)
                                     ↓
                                   ARCHIVE (human decision)
```

### 2.4 Industry Comparisons

| Approach | Example | How Maxwell OS Differs |
|----------|---------|----------------------|
| **Citation-based** | Semantic Scholar, Google Scholar — paper reliability measured by citation count | Maxwell tracks **execution outcomes**, not just references. A cited FB that always fails is flagged. |
| **Peer review** | Academic publishing — pre-publication vetting | Maxwell does **ongoing, cumulative** vetting. Every execution is a mini peer review. |
| **A/B testing** | Feature flags, experimentation platforms | Maxwell tests **knowledge applicability**, not UI variants. "Is this principle true in practice?" |
| **Groundedness detection** | Azure AI Groundedness, Galileo GenAI — automated check for hallucinated claims | Maxwell checks **applicability in context**, not just factual grounding. An FB can be factually true but practically irrelevant. |
| **Trust ledgers** | Blockchain — cumulative trust through repeated verification | Maxwell's trust is **earned through execution**, not declared. auto/queue/watch tiers (D-D7). |
| **Knowledge graph confidence** | Wikidata — confidence scores per statement | Maxwell's scores are **empirically derived** from real use, not assigned by editors. |

**Key insight:** There is NO industry standard for "does this extracted knowledge principle actually work in practice?" Citation tracking and groundedness detection exist, but neither answers the question: "When a real person tried to apply this principle to a real problem, did it help?" Maxwell's `fb_reliability` answers exactly that question. **This is novel.**

---

## 3. THE 3-ZONE FB BODY TEMPLATE

### 3.1 Structure (from `tools/render_zone.py`, v1-proven)

```
---
ZONE 1 - RELATIONS
---
metadata: status, discipline, evidence

---
ZONE 2 - BODY
---
### DEFINITION
> 🏛️ [name + what it is + mechanism + constraints]

### APPLICATION
> 🔥 When [situation] → do [action]

### FAILURE MODE
> ⚠️ [How this principle fails in practice]

### JARGON
> 🤓 [Specialized terms explained]

---
ZONE 3 - STABLE GATE
---
### EVIDENCE
> ✅ Stable if: cited | axiomatic
source: [Author - Book Title]
```

### 3.2 Zone 1: RELATIONS — Metadata

Contains: status (open/draft/stable/archived), discipline, evidence type. This is the **classification header** — machine-readable, used for filtering and routing. NOT the body. NOT the value.

### 3.3 Zone 2: BODY — The Knowledge

The FB's actual content: definition, application, failure mode, elaboration, jargon. This is what humans read and what agents reference during skill execution. **Zone 2 is immutable after verification** — the principle statement doesn't change, only its reliability score changes.

### 3.4 Zone 3: STABLE GATE — The Stabilization Checkpoint

This is the critical piece. Zone 3 is NOT a content section — it's a **stabilization predicate**:

```
ZONE 3 - STABLE GATE
✅ Stable if: cited
source: Kahneman - Thinking Fast and Slow
```

**What "Stable if: cited" means:** This FB has ≥2 distinct source books (BORP verified) and has been cross-referenced against its source texts. It graduates from "extracted" to "stable" when it passes the BORP gate.

**What Zone 3 enables:**
- **Human review trigger:** An FB sitting in "unstable" state appears in the review queue
- **Archival decision:** An FB with reliability_score < 0.20 after 10+ PI executions triggers a human decision: archive it or reclassify it
- **Consolidation signal:** When two FBs consistently get the same outcomes in the same contexts, Zone 3 flags them as merge candidates

### 3.5 The PT and GE Zone 3 Variants

| Object Type | Zone 3 Name | Stabilization Criterion |
|-------------|------------|------------------------|
| **FB** | STABLE GATE | Stable if: cited/axiomatic (BORP ≥2 sources) |
| **GE (Growth Edge)** | RESOLUTION | Resolves when: tested across 3+ contexts |
| **PT (Process Template)** | SHIP GATE | Tested across 3+ contexts before promotion to Active |

**The progression:** GE (experiential, single-source) → tested 3× → FB (cited, multi-source) → PI executions accumulate → STABLE or ARCHIVE.

### 3.6 Is This Good for GUI Feedback?

**Strengths:**
- Zone 3 is a **single, scannable line** that tells a human whether this FB can be trusted
- The `fb_reliability` table provides the **quantitative backup** for the Zone 3 claim
- The progression (GE → FB → STABLE → ARCHIVE) is a **clear lifecycle** that any UI can render as a status badge

**Weaknesses:**
- Zone 3 currently only reflects BORP status, NOT reliability_score. The `fb_reliability` table tracks PI outcomes but Zone 3 doesn't surface them. **This is a gap.**
- No visual indicator of "this FB has been used 47 times with 94% success" — that lives in SQLite, not the body template.

**Better existing solutions:**
- **Notion databases** with formula-based status: `if(prop("reliability") > 0.85, "✅ Stable", "⚠️ Watch")` — Maxwell could render Zone 3 dynamically from the reliability table
- **Obsidian Dataview** queries: `TABLE reliability_score, total_executions FROM "FBs" WHERE reliability_score < 0.5` — gives a living dashboard of unstable FBs
- **Airtable/Google Sheets** with conditional formatting — but these are cloud (violate C3)

**Recommendation:** Keep the Zone 3 STABLE GATE format (it's clean, proven, and human-readable). Add a **dynamic render** that pulls `reliability_score` and `total_executions` from the DB and appends to Zone 3 at render time:

```
ZONE 3 - STABLE GATE
✅ Stable if: cited | reliability: 0.94 (47 executions)
⚠️  Watch: contradicted in 3/23 executions — review applicability for B2B contexts
source: Kahneman - Thinking Fast and Slow
```

---

## 4. PROJECT AND MOC OBJECTS — VIABLE OR BLOAT?

### 4.1 Project Object

**Schema (from v1 ultimate architecture spec):**
```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    goal_statement TEXT,           -- one sentence: what does "done" look like
    status TEXT CHECK(status IN ('active','paused','someday','done')),
    last_touched TEXT,
    next_action TEXT,
    owner_vs_delegated TEXT,       -- what only YOU do vs what the agent owns
    est_hours_per_week REAL        -- honesty check
);
```

**Utility assessment:**
- Projects contain PTs. PTs reference FBs. Without projects, you have a flat list of procedures with no grouping.
- The `owner_vs_delegated` field is the key value — it defines the boundary between "Maxwell does this" and "Goose does this."
- `goal_statement` enables drift detection: "does the most recent activity on this project still trace back to its stated goal?"
- **Verdict: VIABLE, NOT BLOAT.** Projects are the container that makes the Coordinator Recipe possible. Without them, skill orchestration has no "what are we working on?" context.

### 4.2 MOC (Map of Content)

**What it is:** A navigational structure linking related FBs and PTs in a domain. Not a database table — a **curated document** (Markdown in v1, would be Anytype object or Obsidian note).

**Example MOC structure:**
```markdown
# Marketing Strategy MOC
## Core FBs
- [[Value-Based Pricing Over Cost-Plus]] (reliability: 0.91)
- [[Anchoring Effects in Price Perception]] (reliability: 0.87)
- [[Jobs-to-be-Done Framework]] (reliability: 0.94)
## Process Templates
- [[Price a New Client Project]] (7 steps, 12 consulted FBs)
- [[Position Your Niche]] (5 steps, 8 consulted FBs)
## Entry Points
- New to pricing? Start with [[Value-Based Pricing Over Cost-Plus]]
- Building a proposal? Run [[Price a New Client Project]]
```

**Utility assessment:**
- MOCs answer "where do I start?" in a domain with 50+ FBs
- They are the **human navigation layer** — agents use vector search, humans use MOCs
- Building a MOC is itself a PT (D-11), so MOCs are both **output** (a document) and **process** (the PT that builds them)
- MOCs are the bridge between "19,863 FBs" and "what do I do today?"
- **Verdict: VIABLE, NOT BLOAT.** But only if MOC-building is automated. If every MOC requires manual curation, it becomes a tax. The v1 spec makes MOC-building a recurring PT — agent does the first draft, human reviews. This is the right balance.

### 4.3 Relationship Map

```
PROJECT ("Launch Consulting Practice")
  ├── MOC ("Pricing Strategy") ← navigational, human-facing
  │     ├── FB: "Value-Based Pricing" (reliability: 0.91)
  │     ├── FB: "Anchoring Effects" (reliability: 0.87)
  │     └── FB: "Price Objection Handling" (reliability: 0.72 — WATCH)
  │
  ├── PT: "Price a New Client Project" ← procedural, references FBs
  │     ├── Step 1: consult FB_1, FB_2
  │     ├── Step 2: consult FB_3
  │     └── ...
  │
  ├── PI: "Price Acme Corp Website" ← one execution
  │     ├── FB_1 outcome: FB_VALID
  │     ├── FB_2 outcome: FB_VALID
  │     └── → updates fb_reliability scores
  │
  └── SESSION_EPISODES ← what happened, when, what was learned
```

---

## 5. THE FB → PT → SKILL CHAIN (Updated)

### 5.1 FB: Ground Truth + Reliability Score

```
BOOKS → [6-stage pipeline] → FBs
                                ├── name, definition, application, failure_mode
                                ├── classification (domain, discipline, depth, evidence)
                                ├── raw labels preserved (taxonomy expansion)
                                ├── s3_original_domain (crawl provenance)
                                ├── pipeline_run_id (lineage)
                                └── [PI executions] → fb_reliability score
```

**Current state:** 14 FBs, pipeline proven, classification just hardened. Reliability scores = 0 (no PI executions yet).

### 5.2 PT: The Procedure + Consulted FBs

A PT in the Maxwell system (from v1 `render_recipe.py` and eval_loop G1 checks):

```
PT Properties:
  trigger          — when to execute
  prerequisite     — what must be understood first
  consulted_fbs    — list of fb_ids referenced per step
  done_condition   — verifiable completion check
  parent_project   — which project this PT belongs to
  fb_query_domain  — domain filter for FB retrieval
  fb_query_intent  — intent filter for FB retrieval
```

### 5.3 PI: The Execution + FB Outcome Logging

Every PI execution (from `render_recipe.py`):
1. Creates `process_instances` row (state: created → running → completed)
2. For each step, retrieves FBs via keyword + vector search
3. LLM evaluates each FB: VALID / IRRELEVANT / CONTRADICTED / INSUFFICIENT
4. Logs to `fb_executions` + updates `fb_reliability`
5. Verifier (Gemma-4, R5) cross-checks: did the FB actually apply?

### 5.4 Skill: The Automated Package

A Skill packages a PT into an executable format with:
- Goose Recipe YAML (primary target)
- Embedded FB grounding (cited, with reliability scores)
- Trust ledger integration (auto/queue/watch)
- Zone 3 STABLE GATE rendered dynamically from reliability data

---

## 6. RECOMMENDED ARCHITECTURE (Updated)

### Phase 0: Alpha Kit (Now)
3 pricing books → Pipeline → 30-50 FBs → 1 PT → 1 PI → manual validation

### Phase 1: Reliability Infrastructure (After Alpha Kit validates)
- Port `fb_reliability` table to v2 (`pipeline/reliability.py`)
- Wire PI execution logging from v1 `render_recipe.py`
- Auto-render Zone 3 with `reliability_score` and `total_executions`

### Phase 2: Project + MOC Objects (After 50+ FBs)
- `projects` table (from v1 spec)
- MOC-building PT ("Build MOC for domain X")
- Coordinator Recipe (daily triage across projects)

### Phase 3: Recipe Rendering Pipeline
- `pipeline/render_recipe.py` → Goose Recipe YAML
- Dynamic Zone 3 rendering from reliability data
- Trust ledger integration

---

## 7. vs. INDUSTRY STANDARD

### 7.1 Applicability Monitoring

| System | Method | Maxwell OS Difference |
|--------|--------|----------------------|
| **Semantic Scholar** | Citation count | Execution outcomes, not reference counts |
| **Azure Groundedness** | Automated hallucination detection | Context-specific applicability, not just factual accuracy |
| **Notion databases** | Manual status fields | Automated reliability scoring from PI executions |
| **Obsidian Dataview** | Static queries | Dynamic reliability scores updated every execution |
| **Feature flags** | A/B testing | Knowledge A/B testing — "does this principle work?" |
| **Academic peer review** | Pre-publication vetting | Ongoing, cumulative vetting via every PI execution |

### 7.2 Zone 3 Stabilization

| System | Method | Maxwell OS Difference |
|--------|--------|----------------------|
| **Wikipedia talk pages** | Human discussion of article quality | Automated reliability scoring + human archive decision |
| **GitHub Issues** | Bug tracking, labels | FB "bugs" tracked via contradicted/irrelevant outcomes |
| **Jira/Linear** | Ticket lifecycle | FB lifecycle: EXTRACTED → CLASSIFIED → STABLE → WATCH → ARCHIVE |
| **NPM deprecation** | `npm deprecate` | Archive on reliability < 0.20 after 10+ executions |

### 7.3 Project/MOC Utility

| System | Method | Maxwell OS Difference |
|--------|--------|----------------------|
| **Notion** | Databases + relations | FBs are verified, not user-created |
| **Obsidian** | Backlinks + graph view | Backlinks are execution outcomes, not just manual links |
| **Roam Research** | Block references | References carry reliability scores |
| **Airtable** | Linked records | Links are bidirectional and outcome-weighted |
| **Jira epics** | Epic → story → task | Project → PT → PI → FB execution |

---

## 8. SPEC FOR ROUNDTABLE EVALUATION

### Questions

1. **FB Reliability:** Is cumulative execution tracking the right method, or should we use a decaying window (recent executions weighted more heavily)?

2. **Zone 3:** Should the STABLE GATE include reliability_score dynamically, or stay static (BORP only)? Is there a better stabilization signal?

3. **Archival threshold:** Is reliability < 0.20 after 10+ executions the right "garbage" threshold? Too aggressive? Too lenient?

4. **Project object:** Is 7 fields enough? Missing anything critical for cross-project coordination?

5. **MOC as PT:** Is "build a MOC for domain X" being a recurring PT the right approach, or should MOCs be auto-generated from FB classification + vector clustering?

6. **Industry gap:** Is the novelty claim ("no industry standard for practical knowledge applicability testing") accurate, or are there systems we've missed?

7. **Migration:** Should v2 build `fb_reliability` fresh, or port v1's implementation (1070 lines in render_recipe.py, partly Anytype-coupled)?

### Context for Evaluators

- 852 books, 6-stage pipeline, 14 FBs (3 PASS, 10 FLAG, 1 QUARANTINE)
- Classification: 25 domains, 47 disciplines, raw preservation, synonym matching (643 entries), provenance fields
- Models: Qwen3-Coder-30B (gen), Phi-4-mini (verify), Gemma-4 (cross-family verifier — planned), nomic-embed-text (embeddings)
- All $0 marginal cost, all local
- v1 reference: `tools/render_recipe.py` (1070 lines) — proven PI execution + FB reliability tracking
- v1 reference: `tools/render_zone.py` (532 lines) — proven 3-zone body template

---

*Document: FOUNDATION-BLOCK-TO-SKILL-SPEC.md v1.1*
*For cross-examination by: Claude, Kimi, DeepSeek, Grok, Qwen*
