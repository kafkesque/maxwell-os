# THE ACQUISITION LANDED LEDGER — every file this lane has ever delivered, with the rung that served it

Authority: D-3080, D-3081. Written 2026-10-17T22:31Z. The machine-readable twin is
`knowledge pipeline/acquisition/index.jsonl`; this file is the human face of it, and the ONE question it answers is
the one an index of one-line JSON cannot: **which rung delivered which file, and is that file still there?**

The rule it enforces is BUG-844's: *an act that leaves no trace did not happen.* A `landed` line with a sha256 is a
CLAIM. Below, every claim is checked against the disk.

## The four deliveries

| # | ts (UTC) | rung (`adapter` / `via`) | work | sha256 (first 12) | inbox now? | verdict |
|---|---|---|---|---|---|---|
| 1 | 19:18:31 | `open_access` / `oa_pdf` | Kleibeuker, Koolschijn, Jolles — *The neural coding of creative idea generation across adolescence and early adulthood* (2013) | `403e939a26b2` | **present**, 1,149,690 B | clean |
| 2 | 19:55:04 | `open_access` / `unpaywall` | Coulton & Lindley — *More-Than-Human Centred Design: Considering Other Things* (2019) | `1c66f2ec1a9d` | **present**, 1,948,000 B | clean |
| 3 | 20:02:13 | `annas` / `slow_download` → node URL | Norman — *The Design of Everyday Things* (2016) | `c8b20f475020` | **absent** | **duplicate delivery** — see below |
| 4 | 20:04:39 | `libgen` / `index.php?req=` | Norman — *The Design of Everyday Things, Revised and Expanded Edition* (2013) | `baab21243460` | **absent** | **lost delivery** — see below |

## Delivery 3 — the annas rung worked, and it delivered bytes the corpus already had

The file is gone from `education/inbox/`, and that is **not** a loss. The sha256 the index recorded
(`c8b20f47502088aa1ec8c4ec5f396c099434e424d7b5fc7a6251c6565517c7b3`) is present, byte-identical, at:

```
knowledge pipeline/books/DOMAIN 2 Design/practice+process/The Design of Everyday Things Revised and Expanded Edition.epub
```

whose mtime is **15:22 — fifty minutes BEFORE the fetch**. So the corpus already held this work, the annas rung
downloaded a byte-identical copy into the inbox, and the copy was then removed. **The rung worked.** What failed was
the lane's judgement: nothing at fetch time asked "does the corpus already hold these bytes?".

## Delivery 4 — the libgen rung worked, and its bytes are gone with no record

Not in the inbox, not in the corpus, not in `~/.Trash`, and no file anywhere carries sha256 `baab2124…`. The index
says `landed`; the disk says nothing. That is the BUG-844 shape exactly: a claim of delivery that no longer resolves.

Two readings are consistent with the evidence and this ledger does not pretend to choose between them: the file was
**deleted by hand** (plausible — it was an unworded fetch and the owner stopped the run), or it was **moved under a
different name**. Neither is recorded anywhere, which is the actual defect: the lane records DELIVERY and never
CUSTODY. Filed as BUG-914.

## What this means for the ladder (the measured lesson, not a preference)

Both shadow rungs WORK. `annas` needed a headed browser and 24 s on the slow partner; `libgen` needed a mirror that
was not saturated (BUG-909) and a parser that could see a title (BUG-910). Neither is broken.

The defect the ledger exposes is **upstream of both**: the gap-finder proposes a work from a starvation gap and never
consults corpus custody, so the most expensive rungs in the ladder (shadow, browser, owner-word) were spent on a work
already sitting in `knowledge pipeline/books/`. The fix is not a new source; it is one check before `locate()` —
`already_in_corpus(work)` — which is also the cheapest possible saving in the whole lane.

## Reproduce this ledger

```bash
shasum -a 256 "knowledge pipeline/books/DOMAIN 2 Design/practice+process/The Design of Everyday Things Revised and Expanded Edition.epub"
# c8b20f47502088aa1ec8c4ec5f396c099434e424d7b5fc7a6251c6565517c7b3   <- matches delivery 3
find "$HOME/Library/CloudStorage/Dropbox" -type f -exec shasum -a 256 {} + 2>/dev/null | grep baab2124
# (no output)                                                          <- delivery 4 has no bytes
```
