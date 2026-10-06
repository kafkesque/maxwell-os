# Ontology Enforcement Architecture — 2026-10-04

> **Owner:** barn · **Status:** PROPOSED, S6-GATED (zero taxonomy mutation while RATIFY-2 S4 runs) ·
> **Scope:** the label/ontology layer of S4-S6, not the object model (which survived the 2026-09-19 audit intact).
> **Companions:** governance/MARKET_RESEARCH_ONTOLOGY_20260919.md (R1-R8), governance/ONTOLOGY_FORENSIC_20260919.md,
> research/TAXONOMY_EVOLUTION_TOOLING_20261004.md, config/taxonomy_shacl.ttl (the contract that already exists).

## 0. Why this document exists

The 2026-09-19 programme reached a verdict and then stalled on one gate: the ROOT fix (definition-anchored,
closed-menu classification) was never swapped in, so D2138 free-generation still runs and its cost is now MEASURED
on a live corpus rather than estimated. RATIFY-2 S4 re-measured it at scale:

| measurement (in-flight checkpoint, 2026-10-04) | value | reading |
|---|---|---|
| discipline = emerging | 1,321 / 4,860 = 27.2% | ~1 in 4 FBs abstain; the BUG-150 action threshold is 15% |
| taxonomy_match_method | synonym 2,402 / emerging_real 1,321 / exact 1,137 | 49.4% of rows are rescued by a POST-HOC table |
| human agreement by method (D272c) | exact 0.61 > synonym 0.49 > emerging_real 0.33 | the ceiling is ~0.61 — AT the 0.60 floor |
| raw label space | 1,089 raw disciplines for 61 slots (17.9:1); 4,982 raw domain members for 43 slots | the generator's label space is UNBOUNDED by construction |
| config/alias_map.yaml | 999 curated rescue rules (362 discipline + 637 domain) | a COMPENSATING CONTROL for a prompt defect |
| hapax share of raw labels | 61% | "new concept" and "LLM paraphrase" are INDISTINGUISHABLE today |

**Root finding (the one that reorganises everything): axis asymmetry.** The DOMAIN axis carries a full
'Business & Strategy' group (12 domains) and its synonym index has a catch-all that absorbs 79 aliases
(marketing & communications). The DISCIPLINE axis has NO business/marketing/management group at all
('Operational & Strategy' holds only 4: economics, finance, risk management, strategic thinking). A
'consumer psychology' principle therefore lands domain -> 'marketing & communications' and discipline ->
'emerging' — a DOUBLE MISS on one object, and ~39% of the emerging mass (Mode B) is exactly this hole.
The fix is NOT a bigger alias table: it is a MISSING CANONICAL GROUP plus a prompt that stops inventing labels.

Failure modes, measured and separated (they need different remedies):

| mode | size | remedy | new labels? |
|---|---|---|---|
| A — coverage gap (a canonical home EXISTS, no alias entry) | ~210 tokens / 15% | ~26 same-axis synonym aliases | 0 |
| B — genuine ontological gap (no home on the axis) | ~520 tokens / 39% | ONE additive discipline group (D-2815) | 3 |
| C — long tail (400+ labels, <= 10 members each) | ~592 tokens / 44% | support threshold + promotion queue, NOT aliases | 0 now |

## 1. The seven layers (each config-first, C12; each independently testable; each shippable alone)

1. **Menu as a first-class vocabulary.** Every canonical slot carries prefLabel, altLabels, a mandatory
   scope_note, disjoint_with, status and replaced_by/version. Home: config/taxonomy_v5.yaml + the renderer
   scripts/render_closed_menu.py. Enforcement: a slot without a definition is not a slot.
2. **OntoClean lint** (Guarino & Welty, CACM 45(2):61-65, 2002): four tags per slot (+rigid/-rigid,
   +identity/-identity, +unity/-unity, +dependent/-independent) plus four graph constraints (a rigid subsumer of
   an anti-rigid child, an identity clash inside one branch, a unity violation in a part-of branch, a dependence
   cycle). This is the layer that finds the slots that CANNOT be defined — P3 (the 10-12 vague slots).
3. **SHACL gate** against the EXISTING config/taxonomy_shacl.ttl (4,054 bytes, unenforced since 2026-09-04):
   machine-checkable contract — prefLabel uniqueness, scope-note presence, pairwise disjointness of prefLabel and
   altLabel across slots, no altLabel resolving to two canonicals (the ISO 25964-1 USE/UF rule), status/replaced_by
   coherence. pySHACL (Apache-2.0) in CI; nothing about it needs a network.
4. **Definition-anchored classification** (D272c / research R1 / Yin, Hay & Roth, EMNLP 2019, DOI
   10.18653/v1/d19-1404): present the closed menu WITH each label's definition, require one of N or an explicit
   'none', KEEP logging the raw answer for drift measurement. This kills the synonym layer at source and is the
   ONLY layer that lifts the ceiling. Everything else is instrumentation.
5. **Promotion queue as a staging scheme, not as a table.** Novelty detection (hdbscan + nearest-centroid on the
   EXISTING bge-m3 512d vectors — no new embedding pass) -> a candidate cluster -> a parent proposal (TaxoExpan,
   WWW 2020, arXiv:2001.09522) -> a SUPPORT FLOOR over TWO independent batches -> owner ratification. The
   resolver that already exists is scripts/resolve_emerging_promotion.py.
6. **Audit** (generator != verifier, R5): cleanlab Confident Learning (Northcutt et al., JAIR 2021,
   arXiv:1911.00068) to RANK likely-mislabeled rows over the store WITHOUT re-running the pipeline, and
   DeBERTa-v3-large NLI as the independent label-consistency verifier. Never the same model family as the generator.
7. **Lifecycle**: SemVer on the menu, OBO Foundry principle 19 (deprecate, never delete; oboInWl consider /
   IAO:0100001 replaced-by), menu_hash epochs, and the Merkle-style per-axis pinning in menu_axis_hashes.py that
   already exists. A removal or a rename is a BREAKING bump (epoch + crosswalk); an addition is BACKWARD-compatible.

## 2. The standards stack this rests on (peer-reviewed / normative, all local-runnable)

| concern | standard | why it is the right one |
|---|---|---|
| vocabulary form | SKOS (W3C Rec 2009); ISO 25964-1:2011 / -2:2013; ANSI/NISO Z39.19-2005 (R2010) | prefLabel/altLabel/HiddenLabel, USE/UF, BTG/BTP/BTI, mandatory scope note; a thesaurus is exactly this problem |
| disjointness | OWL DisjointClasses / DisjointUnion; SKOS S13/S14 | makes A and B unsatisfiable together — the machine form of "these two umbrella labels may not both apply" |
| slot cleanliness | OntoClean (Guarino & Welty 2002); BFO (ISO/IEC 21838-2:2021); DOLCE (ISO/IEC 21838-3) | rigidity/identity/unity/dependence is how you PROVE a slot is a slot |
| contract checking | SHACL (W3C Rec 2017) + pySHACL; ROBOT + ELK; rdflib / owlready2 | fail-closed validation of the menu itself, offline |
| discipline spine | ANZSRC 2020 FoR (23 divisions / 213 groups / 1,967 fields, open SKOS/RDF + SPARQL) | open, machine-readable, national-statistical authority; ISCED-F 2013, OECD FORD, Scopus ASJC and OpenAlex (CC0) as crosswalks |
| business gap | JEL codes (JEL M = Business Administration / Marketing / Accounting / Personnel Economics) | the discipline axis' missing group already has an authoritative home |
| support/reliability | Cohen 1960, Landis & Koch 1977 (kappa >= 0.61 = substantial), Krippendorff | per-slot agreement as the ACCEPTANCE GATE for a label, exactly as BCTTv1 (Michie et al., Ann Behav Med 2013) does for its 93 labels |
| drift detection | River (ADWIN / KSWIN / PageHinkley, BSD-3); PSI; Evidently (Apache-2.0); BBSE/label-shift (Lipton, Wang & Smola, ICML 2018) | streaming drift alarms on the label distribution, no network |
| labeling audit | cleanlab (Apache-2.0); Snorkel (Apache-2.0) / skweak (MIT) | rank mislabels and weak supervision without re-running S4 |
| rejected | alibi-detect (no longer OSI-open -> breaks C2); scikit-multiflow (deprecated -> River); snorkel-metal (dead 2019); hosted drift APIs (Arize/Fiddler/WhyLabs -> break C1/C3) | a tool that breaks sovereignty or costs money is not a candidate |

Category-count sanity check against mature schemes: top level 12-20 (hard ceiling <= 27), second level <= 300,
leaves <= 2,000, global ratio ~1:10:100. Maxwell OS runs 43 domains / 61 disciplines, i.e. INSIDE the range —
the budget is NOT exhausted. The correct move on the 27.2% is therefore SPEND SLOTS ON THE HOLE (D-2815), never
raise the ceiling (TAXONOMY_MAX_DISCIPLINES = 75, D2378/D2504).

## 3. How raw labels are enforced into canonical groups (the direction, answered precisely)

**RAW-FIRST, bottom-up.** The LLM FREE-GENERATES the raw label at classify time; the canonical mapping happens
AFTERWARDS. Evidence: the CLASSIFY_SYSTEM_PROMPT (pipeline/stage4_merge.py ~line 371) says "Classify based on what
the principle IS, not what label fits best from a predefined list", "If it's about thermo-economics, say
thermo-economics", and "DO NOT: ... Use 'emerging' as a label — the pipeline decides that, not you". The canonical
mapping is post-hoc: map_to_canonical_with_fallback (same file, ~line 546) tries, in order, exact match -> the
SYNONYM INDEX -> a kind-constrained retry (get_synonym_index(kind)) -> 'emerging'.

**Aliases are SECONDARY and HUMAN-CURATED.** Curators harvest recurrences of raw labels and write them into three
homes: config/taxonomy_v5.yaml (per-slot raw: lists), config/synonym_map.yaml (24 DOMAIN-only entries, D2394) and
config/alias_map.yaml (999 rules). pipeline/schemas.py _build_synonym_index merges all three into one flat index of
1,847 entries and caches it (_SYNONYM_INDEX / _SYNONYM_INDEX_BY_KIND); the per-kind view uses forbidden_keys so a
source alias cannot leak across axes. taxonomy_match_method records WHICH path a row took
(exact | synonym | emerging_real | emerging_unmapped | alias) — that is the drift instrument, and it is why the
"aliases are derived from raw labels, NOT the reverse" claim is MEASURABLE rather than opinion.

**Consequence:** the alias table is a symptom of the prompt, not a component of the ontology. It may SHRINK
(after the D-2814 swap) but must never be the mechanism by which a corpus is classified.

## 4. Boundaries, ambiguity, leak and drift: what regulates what

Declared mechanisms today, and whether they actually execute:

| mechanism | home | executable? |
|---|---|---|
| cross-axis guard (a raw label may not resolve to an OPPOSITE-axis canonical) | pipeline/stage4_merge.py + schemas.py forbidden_keys | YES (but over-blunt — BUG-630) |
| per-slot exclude: lists (43/43 domains, 60/61 disciplines) | config/taxonomy_v5.yaml | NO — advisory prose only, and some tokens are non-canonical ('marketing strategy', 'video game development', 'animation', 'web design', 'science research', 'engineering infrastructure', 'social sciences') |
| default_home + boundary_tests (17 pairs incl. cognitive science vs neuroscience, finance vs economics, design psychology vs emerging) | config/boundary_discriminators.yaml (D-325) | NO — prompt-side guidance, not a gate |
| cardinality caps (max_domains_per_fb = 5; TAXONOMY_MAX_DISCIPLINES = 75) | config/pipeline_config.yaml / pipeline_paths.py | PARTIAL — enforced on the LLM path only (BUG-631) |
| promotion controls (min_raw_instances_to_promote 25; replacement_threshold_ratio 1.1; rate gates 0.35 / 0.30) | config/emerging_disciplines.yaml, config/pipeline_config.yaml, scripts/gate_emerging_rate.py | YES |

The RULES that must govern ambiguity, once the menu is a real vocabulary (layer 1-3):
(R1) ONE preferred term per concept; an alias may resolve to AT MOST ONE canonical (ISO 25964-1 USE/UF). An alias
that could resolve to two slots is a DEFECT, not a merge opportunity.
(R2) Umbrella slots are pairwise DISJOINT where declared, and an object may not carry both members of a disjoint
pair — OWL DisjointClasses is the machine form.
(R3) Every slot carries a SCOPE NOTE stating what it INCLUDES and what it EXCLUDES, and the excluded tokens must be
CANONICAL labels (so the exclusion is checkable) — this retires the unenforceable exclude: prose.
(R4) Contamination/drift prevention is a MEASUREMENT, not a rule: taxonomy_match_method + the emerging rate +
per-slot agreement, watched by a drift alarm (River/PSI), with the menu frozen per epoch by menu_hash.

## 5. Should alias buckets be dynamic? NO — the PROMOTION QUEUE must be dynamic

This is the question with the clearest standards answer, and the current design has it backwards.
- A dynamic alias bucket amplifies exactly the drift the system exists to prevent: if alias membership follows the
  corpus, the canonical vocabulary silently changes meaning as the corpus changes, and every historical row's label
  becomes un-interpretable (the vocabulary is no longer a fixed reference frame).
- ISO 25964-1 and Z39.19 require the OPPOSITE: a THIN, globally unique, one-to-one alias mapping, versioned.
- What must be dynamic is the STAGING and the PROMOTION QUEUE: novel clusters (hdbscan + centroid on existing
  bge-m3 vectors) enter 'emerging', accumulate support across >= 2 batches, propose a parent (TaxoExpan), and become
  canonical ONLY by owner ratification. Dynamic intelligence, static vocabulary.
- Supporting evidence that the alias table is being used as a crutch: synonym-mediated rows (49.4% of matched rows)
  agree with humans at 0.49 vs exact 0.61 — every alias-mediated rescue is measurably LESS reliable than a direct
  match, so widening the bucket buys coverage at the price of accuracy.

## 6. Does the system prevent new raw labels / groups? It permits SIGNALS and forbids ADOPTION (correct) — but cannot separate signal from noise

- The generator may emit ANY raw label (that is deliberate: it is the novelty sensor), and raw is preserved forever
  (discipline_source = llm_extracted_from_source), so no information is destroyed.
- Adoption is NOT automatic: 'emerging' is a single catch-all staging slot with group = '' and the raw label parked
  as s3_original_domain, and promotion is owner-gated (support floor 25, replacement ratio 1.1, rate gates 0.35/0.30,
  hard cap 75, resolver scripts/resolve_emerging_promotion.py).
- The GAP: with 61% hapax raw labels, "a genuinely new concept" and "a paraphrase of an existing one" are
  indistinguishable, so the queue cannot rank. Layer 5 closes it: novelty must be a CLUSTER with centroid distance
  and support over two batches, not a string that occurred once.
- Verdict: prevention of unratified NEW canonical labels is already correct and rails-enforced. What is missing is
  a RANKED QUEUE and a same-axis fall-through (BUG-630) — both additive, neither structural.

## 7. Implementation map — POST-HOC (now, on RATIFY-2 output) vs FUTURE BATCHES

POST-HOC (after S6; operates on STORED raw labels — no re-extraction, no re-embedding, no S4 rerun):
| step | site | input | effect |
|---|---|---|---|
| P1 | reconcile mapping with a same-axis fall-through (BUG-630 fix) | stored raw discipline/domain + menu | ~45 tokens rescued, 0 new labels |
| P2 | D-2815 additive menu bump (marketing / management / entrepreneurship) | stored raw labels mass (marketing ~323, management ~136, entrepreneurship 16) | Mode B ~520 tokens homed; emerging rate drops ~10 pts |
| P3 | Mode-A alias addendum (~26 same-axis aliases) | stored raw labels | Mode A ~210 tokens homed |
| P4 | Mode-C long-tail triage (support >= 5) | raw-label census | 400+ labels parked, ranked, owner-gated |
| P5 | legacy rows re-stamp: replay P1-P4 over the committed corpus | store + Parquet export | one BACKWARD-compatible re-map, menu_hash epoch documented |
| P6 | cleanlab + DeBERTa NLI audit | store columns (already present) | ranked mislabel list WITHOUT a pipeline run |
| P7 | drift re-measure (emerging rate, method split, per-slot agreement) | taxonomy_match_method | the acceptance evidence for the whole programme |

FUTURE BATCHES (the design change, so the next corpus does not reproduce 27.2%):
| step | site | change |
|---|---|---|
| F1 | pipeline/stage4_merge.py CLASSIFY_SYSTEM_PROMPT + the call site | definition-anchored, closed-menu (menu + definitions + 'none'), raw answer STILL logged (D-2814) |
| F2 | the mapping step | same-axis fall-through + disjointness check (BUG-630, layer 1-3 contract) |
| F3 | the write site (classify/format + stage6_commit) | cardinality cap enforced AT THE WRITE (BUG-631) |
| F4 | CI / just health | pySHACL against config/taxonomy_shacl.ttl + OntoClean lint, fired on every menu change (D-2816) |
| F5 | nightly/weekly job | novelty clustering + support accumulation -> ranked promotion queue |
| F6 | S4 preflight | refuse to start when the menu fails the contract (fail-closed, C16) — the gate that would have caught all of this |
| F7 | S6 commit | stamp menu_hash (verified non-NULL; see the open scope question) + label_provenance so any label is reinterpretable later |

**The single most important integration point is F6.** A pipeline that can start with a menu that violates its own
contract is the mechanism by which every defect in this document reached production. A preflight refusal costs
minutes; a mislabeled corpus costs a re-run plus a re-map.

## 8. What is NOT claimed (honesty is a rail here, C16)

- "100% ontologically accurate" is NOT achievable and no layer above claims it. OntoClean exists BECAUSE WordNet
  carried hundreds of latent errors found only by auditing it; the defensible target is a MEASURED, GATED,
  ABSTAINING classifier whose ceiling moves from ~0.61 (kappa) toward >= 0.80 with a PUBLISHED abstention rate.
  Any plan that promises 100% hides a failure — that is precisely what C16 forbids.
- The 999-rule alias table is NOT repaired here; it is scheduled for retirement (it is a compensating control).
- Cluster-derived labelling stays REJECTED (post-D2120/D2198 the cluster is not a persistent object; a convergent
  cluster is deliberately cross-discipline; the label must remain a function of the content-addressed FB).
- No hosted API enters any layer (C1/C3). Every tool above runs locally with an open licence.

## 9. Forensic audit of THIS proposal (done before writing a byte)

- NO CASCADE: nothing proposed is imported by, or mutates, a file the live run reads. The documents and the registry
  records are leaf artifacts.
- NO DRIFT: no taxonomy file, no menu file, no prompt and no checkpoint is touched. menu_hash epochs stay intact.
- NO BLINDSPOT INTRODUCED: BUG-630/631 are FILED rather than fixed precisely because a fix now would split the epoch.
- NO BLOAT: additive records and one document; the alias layer is scheduled to SHRINK, not grow; no dead code.
- NO CONFLICT: BUG-631 is declared as the WRITER limb of the existing BUG-273, not a competing bug.
- OPEN QUESTION (declared, not hidden): menu_hash is NULL on 7,995 committed fbs rows while all 5,165 in-flight
  checkpoint rows carry it SET. Drift is NOT measurable against the committed corpus until this scope is resolved.
  Resolution is a VERIFICATION task, not an assumption.
- ONE residual risk, declared: the mint is an append to an append-only registry; if any later consumer assumes
  records are ordered by date rather than by id, D-2814/D-2815/D-2816 will read as "newer" than they are (they are
  the newest ids, so this is only a forward-compatibility note, not a defect).

## 10. Owner actions

- NOW: none. R021 and the four abstentions (R040/R053/R080/R091) are ALREADY resolved by D-2813 — depth sentinel
  R021 = noise_drop (depth None, discipline None, golden_eligible false); the four rows are owner abstentions
  (discipline = emerging, golden_eligible = false). Zero action required.
- AFTER S6, in order: D-2814 (prompt swap) -> D-2815 (additive menu bump) -> D-2816 (SHACL + OntoClean gate) ->
  BUG-630 / BUG-631 fixes -> Mode A aliases -> Mode C triage -> post-hoc replay (P1-P7).
- HARD RULE, unchanged: do NOT pause, stop or re-run S4, and do not edit any taxonomy file until S6 completes.
