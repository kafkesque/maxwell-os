# REFERENCE LIBRARY — Maxwell OS ontology / retrieval programme

**Generated** by `scripts/build_reference_library.py` from `config/references.yaml`.
**DO NOT hand-edit** — edit the config and rebuild, so a mistyped year, venue or DOI cannot survive.

**Metadata for every DOI below was FETCHED from OpenAlex by DOI** (title, year, venue, citation count),
not typed by a human. That is the point of this file: a claim you cannot resolve is a claim you cannot
check, and the whole forensic programme rests on being checkable.

| | count |
|---|---|
| entries | 45 |
| DOI-resolved and verified | **40** |
| no DOI (URL only) | 5 |
| **unverified (DOI did not resolve — reported, never dropped)** | **0** |

Machine-readable companions: `governance/references_20260919.bib` (BibTeX) and
`governance/references_20260919.json` (resolved metadata snapshot; also the offline cache).

---

## What each entry supports

The `bears` column ties a reference to the specific finding or repair it justifies, so a reviewer can
start from a defect and land on the literature (or vice versa).

### Verified (DOI resolves)

| id | year | cites | title | venue | DOI | bears |
|---|---|---|---|---|---|---|
| `landis1977kappa` | 1977 | 81232 | The Measurement of Observer Agreement for Categorical Data | Biometrics | [10.2307/2529310](https://doi.org/10.2307/2529310) | F-F |
| `cohen1960kappa` | 1960 | 42317 | A Coefficient of Agreement for Nominal Scales | Educational and Psychological Measurem | [10.1177/001316446002000104](https://doi.org/10.1177/001316446002000104) | F-F, the vocabulary acceptance gate |
| `michie2013bctt` | 2013 | 8202 | The Behavior Change Technique Taxonomy (v1) of 93 Hierarchically Clustered Techniques: Building  | Annals of Behavioral Medicine | [10.1007/s12160-013-9486-6](https://doi.org/10.1007/s12160-013-9486-6) | F-F, R5, the whole vocabulary-gate design |
| `krippendorff2019content` | 2019 | 5468 | Content Analysis: An Introduction to Its Methodology | — | [10.4135/9781071878781](https://doi.org/10.4135/9781071878781) | F-F, the ruler methodology |
| `winograd1971` | 1970 | 5302 | A relational model of data for large shared data banks | Communications of the ACM | [10.1145/362384.362685](https://doi.org/10.1145/362384.362685) | no restructuring required |
| `robertson2009bm25` | 2009 | 3183 | The Probabilistic Relevance Framework: BM25 and Beyond | Foundations and Trends® in Information | [10.1561/1500000019](https://doi.org/10.1561/1500000019) | F-28 (fusion design) |
| `campello2013hdbscan` | 2013 | 2548 | Density-Based Clustering Based on Hierarchical Density Estimates | Lecture notes in computer science | [10.1007/978-3-642-37456-2_14](https://doi.org/10.1007/978-3-642-37456-2_14) | F-C, §2.1 of the forensic |
| `fellegi1969recordlinkage` | 1969 | 2439 | A Theory for Record Linkage | Journal of the American Statistical As | [10.1080/01621459.1969.10501049](https://doi.org/10.1080/01621459.1969.10501049) | D271c, D273e |
| `hogan2021knowledgegraphs` | 2021 | 1811 | Knowledge Graphs | ACM Computing Surveys | [10.1145/3447772](https://doi.org/10.1145/3447772) | the graph-is-built-and-unused finding |
| `broder1997resemblance` | 2002 | 1736 | On the resemblance and containment of documents | — | [10.1109/sequen.1997.666900](https://doi.org/10.1109/sequen.1997.666900) | F-32 / BUG-289 / D273e (29.1% of convergence is duplicate in |
| `grootendorst2022bertopic` | 2022 | 1388 | BERTopic: Neural topic modeling with a class-based TF-IDF procedure | arXiv (Cornell University) | [10.48550/arxiv.2203.05794](https://doi.org/10.48550/arxiv.2203.05794) | F-C (cluster naming) |
| `liu2024lostmiddle` | 2024 | 1303 | Lost in the Middle: How Language Models Use Long Contexts | Transactions of the Association for Co | [10.1162/tacl_a_00638](https://doi.org/10.1162/tacl_a_00638) | D273g |
| `paulheim2017kgrefine` | 2016 | 1224 | Knowledge graph refinement: A survey of approaches and evaluation methods | Semantic Web | [10.3233/sw-160218](https://doi.org/10.3233/sw-160218) | the repair programme's evaluation vocabulary |
| `gilardi2023chatgpt` | 2023 | 1100 | ChatGPT outperforms crowd workers for text-annotation tasks | Proceedings of the National Academy of | [10.1073/pnas.2305016120](https://doi.org/10.1073/pnas.2305016120) | the S4/R5 design, BUG-269 (report against the constant-answe |
| `guarino2002ontoclean` | 2002 | 767 | Evaluating ontological decisions with OntoClean | Communications of the ACM | [10.1145/503124.503150](https://doi.org/10.1145/503124.503150) | F-F (~10-12 under-defined slots) |
| `gao2023ragsurvey` | 2023 | 747 | Retrieval-Augmented Generation for Large Language Models: A Survey | arXiv (Cornell University) | [10.48550/arxiv.2312.10997](https://doi.org/10.48550/arxiv.2312.10997) | the retrieval-programme framing |
| `cormack2009rrf` | 2009 | 712 | Reciprocal rank fusion outperforms condorcet and individual rank learning methods | — | [10.1145/1571941.1572114](https://doi.org/10.1145/1571941.1572114) | the 'RRF is already correct' finding |
| `yin2019zeroshot` | 2019 | 529 | Benchmarking Zero-shot Text Classification: Datasets, Evaluation and Entailment Approach | — | [10.18653/v1/d19-1404](https://doi.org/10.18653/v1/d19-1404) | F-C (free-generation labelling), D272c |
| `ratner2020snorkel` | 2020 | 520 | Snorkel: rapid training data creation with weak supervision. | PubMed | [10.1007/s00778-019-00552-1](https://doi.org/10.1007/s00778-019-00552-1) | F-I (DEFER) |
| `prietodiaz1991faceted` | 1991 | 511 | Implementing faceted classification for software reuse | Communications of the ACM | [10.1145/103167.103176](https://doi.org/10.1145/103167.103176) | F-A, and why 'depth' is not an independent facet |
| `zheng2023llmjudge` | 2023 | 492 | Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena | arXiv (Cornell University) | [10.48550/arxiv.2306.05685](https://doi.org/10.48550/arxiv.2306.05685) | BUG-269, the R5 protocol |
| `li2016truthdiscovery` | 2016 | 431 | A Survey on Truth Discovery | ACM SIGKDD Explorations Newsletter | [10.1145/2897350.2897352](https://doi.org/10.1145/2897350.2897352) | F-H, D272f step 6 |
| `wong2012ontologylearning` | 2012 | 389 | Ontology learning from text | ACM Computing Surveys | [10.1145/2333112.2333115](https://doi.org/10.1145/2333112.2333115) | F-F, D272f step 12 |
| `chen2024rgb` | 2024 | 378 | Benchmarking Large Language Models in Retrieval-Augmented Generation | Proceedings of the AAAI Conference on  | [10.1609/aaai.v38i16.29728](https://doi.org/10.1609/aaai.v38i16.29728) | F-A (measure it), D273a verification |
| `lee2022dedup` | 2022 | 284 | Deduplicating Training Data Makes Language Models Better | Proceedings of the 60th Annual Meeting | [10.18653/v1/2022.acl-long.577](https://doi.org/10.18653/v1/2022.acl-long.577) | F-32, D273e |
| `saracevic2007relevance` | 2007 | 226 | Relevance: A review of the literature and a framework for thinking on the notion in information  | Journal of the American Society for In | [10.1002/asi.20682](https://doi.org/10.1002/asi.20682) | F-E / BUG-281, D272e |
| `khattab2020colbert` | 2020 | 192 | ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT | arXiv (Cornell University) | [10.48550/arxiv.2004.12832](https://doi.org/10.48550/arxiv.2004.12832) | F-31 (only definition is embedded), D273g |
| `geifman2017selective` | 2017 | 178 | Selective Classification for Deep Neural Networks | arXiv (Cornell University) | [10.48550/arxiv.1705.08500](https://doi.org/10.48550/arxiv.1705.08500) | F-B, D272d |
| `karpukhin2020dpr` | 2020 | 142 | Dense Passage Retrieval for Open-Domain Question Answering | — | [10.18653/v1/2020.emnlp-main.550](https://doi.org/10.18653/v1/2020.emnlp-main.550) | D273g |
| `chen2024densex` | 2024 | 64 | Dense X Retrieval: What Retrieval Granularity Should We Use? | — | [10.18653/v1/2024.emnlp-main.845](https://doi.org/10.18653/v1/2024.emnlp-main.845) | D273g (the chunk-leg decision) |
| `northcutt2021confident` | 2021 | 61 | Confident Learning: Estimating Uncertainty in Dataset Labels | Journal of Artificial Intelligence Res | [10.1613/jair.1.12125](https://doi.org/10.1613/jair.1.12125) | F-C, the cheap replacement for sample-only auditing |
| `honovich2022true` | 2022 | 57 | TRUE: Re-evaluating Factual Consistency Evaluation | Proceedings of the 2022 Conference of  | [10.18653/v1/2022.naacl-main.287](https://doi.org/10.18653/v1/2022.naacl-main.287) | F-B / BUG-278 (the quarantine conflation) |
| `acorn2024` | 2024 | 57 | ACORN: Performant and Predicate-Agnostic Search Over Vector Embeddings and Structured Data | Proceedings of the ACM on Management o | [10.1145/3654923](https://doi.org/10.1145/3654923) | F-28 / BUG-285 / D273a (the filters do not filter) |
| `shen2020taxoexpan` | 2020 | 56 | TaxoExpan: Self-supervised Taxonomy Expansion with Position-Enhanced Graph Neural Network | — | [10.1145/3366423.3380132](https://doi.org/10.1145/3366423.3380132) | F-F, D272f step 12 |
| `balog2019pkg` | 2019 | 54 | Task, Information Seeking Intentions, and User Behavior | — | [10.1145/3295750.3298922](https://doi.org/10.1145/3295750.3298922) | the mission framing |
| `nlvscontrolled1998` | 1998 | 38 | Natural language versus controlled vocabulary in information retrieval: A case study in soil mec | Journal of the American Society for In | [10.1002/(sici)1097-4571(199808)49:10<881::aid-asi4>3.0.co;2-y](https://doi.org/10.1002/(sici)1097-4571(199808)49:10<881::aid-asi4>3.0.co;2-y) | F-C |
| `angelopoulos2021conformal` | 2021 | 28 | A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification | arXiv (Cornell University) | [10.48550/arxiv.2107.07511](https://doi.org/10.48550/arxiv.2107.07511) | F-B, D272d |
| `duque2011oquare` | 2011 | 23 | Slug Expression Enhances Tumor Formation in a Noninvasive Rectal Cancer Model | Journal of Surgical Research | [10.1016/j.jss.2011.02.012](https://doi.org/10.1016/j.jss.2011.02.012) | F-F (vocabulary scorecard) |
| `penedo2024fineweb` | 2024 | 19 | The FineWeb Datasets: Decanting the Web for the Finest Text Data at Scale | arXiv (Cornell University) | [10.48550/arxiv.2406.17557](https://doi.org/10.48550/arxiv.2406.17557) | F-E, and the stage1.3 prefilter's limits |
| `wettig2024qurating` | 2024 | 6 | QuRating: Selecting High-Quality Data for Training Language Models | arXiv (Cornell University) | [10.48550/arxiv.2402.09739](https://doi.org/10.48550/arxiv.2402.09739) | F-E, the relevance-axis design |

### No DOI resolved (URL only -- book, proceedings or W3C standard; the item itself is the authority)

| id | year | cites | title | venue | DOI | bears |
|---|---|---|---|---|---|---|
| `lancaster1972vocab` | n.d. | — |  | — | [link](https://archive.org/details/vocabularycontro0000lanc) | F-C, F-I |
| `shacl` | n.d. | — |  | — | [link](https://www.w3.org/TR/shacl/) | F-F, BUG-273, BUG-290 |
| `skos` | n.d. | — |  | — | [link](https://www.w3.org/TR/skos-reference/) | F-I, D271c |
| `provo` | n.d. | — |  | — | [link](https://www.w3.org/TR/prov-o/) | F-H / BUG-282 |
| `wagstaff2001constrained` | n.d. | — |  | — | [link](https://dl.acm.org/doi/10.5555/645530.655819) | F-C / D7 (why cluster-derived labelling is rejected) |

---

## Full entries (role reproduced verbatim from the config)

**`yin2019zeroshot`** — https://doi.org/10.18653/v1/d19-1404 · cited 529×

- **Benchmarking Zero-shot Text Classification: Datasets, Evaluation and Entailment Approach** (2019). 
- *why:* Definition-anchored / entailment-based zero-shot classification — the method behind repair R1.
- *bears:* F-C (free-generation labelling), D272c
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`, `ROUNDTABLE_MASTERPROMPT_ONTOLOGY_20260919`

**`lancaster1972vocab`** — <https://archive.org/details/vocabularycontro0000lanc>

- **(unresolved)** (n.d.). 
- *why:* Vocabulary control for information retrieval — the 50-year settlement that curated corpora want controlled vocabularies.
- *bears:* F-C, F-I
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`
- **verification: URL_ONLY** — no DOI resolved for this item; the linked document is the authority

**`nlvscontrolled1998`** — https://doi.org/10.1002/(sici)1097-4571(199808)49:10<881::aid-asi4>3.0.co;2-y · cited 38×

- **Natural language versus controlled vocabulary in information retrieval: A case study in soil mechanics** (1998). Journal of the American Society for Information Science
- *why:* Natural language versus controlled vocabulary in retrieval — the finding is context-dependent; Maxwell OS is the curated case.
- *bears:* F-C
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

**`michie2013bctt`** — https://doi.org/10.1007/s12160-013-9486-6 · cited 8202×

- **The Behavior Change Technique Taxonomy (v1) of 93 Hierarchically Clustered Techniques: Building an International Consensus for the Reporting of Behavior Change Interventions** (2013). Annals of Behavioral Medicine
- *why:* BCTTv1 — the authoritative analogue: 93 consensus-built labels, published per-label reliability, a coding manual, mandatory training. Maxwell OS's RULER_MENUS is its coding manual.
- *bears:* F-F, R5, the whole vocabulary-gate design
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`, `ROUNDTABLE_MASTERPROMPT_ONTOLOGY_20260919`

**`guarino2002ontoclean`** — https://doi.org/10.1145/503124.503150 · cited 767×

- **Evaluating ontological decisions with OntoClean** (2002). Communications of the ACM
- *why:* OntoClean (rigidity / identity / unity / dependence) — the test for why 'typography' is applicable and 'cultural design' is not.
- *bears:* F-F (~10-12 under-defined slots)
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

**`cohen1960kappa`** — https://doi.org/10.1177/001316446002000104 · cited 42317×

- **A Coefficient of Agreement for Nominal Scales** (1960). Educational and Psychological Measurement
- *why:* Cohen's kappa — the agreement coefficient for per-slot reliability.
- *bears:* F-F, the vocabulary acceptance gate
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

**`landis1977kappa`** — https://doi.org/10.2307/2529310 · cited 81232×

- **The Measurement of Observer Agreement for Categorical Data** (1977). Biometrics
- *why:* Landis & Koch — the 0.61 'substantial' threshold adopted as the per-slot acceptance gate.
- *bears:* F-F
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`, `ROUNDTABLE_MASTERPROMPT_ONTOLOGY_20260919`

**`krippendorff2019content`** — https://doi.org/10.4135/9781071878781 · cited 5468×

- **Content Analysis: An Introduction to Its Methodology** (2019). 
- *why:* Content analysis — the reliability framework for human coding; also the source of the 'no spotless without a number' discipline.
- *bears:* F-F, the ruler methodology
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`, `CONTEXT_INDEX`
- *note:* EDITION NOTE: the 4th edition (2019) is cited; the work originates in 1980 and this DOI is the SAGE edition.

**`duque2011oquare`** — https://doi.org/10.1016/j.jss.2011.02.012 · cited 23×

- **Slug Expression Enhances Tumor Formation in a Noninvasive Rectal Cancer Model** (2011). Journal of Surgical Research
- *why:* OQuaRE — SQuaRE-based ontology quality metrics (cohesion, completeness, consistency).
- *bears:* F-F (vocabulary scorecard)
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

**`shacl`** — <https://www.w3.org/TR/shacl/>

- **(unresolved)** (n.d.). 
- *why:* W3C SHACL — the machine-checkable shape contract. config/taxonomy_shacl.ttl already exists in this repo and is unenforced.
- *bears:* F-F, BUG-273, BUG-290
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`
- **verification: URL_ONLY** — no DOI resolved for this item; the linked document is the authority

**`skos`** — <https://www.w3.org/TR/skos-reference/>

- **(unresolved)** (n.d.). 
- *why:* W3C SKOS — prefLabel / altLabel / scopeNote; the authority-control vocabulary for one preferred label plus variants.
- *bears:* F-I, D271c
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`
- **verification: URL_ONLY** — no DOI resolved for this item; the linked document is the authority

**`northcutt2021confident`** — https://doi.org/10.1613/jair.1.12125 · cited 61×

- **Confident Learning: Estimating Uncertainty in Dataset Labels** (2021). Journal of Artificial Intelligence Research
- *why:* Confident Learning / cleanlab — ranks likely-mislabeled rows from existing features and labels, no LLM, fully local.
- *bears:* F-C, the cheap replacement for sample-only auditing
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

**`ratner2020snorkel`** — https://doi.org/10.1007/s00778-019-00552-1 · cited 520×

- **Snorkel: rapid training data creation with weak supervision.** (2020). PubMed
- *why:* Snorkel — weak supervision: many cheap labelling functions combined with learned accuracies. The principled successor to a 999-rule alias table.
- *bears:* F-I (DEFER)
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`
- *note:* VERSION NOTE: the VLDB Journal article (2020) supersedes the 2017 arXiv preprint; cite the journal version.

**`honovich2022true`** — https://doi.org/10.18653/v1/2022.naacl-main.287 · cited 57×

- **TRUE: Re-evaluating Factual Consistency Evaluation** (2022). Proceedings of the 2022 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies
- *why:* TRUE — NLI-based factual-consistency scorers correlate weakly with human judgement. This is the citation that forbids reading an S5 NEUTRAL as FALSE.
- *bears:* F-B / BUG-278 (the quarantine conflation)
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`, `ROUNDTABLE_MASTERPROMPT_ONTOLOGY_20260919`

**`geifman2017selective`** — https://doi.org/10.48550/arxiv.1705.08500 · cited 178×

- **Selective Classification for Deep Neural Networks** (2017). arXiv (Cornell University)
- *why:* Selective classification — abstain by an explicit risk/coverage trade-off rather than an arbitrary threshold.
- *bears:* F-B, D272d
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`
- *note:* arXiv identifier: the NeurIPS 2017 version is the citable one; the arXiv record has the lower citation count (OpenAlex does not merge them).

**`angelopoulos2021conformal`** — https://doi.org/10.48550/arxiv.2107.07511 · cited 28×

- **A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification** (2021). arXiv (Cornell University)
- *why:* Conformal prediction — distribution-free guarantees; how to choose the S5 threshold with a stated error budget.
- *bears:* F-B, D272d
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

**`saracevic2007relevance`** — https://doi.org/10.1002/asi.20682 · cited 226×

- **Relevance: A review of the literature and a framework for thinking on the notion in information science. Part II: nature and manifestations of relevance** (2007). Journal of the American Society for Information Science and Technology
- *why:* Relevance is RELATIONAL (document x user x goal), not an intrinsic property of text. The theoretical basis for a separate, revisable relevance axis.
- *bears:* F-E / BUG-281, D272e
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`, `ROUNDTABLE_MASTERPROMPT_ONTOLOGY_20260919`

**`wettig2024qurating`** — https://doi.org/10.48550/arxiv.2402.09739 · cited 6×

- **QuRating: Selecting High-Quality Data for Training Language Models** (2024). arXiv (Cornell University)
- *why:* QuRating — quality as explicit human-rated criteria plus a trained local judge. The template for turning 'valid fact but irrelevant' into named, ratable criteria.
- *bears:* F-E, the relevance-axis design
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

**`penedo2024fineweb`** — https://doi.org/10.48550/arxiv.2406.17557 · cited 19×

- **The FineWeb Datasets: Decanting the Web for the Finest Text Data at Scale** (2024). arXiv (Cornell University)
- *why:* FineWeb / FineWeb-Edu — a classifier trained on a small labelled set beats regex heuristics for 'is this valuable'.
- *bears:* F-E, and the stage1.3 prefilter's limits
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

**`balog2019pkg`** — https://doi.org/10.1145/3295750.3298922 · cited 54×

- **Task, Information Seeking Intentions, and User Behavior** (2019). 
- *why:* Personal Knowledge Graphs — the closest architectural frame: user-scoped, privacy-bound, non-canonical, assumes personal relevance and personal vocabulary drift.
- *bears:* the mission framing
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

**`acorn2024`** — https://doi.org/10.1145/3654923 · cited 57×

- **ACORN: Performant and Predicate-Agnostic Search Over Vector Embeddings and Structured Data** (2024). Proceedings of the ACM on Management of Data
- *why:* ACORN — predicate-agnostic filtered vector search. The design conclusion that a facet meant to PARTITION must constrain every candidate generator, before truncation.
- *bears:* F-28 / BUG-285 / D273a (the filters do not filter)
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`, `ROUNDTABLE_MASTERPROMPT_ONTOLOGY_20260919`

**`chen2024densex`** — https://doi.org/10.18653/v1/2024.emnlp-main.845 · cited 64×

- **Dense X Retrieval: What Retrieval Granularity Should We Use?** (2024). 
- *why:* Dense X Retrieval — retrieval GRANULARITY: finer self-contained units beat passages, but the unit must stay self-contained.
- *bears:* D273g (the chunk-leg decision)
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`, `ROUNDTABLE_MASTERPROMPT_ONTOLOGY_20260919`

**`karpukhin2020dpr`** — https://doi.org/10.18653/v1/2020.emnlp-main.550 · cited 142×

- **Dense Passage Retrieval for Open-Domain Question Answering** (2020). 
- *why:* DPR — passage-level dense retrieval; the baseline for what 'a retrieval unit' means.
- *bears:* D273g
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

**`khattab2020colbert`** — https://doi.org/10.48550/arxiv.2004.12832 · cited 192×

- **ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT** (2020). arXiv (Cornell University)
- *why:* ColBERT — late interaction over token-level units; the finer-grained alternative to a single pooled vector.
- *bears:* F-31 (only definition is embedded), D273g
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

**`liu2024lostmiddle`** — https://doi.org/10.1162/tacl_a_00638 · cited 1303×

- **Lost in the Middle: How Language Models Use Long Contexts** (2024). Transactions of the Association for Computational Linguistics
- *why:* Lost in the Middle — more context is not better context. Why returning the matched segment with its parent beats returning everything.
- *bears:* D273g
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

**`robertson2009bm25`** — https://doi.org/10.1561/1500000019 · cited 3183×

- **The Probabilistic Relevance Framework: BM25 and Beyond** (2009). Foundations and Trends® in Information Retrieval
- *why:* BM25 / probabilistic relevance — the ranking function under the FTS leg; the reference for keyword-leg weighting in fusion.
- *bears:* F-28 (fusion design)
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

**`cormack2009rrf`** — https://doi.org/10.1145/1571941.1572114 · cited 712×

- **Reciprocal rank fusion outperforms condorcet and individual rank learning methods** (2009). 
- *why:* Reciprocal Rank Fusion — the ORIGINAL RRF paper. search_hybrid already implements Score(d)=sum 1/(k+rank) with k=60, so this is the reference for the fusion that already exists, not a change.
- *bears:* the 'RRF is already correct' finding
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`, `ROUNDTABLE_MASTERPROMPT_ONTOLOGY_20260919`

**`gao2023ragsurvey`** — https://doi.org/10.48550/arxiv.2312.10997 · cited 747×

- **Retrieval-Augmented Generation for Large Language Models: A Survey** (2023). arXiv (Cornell University)
- *why:* RAG survey — the landscape and the standard component decomposition.
- *bears:* the retrieval-programme framing
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

**`chen2024rgb`** — https://doi.org/10.1609/aaai.v38i16.29728 · cited 378×

- **Benchmarking Large Language Models in Retrieval-Augmented Generation** (2024). Proceedings of the AAAI Conference on Artificial Intelligence
- *why:* RGB — noise robustness is the dominant RAG failure mode. Wilson OS has NO retrieval benchmark; this is why one is required.
- *bears:* F-A (measure it), D273a verification
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

**`prietodiaz1991faceted`** — https://doi.org/10.1145/103167.103176 · cited 511×

- **Implementing faceted classification for software reuse** (1991). Communications of the ACM
- *why:* Faceted classification for software reuse — the canonical demonstration that small orthogonal controlled facets scale, and that facets MUST be orthogonal.
- *bears:* F-A, and why 'depth' is not an independent facet
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

**`li2016truthdiscovery`** — https://doi.org/10.1145/2897350.2897352 · cited 431×

- **A Survey on Truth Discovery** (2016). ACM SIGKDD Explorations Newsletter
- *why:* Truth discovery — jointly estimate source reliability and claim truth from agreement, no ground truth needed. The missing implementation behind an empty contradicts_fbs.
- *bears:* F-H, D272f step 6
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

**`paulheim2017kgrefine`** — https://doi.org/10.3233/sw-160218 · cited 1224×

- **Knowledge graph refinement: A survey of approaches and evaluation methods** (2016). Semantic Web
- *why:* Knowledge graph refinement — the standard taxonomy of error detection / completion / repair, and its evaluation methods.
- *bears:* the repair programme's evaluation vocabulary
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`
- *note:* METADATA DISCREPANCY: OpenAlex returns 2016 (online-first); the Semantic Web Journal article is conventionally cited as 2017, 8(1).

**`broder1997resemblance`** — https://doi.org/10.1109/sequen.1997.666900 · cited 1736×

- **On the resemblance and containment of documents** (2002). 
- *why:* Broder shingling/MinHash — near-duplicate detection for work-identity dedup.
- *bears:* F-32 / BUG-289 / D273e (29.1% of convergence is duplicate ingestion)
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`
- *note:* METADATA DISCREPANCY: OpenAlex returns 2002 for this DOI; the paper is from the 1997 Compression and Complexity of Sequences proceedings. Cite as 1997 and treat the fetched year as an indexing artefact.

**`lee2022dedup`** — https://doi.org/10.18653/v1/2022.acl-long.577 · cited 284×

- **Deduplicating Training Data Makes Language Models Better** (2022). Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)
- *why:* Deduplicating training data — measured cost of duplicates in a corpus.
- *bears:* F-32, D273e
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

**`fellegi1969recordlinkage`** — https://doi.org/10.1080/01621459.1969.10501049 · cited 2439×

- **A Theory for Record Linkage** (1969). Journal of the American Statistical Association
- *why:* Fellegi & Sunter — probabilistic record linkage with clerical review. The basis for the identity layer (Splink line of work) and for fuzzy work-identity matching.
- *bears:* D271c, D273e
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`, `DECISION_D271_IDENTITY_20260917`

**`winograd1971`** — https://doi.org/10.1145/362384.362685 · cited 5302×

- **A relational model of data for large shared data banks** (1970). Communications of the ACM
- *why:* Codd's relational model — the object/property logic the schema already follows; cited to show the schema need not be re-engineered.
- *bears:* no restructuring required
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

**`hogan2021knowledgegraphs`** — https://doi.org/10.1145/3447772 · cited 1811×

- **Knowledge Graphs** (2021). ACM Computing Surveys
- *why:* Knowledge Graphs (Hogan et al.) — the reference definition of a graph-structured KB; the frame for using the existing 164,202 edges in retrieval.
- *bears:* the graph-is-built-and-unused finding
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`
- *note:* METADATA DISCREPANCY: OpenAlex returns 2021; the ACM Computing Surveys issue is 54(4), 2022. Cite as 2021.

**`provo`** — <https://www.w3.org/TR/prov-o/>

- **(unresolved)** (n.d.). 
- *why:* W3C PROV-O — entity/activity/agent provenance. R14 demands it; the provenance column currently holds one constant for 100% of rows.
- *bears:* F-H / BUG-282
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`
- **verification: URL_ONLY** — no DOI resolved for this item; the linked document is the authority

**`gilardi2023chatgpt`** — https://doi.org/10.1073/pnas.2305016120 · cited 1100×

- **ChatGPT outperforms crowd workers for text-annotation tasks** (2023). Proceedings of the National Academy of Sciences
- *why:* ChatGPT outperforms crowd workers on text-annotation tasks — the evidence that an LLM annotator can be viable, WITH the reliability caveats.
- *bears:* the S4/R5 design, BUG-269 (report against the constant-answer baseline)
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

**`zheng2023llmjudge`** — https://doi.org/10.48550/arxiv.2306.05685 · cited 492×

- **Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena** (2023). arXiv (Cornell University)
- *why:* LLM-as-a-Judge (MT-Bench) — including the documented position/verbosity/self-enhancement biases. The basis for judging judges and for cross-family verification (R5/C8).
- *bears:* BUG-269, the R5 protocol
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`
- *note:* arXiv identifier: the NeurIPS 2023 Datasets and Benchmarks version is the citable one.

**`wagstaff2001constrained`** — <https://dl.acm.org/doi/10.5555/645530.655819>

- **(unresolved)** (n.d.). 
- *why:* Constrained K-means with must-link/cannot-link — the only peer-reviewed way to inject ontology into clustering. Produces discipline-pure clusters, NOT a label from the cluster.
- *bears:* F-C / D7 (why cluster-derived labelling is rejected)
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`
- **verification: URL_ONLY** — no DOI resolved for this item; the linked document is the authority

**`campello2013hdbscan`** — https://doi.org/10.1007/978-3-642-37456-2_14 · cited 2548×

- **Density-Based Clustering Based on Hierarchical Density Estimates** (2013). Lecture notes in computer science
- *why:* HDBSCAN — density-based clustering with stability. Removed by D2120/D2198 for reproducibility; DEFER as a stability MEASUREMENT only.
- *bears:* F-C, §2.1 of the forensic
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

**`grootendorst2022bertopic`** — https://doi.org/10.48550/arxiv.2203.05794 · cited 1388×

- **BERTopic: Neural topic modeling with a class-based TF-IDF procedure** (2022). arXiv (Cornell University)
- *why:* BERTopic — c-TF-IDF topic representation, the standard way to NAME a cluster. The step stage 2 currently skips.
- *bears:* F-C (cluster naming)
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

**`wong2012ontologylearning`** — https://doi.org/10.1145/2333112.2333115 · cited 389×

- **Ontology learning from text** (2012). ACM Computing Surveys
- *why:* Ontology learning from text — the survey for growing the vocabulary from the corpus (DEFER until application reliability is fixed).
- *bears:* F-F, D272f step 12
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

**`shen2020taxoexpan`** — https://doi.org/10.1145/3366423.3380132 · cited 56×

- **TaxoExpan: Self-supervised Taxonomy Expansion with Position-Enhanced Graph Neural Network** (2020). 
- *why:* Taxonomy expansion — self-supervised placement of a new label into an existing taxonomy.
- *bears:* F-F, D272f step 12
- *cited in:* `MARKET_RESEARCH_ONTOLOGY_20260919`

---

## How to reproduce

```bash
python3 scripts/build_reference_library.py            # fetch every DOI from OpenAlex, then render
python3 scripts/build_reference_library.py --cached    # re-render from the JSON snapshot (offline)
python3 scripts/build_reference_library.py --check     # fetch and report, write nothing
```
