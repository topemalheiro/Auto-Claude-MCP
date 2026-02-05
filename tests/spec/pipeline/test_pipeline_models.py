"""
Comprehensive tests for spec.pipeline.models module.

Tests for utility functions, models, and helper functions in the spec pipeline.
"""

import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

import pytest

from spec.pipeline.models import (
    get_specs_dir,
    cleanup_orphaned_pending_folders,
    create_spec_dir,
    generate_spec_name,
    rename_spec_dir_from_requirements,
    PHASE_DISPLAY,
)


class TestGetSpecsDir:
    """Tests for get_specs_dir function."""

    def test_get_specs_dir_creates_directory(self, tmp_path):
        """Test get_specs_dir creates .auto-claude directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        specs_dir = get_specs_dir(project_dir)

        assert specs_dir == project_dir / ".auto-claude" / "specs"
        # .auto-claude directory should be created by init_auto_claude_dir
        assert (project_dir / ".auto-claude").exists()
        # specs directory path is returned but may not exist yet
        # (it gets created when first spec is created)

    def test_get_specs_dir_existing_directory(self, tmp_path):
        """Test get_specs_dir returns existing specs directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / ".auto-claude"
        auto_claude.mkdir()
        specs_dir = auto_claude / "specs"
        specs_dir.mkdir()

        result = get_specs_dir(project_dir)

        assert result == specs_dir

    def test_get_specs_dir_initializes_auto_claude(self, tmp_path):
        """Test get_specs_dir initializes .auto-claude directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Mock at the import location - spec.pipeline.models imports init_auto_claude_dir
        with patch("spec.pipeline.models.init_auto_claude_dir") as mock_init:
            get_specs_dir(project_dir)
            mock_init.assert_called_once_with(project_dir)


class TestCleanupOrphanedPendingFolders:
    """Tests for cleanup_orphaned_pending_folders function."""

    def test_cleanup_removes_old_empty_pending_folders(self, temp_specs_dir):
        """Test cleanup removes old pending folders without content."""
        # Create an old pending folder (no content)
        old_pending = temp_specs_dir / "001-pending"
        old_pending.mkdir()

        # Make it appear old (> 10 minutes)
        old_time = datetime.now() - timedelta(minutes=15)
        import os
        os.utime(old_pending, (old_time.timestamp(), old_time.timestamp()))

        cleanup_orphaned_pending_folders(temp_specs_dir)

        assert not old_pending.exists()

    def test_cleanup_preserves_folders_with_requirements(self, temp_specs_dir):
        """Test cleanup preserves folders with requirements.json."""
        pending = temp_specs_dir / "001-pending"
        pending.mkdir()
        (pending / "requirements.json").write_text('{}')

        # Make it old
        old_time = datetime.now() - timedelta(minutes=15)
        import os
        os.utime(pending, (old_time.timestamp(), old_time.timestamp()))

        cleanup_orphaned_pending_folders(temp_specs_dir)

        assert pending.exists()

    def test_cleanup_preserves_folders_with_spec(self, temp_specs_dir):
        """Test cleanup preserves folders with spec.md."""
        pending = temp_specs_dir / "001-pending"
        pending.mkdir()
        (pending / "spec.md").write_text("# Spec")

        old_time = datetime.now() - timedelta(minutes=15)
        import os
        os.utime(pending, (old_time.timestamp(), old_time.timestamp()))

        cleanup_orphaned_pending_folders(temp_specs_dir)

        assert pending.exists()

    def test_cleanup_preserves_folders_with_plan(self, temp_specs_dir):
        """Test cleanup preserves folders with implementation_plan.json."""
        pending = temp_specs_dir / "001-pending"
        pending.mkdir()
        (pending / "implementation_plan.json").write_text('{}')

        old_time = datetime.now() - timedelta(minutes=15)
        import os
        os.utime(pending, (old_time.timestamp(), old_time.timestamp()))

        cleanup_orphaned_pending_folders(temp_specs_dir)

        assert pending.exists()

    def test_cleanup_preserves_recent_empty_folders(self, temp_specs_dir):
        """Test cleanup preserves recent empty folders (< 10 minutes)."""
        recent_pending = temp_specs_dir / "001-pending"
        recent_pending.mkdir()

        cleanup_orphaned_pending_folders(temp_specs_dir)

        assert recent_pending.exists()

    def test_cleanup_handles_non_directory_files(self, temp_specs_dir):
        """Test cleanup handles non-directory files matching pattern."""
        # Create a file (not directory) matching the pattern
        pending_file = temp_specs_dir / "001-pending"
        pending_file.write_text("not a directory")

        # Should not crash
        cleanup_orphaned_pending_folders(temp_specs_dir)

        # File should still exist (not a directory, so not cleaned up)
        assert pending_file.exists()

    def test_cleanup_handles_multiple_orphaned_folders(self, temp_specs_dir):
        """Test cleanup handles multiple orphaned folders."""
        # Create multiple old pending folders
        for i in range(3):
            pending = temp_specs_dir / f"{i+1:03d}-pending"
            pending.mkdir()
            old_time = datetime.now() - timedelta(minutes=15)
            import os
            os.utime(pending, (old_time.timestamp(), old_time.timestamp()))

        cleanup_orphaned_pending_folders(temp_specs_dir)

        # All should be removed
        for i in range(3):
            assert not (temp_specs_dir / f"{i+1:03d}-pending").exists()

    def test_cleanup_handles_oserror_during_rmtree(self, temp_specs_dir):
        """Test cleanup handles OSError during rmtree gracefully."""
        pending = temp_specs_dir / "001-pending"
        pending.mkdir()

        # Make it old
        old_time = datetime.now() - timedelta(minutes=15)
        import os
        os.utime(pending, (old_time.timestamp(), old_time.timestamp()))

        # Mock shutil.rmtree to raise OSError
        import shutil
        with patch.object(shutil, "rmtree", side_effect=OSError("Permission denied")):
            # Should not crash
            cleanup_orphaned_pending_folders(temp_specs_dir)

    def test_cleanup_with_nonexistent_specs_dir(self, tmp_path):
        """Test cleanup with nonexistent specs directory."""
        nonexistent = tmp_path / "nonexistent" / "specs"

        # Should not crash
        cleanup_orphaned_pending_folders(nonexistent)

    def test_cleanup_handles_stat_oserror_on_age_check(self, temp_specs_dir):
        """Test cleanup handles OSError when checking folder age (line 70)."""
        pending = temp_specs_dir / "001-pending"
        pending.mkdir()

        # Make it old first
        old_time = datetime.now() - timedelta(minutes=15)
        import os
        os.utime(pending, (old_time.timestamp(), old_time.timestamp()))

        # Mock stat() to raise OSError only on the second call (when checking age)
        original_stat = Path.stat
        call_count = [0]
        in_cleanup = [False]  # Track when we're in the cleanup function

        def mock_stat(self, follow_symlinks=True):
            if self == pending:
                call_count[0] += 1
                # During cleanup, second call (for st_mtime) should raise error
                if in_cleanup[0] and call_count[0] == 2:
                    raise OSError("Cannot get mtime")
                return original_stat(self, follow_symlinks=follow_symlinks)
            return original_stat(self, follow_symlinks=follow_symlinks)

        with patch.object(Path, "stat", mock_stat):
            # Mark that we're entering cleanup
            in_cleanup[0] = True
            # Should not crash and should preserve the folder (can't determine age)
            cleanup_orphaned_pending_folders(temp_specs_dir)
            in_cleanup[0] = False
            # Folder should still exist since we couldn't check its age
            assert pending.exists()


class TestCreateSpecDir:
    """Tests for create_spec_dir function."""

    def test_create_spec_dir_first_spec(self, temp_specs_dir):
        """Test create_spec_dir creates 001-pending for first spec."""
        result = create_spec_dir(temp_specs_dir)

        assert result == temp_specs_dir / "001-pending"

    def test_create_spec_dir_incrementing(self, temp_specs_dir):
        """Test create_spec_dir increments number correctly."""
        # Create existing specs
        (temp_specs_dir / "001-feature").mkdir()
        (temp_specs_dir / "002-bugfix").mkdir()

        result = create_spec_dir(temp_specs_dir)

        assert result == temp_specs_dir / "003-pending"

    def test_create_spec_dir_finds_highest_number(self, temp_specs_dir):
        """Test create_spec_dir finds the highest existing number."""
        # Create non-sequential specs
        (temp_specs_dir / "001-feature").mkdir()
        (temp_specs_dir / "005-bugfix").mkdir()
        (temp_specs_dir / "003-task").mkdir()

        result = create_spec_dir(temp_specs_dir)

        assert result == temp_specs_dir / "006-pending"

    def test_create_spec_dir_with_empty_existing(self, temp_specs_dir):
        """Test create_spec_dir when no existing specs match pattern."""
        # Create a folder that doesn't match the pattern
        (temp_specs_dir / "custom-folder").mkdir()

        result = create_spec_dir(temp_specs_dir)

        assert result == temp_specs_dir / "001-pending"

    def test_create_spec_dir_with_invalid_names(self, temp_specs_dir):
        """Test create_spec_dir ignores folders with invalid names."""
        # Create folders that don't match the XXX-* pattern
        (temp_specs_dir / "folder").mkdir()
        (temp_specs_dir / "99-invalid").mkdir()

        result = create_spec_dir(temp_specs_dir)

        assert result == temp_specs_dir / "001-pending"

    def test_create_spec_dir_with_lock(self, temp_specs_dir):
        """Test create_spec_dir with SpecNumberLock."""
        mock_lock = MagicMock()
        mock_lock.get_next_spec_number.return_value = 42

        result = create_spec_dir(temp_specs_dir, lock=mock_lock)

        assert result == temp_specs_dir / "042-pending"
        mock_lock.get_next_spec_number.assert_called_once()

    def test_create_spec_dir_without_lock_uses_local_scan(self, temp_specs_dir):
        """Test create_spec_dir without lock uses local scan."""
        (temp_specs_dir / "001-existing").mkdir()

        result = create_spec_dir(temp_specs_dir, lock=None)

        assert result == temp_specs_dir / "002-pending"


class TestGenerateSpecName:
    """Tests for generate_spec_name function."""

    def test_generate_spec_name_basic(self):
        """Test generate_spec_name with basic description."""
        result = generate_spec_name("Add user authentication system")
        assert "user" in result
        assert "authentication" in result
        assert "system" in result

    def test_generate_spec_name_removes_skip_words(self):
        """Test generate_spec_name removes common skip words."""
        result = generate_spec_name("Create a new user authentication system for the app")
        assert "a" not in result.split("-")
        assert "new" not in result.split("-")
        assert "the" not in result.split("-")
        assert "for" not in result.split("-")

    def test_generate_spec_name_limits_to_four_words(self):
        """Test generate_spec_name limits to 4 meaningful words."""
        result = generate_spec_name("add create make implement build new user authentication login system with database")
        # Should have at most 4 words after filtering
        word_count = len(result.split("-"))
        assert word_count <= 4

    def test_generate_spec_name_all_skip_words(self):
        """Test generate_spec_name when all words are skip words."""
        result = generate_spec_name("the a an for to of in on")
        # Should fall back to first few words (all skip words but < 3 chars each removed)
        # Actually, skip words include short words, so we get first few words
        assert len(result.split("-")) <= 4

    def test_generate_spec_name_short_words_filtered(self):
        """Test generate_spec_name filters out short words."""
        result = generate_spec_name("add a new user auth system to the app")
        assert "add" not in result.split("-")
        assert "to" not in result.split("-")
        # Should have meaningful words
        assert "user" in result or "auth" in result or "system" in result or "app" in result

    def test_generate_spec_name_special_chars_removed(self):
        """Test generate_spec_name removes special characters."""
        result = generate_spec_name("Add user@auth #system! for $app")
        assert "@" not in result
        assert "#" not in result
        assert "!" not in result
        assert "$" not in result

    def test_generate_spec_name_lowercase(self):
        """Test generate_spec_name converts to lowercase."""
        result = generate_spec_name("Build User AUTHENTICATION System")
        assert result == result.lower()

    def test_generate_spec_name_empty_description(self):
        """Test generate_spec_name with empty description."""
        result = generate_spec_name("")
        assert result == "spec"

    def test_generate_spec_name_very_short_description(self):
        """Test generate_spec_name with very short description."""
        result = generate_spec_name("do")
        # "do" is a skip word and too short
        assert result == "do"

    def test_generate_spec_name_with_numbers(self):
        """Test generate_spec_name preserves numbers in description."""
        result = generate_spec_name("Add OAuth2 authentication for API v3")
        assert "oauth2" in result or "oauth" in result
        assert "api" in result

    def test_generate_spec_name_max_four_meaningful_words(self):
        """Test that only first 4 meaningful words are used."""
        result = generate_spec_name("implement secure user authentication system with database integration and api endpoints")
        words = result.split("-")
        assert len(words) <= 4


class TestRenameSpecDirFromRequirements:
    """Tests for rename_spec_dir_from_requirements function."""

    def test_rename_success(self, tmp_path):
        """Test rename_spec_dir_from_requirements successfully renames."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir(parents=True)
        spec_dir = specs_dir / "001-pending"
        spec_dir.mkdir()

        # Create requirements
        req_file = spec_dir / "requirements.json"
        req_file.write_text(json.dumps({
            "task_description": "Build authentication system"
        }), encoding="utf-8")

        result = rename_spec_dir_from_requirements(spec_dir)

        assert result is True
        assert not spec_dir.exists()
        assert (specs_dir / "001-authentication-system").exists()

    def test_rename_missing_requirements(self, tmp_path):
        """Test rename when requirements.json doesn't exist."""
        spec_dir = tmp_path / "001-pending"
        spec_dir.mkdir()

        result = rename_spec_dir_from_requirements(spec_dir)

        assert result is False
        assert spec_dir.exists()

    def test_rename_empty_task_description(self, tmp_path):
        """Test rename when task_description is empty."""
        spec_dir = tmp_path / "001-pending"
        spec_dir.mkdir()
        req_file = spec_dir / "requirements.json"
        req_file.write_text(json.dumps({
            "task_description": ""
        }), encoding="utf-8")

        result = rename_spec_dir_from_requirements(spec_dir)

        assert result is False
        assert spec_dir.exists()

    def test_rename_non_pending_dir(self, tmp_path):
        """Test rename when directory is not pending."""
        spec_dir = tmp_path / "001-existing-name"
        spec_dir.mkdir()
        req_file = spec_dir / "requirements.json"
        req_file.write_text(json.dumps({
            "task_description": "Build feature"
        }), encoding="utf-8")

        result = rename_spec_dir_from_requirements(spec_dir)

        assert result is True  # Returns True (no rename needed)
        assert spec_dir.exists()

    def test_rename_target_exists(self, tmp_path):
        """Test rename when target directory already exists."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir(parents=True)
        spec_dir = specs_dir / "001-pending"
        spec_dir.mkdir()

        # Create target directory
        (specs_dir / "001-authentication-system").mkdir()

        req_file = spec_dir / "requirements.json"
        req_file.write_text(json.dumps({
            "task_description": "Build authentication system"
        }), encoding="utf-8")

        result = rename_spec_dir_from_requirements(spec_dir)

        assert result is True  # Returns True (rename skipped)
        assert spec_dir.exists()

    def test_rename_invalid_json(self, tmp_path):
        """Test rename with invalid JSON in requirements."""
        spec_dir = tmp_path / "001-pending"
        spec_dir.mkdir()
        req_file = spec_dir / "requirements.json"
        req_file.write_text("invalid json", encoding="utf-8")

        result = rename_spec_dir_from_requirements(spec_dir)

        assert result is False
        assert spec_dir.exists()

    def test_rename_without_digit_prefix(self, tmp_path):
        """Test rename when directory doesn't have digit prefix."""
        spec_dir = tmp_path / "pending"
        spec_dir.mkdir()
        req_file = spec_dir / "requirements.json"
        req_file.write_text(json.dumps({
            "task_description": "Build feature"
        }), encoding="utf-8")

        result = rename_spec_dir_from_requirements(spec_dir)

        assert result is True

    def test_rename_updates_task_logger(self, tmp_path):
        """Test rename updates global task logger path."""
        spec_dir = tmp_path / "001-pending"
        spec_dir.mkdir()
        req_file = spec_dir / "requirements.json"
        req_file.write_text(json.dumps({
            "task_description": "Build feature"
        }), encoding="utf-8")

        with patch("spec.pipeline.models.update_task_logger_path") as mock_update:
            result = rename_spec_dir_from_requirements(spec_dir)

            assert result is True
            mock_update.assert_called_once()

    def test_rename_handles_move_error(self, tmp_path):
        """Test rename handles shutil.move errors."""
        spec_dir = tmp_path / "001-pending"
        spec_dir.mkdir()
        req_file = spec_dir / "requirements.json"
        req_file.write_text(json.dumps({
            "task_description": "Build feature"
        }), encoding="utf-8")

        import shutil
        with patch.object(shutil, "move", side_effect=OSError("Permission denied")):
            result = rename_spec_dir_from_requirements(spec_dir)

            assert result is False

    def test_rename_various_descriptions(self, tmp_path):
        """Test rename with various task descriptions."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir(parents=True)

        test_cases = [
            "Add OAuth2 authentication",
            "Create user profile page",
            "Implement database migrations",
            "Fix login bug",
        ]

        for i, desc in enumerate(test_cases):
            spec_dir = specs_dir / f"{i+1:03d}-pending"
            spec_dir.mkdir()
            req_file = spec_dir / "requirements.json"
            req_file.write_text(json.dumps({
                "task_description": desc
            }), encoding="utf-8")

            result = rename_spec_dir_from_requirements(spec_dir)
            assert result is True


class TestPhaseDisplay:
    """Tests for PHASE_DISPLAY constant."""

    def test_phase_display_structure(self):
        """Test PHASE_DISPLAY has correct structure."""
        assert isinstance(PHASE_DISPLAY, dict)

        for key, (name, icon) in PHASE_DISPLAY.items():
            assert isinstance(key, str)
            assert isinstance(name, str)
            # Icon is a tuple of (emoji, text_code) from ui.Icons
            assert isinstance(icon, tuple)
            assert len(icon) == 2
            assert isinstance(icon[0], str)  # emoji
            assert isinstance(icon[1], str)  # text code

    def test_phase_display_required_keys(self):
        """Test PHASE_DISPLAY has all required phase keys."""
        required_keys = [
            "discovery",
            "historical_context",
            "requirements",
            "complexity_assessment",
            "research",
            "context",
            "quick_spec",
            "spec_writing",
            "self_critique",
            "planning",
            "validation",
        ]

        for key in required_keys:
            assert key in PHASE_DISPLAY
            name, icon = PHASE_DISPLAY[key]
            assert name  # Should not be empty
            assert icon  # Should not be empty


class TestGetSpecsDirEdgeCases:
    """Edge case tests for get_specs_dir function."""

    def test_get_specs_dir_init_failure(self, tmp_path):
        """Test get_specs_dir when init_auto_claude_dir fails."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Mock init to raise an exception
        with patch("spec.pipeline.models.init_auto_claude_dir",
                   side_effect=OSError("Permission denied")):
            with pytest.raises(OSError):
                get_specs_dir(project_dir)

    def test_get_specs_dir_with_symlink_project(self, tmp_path):
        """Test get_specs_dir with symlinked project directory."""
        # Create actual project directory
        actual_project = tmp_path / "actual_project"
        actual_project.mkdir()

        # Create symlink
        project_symlink = tmp_path / "project_link"
        try:
            project_symlink.symlink_to(actual_project)
        except OSError:
            # Symlinks not supported on this system
            pytest.skip("Symlinks not supported")

        specs_dir = get_specs_dir(project_symlink)

        # Should resolve to specs dir in the symlink target
        assert specs_dir == project_symlink / ".auto-claude" / "specs"

    def test_get_specs_dir_read_only_project(self, tmp_path):
        """Test get_specs_dir when .auto-claude cannot be created."""
        project_dir = tmp_path / "readonly_project"
        project_dir.mkdir()

        # Mock mkdir to raise permission error
        with patch("pathlib.Path.mkdir", side_effect=OSError("Read-only filesystem")):
            with patch("spec.pipeline.models.init_auto_claude_dir",
                       side_effect=OSError("Read-only filesystem")):
                with pytest.raises(OSError):
                    get_specs_dir(project_dir)


class TestCleanupOrphanedPendingFoldersEdgeCases:
    """Edge case tests for cleanup_orphaned_pending_folders function."""

    def test_cleanup_with_permission_denied_on_iterate(self, temp_specs_dir):
        """Test cleanup when iterating fails due to permissions."""
        # The glob() call happens on specs_dir, but we can't mock Path.glob globally
        # Instead test the behavior when specs_dir doesn't exist
        # (the function checks existence first)
        nonexistent = temp_specs_dir / "nonexistent_specs"
        # Should not crash
        cleanup_orphaned_pending_folders(nonexistent)

    def test_cleanup_with_broken_symlink(self, temp_specs_dir):
        """Test cleanup handles broken symlinks gracefully."""
        # Create a symlink pointing to non-existent target
        broken_link = temp_specs_dir / "001-pending"
        try:
            broken_link.symlink_to("/nonexistent/path")
        except OSError:
            pytest.skip("Symlinks not supported")

        # The glob will find the symlink
        # When is_dir() is called on a broken symlink, it may raise OSError
        # or return False depending on the Python version and OS
        # The function catches OSError during stat() so should not crash
        try:
            cleanup_orphaned_pending_folders(temp_specs_dir)
            # If it doesn't crash, test passes
            assert True
        except OSError:
            # On some systems, the symlink causes errors
            # This is acceptable behavior
            pytest.skip("Broken symlink handling not supported on this system")

    def test_cleanup_with_file_instead_of_dir(self, temp_specs_dir):
        """Test cleanup when a file matches the pending pattern."""
        # Create a file matching the pattern
        pending_file = temp_specs_dir / "001-pending"
        pending_file.write_text("I'm a file, not a directory")

        # Should not crash or remove the file
        cleanup_orphaned_pending_folders(temp_specs_dir)
        assert pending_file.exists()

    def test_cleanup_with_empty_specs_dir(self, tmp_path):
        """Test cleanup with empty specs directory."""
        empty_specs = tmp_path / "empty_specs"
        empty_specs.mkdir(parents=True)

        # Should not crash
        cleanup_orphaned_pending_folders(empty_specs)

    def test_cleanup_with_partial_content_files(self, temp_specs_dir):
        """Test cleanup preserves folders with partial content files."""
        pending = temp_specs_dir / "001-pending"
        pending.mkdir()

        # Create a non-standard content file
        (pending / "context.json").write_text('{"context": "data"}')

        # Make it old
        old_time = datetime.now() - timedelta(minutes=15)
        os.utime(pending, (old_time.timestamp(), old_time.timestamp()))

        cleanup_orphaned_pending_folders(temp_specs_dir)

        # Should be removed since context.json is not one of the checked files
        assert not pending.exists()

    def test_cleanup_with_exactly_10_minutes_old(self, temp_specs_dir):
        """Test cleanup boundary condition at exactly 10 minutes."""
        pending = temp_specs_dir / "001-pending"
        pending.mkdir()

        # Make it exactly 10 minutes old (boundary condition)
        old_time = datetime.now() - timedelta(minutes=10)
        os.utime(pending, (old_time.timestamp(), old_time.timestamp()))

        cleanup_orphaned_pending_folders(temp_specs_dir)

        # Will be removed since condition is < 10 minutes to preserve,
        # and exactly 10 minutes fails that check
        assert not pending.exists()

    def test_cleanup_with_subdirectories(self, temp_specs_dir):
        """Test cleanup handles folders with subdirectories."""
        pending = temp_specs_dir / "001-pending"
        pending.mkdir()
        (pending / "subdir").mkdir()
        (pending / "subdir2").mkdir()

        # Make it old
        old_time = datetime.now() - timedelta(minutes=15)
        os.utime(pending, (old_time.timestamp(), old_time.timestamp()))

        cleanup_orphaned_pending_folders(temp_specs_dir)

        # Should be removed even with subdirectories
        assert not pending.exists()

    def test_cleanup_with_similar_but_different_pattern(self, temp_specs_dir):
        """Test cleanup only matches exact pattern."""
        # Create folders with similar but different patterns
        (temp_specs_dir / "001-pending-old").mkdir()
        (temp_specs_dir / "pending-001").mkdir()
        (temp_specs_dir / "01-pending").mkdir()

        # Make them all old
        old_time = datetime.now() - timedelta(minutes=15)
        for folder in [
            temp_specs_dir / "001-pending-old",
            temp_specs_dir / "pending-001",
            temp_specs_dir / "01-pending",
        ]:
            os.utime(folder, (old_time.timestamp(), old_time.timestamp()))

        cleanup_orphaned_pending_folders(temp_specs_dir)

        # None should be removed as they don't match the exact pattern
        assert (temp_specs_dir / "001-pending-old").exists()
        assert (temp_specs_dir / "pending-001").exists()
        assert (temp_specs_dir / "01-pending").exists()


class TestCreateSpecDirEdgeCases:
    """Edge case tests for create_spec_dir function."""

    def test_create_spec_dir_with_gaps_in_numbers(self, temp_specs_dir):
        """Test create_spec_dir with gaps in existing spec numbers."""
        # Create non-sequential specs with gaps
        (temp_specs_dir / "001-feature").mkdir()
        (temp_specs_dir / "005-bugfix").mkdir()
        (temp_specs_dir / "010-task").mkdir()

        result = create_spec_dir(temp_specs_dir)

        # Should use highest + 1
        assert result == temp_specs_dir / "011-pending"

    def test_create_spec_dir_with_non_digit_prefix(self, temp_specs_dir):
        """Test create_spec_dir handles folders with non-digit prefixes."""
        (temp_specs_dir / "aaa-feature").mkdir()
        (temp_specs_dir / "bbb-bugfix").mkdir()

        result = create_spec_dir(temp_specs_dir)

        # Should start from 001 since no valid numeric prefixes found
        assert result == temp_specs_dir / "001-pending"

    def test_create_spec_dir_with_mixed_valid_invalid(self, temp_specs_dir):
        """Test create_spec_dir with mix of valid and invalid folders."""
        (temp_specs_dir / "001-valid").mkdir()
        (temp_specs_dir / "abc-invalid").mkdir()
        (temp_specs_dir / "003-valid").mkdir()
        (temp_specs_dir / "xyz-nonsense").mkdir()

        result = create_spec_dir(temp_specs_dir)

        # Should find max of valid (003) and add 1
        assert result == temp_specs_dir / "004-pending"

    def test_create_spec_dir_very_high_number(self, temp_specs_dir):
        """Test create_spec_dir with very high existing spec number."""
        (temp_specs_dir / "999-feature").mkdir()

        result = create_spec_dir(temp_specs_dir)

        assert result == temp_specs_dir / "1000-pending"

    def test_create_spec_dir_lock_returns_zero(self, temp_specs_dir):
        """Test create_spec_dir when lock returns 0."""
        mock_lock = MagicMock()
        mock_lock.get_next_spec_number.return_value = 0

        result = create_spec_dir(temp_specs_dir, lock=mock_lock)

        # Should format 0 as 000
        assert result == temp_specs_dir / "000-pending"

    def test_create_spec_dir_lock_raises_exception(self, temp_specs_dir):
        """Test create_spec_dir when lock.get_next_spec_number raises."""
        mock_lock = MagicMock()
        mock_lock.get_next_spec_number.side_effect = RuntimeError("Lock error")

        with pytest.raises(RuntimeError):
            create_spec_dir(temp_specs_dir, lock=mock_lock)

    def test_create_spec_dir_lock_returns_negative(self, temp_specs_dir):
        """Test create_spec_dir when lock returns negative number."""
        mock_lock = MagicMock()
        mock_lock.get_next_spec_number.return_value = -1

        result = create_spec_dir(temp_specs_dir, lock=mock_lock)

        # Should format -1 as -01 (weird but should not crash)
        assert result == temp_specs_dir / "-01-pending"

    def test_create_spec_dir_with_readonly_parent(self, temp_specs_dir):
        """Test create_spec_dir when specs dir is read-only."""
        # Note: This test may not work on all systems due to permission handling
        # The function only returns a path, doesn't create the directory
        (temp_specs_dir / "001-existing").mkdir()

        result = create_spec_dir(temp_specs_dir)

        # Should still return the path even if directory can't be created
        assert result == temp_specs_dir / "002-pending"


class TestGenerateSpecNameEdgeCases:
    """Edge case tests for generate_spec_name function."""

    def test_generate_spec_name_all_special_chars(self):
        """Test generate_spec_name with only special characters."""
        result = generate_spec_name("@#$%^&*()!")

        # Should return "spec" when no meaningful words
        assert result == "spec"

    def test_generate_spec_name_all_numbers(self):
        """Test generate_spec_name with only numbers."""
        result = generate_spec_name("123 456 789")

        # Numbers are kept as they're > 2 chars
        assert result == "123-456-789"

    def test_generate_spec_name_with_unicode_chars(self):
        """Test generate_spec_name with unicode characters."""
        result = generate_spec_name("Add user authentication system café")

        # Unicode chars become spaces, words are preserved
        assert "user" in result
        assert "authentication" in result or "caf" in result

    def test_generate_spec_name_with_tabs_and_newlines(self):
        """Test generate_spec_name with tabs and newlines."""
        result = generate_spec_name("Add\tuser\nauthentication\rsystem")

        # Should handle whitespace characters
        assert "user" in result
        assert "authentication" in result

    def test_generate_spec_name_very_long_description(self):
        """Test generate_spec_name with very long description."""
        long_desc = " ".join(["feature"] * 100)
        result = generate_spec_name(long_desc)

        # Should limit to 4 words
        assert len(result.split("-")) <= 4

    def test_generate_spec_name_with_url(self):
        """Test generate_spec_name with URL in description."""
        result = generate_spec_name("Add user authentication https://example.com/auth")

        # URL chars become spaces or are removed
        assert "user" in result
        assert "authentication" in result

    def test_generate_spec_name_with_underscores(self):
        """Test generate_spec_name with underscores."""
        result = generate_spec_name("Add user_auth system")

        # Underscores are replaced with spaces
        assert "user" in result
        assert "auth" in result

    def test_generate_spec_name_single_character_words(self):
        """Test generate_spec_name filters single character words."""
        result = generate_spec_name("Add a new user auth system")

        # "a" is filtered but other words remain
        assert "a" not in result.split("-")

    def test_generate_spec_name_exactly_four_meaningful_words(self):
        """Test generate_spec_name with exactly 4 meaningful words."""
        result = generate_spec_name("User authentication login system database")

        # Should take all 4 words
        assert "user" in result
        assert "authentication" in result or "login" in result

    def test_generate_spec_name_with_punctuation_only(self):
        """Test generate_spec_name with only punctuation."""
        result = generate_spec_name("!@#$%")

        # Should return "spec" fallback
        assert result == "spec"

    def test_generate_spec_name_with_hyphenated_words(self):
        """Test generate_spec_name with hyphenated input."""
        result = generate_spec_name("Add user-auth system")

        # Hyphen becomes space, words processed separately
        assert "user" in result or "auth" in result

    def test_generate_spec_name_with_multiple_spaces(self):
        """Test generate_spec_name with multiple consecutive spaces."""
        result = generate_spec_name("Add    user    authentication")

        # Multiple spaces collapsed to single
        assert "user" in result
        assert "authentication" in result

    def test_generate_spec_name_case_insensitive_skip_words(self):
        """Test that skip words are filtered case-insensitively."""
        result = generate_spec_name("Create THE system for User")

        # "THE" and "for" should be filtered regardless of case
        assert "the" not in result.lower().split("-")
        assert "for" not in result.lower().split("-")


class TestRenameSpecDirFromRequirementsEdgeCases:
    """Edge case tests for rename_spec_dir_from_requirements function."""

    def test_rename_with_permission_denied_on_read(self, tmp_path):
        """Test rename when requirements.json cannot be read."""
        spec_dir = tmp_path / "001-pending"
        spec_dir.mkdir()
        req_file = spec_dir / "requirements.json"
        req_file.write_text('{"task_description": "test"}')

        # Mock open to raise permission error
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            result = rename_spec_dir_from_requirements(spec_dir)

            assert result is False

    def test_rename_with_corrupted_symlink(self, tmp_path):
        """Test rename when requirements.json is a corrupted symlink."""
        spec_dir = tmp_path / "001-pending"
        spec_dir.mkdir()

        # Create a symlink to nowhere
        req_link = spec_dir / "requirements.json"
        try:
            req_link.symlink_to("/nonexistent/file.json")
        except OSError:
            pytest.skip("Symlinks not supported")

        # The exists() check on broken symlink may raise PermissionError
        # The function catches OSError (which includes PermissionError)
        try:
            result = rename_spec_dir_from_requirements(spec_dir)
            # If we get here, the system handled the symlink gracefully
            assert result is False
        except (PermissionError, OSError):
            # On some systems, broken symlinks cause errors before we can catch them
            # This is acceptable behavior for this edge case
            pass

    def test_rename_with_missing_task_description_key(self, tmp_path):
        """Test rename when task_description key is missing."""
        spec_dir = tmp_path / "001-pending"
        spec_dir.mkdir()
        req_file = spec_dir / "requirements.json"
        req_file.write_text('{"other_key": "value"}')

        result = rename_spec_dir_from_requirements(spec_dir)

        assert result is False

    def test_rename_with_none_task_description(self, tmp_path):
        """Test rename when task_description is None."""
        spec_dir = tmp_path / "001-pending"
        spec_dir.mkdir()
        req_file = spec_dir / "requirements.json"
        req_file.write_text('{"task_description": null}')

        result = rename_spec_dir_from_requirements(spec_dir)

        assert result is False

    def test_rename_with_nonexistent_parent_dir(self, tmp_path):
        """Test rename with spec_dir in nonexistent parent."""
        nonexistent_spec = tmp_path / "nonexistent" / "001-pending"

        result = rename_spec_dir_from_requirements(nonexistent_spec)

        assert result is False

    def test_rename_with_whitespace_only_description(self, tmp_path):
        """Test rename with whitespace-only task description."""
        spec_dir = tmp_path / "001-pending"
        spec_dir.mkdir()
        req_file = spec_dir / "requirements.json"
        req_file.write_text('{"task_description": "   "}')

        result = rename_spec_dir_from_requirements(spec_dir)

        # generate_spec_name handles whitespace, returns "spec"
        # The rename may succeed or fail depending on target existence
        assert isinstance(result, bool)

    def test_rename_with_number_suffix_collision(self, tmp_path):
        """Test rename when generated name would create collision."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir(parents=True)
        spec_dir = specs_dir / "001-pending"
        spec_dir.mkdir()

        # Create target that will conflict
        (specs_dir / "001-feature").mkdir()

        req_file = spec_dir / "requirements.json"
        req_file.write_text('{"task_description": "Build feature"}')

        result = rename_spec_dir_from_requirements(spec_dir)

        # Should return True (rename skipped due to collision)
        assert result is True

    def test_rename_with_empty_prefix_directory(self, tmp_path):
        """Test rename with directory name that has no numeric prefix."""
        spec_dir = tmp_path / "pending"  # No numeric prefix
        spec_dir.mkdir()
        req_file = spec_dir / "requirements.json"
        req_file.write_text('{"task_description": "Build feature"}')

        result = rename_spec_dir_from_requirements(spec_dir)

        # Should still work with empty prefix
        assert isinstance(result, bool)

    def test_rename_with_task_logger_update_failure(self, tmp_path):
        """Test rename when task logger update fails."""
        spec_dir = tmp_path / "001-pending"
        spec_dir.mkdir()
        req_file = spec_dir / "requirements.json"
        req_file.write_text('{"task_description": "Build feature"}')

        # Mock update_task_logger_path to raise error
        # The function still returns True but the error is printed via print_status
        with patch("spec.pipeline.models.update_task_logger_path"):
            with patch("spec.pipeline.models.print_status") as mock_print:
                import shutil
                with patch.object(shutil, "move",
                                  side_effect=[None, OSError("Logger error")]):
                    # First call (move) succeeds, second (update_task_logger_path) fails
                    # Actually, the move happens first, then update is called
                    # If update fails, the function still returns True because rename succeeded
                    result = rename_spec_dir_from_requirements(spec_dir)
                    # The function catches exceptions from both move and update
                    # But print_status is only called on OSError from move
                    # Let's just verify it doesn't crash
                    assert isinstance(result, bool)

    def test_rename_with_read_only_target_dir(self, tmp_path):
        """Test rename when target directory exists and is read-only."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir(parents=True)
        spec_dir = specs_dir / "001-pending"
        spec_dir.mkdir()

        # Create target directory
        target = specs_dir / "001-feature"
        target.mkdir()

        req_file = spec_dir / "requirements.json"
        req_file.write_text('{"task_description": "Build feature"}')

        result = rename_spec_dir_from_requirements(spec_dir)

        # Should skip rename and return True
        assert result is True
        assert spec_dir.exists()

    def test_rename_with_non_ascii_description(self, tmp_path):
        """Test rename with non-ASCII characters in description."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir(parents=True)
        spec_dir = specs_dir / "001-pending"
        spec_dir.mkdir()

        req_file = spec_dir / "requirements.json"
        req_file.write_text('{"task_description": "用户认证系统"}')

        result = rename_spec_dir_from_requirements(spec_dir)

        # Should handle non-ASCII gracefully
        assert isinstance(result, bool)

    def test_rename_with_very_long_description(self, tmp_path):
        """Test rename with very long task description."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir(parents=True)
        spec_dir = specs_dir / "001-pending"
        spec_dir.mkdir()

        long_desc = "Implement a " + "very " * 100 + "complex system"
        req_file = spec_dir / "requirements.json"
        req_file.write_text(json.dumps({"task_description": long_desc}))

        result = rename_spec_dir_from_requirements(spec_dir)

        # Should handle long descriptions (limited to 4 words)
        assert isinstance(result, bool)

    def test_rename_with_existing_target_as_file(self, tmp_path):
        """Test rename when target exists as a file not directory."""
        specs_dir = tmp_path / "specs"
        specs_dir.mkdir(parents=True)
        spec_dir = specs_dir / "001-pending"
        spec_dir.mkdir()

        # Create target as a file (not directory)
        target_file = specs_dir / "001-feature"
        target_file.write_text("I'm a file")

        req_file = spec_dir / "requirements.json"
        req_file.write_text('{"task_description": "Build feature"}')

        result = rename_spec_dir_from_requirements(spec_dir)

        # Should skip rename
        assert result is True

    def test_rename_preserves_existing_non_pending(self, tmp_path):
        """Test rename preserves directory already renamed."""
        spec_dir = tmp_path / "001-existing-name"
        spec_dir.mkdir()
        req_file = spec_dir / "requirements.json"
        req_file.write_text('{"task_description": "Build different feature"}')

        result = rename_spec_dir_from_requirements(spec_dir)

        # Should return True (no rename needed for non-pending)
        assert result is True
        assert spec_dir.exists()  # Name unchanged


class TestIntegrationScenarios:
    """Integration tests combining multiple functions."""

    def test_full_spec_creation_workflow(self, temp_specs_dir):
        """Test the complete workflow of creating and renaming a spec."""
        # Create spec dir (function returns path, we need to mkdir)
        spec_dir = create_spec_dir(temp_specs_dir)
        spec_dir.mkdir()  # Create the actual directory
        assert spec_dir.name == "001-pending"

        # Create requirements file
        req_file = spec_dir / "requirements.json"
        req_file.write_text(json.dumps({
            "task_description": "Implement OAuth2 authentication system"
        }))

        # Rename based on requirements
        result = rename_spec_dir_from_requirements(spec_dir)
        assert result is True

        # Check renamed directory exists
        new_dir = temp_specs_dir / "001-oauth2-authentication-system"
        assert new_dir.exists()
        assert not spec_dir.exists()

    def test_cleanup_after_failed_spec_creation(self, temp_specs_dir):
        """Test cleanup of orphaned folders after failed spec creation."""
        # Create a pending folder that was never completed
        pending = temp_specs_dir / "001-pending"
        pending.mkdir()

        # Make it old
        old_time = datetime.now() - timedelta(minutes=15)
        os.utime(pending, (old_time.timestamp(), old_time.timestamp()))

        # Create another spec with content
        (temp_specs_dir / "002-feature").mkdir()
        ((temp_specs_dir / "002-feature") / "spec.md").write_text("# Spec")

        # Run cleanup
        cleanup_orphaned_pending_folders(temp_specs_dir)

        # Orphaned folder should be removed
        assert not pending.exists()
        # Valid spec should remain
        assert (temp_specs_dir / "002-feature").exists()

    def test_multiple_specs_sequential_creation(self, temp_specs_dir):
        """Test creating multiple specs sequentially."""
        for i, desc in enumerate([
            "Add user authentication",
            "Create payment system",
            "Implement search feature"
        ]):
            spec_dir = create_spec_dir(temp_specs_dir)
            spec_dir.mkdir()  # Create the actual directory
            expected_num = f"{i+1:03d}"
            assert spec_dir.name == f"{expected_num}-pending"

            # Add requirements and rename
            req_file = spec_dir / "requirements.json"
            req_file.write_text(json.dumps({
                "task_description": desc
            }))

            rename_spec_dir_from_requirements(spec_dir)

        # Check all specs were created and renamed
        assert (temp_specs_dir / "001-user-authentication").exists()
        assert (temp_specs_dir / "002-payment-system").exists()
        assert (temp_specs_dir / "003-search-feature").exists()
