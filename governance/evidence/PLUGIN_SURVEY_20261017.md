# PLUGIN SURVEY — 2026-10-17 (subagent 20261016_14, read-only market research)

> **Deliverable:** the per-candidate web sweep the research register names as its REMAINING WORK
> (`governance/NOT-YET-EVALUATED-RESEARCH.md`, closing note: *"a per-candidate web sweep (current
> alternatives, licenses, benchmark provenance, and whether a candidate duplicates an installed
> capability) is the REMAINING WORK, not a claim made here"*).
> **Written to:** `temp/PLUGIN_SURVEY_20261017.md` only. No repo file was edited.
> **Method (receipts first, then market):** read before searching — `governance/NOT-YET-EVALUATED-RESEARCH.md`,
> `governance/MARKET_RESEARCH_20260917.md`, `config/decisions.yaml` (D-3038 body + every `REJECTED`/refusal row
> touching tools/plugins), `config/capability_registry.yaml`, `config/engine.yaml#fanout` + `#jobs`,
> the live harness config `~/.config/goose/config.yaml` (19 extensions enabled) and the live goose extension
> catalog (`extensionmanager.searchAvailableExtensions`).
> **Search budget:** 23 discovery queries/reads (16 GitHub search queries, 1 awesome-list read, 2 goose-docs reads,
> 4 MCP-registry queries) + metadata lookups (12 GitHub repo records, 5 PyPI records). Cap was 25 searches. Not exceeded.
> **Evidence tiers:** [M] measured on this machine | [D] read from this repo/disk | [K] read from a third-party
> source whose URL is cited. Every third-party claim carries its URL. No tool, repo or version below is invented;
> where nothing credible was found the text says so.

---

## 1. Ranked candidates (10 rows)

| # | name | source URL | kind | what it does | install | licence | offline? | cost | Maxwell open item it serves | verdict + reason |
|---|------|-----------|------|--------------|---------|---------|----------|------|------------------------------|------------------|
| 1 | **ruff 0.15.17 + mypy 2.1.0** (both ALREADY INSTALLED) | https://docs.astral.sh/ruff/ · https://www.mypy-lang.org/ | local CLI | fast Python linter/formatter (C17/C19/C20 enforcement: hardcoded values, dead code, signature type hints); mypy = the type half of C17 | `brew install ruff mypy` (both present [M]: `ruff 0.15.17`, `mypy 2.1.0`) | MIT (PyPI: ruff 0.17.1 MIT, mypy 2.4.0 MIT) [K] | yes | $0 | the register's own row 13, *"static enforcement for the fleet — pyright/mypy/ruff gate on C17's 'type hints on all signatures'"*: C17 is a DECLARED rule with **no rail** (the BUG-492 shape, "a rule in a message is not a rule") | **ADOPT** — the only candidate that is already installed, deterministic, offline and adds no second home; it turns a prose rule into a checkable rail. Not a plugin: a rail. Note the installed versions trail PyPI (0.15.17→0.17.1, 2.1.0→2.4.0) so a pin belongs in the existing `min_version` rail |
| 2 | **ripwire** | https://github.com/redhat-et/ripwire | local CLI + MCP server | zero-dependency C++23 code-context CLI; "find what you want without reading the repo, then check you built what you meant" (Apache-2.0, ★2,450, pushed 2026-10-16) [K] | upstream installer is a `curl … \| bash` line (README line 174) — for this repo: build from a PINNED commit with cmake (README names cmake as the only requirement) | Apache-2.0 [K] | yes | $0 | the delegation path: `config/engine.yaml#fanout.excerpt_bytes: 24000` — how a subagent is handed context today is a byte budget, not a relevance choice; `answer_shapes` already had to be invented because a 22 KB excerpt produced a citation-only answer | **TRIAL (pinned, read-only)** — read-only, offline, no data home, and it is the one candidate pointed at a MEASURED weakness (excerpt selection). The `curl \| bash` installer is not admissible under D-382/R14 (a floating artifact is not a dependency): build from a pinned commit instead |
| 3 | **PDF Reader (`mcp-read-pdf`)** — present in the goose catalog, `enabled:false` today | https://pypi.org/project/mcp-read-pdf/ (upstream named by PyPI: https://github.com/michaelneale/mcp-read-pdf) | goose extension (stdio, uvx) | reads large / password-protected PDFs into the session | already declared in `~/.config/goose/config.yaml`; flip `enabled:true` (no repo change) | MIT, v0.1.1 [K] | yes at run time (uvx fetches on first install) | $0 | T-176 / T-180: the intake is worked from a plan in which the OWNER names each work per row; a local PDF read surface inside the harness is the difference between naming a book and guessing it | **TRIAL** — zero blast radius (one config flag, already in the catalog), and the register already records `pdfreader: enabled:false` as a session-surface fact (BUG-873 limb b). CONDITION: pin `mcp-read-pdf==0.1.1` — an unpinned `uvx mcp-read-pdf` is the same floating-dependency fault as row 2's installer |
| 4 | **Document-conversion MCP servers** — `docling-mcp`, `markitdown-mcp`, `mcp-pandoc` | https://github.com/docling-project/docling-mcp · https://github.com/trsdn/markitdown-mcp · https://github.com/vivekVells/mcp-pandoc | MCP servers | EPUB/PDF/DOCX → Markdown/JSON conversion inside a session (MIT, ★773 / ★41 / ★583 respectively, all pushed 2026-08…10) [K] | `uvx --from docling-mcp docling-mcp-server` (upstream README) | MIT [K] | yes (models fetched on install) | $0 | superficially T-176 (conversion) and the S0 stage | **REFUSE** — S0 is already declared and wired: `pandoc 3.9` [M] for EPUB and Docling for PDF (`config/pipeline_config.yaml` S0, cited in D-3049-era text), and stage0's output is already SHA-256-deduped by S1. A conversion MCP would be a SECOND home for a fact the pipeline already declares (D-2646 one-home rule), and it would put an unpinned model download behind a session call |
| 5 | **Ebook / bibliography library MCP servers** — `calibre-mcp`, `ZotSeek`, `mcp-zotero` | https://github.com/caelum29/calibre-mcp · https://github.com/introfini/ZotSeek · https://github.com/kaliaboi/mcp-zotero | MCP servers | read/write + semantic search over a local Calibre or Zotero library (★18 MIT / ★227 licence **none reported** / cloud library) [K] | npm/npx or uvx per each README | mixed — **ZotSeek ships no licence** [K] | partly | $0 | T-176 (metadata sources) | **REFUSE, already decided** — Calibre IS installed here and was MEASURED and refused as a metadata source (`config/decisions.yaml` D-3049: 61 rows, one author *"Ismeretlen"*, titles are this repo's own governance documents; *"it may own a READING surface and never the bytes"*). ZotSeek is refused independently on licence (no licence file ⇒ not C2-clean, same ground as `desert-ant-labs/title` in the register), and `mcp-zotero` works against a Zotero CLOUD library (C3) |
| 6 | **ExifTool + its MCP wrappers** | https://exiftool.org/ · https://github.com/vgribok/exiftool-mcp-server · https://github.com/joshmsimpson/ExifTool_MCP | local CLI (+ 0–3★ MCP wrappers) | reads/writes file metadata incl. PDF Info dicts | `brew install exiftool` (ABSENT here [M]) | ISC / MIT for the wrappers [K]; ExifTool's own term **not verified** in this sweep | yes | $0 | T-176: the 83 PDF-Info rows and 39 EPUB-OPF rows | **REFUSE** — T-176's declared sources already exist and are read (`scripts/census_source_names.py`, `plan_source_rename.py`, D-3045/D-3048); poppler `pdfinfo`/`pdftotext` are already PRESENT [M], so ExifTool would add a FOURTH reader of the same bytes while the blocker remains the owner's per-row word (122 eligible rows). An MCP wrapper at ★0–3 is not a credible dependency either (D-382) |
| 7 | **Duplicate-file finders** — `czkawka`, `fclones` | https://github.com/qarmin/czkawka · https://github.com/pkolaczk/fclones | local CLI | hash/name/size/similar-image duplicate detection (★34,289, licence reported NOASSERTION by GitHub [K]; fclones ★2,972 MIT, last push 2025-03-03 [K]) | `brew install czkawka fclones` (both ABSENT [M]) | czkawka: NOASSERTION reported [K]; fclones: MIT [K] | yes | $0 | T-179 (929 works in two homes, **727 drifted**) and T-180 | **REFUSE** — wrong operator. A duplicate finder answers BYTE-equal overlap (and its sibling, perceptual similarity); T-179's finding is that 727 of the second materialisation **DRIFT**, i.e. the bytes differ and identity — not equality — is the question. The repo's identity gate plus `pipeline/safe_delete.py` (R-D410) already own the deletion side. (No credible MCP server for this either: the only hits were ★0 wrappers, e.g. `rog0x/mcp-file-tools`, `AlexeySamosadov/vaulthash-mcp` [K]) |
| 8 | **Watchexec** | https://github.com/Watchexec/watchexec | local CLI | runs a command when files change (Apache-2.0, ★7,238, pushed 2026-10-13) [K] | `brew install watchexec` (ABSENT [M]) | Apache-2.0 [K] | yes | $0 | T-180 placement / BUG-864 (the Hazel replacement shape) | **REFUSE** — D-3049 already recorded the decision: *"the owner's own Downloads triage is not wrong in KIND — an arrival pen is the right idea — it is wrong in HOME and in SILENCE"*, and the pens are counted in every health run. Adding a watched trigger re-introduces a mover nobody watches; the applier (T-183) must be plan-keyed and dry-run-default, which is a `pipeline/` script, not a watcher |
| 9 | **Local knowledge/memory MCP servers** — `basic-memory`, `memento`, official **Memory** reference server | https://github.com/basicmachines-co/basic-memory · https://github.com/iAchilles/memento · https://github.com/modelcontextprotocol/servers (README: Memory = "Knowledge graph-based persistent memory system") | MCP servers | durable agent memory / knowledge graph over sqlite-vec + FTS5 or markdown (★4,249 **AGPL-3.0** / ★13 **no licence reported** / MCP steering group) [K] | `uvx basic-memory` etc. per README | AGPL-3.0 (basic-memory) [K] | yes | $0 | the knowledge layer: `pipeline/retrieve.py`, `pipeline/query.py`, FTS5 + sqlite-vec in the declared `knowledge pipeline/maxwell.db` (7,640 FBs), and the MEASURED gap that `just ask` is a BARE one-shot with NO retrieval | **REFUSE** — every one of these is a SECOND home for the fact the repo already declares. `maxwell_mcp_server.py::_tool_query_knowledge` is the declared read surface (D-2646 one-home); the corpus store, its dimension contract and its FTS/vec indexes are declared in `config/store_columns.yaml`/`config/capability_registry.yaml`. Adding an AGPL-3.0 memory server on top would also import a licence question for zero capability gain |
| 10 | **Read-only SQL MCP servers** — registry entry `io.github.arifulislamat/database-mcp-sqlite`; the MCP steering group's own SQLite server (**ARCHIVED**) | https://registry.modelcontextprotocol.io/ · https://github.com/modelcontextprotocol/servers-archived (SQLite listed under "Archived") | MCP servers | "read-only by default, row caps, statement timeouts" access to a SQLite DB [K] | npx/uvx per registry entry (licence **not verified** here) | not verified | yes | $0 | `just ask` retrieval / ad-hoc DB inspection | **REFUSE** — (a) the official one is ARCHIVED by the steering group, so it fails the "who maintains it" test; (b) the repo's own MCP server already owns `query_knowledge`, and a second SQL surface over the same DB is precisely the "second home for a fact we already declare" refused by the brief's constraint list |

**Not in the table but read and refused on sight:** `oraios/serena` (★30,329 MCP coding toolkit, licence reported NOASSERTION) — a second repo-navigation/semantic-edit home beside goose's own `developer` + `analyze` extensions; `hibou04-ops/antemortem-cli` (★1, Apache-2.0, "prove every claim with a file:line citation, then machine-check it offline") — the same mechanism this repo already built into `config/engine.yaml#answer_shapes` + the citation reader (D-3022 harness fired 82 citations, 0 refuted); the MCP registry's citation entries (`com.citationsafe/verifier`, `co.pixelcove/citation-tracker`) are cloud services (C1/C3), and `app.openkrill/citations` checks *real-world* bibliographies, not our own bytes. Linux-only system monitors (`hungtrungthinh/mcp-system-monitor`, ★5, NOASSERTION) do not run on this target host.

---

## 2. ALREADY REJECTED — DO NOT RE-PROPOSE

Recorded with the reason that produced it (D-3038: *"WHAT WE REJECT WE REGISTER. A rejected idea that is merely ABSENT can be re-proposed by the next reader as if it were new"*). None of the rows below was re-proposed in §1.

| Rejected | Where the refusal is registered | Reason (as recorded) |
|---|---|---|
| Cloud burst (GPT-4o-mini), any frontier API | register ❌ table | C1/C3 |
| LangChain / LlamaIndex | register ❌ (D2010) | C2 vendor lock-in |
| Microsoft GraphRAG | register ❌ (D2118) | cloud-native |
| LanceDB / DuckDB | register ❌ (D2048) | SQLite adequate (C5) |
| Dagster / Prefect | register ❌ (D2061) | PipelineRunner <300 LOC |
| Full Pydantic migration | register ❌ (D2120) | schema accessors sufficient |
| Neo4j / graph DB (incl. any neo4j MCP) | register ❌ (D2205) | C3 external service |
| Multi-agent swarm / agent frameworks (LangGraph, CrewAI, AutoGen, OpenAI Agents SDK, smolagents) | register ❌ (D2205); sweep row 5 | goose+MCP already are the loop and the tool surface (C25); a framework is a second orchestration home (D-2646) + future tax (C27) |
| CRAG web search · Self-RAG training · ColBERT late interaction | register ❌ (D2205) | C3 / C1+R7 / M1 Max memory |
| Hosted observability (Langfuse, Phoenix) | sweep row 12 | local `METRICS.jsonl` + `measure --gaps` already carry it |
| Rapid-MLX · MTPLX · CIDER | register ❌ (feed.opml evals) | HF network cache (C1/C3) · M5-only TensorOps |
| `gpt-researcher` / `marker-pdf` / `surya-ocr` / `prawcore` | `config/decisions.yaml` (D-2456-era audit) | 0 pipeline references |
| AnyJev (`nokia-applied-research/AnyJev`) | register, EVALUATED 2026-10-16 | REFUSED as labeller/classifier (batch-estimated correction = drifts by construction); ONLY its order-rotation probe was adopted |
| `desert-ant-labs/title` | register | source-available licence; generation where the repo is deterministic (D-2898) |
| `divinetribe/Hermes-4-14B-abliterated-4bit-mlx` | register | abliterated provenance; a lane whose job is refusing must not refuse less |
| Notion / hosted workspaces / any hosted agent platform | register ❌ (sweep row 6) | C1/C2/C3 by construction |
| Calibre as an authority; Hazel as a decider | D-3049 | Calibre holds 61 rows of this repo's own docs; Hazel's rule store is undiffable and its destinations do not exist (BUG-864) |
| DigUp as an OS dependency; any MCP wrapper over it | D-3052 / D-3054 | an unpinned surface cannot be a dependency; re-open needs a hashable CLI/MCP + its index + ONE named consumer |
| Laya-mlx / CLM / Apple FM as verifiers or generators | register watch-list; `config/apple_fm.yaml` | arm never run / no Metal path / gate on measurement; S5 stays DeBERTa (D2298) |

**One thing I would put BACK on the table — and it is not a rejection.** No register refusal looked wrong to me.
Exactly one row deserves to move UP, and it is the register's own **row 13 (pyright/mypy/ruff gate)**: it is filed
as "CANDIDATE (cheap, verifiable)" while C17 is a DECLARED rule with no rail. Recommendation: promote row 13 from
candidate to an ADOPT against the existing ladder, and let the check name its own denominator (files with
signatures) so a green run cannot be a silence.

---

## 3. MISSING CAPABILITY — NO GOOD PLUGIN FOUND

A gap honestly named is worth more than a padded list. For each open item: what was searched, and what does not exist.

- **T-176 source-library names (1,254 defective names; 39 EPUB OPF + 83 PDF Info; 122 ELIGIBLE rows).**
  **No credible plugin found.** The two credible extractors are already here (`pdfinfo`/`pdftotext` [M]; the OPF
  source is declared) and the two popular third-party ones are refused with reasons (Calibre, D-3049; ExifTool,
  §1 row 6). The open item is not an extraction gap: it is a per-row OWNER word over 122 eligible rows.
- **T-179 second materialisation (929 works in two homes, 727 drifted).** **No credible plugin found, and the class
  is wrong.** Duplicate finders (`czkawka`, `fclones`) answer byte-equality; drift is an identity question the repo
  already owns in its identity gate. No MCP server for identity-vs-duplication was found.
- **T-180 placement (2,811 files; 12 waiting; 1,729 files/2,263 MB in `education_unsorted`; Hazel = BUG-864).**
  **No credible plugin found.** Every automation candidate (Hazel-class rule engines, `watchexec`-class triggers)
  is either undiffable or an unwatched mover, and D-3049 already declares the refusal; the census counts the pens.
- **T-181 note admission (2,811 files in declared roots; 621 with no declared corpus home; notes have no home).**
  **No credible plugin found, and a plugin is the wrong shape.** Every "notes/knowledge base" MCP server found
  (`basic-memory`, `memento`, `brain.md`, `seekstone`, `docsagent`) would CREATE a second declared home for facts.
  The missing thing is a declared AXIS + an owner word — D-2898 forbids a model or heuristic deciding a canonical home.
- **T-182 legacy placement tools (`tools/place_quarantine.py`, `tools/restructure_books.py`, DOMAIN→cross_domain
  vocabulary).** **No credible plugin found.** This is a one-home code migration, not a capability gap.
- **T-183 admit applier (one crash-safe, plan-keyed writer, dry-run default).** **No credible plugin found, by
  construction.** No external applier can be plan-keyed to this repo's plan and default to dry-run; C6's
  tempfile→fsync→os.replace is a ~40-line script, and the market has no plugin whose receipt would satisfy D-3034.
- **The knowledge layer / `just ask` (declared store: FTS5 + sqlite-vec in `knowledge pipeline/maxwell.db`, 7,640 FBs).**
  **No credible plugin found — and none is needed: the gap is WIRING, not tooling.** `pipeline/retrieve.py` and
  `pipeline/query.py` exist; `just ask` runs `pipeline/oneshot_ask.py`, a bare one-shot with no DB handle (measured
  2026-10-17 in the register). Every vector/memory MCP server found (rows 9–10) is a second home (D-2646). The
  adoption is a 2-line change to the ask path plus a refusal-when-silent clause.
- **Sub-agent delegation (`pipeline/subagent_fanout.py`, `scripts/delegate_journal.py`).** **No credible plugin
  found.** No MCP server found implements THIS repo's guards (`config/engine.yaml#fanout.guards`: stall_s,
  deadline_s, max_attempts, `verify_with_another_family` R5, `answer_shapes`). `ripwire` (§1 row 2) is the only
  read-only aid worth a trial, and it improves the INPUT to the fanout, not the fanout.
- **Harness observability (19 enabled extensions; `~/.config/goose/config.yaml`).** **No credible plugin found for
  macOS.** The catalog's own suggestions were checked live: `computercontroller`, `autovisualiser`, `tutorial`,
  `PDF Reader`, `GitMCP`, `Puppeteer`. Only `PDF Reader` is a candidate (§1 row 3); `GitMCP` fetches docs from
  gitmcp.io and `Puppeteer` is browser automation over the network — both C3 escalations. System-monitor MCP
  servers found are Linux-only and ★4–5 with an unasserted licence; the register's own R-11 (SiliconScope,
  Apple-Silicon native monitor) remains the only diagnostic candidate and is not a plugin.
- **Provenance / citation integrity.** **No credible plugin found** for provenance over OUR bytes: the registry's
  citation servers are cloud checks of published bibliographies, and the one offline local idea
  (`antemortem-cli`, ★1) duplicates the citation reader this repo already has with teeth (D-3022).

---

## 4. IF I OWNED THE ROADMAP

- **Adopt #1 (ruff+mypy as a rail), today.** Zero install, zero dependency, deterministic: it gives C17 — a declared
  rule with NO rail — its first reader. Smallest blast radius of anything in this survey.
- **Wire the retriever into `just ask` (no plugin).** The corpus is already queryable; a plugin would add a second
  home. This is the highest-leverage change available and it is a diff to one script plus a refuse-when-silent clause.
- **Trial #2 (ripwire, pinned from source) against the MEASURED weakness** in `fanout.excerpt_bytes` — a byte
  budget choosing 24 KB — not against a mood. Keep it read-only; if the eval rail does not move, delete it.
- **Everything else in §1 is a refusal already decided or a second home.** Do not install a conversion MCP (S0 is
  wired), a metadata source (D-3049), an ebook/bibliography library (no licence on the local-first one), a duplicate
  finder (wrong operator), a file watcher (D-3049) or a memory/SQL MCP (D-2646). Register the refusals so the next
  sweep starts here instead of at zero.
