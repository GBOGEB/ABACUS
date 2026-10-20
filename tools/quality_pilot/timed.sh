#!/usr/bin/env bash
# Run one pilot scanner and record telemetry: tool,seconds,exit_code,version
#   usage: timed.sh <tool> <stdout-file|-> <command...>
#   env:   REPORTS (dir), TOOL_VERSION (optional, recorded as-is)
# Returns the scanner's own exit code, so the workflow step result stays honest.
set -uo pipefail
tool="$1"; out="$2"; shift 2
mkdir -p "${REPORTS:?REPORTS not set}"
start=$(date +%s)
err="$REPORTS/${tool}.stderr"
if [ "$out" = "-" ]; then
  "$@" 2> >(tee "$err" >&2)
else
  "$@" > "$out" 2> >(tee "$err" >&2)
fi
rc=$?
secs=$(( $(date +%s) - start ))
ver="${TOOL_VERSION:-}"
echo "${tool},${secs},${rc},${ver//,/;}" >> "$REPORTS/timings.csv"
echo "telemetry: ${tool} ${secs}s exit=${rc} ${ver}"
exit "$rc"
