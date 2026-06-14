# dev-machine-hygiene

Read-only scanners and reversible cleanup helpers for local dev machines.

Turn messy folders, orphan caches, and broken symlinks into a reviewable report — without auto-deleting anything.

## Tools

### Machine hygiene scan (read-only)

```bash
python3 machine_hygiene_scan.py
```

Reports:

- Project-like folders outside `~/Projects`
- Rebuildable cache candidates (`node_modules`, `.venv`, `.pytest_cache`, etc.)
- Active runtime caches to leave alone
- Orphan signals and broken symlinks
- LaunchAgent failures under `~/Library/LaunchAgents`
- Large files on Desktop, Downloads, and Movies (>= 500MB)

### ForgeGuard scan (read-only)

```bash
./forgeguard-scan.sh
```

Quick monthly pass for empty dirs, orphan venvs, broken symlinks, Codex staging bloat, and stray installers.

### ForgeGuard cleanup (dry-run by default)

```bash
./forgeguard-cleanup.sh           # preview only
./forgeguard-cleanup.sh --execute # archive-first moves
```

Default rule: **archive first, trash second, delete only after manual review.**

## Project bootstrap templates

`templates/project-bootstrap/` includes starter `README` and `.gitignore` templates for new experiments.

## Safety

These tools only **read** (scan) or **move/archive** with explicit `--execute`. They never touch secrets, cloud accounts, or git history.

## License

MIT
