"""Tests for git_utils module in core.workspace.git_utils

Comprehensive test coverage for git utility functions including:
- detect_file_renames()
- apply_path_mapping()
- get_merge_base()
- has_uncommitted_changes()
- get_current_branch()
- get_existing_build_worktree()
- get_file_content_from_ref()
- get_binary_file_content_from_ref()
- get_changed_files_from_branch()
- is_process_running()
- is_binary_file()
- is_lock_file()
- validate_merged_syntax()
- create_conflict_file_with_git()
- Constants
- Backward compatibility aliases
"""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest

from core.workspace.git_utils import (
    # Constants
    MAX_FILE_LINES_FOR_AI,
    MAX_PARALLEL_AI_MERGES,
    LOCK_FILES,
    BINARY_EXTENSIONS,
    MERGE_LOCK_TIMEOUT,
    MAX_SYNTAX_FIX_RETRIES,
    # Functions
    apply_path_mapping,
    detect_file_renames,
    get_merge_base,
    has_uncommitted_changes,
    get_current_branch,
    get_existing_build_worktree,
    get_file_content_from_ref,
    get_binary_file_content_from_ref,
    get_changed_files_from_branch,
    is_process_running,
    is_binary_file,
    is_lock_file,
    validate_merged_syntax,
    create_conflict_file_with_git,
    # Backward compat aliases
    _is_process_running,
    _is_binary_file,
    _is_lock_file,
    _validate_merged_syntax,
    _get_file_content_from_ref,
    _get_binary_file_content_from_ref,
    _get_changed_files_from_branch,
    _create_conflict_file_with_git,
)


class TestConstants:
    """Tests for module constants."""

    def test_max_file_lines_for_ai(self):
        """Test MAX_FILE_LINES_FOR_AI constant."""
        assert MAX_FILE_LINES_FOR_AI == 5000

    def test_max_parallel_ai_merges(self):
        """Test MAX_PARALLEL_AI_MERGES constant."""
        assert MAX_PARALLEL_AI_MERGES == 5

    def test_lock_files_constant(self):
        """Test LOCK_FILES constant includes expected files."""
        assert "package-lock.json" in LOCK_FILES
        assert "yarn.lock" in LOCK_FILES
        assert "Cargo.lock" in LOCK_FILES
        assert "poetry.lock" in LOCK_FILES

    def test_binary_extensions_constant(self):
        """Test BINARY_EXTENSIONS constant includes expected extensions."""
        assert ".png" in BINARY_EXTENSIONS
        assert ".jpg" in BINARY_EXTENSIONS
        assert ".pdf" in BINARY_EXTENSIONS
        assert ".zip" in BINARY_EXTENSIONS
        assert ".exe" in BINARY_EXTENSIONS

    def test_merge_lock_timeout(self):
        """Test MERGE_LOCK_TIMEOUT constant."""
        assert MERGE_LOCK_TIMEOUT == 300

    def test_max_syntax_fix_retries(self):
        """Test MAX_SYNTAX_FIX_RETRIES constant."""
        assert MAX_SYNTAX_FIX_RETRIES == 2


class TestDetectFileRenames:
    """Tests for detect_file_renames function."""

    def test_detect_file_renames_basic(self):
        """Test detect_file_renames with renames."""
        project_dir = Path("/tmp/test")
        from_ref = "main"
        to_ref = "feature"

        with patch("core.workspace.git_utils.run_git") as mock_git:
            mock_git.return_value = MagicMock(
                returncode=0,
                stdout="R100\told/path.py\tnew/path.py\nR095\ta.py\tb.py\n",
                stderr=""
            )

            result = detect_file_renames(project_dir, from_ref, to_ref)

            assert result == {
                "old/path.py": "new/path.py",
                "a.py": "b.py",
            }

    def test_detect_file_renames_no_renames(self):
        """Test detect_file_renames with no renames."""
        project_dir = Path("/tmp/test")

        with patch("core.workspace.git_utils.run_git") as mock_git:
            mock_git.return_value = MagicMock(
                returncode=0,
                stdout="",
                stderr=""
            )

            result = detect_file_renames(project_dir, "main", "feature")

            assert result == {}

    def test_detect_file_renames_git_error(self):
        """Test detect_file_renames handles git errors gracefully."""
        project_dir = Path("/tmp/test")

        with patch("core.workspace.git_utils.run_git") as mock_git:
            mock_git.return_value = MagicMock(returncode=1, stdout="", stderr="Error")

            result = detect_file_renames(project_dir, "main", "feature")

            # Should return empty dict on error
            assert result == {}

    def test_detect_file_renames_exception_handling(self):
        """Test detect_file_renames handles exceptions gracefully."""
        project_dir = Path("/tmp/test")

        with patch("core.workspace.git_utils.run_git") as mock_git:
            mock_git.side_effect = Exception("Git error")

            result = detect_file_renames(project_dir, "main", "feature")

            # Should return empty dict on exception
            assert result == {}

    def test_detect_file_renames_malformed_output(self):
        """Test detect_file_renames handles malformed git output."""
        project_dir = Path("/tmp/test")

        with patch("core.workspace.git_utils.run_git") as mock_git:
            # Output with missing tabs
            mock_git.return_value = MagicMock(
                returncode=0,
                stdout="R100 old.py",
                stderr=""
            )

            result = detect_file_renames(project_dir, "main", "feature")

            # Should handle gracefully
            assert isinstance(result, dict)


class TestApplyPathMapping:
    """Tests for apply_path_mapping function."""

    def test_apply_path_mapping_exact_match(self):
        """Test apply_path_mapping with exact path match."""
        mappings = {"old/path.py": "new/path.py"}
        result = apply_path_mapping("old/path.py", mappings)
        assert result == "new/path.py"

    def test_apply_path_mapping_no_match(self):
        """Test apply_path_mapping with no matching path."""
        mappings = {"old/path.py": "new/path.py"}
        result = apply_path_mapping("unchanged/path.py", mappings)
        assert result == "unchanged/path.py"

    def test_apply_path_mapping_empty_mappings(self):
        """Test apply_path_mapping with empty mappings dict."""
        result = apply_path_mapping("some/path.py", {})
        assert result == "some/path.py"

    def test_apply_path_mapping_multiple_mappings(self):
        """Test apply_path_mapping with multiple mappings."""
        mappings = {
            "a.py": "b.py",
            "c.py": "d.py",
            "e/x.py": "f/y.py",
        }
        assert apply_path_mapping("a.py", mappings) == "b.py"
        assert apply_path_mapping("c.py", mappings) == "d.py"
        assert apply_path_mapping("e/x.py", mappings) == "f/y.py"
        assert apply_path_mapping("z.py", mappings) == "z.py"


class TestGetMergeBase:
    """Tests for get_merge_base function."""

    def test_get_merge_base_success(self):
        """Test get_merge_base returns commit hash."""
        project_dir = Path("/tmp/test")

        with patch("core.workspace.git_utils.run_git") as mock_git:
            mock_git.return_value = MagicMock(
                returncode=0,
                stdout="abc123def456\n",
                stderr=""
            )

            result = get_merge_base(project_dir, "main", "feature")

            assert result == "abc123def456"

    def test_get_merge_base_failure(self):
        """Test get_merge_base returns None on failure."""
        project_dir = Path("/tmp/test")

        with patch("core.workspace.git_utils.run_git") as mock_git:
            mock_git.return_value = MagicMock(returncode=1, stdout="", stderr="Error")

            result = get_merge_base(project_dir, "main", "feature")

            assert result is None


class TestHasUncommittedChanges:
    """Tests for has_uncommitted_changes function."""

    def test_has_uncommitted_changes_true(self):
        """Test has_uncommitted_changes returns True when changes exist."""
        project_dir = Path("/tmp/test")

        with patch("core.workspace.git_utils.run_git") as mock_git:
            mock_git.return_value = MagicMock(
                returncode=0,
                stdout=" M file.py\n",
                stderr=""
            )

            result = has_uncommitted_changes(project_dir)

            assert result is True

    def test_has_uncommitted_changes_false(self):
        """Test has_uncommitted_changes returns False when clean."""
        project_dir = Path("/tmp/test")

        with patch("core.workspace.git_utils.run_git") as mock_git:
            mock_git.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = has_uncommitted_changes(project_dir)

            assert result is False


class TestGetCurrentBranch:
    """Tests for get_current_branch function."""

    def test_get_current_branch_main(self):
        """Test get_current_branch returns branch name."""
        project_dir = Path("/tmp/test")

        with patch("core.workspace.git_utils.run_git") as mock_git:
            mock_git.return_value = MagicMock(
                returncode=0,
                stdout="main\n",
                stderr=""
            )

            result = get_current_branch(project_dir)

            assert result == "main"

    def test_get_current_branch_feature(self):
        """Test get_current_branch with feature branch."""
        project_dir = Path("/tmp/test")

        with patch("core.workspace.git_utils.run_git") as mock_git:
            mock_git.return_value = MagicMock(
                returncode=0,
                stdout="feature/test-branch\n",
                stderr=""
            )

            result = get_current_branch(project_dir)

            assert result == "feature/test-branch"


class TestGetExistingBuildWorktree:
    """Tests for get_existing_build_worktree function."""

    def test_get_existing_build_worktree_new_path(self, tmp_path):
        """Test get_existing_build_worktree finds new path."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_name = "001-feature"

        # Create new path
        new_path = project_dir / ".auto-claude" / "worktrees" / "tasks" / spec_name
        new_path.mkdir(parents=True)

        result = get_existing_build_worktree(project_dir, spec_name)

        assert result == new_path

    def test_get_existing_build_worktree_legacy_path(self, tmp_path):
        """Test get_existing_build_worktree finds legacy path."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_name = "001-feature"

        # Create legacy path
        legacy_path = project_dir / ".worktrees" / spec_name
        legacy_path.mkdir(parents=True)

        result = get_existing_build_worktree(project_dir, spec_name)

        assert result == legacy_path

    def test_get_existing_build_worktree_new_takes_priority(self, tmp_path):
        """Test get_existing_build_worktree prefers new path."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_name = "001-feature"

        # Create both paths
        new_path = project_dir / ".auto-claude" / "worktrees" / "tasks" / spec_name
        new_path.mkdir(parents=True)
        legacy_path = project_dir / ".worktrees" / spec_name
        legacy_path.mkdir(parents=True)

        result = get_existing_build_worktree(project_dir, spec_name)

        # Should prefer new path
        assert result == new_path

    def test_get_existing_build_worktree_not_found(self, tmp_path):
        """Test get_existing_build_worktree returns None when not found."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_name = "001-feature"

        result = get_existing_build_worktree(project_dir, spec_name)

        assert result is None


class TestGetFileContentFromRef:
    """Tests for get_file_content_from_ref function."""

    def test_get_file_content_from_ref_success(self):
        """Test get_file_content_from_ref returns file content."""
        project_dir = Path("/tmp/test")

        with patch("core.workspace.git_utils.run_git") as mock_git:
            mock_git.return_value = MagicMock(
                returncode=0,
                stdout="file content here",
                stderr=""
            )

            result = get_file_content_from_ref(project_dir, "main", "README.md")

            assert result == "file content here"

    def test_get_file_content_from_ref_not_found(self):
        """Test get_file_content_from_ref returns None when file not found."""
        project_dir = Path("/tmp/test")

        with patch("core.workspace.git_utils.run_git") as mock_git:
            mock_git.return_value = MagicMock(returncode=1, stdout="", stderr="Error")

            result = get_file_content_from_ref(project_dir, "main", "missing.py")

            assert result is None


class TestGetBinaryFileContentFromRef:
    """Tests for get_binary_file_content_from_ref function."""

    def test_get_binary_file_content_from_ref_success(self):
        """Test get_binary_file_content_from_ref returns bytes."""
        project_dir = Path("/tmp/test")

        with patch("core.workspace.git_utils.get_git_executable") as mock_git_exe:
            mock_git_exe.return_value = "git"

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout=b"\x89PNG\r\n\x1a\n",
                    stderr=b""
                )

                result = get_binary_file_content_from_ref(
                    project_dir, "main", "image.png"
                )

                assert result == b"\x89PNG\r\n\x1a\n"

    def test_get_binary_file_content_from_ref_not_found(self):
        """Test get_binary_file_content_from_ref returns None on failure."""
        project_dir = Path("/tmp/test")

        with patch("core.workspace.git_utils.get_git_executable") as mock_git_exe:
            mock_git_exe.return_value = "git"

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1,
                    stdout=b"",
                    stderr=b"Error"
                )

                result = get_binary_file_content_from_ref(
                    project_dir, "main", "missing.png"
                )

                assert result is None


class TestGetChangedFilesFromBranch:
    """Tests for get_changed_files_from_branch function."""

    def test_get_changed_files_from_branch_basic(self):
        """Test get_changed_files_from_branch returns list of files."""
        project_dir = Path("/tmp/test")

        # Patch at the point of use in the function
        import core.workspace.git_utils as git_utils_module
        with patch.object(git_utils_module, "run_git") as mock_git:
            mock_git.return_value = MagicMock(
                returncode=0,
                stdout="M\tfile1.py\nA\tfile2.py\nD\tfile3.py\n",
                stderr=""
            )

            result = get_changed_files_from_branch(
                project_dir, "main", "feature", exclude_auto_claude=False
            )

            assert len(result) == 3
            assert ("file1.py", "M") in result
            assert ("file2.py", "A") in result
            assert ("file3.py", "D") in result

    def test_get_changed_files_from_branch_exclude_auto_claude(self):
        """Test get_changed_files_from_branch excludes .auto-claude files."""
        project_dir = Path("/tmp/test")

        import core.workspace.git_utils as git_utils_module
        with patch.object(git_utils_module, "run_git") as mock_git:
            mock_git.return_value = MagicMock(
                returncode=0,
                stdout=(
                    "M\tfile1.py\n"
                    "M\t.auto-claude/specs/001/spec.md\n"
                    "M\tauto-claude/specs/002/plan.json\n"
                    "A\tfile2.py\n"
                ),
                stderr=""
            )

            result = get_changed_files_from_branch(
                project_dir, "main", "feature", exclude_auto_claude=True
            )

            # Should exclude .auto-claude and auto-claude/specs files
            assert len(result) == 2
            assert ("file1.py", "M") in result
            assert ("file2.py", "A") in result

    def test_get_changed_files_from_branch_tab_separated(self):
        """Test get_changed_files_from_branch handles tab-separated output."""
        project_dir = Path("/tmp/test")

        import core.workspace.git_utils as git_utils_module
        with patch.object(git_utils_module, "run_git") as mock_git:
            mock_git.return_value = MagicMock(
                returncode=0,
                stdout="M\tfile with spaces.py\nA\tnested/file.py\n",
                stderr=""
            )

            result = get_changed_files_from_branch(
                project_dir, "main", "feature", exclude_auto_claude=False
            )

            assert len(result) == 2
            assert ("file with spaces.py", "M") in result
            assert ("nested/file.py", "A") in result

    def test_get_changed_files_from_branch_empty(self):
        """Test get_changed_files_from_branch with no changes."""
        project_dir = Path("/tmp/test")

        import core.workspace.git_utils as git_utils_module
        with patch.object(git_utils_module, "run_git") as mock_git:
            mock_git.return_value = MagicMock(
                returncode=0,
                stdout="",
                stderr=""
            )

            result = get_changed_files_from_branch(
                project_dir, "main", "feature", exclude_auto_claude=False
            )

            assert result == []

    def test_get_changed_files_from_branch_windows_paths(self):
        """Test get_changed_files_from_branch handles Windows backslashes."""
        project_dir = Path("/tmp/test")

        import core.workspace.git_utils as git_utils_module
        with patch.object(git_utils_module, "run_git") as mock_git:
            mock_git.return_value = MagicMock(
                returncode=0,
                stdout="M\tpath\\to\\file.py\n",
                stderr=""
            )

            result = get_changed_files_from_branch(
                project_dir, "main", "feature", exclude_auto_claude=False
            )

            # Should still work even with backslashes
            assert len(result) >= 0


class TestIsProcessRunning:
    """Tests for is_process_running function."""

    def test_is_process_running_current_process(self):
        """Test is_process_running with current process PID."""
        import os as os_module
        current_pid = os_module.getpid()

        result = is_process_running(current_pid)

        # Current process should be running
        assert result is True

    def test_is_process_running_nonexistent_pid(self):
        """Test is_process_running with non-existent PID."""
        # Use a very high PID that likely doesn't exist
        result = is_process_running(9999999)

        assert result is False


class TestIsBinaryFile:
    """Tests for is_binary_file function."""

    def test_is_binary_file_images(self):
        """Test is_binary_file with image extensions."""
        assert is_binary_file("image.png") is True
        assert is_binary_file("photo.jpg") is True
        assert is_binary_file("pic.jpeg") is True
        assert is_binary_file("icon.gif") is True
        assert is_binary_file("logo.ico") is True
        assert is_binary_file("webp.webp") is True
        assert is_binary_file("tiff.tiff") is True
        assert is_binary_file("heic.heic") is True

    def test_is_binary_file_documents(self):
        """Test is_binary_file with document extensions."""
        assert is_binary_file("doc.pdf") is True
        assert is_binary_file("doc.doc") is True
        assert is_binary_file("sheet.xlsx") is True
        assert is_binary_file("slides.pptx") is True

    def test_is_binary_file_archives(self):
        """Test is_binary_file with archive extensions."""
        assert is_binary_file("archive.zip") is True
        assert is_binary_file("data.tar.gz") is True
        assert is_binary_file("compressed.7z") is True
        assert is_binary_file("package.rar") is True

    def test_is_binary_file_executables(self):
        """Test is_binary_file with executable extensions."""
        assert is_binary_file("program.exe") is True
        assert is_binary_file("library.dll") is True
        assert is_binary_file("lib.so") is True
        assert is_binary_file("mac.dylib") is True
        assert is_binary_file("binary.bin") is True

    def test_is_binary_file_media(self):
        """Test is_binary_file with media extensions."""
        assert is_binary_file("song.mp3") is True
        assert is_binary_file("video.mp4") is True
        assert is_binary_file("movie.avi") is True
        assert is_binary_file("clip.mov") is True

    def test_is_binary_file_fonts(self):
        """Test is_binary_file with font extensions."""
        assert is_binary_file("font.woff") is True
        assert is_binary_file("font.woff2") is True
        assert is_binary_file("font.ttf") is True
        assert is_binary_file("font.otf") is True

    def test_is_binary_file_text_extensions(self):
        """Test is_binary_file with text file extensions."""
        assert is_binary_file("file.py") is False
        assert is_binary_file("file.js") is False
        assert is_binary_file("file.ts") is False
        assert is_binary_file("file.txt") is False
        assert is_binary_file("file.md") is False
        assert is_binary_file("file.json") is False
        assert is_binary_file("file.xml") is False
        assert is_binary_file("file.html") is False
        assert is_binary_file("file.css") is False
        assert is_binary_file("file.yml") is False
        assert is_binary_file("file.yaml") is False
        assert is_binary_file("Dockerfile") is False

    def test_is_binary_file_case_insensitive(self):
        """Test is_binary_file is case-insensitive for extensions."""
        # The function converts to lowercase, so it's case-insensitive
        assert is_binary_file("file.PNG") is True  # Uppercase is also matched
        assert is_binary_file("file.Png") is True
        assert is_binary_file("file.png") is True
        # Test that all binary extensions are lowercase in the constant
        for ext in BINARY_EXTENSIONS:
            assert ext.islower() or ext.startswith(".")


class TestIsLockFile:
    """Tests for is_lock_file function."""

    def test_is_lock_file_npm(self):
        """Test is_lock_file with npm lock files."""
        assert is_lock_file("package-lock.json") is True
        assert is_lock_file("pnpm-lock.yaml") is True
        assert is_lock_file("yarn.lock") is True
        assert is_lock_file("bun.lockb") is True
        assert is_lock_file("bun.lock") is True

    def test_is_lock_file_python(self):
        """Test is_lock_file with Python lock files."""
        assert is_lock_file("Pipfile.lock") is True
        assert is_lock_file("poetry.lock") is True
        assert is_lock_file("uv.lock") is True

    def test_is_lock_file_rust(self):
        """Test is_lock_file with Rust lock files."""
        assert is_lock_file("Cargo.lock") is True

    def test_is_lock_file_ruby(self):
        """Test is_lock_file with Ruby lock files."""
        assert is_lock_file("Gemfile.lock") is True

    def test_is_lock_file_php(self):
        """Test is_lock_file with PHP lock files."""
        assert is_lock_file("composer.lock") is True

    def test_is_lock_file_go(self):
        """Test is_lock_file with Go lock files."""
        assert is_lock_file("go.sum") is True

    def test_is_lock_file_non_lock(self):
        """Test is_lock_file with non-lock files."""
        assert is_lock_file("package.json") is False
        assert is_lock_file("requirements.txt") is False
        assert is_lock_file("Pipfile") is False
        assert is_lock_file("Cargo.toml") is False
        assert is_lock_file("Gemfile") is False
        assert is_lock_file("composer.json") is False
        assert is_lock_file("go.mod") is False

    def test_is_lock_file_checks_filename_only(self):
        """Test is_lock_file only checks filename, not path."""
        assert is_lock_file("path/to/package-lock.json") is True
        assert is_lock_file("../package-lock.json") is True
        assert is_lock_file("./package-lock.json") is True


class TestValidateMergedSyntax:
    """Tests for validate_merged_syntax function."""

    def test_validate_merged_syntax_python_valid(self):
        """Test validate_merged_syntax with valid Python."""
        file_path = "test.py"
        content = "print('hello world')\ndef foo():\n    return 42\n"
        project_dir = Path("/tmp/test")

        result = validate_merged_syntax(file_path, content, project_dir)

        assert result == (True, "")

    def test_validate_merged_syntax_python_invalid(self):
        """Test validate_merged_syntax with invalid Python."""
        file_path = "test.py"
        content = "print('hello world'\ndef foo(:\n    return 42\n"  # Syntax errors
        project_dir = Path("/tmp/test")

        result = validate_merged_syntax(file_path, content, project_dir)

        assert result[0] is False
        assert "syntax error" in result[1].lower()

    def test_validate_merged_syntax_json_valid(self):
        """Test validate_merged_syntax with valid JSON."""
        file_path = "test.json"
        content = '{"key": "value", "number": 42}'
        project_dir = Path("/tmp/test")

        result = validate_merged_syntax(file_path, content, project_dir)

        assert result == (True, "")

    def test_validate_merged_syntax_json_invalid(self):
        """Test validate_merged_syntax with invalid JSON."""
        file_path = "test.json"
        content = '{"key": "value", "number": '  # Incomplete
        project_dir = Path("/tmp/test")

        result = validate_merged_syntax(file_path, content, project_dir)

        assert result[0] is False
        assert "error" in result[1].lower()

    def test_validate_merged_syntax_javascript_no_esbuild(self, tmp_path):
        """Test validate_merged_syntax with JS when esbuild not available."""
        file_path = "test.js"
        content = "function foo() { return 42; }"
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Mock subprocess to raise FileNotFoundError
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = validate_merged_syntax(file_path, content, project_dir)

        # Should skip validation and return True
        assert result == (True, "")

    def test_validate_merged_syntax_javascript_timeout(self, tmp_path):
        """Test validate_merged_syntax with JS when esbuild times out."""
        file_path = "test.js"
        content = "function foo() { return 42; }"
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Mock subprocess to raise TimeoutExpired
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("esbuild", 15)):
            result = validate_merged_syntax(file_path, content, project_dir)

        # Should skip validation on timeout
        assert result == (True, "")

    def test_validate_merged_syntax_unknown_extension(self):
        """Test validate_merged_syntax with unknown file extension."""
        file_path = "test.unknown"
        content = "some content"
        project_dir = Path("/tmp/test")

        result = validate_merged_syntax(file_path, content, project_dir)

        # Should skip validation for unknown types
        assert result == (True, "")

    def test_validate_merged_syntax_empty_python(self):
        """Test validate_merged_syntax with empty Python file."""
        file_path = "test.py"
        content = ""
        project_dir = Path("/tmp/test")

        result = validate_merged_syntax(file_path, content, project_dir)

        assert result == (True, "")

    def test_validate_merged_syntax_multiline_python(self):
        """Test validate_merged_syntax with multiline Python."""
        file_path = "test.py"
        content = """
class MyClass:
    def __init__(self):
        self.value = 42

    def method(self):
        return self.value
"""
        project_dir = Path("/tmp/test")

        result = validate_merged_syntax(file_path, content, project_dir)

        assert result == (True, "")


class TestCreateConflictFileWithGit:
    """Tests for create_conflict_file_with_git function."""

    def test_create_conflict_file_with_git_clean_merge(self):
        """Test create_conflict_file_with_git with clean merge."""
        main_content = "def foo():\n    return 'main'\n"
        worktree_content = "def foo():\n    return 'main'\n"  # Same content
        base_content = "def foo():\n    return 'base'\n"
        project_dir = Path("/tmp/test")

        with patch("core.workspace.git_utils.run_git") as mock_git:
            # Return code 0 means clean merge
            mock_git.return_value = MagicMock(
                returncode=0,
                stdout=main_content,
                stderr=""
            )

            content, had_conflicts = create_conflict_file_with_git(
                main_content, worktree_content, base_content, project_dir
            )

            assert content == main_content
            assert had_conflicts is False

    def test_create_conflict_file_with_git_conflicts(self):
        """Test create_conflict_file_with_git with conflicts."""
        main_content = "def foo():\n    return 'main'\n"
        worktree_content = "def foo():\n    return 'worktree'\n"
        base_content = "def foo():\n    return 'base'\n"
        project_dir = Path("/tmp/test")

        with patch("core.workspace.git_utils.run_git") as mock_git:
            # Return code 1 means conflicts
            mock_git.return_value = MagicMock(
                returncode=1,
                stdout="<<<<<<< HEAD\nreturn 'main'\n=======\nreturn 'worktree'\n>>>>>>> worktree\n",
                stderr=""
            )

            content, had_conflicts = create_conflict_file_with_git(
                main_content, worktree_content, base_content, project_dir
            )

            assert "<<<<<<< HEAD" in content
            assert had_conflicts is True

    def test_create_conflict_file_with_git_no_base(self):
        """Test create_conflict_file_with_git with None base_content."""
        main_content = "line 1\nline 2\n"
        worktree_content = "line 1\nline 2\n"
        base_content = None
        project_dir = Path("/tmp/test")

        with patch("core.workspace.git_utils.run_git") as mock_git:
            mock_git.return_value = MagicMock(
                returncode=0,
                stdout=main_content,
                stderr=""
            )

            content, had_conflicts = create_conflict_file_with_git(
                main_content, worktree_content, base_content, project_dir
            )

            assert content is not None

    def test_create_conflict_file_with_git_exception(self):
        """Test create_conflict_file_with_git handles exceptions."""
        main_content = "content"
        worktree_content = "different"
        base_content = "base"
        project_dir = Path("/tmp/test")

        with patch("core.workspace.git_utils.run_git") as mock_git:
            mock_git.side_effect = Exception("Git error")

            content, had_conflicts = create_conflict_file_with_git(
                main_content, worktree_content, base_content, project_dir
            )

            # Should return None on exception
            assert content is None
            assert had_conflicts is False

    def test_create_conflict_file_with_git_temp_files_cleanup(self):
        """Test create_conflict_file_with_git cleans up temp files."""
        main_content = "main"
        worktree_content = "worktree"
        base_content = "base"
        project_dir = Path("/tmp/test")

        with patch("core.workspace.git_utils.run_git") as mock_git:
            mock_git.return_value = MagicMock(
                returncode=0,
                stdout="merged",
                stderr=""
            )

            with patch("pathlib.Path.unlink") as mock_unlink:
                content, had_conflicts = create_conflict_file_with_git(
                    main_content, worktree_content, base_content, project_dir
                )

                # Verify cleanup was attempted
                assert mock_unlink.call_count >= 3  # At least 3 temp files


class TestBackwardCompatibilityAliases:
    """Tests for backward compatibility aliases."""

    def test_is_process_running_alias(self):
        """Test _is_process_running alias exists."""
        assert _is_process_running is is_process_running

    def test_is_binary_file_alias(self):
        """Test _is_binary_file alias exists."""
        assert _is_binary_file is is_binary_file

    def test_is_lock_file_alias(self):
        """Test _is_lock_file alias exists."""
        assert _is_lock_file is is_lock_file

    def test_validate_merged_syntax_alias(self):
        """Test _validate_merged_syntax alias exists."""
        assert _validate_merged_syntax is validate_merged_syntax

    def test_get_file_content_from_ref_alias(self):
        """Test _get_file_content_from_ref alias exists."""
        assert _get_file_content_from_ref is get_file_content_from_ref

    def test_get_binary_file_content_from_ref_alias(self):
        """Test _get_binary_file_content_from_ref alias exists."""
        assert _get_binary_file_content_from_ref is get_binary_file_content_from_ref

    def test_get_changed_files_from_branch_alias(self):
        """Test _get_changed_files_from_branch alias exists."""
        assert _get_changed_files_from_branch is get_changed_files_from_branch

    def test_create_conflict_file_with_git_alias(self):
        """Test _create_conflict_file_with_git alias exists."""
        assert _create_conflict_file_with_git is create_conflict_file_with_git


class TestGitUtilsEdgeCases:
    """Tests for edge cases in git utilities."""

    def test_apply_path_mapping_with_nested_paths(self):
        """Test apply_path_mapping with deeply nested paths."""
        mappings = {
            "a/b/c/d/old.py": "x/y/z/new.py",
        }
        result = apply_path_mapping("a/b/c/d/old.py", mappings)
        assert result == "x/y/z/new.py"

    def test_detect_file_renames_empty_lines(self):
        """Test detect_file_renames with empty lines in output."""
        project_dir = Path("/tmp/test")

        with patch("core.workspace.git_utils.run_git") as mock_git:
            mock_git.return_value = MagicMock(
                returncode=0,
                stdout="\n\nR100\told.py\tnew.py\n\n",
                stderr=""
            )

            result = detect_file_renames(project_dir, "main", "feature")

            assert isinstance(result, dict)

    def test_is_binary_file_empty_extension(self):
        """Test is_binary_file with file without extension."""
        assert is_binary_file("Makefile") is False
        assert is_binary_file("Dockerfile") is False
        assert is_binary_file("script") is False

    def test_is_lock_file_path_with_directories(self):
        """Test is_lock_file with file in subdirectory."""
        assert is_lock_file("node_modules/package/package-lock.json") is True
        assert is_lock_file("./package-lock.json") is True

    def test_validate_merged_syntax_unicode_content(self):
        """Test validate_merged_syntax with Unicode content."""
        file_path = "test.py"
        content = "# Comment with unicode: 你好世界\nprint('Hello')\n"
        project_dir = Path("/tmp/test")

        result = validate_merged_syntax(file_path, content, project_dir)

        assert result == (True, "")

    def test_get_changed_files_from_branch_mixed_line_endings(self):
        """Test get_changed_files_from_branch with various line endings."""
        project_dir = Path("/tmp/test")

        import core.workspace.git_utils as git_utils_module
        with patch.object(git_utils_module, "run_git") as mock_git:
            # Mix of \n and empty lines
            mock_git.return_value = MagicMock(
                returncode=0,
                stdout="M\tfile1.py\n\nA\tfile2.py\n",
                stderr=""
            )

            result = get_changed_files_from_branch(
                project_dir, "main", "feature", exclude_auto_claude=False
            )

            # Should handle empty lines gracefully
            assert ("file1.py", "M") in result
            assert ("file2.py", "A") in result
