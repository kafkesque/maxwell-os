#!/bin/sh
# resolve_python.sh - BUG-1000: ONE reader of the interpreter pin, for the surfaces that cannot import Python.
#
# WHY THIS EXISTS. D-2745 pinned `run.python_bin` inside pipeline/runner.py, so the STAGES got one interpreter.
# It did not cover the two surfaces that run OUTSIDE the runner: the justfile ladder (193 declaring lines, each
# shelling a bare `python3`) and the git pre-commit hook (5 rails). Both resolve a bare NAME by PATH ORDER, and
# PATH order differs between shells on ONE machine (BUG-607's class). MEASURED 2026-10-25, this machine:
#     PATH=/usr/bin:/bin              -> git commit   : RAIL 0 died, No module named 'yaml'
#     PATH=/opt/homebrew/bin:/usr/bin -> just health  : line 20 died, No module named 'mcp'
# Both were REFUSALS FOR THE WRONG REASON: the rails were fine, the interpreter was not.
#
# WHAT IT DOES. It reads `run.python_bin` from config/pipeline_config.yaml - the SAME home pipeline/runner.py
# and scripts/phase0_idempotency.py read, never a second copy of the path (C12/C12c) - and then PROVES the pin
# before printing it:
#     (1) the key exists and names an EXECUTABLE file, and
#     (2) that interpreter can import every module in `run.python_required_modules` (same file), which is the
#         ACTUAL failure mode above - not "does a file exist" but "is the file the one that has the deps".
# A pin that fails either test is REFUSED with a diagnostic naming the key, the value, the modules and the
# remedy. THERE IS NO FALLBACK: a fallback is precisely how the ladder ran on the wrong interpreter unnoticed.
#
# WHY THIS IS A SHELL SCRIPT AND NOT PYTHON. A Python resolver would need a correct interpreter first - the
# chicken and egg that produced the bug. awk/dirname are on every target platform (C26) and need nothing.
#
# USAGE  sh scripts/resolve_python.sh --dir   -> the DIRECTORY to PREPEND to PATH (for callers that shell `python3`)
#        sh scripts/resolve_python.sh         -> the interpreter path itself (for a direct exec)
# EXIT   0 resolved and proven | 2 pin absent / not executable / config unreadable / cannot import a module
set -u

DEFAULT_CONFIG="config/pipeline_config.yaml"

die() {
    printf 'FAIL-CLOSED (BUG-1000 / scripts/resolve_python.sh): %s\n' "$1" >&2
    exit 2
}

MODE="bin"
case "${1:-}" in
    --dir) MODE="dir" ;;
    "")    MODE="bin" ;;
    *)     die "unknown argument: $1 (accepted: --dir, or no argument)" ;;
esac

# The config home is resolved from THIS SCRIPT's directory, never from the caller's cwd: the pre-commit hook runs
# at the repo root but an operator may run this from anywhere in the tree (D-2687: never assume a path shape).
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd) || die "the script's own directory does not resolve"
CONFIG="$ROOT/$DEFAULT_CONFIG"
[ -r "$CONFIG" ] || die "the declared config home is unreadable: $CONFIG"

# A scalar key with its comment stripped. sub() rather than a field split, because a value may contain a colon.
read_scalar() {
    awk -v k="$1" '
        $0 ~ "^[[:space:]]*" k ":" { line=$0; sub("^[^:]*:[[:space:]]*", "", line);
                                     sub("[[:space:]]*#.*$", "", line);
                                     gsub(/[[:space:]]+$/, "", line); print line; exit }
    ' "$CONFIG"
}

# A flow list `[a, b]` OR a single bare value -> space-separated words. Both shapes are accepted: a one-element
# list is a common simplification, and refusing it would be a trap rather than a rule.
read_list() {
    awk -v k="$1" '
        $0 ~ "^[[:space:]]*" k ":" { line=$0; sub("^[^:]*:[[:space:]]*", "", line);
                                     sub("[[:space:]]*#.*$", "", line);
                                     gsub(/[][,"]/, " ", line); print line; exit }
    ' "$CONFIG"
}

PIN=$(read_scalar python_bin)
[ -n "${PIN:-}" ] || die "config/pipeline_config.yaml#run.python_bin is ABSENT - refusing to guess an interpreter"
[ -x "$PIN" ] || die "run.python_bin names a file that is NOT executable: $PIN"

# The flow-list brackets and commas are already spaces; collapse and trim so no EMPTY word reaches `import`
# (measured while writing this: `[yaml, mcp]` became ", yaml, mcp, " and the check failed on a SyntaxError of
# its own making - a prover that fails for its own reason is worse than no prover).
MODULES=$(read_list python_required_modules | tr -s '[:space:]' ' ' | sed 's/^ //; s/ $//')
[ -n "${MODULES:-}" ] || die "config/pipeline_config.yaml#run.python_required_modules is ABSENT - a pin that is never proven is a name, not an interpreter"

# ONE import call naming every module, so a failure can quote the interpreter's OWN error rather than paraphrase.
IMPORT_LIST=$(printf '%s' "$MODULES" | sed 's/ /, /g')
if ! ERROR=$("$PIN" -c "import $IMPORT_LIST" 2>&1); then
    {
        printf 'FAIL-CLOSED (BUG-1000 / scripts/resolve_python.sh): run.python_bin cannot import the modules the rails need.\n'
        printf '   key    : config/pipeline_config.yaml#run.python_bin\n'
        printf '   value  : %s\n' "$PIN"
        printf '   needed : %s\n' "$IMPORT_LIST"
        printf '   it said: %s\n' "$(printf '%s\n' "$ERROR" | tail -1)"
        printf '   remedy : point run.python_bin at an interpreter that has them, or install them into this one.\n'
    } >&2
    exit 2
fi

if [ "$MODE" = "dir" ]; then
    dirname -- "$PIN"
else
    printf '%s\n' "$PIN"
fi
