# Dev Machine Hygiene

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![CI](https://github.com/TonkaToyXL/dev-machine-hygiene/actions/workflows/ci.yml/badge.svg)](https://github.com/TonkaToyXL/dev-machine-hygiene/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](./hygiene_scan.py)
[![Bash](https://img.shields.io/badge/Bash-5.0+-green)](./hygiene-scan.sh)

Read-only scanners and reversible cleanup helpers for local dev machines.

## Tools

| Script | Mode | Purpose |
|--------|------|---------|
| `hygiene_scan.py` | read-only | Full report: caches, orphans, symlinks, large files |
| `hygiene-scan.sh` | read-only | Quick monthly pass: empty dirs, venvs, staging bloat |
| `hygiene-cleanup.sh` | dry-run / `--execute` | Archive-first moves — never auto-deletes |

### Full scan

```bash
python3 hygiene_scan.py
```

Reports project-like folders outside `~/Projects`, rebuildable caches, broken symlinks, LaunchAgent failures, and large files (≥ 500 MB).

### Quick scan

```bash
./hygiene-scan.sh
```

### Cleanup

```bash
./hygiene-cleanup.sh           # preview
./hygiene-cleanup.sh --execute # archive-first moves
```

Rule: **archive first, review, then delete manually.**

## Bootstrap templates

`templates/project-bootstrap/` — starter `README` and `.gitignore` for new experiments.

## License

MIT
