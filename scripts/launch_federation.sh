#!/usr/bin/env bash
# DELTA_1 federation launcher (bash).
#
# Locates the three federation repos under configurable local roots, then runs
# each repo's entry points (shared bridge status + native smoke) and optionally
# opens the HTML portals. Read-only / smoke only; never mutates governed SSOT.
#
# Usage:
#   ./launch_federation.sh [--roots "/path/a:/path/b"] [--open-html] [--no-smoke]
#
# Defaults mirror the Windows PowerShell launcher: it searches C:/repos and
# C:/DEV equivalents. On Linux/mac pass --roots to point at your clones.
set -euo pipefail

ROOTS_DEFAULT="C:/repos:C:/DEV:$HOME/repos:$HOME/DEV:$(pwd)/.."
ROOTS="$ROOTS_DEFAULT"
OPEN_HTML=0
RUN_SMOKE=1
REPOS=("CODEX" "ABACUS" "cryoplant-project")

while [[ $# -gt 0 ]]; do
  case "$1" in
    --roots) ROOTS="$2"; shift 2;;
    --open-html) OPEN_HTML=1; shift;;
    --no-smoke) RUN_SMOKE=0; shift;;
    *) echo "unknown arg: $1"; exit 2;;
  esac
done

find_repo() {
  local name="$1"
  IFS=':' read -ra RARR <<< "$ROOTS"
  for root in "${RARR[@]}"; do
    [[ -z "$root" ]] && continue
    if [[ -d "$root/$name/.git" || -d "$root/$name" ]]; then
      echo "$root/$name"; return 0
    fi
  done
  return 1
}

open_url() {
  local target="$1"
  if command -v xdg-open >/dev/null 2>&1; then xdg-open "$target" >/dev/null 2>&1 || true
  elif command -v open >/dev/null 2>&1; then open "$target" >/dev/null 2>&1 || true
  else echo "  (open manually: $target)"; fi
}

echo "== DELTA_1 federation launcher =="
echo "roots: $ROOTS"
for repo in "${REPOS[@]}"; do
  echo
  echo "---- $repo ----"
  if ! path="$(find_repo "$repo")"; then
    echo "  NOT FOUND under roots (adjust --roots)"; continue
  fi
  echo "  path: $path"
  ( cd "$path"
    if python -c "import delta1_bridge" >/dev/null 2>&1; then
      echo "  [bridge] status:"; python -m delta1_bridge status --repo-root . || true
    else
      echo "  [bridge] delta1_bridge not importable here (vendor it or set PYTHONPATH)"
    fi
    if [[ "$RUN_SMOKE" -eq 1 ]]; then
      case "$repo" in
        ABACUS) echo "  [smoke] DMAIC_V3 self-smoke:"; python -m DMAIC_V3 self-smoke >/dev/null 2>&1 && echo "    OK" || echo "    (needs deps)";;
        cryoplant-project) echo "  [smoke] federation_smoke.py:"; python scripts/federation_smoke.py >/dev/null 2>&1 && echo "    OK" || echo "    (needs deps)";;
        CODEX) echo "  [smoke] pca_engine tests:"; (cd pca_engine && python -m pytest -q >/dev/null 2>&1 && echo "    OK" || echo "    (needs deps)");;
      esac
    fi
    if [[ "$OPEN_HTML" -eq 1 ]]; then
      for html in docs/index.html docs/bridge_overview.html qps/engineering_hub/site/index.html; do
        [[ -f "$html" ]] && { echo "  [html] opening $html"; open_url "$path/$html"; }
      done
    fi
  )
done
echo
echo "done."
