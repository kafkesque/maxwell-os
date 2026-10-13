# RELABEL PLAN — 2026-10-13

Rendered by `scripts/apply_relabel_rulings.py` (D-2977) from `config/relabel_rulings.yaml` + `canonical_relabel_review_20261013.csv`. **DO NOT hand-edit: re-run the applier.**

- units: 197 — **LEAVE** 1 (94 rows), **ESCALATE** 196 (809 rows)
- CONFIRM declarations to add: **0** alias(es) in config/taxonomy.yaml, making 0 row(s) reproducible
- the CONFIRM half is a raw-alias declaration: MEASURED to move neither `menu_hash` nor the answer space, so it rewrites no provenance (I2/D-2896) and relabels nothing
- CORRECT/ABSTAIN are RECORDED HERE AS OWED: a canonical relabel is a separate owner-gated store write with its own backup and decision (D-2898) — this applier never performs it

## CONFIRM — the raw labels to declare (one line each in config/taxonomy.yaml)

| canonical (the ONE home) | raw labels to declare | rows made reproducible |
|---|---|---|

## LEAVE — 1 unit(s), 94 row(s)

| unit_key (the identity to rule on) | rows | live says | cause | why |
|---|---|---|---|---|
| `marketing science -> emerging` | 94 | `marketing` | LATE-HOME | OWNER-RULED unit (config/relabel_rulings.yaml#unit_rulings) |

## ESCALATE — 196 unit(s), 809 row(s)

These units NO ruling reaches. They are the owner's remaining decision, ordered by leverage — nothing here is inferred from a neighbour.

| unit_key (the identity to rule on) | rows | live says | cause | why |
|---|---|---|---|---|
| `computer science -> software engineering` | 60 | `emerging` | PROVENANCE-UNRESOLVED | OWNER-RULED CONFIRM but HELD: awaiting re-affirmation: CONFIRM has a forward propagation effect (see note) |
| `innovation management -> creative process` | 29 | `entrepreneurship studies` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `public policy -> political economy` | 28 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `information visualization -> information science` | 23 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `narrative theory -> literary theory` | 23 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `religious studies -> anthropology` | 23 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `historical linguistics -> linguistics` | 22 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `design science -> design thinking` | 20 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `industrial engineering -> engineering` | 17 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `career counseling -> psychology` | 14 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `human factors engineering -> human-computer interaction` | 13 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `information systems -> information science` | 13 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `innovation studies -> creative process` | 13 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `literary studies -> literary theory` | 11 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `creative studies -> creative process` | 9 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `music theory -> performing arts` | 9 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `public administration -> political economy` | 9 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `architectural design -> design thinking` | 8 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `creative cognition -> cognitive science` | 8 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `health economics -> economics` | 8 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `industrial economics -> economics` | 8 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `sports science -> health & medicine` | 8 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `accounting -> finance` | 7 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `animation studies -> computer graphics` | 7 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `cognitive anthropology -> anthropology` | 7 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `color science -> color theory` | 7 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `energy economics -> economics` | 7 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `health informatics -> information science` | 7 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `learning science -> cognitive science` | 7 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `psychometrics -> research methodology` | 7 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `architectural theory -> cultural design` | 6 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `distributed systems -> software engineering` | 6 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `financial management -> finance` | 6 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `mythology -> cultural studies` | 6 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `nutrition science -> health & medicine` | 6 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `political philosophy -> philosophy` | 6 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `service design -> design thinking` | 6 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `social entrepreneurship -> political economy` | 6 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `urban studies -> interdisciplinary studies` | 6 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `behavioral finance -> behavioral economics` | 5 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `critical theory -> cultural studies` | 5 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `data engineering -> software engineering` | 5 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `exercise physiology -> health & medicine` | 5 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `health services research -> health & medicine` | 5 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `historical sociology -> sociology` | 5 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `learning sciences -> cognitive science` | 5 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `sports psychology -> psychology` | 5 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `theology -> philosophy` | 5 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `visual analytics -> information science` | 5 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `classical mechanics -> theoretical physics` | 4 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `communication science -> communication theory` | 4 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `contract law -> law` | 4 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `entrepreneurial economics -> economics` | 4 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `entrepreneurial studies -> emerging` | 4 | `entrepreneurship studies` | LATE-HOME | class LATE-HOME is PENDING — the owner has not ruled it yet |
| `environmental engineering -> engineering` | 4 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `financial regulation -> law` | 4 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `higher education administration -> organizational theory` | 4 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `industrial organization economics -> economics` | 4 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `marketing strategy -> emerging` | 4 | `marketing` | LATE-HOME | class LATE-HOME is PENDING — the owner has not ruled it yet |
| `media economics -> economics` | 4 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `military strategy -> strategic thinking` | 4 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `reliability engineering -> systems engineering` | 4 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `translation studies -> linguistics` | 4 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `visual cognition -> cognitive science` | 4 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `automotive engineering -> engineering` | 3 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `business law -> law` | 3 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `cloud computing -> software engineering` | 3 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `cultural psychology -> psychology` | 3 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `educational measurement -> research methodology` | 3 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `financial accounting -> finance` | 3 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `financial engineering -> finance` | 3 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `healthcare management -> health & medicine` | 3 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `moral psychology -> psychology` | 3 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `nonprofit management -> political economy` | 3 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `numerical analysis -> computational physics & simulation` | 3 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `optimization theory -> operations research` | 3 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `platform economics -> economics` | 3 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `real estate economics -> economics` | 3 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `rhetorical studies -> communication theory` | 3 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `statistical theory -> operations research` | 3 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `type design -> typography` | 3 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `web development -> software engineering` | 3 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `web engineering -> software engineering` | 3 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `agricultural economics -> economics` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `ai ethics -> artificial intelligence` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `architectural sociology -> sociology` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `artificial intelligence safety -> artificial intelligence` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `atmospheric physics -> computational physics & simulation` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `business finance -> finance` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `corporate law -> law` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `cultural economics -> economics` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `database systems -> software engineering` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `existential psychology -> psychology` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `experimental design -> research methodology` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `family systems theory -> systems thinking` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `film theory -> media studies` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `health communication -> communication theory` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `historical methodology -> research methodology` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `industrial relations -> sociology` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `knowledge representation and reasoning -> artificial intelligence` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `legal psychology -> psychology` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `marketing economics -> economics` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `media arts -> media studies` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `medical ethics -> philosophy` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `medical informatics -> health & medicine` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `music psychology -> cognitive science` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `optical engineering -> engineering` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `personal finance -> finance` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `philosophy of logic -> philosophy` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `phonology -> linguistics` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `psycholinguistics -> linguistics` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `publishing studies -> media studies` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `second language acquisition -> linguistics` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `service management -> operations research` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `social movement studies -> sociology` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `social science methodology -> sociology` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `social science research methods -> research methodology` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `sociology of technology -> sociology` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `statistical physics -> theoretical physics` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `strategic studies -> strategic thinking` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `technology ethics -> philosophy` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `technology studies -> cultural studies` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `time series analysis -> operations research` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `transportation economics -> economics` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `urban design -> design thinking` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `visual culture studies -> visual perception` | 2 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `affective computing -> human-computer interaction` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `animal cognition -> cognitive science` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `art economics -> economics` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `autonomous systems engineering -> robotics` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `biological semiotics -> semiotics` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `biostatistics -> research methodology` | 1 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `chronobiology -> neuroscience` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `clinical epidemiology -> health & medicine` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `clinical neuroscience -> neuroscience` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `communication design -> communication theory` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `community development -> political economy` | 1 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `community-based participatory research -> research methodology` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `comparative cognition -> cognitive science` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `consumer economics -> economics` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `cross-cultural communication -> communication theory` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `cultural geography -> cultural studies` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `customer experience management -> design psychology` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `data mining -> machine learning` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `design cognition -> cognitive science` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `digital publishing -> media studies` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `distributed systems engineering -> software engineering` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `embodied cognition -> cognitive science` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `engineering design -> engineering` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `experimental psychology -> psychology` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `financial mathematics -> finance` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `healthcare design -> health & medicine` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `history of philosophy -> philosophy` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `history of science and technology -> research methodology` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `implementation science -> research methodology` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `industrial and organizational psychology -> psychology` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `interactive media design -> media studies` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `journalism studies -> media studies` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `law and technology -> law` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `market research -> emerging` | 1 | `marketing` | LATE-HOME | class LATE-HOME is PENDING — the owner has not ruled it yet |
| `medical humanities -> health & medicine` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `military ethics -> philosophy` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `military studies -> strategic thinking` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `molecular biology -> health & medicine` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `optics -> theoretical physics` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `organizational communication -> communication theory` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `organizational economics -> economics` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `performance engineering -> systems engineering` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `political sociology -> sociology` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `problem solving -> cognitive science` | 1 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `problem solving theory -> decision making` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `programming languages -> software engineering` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `psychophysiology -> neuroscience` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `rhetorical theory -> communication theory` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `science and technology policy -> cultural studies` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `science and technology studies -> cultural studies` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `science communication -> communication theory` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `social media studies -> sociology` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `software architecture -> software engineering` | 1 | `emerging` | PROVENANCE-UNRESOLVED | class PROVENANCE-UNRESOLVED ruled ESCALATE |
| `statistical learning -> machine learning` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `systems biology -> evolutionary biology` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `technical communication -> communication theory` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `transpersonal psychology -> psychology` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `user experience research -> design thinking` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `visual communication theory -> semiotics` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `visual effects technology -> computer graphics` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `web accessibility -> human-computer interaction` | 1 | `emerging` | ALIAS-LAYER-RETIRED | class ALIAS-LAYER-RETIRED is PENDING — the owner has not ruled it yet |
| `row:3bd897791f45a5796840971068a33144c4d4721498759b461836af071ef99892` | 1 | `marketing` | DEFINITION-RE-SCOPE | class DEFINITION-RE-SCOPE ruled ESCALATE |
| `row:9d6aa605c70cac702f12a47f738dacf2e63225ad9700f9a3486fbb40658ce646` | 1 | `design thinking` | DEFINITION-RE-SCOPE | class DEFINITION-RE-SCOPE ruled ESCALATE |
| `row:0f808ed97f0df455f77adcb3d78bcc020e911106d2874f4ac947248576ec2225` | 1 | `creative process` | DEFINITION-RE-SCOPE | class DEFINITION-RE-SCOPE ruled ESCALATE |
| `row:1dcb9f1d7b15f12041428e909a309ecaa65f8ba50295aec42067445b5d786be6` | 1 | `emerging` | DEFINITION-RE-SCOPE | class DEFINITION-RE-SCOPE ruled ESCALATE |
| `row:1f9d2696b37072d165fe786d8e83dfbc6bd4cdf30023c19846fbad4e0adf7503` | 1 | `business administration` | DEFINITION-RE-SCOPE | class DEFINITION-RE-SCOPE ruled ESCALATE |
| `row:2dbf74fca79b7302df0537696958c9c6b155c3d9352bdb4d993a7ae337aca7a6` | 1 | `business administration` | DEFINITION-RE-SCOPE | class DEFINITION-RE-SCOPE ruled ESCALATE |
| `row:3d25109da166538e711ab327f1619265871c082b3f4d152b01825114ee4d13b2` | 1 | `business administration` | DEFINITION-RE-SCOPE | class DEFINITION-RE-SCOPE ruled ESCALATE |
| `row:4ff20c35c6edd8a137d3c05d843d07a936295e3545ac93842e8b096b557c3476` | 1 | `business administration` | DEFINITION-RE-SCOPE | class DEFINITION-RE-SCOPE ruled ESCALATE |
| `row:7196e92b224bc5710254570558807e2939df002c78af825ecbee6d0522256097` | 1 | `business administration` | DEFINITION-RE-SCOPE | class DEFINITION-RE-SCOPE ruled ESCALATE |
