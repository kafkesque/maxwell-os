# MASTER PROMPT - domain + depth coding of 150 anchor rows

Attach `BLIND_INPUT_150.csv` + `taxonomy_domain_depth.md`, paste the block below, set `{CHUNK}`. Use the SAME
prompt and the SAME taxonomy for every chunk and every coder.

---
You are a **taxonomy coder**, not an assistant and not a summariser. Label knowledge items on two independent
axes using a CLOSED menu. Both axes are scored against a frozen reference: consistency matters more than
creativity.

**Inputs:** `BLIND_INPUT_150.csv` (cols `row,item_id,name,DEFINITION,APPLICATION,MECHANISM,SOURCE EXCERPT`) and
`taxonomy_domain_depth.md` (the closed menus).

**Task.** For every row in `{CHUNK}` output exactly one row with columns:
`item_id,domains,domains_secondary,depth,conf_domain,conf_depth,evidence_quote,rationale,boundary_condition,coder,date`

- `domains` - 1-3 DOMAIN values separated by `|`, most central first.
- `domains_secondary` - further genuine values, else empty.
- `depth` - exactly one of `universal|cross-domain|domain|specialized`, decided by the scope test: would this
  claim survive substitution into a DIFFERENT field with no domain-specific change? Highest surviving scope
  wins. Never use subject matter as a proxy for scope.
- `conf_domain`, `conf_depth` - honest `0.0`-`1.0`; a low number is useful, a flattering one is not.
- `evidence_quote` - verbatim span from that row's own text.
- `rationale` - 1-2 sentences naming which menu value you rejected and why.
- `boundary_condition` - one clause saying where the claim stops holding (required for `domain` and
  `specialized`; else `n/a`).
- `coder` - your model name exactly (`claude-sonnet`, `kimi-k2`, ...); `date` - ISO date.

**Hard rules.**
1. CLOSED MENU. A value outside the taxonomy is a defect. Nothing fits -> `none_fits` + justification.
2. BLIND. Do not consult or reconstruct any prior label, consensus, or earlier coding of the same item.
3. NO ROW LEFT. One output row per input row, in input order. Unanswerable rows still get a row:
   `depth=none_fits`, `conf_depth=0.0`, reason in `rationale`.
4. FORMAT. One fenced CSV block, exact header, no extra columns, no commentary outside the block.
5. SELF-CHECK. One line outside the block: `rows_expected={N} rows_emitted={M}`. If they differ, stop.

**Calibration (illustrative, NOT part of the 150, must not be reused as labels):**
- feedback loops amplify errors in any predictive system, verifiable in economics, ecology, control engineering -> `cross-domain`
- a specific letterform technique produces a specific typographic illusion -> `specialized`
- memory consolidation works a certain way, asserted with no field restriction -> `universal`
- a clinical trial registry's reporting rules shape publication practice -> `domain`
---

## Runner rules (anti-drift)
1. Identical prompt, taxonomy and row order for both coders; only `coder` and `{CHUNK}` change.
2. Never answer menu questions from your own knowledge - quote the taxonomy file.
3. Save each reply verbatim as `raw_<coder>_<chunk>.md` BEFORE parsing. Never paste-edit a model reply.
4. `python3 scripts/parse_frontier_pack.py governance/frontier_pack_20260924` enforces schema, menu closure, row
   count and evidence quote, and refuses a bad file whole. Never hand-fix a parsed row - re-run that chunk.
5. The owner adjudicates DISPUTES ONLY. Do not pre-filter disagreements: the dispute set is the instrument.
