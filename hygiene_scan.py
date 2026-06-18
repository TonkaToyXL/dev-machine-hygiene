#!/usr/bin/env python3
"""Read-only local dev hygiene scanner.

This prints a compact report. It does not modify files.
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


HOME = Path.home()
PROJECTS = HOME / "Projects"
PROJECT_SCAN_ROOTS = [
    PROJECTS,
    HOME / "Documents",
    HOME / "Desktop",
    HOME / "Downloads",
]

CACHE_SCAN_ROOTS = [
    *PROJECT_SCAN_ROOTS,
    HOME / ".opencode",
    HOME / ".continue",
    HOME / ".codex",
    HOME / ".agents",
    HOME / ".grok",
    HOME / ".npm",
]

PROJECT_MARKERS = {
    ".git",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Cargo.toml",
    "go.mod",
    "Makefile",
    "README.md",
    "AGENTS.md",
    "SKILL.md",
}

CACHE_NAMES = {
    "node_modules",
    ".venv",
    "venv",
    ".next",
    "dist",
    "build",
    "out",
    "target",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "_npx",
    ".tmp",
    "backups",
    "state-snapshots",
}

PRUNE_NAMES = CACHE_NAMES | {
    ".git",
    "Archive",
    "Library",
    "Movies",
    "Music",
    "Pictures",
    ".Trash",
}

TOOL_MANAGED_PARTS = {
    ".codex/skills",
    ".codex/plugins",
    ".codex/.tmp/marketplaces",
    ".agents/skills",
    ".grok/skills",
    ".grok/bundled",
    ".grok/marketplace-cache",
}

ORPHAN_NAME = re.compile(
    r"(^|[-_ .])(old|tmp|temp|backup|bak|copy|final|test|demo|draft|untitled)([-_ .]|$)",
    re.IGNORECASE,
)


@dataclass
class ProjectHit:
    path: Path
    size: str
    modified: str
    markers: list[str]
    reason: str


@dataclass
class CacheHit:
    path: Path
    size: str
    note: str = "cleanup candidate"


@dataclass
class LaunchAgentHit:
    label: str
    pid: str
    last_exit: str
    note: str = ""


ACTIVE_CACHE_PATHS = {
    HOME / ".codex" / ".tmp",
    HOME / ".codex" / "backups",
    HOME / ".npm" / "_npx",
    HOME / ".opencode" / "node_modules",
}

APP_OWNED_EMPTY_DIRS: set[Path] = set()

IGNORED_BROKEN_LINK_PREFIXES: set[Path] = set()


def run(args: list[str]) -> str:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=8).stdout.strip()
    except Exception:
        return ""


def size_of(path: Path) -> str:
    out = run(["/usr/bin/du", "-sh", str(path)])
    return out.split()[0] if out else "unknown"


def modified(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
    except OSError:
        return "unknown"


def existing_roots(roots: list[Path]) -> list[Path]:
    return [root for root in roots if root.exists()]


def is_tool_managed(path: Path) -> bool:
    text = str(path.relative_to(HOME)) if path.is_relative_to(HOME) else str(path)
    return any(part in text for part in TOOL_MANAGED_PARTS)


def is_active_runtime_cache(path: Path) -> bool:
    return path in ACTIVE_CACHE_PATHS


def is_app_owned_empty_dir(path: Path) -> bool:
    if path in APP_OWNED_EMPTY_DIRS:
        return True
    recordings = HOME / "Documents" / "superwhisper" / "recordings"
    return path.parent == recordings


def is_ignored_broken_link(path: Path) -> bool:
    return any(path.is_relative_to(prefix) for prefix in IGNORED_BROKEN_LINK_PREFIXES)


def find_projects(max_depth: int = 4) -> list[ProjectHit]:
    hits: dict[Path, ProjectHit] = {}
    for root in existing_roots(PROJECT_SCAN_ROOTS):
        for dirpath, dirnames, _filenames in os.walk(root):
            path = Path(dirpath)
            if is_tool_managed(path):
                dirnames[:] = []
                continue
            depth = len(path.relative_to(root).parts)
            if depth > max_depth:
                dirnames[:] = []
                continue

            markers = sorted(name for name in PROJECT_MARKERS if (path / name).exists())
            if markers:
                reason = "project markers"
                if not path.is_relative_to(PROJECTS):
                    reason = "outside /Projects"
                elif "README.md" not in markers and ".git" not in markers:
                    reason = "no README or Git metadata"
                hits[path] = ProjectHit(path, size_of(path), modified(path), markers, reason)
                if ".git" in markers:
                    dirnames[:] = []
                    continue

            dirnames[:] = [name for name in dirnames if name not in PRUNE_NAMES]
    return sorted(hits.values(), key=lambda hit: str(hit.path))


def find_caches(max_depth: int = 6, min_mb: int = 50) -> tuple[list[CacheHit], list[CacheHit]]:
    hits: list[CacheHit] = []
    watched: list[CacheHit] = []
    for root in existing_roots(CACHE_SCAN_ROOTS):
        for dirpath, dirnames, _filenames in os.walk(root):
            path = Path(dirpath)
            depth = len(path.relative_to(root).parts)
            if depth > max_depth:
                dirnames[:] = []
                continue

            keep: list[str] = []
            for name in dirnames:
                child = path / name
                if name in CACHE_NAMES:
                    size = size_of(child)
                    if size.endswith("G") or (size.endswith("M") and float(size[:-1]) >= min_mb):
                        if is_active_runtime_cache(child):
                            watched.append(CacheHit(child, size, "active runtime cache"))
                        else:
                            hits.append(CacheHit(child, size))
                else:
                    keep.append(name)
            dirnames[:] = [name for name in keep if name not in PRUNE_NAMES]
    return (
        sorted(hits, key=lambda hit: hit.path.name),
        sorted(watched, key=lambda hit: hit.path.name),
    )


def find_broken_links(max_depth: int = 6) -> list[Path]:
    broken: list[Path] = []
    for root in existing_roots(PROJECT_SCAN_ROOTS):
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            path = Path(dirpath)
            depth = len(path.relative_to(root).parts)
            if depth > max_depth:
                dirnames[:] = []
                continue

            for name in [*dirnames, *filenames]:
                child = path / name
                try:
                    if child.is_symlink() and not child.exists() and not is_ignored_broken_link(child):
                        broken.append(child)
                except OSError:
                    pass
            dirnames[:] = [name for name in dirnames if name not in PRUNE_NAMES]
    return sorted(broken)


def user_launchagent_labels() -> set[str]:
    agents_dir = HOME / "Library" / "LaunchAgents"
    if not agents_dir.exists():
        return set()
    labels: set[str] = set()
    for plist in agents_dir.glob("*.plist"):
        labels.add(plist.stem)
    return labels


def find_launchagent_issues() -> list[LaunchAgentHit]:
    hits: list[LaunchAgentHit] = []
    labels = user_launchagent_labels()
    out = run(["/bin/launchctl", "list"])
    if not out:
        return hits
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 3 or parts[2] not in labels:
            continue
        pid, last_exit, label = parts[0], parts[1], parts[2]
        if last_exit in {"0", "-"}:
            continue
        hits.append(
            LaunchAgentHit(
                label,
                pid,
                last_exit,
                "last run failed — check StandardErrorPath in plist",
            )
        )
    return sorted(hits, key=lambda hit: hit.label)


def count_broken_links(roots: list[Path], max_depth: int = 4) -> int:
    total = 0
    for root in existing_roots(roots):
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            path = Path(dirpath)
            depth = len(path.relative_to(root).parts)
            if depth > max_depth:
                dirnames[:] = []
                continue
            for name in [*dirnames, *filenames]:
                child = path / name
                try:
                    if child.is_symlink() and not child.exists() and not is_ignored_broken_link(child):
                        total += 1
                except OSError:
                    pass
            dirnames[:] = [name for name in dirnames if name not in PRUNE_NAMES]
    return total


def find_large_home_files(min_mb: int = 500) -> list[tuple[Path, str]]:
    hits: list[tuple[Path, str]] = []
    for root in [HOME / "Desktop", HOME / "Movies", HOME / "Downloads"]:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            path = Path(dirpath)
            dirnames[:] = [name for name in dirnames if name not in PRUNE_NAMES]
            for name in filenames:
                child = path / name
                try:
                    if child.stat().st_size >= min_mb * 1024 * 1024:
                        hits.append((child, size_of(child)))
                except OSError:
                    pass
    return sorted(hits, key=lambda item: str(item[0]))


def find_orphans(max_depth: int = 3) -> list[Path]:
    orphans: list[Path] = []
    for root in [PROJECTS, HOME / "Documents", HOME / "Desktop", HOME / "Downloads"]:
        if not root.exists():
            continue
        for dirpath, dirnames, _filenames in os.walk(root):
            path = Path(dirpath)
            depth = len(path.relative_to(root).parts)
            if depth > max_depth:
                dirnames[:] = []
                continue

            has_marker = any((path / marker).exists() for marker in PROJECT_MARKERS)
            empty = not any(path.iterdir()) if path.exists() else False
            if empty and is_app_owned_empty_dir(path):
                dirnames[:] = [name for name in dirnames if name not in PRUNE_NAMES]
                continue
            if path != root and (empty or (ORPHAN_NAME.search(path.name) and not has_marker)):
                orphans.append(path)
            dirnames[:] = [name for name in dirnames if name not in PRUNE_NAMES]
    return sorted(orphans)


def print_section(title: str) -> None:
    print(f"\n## {title}")


def main() -> int:
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    print("# Machine Hygiene Scan")
    print(f"Generated: {datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M')}")

    projects = find_projects()
    caches, watched_caches = find_caches()
    broken = find_broken_links()
    orphans = find_orphans()
    launch_issues = find_launchagent_issues()
    scoped_broken = count_broken_links([PROJECTS, HOME / "Library" / "LaunchAgents"])
    large_files = find_large_home_files()

    print_section("Summary")
    print(f"- Project-like folders: {len(projects)}")
    print(f"- Cleanup cache candidates: {len(caches)}")
    print(f"- Watched active caches: {len(watched_caches)}")
    print(f"- Orphan signals: {len(orphans)}")
    print(f"- Broken symlinks (Projects + LaunchAgents): {scoped_broken}")
    print(f"- Broken symlinks (project scan): {len(broken)}")
    print(f"- LaunchAgent issues (~/Library/LaunchAgents): {len(launch_issues)}")
    print(f"- Large home files (>=500MB): {len(large_files)}")

    print_section("Project-Like Folders")
    for hit in projects:
        marker_text = ", ".join(hit.markers[:6])
        print(f"- {hit.path} | {hit.size} | {hit.modified} | {hit.reason} | {marker_text}")

    print_section("Cleanup Cache Candidates")
    for hit in caches:
        print(f"- {hit.path} | {hit.size} | suggested action: move to Trash after review")

    print_section("Watched Active Caches")
    for hit in watched_caches:
        print(f"- {hit.path} | {hit.size} | {hit.note}; leave alone unless intentionally resetting that tool")

    print_section("Orphan Signals")
    for path in orphans:
        print(f"- {path} | {size_of(path)} | suggested action: archive after review")

    print_section("Broken Symlinks")
    for path in broken:
        print(f"- {path} -> {os.readlink(path)}")

    print_section("LaunchAgent Issues")
    if launch_issues:
        for hit in launch_issues:
            print(
                f"- {hit.label} | pid={hit.pid} | last_exit={hit.last_exit} | {hit.note}"
            )
    else:
        print("- none")

    print_section("Large Home Files")
    if large_files:
        for path, size in large_files:
            print(f"- {path} | {size}")
    else:
        print("- none")

    print_section("Review Command Pattern")
    print('mkdir -p "$HOME/Projects/Archive/YYYY-MM-machine-hygiene" "$HOME/.Trash/YYYY-MM-machine-hygiene"')
    print('mv "/path/to/orphan" "$HOME/Projects/Archive/YYYY-MM-machine-hygiene/"')
    print('mv "/path/to/cache" "$HOME/.Trash/YYYY-MM-machine-hygiene/"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
