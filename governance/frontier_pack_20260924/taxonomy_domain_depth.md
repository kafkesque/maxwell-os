# Closed taxonomy - domain + depth (frontier pack 2026-09-24)

Generated from `config/closed_menu_v5.json` and `config/depth_classes.yaml`. **Those configs are authoritative;
this sheet is a rendering. If they disagree, the config wins.**

## A. DOMAIN (44 values) - multi-label, 1-3 typical

1. `ai & agents`
2. `arts & culture`
3. `brand identity`
4. `business development`
5. `business operations`
6. `code & computation`
7. `computational art`
8. `computational science & physics`
9. `creative technology`
10. `data visualization`
11. `design strategy`
12. `design systems`
13. `digital product`
14. `editorial & advertising`
15. `education`
16. `engineering & infrastructure`
17. `engineering practice`
18. `entrepreneurship`
19. `environmental design`
20. `finance & investment`
21. `graphic design`
22. `health & wellness`
23. `illustration`
24. `industrial design`
25. `information architecture`
26. `leadership`
27. `legal & public policy`
28. `marketing & communications`
29. `media & entertainment`
30. `motion design`
31. `organizational behavior`
32. `packaging`
33. `personal productivity`
34. `product design`
35. `project management`
36. `research & methodology`
37. `science & research`
38. `semiotics & communication`
39. `social sciences`
40. `systems & frameworks`
41. `urban planning`
42. `user experience`
43. `web & ui`
44. `emerging`

**CLOSED MENU.** Use only the values above. Never invent, rename or merge. If nothing fits, output the single
token `none_fits` and justify it in `rationale`. A 4th label needs an explicit justification.

## B. DEPTH (4 values) - single label, epistemic SCOPE not subject matter

1. `universal` - holds in every field tried; the domain context is irrelevant to its truth
2. `cross-domain` - holds in >= 2 fields but not all; at least one field resists it
3. `domain` - holds inside one field; carrying it elsewhere needs re-derivation
4. `specialized` - holds only inside a narrow sub-specialty, an instrument, a technique or a named corpus

**Scope test:** ask whether the claim survives substitution into a DIFFERENT field with no domain-specific change

Soft band (informative, never mechanical): universal >= 3 domains; cross-domain >= 2; domain 1..N adjacent; specialized 1

Guards:
- D282: scope is the depth axis and NEVER the content_type discriminator - a 1-domain or specialized PRINCIPLE is still a principle
- D2130: the band informs, it does not decide; a coder may deviate with a note
- the menu is CLOSED: a value outside 1-4 is a defect, never a new class

## C. NEVER USE
gpt-oss labels, the 3-voter depth consensus, gold_4axis.jsonl depth values, any pre-registered prediction key. Code from the row's own text only; do not reconstruct a prior label.

## D. EVIDENCE
Every row needs `evidence_quote` copied **verbatim** from that row's `DEFINITION`/`APPLICATION`/`MECHANISM`.
No quote, no row.
