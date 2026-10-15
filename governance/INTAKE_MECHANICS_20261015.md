# CURATOR INTAKE — mechanics, evidence, and what already exists

**Measured 2026-10-15. Answers block III. Companion to `config/curator_intake.yaml` (policy) and `governance/CURATOR_INTAKE_20261015.md` (design).**
Every factual claim below carries the URL it was read from, or is marked **UNVERIFIED**.

## 1. Do you add sources one by one, or connect accounts?

**Answer: for everything feed-shaped you import a LIST, not items. You add one by one only where no feed exists.**

| source class | connect once, or one-by-one? | evidence |
|---|---|---|
| news / blogs / Substack / Medium | **One import.** OPML is the account-connect equivalent — a single file carries thousands of subscriptions. Substack and Medium both publish native `/feed`. | OPML import/export is a first-class API operation in the two readers below |
| an existing RSS reader's subscriptions | **One API call.** `reader/api/0/subscription/list` (Inoreader; FreshRSS exposes the same Google-Reader path) | inoreader.com/developers/subscription-list; freshrss.github.io/FreshRSS/en/developers/06_GoogleReader_API.html |
| the self-hosted reader itself | **Full API + OPML in/out**: `/v1/feeds`, `/v1/entries`, `/v1/categories`, `/v1/export`, `/v1/import` | miniflux.app/docs/api.html |
| YouTube channel subscriptions | **Connect once via OAuth** (`subscriptions.list` returns every subscription), or export once (Takeout `subscriptions.csv`), or add channel RSS after one enumeration. Requires an OAuth client. | developers.google.com/youtube/v3 — exact quota-unit cost **UNVERIFIED** (the cost page is JS-rendered and returned no readable table) |
| X.com following | **Best effort, and it may not be possible locally.** Account-level following sits behind the paid API; the community path is an RSS bridge. The RSSHub social-media doc page is JS-rendered, so the route's auth requirement is **UNVERIFIED**. | docs.rsshub.app (unreachable content) |
| Telegram channels | **A bot cannot read your subscriptions** — the Bot API delivers `channel_post` only for chats the bot is a member of. A **user-account** session (MTProto/TDLib/Telethon) or a one-time offline export can. | core.telegram.org/bots/api |
| podcasts | RSS enclosures, and the **Podcast 2.0 namespace carries transcripts** (`podcast:transcript`) — transcripts first, ASR only as fallback. | github.com/Podcastindex-org/podcast-namespace → `/docs/tags/transcript.md` |
| an article with no feed | `changedetection.io` watches the page | github.com/dgtlmoon/changedetection.io |

**Consequence for the build:** the source list is a *file you own* (OPML), not data locked in five accounts. That is the C2/C4 test, and it is why OPML is the seed format rather than an app's database.

## 2. Is there one place that aggregates everything, broken into interest sections?

Yes — but it is two things, and conflating them is the trap:

- **The store** (one place, sections = categories/tags): Miniflux `/v1/categories` or FreshRSS `tag/list`. Both are self-hostable, both have APIs, both round-trip OPML. This is where items *live*.
- **The reading surface** (one place to read): the **daily report is a file** (JSON + Markdown) rendered by the curator. A file is readable in a terminal, an editor, a phone, a git diff — and it survives an app being abandoned. *Do not make an app the place where the feed lives.*

Honest caveat on "one terminal": the aggregation is a **store + a rendered report**, not a single TUI someone else maintains. The report is the terminal-agnostic artefact.

## 3. How would curation decide what to include, and what makes it *personal*?

The pipeline is eight stages; each is a script with declared config and a receipt (C25 — no harness load-bearing):

```
S0 fetch/normalise → S1 dedupe → S2 screens → S3 evidence extraction →
S4 noise classification → S5 relevance → S6 diversity → S7 budget → S8 report
```

**S5 is the only genuinely personal stage, and it has exactly two honest mechanisms:**

| mechanism | cold start? | explainable? | needs history? | recommendation |
|---|---|---|---|---|
| **bge-m3 centroid** of the items the owner has *accepted*, seeded from the interest list | works immediately | yes — "you accepted 9 items near this" | no | **start here** |
| classifier trained on the owner's approve/drop ledger | no | partial | yes (hundreds of labels) | later, when the ledger is big enough |

**The label is the owner's action, never the curator's own score.** The curator is not the checker (R5): relevance is scored by one family, and any *claim* is checked by a different family. The approve/drop ledger is the training set for the second mechanism and is the asset worth protecting.

## 4. How does it detect alpha and filter noise *mechanically*?

Not one "alpha score" — **four independent checks, each of which must name the evidence that produced it**, with a class that cannot name its evidence failing to `UNKNOWN` rather than silently passing:

| noise class | required evidence | mechanism |
|---|---|---|
| `clickbait` | the promised payload is absent from the body | title-vs-body entailment below the declared floor |
| `psyops` | claimed provenance contradicts the cited source | claim-vs-source entailment below floor |
| `scam` | urgency/guarantee/payment pattern **and** an unsupportable claim | pattern rule + claim check |
| `duplicate` | same id, or same served_run_name_and_author, or one corpus row | reuses the D-2999 ladder |
| `off_interest` / `low_alpha` | distance from the accepted-item distribution | S5 reading |
| `unreadable` | extraction failed | S0 receipt |

**Alpha** is what survives: (a) the item has a *checkable* claim or a *reusable* artefact (code, config, benchmark, method), (b) it is not a duplicate of something already in the store, (c) it is distinct from the day's other keeps (MMR — Carbonell & Goldstein, SIGIR 1998), (d) it fits one declared domain. `estimated_units` in the report is the price of admission to the pipeline — the owner approves a cost, not just an opinion.

**Two-sided by construction:** every drop is counted, every dropped item stays re-viewable, and a filter change without a re-measured precision/recall pair on a frozen golden set is refused. **A false negative is the expensive error** — an alpha item dropped is worse than a slop item shown.

## 5. What already exists that can be adopted, referenced, or reverse-engineered

**The verified negative result first, because it changes the plan.** GitHub search for AI-news-curator / digest shapes returned `total_count` **1**, **17**, **0** across three queries. **This space is not mature.** There is no product to adopt; there are components to compose.

**Adopt (components):**
- `yt-dlp/yt-dlp` — 197,946★, Unlicense, pushed 2026-10-10 — video/audio acquisition.
- `RSSHub` (DIYgod) — turns X/Telegram/Substack-shaped sources into feeds; its own docs index lists **Folo** as a client.
- `miniflux` (API + OPML, verified above) or FreshRSS (Google-Reader API, verified above) — the store.
- `karakeep-app/karakeep` — 29,666★, **AGPL-3.0**, pushed 2026-10-13, *"self-hostable bookmark-everything app with AI-based automatic tagging"* — this is the **bookmarker half** of the curator, already built.
- `changedetection.io` — feedless pages.

**Reference / reverse-engineer (the only two close shapes found):**
- `joshrichards37/sift` — MIT, 4★ — *"Self-hosted personal news agent — local LLM filters your feeds into a daily …"*: the **exact shape** of this design at toy scale.
- `huawolf/news-agent` — MIT, 18★, pushed 2026-09-07 — LLM scoring + console.
- `RSSNext/Folo` — 39,104★, AGPL-3.0, pushed 2026-10-13, *"Folo is the AI RSS Reader"* — **reference for UX only**; it is account-centric, so it cannot be the store under C2/C3.

**Established methodology, cited (verified to exist this session by fetching arXiv):**
- **FEVER** — `arXiv:1809.00626` — the claim/evidence/label task definition, reused verbatim as the internal contract for S3.
- **Indirect prompt injection** — the query `ti:"indirect prompt injection"` returns live work (e.g. `arXiv:2403.14720`), i.e. the "never trust the text you read" threat model is an active published field, not a private intuition. OWASP's *Top 10 for LLM Applications* is the practical checklist — edition **UNVERIFIED** here.
- **LLM-as-reranker** — `arXiv:2412.20061`, `arXiv:2406.12433` exist; this is the published form of S5's reranking stage.
- **Clickbait detection** — `arXiv:1906.00638` exists; this is the published form of the `clickbait` evidence rule.
- **Maximal Marginal Relevance** — Carbonell & Goldstein, SIGIR 1998 — S6 diversity. **Not verified by fetch this session** (pre-arXiv venue).
- **Cohen's kappa** (agreement) and **TREC pooling** (pooling bias in evaluation) — standard names for S8's honesty requirements; **not verified by fetch this session**.
- **Filter-bubble harm evidence** — **UNVERIFIED**: I did not verify a citation this session, so no claim is made either way.

## 6. Which harness can drive this? (the question that kept returning)

**Any of them, and none of them may be load-bearing.** oMLX's own admin dashboard has one-click setup for *OpenClaw, OpenCode, Codex, Hermes Agent, Copilot, Pi, Mistral Vibe and DeepSeek Harness* — they are clients of one local OpenAI/Anthropic-compatible server, so they are interchangeable drivers. The intake's deliverable is therefore **scripts + `config/curator_intake.yaml` + a receipt per run**, and its only output is a **proposal** that stops at the owner.

## Open questions this document does NOT settle

1. **Relevance mechanism** — centroid vs trained classifier: decide by measurement once ~100 approve/drop labels exist.
2. **Golden set** — `governance/curator_golden_20261015.json` is referenced but **not yet created**; until it exists the recall floor is declared and the ladder is blind.
3. **X.com viability** — unverified; assume it may be unavailable and design it as optional.
4. **Volume honesty** — the number of items/day from these sources is unmeasured; the 12-item report cap is a declared budget, not a measured one.
