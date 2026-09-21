# MENU REPAIR QUEUE - discipline boundary pairs (PART2 B, owner-approved)

Review method: I send ONE pair below with a drafted inclusion/exclusion test; you answer
SAME or DIFFERENT with one line of rationale. Nothing is applied to the pipeline until all
pairs are settled, then kappa is re-measured on the 116 labelled ruler rows.

1. cognitive science vs psychology (3 rows) - OWNER: DIFFERENT (mechanism vs behaviour) - DRAFT ACCEPTED 2026-09-21
2. political economy vs economics (2 rows) - OWNER: DIFFERENT (power/institutions vs markets) - DRAFT ACCEPTED
3. finance vs strategic thinking (2 rows) - status: SETTLED (DIFFERENT, blanket approval)
4. design thinking vs human-computer interaction (2 rows) - status: SETTLED (DIFFERENT, blanket approval)
5. research methodology vs risk management (1 rows) - status: SETTLED (DIFFERENT, blanket approval)
6. operations research vs strategic thinking (1 rows) - status: SETTLED (DIFFERENT, blanket approval)
7. operations research vs behavioral economics (1 rows) - status: SETTLED (DIFFERENT, blanket approval)
8. visual semiotics vs communication theory (1 rows) - status: SETTLED (DIFFERENT, blanket approval)
9. artificial intelligence vs economics (1 rows) - status: SETTLED (DIFFERENT, blanket approval)
10. research methodology vs behavioral economics (1 rows) - status: SETTLED (DIFFERENT, blanket approval)
11. systems thinking vs software engineering (1 rows) - status: SETTLED (DIFFERENT, blanket approval)
12. visual semiotics vs psychology (1 rows) - status: SETTLED (DIFFERENT, blanket approval)
13. psychology vs behavioral economics (1 rows) - status: SETTLED (DIFFERENT, blanket approval)
14. creative process vs cultural design (1 rows) - status: SETTLED (DIFFERENT, blanket approval)
15. behavioral economics vs emerging (1 rows) - status: SETTLED (DIFFERENT, blanket approval)
16. strategic thinking vs psychology (1 rows) - status: SETTLED (DIFFERENT, blanket approval)
17. cognitive science vs neuroscience (1 rows) - status: SETTLED (DIFFERENT, blanket approval)
18. operations research vs creative process (1 rows) - status: SETTLED (DIFFERENT, blanket approval)
19. motion & time vs human-computer interaction (1 rows) - status: SETTLED (DIFFERENT, blanket approval)
20. finance vs economics (1 rows) - status: SETTLED (DIFFERENT, blanket approval)
21. design psychology vs emerging (1 rows) - status: SETTLED (DIFFERENT, blanket approval)
22. artificial intelligence vs software engineering (1 rows) - status: SETTLED (DIFFERENT, blanket approval)
23. research methodology vs finance (1 rows) - status: SETTLED (DIFFERENT, blanket approval)
24. strategic thinking vs behavioral economics (1 rows) - status: SETTLED (DIFFERENT, blanket approval)
25. psychology vs health & medicine (1 rows) - status: SETTLED (DIFFERENT, blanket approval)
26. behavioral economics vs psychology (1 rows) - status: SETTLED (DIFFERENT, blanket approval)

## Item 1 - SETTLED: DIFFERENT (owner, 2026-09-21) - boundary = mechanism of mind vs behaviour/affect/outcome

## Items 2-16 - SETTLED BY BLANKET APPROVAL (owner PART2 B: all pairs are DIFFERENT) - drafted boundaries

- finance vs strategic thinking :: power/index of capital allocation and valuation => finance; long-horizon choice under uncertainty without capital markets => strategic thinking
- design thinking vs human-computer interaction :: process/method for problem framing in any domain => design thinking; interface, interaction or usability mechanism => HCI
- research methodology vs risk management :: how knowledge is produced or validated => research methodology; how downside exposure is identified or mitigated => risk management
- operations research vs strategic thinking :: formal optimisation, scheduling or queueing model => operations research; ends and positioning chosen without a formal model => strategic thinking
- operations research vs behavioral economics :: optimisation/decision model with a formal objective => operations research; systematic deviation of human judgement from that model => behavioral economics
- visual semiotics vs communication theory :: sign, code and meaning of visual form => visual semiotics; message transmission, audience or framing => communication theory
- artificial intelligence vs economics :: learning, representation or model behaviour => AI; market, incentive or resource consequence of it => economics
- research methodology vs behavioral economics :: design, sampling or validity of a study => research methodology; bias or choice anomaly as the finding => behavioral economics
- systems thinking vs software engineering :: feedback, stocks/flows or emergence at system level => systems thinking; construction practice of software artefacts => software engineering
- visual semiotics vs psychology :: meaning carried by visual sign systems => visual semiotics; perception, attention or affect of an observer => psychology
- psychology vs behavioral economics :: affect, personality or clinical behaviour => psychology; choice, incentive or market-facing decision => behavioral economics
- creative process vs cultural design :: how an idea is generated or refined => creative process; how meaning or identity is designed into a culture or brand => cultural design
- behavioral economics vs emerging (catch-all) :: decision anomaly with an incentive frame => behavioral economics; the item does not yet belong to any established slot => emerging (a label of last resort, never a first choice)
- strategic thinking vs psychology :: deliberate positioning or choice of ends => strategic thinking; cognitive or affective mechanism of the decision maker => psychology

Status: all 16 discipline pairs are DIFFERENT with a drafted boundary test. No per-pair questions remain.
Next: wire config/normalization_map.yaml into the comparison layer, then re-measure kappa.

## CORRECTION (appended 2026-09-21, session 12) — the "Next:" line above is stale (BUG-356)

Line "Next: wire config/normalization_map.yaml into the comparison layer, then re-measure kappa" is
**already done**: `scripts/anchor2_kappa.py:56` reads the map (D-307) and the domain observed agreement
moved 0.3938 -> 0.4385. Do not re-do it.

What this queue actually still owes:

1. **10 pairs have no drafted boundary test.** Re-derived against the ANCHOR-2 sheet, the disagreement
   list is **26 pairs / 31 rows**, not 16. Items 17-26 have no test; they are drafted in
   `governance/BOUNDARY_DISCRIMINATORS_20260921.md`.
2. **Re-check asymmetric pairs.** Rows 25/26 are the same two slots in opposite directions, and rows
   19/23 pair a method with an object. A rule phrased on a slot NAME will not converge for these;
   the `default_home` + escape-condition form is recommended instead.
3. **Nothing is wired into the classifier prompt yet.** The pairs are settled as a ruling, not applied
   as behaviour. That wiring is a separate, measurable step (it changes what S4 emits), and it must be
   measured on the frozen ruler, not asserted.

PART 1 is additionally re-issued as `governance/PART1_PART2_REISSUE_20260921.md` (BUG-348): NOVEL=0 —
no human label introduced a domain concept absent from the menu.
