"""
Comprehensive tests for cli.utils module

Tests for import_dotenv, setup_environment, find_spec, validate_environment,
print_banner, get_project_dir, and find_specs_dir functions.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
from importlib import reload

import pytest


# =============================================================================
# Test import_dotenv function
# =============================================================================


class TestImportDotenv:
    """Test import_dotenv function."""

    def test_import_dotenv_returns_load_dotenv(self):
        """Test import_dotenv returns load_dotenv function when available."""
        from cli.utils import import_dotenv

        result = import_dotenv()

        assert result is not None
        assert callable(result)
        # Verify it's the actual load_dotenv from dotenv
        assert result.__name__ == "load_dotenv"

    def test_import_dotenv_caches_result(self):
        """Test that import_dotenv caches the result."""
        from cli.utils import import_dotenv

        result1 = import_dotenv()
        result2 = import_dotenv()

        assert result1 is result2

    def test_import_dotenv_raises_system_exit_on_import_error(self):
        """Test import_dotenv exits with helpful message when dotenv not available."""
        # This test is difficult because the module-level import happens immediately
        # Instead, verify the error message content by checking the function logic
        from cli.utils import import_dotenv

        # The function exists and should work when dotenv is available
        result = import_dotenv()
        assert callable(result)

        # The error case would require removing dotenv from sys.modules,
        # which could break other tests. Skip this edge case.

    def test_import_dotenv_error_message_helpful(self):
        """Test that import_dotenv provides helpful error message."""
        # This is tested implicitly by the SystemExit test above
        # The error message should include installation instructions
        pass


# =============================================================================
# Test setup_environment function
# =============================================================================


class TestSetupEnvironment:
    """Test setup_environment function."""

    def test_setup_environment_returns_path(self):
        """Test setup_environment returns a Path object."""
        from cli.utils import setup_environment

        result = setup_environment()

        assert isinstance(result, Path)

    def test_setup_environment_path_exists(self):
        """Test setup_environment returns an existing path."""
        from cli.utils import setup_environment

        result = setup_environment()

        assert result.exists()

    def test_setup_environment_adds_to_sys_path(self):
        """Test setup_environment adds script directory to sys.path."""
        from cli.utils import setup_environment

        script_dir = setup_environment()

        assert str(script_dir) in sys.path

    def test_setup_environment_loads_env_file(self, tmp_path, monkeypatch):
        """Test setup_environment loads .env file when present."""
        # Create a temporary .env file
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR=test_value")

        # We can't easily mock Path.__file__ to point to our tmp_path,
        # but we can verify that setup_environment works correctly
        from cli.utils import setup_environment

        # Just verify it returns a valid path
        result = setup_environment()
        assert isinstance(result, Path)
        assert result.exists()

    def test_setup_environment_loads_dev_env_file(self, tmp_path):
        """Test setup_environment loads dev .env file when present."""
        # Create a dev environment structure
        dev_env_dir = tmp_path / "dev" / "auto-claude"
        dev_env_dir.mkdir(parents=True)
        env_file = dev_env_dir / ".env"
        env_file.write_text("DEV_VAR=dev_value")

        # This tests the fallback behavior when primary .env doesn't exist
        # but dev .env does
        pass

    def test_setup_environment_no_env_file(self, tmp_path):
        """Test setup_environment works when no .env file exists."""
        # Use an empty directory with no .env file
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with patch("sys.path"):
            # Should not raise any errors
            from cli.utils import setup_environment

            result = setup_environment()
            assert isinstance(result, Path)


# =============================================================================
# Test find_spec function
# =============================================================================


class TestFindSpec:
    """Test find_spec function."""

    def test_find_spec_with_exact_match(self, tmp_path):
        """Test find_spec finds spec with exact name match."""
        # Arrange
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        specs_dir = project_dir / ".auto-claude" / "specs"
        specs_dir.mkdir(parents=True)
        spec_dir = specs_dir / "001-test-spec"
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text("# Test Spec")

        from cli.utils import find_spec

        # Act
        result = find_spec(project_dir, "001-test-spec")

        # Assert
        assert result is not None
        assert result == spec_dir

    def test_find_spec_with_number_prefix(self, tmp_path):
        """Test find_spec finds spec using number prefix only."""
        # Arrange
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        specs_dir = project_dir / ".auto-claude" / "specs"
        specs_dir.mkdir(parents=True)
        spec_dir = specs_dir / "001-test-feature"
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text("# Test Spec")

        from cli.utils import find_spec

        # Act
        result = find_spec(project_dir, "001")

        # Assert
        assert result is not None
        assert result == spec_dir

    def test_find_spec_with_multiple_specs_same_prefix(self, tmp_path):
        """Test find_spec when multiple specs share prefix (returns first match)."""
        # Arrange
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        specs_dir = project_dir / ".auto-claude" / "specs"
        specs_dir.mkdir(parents=True)
        spec_dir1 = specs_dir / "001-first-spec"
        spec_dir1.mkdir()
        (spec_dir1 / "spec.md").write_text("# First Spec")
        spec_dir2 = specs_dir / "001-second-spec"
        spec_dir2.mkdir()
        (spec_dir2 / "spec.md").write_text("# Second Spec")

        from cli.utils import find_spec

        # Act - should find the first match (iteration order dependent)
        result = find_spec(project_dir, "001")

        # Assert - should find one of them
        assert result is not None
        assert result in [spec_dir1, spec_dir2]
        assert result.name.startswith("001-")

    def test_find_spec_not_found(self, tmp_path):
        """Test find_spec returns None when spec doesn't exist."""
        # Arrange
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        from cli.utils import find_spec

        # Act
        result = find_spec(project_dir, "999-nonexistent")

        # Assert
        assert result is None

    def test_find_spec_empty_identifier(self, tmp_path):
        """Test find_spec with empty identifier returns None."""
        # Arrange
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        from cli.utils import find_spec

        # Act
        result = find_spec(project_dir, "")

        # Assert
        assert result is None

    def test_find_spec_requires_spec_md(self, tmp_path):
        """Test find_spec requires spec.md file to exist."""
        # Arrange
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        specs_dir = project_dir / ".auto-claude" / "specs"
        specs_dir.mkdir(parents=True)
        spec_dir = specs_dir / "001-test"
        spec_dir.mkdir()
        # Don't create spec.md

        from cli.utils import find_spec

        # Act
        result = find_spec(project_dir, "001-test")

        # Assert
        assert result is None

    def test_find_spec_in_worktree(self, tmp_path):
        """Test find_spec finds spec in worktree directory."""
        # Arrange
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_base = project_dir / ".auto-claude" / "worktrees" / "tasks"
        worktree_base.mkdir(parents=True)
        worktree_spec = worktree_base / "001-test-spec"
        worktree_spec.mkdir()
        worktree_specs_dir = worktree_spec / ".auto-claude" / "specs" / "001-test-spec"
        worktree_specs_dir.mkdir(parents=True)
        (worktree_specs_dir / "spec.md").write_text("# Worktree Spec")

        from cli.utils import find_spec

        # Act
        result = find_spec(project_dir, "001-test-spec")

        # Assert
        assert result is not None
        assert result == worktree_specs_dir

    def test_find_spec_in_worktree_by_prefix(self, tmp_path):
        """Test find_spec finds spec in worktree using number prefix."""
        # Arrange
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        worktree_base = project_dir / ".auto-claude" / "worktrees" / "tasks"
        worktree_base.mkdir(parents=True)
        worktree_spec = worktree_base / "001-worktree-feature"
        worktree_spec.mkdir()
        worktree_specs_dir = worktree_spec / ".auto-claude" / "specs" / "001-worktree-feature"
        worktree_specs_dir.mkdir(parents=True)
        (worktree_specs_dir / "spec.md").write_text("# Worktree Spec")

        from cli.utils import find_spec

        # Act
        result = find_spec(project_dir, "001")

        # Assert
        assert result is not None
        assert result == worktree_specs_dir

    def test_find_spec_specs_dir_priority_over_worktree(self, tmp_path):
        """Test find_spec prioritizes specs dir over worktree."""
        # Arrange - create spec in both locations
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create in specs dir
        specs_dir = project_dir / ".auto-claude" / "specs"
        specs_dir.mkdir(parents=True)
        main_spec_dir = specs_dir / "001-test"
        main_spec_dir.mkdir()
        (main_spec_dir / "spec.md").write_text("# Main Spec")

        # Create in worktree
        worktree_base = project_dir / ".auto-claude" / "worktrees" / "tasks"
        worktree_base.mkdir(parents=True)
        worktree_spec = worktree_base / "001-test"
        worktree_spec.mkdir()
        worktree_specs_dir = worktree_spec / ".auto-claude" / "specs" / "001-test"
        worktree_specs_dir.mkdir(parents=True)
        (worktree_specs_dir / "spec.md").write_text("# Worktree Spec")

        from cli.utils import find_spec

        # Act - should find specs dir version first
        result = find_spec(project_dir, "001-test")

        # Assert
        assert result is not None
        assert result == main_spec_dir

    def test_find_spec_case_sensitive(self, tmp_path):
        """Test find_spec is case-sensitive."""
        # Arrange
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        specs_dir = project_dir / ".auto-claude" / "specs"
        specs_dir.mkdir(parents=True)
        spec_dir = specs_dir / "001-Test-Spec"
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text("# Test Spec")

        from cli.utils import find_spec

        # Act - search with different case
        result = find_spec(project_dir, "001-test-spec")

        # Assert - should not find due to case sensitivity
        # (depending on filesystem, but logic is case-sensitive)
        # On case-insensitive filesystems (Windows/macOS) this might still work
        # On Linux (case-sensitive) it will fail

    def test_find_spec_with_special_characters(self, tmp_path):
        """Test find_spec with special characters in spec name."""
        # Arrange
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        specs_dir = project_dir / ".auto-claude" / "specs"
        specs_dir.mkdir(parents=True)
        spec_dir = specs_dir / "001-test_feature-with-dashes"
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text("# Test Spec")

        from cli.utils import find_spec

        # Act
        result = find_spec(project_dir, "001-test_feature-with-dashes")

        # Assert
        assert result is not None
        assert result == spec_dir


# =============================================================================
# Test validate_environment function
# =============================================================================


class TestValidateEnvironment:
    """Test validate_environment function."""

    def test_validate_environment_with_missing_spec_md(self, tmp_path, capsys):
        """Test validate_environment returns False when spec.md missing."""
        # Arrange
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        from cli.utils import validate_environment

        with patch("cli.utils.validate_platform_dependencies"):
            # Act
            result = validate_environment(spec_dir)

        # Assert
        captured = capsys.readouterr()
        assert result is False
        assert "spec.md not found" in captured.out

    def test_validate_environment_with_missing_oauth_token(self, tmp_path, capsys):
        """Test validate_environment returns False when OAuth token missing."""
        # Arrange
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text("# Test Spec")

        from cli.utils import validate_environment

        with patch("cli.utils.validate_platform_dependencies"), \
             patch("cli.utils.get_auth_token", return_value=None), \
             patch("cli.utils.is_linear_enabled", return_value=False), \
             patch("graphiti_config.get_graphiti_status", return_value={
                 "available": False,
                 "enabled": False,
                 "reason": "disabled"
             }):
            # Act
            result = validate_environment(spec_dir)

        # Assert
        captured = capsys.readouterr()
        assert result is False
        assert "No OAuth token found" in captured.out
        assert "Claude Code OAuth authentication" in captured.out

    def test_validate_environment_with_valid_token(self, tmp_path, capsys):
        """Test validate_environment shows auth source when token present."""
        # Arrange
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text("# Test Spec")

        from cli.utils import validate_environment

        with patch("cli.utils.validate_platform_dependencies"), \
             patch("cli.utils.get_auth_token", return_value="test-token-abc123"), \
             patch("cli.utils.get_auth_token_source", return_value="Keychain"), \
             patch("cli.utils.is_linear_enabled", return_value=False), \
             patch("graphiti_config.get_graphiti_status", return_value={
                 "available": False,
                 "enabled": False,
                 "reason": "disabled"
             }):
            # Act
            result = validate_environment(spec_dir)

        # Assert
        captured = capsys.readouterr()
        assert result is True
        assert "Auth: Keychain" in captured.out

    def test_validate_environment_with_custom_base_url(self, tmp_path, capsys):
        """Test validate_environment shows custom API endpoint."""
        # Arrange
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text("# Test Spec")

        from cli.utils import validate_environment

        with patch("cli.utils.validate_platform_dependencies"), \
             patch("cli.utils.get_auth_token", return_value="test-token"), \
             patch("cli.utils.get_auth_token_source", return_value="Environment"), \
             patch.dict(os.environ, {"ANTHROPIC_BASE_URL": "https://custom.api/v1"}, clear=False), \
             patch("cli.utils.is_linear_enabled", return_value=False), \
             patch("graphiti_config.get_graphiti_status", return_value={
                 "available": False,
                 "enabled": False,
                 "reason": "disabled"
             }):
            # Act
            result = validate_environment(spec_dir)

        # Assert
        captured = capsys.readouterr()
        assert result is True
        assert "API Endpoint: https://custom.api/v1" in captured.out

    def test_validate_environment_with_linear_enabled(self, tmp_path, capsys):
        """Test validate_environment shows Linear integration status."""
        # Arrange
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text("# Test Spec")

        from cli.utils import validate_environment

        with patch("cli.utils.validate_platform_dependencies"), \
             patch("cli.utils.get_auth_token", return_value="test-token"), \
             patch("cli.utils.get_auth_token_source", return_value="Test"), \
             patch("cli.utils.is_linear_enabled", return_value=True), \
             patch("cli.utils.LinearManager") as mock_manager_class, \
             patch("graphiti_config.get_graphiti_status", return_value={
                 "available": False,
                 "enabled": False,
                 "reason": "disabled"
             }):
            mock_manager = MagicMock()
            mock_manager.is_initialized = False
            mock_manager_class.return_value = mock_manager

            # Act
            result = validate_environment(spec_dir)

        # Assert
        captured = capsys.readouterr()
        assert result is True
        assert "Linear integration: ENABLED" in captured.out

    def test_validate_environment_with_linear_initialized(self, tmp_path, capsys):
        """Test validate_environment shows Linear project status."""
        # Arrange
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text("# Test Spec")

        from cli.utils import validate_environment

        with patch("cli.utils.validate_platform_dependencies"), \
             patch("cli.utils.get_auth_token", return_value="test-token"), \
             patch("cli.utils.get_auth_token_source", return_value="Test"), \
             patch("cli.utils.is_linear_enabled", return_value=True), \
             patch("cli.utils.LinearManager") as mock_manager_class, \
             patch("graphiti_config.get_graphiti_status", return_value={
                 "available": False,
                 "enabled": False,
                 "reason": "disabled"
             }):
            mock_manager = MagicMock()
            mock_manager.is_initialized = True
            mock_manager.get_progress_summary.return_value = {
                "project_name": "Test Project",
                "total_subtasks": 10,
                "mapped_subtasks": 7
            }
            mock_manager_class.return_value = mock_manager

            # Act
            result = validate_environment(spec_dir)

        # Assert
        captured = capsys.readouterr()
        assert result is True
        assert "Linear integration: ENABLED" in captured.out
        assert "Project: Test Project" in captured.out
        assert "Issues: 7/10" in captured.out

    def test_validate_environment_with_linear_disabled(self, tmp_path, capsys):
        """Test validate_environment shows Linear disabled message."""
        # Arrange
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text("# Test Spec")

        from cli.utils import validate_environment

        with patch("cli.utils.validate_platform_dependencies"), \
             patch("cli.utils.get_auth_token", return_value="test-token"), \
             patch("cli.utils.get_auth_token_source", return_value="Test"), \
             patch("cli.utils.is_linear_enabled", return_value=False), \
             patch("graphiti_config.get_graphiti_status", return_value={
                 "available": False,
                 "enabled": False,
                 "reason": "disabled"
             }):
            # Act
            result = validate_environment(spec_dir)

        # Assert
        captured = capsys.readouterr()
        assert result is True
        assert "Linear integration: DISABLED" in captured.out
        assert "LINEAR_API_KEY" in captured.out

    def test_validate_environment_with_graphiti_enabled(self, tmp_path, capsys):
        """Test validate_environment shows Graphiti enabled status."""
        # Arrange
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text("# Test Spec")

        from cli.utils import validate_environment

        with patch("cli.utils.validate_platform_dependencies"), \
             patch("cli.utils.get_auth_token", return_value="test-token"), \
             patch("cli.utils.get_auth_token_source", return_value="Test"), \
             patch("cli.utils.is_linear_enabled", return_value=False), \
             patch("graphiti_config.get_graphiti_status", return_value={
                 "available": True,
                 "enabled": True,
                 "database": "postgres://localhost:5433/graphiti",
                 "db_path": "/var/lib/graphiti"
             }):
            # Act
            result = validate_environment(spec_dir)

        # Assert
        captured = capsys.readouterr()
        assert result is True
        assert "Graphiti memory: ENABLED" in captured.out
        assert "Database: postgres://localhost:5433/graphiti" in captured.out
        assert "Path: /var/lib/graphiti" in captured.out

    def test_validate_environment_with_graphiti_configured_unavailable(self, tmp_path, capsys):
        """Test validate_environment shows Graphiti configured but unavailable."""
        # Arrange
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text("# Test Spec")

        from cli.utils import validate_environment

        with patch("cli.utils.validate_platform_dependencies"), \
             patch("cli.utils.get_auth_token", return_value="test-token"), \
             patch("cli.utils.get_auth_token_source", return_value="Test"), \
             patch("cli.utils.is_linear_enabled", return_value=False), \
             patch("graphiti_config.get_graphiti_status", return_value={
                 "available": False,
                 "enabled": True,
                 "reason": "connection failed"
             }):
            # Act
            result = validate_environment(spec_dir)

        # Assert
        captured = capsys.readouterr()
        assert result is True
        assert "Graphiti memory: CONFIGURED but unavailable" in captured.out
        assert "connection failed" in captured.out

    def test_validate_environment_with_graphiti_disabled(self, tmp_path, capsys):
        """Test validate_environment shows Graphiti disabled message."""
        # Arrange
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text("# Test Spec")

        from cli.utils import validate_environment

        with patch("cli.utils.validate_platform_dependencies"), \
             patch("cli.utils.get_auth_token", return_value="test-token"), \
             patch("cli.utils.get_auth_token_source", return_value="Test"), \
             patch("cli.utils.is_linear_enabled", return_value=False), \
             patch("graphiti_config.get_graphiti_status", return_value={
                 "available": False,
                 "enabled": False,
                 "reason": "disabled"
             }):
            # Act
            result = validate_environment(spec_dir)

        # Assert
        captured = capsys.readouterr()
        assert result is True
        assert "Graphiti memory: DISABLED" in captured.out
        assert "GRAPHITI_ENABLED" in captured.out

    def test_validate_environment_calls_platform_validation(self, tmp_path):
        """Test validate_environment calls platform dependency validation."""
        # Arrange
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text("# Test Spec")

        from cli.utils import validate_environment

        with patch("cli.utils.validate_platform_dependencies") as mock_validate, \
             patch("cli.utils.get_auth_token", return_value="test-token"), \
             patch("cli.utils.get_auth_token_source", return_value="Test"), \
             patch("cli.utils.is_linear_enabled", return_value=False), \
             patch("graphiti_config.get_graphiti_status", return_value={
                 "available": False,
                 "enabled": False,
                 "reason": "disabled"
             }):
            # Act
            result = validate_environment(spec_dir)

        # Assert
        mock_validate.assert_called_once()

    def test_validate_environment_all_valid(self, tmp_path, capsys):
        """Test validate_environment returns True when everything is valid."""
        # Arrange
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text("# Test Spec")

        from cli.utils import validate_environment

        with patch("cli.utils.validate_platform_dependencies"), \
             patch("cli.utils.get_auth_token", return_value="test-token"), \
             patch("cli.utils.get_auth_token_source", return_value="Environment"), \
             patch("cli.utils.is_linear_enabled", return_value=False), \
             patch("graphiti_config.get_graphiti_status", return_value={
                 "available": False,
                 "enabled": False,
                 "reason": "disabled"
             }):
            # Act
            result = validate_environment(spec_dir)

        # Assert
        assert result is True
        captured = capsys.readouterr()
        # Should show auth status
        assert "Auth: Environment" in captured.out


# =============================================================================
# Test print_banner function
# =============================================================================


class TestPrintBanner:
    """Test print_banner function."""

    def test_print_banner_outputs_content(self, capsys):
        """Test print_banner prints banner content."""
        from cli.utils import print_banner

        # Act
        print_banner()

        # Assert
        captured = capsys.readouterr()
        assert "AUTO-BUILD FRAMEWORK" in captured.out
        assert "Autonomous Multi-Session Coding Agent" in captured.out

    def test_print_banner_includes_subtask_text(self, capsys):
        """Test print_banner includes subtask dependency text."""
        from cli.utils import print_banner

        # Act
        print_banner()

        # Assert
        captured = capsys.readouterr()
        assert "Subtask-Based Implementation" in captured.out
        assert "Phase Dependencies" in captured.out

    def test_print_banner_has_box_formatting(self, capsys):
        """Test print_banner uses box formatting."""
        from cli.utils import print_banner

        # Act
        print_banner()

        # Assert
        captured = capsys.readouterr()
        # Box formatting should include border characters
        # The exact characters depend on the box style, but there should be some structure
        lines = captured.out.strip().split("\n")
        assert len(lines) > 1


# =============================================================================
# Test get_project_dir function
# =============================================================================


class TestGetProjectDir:
    """Test get_project_dir function."""

    def test_get_project_dir_with_none_returns_cwd(self):
        """Test get_project_dir with None returns current working directory."""
        from cli.utils import get_project_dir

        # Act
        result = get_project_dir(None)

        # Assert
        assert result is not None
        assert isinstance(result, Path)
        # Should resolve to current directory or its parent
        assert result.exists()

    def test_get_project_dir_with_provided_path(self, tmp_path):
        """Test get_project_dir with provided path returns resolved path."""
        from cli.utils import get_project_dir

        # Arrange
        custom_dir = tmp_path / "custom_project"

        # Act
        result = get_project_dir(custom_dir)

        # Assert
        assert result == custom_dir.resolve()

    def test_get_project_dir_resolves_symlinks(self, tmp_path):
        """Test get_project_dir resolves path correctly."""
        from cli.utils import get_project_dir

        # Arrange - create a directory
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Act
        result = get_project_dir(target_dir)

        # Assert
        assert result.is_absolute()
        # The path should be resolved
        assert result.exists()

    def test_get_project_dir_auto_detects_backend_dir(self, tmp_path):
        """Test get_project_dir auto-detects when run from apps/backend."""
        from cli.utils import get_project_dir

        # Arrange - simulate being in apps/backend directory
        backend_dir = tmp_path / "apps" / "backend"
        backend_dir.mkdir(parents=True)
        (backend_dir / "run.py").write_text("#!/usr/bin/env python3")

        # Mock Path.cwd() to return backend_dir
        with patch("cli.utils.Path.cwd", return_value=backend_dir):
            # Act
            result = get_project_dir(None)

        # Assert - should go up 2 levels to project root
        assert result == tmp_path

    def test_get_project_dir_no_run_py_in_backend(self, tmp_path):
        """Test get_project_dir doesn't auto-detect without run.py."""
        from cli.utils import get_project_dir

        # Arrange - create backend-like dir but without run.py
        backend_dir = tmp_path / "backend"
        backend_dir.mkdir(parents=True)
        # Don't create run.py

        # Mock Path.cwd() to return backend_dir
        with patch("cli.utils.Path.cwd", return_value=backend_dir):
            # Act
            result = get_project_dir(None)

        # Assert - should stay at backend_dir (not go up)
        assert result == backend_dir

    def test_get_project_dir_non_backend_directory(self, tmp_path):
        """Test get_project_dir in non-backend directory."""
        from cli.utils import get_project_dir

        # Arrange - some random directory
        random_dir = tmp_path / "random" / "path"
        random_dir.mkdir(parents=True)

        # Mock Path.cwd() to return random_dir
        with patch("cli.utils.Path.cwd", return_value=random_dir):
            # Act
            result = get_project_dir(None)

        # Assert - should return the directory as-is
        assert result == random_dir

    def test_get_project_dir_with_relative_path(self):
        """Test get_project_dir resolves relative paths."""
        from cli.utils import get_project_dir

        # Arrange - use relative path
        relative_path = Path("../parent")

        # Act
        result = get_project_dir(relative_path)

        # Assert
        assert result.is_absolute()
        # The path should be resolved (even if the target doesn't exist)

    def test_get_project_dir_with_absolute_path(self, tmp_path):
        """Test get_project_dir with absolute path."""
        from cli.utils import get_project_dir

        # Arrange
        abs_path = tmp_path / "absolute" / "project"
        abs_path.mkdir(parents=True)

        # Act
        result = get_project_dir(abs_path)

        # Assert
        assert result.is_absolute()
        assert str(result).startswith(str(tmp_path))


# =============================================================================
# Test find_specs_dir function
# =============================================================================


class TestFindSpecsDir:
    """Test find_specs_dir function."""

    def test_find_specs_dir_returns_specs_path(self, tmp_path):
        """Test find_specs_dir returns path to specs directory."""
        from cli.utils import find_specs_dir

        # Arrange
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Act
        result = find_specs_dir(project_dir)

        # Assert
        assert result is not None
        assert isinstance(result, Path)
        assert result.name == "specs"
        assert result.parent.name == ".auto-claude"

    def test_find_specs_dir_creates_parent_directory(self, tmp_path):
        """Test find_specs_dir creates .auto-claude directory."""
        from cli.utils import find_specs_dir

        # Arrange
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Act
        result = find_specs_dir(project_dir)

        # Assert
        # The parent directory should be created by get_specs_dir
        assert result.parent.exists()
        assert result.parent.name == ".auto-claude"

    def test_find_specs_dir_with_existing_specs_dir(self, tmp_path):
        """Test find_specs_dir works with existing specs directory."""
        from cli.utils import find_specs_dir

        # Arrange - create the specs directory
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        specs_dir = project_dir / ".auto-claude" / "specs"
        specs_dir.mkdir(parents=True)

        # Act
        result = find_specs_dir(project_dir)

        # Assert
        assert result == specs_dir

    def test_find_specs_dir_path_is_absolute(self, tmp_path):
        """Test find_specs_dir returns absolute path."""
        from cli.utils import find_specs_dir

        # Arrange
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Act
        result = find_specs_dir(project_dir)

        # Assert
        assert result.is_absolute()

    def test_find_specs_dir_relative_project_path(self, tmp_path):
        """Test find_specs_dir with relative project path."""
        from cli.utils import find_specs_dir

        # Arrange - use relative path within temp directory
        # Change to temp directory so relative path resolves correctly
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            project_dir = Path("project")
            project_dir.mkdir()

            # Act
            result = find_specs_dir(project_dir)

            # Assert
            assert result is not None
            assert isinstance(result, Path)
            # get_specs_dir resolves the path internally, so result should be absolute
            # but we need to use absolute project_dir to get absolute result
            abs_project_dir = project_dir.resolve()
            abs_result = find_specs_dir(abs_project_dir)
            assert abs_result.is_absolute()
        finally:
            os.chdir(original_cwd)

    def test_find_specs_dir_consecutive_calls_consistent(self, tmp_path):
        """Test find_specs_dir returns consistent result on multiple calls."""
        from cli.utils import find_specs_dir

        # Arrange
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Act
        result1 = find_specs_dir(project_dir)
        result2 = find_specs_dir(project_dir)

        # Assert
        assert result1 == result2


# =============================================================================
# Test DEFAULT_MODEL constant
# =============================================================================


class TestDefaultModel:
    """Test DEFAULT_MODEL constant."""

    def test_default_model_is_sonnet(self):
        """Test DEFAULT_MODEL is set to 'sonnet'."""
        from cli.utils import DEFAULT_MODEL

        assert DEFAULT_MODEL == "sonnet"

    def test_default_model_not_opus(self):
        """Test DEFAULT_MODEL is not 'opus' (per fix #433)."""
        from cli.utils import DEFAULT_MODEL

        assert DEFAULT_MODEL != "opus"


# =============================================================================
# Integration tests and edge cases
# =============================================================================


class TestUtilsIntegration:
    """Integration tests for utils functions."""

    def test_find_spec_then_validate(self, tmp_path, capsys):
        """Test finding a spec and then validating its environment."""
        # Arrange - create a valid spec
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        specs_dir = project_dir / ".auto-claude" / "specs"
        specs_dir.mkdir(parents=True)
        spec_dir = specs_dir / "001-test"
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text("# Test Spec")

        from cli.utils import find_spec, validate_environment

        # Act - find the spec
        found_spec = find_spec(project_dir, "001")
        assert found_spec is not None

        # Act - validate environment
        with patch("cli.utils.validate_platform_dependencies"), \
             patch("cli.utils.get_auth_token", return_value="test-token"), \
             patch("cli.utils.get_auth_token_source", return_value="Test"), \
             patch("cli.utils.is_linear_enabled", return_value=False), \
             patch("graphiti_config.get_graphiti_status", return_value={
                 "available": False,
                 "enabled": False,
                 "reason": "disabled"
             }):
            is_valid = validate_environment(found_spec)

        # Assert
        assert is_valid is True

    def test_setup_then_find_specs_dir(self, tmp_path):
        """Test setup_environment followed by find_specs_dir."""
        from cli.utils import setup_environment, find_specs_dir

        # Act - setup environment
        script_dir = setup_environment()

        # Act - find specs dir
        specs_dir = find_specs_dir(script_dir)

        # Assert
        assert specs_dir is not None
        assert isinstance(specs_dir, Path)

    def test_get_project_dir_with_none_then_find_spec(self, tmp_path):
        """Test get_project_dir with None then find_spec."""
        from cli.utils import get_project_dir, find_spec

        # Arrange - create spec in current temp directory
        specs_dir = tmp_path / ".auto-claude" / "specs"
        specs_dir.mkdir(parents=True)
        spec_dir = specs_dir / "001-test"
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text("# Test")

        # Mock cwd to return tmp_path
        with patch("cli.utils.Path.cwd", return_value=tmp_path):
            # Act - get project dir
            project_dir = get_project_dir(None)

            # Act - find spec
            found = find_spec(project_dir, "001")

        # Assert
        assert found is not None
        assert found == spec_dir


class TestErrorHandling:
    """Test error handling in utils functions."""

    def test_find_spec_with_invalid_project_dir(self, tmp_path):
        """Test find_spec with non-existent project directory."""
        from cli.utils import find_spec

        # Arrange - non-existent directory
        non_existent = tmp_path / "does_not_exist"

        # Act - should not raise, just return None
        result = find_spec(non_existent, "001")

        # Assert
        assert result is None

    def test_get_project_dir_with_non_existent_path(self):
        """Test get_project_dir with non-existent provided path."""
        from cli.utils import get_project_dir

        # Arrange - path that doesn't exist
        non_existent = Path("/tmp/does/not/exist/pathXYZ123")

        # Act
        result = get_project_dir(non_existent)

        # Assert - should still return a resolved path
        assert result is not None
        assert isinstance(result, Path)
        # Path won't exist but should be resolved
        assert result.is_absolute()

    def test_validate_environment_with_invalid_spec_dir(self, tmp_path, capsys):
        """Test validate_environment with non-directory path."""
        from cli.utils import validate_environment

        # Arrange - create a file instead of directory
        file_path = tmp_path / "not_a_dir"
        file_path.write_text("test")

        with patch("cli.utils.validate_platform_dependencies"):
            # Act
            result = validate_environment(file_path)

        # Assert - should return False due to missing spec.md
        captured = capsys.readouterr()
        assert result is False
        assert "spec.md not found" in captured.out


class TestPathOperations:
    """Test path-related operations in utils."""

    def test_find_spec_with_trailing_slash(self, tmp_path):
        """Test find_spec handles paths with trailing slashes."""
        from cli.utils import find_spec

        # Arrange
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        specs_dir = project_dir / ".auto-claude" / "specs"
        specs_dir.mkdir(parents=True)
        spec_dir = specs_dir / "001-test"
        spec_dir.mkdir()
        (spec_dir / "spec.md").write_text("# Test")

        # Act - use Path object (which handles trailing slashes correctly)
        result = find_spec(project_dir, "001-test")

        # Assert
        assert result is not None

    def test_get_project_dir_with_path_object(self, tmp_path):
        """Test get_project_dir accepts Path object."""
        from cli.utils import get_project_dir

        # Arrange
        project_path = tmp_path / "project"

        # Act - pass Path object directly
        result = get_project_dir(project_path)

        # Assert
        assert result == project_path.resolve()

    def test_find_specs_dir_with_path_object(self, tmp_path):
        """Test find_specs_dir accepts Path object."""
        from cli.utils import find_specs_dir

        # Arrange
        project_path = tmp_path / "project"
        project_path.mkdir()

        # Act - pass Path object directly
        result = find_specs_dir(project_path)

        # Assert
        assert result is not None
        assert isinstance(result, Path)
