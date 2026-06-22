# Dev Machine Hygiene — agent instructions

Read-only scanners and archive-first cleanup helpers. Never auto-delete.

## Verification (run before finishing any task)

```bash
python3 -m py_compile hygiene_scan.py
bash -n hygiene-scan.sh hygiene-cleanup.sh
python3 -m pytest tests/ -q
```

If pytest is not configured, add it as a dev dependency and wire CI only if the task requires it.

## Scope rules

- Fix only issues in the current task scope.
- Do not modify CI workflows unless the task explicitly requires it.
- Do not add dependencies beyond pytest for test tasks.
- Scripts must stay read-only by default; cleanup stays archive-first.
- Prefer small, reviewable PRs.

## Jules specific instructions

- Only add tests for pure helper functions that need no filesystem mocking.
- Good targets: `existing_roots`, `is_tool_managed`, `is_active_runtime_cache`, `is_app_owned_empty_dir`, `is_ignored_broken_link`.
- Do not test `find_projects`, `find_caches`, or other filesystem-walking functions.
- Tests live in `tests/test_hygiene_scan.py`.
