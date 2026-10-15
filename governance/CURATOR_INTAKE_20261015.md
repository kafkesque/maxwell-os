# CURATOR / INTAKE STAGE — 2026-10-15 (design, references, gates)

> Policy home: **`config/curator_intake.yaml`** (do not restate its values here — C12/D-2646).
> Decision: **D-3001**. Task: **T-133**. Defects: `governance/buglog.md`.
> Market/reference evidence: `governance/MARKET_RESEARCH_20261015.md`.

## 1. What the owner asked for, restated exactly

One interest-based feed (web3, privacy, geopolitics, macro, AI/ML, design, business/indiehacker,
productivity/health, music/DJ/VJ + creative coding) + a **curator stage** that bookmarks what is relevant
(to the owner personally, to music/DJ/VJ/creative-coding, to trends, to business/design, or to Maxwell OS
improvement), **filters the noise** (pragmatically: scams, psyops, clickbait), **distils only the alpha**,
and gives a **daily report** whose rows the owner can approve into the pipeline as *primitive* or reject as
*non-principle*.

## 2. Where it plugs in (and where it must NOT)

```
sources -> S0-intake (transcript/HTML -> MD)  ->  CURATOR (score, classify, distil)  ->  DAILY REPORT
                                                                                        |
                                                                        OWNER GATE (approve / drop)
                                                                                        |
                                                     ingest door (config/ingest_identity_gate.yaml)
                                                                                        |
                                                        S1 chunk -> S1.5 embed/cluster -> S2..S6
```

The curator sits **in front of S0's door and never inside S1-S6**. It therefore cannot corrupt the store,
cannot mint labels, and cannot change an ontology: its only output is a **proposal with provenance**.

## 3. Why this is a decision and not a feature (the two-sided control)

A noise filter has two error directions, and only one of them is visible. Admitted slop is *seen* (the
owner notices on day 3); dropped alpha is *invisible* (nobody ever sees what they never saw). Left
unmanaged, any filter drifts toward showing less, which looks like quality. Therefore: the curator
publishes **its own precision/recall on a frozen golden set**, **counts every drop**, and keeps every
dropped item re-viewable. **A filter whose drops are not counted is an invisible failure — the BUG-787
shape, in the intake.**

## 4. Reference stack — what to adopt, reverse-engineer, or refuse

Adopt/refuse verdicts are in `governance/MARKET_RESEARCH_20261015.md#d`; the load-bearing ones:
**RSSHub** is the single component that lets "one feed" exist without a per-platform scraper; **yt-dlp +
youtube-transcript-api** (transcripts first, Whisper only as fallback) is the video route; **crawl4ai /
markitdown** feed the existing S0 converter; **changedetection.io** covers sources with no feed; the
**prompt-injection screen** (`protectai` class) runs *before* any model treats text as content because an
intake is the one place where untrusted text arrives by design. **Refused as architecture:**
`openclaw-newsroom` (harness-coupled — C25 forbids it for us, though it proves the shape) and any hosted
extraction service (C1/C3).

## 5. Which harness can drive it (the block-II question, answered)

**Any of them, and none of them may be load-bearing.** oMLX/Codex/Claude Code/OpenClaw/Hermes/Pi/DeepSeek
Harness all reach the local engine through an OpenAI- or Anthropic-compatible URL
(`governance/MARKET_RESEARCH_20261015.md#c`), and all could *invoke* the intake. The intake itself must be
a **scriptable pipeline with declared config and a receipt**, because a harness-driven curator cannot be
audited by a rail and cannot be run by cron. Concretely: harness = the driver (an operator's TUI),
`pipeline/` scripts + `config/curator_intake.yaml` = the machine.

## 6. Owner gates and open questions

1. **Owner gate (structural):** the daily report is the gate. No auto-admit, ever.
2. **Open:** the relevance model. Options are (a) embeddings + a centroid per domain using the existing
   bge-m3 (cheap, no new model, no new vector space), or (b) a small classifier trained on the owner's own
   approve/drop history (**preferred after ~2 weeks of labels**). Until a choice is measured, the curator
   ships **rules + embeddings**, and says so.
3. **Open (the honest one):** volume. The screen cannot be measured until a real week of items exists;
   the first receipt must report items/day, admit rate and drop rate **before** any noise class is trusted.
4. **Not this session:** no scraper was run, no source was fetched, no item was admitted. This session
   delivers the policy, the design, the decision and the task — a scheduler and a corpus are the next act.
