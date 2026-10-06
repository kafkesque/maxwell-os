# Taxonomy Evolution / Label Promotion / Drift Detection — Tooling & Literature
Subagent 20261004_3 · 2026-10-04 · verified via GitHub API + arXiv (licenses below are as returned by the GitHub API on 2026-10-04)

## 0. TL;DR — the 5-stage loop mapped to tools

```
raw-label harvest  ->  support threshold  ->  candidate promotion  ->  owner ratification  ->  menu version bump
     (drift)              (coverage)            (novelty score)          (audit)               (hash re-mint)
```

| Stage | Primary tool | Secondary |
|---|---|---|
| raw-label harvest / drift | **River** ADWIN + KSWIN + PageHinkley on per-axis label distribution | Evidently `DataDriftPreset` (embeddings), PSI, JS-divergence |
| support threshold | `fbs` SQL GROUP BY + min_raw_instances (already: `config/emerging_disciplines.yaml`) | **LABELSHIFT** / BBSE for prior shift correction |
| candidate promotion | **hdbscan + BERTopic** over unmapped/abstained rows in existing **bge-m3 512d** space; novelty = 1 − max cosine to known centroids | **TaxoExpan** (WWW 2020) for parent placement scoring |
| challenger / audit | **cleanlab** `find_label_issues` + `Datalab` | **co-teaching** (Han 2018), Snorkel/skweak LFs |
| owner ratification | **pySHACL** against existing `config/taxonomy_shacl.ttl` | Snorkel label model for agreement margin |
| menu version bump | **menu_axis_hashes.py** + `closed_menu_v5.sha256` + **D-353 re-mint rule** (already built) | ROBOT `reason`/`report`, Confluent-style compatibility levels, SNOMED conceptual model |

**Blocking prerequisite (measured, from `config/label_provenance.yaml`):** `menu_hash` is NULL on 7,995/7,995 rows and `content_type_source` / `discipline_source` / `extraction_type_source` are empty on all rows. **Drift detection across menu versions is undefined until menu_hash is backfilled** — you cannot attribute a label shift to corpus vs. menu without it. This is the single highest-leverage fix before any tool below delivers value.

---

## 1. Concept drift detection in text classification

### 1.1 River — `online-ml/river` (BSD-3-Clause, 6.1k★, pure Python, offline)
- **Drift module:** `ADWIN`, `KSWIN`, `DDM`, `EDDM`, `PageHinkley`, `CUSUM`, `HDDM_A/W`. All expose `update(x) -> bool / .drift_detected`.
- **ADWIN**: Bifet & Gavaldà, *Learning from Time-Changing Data with Adaptive Windowing*, SIAM SDM 2007. Adaptive window, theoretical false-positive/negative guarantees; no hyperparameter tuning beyond δ.
- **DDM**: Gama, Medas, Castillo, Rodrigues, *Learning with Drift Detection*, SBIA 2004. Monitors error rate; warning + drift levels.
- **Page-Hinkley / CUSUM**: Page, *Continuous Inspection Schemes*, Biometrika 42(1), 1954. Detects change in mean of a monitored statistic.
- **KSWIN**: two-sample KS test on two sliding windows.
- **Offline / Python:** yes / yes (`pip install river`). No API calls, no GPU.
- **Plug-in:** run per-axis (domain, discipline, content_type, extraction_type) on the **stream of labels emitted per corpus batch**. Observation variable choice matters: a 2024 DiVA thesis (*Concept Drift Detection in Document Classification*, diva-portal.org/smash/get/diva2:1867280) compared ADWIN/KSWIN/PageHinkley with inputs {prediction accuracy, confidence, predicted label} and found the **predicted-label stream** to be the most sensitive for label-distribution shift — exactly the Maxwell case (no ground-truth accuracy available in production). One detector per axis, thresholds in YAML, not code (C12).

### 1.2 KSWIN / two-sample tests on embeddings
- Direct alternative: KS-test on **bge-m3 512d projected to a scalar** (per-dimension KS, Bonferroni-corrected), or MMD / LSDD on the embedding cloud. Reference implementation: `alibi-detect` (see 1.4).
- **Plug-in:** reference = classification-time embedding distribution of a frozen month; current = new corpus. Detects *input* drift before labels shift, giving earlier warning.

### 1.3 Population Stability Index (PSI)
- Siddiqi, *Credit Risk Scorecards*, Wiley 2006 (origin); Yurdakul, *Statistical Properties of Population Stability Index*, WMU 2018 (theoretical properties, peer-reviewed thesis).
- PSI = Σ (A%−E%)·ln(A%/E%). Rule of thumb <0.1 stable, 0.1–0.25 moderate, >0.25 shift. **Zero dependencies — implement in ~15 lines; but per C12, put the 0.1/0.25 cut points in YAML.**
- **Plug-in:** per-axis PSI(menu v5 vs v6 label distribution) is the cheapest promotion trigger and is directly comparable to the existing per-axis hashes.

### 1.4 Evidently — `evidentlyai/evidently` (Apache-2.0, 8.0k★, Python, fully offline)
- 100+ metrics; `DataDriftPreset` for tabular **and text** (added v0.2.2, Jan 2025); classifier drift; text descriptors; `LabelDrift` metric; supports embedding-based drift via a `TextDescriptor`. Model-based drift: trains a discriminator between reference/current — reported as significant if it can tell them apart.
- **Caveat (C28):** large dependency surface (pandas/plotly/nltk); use CLI/`Dataset` API rather than notebooks.
- **Plug-in:** scheduled weekly report over the `fbs` table by `pipeline_run_id`; output JSON consumed by the promotion script, not by humans.

### 1.5 Label shift specifically (the correct formalism for "labels moved")
- Lipton, Wang, Smola, *Detecting and Correcting for Label Shift with Black Box Predictors* (BBSE), ICML 2018.
- Saerens et al., *Adjusting the Outputs of a Classifier to New a Priori Probabilities*, Neural Computation 2002 (EM prior correction).
- Alexandari et al., *Maximum Likelihood with Bias-Corrected Calibration is Hard-To-Beat at Label Shift Adaptation*, ICML 2020 (Calibrated EM / MLLS).
- `LABELSHIFT` reference implementation: Tahmasbi et al., *A Unified Evaluation of Classification under Label Shift* (arXiv 2020) — pure numpy/sklearn.
- **Plug-in:** gives a *significance test* (BBSE has a χ² test) for "the label distribution has genuinely shifted" vs. sampling noise — this is the statistically defensible form of the "support threshold" gate.

### 1.6 Deprecated
- `scikit-multiflow/scikit-multiflow` (BSD-3-Clause, 798★) — superseded by **River** (same authors). Use only if a paper reproduces on it. Successor for MOA semantics: **CapyMOA** (`adaptive-machine-learning/CapyMOA`, BSD-3-Clause, 151★).

---

## 2. Open-world / open-set / novel class discovery (NCD)

| Paper | Venue | What it decides | Relevance |
|---|---|---|---|
| Bendale & Boult, *Towards Open World Recognition* | CVPR 2015 | Introduces OpenMax: **EVT-calibrated tail probability over activation vectors** → "none of the above" | The canonical "reject then promote" protocol |
| Scheirer et al., *Meta-Recognition: The Theory and Practice of Recognition Score Analysis* | IEEE TPAMI 2013 | EVT/Weibull tail fitting for open-set risk | Statistical basis for novelty thresholds |
| Geng, Huang, Chen, *Recent Advances in Open Set Recognition: A Survey* | IEEE TPAMI 2021 (arXiv:1811.08581 ✅) | Taxonomy of OSR methods, risk formulation | Survey entry point |
| Yang, Zhou, Li, Liu, *Generalized Out-of-Distribution Detection: A Survey* | IJCV 2024 (arXiv:2110.11334 ✅) | Unifies OOD/OSR/anomaly detection; scores: MSP, ODIN, Energy, Mahalanobis, KNN | Score menu to pick a novelty scorer |
| Vaze et al., *Generalized Category Discovery* | CVPR 2022 | Discovers novel classes **and** classifies known ones, with only known-class labels; auto-estimates #classes by k-means on semi-supervised features | The closest fit to "promote some harvested clusters, keep the rest unknown" |
| *Unified Open-Set Recognition and Novel Class Discovery* | MDPI Applied Sciences 15(21):11468, 2025 | Single framework automating OSR→NCD handoff | Recent unification |
| `JosephKJ/Awesome-Novel-Class-Discovery` | GitHub (survey repo) | Living bibliography | Tracking |

**How a cluster is judged to "deserve" a class** — the recurring decision recipe:
1. **Reject** items whose novelty score exceeds an EVT/threshold calibrated at a target FPR (OpenMax, Meta-Recognition).
2. **Cluster** the rejected pool (density-based, `hdbscan`, BSD-3-Clause, 3.2k★).
3. **Estimate k** by the **gap statistic / silhouette / Dirichlet-Process mixture** — not by fixing k.
4. **Score cohesion + separation**: intra-cluster silhouette vs. distance to nearest known centroid (Mahalanobis, not cosine, if embeddings are whitened).
5. **Require a stable support floor over ≥2 independent harvest batches** — this is the operational reading of `min_raw_instances_to_promote: 25` in `config/emerging_disciplines.yaml`.

**Local/offline:** all methods are offline; only the classifiers need training. Python: `hdbscan`, `BERTopic` (`MaartenGr/BERTopic`, MIT, 7.9k★ — has `topics_over_time` for emerging-topic tracking), `pyod` for novelty scores.

**Plug-in (Maxwell-specific, zero new model cost):** the pipeline already computes **bge-m3 512d Matryoshka** embeddings in `stage1_5_embed_cluster.py`. Reuse them: the "unknown class discovery" step is then a pure in-repo script — cosine to frozen per-axis centroids, threshold in YAML, hdbscan over the tail. No new dependency, no API, $0 marginal.

---

## 3. Automated taxonomy expansion / label induction

| System | Citation | Mechanism | Score for a candidate node |
|---|---|---|---|
| **TaxoExpan** | Shen, Shen, Xiong, Wang, *Self-supervised Taxonomy Expansion with Position-Enhanced Graph Neural Network*, **WWW 2020** (arXiv:2001.09522 ✅; repo `mickeysjm/TaxoExpan`, Apache-2.0). ⚠️ **Not SIGIR** — the task brief is wrong on venue; WWW '20. | Position-enhanced GNN over the existing taxonomy graph + term embeddings; **self-supervised**: existing edges are the training signal | `P(term t attaches as child of existing node x)`; top-k parents |
| **TaxoGen** | Zhang et al., *TaxoGen: Unsupervised Topic Taxonomy Construction by Adaptive Term Embedding and Clustering*, KDD 2018 | Recursive clustering of terms with adaptive embeddings | cluster cohesion/local + global term score |
| **HiExpan** | Shen et al., *HiExpan: Task-Guided Taxonomy Construction by Hierarchical Tree Expansion*, KDD 2018 | Iteratively expands seed taxonomy via auxiliary corpus | co-occurrence + sibling-similarity score |
| **TaxoCom** | KDD 2022 | Discovers *pseudo-hierarchy* latent in a corpus, then recovers taxonomy | latent-topic hierarchy score |
| **CoRel** | WWW 2022 | Relation-based + topical expansion; argues topical models alone miss relations | combined relation/topic prior |
| **OntoGen** | Fortuna, Grobelnik, Mladenič, *OntoGen: Semi-automatic Ontology Editor*, HCI 2007 | Concept + instance suggestion from a corpus | centroid closeness to concept |

**Offline/Python:** TaxoGen/CoRel have reference code; TaxoExpan is PyTorch + Gensim, offline; all train locally on CPU or the local GPU.

**Plug-in:** TaxoExpan's self-supervised framing is the direct answer to "how do we score a candidate new node". Concretely: freeze `config/taxonomy_v5.yaml` as the graph, feed harvested raw-label terms + their bge-m3 embeddings, get a **parent-attachment score** per candidate; route to owner ratification with (candidate term, proposed parent, score, support count, 3 exemplar FBs). Note that the Maxwell 4-axis structure (`menu_axis_groups.yaml`: answer_space / definition_axes / housekeeping) means each axis is its own taxonomy graph — run the scorer per axis.

---

## 4. Weak supervision / programmatic labeling

| Tool | Citation | License | Offline |
|---|---|---|---|
| **Snorkel** | Ratner et al., *Snorkel: Rapid Training Data Creation with Weak Supervision*, VLDB 2018 (arXiv:1711.10160) | Apache-2.0 (`snorkel-team/snorkel`, 6.0k★) | yes |
| **Data Programming** (the label model) | Ratner, De Sa, Wu, Selsam, Ré, NeurIPS 2016 | — | yes |
| **Snorkel MeTaL** | Ratner et al., *Training Complex Models with Multi-Task Weak Supervision*, AAAI 2019; repo `HazyResearch/metal` | Apache-2.0 (PyPI `snorkel-metal`) | yes, but **unmaintained since 2019** |
| **Snorkel DryBell** | Bach et al., SIGMOD 2019 | — | industrial case study |
| **skweak** | Lison, Barnes, Hubin, *skweak: Weak Supervision Made Easy for NLP*, ACL 2021 demo (arXiv:2104.09683 ✅) | MIT (`NorskRegnesentral/skweak`, 925★) | yes; spaCy-based |
| **FlyingSquid** | Fu et al., *Fast and Three-cious: Speeding Up Weak Supervision with Triplet Methods*, ICML 2020 | Apache-2.0 (HazyResearch) | yes |
| **Weasel** | — | — | interactive LF labelling UI |

**The key property for taxonomy evolution:** a labeling function (LF) is just a function `x → label | ⊥`. **Adding a new candidate label means adding a new LF column**, not relabeling the corpus — the label model re-estimates LF accuracies/correlations and produces new probabilistic labels for *all* rows. That is precisely the "add a label without relabeling everything" requirement.

**Plug-in:** build a `labeling_functions.yaml` where each LF is a declared, versioned, deterministic or LLM-backed voter (e.g. `regex_match`, `knn_vote`, `gpt_oss_20b_judge`, `qwen3coder_oneshot`). Use Snorkel's label model to produce (a) probabilistic labels and (b) **LF agreement margin** — low-margin rows are the ratification queue. skweak is the lighter option and integrates with spaCy; Snorkel has the multi-task (MeTaL) structure that maps naturally onto the 4 axes.

**C12 note:** LF parameters (thresholds, patterns, prompts) must live in YAML; the label model is a fixed, pinned algorithm.

---

## 5. Mislabel detection / label auditing

| Item | Citation | License | Offline |
|---|---|---|---|
| **Confident Learning** (theory) | Northcutt, Jiang, Chuang, *Confident Learning: Estimating Uncertainty in Dataset Labels*, **JAIR 2021** (arXiv:1911.00068 ✅) | — | — |
| **cleanlab** (implementation) | `cleanlab/cleanlab` (Apache-2.0, 11.7k★) | Apache-2.0 | yes, pure Python |
| **Rank Pruning** | Northcutt, Wu, Chuang, *Learning with Confident Examples*, UAI 2017 | — | — |
| **Co-teaching** | Han et al., NeurIPS 2018; *Co-teaching+*, ICLR 2019; *DivideMix*, ICLR 2020 | — | yes (needs local GPU) |
| **Calibration reference** | Guo et al., *On Calibration of Modern Neural Networks*, ICML 2017 (ECE) | — | yes |

**What cleanlab does:** computes the **confident joint** `C[y_given][y_pred]` (out-of-sample predicted probabilities), then flags `find_label_issues()` — items whose given label sits in an off-diagonal cell with excess mass. Gives per-item `label_quality_score` and, via `Datalab`, a ranked issue list with issue type (wrong label / outlier / near-duplicate / ambiguous).

**Plug-in (this is the "challenger model" ask):** run cleanlab over `fbs` where `*_source` is non-empty and confidence is available, using the **S4 classifier's cross-validated `pred_probs`**. The generator≠verifier rule (R5) is satisfied because cleanlab's statistics are a different mechanism from the LLM that produced the label. Output → ratification queue, *not* auto-mutation (C15/no-silent-repair). Cheaper alternative if `pred_probs` are unavailable: **agreement-tee** across the existing generator + DeBERTa S5 verifier + kNN arm — disagreement = audit candidate.

---

## 6. Ontology evolution / versioning / consistency checking

### 6.1 Peer-reviewed foundations
- Zablith, Antoniou, d'Aquin, Flouris, Kondrakis, Motta, Plexousakis, Sabou, *Ontology evolution: a process-centric survey*, **The Knowledge Engineering Review** (Cambridge), 2015 — the canonical process model: *change capture → change representation → semantics of change → change implementation → change propagation → change validation*.
- *Ontology Evolution: A Survey and Future Challenges* (Springer, 2009) — versioning/merging/integration taxonomy.
- Stojanovic et al., *Change Management in Ontology Evolution* (2002); Klein & Fensel, *Ontology Versioning on the Semantic Web* (2001).
- **"Ontology drift"** is most rigorously treated in the biomedicine/standards literature: **SNOMED CT concept inactivation** with historical associations (`SAME AS`, `REPLACED BY`, `POSSIBLY EQUIVALENT TO`, `MOVED TO`), quarterly international releases; MedDRA versioning with mandatory cross-version mapping; ICD-9→ICD-10 crosswalks. **These are the concrete, ratified practice for deprecating/promoting a label while preserving history** — a direct template for the Maxwell "menu version bump".

### 6.2 Tools (all local/offline)
| Tool | License | Lang | Role |
|---|---|---|---|
| **Protégé** (`protegeproject/protege`) | MPL 2.0 (API returns NOASSERTION; repo LICENSE is MPL-2.0) | Java | Editing, diff/versioning plugins, reasoner integration |
| **ROBOT** (`ontodev/robot`) | **BSD-3-Clause** ✅ | Java (CLI) | `robot reason`, `robot report` (consistency/obsolete-term/duplicate-label checks), `robot merge/diff`, OBO release workflow |
| **ELK** (`liveontologies/elk-reasoner`) | **Apache-2.0** ✅ | Java | Fast OWL 2 EL reasoner; thousands of classes/sec |
| **HermiT** | LGPL-3.0 | Java | Full OWL 2 DL reasoner; catches inconsistency Protégé displays |
| **pySHACL** (`RDFLib/pySHACL`) | **Apache-2.0** ✅ | Python | Hosted Python SHACL validation — **and `config/taxonomy_shacl.ttl` already exists in this repo** |
| **rdflib** (`RDFLib/rdflib`) | BSD-3-Clause ✅ | Python | Turtle/OWL parsing, graph diffs |
| **owlready2** | LGPL-3.0 | Python | OWL 2 in Python, can drive HermiT/Pellet via Java gateway |

**Plug-in (highest ROI, lowest effort):** `config/taxonomy_v5.yaml` → Turtle → validate with **pySHACL against the existing `config/taxonomy_shacl.ttl`**; add a `robot reason` step (ELK for speed) that fails the version bump if the new menu is **inconsistent** or if a promoted label has no disjointness/coverage declaration. Then `robot diff` v5↔v6 to emit the machine-readable change set that the ratification record cites. This gives "consistency checking after a taxonomy change" without leaving Python except for the JVM reasoner (or skip the JVM: SHACL alone already catches most shape violations — C28 quality-tiering says start with pySHACL).

---

## 7. Deterministic regression / hash-pinning

### 7.1 Peer-reviewed and normative backing
- Lamb & Zacchiroli, *Reproducible Builds: Increasing the Integrity of Software Supply Chains*, IEEE Software 2021/2022 — the canonical argument for byte-identical rebuilds and content-addressing.
- Pineau et al., *Improving Reproducibility in Machine Learning Research (Report from the ML Reproducibility Challenge)*, JMLR 2021 — the reproducibility checklist (pinned data splits, seeds, versions).
- Raff, *A Step Toward Quantifying Independently Reproducible Machine Learning Research*, NeurIPS 2019 — reproducibility requires a single command + pinned inputs.
- Merkle, *A Digital Signature Based on a Conventional Encryption Function*, CRYPTO 1987 — hash trees; the basis for axis-wise hashing.
- Schema-evolution determinism analog: **Apache Avro schema resolution** and **Confluent Schema Registry compatibility levels** (BACKWARD / FORWARD / FULL / NONE) — the missing vocabulary for a "label promotion compatibility gate".

### 7.2 What Maxwell OS already has (verified in-repo, on 2026-10-04)
| Artifact | Evidence | What it gives you |
|---|---|---|
| `config/closed_menu_v5.json` + `config/closed_menu_v5.sha256` = `73597ee2…89df6f` | file present | Whole-menu content hash |
| `config/menu_axis_hashes.yaml` | generated by `scripts/menu_axis_hashes.py`, 2026-09-25; per-axis sha256 (`abstention`, `content_types`, `decision`, `disciplines`, `domains`, …) | **Per-axis Merkle-style pinning** — exactly Reproducible-Builds practice applied to a taxonomy |
| `config/recalibration_pins.yaml` + **D-353** | tri-state scan (0 clean / 1 broken / 2 owner owes re-measure), pre-commit write gate refuses either | Any change to a pinned artifact requires a **new decision id** in the same commit — a re-pin is a re-mint (BUG-535) |
| `config/pipeline_config.yaml` / R7 | temp=0.0 | Generation determinism |
| R14 | every persistent object stamped `schema_version`, `gen_model`, `pipeline_commit` | Provenance pinning |
| `config/golden/gold_frozen.yaml`, `config/golden/stage4_golden.yaml`, `evals/` | present | Golden-set regression harness |
| `config/eval_integrity.yaml` | floors + provenance tier vocabulary | Ratchet floors so a menu bump cannot regress eval |

### 7.3 Gaps / recommendations
1. **Backfill `menu_hash` on all 7,995 `fbs` rows** (currently NULL everywhere) — without it, drift between menu versions is unmeasurable and the F-44 `min_human_share` gate is undefined. This is the precondition for sections 1–5 to mean anything.
2. Add `menu_hash` + `pipeline_commit` + `gen_model` + `seed` to the **golden-set regression**: re-classify `gold_frozen.yaml`, require bit-identical labels or an explicit decision id.
3. Version the **prompt templates and LF configs** with their own sha256 (`config/prompts/*.sha256`) — a change in a prompt is a change in the classifier.
4. Adopt **DVC** (`treeverse/dvc`, Apache-2.0, 15.9k★) if you want lock-file determinism for the corpus graphs (`dvc.lock` contains hashes of inputs/params/outputs) — or keep the lighter in-repo `sha256` + pre-commit gate already built. C28 says stay with what exists unless a real need appears.
5. Define **compatibility levels** for the menu (à la Confluent): a promotion is `BACKWARD-compatible` if every existing FB's `menu_hash` still resolves (label retained or mapped via `menu_merge_map.yaml`); otherwise it is a **breaking epoch bump** requiring owner ratification + a crosswalk.

---

## 8. Recommended minimal stack (local, $0 marginal, Python-first, config-driven)

| Need | Pick | Why |
|---|---|---|
| Drift on label distribution | **River** (BSD-3) `ADWIN` + `KSWIN`, one per axis | Pure Python, no deps, per-axis, offline |
| Drift on embeddings | **River/alibi-free**: KS + MMD on existing bge-m3 vectors; optionally **Evidently** (Apache-2.0) for reporting | Reuses `stage1_5` output |
| Label-shift significance | **BBSE / LABELSHIFT** (numpy) | Statistical test, not a heuristic |
| Novel class candidate | **hdbscan** (BSD-3) + **BERTopic** (MIT) + nearest-centroid novelty | Reuses bge-m3 cache; no training |
| Parent placement score | **TaxoExpan** (Apache-2.0, WWW 2020) | Purpose-built, self-supervised |
| Add-label-without-relabel | **Snorkel** (Apache-2.0) or **skweak** (MIT) | LF columns = new labels |
| Mislabel audit | **cleanlab** (Apache-2.0) | Confident Learning, JAIR 2021 |
| Taxonomy consistency | **pySHACL** (Apache-2.0) vs existing `taxonomy_shacl.ttl`; **ROBOT+ELK** if OWL reasoning needed | Python-first, JVM optional |
| Determinism | existing `menu_axis_hashes.py` + `closed_menu_v5.sha256` + D-353 re-mint | Already built and enforced |

**Do not adopt:** `alibi-detect` under its current license (Seldon custom/BUSL-style, **not OSI-open** — flagged, breaks C2); `scikit-multiflow` (superseded by River); `snorkel-metal` (unmaintained since 2019, use `snorkel`).

**Rejected-by-design:** any API-hosted drift service (Arize, Fiddler, WhyLabs, DataRobot) — violates C1 (sovereign/$0) unless self-hosted, and they add a second source of truth.

## 9. Corrections to the task brief
1. **TaxoExpan is WWW 2020, not SIGIR 2020** (verified: arXiv:2001.09522, "Self-supervised Taxonomy Expansion with Position-Enhanced Graph Neural Network").
2. **scikit-multiflow is effectively deprecated**; River is the successor (BSD-3, same lineage).
3. **alibi-detect is not Apache-2.0 anymore** — Seldon custom license; not usable under a no-vendor-lock-in rule without review.
4. "Confident learning" = Northcutt, Jiang, Chuang, **JAIR 2021** (arXiv:1911.00068 ✅) — confirmed.
5. `snorkel-metal` has no maintenance since 2019 — MeTaL's ideas survive in the main `snorkel` repo.

*Verified via GitHub REST API (`/repos/{owner}/{repo}` license + stars) and arXiv `citation_title` metadata on 2026-10-04. Search via the `web-search` skill (DuckDuckGo path).*
