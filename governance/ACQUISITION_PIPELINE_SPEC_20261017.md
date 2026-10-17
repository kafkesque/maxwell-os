# The Acquisition Pipeline — full spec (knowledge gap → literature → bytes → corpus)

> **Written** 2026-10-17, in answer to: *"an agnostic webscraping / CLI / MCP tool that goose can instruct to
> download books from the FMHY reading list, triggered by the knowledge layer when it cannot back a claim"*.
> **Status: SPEC + ONE DECISION (D-3078).** Nothing in the acquisition lane is implemented and nothing may be
> until the owner words it: this document exists so the thing that eventually gets built is the thing Maxwell
> already has a place for, rather than a second pipeline beside it.
>
> Every external claim below carries the reading that re-takes it (D-3034). Every Maxwell internal (file, class,
> count) was read from this repo on 2026-10-17, not remembered.

---

## 0. Verdict

**Viable: yes. Feasible: yes. Worth building in this shape: yes — but not as a downloader.**

Three corrections to the framing, before any code. The first two come from the research that preceded this
document; the third is the one that decides whether this lands inside Maxwell or beside it.

**Correction 1 — "multiple pirate sites" is the wrong shape.** Anna's Archive is a *superset index* over LibGen
and much of Z-Library. Writing ten adapters is ten copies of one fact with ten failure modes. What is needed is
**one resolver over three adapters** (and the lawful lane is not a courtesy, it is the cheapest adapter: it needs
no mirror, no key and no health poll).

**Correction 2 — "guaranteed agentic-readable quality" is a filter, not a source.** Sourcing yields bytes; EPUB
yields text; PDF yields a coin flip. The guarantee can only be produced by a gate that *rejects*, and Maxwell
already owns that gate on the container axis (D-3077, `config/pipeline_config.yaml#stage0.containers`).

**Correction 3 — the biggest one, and it is architectural: everything downstream of the bytes already exists.**
The ingest door (`pipeline/ingest_gate.py`, D-2997/D-3050), the admission plan/sign/apply lane
(`scripts/plan_admission.py`, `scripts/apply_admission.py`, T-181/T-183), the container probes
(`pipeline/container_integrity.py`, D-3071/D-3075) and the 8-stage pipeline all take over the moment a file
appears in a **declared arrival pen**. Therefore:

> **D-3078 — AN ACQUIRER'S RECEIPT IS A FILE IN A PEN, NEVER A ROW IN THE CORPUS.**
> The acquisition layer terminates at `source_library.placement.pens`. It may not write `knowledge pipeline/books`,
> may not create an `.md`, may not sign, may not convert. The door stays the only way in — because the door is the
> only thing that carries identity, probe, owner word, digest and receipt, and a second way in would make the first
> one deaf (BUG-851 is the measured shape of that deafness).

That single invariant is why this pipeline can be large without being a risk: **a bad acquisition costs a pen
file the owner can delete, never a corpus object the owner cannot untangle.**

---

## 1. What Maxwell already has (and what the spec is therefore NOT allowed to rebuild)

| Existing thing | Home | What it already answers | The spec must NOT re-implement |
|---|---|---|---|
| Arrival pens + placement | `config/ingest_identity_gate.yaml#source_library.placement` | where a file may sit, and that no engine moves it by name | a "downloader folder" |
| Container probes (5: zip/pdf/mobi/ole/none) | `pipeline/container_integrity.py` | is this file openable, named by a declared defect | an "is this a good PDF" heuristic |
| Reader registry (11 containers) | `config/pipeline_config.yaml#stage0.containers` + `pipeline/stage0_convert.py` | can S0 open it, and with which engine | a converter |
| Identity / delta / duplicates | `pipeline/ingest_gate.py`, `governance/duplicate_adjudication.json` | is this work already here, under any name | a deduper |
| Owner-gated writes | `scripts/plan_admission.py` → `ADMISSION_PLAN` → sign → `apply_admission.py` | nothing enters without a human word and a receipt | an auto-importer |
| Starvation census | `scripts/plan_targeted_ingestion.py`, `governance/targeted_ingestion_plan.json` | **18 starved disciplines, 9 CRITICAL** (convergent ≤ 3) | a gap detector, for class (a) |
| Residual coverage | `pipeline/coverage_check.py` (D2149) | singletons / uncovered embedding regions | a coverage instrument |
| Route graph + receipts | `config/capability_registry.yaml`, `scripts/resolve_route.py` | which capability owns which entry point, check, receipt, cost tier | a plugin registry |
| Delegated-run trace | `scripts/delegate_journal.py` (T-168/D-3036) | a run declares purpose/model/budget/files BEFORE it runs | an "agent log" |
| Source map for starved domains | `governance/targeted_ingestion_sources.md` (D2607-D, D-2897) | which feeds supply the 8 CRITICAL disciplines (**finding: `feed.opml` covers none of them**) | a curated source list |

**The measured consequence.** The one live reading of starvation says 18 disciplines have fewer than 10 golden
examples and 9 have ≤ 3 convergent FBs. That is a *knowledge-layer* gap of exactly the kind the owner described —
and it is already counted, already owned, and has no acquisition engine behind it. The missing piece is not
detection. It is **translation**: a starved discipline is not a book title. Turning `design psychology (4 golden,
1 convergent, shortfall 19)` into *"these 6 works, in this order, in these formats"* is the new work, and it is
the only genuinely new work.

---

## 2. The three capabilities (and nothing else)

Each is declared in `config/capability_registry.yaml` with kind, entrypoint, **check**, receipt and cost tier —
a capability with no control is a comment (BUG-492), and this spec refuses to add three of those.

### 2.1 `gap_reader` (T0, deterministic, writes ONE record)

**Job:** turn a *task* into a **gap record** — never a book list, never prose.

Three declared gap classes, each with a measured trigger. All three read instruments that exist:

| Class | Trigger (measured, not judged) | Instrument |
|---|---|---|
| `discipline_starvation` | golden < 10 or convergent ≤ 3 for the discipline the task resolves to | `plan_targeted_ingestion.py` (18/9 today) |
| `primitive_absence` | top-k retrieval max cosine < τ **or** 0 convergent FBs above the floor | FAISS index + `is_convergent` |
| `claim_unsupported` | the answer's claims have no NLI-entailing passage at the declared threshold | `stage5_verify.py` (DeBERTa-v3-large, fail-closed) |

**The record** (JSON, one file per gap, stamped R14: `schema_version`, `gen_model`, `pipeline_commit`):

```
{gap_id, task_ref, classes:[...], evidence:{retrieval_ids, scores, golden/convergent counts},
 sub_questions:[...], discipline, domain, requested_at, corpus_fingerprint}
```

τ is **declared in YAML and calibrated**, never a literal in code (C12). The `corpus_fingerprint` is what makes a
gap record *expire*: a gap measured against a corpus that has since grown is not a gap any more, and the record
must say which corpus it was measured against.

**Why a separate capability from the advisory agent.** The owner's framing was "the knowledge layer advisory agent
detects that it can't reliably provide grounded primitives". That agent must not also *decide* the gap: a detector
that can be argued with is a detector that can be talked into a gap. The reader produces numbers; the advisory
agent reads them and writes the sentence. Same separation as generator ≠ verifier (R5).

### 2.2 `reading_cartographer` (T1, the only LLM in the lane, and only for language)

**Job:** gap record → **ranked reading manifest**. This is the "market research expert" the owner asked for, and
its name should be narrow so it cannot ramble: *cartographer*, not *researcher*.

**Method — the two peer-reviewed pieces worth stealing, both verified today:**

- **STORM** (Shao et al., `arXiv 2402.14207`, NAACL 2024 — *"Assisting in Writing Wikipedia-like Articles From
  Scratch"*): perspective-guided question asking + simulated expert conversation. Steal the *perspective
  enumeration* step, because a single-perspective query returns a single school of thought and that is exactly how
  a corpus becomes a monoculture.
- **Co-STORM** (Jiang et al., `arXiv 2408.15232`, EMNLP 2024 — *"Into the Unknown Unknowns"*): the discourse
  protocol plus a **dynamic mind map**, which is the only published structure that maps naturally onto a *gap
  taxonomy* rather than a search session.
- **PaperQA2** (Skarlinski et al., `arXiv 2409.13740` — *"Language agents achieve superhuman synthesis of
  scientific knowledge"*): its pipeline is keyword query → chunk/embed → rank → scored summary → LLM re-score →
  answer, with **metadata + citation counts + retraction check**. Its own README states it needs PDFs supplied
  locally. Maxwell's pipeline is the missing supply half; PaperQA2 is the missing read half.

**The manifest is machine-readable or it is unusable:**

```json
{"gap_id":"...","sub_questions":["..."],
 "candidates":[{"canonical_id":"isbn:9780262039246","title":"...","authors":["..."],"year":2020,
                "tier":1,"priority":1,"why":"answers SQ1+SQ2; canonical text",
                "expected_format":["epub","pdf"],"doi_or_isbn_resolved":true,
                "license_class":"publisher_licensed","redundancy_cosine":0.41}],
 "rejected":[{"title":"...","reason":"blog-tier; superseded by <candidate>"}]}
```

**The hallucination gate — and Maxwell has already paid for this lesson.** `config/decisions.yaml` records a
market-research session that produced **2 fabricated arXiv citations (2602.14862 / 2605.18796)** and a model with
no repo access. So: **a candidate that does not resolve against Crossref / OpenAlex / an ISBN registry never enters
the manifest.** Unresolvable = `rejected`, with the resolver's error as the reason. This is not caution, it is a
receipt from this repo.

**Ranking — deterministic where it can be, language where it must be:**

```
score = w1·citation_percentile + w2·venue_class + w3·recency_decay + w4·authority − w5·redundancy
```

`citation_percentile`, `venue_class` and `authority` come from OpenAlex/Crossref fields (no model). `redundancy` is
cosine against the **existing corpus embeddings** (bge-m3, already loaded) — this is the single most important
term, because it is what stops six books the corpus already holds. The LLM writes `why` and the sub-questions; it
never writes a score. (D-2898's rule — no LLM canonical promotion — applied to ranking: a number an LLM can
change is a number nobody can audit.)

### 2.3 `acquirer` (T0, deterministic, the only capability that touches the network)

**Job:** manifest → resolved canonical IDs → adapter ladder → **file in a pen**, with a provenance record.

- **Resolver first.** Store `{doi | isbn13 | openlibrary_id | title+author+year-hash}`, never "get it from LibGen".
  Then adapters are tried in a declared order and the first success wins.
- **Declared adapter order (lawful lane first — it is also the cheapest):**
  `open_access (Unpaywall/OpenAlex/arXiv)` → `gutenberg/StandardEbooks` → `annas` → `libgen` → `zlibrary`.
  Sci-Hub is papers-by-DOI only and is **not** in the default ladder; it is a declared opt-in.
- **Format preference, enforced before download:** `EPUB/AZW3 > TXT/MD > PDF(born-digital) > PDF(scanned) > DJVU`.
  If the manifest says an EPUB exists and the adapter can only give a PDF, that candidate is *retried*, not
  accepted — because a PDF is a research problem and an EPUB is a parsing problem.
- **Idempotency:** `hash(canonical_id + source + attempt)`; a crashed worker never double-downloads.
- **Mirror health:** `open-slum.org` is real and was read today — it tracks shadow-library domains with
  `UP / PROTECTED / DEGRADED / DOWN / UNKNOWN` on a 5-minute window, and the state it reported today was
  **6 domains 2 UP 4 PROTECTED** (Anna's), **2 UP 2 PROTECTED 1 DOWN** (a LibGen-family entry). What is **NOT
  measured here**: whether it exposes JSON. Until the owner confirms, poll the HTML and parse — do not hardcode
  domains.
- **Circuit breaker:** 3 consecutive failures parks an adapter for a cooldown. **A source dying must degrade
  recall, never corrupt the corpus** — which it cannot, because the worst case is a pen file.
- **Never trust a filename** (Maxwell's own rule, D-3045: a name is evidence, never identity). The acquirer writes
  the pen file under the manifest's canonical name and records the served name in provenance.

---

## 3. The one new invariant that makes it safe: licence class

Every acquisition carries `license_class ∈ {public_domain, open_access, publisher_licensed, shadow}` recorded at
download time.

Maxwell does not get to be squeamish here *after the fact*: `config/ingest_identity_gate.yaml` already carries an
**accepted debt of 478 `ingest_site_marker` names** (mirror markers in filenames, owner word T-173), i.e. the
library's provenance is *already* mixed and *already* acknowledged. What is new is that the provenance stops being
a filename suffix and becomes a **field**, so that (a) a future commercial use can filter, (b) a retraction or a
takedown can be answered by enumerating objects, and (c) nobody has to guess.

**Stated plainly, because a spec that hides this is not a spec:** downloading in-copyright works from shadow
libraries is copyright infringement in most jurisdictions, and the exposure sits with the person who does it, not
with the tool. The architecture above is deliberately lawful-first, local-only, non-commercial and
provenance-flagged; the owner decides which lane to enable, in writing, once — exactly like the admission signature.

---

## 4. Tool matrix — measured today (stars / licence / last push, GitHub API 2026-10-17)

| Tool | Reading | Verdict |
|---|---|---|
| `iosifache/annas-mcp` | 1,087★, **no licence file**, pushed 2026-06-26 | best-shaped AA MCP; **vendored, never depended on** (no licence = no rights) |
| `yashimosh/biblio-mcp` | **22★**, MIT, pushed 2026-08-28 | claims AA+LibGen+Sci-Hub+Z-Library in one server; too young to depend on |
| `rookslog/zlibrary-mcp` | 94★, MIT, pushed **2026-10-17** | active; single-site; the RAG-extraction idea is the valuable part |
| `heartleo/zlib` | 986★, MIT, pushed 2026-10-07 | Go CLI, bulk, agent-aware |
| `docling-project/docling` | **69,009★**, MIT, pushed 2026-10-16 | already installed here (`/Library/Frameworks/Python.framework/Versions/3.12`); S0's PDF reader |
| `datalab-to/marker` | 40,517★, Apache-2.0, pushed 2026-10-14 | installed here (`marker_single`); the PDF fallback with the better benchmark |
| `allenai/olmocr` | 19,751★, Apache-2.0, pushed **2026-03-25** | needs a GPU; not for this machine |
| `Future-House/paper-qa` | 9,399★, Apache-2.0, pushed 2026-10-13 | the *reading* side; adopt later, not now |

**The judgement on "MCP vs CLI":** goose's tool surface is MCP, so the *shape* should be MCP — but not by
depending on someone else's server. All three published book MCPs are single-site, young, or unlicensed; mirrors
rename their domains monthly and ToS churn is the norm. The durable form is **one small local MCP server Maxwell
owns (`maxwell_acq`) with three adapters behind one protocol**, because C21 (swappable infrastructure) exists for
exactly this: a protocol plus adapters is a swap; a pinned dependency is a bet.

**Do not build adapters for** Mobilism, Bookracy, OceanOfPDF, pdfroom, WeLib, ebookoz — diminishing returns, and
each one is a maintenance debt with a domain that will move.

---

## 5. Build order (each phase has a receipt; no phase starts without the previous one's)

**Phase 0 — the gap record (no network).** `gap_reader` + `config/acquisition.yaml` (τ, weights, adapter order,
licence vocabulary). Receipt: a gap record for the live starvation census (18/9) that resolves to the disciplines
the pipeline already knows are starved. **This phase is legal, local and useful on its own** — it tells the owner
which disciplines are actually starving and by how much, per task, today.

**Phase 1 — the manifest (no downloads).** `reading_cartographer` with the Crossref/OpenAlex gate and the
redundancy term. Receipt: a manifest for one starved discipline (design psychology, 4 golden / 1 convergent) where
every candidate resolves and every rejection names its reason. Success criterion is not "good books" — it is
**zero unresolvable candidates**.

**Phase 2 — one lawful adapter.** Unpaywall/OpenAlex → a PDF into a pen → the existing door refuses or admits it.
This proves the *whole* chain end-to-end with zero legal exposure, and it will expose every integration assumption
(pen declaration, provenance record, probe behaviour on a real download) before any shadow adapter exists.

**Phase 3 — the shadow adapters behind the protocol.** Anna's first (superset), LibGen second, Z-Library third,
each behind the same interface, each with the circuit breaker and the licence class. **Owner word required to
enable each**, recorded in the gate declaration — not a config default.

**Phase 4 — the loop closes.** PaperQA2-class reading (`paper-qa`, 9.4k★, Apache-2.0) over the corpus for
citation-graph traversal and retraction checks, plus the contradiction detection that makes a gap *actionable*
rather than merely visible.

**What must NOT happen at any phase:** the acquirer writing the corpus; the cartographer emitting prose; the
ranker being an LLM; a hardcoded mirror domain; a dependency on an unlicensed repo; a PDF accepted where an EPUB
was available.

---

## 6. The one-sentence spec

> A deterministic gap reader turns a starved discipline or an unsupported claim into a stamped gap record; a narrow
> cartographer turns that record into a ranked, resolver-verified JSON manifest whose scores are computed and whose
> sentences are written; a resolver maps each canonical ID onto the cheapest lawful source first and a shadow source
> last; the acquirer drops bytes into a declared pen with their provenance and licence class; and the ingest door
> Maxwell already has decides — with the owner's word — whether they become knowledge.

---

## 7. Open questions the owner must answer (in this order)

1. **Shadow lane: enabled or not?** (The spec works entirely without it; Phase 3 is opt-in by declaration.)
2. **Per-task cap:** how many works may one gap manifest request before it needs a new word? (Unbounded acquisition
   is how a corpus becomes a landfill.)
3. **The lawful-first ordering:** accept it, or is `annas` first because coverage matters more than exposure?
4. **Does `open-slum.org` expose JSON?** If not, the mirror-health poll parses HTML and that parser is a declared
   debt from day one.

---

## 6. BUILT — 2026-10-17 (this lane is now code, not only a spec)

**What exists.** `scripts/acquire.py` is the ONE entry point; `pipeline/acquisition/` holds four modules behind one
protocol. `python3 scripts/acquire.py --selftest` is the control (31 checks).

| act | command | what it does | writes |
|---|---|---|---|
| DETECT | `python3 scripts/acquire.py gap` | three declared classes; every unmeasured class NAMED (`NOT_MEASURED`) | nothing |
| ASK | `python3 scripts/acquire.py map --census --limit 1` | worst measured starvation gap → ranked JSON manifest | `governance/evidence/ACQ_MANIFEST_*.json` |
| ASK | `python3 scripts/acquire.py map --gap "colour theory"` | a named topic → same manifest shape | same |
| LOCATE/FETCH | `python3 scripts/acquire.py fetch --manifest <json>` | lawful ladder only (OA → Gutenberg → Standard Ebooks) | **the INBOX pen only** |
| LOCATE/FETCH | `python3 scripts/acquire.py fetch --manifest <json> --allow-shadow "<your word>"` | adds the LibGen rung | **the INBOX pen only** |
| READ | `python3 scripts/acquire.py status` / `mirrors --refresh` | the lane's own state; which domains are VALIDATED today | cache + nothing |

**Where a downloaded book goes — the whole point.** `pens.land: education_inbox` → resolved through
`config/ingest_identity_gate.yaml#source_library.placement.pens` → `~/Library/CloudStorage/Dropbox/education/inbox`.
**Directly into the inbox, no subfolder, never `knowledge pipeline/books`, never an `.md`, never a conversion.**
A file that arrives damaged is moved to `knowledge pipeline/acquisition/quarantine/<stamp>/` and recorded as
`refused_container_unreadable`, so the inbox the owner reads holds only what is worth reading.

**The first real acquisition (proven, not claimed).** Gap `starvation:creative coding` → manifest of 10 ranked works
→ fetch → landed in the inbox:
`Sietske W. Kleibeuker; P. Cédric M. P. Koolschijn; Dietsje Jolles - The neural coding of creative idea generation
across adolescence and early adulthood - 2013.pdf`, 1,149,690 B, sha256 `403e939a…`, licence_class `open_access`,
probe `pdf` PASS, receipt `governance/evidence/ACQUISITION_20261017T191805Z.jsonl`, index row in
`knowledge pipeline/acquisition/index.jsonl`.

**Four rules that replaced versions which were WRONG in practice** (D-3079; each was measured, see BUG-908):
1. the resolver answers in its own RELEVANCE order; the declared score ranks INSIDE that answer;
2. `enabled` (build) and `requires_owner_word` (run) are two gates — collapsing them made `--allow-shadow` inert;
3. a 200 is not liveness (a parked domain answers 200) and a 500 carries its reason — so mirrors are validated by
   MARKER and refusals keep the body;
4. one write path: adapters only LOCATE, the downloader names/probes/lands, and it cannot manufacture a name the
   ingest door refuses (marker, spine, truncation patterns).

**What is NOT built, stated so it cannot be mistaken for done.**
- `primitive_absence` needs a readings file (`primitive_readings.jsonl` — query + cosine). The tau is declared
  `DEFAULT_UNMEASURED`; the class reports `NOT_MEASURED` until a real calibration replaces it.
- `claim_unsupported` reads `stage5_verify_report.jsonl` when it exists; today it reports `NOT_MEASURED`.
- Anna's Archive: declared `unreachable_by_scraping` (DDoS-Guard JS challenge; one mirror is a parked domain).
- Z-Library: declared `not_implemented` (needs a personal login this repository must not hold).
- A local MCP wrapper (`maxwell_acq`) is a THIN layer over this CLI and is not built; `Adapter` is already the
  protocol it would expose, so the work is a transport, not a rewrite (C21).
- PaperQA2-class reading of what was fetched is Phase 4 and untouched.
- **BUG-909 (OPEN):** every LibGen front answered `500 max_user_connections (current value: 300)` at 21:20–21:26 —
  the one working shadow rung is a single point of failure. Remedy is an OWNER WORD: (a) an official Anna's API key,
  (b) a second shadow source behind the same protocol, or (c) accept the named gap.

---

## 8. v1.1 CONSOLIDATION — 2026-10-17T22:50Z (authority: D-3081)

> **What this section is.** Four questions the owner asked in one message, answered from measurements taken today, and
> the corrections that the answered questions force on the sections above. It does not replace §0–§7: the six layers,
> the three capabilities and the D-3078 invariant (an acquirer's receipt is a FILE IN A PEN) all stand unchanged.
> What changes is §6 (`BUILT`), which has drifted, and one missing LAYER (§8.7), which the ledger proved was missing.

### 8.1 Drift named — four claims in §6 that are no longer true

| §6 said | measured now | authority |
|---|---|---|
| "Anna's Archive: declared `unreachable_by_scraping` (DDoS-Guard JS challenge)" | **wrong ENGINE, not unreachable.** Headed Chrome settles the challenge in 14 s → 693,342 B → 116 `/md5/` rows; plain HTTP 403 (902 B), headless 403 (1,896 B) | BUG-911, D-3080 |
| "Z-Library: declared `not_implemented` (needs a personal login this repository must not hold)" | **implemented as `credential_required`** — it refuses BY NAME until `ZLIB_DOMAIN`+`ZLIB_COOKIE` (or `zlib login`) exists, which is the correct behaviour, not an absence | D-3080, §8.3 |
| "`--selftest` is the control (31 checks)" | **42/42 green**, 11 new controls including the decoy matcher and the lawful-before-shadow ordering assertion | `python3 scripts/acquire.py --selftest` |
| §2.3 ladder `open_access → gutenberg/StandardEbooks → annas → libgen → zlibrary`, with Sci-Hub "NOT in the default ladder" | the ladder is **8 rungs**: `open_access (3 routes) → gutenberg → standardebooks → arxiv → annas → libgen → zlibrary → scihub`. Two differences, both deliberate and both declared here so the two documents cannot be read as a contradiction: **arxiv is inserted before annas** (a lawful PAPER rung must precede a shadow BOOK rung, and a paper gap offered a book is a wrong answer, not a slow one); **scihub is in the ORDER but owner-word-gated**, so "not in the default ladder" still holds in effect — the order declares where it would sit, `requires_owner_word` decides whether it is walked | D-3080, `config/acquisition.yaml` |

### 8.2 THE FREE-KEY QUESTION — answered in the vendors' own words

**There is no free official API key. There is a free official BULK route, and it is better than the key.**

- **Anna's Archive.** The official FAQ states: *"We have one stable JSON API for members, for getting a fast download
  URL: `/dyn/api/fast_download.json`"* — members, i.e. donors. Memberships do not auto-renew, and the thing a
  membership buys is a **fast-downloads-per-24 h counter**, not access. For everything else the FAQ points at the
  **free** route: generated ElasticSearch and MariaDB databases, raw JSON, and a **torrent JSON list**. So the honest
  reading is: *a key buys concurrency; it buys no capability.* A torrent of the corpus is unattended, parallel, and
  gets faster with scale instead of hitting a quota — it is the only route here that does.
- **Z-Library.** No API key exists to obtain. The official apps (indexed at `go-to-library.sk`) authenticate a
  **session against the website**; `heartleo/zlib` reads as `internal/cli/{login,cookies,search,download,history,
  profile}.go` — login, cookies, search, download, quota. The quota is **server-side per account AND per IP**:
  community documentation (Awesome-Zlibrary, 2026) says ~**10 books/day** for a free registered account, up to **60**
  with personal access. No client-side trick can raise it; the only levers are more accounts (a ToS violation that is
  IP-bound and therefore mostly ineffective), premium, or **not needing it** (§8.7's ladder).
- **LibGen.** No API. Its free download path is a **two-step**: `ads.php?md5=<hash>` → extract the session key →
  `get.php?md5=<hash>&key=<session>` → a direct URL valid for a few minutes. Bulk = torrents.
- **Sci-Hub.** No API, a captcha wall; the keyless paper route is `sci-net.xyz/{doi}` → iframe PDF (**NOT MEASURED
  here** — a README is not a receipt).

**Consequence for the decision the owner was about to make:** buying the Anna's key is a **convenience purchase**
(no window, run two candidates in parallel), not an unlock. The measured free alternatives are the torrent dump (bulk)
and the slow-partner links (single files). Buy the key only if the 24 s-per-file, one-at-a-time ceiling becomes the
binding constraint in real use — not before.

### 8.3 "Reverse-engineer the app via `go-to-library.sk`" — what exists, and why it does not help

`go-to-library.sk` is the **official apps/extensions index** (FMHY links it as exactly that). Its clients do not talk
to a separate API: they log into the same website and reuse the session cookie. That is the whole surface.

- **There is nothing to decompile that the website does not already give you.** An APK's embedded client id or
  signing secret grants no quota: the quota is enforced server-side against the account and the IP.
- **It would be a net loss.** Decompilation adds malware exposure (unsigned, unverifiable binaries from a shadow
  index) and a legal footing worse than the session reuse, in exchange for **zero** additional capability.
- **The correct lever is the ladder, not the client.** Z-Library is rung 7 of 8. A 10-books/day cap is irrelevant to
  a lane that only reaches it after six other rungs have missed. Making the ladder right is worth more than any
  amount of client work.
- **Owner action, unchanged and already declared:** `brew install heartleo/tap/zlib && zlib login` (MIT, Go, reviewed,
  actively maintained) **or** export `ZLIB_DOMAIN` + `ZLIB_COOKIE` in the shell that runs `acquire.py`.

### 8.4 Headless / MCP across the FMHY list — ranked by SUPPLY-CHAIN risk

The ransomware risk is **in the package, not in the shadow library**: a shadow library serves a `.epub`, while a
random MCP server or installer runs **code with your privileges**.

| tier | what | verdict |
|---|---|---|
| 0 | our own adapters (`pipeline/acquisition/adapters.py`, 8 rungs, one protocol) | **use** — no third-party code executes |
| 1 | **port the method, never call the service**: `francy2222/annas-archive-download-mcp` (LibGen 2-step + Sci-Net + slow partner links, **no key**) | **port** — the chain is three HTTP calls; the hosted Vercel endpoint sees every query and runs with your privileges |
| 2 | **run locally, reviewed, licensed**: `heartleo/zlib` (MIT, Go, 993★, pushed 2026-10-07) | **use** for the Z-Library credential path |
| 3 | **read, do not depend**: `JeremiahM37/librarr` (Go, MIT, 13 indexers, Torznab/OPDS — the best public map of what a book finder must try), `calibrain/shelfmark`, `bookracy.com` | reference only; our ladder already covers the ground behind a protocol (C21) |
| 4 | **never**: hosted MCP endpoints, prebuilt binaries from young/low-star repos, `curl \| sh` installers, **unlicensed** repos (`iosifache/annas-mcp` has no LICENSE — no licence means no rights), anything that asks for your account password instead of a cookie | refused |

**Hard rules for anything from tier 1–3** (these are the ransomware controls, and they are cheap):
1. build from source at a **pinned commit**; nothing is fetched as an opaque binary;
2. Python via `pip install --require-hashes`; Go via `go build` from the pinned tree;
3. **never hand a third-party server a password** — a cookie stays local, and it is revoked by logging out;
4. first run under a read-only sandbox with network egress limited to the source's own domains;
5. **the lane never executes and never auto-opens what it fetches** — bytes go to the QUARANTINE pen and must pass the
   container probe before they are named a work. That single rule is why a malicious file costs a refused probe, not
   a compromise.

### 8.5 Paywalls (Substack / Medium / other blogs) — measured landscape and the posture

Measured 2026-10-17T22:33Z: **Freedium** mirrors exist for Medium; **Hover** (referer/crawler impersonation) is
1,311★ but last pushed **2024-08**; **Bypass Paywalls Clean**'s canonical GitLab answers **403** and gitflic **500**,
with GitHub carrying only a **2022-06** mirror — so BPC is **not a pinnable dependency** and is registered as rejected
for that measured reason.

Posture, in order: **legitimate → grey → red.**
- **Legitimate and usually sufficient:** Substack **RSS gives the full text** of free posts; many writers republish
  the same essay on their own site; institutional access covers most journals; the author's own copy is the cleanest
  possible source of a paywalled essay.
- **Grey:** an archived snapshot (`archive.today`) for a link that has rotted — for *reading*, not for corpus-building.
- **Red:** sharing credentials, or bulk-scraping paid content. It breaks the licence field later (§3), and a corpus
  that cannot state its own licence is exactly what Maxwell refuses elsewhere.

**Architecture ruling:** a bypass the OWNER uses in their own browser is an **owner-side manual route**, never a lane.
If paywalled text is retained at all it is `licence_class: paywalled_personal` and it lives in the **assessment notes**,
never in `knowledge pipeline/books`.

### 8.6 Review intelligence — what experts actually use for pragmatic judgement

The distinction that decides everything: **CRITIC** (a byline, an editorial policy, paid by the *publication*) vs
**CROWD** (a star average anyone can enter) vs **PAID PLACEMENT** (the *publisher* pays).

| class | source | measured today | use it for |
|---|---|---|---|
| critic | **Book Marks** (`bookmarks.reviews`) | 200, 626,458 B | the best single "is this book any good" — aggregates NAMED critics per book and shows the individual verdicts, not one blended star |
| expert nomination | **Five Books** | 200, 764,222 B | the best proxy for expert *curation*: a named expert picks five works and explains why — use it to SEED a gap |
| critic (academic) | **Choice Reviews** | 200; corpus subscription-gated | the best review source for a **monograph/textbook** — the reviewer is a subject librarian with no commercial stake |
| criticism | **NYRB** / **LRB** / **Literary Review** | 200 / 200 / 200, metered | the best place to find an *argument* about a book; most useful where two of them **disagree** |
| crowd, clean-ish | **Open Library** (keyless), **BookWyrm** (federated, self-hostable) | 200 / 200 | metadata + a small, un-gamed signal; BookWyrm is the only review network that is sovereign-compatible by construction |
| crowd, dirty at scale | **Goodreads**, Amazon | 200 | review VOLUME only — expect review bombing and incentivised ratings; never a verdict on its own |
| paid placement | **Kirkus** | 200 | registered **with its conflict**: the publisher pays. Use as an existence/metadata check, never as quality |

**The score this OS should use — three limbs, never a star average alone:**
`independent critic agreement (Book Marks) + expert nomination (Five Books) + citation percentile (OpenAlex)` — a work
that scores on one limb and fails the other two is a *popular* book, not a *reliable* one. All 41 sources and their
measured access codes live in `config/research_sources.yaml`; the check is `python3 scripts/acquire.py sources --check`.

### 8.7 THE DOWNLOAD SPEC v1.1 — the layer that was missing: **CUSTODY**

The lane had `RESOLVE → RANK → ROUTE → FETCH → PROBE → PEN`. It has no memory of what it already delivered, and the
ledger caught it: two shadow rungs — the most expensive in the ladder — were spent on Donald Norman's *The Design of
Everyday Things*, and the `annas` delivery's sha256 (`c8b20f47…`) is **byte-identical to a corpus file with mtime
15:22**, fifty minutes *before* the fetch. The `libgen` delivery (`baab2124…`) exists nowhere at all. Filed as
BUG-914 and carried by hand in `governance/evidence/ACQ_LANDED_LEDGER.md` until the layer exists.

**CUSTODY (new, three points):**
1. **before the ladder**: `already_in_corpus(work)` by sha256 → canonical id → normalized name key; a hit REFUSES with
   the path, because the cheapest possible saving in this lane is not fetching (precision over recall, same posture as
   the title matcher);
2. **on landing**: append a custody row (`custody: {checked, inbox_present, corpus_match}`) beside the delivery row;
3. **on admit**: append `admit_handoff` when the door admits a file whose sha256 matches a landed row — so a delivery's
   later life is *recorded*, never inferred.

**Engine per access class** (the register's vocabulary is the router):

| `access` | engine | example |
|---|---|---|
| `api` | `net.read_text` → JSON | OpenAlex, Unpaywall, Europe PMC, arXiv Atom |
| `scrape` | `net.read_text` → HTML parse | LibGen rows, Book Marks, Goodreads |
| `browser` | **headed Chrome**, persistent profile, challenge loop | Anna's search, `/md5/`, `/slow_download/` |
| `credential` | cookie/session from env or the owner's CLI | Z-Library |
| `captcha` | human hand-off, declared | Sci-Hub; Telegram bot |
| `manual` / `none` | **refuse BY NAME** with the reason (D-3034) | StoryGraph, LibraryThing, Mobilism |

**Throughput, measured, so a plan can be costed:** `open_access` ~1–2 s/work (3 routes tried in order); `arxiv` polite
interval; `annas` **24 s/file** plus one browser session for the whole run; `libgen` 1–2 s/row *when a front is up*
(BUG-909: intermittent 500 `max_user_connections`); `zlibrary` **10/day** (served by a session, not a key); `scihub`
human-in-the-loop. A ten-work shadow manifest therefore costs ≈ 5 minutes of browser and 4 minutes of slow downloads —
not an afternoon.

**Failure taxonomy — every class has ONE declared response:** 403 challenge → browser, else refuse by name; 429 →
breaker + back-off, never a retry storm; 5xx → one retry with jitter, then breaker and a NAMED refusal carrying the
body (BUG-909); wrong bytes (`text/html`, a truncated container) → refuse and name the content type (BUG-912); timeout
→ retry once then breaker; a raised ceiling → **never** (D-3023/D-3038).

**Acceptance tests** (all already controls, `42/42` green): the ladder puts every lawful rung before every shadow rung;
a decoy with FULL token recall is still refused; zlibrary names the missing credential instead of pretending the book
is absent; annas declares the engine it needs instead of claiming the source is dead; a route that cannot be reached
is declared, not dropped; an unknown task is refused by name. **Three to add with CUSTODY:** a work already in the
corpus is refused *before* the ladder; a landed file with no custody row is a named fault; a custody row whose corpus
path has vanished is a named fault.

### 8.8 WHAT IS REJECTED, with the reason (D-3038 — so none of it is re-proposed from memory)

- **Buying the Anna's key today** — the torrent dump is free and faster; buy it only when the 24 s/file ceiling binds.
- **Decompiling Z-Library clients** — same server-side quota, worse legal footing, real malware exposure, zero gain.
- **Hosted MCP endpoints** (any) — an unknown account sees every query and executes with your privileges.
- **Bypass Paywalls Clean as a dependency** — canonical source 403/500, GitHub mirrors frozen at 2022-06.
- **Scraping StoryGraph / LibraryThing** — 403 Cloudflare; an owner CSV export is the honest route.
- **Adapters for Mobilism / Bookracy / OceanOfPDF / pdfroom / WeLib / ebookoz** — §4 stands. They are REGISTERED in
  `config/research_sources.yaml` as *candidates with a `why`* and explicitly **not** as rungs: registration is how a
  candidate stops being re-proposed from memory, not an approval to build (D-3035).
- **A star average as a quality verdict** — three limbs or nothing (§8.6).

### 8.9 The running applier — measured, not estimated (2026-10-17T22:35Z)

PID 54639, started 19:09:51Z, **25 rows of 541** (`failed 5`), at **3.26 min/row** → **516 remaining ≈ 28.0 h**,
ETA **2026-10-19 ≈ 02:30 CEST**, dominated by large PDFs. It is crash-safe and resumable, SIGINT only *between* rows.
Do not edit `pipeline/stage0_convert.py` while it runs (BUG-614 fails every remaining row). The five failures so far
are 2 × `pandoc rc=64` on VALID zips (BUG-900's class) and 3 × `budget_expired` on large PDFs — all quarantined
correctly, none silent.

### 8.10 The next three actions, in consequential order

1. **CUSTODY (BUG-914)** — the cheapest fix in the lane: it stops the most expensive rungs being spent on works the
   corpus already holds. One lookup, three write points, three new selftest controls.
2. **The `ads.php → get.php` probe (BUG-911)** — two minutes, and it decides whether the shadow lane needs a browser at
   all: if the session-key chain resolves headlessly, two candidates can run in parallel and a closed window stops
   being a failure mode. **A route is declared only after it names its bytes.**
3. **BUG-900's spine probe** — refuse a container-readable-but-uncovertible epub at PLAN time instead of after a copy
   and a pandoc failure; **not while the applier is running**.
