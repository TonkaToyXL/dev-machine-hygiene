#!/usr/bin/env bash
# Quick hygiene scan — flags orphans, no destructive actions
set -euo pipefail

echo "=== Hygiene Scan $(date +%Y-%m-%d) ==="

echo ""
echo "-- Empty dirs (Documents, maxdepth 2) --"
find "$HOME/Documents" -maxdepth 2 -type d -empty 2>/dev/null || true

echo ""
echo "-- Orphan venvs (~/.local/venvs with no matching project) --"
for v in "$HOME/.local/venvs"/*; do
  [ -d "$v" ] || continue
  name=$(basename "$v")
  if ! find "$HOME/Projects" "$HOME/Documents" -maxdepth 5 -type d -iname "*${name}*" 2>/dev/null | grep -q .; then
    echo "ORPHAN VENV: $v ($(du -sh "$v" | cut -f1))"
  fi
done

echo ""
echo "-- Broken symlinks in Projects --"
find "$HOME/Projects" -type l ! -exec test -e {} \; -print 2>/dev/null || true

echo ""
echo "-- Codex staging bloat --"
STAGING="$HOME/.codex/.tmp/marketplaces/.staging"
if [ -d "$STAGING" ]; then
  sz=$(du -sm "$STAGING" | cut -f1)
  cnt=$(find "$STAGING" -maxdepth 1 -type d -name 'marketplace-upgrade-*' 2>/dev/null | wc -l | tr -d ' ')
  echo "Codex staging: ${sz}MB ($cnt dirs)"
  [ "$sz" -gt 500 ] && echo "WARN: run ./hygiene-cleanup.sh --execute"
fi

echo ""
echo "-- Code manifests outside ~/Projects --"
find "$HOME/Documents" -maxdepth 3 \( -name package.json -o -name pyproject.toml \) 2>/dev/null || true

echo ""
echo "-- Name-pattern orphans --"
find "$HOME/Projects" "$HOME/Documents" -maxdepth 3 -type d \
  \( -iname '*copy*' -o -iname '*backup*' -o -iname '*-old' -o -iname '*_old' -o -iname '*tmp*' \) \
  2>/dev/null | head -20 || true

echo ""
echo "=== Scan complete ==="
