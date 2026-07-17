"""Tests for action_entrypoint._safe_resolve path-injection hardening.

These are security-critical: regressions here would re-open the path
injection vulnerability flagged by SonarCloud (issue #11).
"""

import os
import sys
from pathlib import Path

import pytest

# action_entrypoint.py lives at the repo root (not under src/qwed_ucp).
# Add it to sys.path so the module is importable.
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from action_entrypoint import _safe_resolve  # noqa: E402


class TestSafeResolveInSandbox:
    """Valid paths inside the sandbox must be accepted."""

    def test_valid_relative_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
        f = tmp_path / "txn.json"
        f.write_text('{"currency": "USD", "totals": []}')
        resolved = _safe_resolve("txn.json")
        assert resolved == str(f.resolve())

    def test_valid_absolute_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
        f = tmp_path / "txn.json"
        f.write_text('{"currency": "USD", "totals": []}')
        resolved = _safe_resolve(str(f))
        assert resolved == str(f.resolve())

    def test_valid_nested_relative_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
        sub = tmp_path / "samples"
        sub.mkdir()
        f = sub / "txn.json"
        f.write_text("{}")
        resolved = _safe_resolve("samples/txn.json")
        assert resolved == str(f.resolve())

    def test_falls_back_to_cwd_without_env(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GITHUB_WORKSPACE", raising=False)
        monkeypatch.chdir(tmp_path)
        f = tmp_path / "txn.json"
        f.write_text("{}")
        resolved = _safe_resolve("txn.json")
        assert resolved == str(f.resolve())


class TestSafeResolveRejectsTraversal:
    """Path traversal attempts must be rejected before any file access."""

    def test_parent_traversal_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
        with pytest.raises(ValueError, match="outside the allowed sandbox"):
            _safe_resolve("../../etc/passwd")

    def test_absolute_outside_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
        with pytest.raises(ValueError, match="outside the allowed sandbox"):
            _safe_resolve(os.path.abspath("/etc/passwd"))

    def test_symlink_escape_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
        outside = tmp_path.parent / "outside_target.json"
        outside.write_text("{}", encoding="utf-8")
        link = tmp_path / "escape.json"
        try:
            os.symlink(str(outside), link)
        except OSError:
            pytest.skip("symlinks not supported on this platform")
        with pytest.raises(ValueError, match="outside the allowed sandbox"):
            _safe_resolve("escape.json")


class TestSafeResolvePartialPathTraversal:
    """The /foo vs /foo-evil prefix-confusion pitfall must not regress."""

    def test_sibling_directory_with_prefix_not_matched(self, tmp_path, monkeypatch):
        # Create two sibling dirs where one name is a prefix of the other.
        # Without the trailing-sep guard, /base would match /base-eviltwin.
        base = tmp_path / "base"
        evil = tmp_path / "base-eviltwin"
        base.mkdir()
        evil.mkdir()
        (evil / "secret.json").write_text("{}", encoding="utf-8")
        monkeypatch.setenv("GITHUB_WORKSPACE", str(base))
        # Construct absolute path to evil sibling — must not match base prefix.
        with pytest.raises(ValueError, match="outside the allowed sandbox"):
            _safe_resolve(str(evil / "secret.json"))
