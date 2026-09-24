# Claude

1. New Project or plain chat: upload `BLIND_INPUT_150.csv` and `taxonomy_domain_depth.md`.
2. Paste the MASTER PROMPT block with `{CHUNK}=rows 1-50`; repeat for 51-100 and 101-150, taxonomy attached each time.
3. Save each reply verbatim as `governance/frontier_pack_20260924/raw_claude_<chunk>.md`.
4. `python3 scripts/parse_frontier_pack.py governance/frontier_pack_20260924`
5. Keep the taxonomy attached - an unattached taxonomy is the top cause of invented domain values.
