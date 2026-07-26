# N5: Modular Prompt Template — Context Classification (L2, D29-D)
# 2026-07-08
#
# Modular prompt template for classification tasks.
# Uses context definitions from config/context_definitions.yaml
# and synonym mappings from config/synonym_map.yaml.
#
# Principles:
# 1. One prompt per stage (S3a, S5, S6) — no shared bloat
# 2. Each prompt imports only the context it needs
# 3. Prompt structure: Role → Context → Task → Format → Examples
# 4. temp=0.0 for all generation prompts (Rule R7)
# 5. Generator ≠ Verifier (Rule R5)

---
# ── SECTION: Context ──
# Populated from config/context_definitions.yaml

context_labels:
  - business: "Operational efficiency, cost optimization, risk management, resource governance"
  - design: "Architecture, modularity, patterns, taxonomy, creative practice"
  - academic: "Verification methodology, embedding theory, evidence quality"
  - personal: "Session management, conversation coherence, delegate behavior"
  - agentic-os: "System self-management, LLM resilience, health monitoring"

# ── SECTION: Domain Taxonomy ──
# Populated from config/taxonomy_v5.yaml (25 domains)

available_domains:
  - graphic design
  - brand identity
  - editorial & advertising
  - motion design
  - environmental design
  - digital product
  - data visualization
  - creative technology
  - web & ui
  - user experience
  - illustration
  - packaging
  - business operations
  - business development
  - entrepreneurship
  - organizational behavior
  - ai & agents
  - ai systems
  - engineering practice
  - computational art
  - code & computation
  - computational science & physics
  - systems & frameworks
  - semiotics & communication
  - research & methodology

# ── SECTION: Discipline Taxonomy ──
# Populated from config/taxonomy_v5.yaml (47 disciplines)

available_disciplines:
  - visual perception
  - visual semiotics
  - cultural design
  - semiotics
  - multimodal metaphor
  - typography
  - color theory
  - composition & layout
  - geometry & proportion
  - motion & time
  - iconography
  - design psychology
  - information architecture
  - narrative design
  - design systems
  - design strategy
  - creative process
  - cognitive science
  - behavioral economics
  - decision making
  - psychology
  - linguistics
  - leadership
  - strategic thinking
  - project management
  - risk management
  - personal productivity
  - marketing
  - systems thinking
  - complex adaptive systems
  - systems engineering
  - research methodology
  - operations research
  - prompt engineering
  - agentic architecture
  - machine learning
  - generative AI
  - software engineering
  - creative coding
  - generative design
  - computational physics & simulation
  - computational geometry
  - game design
  - social engineering
  - political economy
  - philosophy
  - privacy & surveillance

# ── SECTION: Prompt Templates ──

TEMPLATE_S3A_EXTRACTION: |
  Role: You are a convergence expert extracting principles from clustered source materials.

  Context: These sources come from domain [{domain}] with discipline [{discipline}].
  Extract ONE principle per cluster. Each principle must be:
  1. 15-25 words
  2. A general truth, not a specific observation
  3. Grounded in the source texts

  Classification rules:
  - Depth: universal | interdisciplinary | domain-specific
  - Domain: pick 1-3 from the 25 available domains
  - Discipline: pick 1 from the 47 available disciplines
  - Context: pick 1 from: business | design | academic | personal | agentic-os

  Temperature: 0.0
  Output: JSON object with fields: principle, depth, domain, discipline, context, evidence

TEMPLATE_S5_GENERATION: |
  Role: You are a boundary condition expert writing a Foundation Block (FB).

  Context: Domain [{domain}], Discipline [{discipline}], Context [{context}]

  A Foundation Block is a structured knowledge unit with:
  - definition: The principle statement (15-25 words)
  - application: How to apply it
  - failure_mode: When it breaks
  - elaboration: Why it matters, with examples
  - keywords: 5-7 searchable terms
  - jargon: 1-3 technical terms

  Rules:
  - definition must be self-contained
  - failure_mode is REQUIRED — every principle has limits
  - elaboration must cite specific examples or counter-examples
  - keywords must overlap with synonym map entries for verifiability

  Temperature: 0.0
  Output: JSON object with all 6 fields

TEMPLATE_S6_VERIFICATION: |
  Role: You are a validation expert checking Foundation Block quality.

  Context: Verify this FB against its source material.

  Check:
  1. Does the definition match the source?
  2. Is the failure_mode specific, not generic?
  3. Does the elaboration provide evidence?
  4. Are domain/discipline/context labels accurate?
  5. Is the FB self-contained (no external references)?

  If any check fails:
  - Minor: Set status=FLAG with explanation
  - Major: Set status=QUARANTINE

  Temperature: 0.0
  Output: JSON object with status, violations[], overrides[]

# ── SECTION: Usage ──
# Each prompt template should be loaded independently.
# Do not concatenate templates for different stages.
# Import via: load_prompt(stage="S3A") or load_prompt(stage="S5")
