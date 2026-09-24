# Kimi

1. Same two attachments, same prompt block, `{CHUNK}` as on Claude - the pack is provider-agnostic by design.
2. If a paste truncates, chunk by 25 rows and keep the taxonomy in EVERY message. Never paraphrase it to save space.
3. Save each reply verbatim as `governance/frontier_pack_20260924/raw_kimi_<chunk>.md`.
4. `python3 scripts/parse_frontier_pack.py governance/frontier_pack_20260924`
5. The parser rejects any domain value outside the 44-value menu, so a passing run is usable.
