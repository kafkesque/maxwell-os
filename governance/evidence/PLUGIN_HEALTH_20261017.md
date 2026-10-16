# Plugin Health Receipt — goose 1.39.0

measured_at: 2026-10-17 00:28 +02:00 · config: `~/.config/goose/config.yaml` (read-only) · 26 declared (19 enabled / 7 disabled)
TASK 1 authority = stdio handshake (initialize → initialized → tools/list). TASK 2 authority = `goose run` banner. TASK 3 authority = delivered tool surface (61 tools).

| extension | type | enabled | handshake | tools | wall_s | first tools / exact error |
|---|---|---|---|---|---|---|
| analyze | platform | yes | n/a (no cmd) | 1 | – | surface: analyze |
| apps | platform | yes | n/a (no cmd) | 4 | – | create_app, delete_app, iterate_app |
| chatrecall | platform | yes | n/a (no cmd) | 1 | – | chatrecall |
| code_execution | platform | yes | n/a (no cmd) | 1 | – | execute_typescript |
| developer | platform | yes | n/a (no cmd) | 5 | – | edit, shell, write, tree, read_image |
| extensionmanager | platform | yes | n/a (no cmd) | 3 | – | list_resources, read_resource, search_available_extensions |
| scheduler | platform | yes | n/a (no cmd) | **0** | – | no error emitted — silently absent |
| skills | platform | yes | n/a (no cmd) | 2 | – | load, load_skill |
| summarize | platform | yes | n/a (no cmd) | 1 | – | summarize |
| summon | platform | yes | n/a (no cmd) | 2 | – | get_function_details, list_functions |
| todo | platform | yes | n/a (no cmd) | 1 | – | todo_write |
| tom | platform | yes | n/a (no cmd) | 0 | – | context injection only, no tools by design |
| memory | builtin | yes | n/a (builtin) | 4 | – | remember_memory, retrieve_memories, remove_memory_category, remove_specific_memory |
| docguard | stdio | yes | YES | 4 | 1.8 | check_protected, safe_write, safe_append |
| fetch | stdio | yes | YES | 1 | 0.8 | fetch |
| filesystem | stdio | yes | YES | 14 | 1.2 | read_file, read_text_file, read_media_file |
| gitmcp-mcp | stdio | yes | YES | 12 | 0.8 | git_status, git_diff_unstaged, git_diff_staged |
| reddit | stdio | yes | **NO** | **0** | 30.2 | `ModuleNotFoundError: An HTTP transport library needs to be installed.` |
| youtubetranscript | stdio | yes | YES | 4 | 1.6 | get_transcript, get_timed_transcript, get_video_info |
| orchestrator | platform | no | n/a (no cmd) | – | – | platform type, disabled |
| computercontroller | builtin | no | n/a (builtin) | – | – | builtin type, disabled |
| autovisualiser | builtin | no | n/a (builtin) | – | – | builtin type, disabled |
| tutorial | builtin | no | n/a (builtin) | – | – | builtin type, disabled |
| pdfreader | stdio | no | **NO** | 0 | 30.2 | `ModuleNotFoundError: No module named 'mcp.server.fastmcp'. This is mcp 2.x, where FastMCP was renamed to MCPServer ... or pin 'mcp<2' to keep running v1 code.` |
| gitmcp | stdio | no | YES | 5 | 4.5 | match_common_libs_owner_repo_mapping, fetch_generic_documentation, search_generic_documentation |
| puppeteer | stdio | no | YES | 7 | 1.0 | puppeteer_navigate, puppeteer_screenshot, puppeteer_click |

## VERDICT

- analyze — WORKING (platform; 1 tool in delivered surface)
- apps — WORKING (platform; 4 tools)
- chatrecall — WORKING (platform; 1 tool)
- code_execution — WORKING (platform; 1 tool: execute_typescript)
- developer — WORKING (platform; 5 tools)
- extensionmanager — WORKING (platform; 3 tools)
- scheduler — **DEAD** (0 tools; exact error: **none emitted** — silently absent from the delivered surface and from `sessions.extension_data` in 12/12 recent sessions while all other loaded extensions are listed)
- skills — WORKING (platform; 2 tools)
- summarize — WORKING (platform; 1 tool)
- summon — WORKING (platform; 2 tools)
- todo — WORKING (platform; 1 tool)
- tom — NOT-A-TOOL-EXTENSION (platform; injects GOOSE_MOIM context into every turn, contributes 0 tools by design)
- memory — WORKING (builtin; 4 tools)
- docguard — WORKING (stdio handshake, 4 tools)
- fetch — WORKING (stdio handshake, 1 tool)
- filesystem — WORKING (stdio handshake, 14 tools)
- gitmcp-mcp — WORKING (stdio handshake, 12 tools)
- reddit — **DEAD** (handshake: started=no, 0 tools; exact error: `ModuleNotFoundError: An HTTP transport library needs to be installed.`; goose banner agrees: `Warning: Failed to start extension 'Reddit'`)
- youtubetranscript — WORKING (stdio handshake, 4 tools: get_transcript, get_timed_transcript, get_video_info, get_available_languages)
- orchestrator — UNTESTABLE (platform type, disabled, no cmd/args → nothing to handshake; no tool surface since disabled)
- computercontroller — NOT-A-TOOL-EXTENSION (builtin type, disabled, no cmd/args; cannot be handshaken)
- autovisualiser — NOT-A-TOOL-EXTENSION (builtin type, disabled, no cmd/args; cannot be handshaken)
- tutorial — NOT-A-TOOL-EXTENSION (builtin type, disabled, no cmd/args; cannot be handshaken)
- pdfreader — **DEAD** (handshake: started=no, 0 tools; exact error: `ModuleNotFoundError: No module named 'mcp.server.fastmcp'. This is mcp 2.x, where FastMCP was renamed to MCPServer (from mcp.server.mcpserver import MCPServer) and other APIs changed; see the migration guide at https://py.sdk.modelcontextprotocol.io/v2/migration/#fastmcp-renamed-to-mcpserver or pin 'mcp<2' to keep running v1 code.`)
- gitmcp — WORKING (stdio handshake, 5 tools; disabled by choice)
- puppeteer — WORKING (stdio handshake, 7 tools; disabled by choice)

## WHAT THIS MEANS

1. Two ENABLED extensions are lies: **reddit** (enabled:true, goose itself refuses it — `ModuleNotFoundError: An HTTP transport library needs to be installed.`; the uvx resolution `uvx --from git+https://github.com/adhikasp/mcp-reddit.git mcp-reddit` succeeds and resolves to `~/.cache/uv/archive-v0/q2AoTJIWbpM5PhRhhUp4E/bin/mcp-reddit`, then dies at import in redditwarp `http/transport/reg_ASYNC.py:26` because no HTTP transport adapter is installed for py3.14) and **scheduler** (enabled:true, 0 tools, silently absent, no warning at all).
2. Reddit faults BEFORE the handshake: zero stdout, so it contributes no tools AND costs a startup crash in every session; goose drops it from the session record (session 20261016_15 lists 17 extensions, not 19).
3. TASK 2 = ONE failure only: `Warning: Failed to start extension 'Reddit'` + `Hint: once the session starts, ask goose to help debug the 'Reddit' extension`. Everything else the harness manages to run.
4. YouTubetranscript is CONFIRMED WORKING with the expected 4 tools — BUG-873-class concern disproved for it.
5. Disabled `pdfreader` is also DEAD: uvx installs 38 packages in 90ms, then the package imports `mcp.server.fastmcp`, removed in mcp 2.x → enabling it as-is would fail immediately (pin `mcp<2` or drop the extension).
6. Counter-examples, not lies: disabled `gitmcp` (5 tools) and `puppeteer` (7 tools) both start fine — two healthy extensions deliberately switched off.
7. Platform/builtin extensions cannot be handshaken (no cmd/args); their tool counts here are the delivered-surface counts, so `started` is null rather than guessed in the receipt.
