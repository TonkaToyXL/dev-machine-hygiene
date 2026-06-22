import os
import sys
from pathlib import Path
import pytest

# Add the parent directory to sys.path to allow importing hygiene_scan
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import hygiene_scan

def test_existing_roots(tmp_path):
    root1 = tmp_path / "root1"
    root2 = tmp_path / "root2"
    root3 = tmp_path / "root3"

    root1.mkdir()
    root3.mkdir()

    roots = [root1, root2, root3]
    result = hygiene_scan.existing_roots(roots)

    assert result == [root1, root3]
    assert root2 not in result

def test_is_tool_managed(monkeypatch, tmp_path):
    monkeypatch.setattr(hygiene_scan, "HOME", tmp_path)

    # Tool managed paths
    p1 = tmp_path / ".codex" / "skills" / "my_skill"
    p2 = tmp_path / ".grok" / "bundled" / "test"

    # Not tool managed paths
    p3 = tmp_path / ".config" / "test"
    p4 = tmp_path / "Projects" / "test"

    # Test path that isn't relative to HOME but contains matching string
    p5 = Path("/some/other/path/.codex/skills/test")

    assert hygiene_scan.is_tool_managed(p1) is True
    assert hygiene_scan.is_tool_managed(p2) is True
    assert hygiene_scan.is_tool_managed(p3) is False
    assert hygiene_scan.is_tool_managed(p4) is False
    assert hygiene_scan.is_tool_managed(p5) is True

def test_is_active_runtime_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(hygiene_scan, "HOME", tmp_path)

    # We need to recreate ACTIVE_CACHE_PATHS after monkeypatching HOME
    original_active_cache_paths = hygiene_scan.ACTIVE_CACHE_PATHS
    hygiene_scan.ACTIVE_CACHE_PATHS = {
        tmp_path / ".codex" / ".tmp",
        tmp_path / ".codex" / "backups",
        tmp_path / ".npm" / "_npx",
        tmp_path / ".opencode" / "node_modules",
    }

    try:
        assert hygiene_scan.is_active_runtime_cache(tmp_path / ".codex" / ".tmp") is True
        assert hygiene_scan.is_active_runtime_cache(tmp_path / ".codex" / "backups") is True
        assert hygiene_scan.is_active_runtime_cache(tmp_path / "Projects" / "test") is False
        assert hygiene_scan.is_active_runtime_cache(tmp_path / ".npm" / "_npx") is True
        assert hygiene_scan.is_active_runtime_cache(tmp_path / ".npm" / "cache") is False
    finally:
        hygiene_scan.ACTIVE_CACHE_PATHS = original_active_cache_paths

def test_is_app_owned_empty_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(hygiene_scan, "HOME", tmp_path)

    p1 = tmp_path / "Documents" / "superwhisper" / "recordings" / "empty1"
    p2 = tmp_path / "Documents" / "superwhisper" / "recordings" / "empty2"
    p3 = tmp_path / "Documents" / "other" / "empty"

    # Add an explicitly app owned empty dir
    p4 = tmp_path / "app" / "owned" / "dir"

    original_app_owned_empty_dirs = hygiene_scan.APP_OWNED_EMPTY_DIRS
    hygiene_scan.APP_OWNED_EMPTY_DIRS = {p4}

    try:
        assert hygiene_scan.is_app_owned_empty_dir(p1) is True
        assert hygiene_scan.is_app_owned_empty_dir(p2) is True
        assert hygiene_scan.is_app_owned_empty_dir(p3) is False
        assert hygiene_scan.is_app_owned_empty_dir(p4) is True
    finally:
        hygiene_scan.APP_OWNED_EMPTY_DIRS = original_app_owned_empty_dirs

def test_is_ignored_broken_link(tmp_path):
    prefix1 = tmp_path / "prefix1"
    prefix2 = tmp_path / "prefix2"

    original_ignored_broken_link_prefixes = hygiene_scan.IGNORED_BROKEN_LINK_PREFIXES
    hygiene_scan.IGNORED_BROKEN_LINK_PREFIXES = {prefix1, prefix2}

    try:
        # Path inside prefix1
        p1 = prefix1 / "some" / "broken" / "link"
        # Path inside prefix2
        p2 = prefix2 / "another" / "link"
        # Path not inside any ignored prefix
        p3 = tmp_path / "prefix3" / "link"

        assert hygiene_scan.is_ignored_broken_link(p1) is True
        assert hygiene_scan.is_ignored_broken_link(p2) is True
        assert hygiene_scan.is_ignored_broken_link(p3) is False
    finally:
        hygiene_scan.IGNORED_BROKEN_LINK_PREFIXES = original_ignored_broken_link_prefixes
