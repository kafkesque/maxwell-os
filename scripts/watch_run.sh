#!/usr/bin/env bash
#
# watch_run.sh — lightweight health/process tracker for a Maxwell OS pipeline run.
#
# Read-only. Never touches the pipeline, the log, or any checkpoint. It only:
#   1. tails the run log for stage banners / progress / completion / failure markers
#   2. checks the runner process is alive (from .pipeline_runner.lock)
#   3. samples the omlx-server CPU% (the actual LLM compute)
#
# Usage:
#   scripts/watch_run.sh                 # continuous, auto-detects latest ratify2 log
#   scripts/watch_run.sh --once          # print a single snapshot and exit
#   scripts/watch_run.sh LOG INTERVAL    # explicit log file + interval seconds
#
# Exit codes: 0 = completed clean, 3 = failed/crashed, 4 = no run found.

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

ONCE=0
LOG=""
INTERVAL=10

# --- arg parse ----------------------------------------------------------------
for a in "$@"; do
  case "$a" in
    --once) ONCE=1 ;;
    --*) echo "unknown flag: $a" >&2; exit 2 ;;
    *) [ -z "$LOG" ] && LOG="$a" || INTERVAL="$a" ;;
  esac
done

[ -z "$LOG" ] && LOG="$(ls -t logs/ratify2_*.log 2>/dev/null | grep -v '_watch' | head -1)"
[ -z "$LOG" ] || [ ! -f "$LOG" ] && { echo "no ratify2 log found" >&2; exit 4; }

# --- helpers -------------------------------------------------------------------
runner_pid() { awk 'NR==1{print $1}' .pipeline_runner.lock 2>/dev/null; }
is_alive()   { local p; p="$(runner_pid)"; [ -n "$p" ] && ps -p "$p" >/dev/null 2>&1; }
current_stage() { grep -oE "▶ \[Stage [0-9.]+" "$LOG" | tail -1; }
progress()      { grep -oE "\[[0-9]+/[0-9]+\]" "$LOG" | tail -1; }
done_marker()   { grep -qE "Pipeline (complete|preview)" "$LOG"; }
fail_marker()   { grep -qE "❌ .*FAILED|⚠️  Stage .*FAILED|Traceback \(most recent" "$LOG"; }

stage_banner_count() { grep -cE "▶ \[Stage [0-9.]+" "$LOG"; }

omlx_line() {
  local pid cpu
  pid="$(pgrep -x omlx-server 2>/dev/null | head -1)"
  if [ -n "$pid" ]; then
    cpu="$(ps -o %cpu= -p "$pid" 2>/dev/null | tr -d ' ')"
    printf 'omlx-server pid=%s cpu=%s%%' "$pid" "${cpu:-?}"
  else
    printf 'omlx-server NOT RUNNING'
  fi
}

# --- state machine --------------------------------------------------------------
SEEN=0
while :; do
  TS="$(date '+%Y-%m-%d %H:%M:%S')"
  NOW_STAGE="$(current_stage)"
  NOW_COUNT="$(stage_banner_count)"

  # completion / failure take priority
  if done_marker; then
    echo "[$TS] ✅ DONE — $(grep -E 'Pipeline (complete|preview)' "$LOG" | tail -1)"
    exit 0
  fi
  if fail_marker; then
    echo "[$TS] ❌ FAILED/CRASHED — last lines:"
    tail -n 5 "$LOG"
    exit 3
  fi
  if ! is_alive; then
    # runner gone but no completion/failure marker yet → treat as stopped
    echo "[$TS] ⚠️ runner PID $(runner_pid) no longer alive; no completion marker seen"
    tail -n 8 "$LOG"
    exit 3
  fi

  # stage transition alert
  if [ "$NOW_COUNT" -gt "$SEEN" ]; then
    echo ""
    echo "[$TS] 🔔 STAGE TRANSITION → $NOW_STAGE"
    SEEN="$NOW_COUNT"
  fi

  printf '[%s] %s | progress %s | runner=%s | %s\n' \
    "$TS" "${NOW_STAGE:-pre-stage}" "$(progress)" "$(runner_pid)" "$(omlx_line)"

  [ "$ONCE" = 1 ] && exit 0
  sleep "$INTERVAL"
done
