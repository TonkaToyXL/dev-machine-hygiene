#!/usr/bin/env bash
# Hygiene cleanup — archive-first, reversible
# Usage: ./hygiene-cleanup.sh           # dry-run
#        ./hygiene-cleanup.sh --execute
set -euo pipefail

EXECUTE=false
[[ "${1:-}" == "--execute" ]] && EXECUTE=true

ARCHIVE="$HOME/Projects/Archive/$(date +%Y-%m)-machine-hygiene"
LOG_DIR="$ARCHIVE/logs"
mkdir -p "$ARCHIVE"/{codex-tmp,orphan-venvs,empty-stubs,installers,dmgs,misc,logs} "$LOG_DIR"

run() {
  if $EXECUTE; then
    eval "$@"
  else
    echo "[DRY-RUN] $*"
  fi
}

echo "=== Hygiene Cleanup $(date) mode=$($EXECUTE && echo EXECUTE || echo DRY-RUN) ==="

# Codex marketplace staging
if [ -d "$HOME/.codex/.tmp/marketplaces/.staging" ]; then
  cnt=$(find "$HOME/.codex/.tmp/marketplaces/.staging" -maxdepth 1 -type d -name 'marketplace-upgrade-*' 2>/dev/null | wc -l | tr -d ' ')
  sz=$(du -sh "$HOME/.codex/.tmp/marketplaces/.staging" 2>/dev/null | cut -f1)
  if [ "${cnt:-0}" -gt 5 ] || { [ "$sz" != "0B" ] && [ "${sz%M*}" != "$sz" ]; }; then
    run "mv '$HOME/.codex/.tmp/marketplaces/.staging' '$ARCHIVE/codex-tmp/staging-$(date +%Y%m%d)'"
    run "mkdir -p '$HOME/.codex/.tmp/marketplaces/.staging'"
  fi
fi

# Codex bundled cache (regenerates)
if [ -d "$HOME/.codex/.tmp/bundled-marketplaces" ]; then
  run "mv '$HOME/.codex/.tmp/bundled-marketplaces' '$ARCHIVE/codex-tmp/bundled-$(date +%Y%m%d)'"
fi

# Orphan venvs under ~/.local/venvs with no matching project folder
if [ -d "$HOME/.local/venvs" ]; then
  for v in "$HOME/.local/venvs"/*; do
    [ -d "$v" ] || continue
    name=$(basename "$v")
    if ! find "$HOME/Projects" "$HOME/Documents" -maxdepth 5 -type d -iname "*${name}*" 2>/dev/null | grep -q .; then
      run "mv '$v' '$ARCHIVE/orphan-venvs/'"
    fi
  done
fi

# Broken symlinks in Projects
while IFS= read -r link; do
  run "rm '$link'"
done < <(find "$HOME/Projects" -type l ! -exec test -e {} \; -print 2>/dev/null)

# pytest caches
while IFS= read -r d; do
  run "rm -rf '$d'"
done < <(find "$HOME/Projects" "$HOME/Documents" -name ".pytest_cache" -type d 2>/dev/null)

# DMGs in Downloads
run "mkdir -p '$ARCHIVE/dmgs'"
for f in "$HOME/Downloads/"*.dmg; do
  [ -f "$f" ] || continue
  run "mv '$f' '$ARCHIVE/dmgs/'"
done

echo "Done."
