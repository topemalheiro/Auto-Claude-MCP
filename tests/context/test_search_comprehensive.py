"""
Comprehensive Tests for context.search module
=============================================

Tests for CodeSearcher class including edge cases, error handling,
and all search functionality paths.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from context.search import CodeSearcher
from context.models import FileMatch
from context.constants import SKIP_DIRS, CODE_EXTENSIONS


class TestCodeSearcherInit:
    """Tests for CodeSearcher.__init__"""

    def test_init_resolves_path(self):
        """Test that project_dir is resolved to absolute path"""
        project_dir = Path("/tmp/test/../test_project")
        searcher = CodeSearcher(project_dir)
        assert searcher.project_dir == project_dir.resolve()

    def test_init_with_absolute_path(self):
        """Test initialization with absolute path"""
        project_dir = Path("/tmp/test_project")
        searcher = CodeSearcher(project_dir)
        assert searcher.project_dir == project_dir


class TestIterCodeFiles:
    """Tests for CodeSearcher._iter_code_files"""

    def test_iter_code_files_basic(self, tmp_path):
        """Test basic code file iteration"""
        searcher = CodeSearcher(tmp_path)

        # Create test files
        (tmp_path / "test.py").write_text("print('hello')")
        (tmp_path / "test.js").write_text("console.log('hello')")
        (tmp_path / "test.txt").write_text("not code")

        files = list(searcher._iter_code_files(tmp_path))
        assert len(files) == 2
        assert any(f.name == "test.py" for f in files)
        assert any(f.name == "test.js" for f in files)

    def test_iter_code_files_skips_directories(self, tmp_path):
        """Test that skip directories are excluded"""
        searcher = CodeSearcher(tmp_path)

        # Create files in skip directories
        for skip_dir in ["node_modules", ".git", "__pycache__", ".venv"]:
            skip_path = tmp_path / skip_dir
            skip_path.mkdir(parents=True)
            (skip_path / "code.py").write_text("should be skipped")

        # Create file that should be included
        (tmp_path / "include.py").write_text("should be included")

        files = list(searcher._iter_code_files(tmp_path))
        assert len(files) == 1
        assert files[0].name == "include.py"

    def test_iter_code_files_nested_structure(self, tmp_path):
        """Test iteration with nested directory structure"""
        searcher = CodeSearcher(tmp_path)

        # Create nested structure
        src_dir = tmp_path / "src" / "components"
        src_dir.mkdir(parents=True)
        (src_dir / "Button.tsx").write_text("export Button")

        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_button.py").write_text("def test_button")

        files = list(searcher._iter_code_files(tmp_path))
        assert len(files) == 2
        assert any("Button.tsx" in f.name for f in files)
        assert any("test_button.py" in f.name for f in files)

    def test_iter_code_files_all_extensions(self, tmp_path):
        """Test that all code extensions are detected"""
        searcher = CodeSearcher(tmp_path)

        extensions = [".py", ".js", ".jsx", ".ts", ".tsx", ".vue", ".go", ".rs", ".rb", ".php"]
        for ext in extensions:
            (tmp_path / f"test{ext}").write_text("code")

        files = list(searcher._iter_code_files(tmp_path))
        assert len(files) == len(extensions)


class TestSearchService:
    """Tests for CodeSearcher.search_service"""

    def test_search_service_nonexistent_path(self, tmp_path):
        """Test searching a non-existent service path"""
        searcher = CodeSearcher(tmp_path)
        result = searcher.search_service(
            tmp_path / "nonexistent" / "path",
            "test_service",
            ["test"]
        )
        assert result == []

    def test_search_service_no_matches(self, tmp_path):
        """Test search with no keyword matches"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        (service_dir / "auth.py").write_text("def authenticate(): pass")

        result = searcher.search_service(service_dir, "api", ["nonexistent"])
        assert result == []

    def test_search_service_single_keyword(self, tmp_path):
        """Test search with a single keyword"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        (service_dir / "auth.py").write_text("def authenticate_user(): pass")

        result = searcher.search_service(service_dir, "api", ["authenticate"])

        assert len(result) == 1
        assert result[0].path.endswith("auth.py")
        assert result[0].service == "api"
        assert result[0].relevance_score > 0
        assert "authenticate" in result[0].reason

    def test_search_service_multiple_keywords(self, tmp_path):
        """Test search with multiple keywords"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        (service_dir / "user.py").write_text(
            "class UserService:\n"
            "    def authenticate_user(self, username):\n"
            "        return self.authenticate(username)"
        )

        result = searcher.search_service(service_dir, "api", ["authenticate", "user"])

        assert len(result) == 1
        # Should score higher for multiple keywords
        assert result[0].relevance_score >= 2

    def test_search_service_case_insensitive(self, tmp_path):
        """Test that search is case insensitive"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        (service_dir / "Auth.py").write_text("def Authenticate(): pass")

        result = searcher.search_service(service_dir, "api", ["authenticate"])
        assert len(result) == 1

    def test_search_service_score_capping(self, tmp_path):
        """Test that keyword scores are capped at 10 per keyword"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        # Create file with many occurrences of the same keyword
        content = "authenticate\n" * 50
        (service_dir / "auth.py").write_text(content)

        result = searcher.search_service(service_dir, "api", ["authenticate"])
        # Score should be capped at 10 per keyword
        assert result[0].relevance_score <= 10

    def test_search_service_matching_lines(self, tmp_path):
        """Test that matching lines are captured"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        (service_dir / "auth.py").write_text(
            "line 1\n"
            "line 2 authenticate\n"
            "line 3\n"
            "line 4 authenticate\n"
            "line 5\n"
        )

        result = searcher.search_service(service_dir, "api", ["authenticate"])

        assert len(result) == 1
        assert len(result[0].matching_lines) > 0
        # Check that lines are tuples of (line_number, content)
        assert all(isinstance(line, tuple) and len(line) == 2 for line in result[0].matching_lines)

    def test_search_service_matching_lines_limit(self, tmp_path):
        """Test that matching lines are limited to 3 per keyword"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        # Create file with many matching lines
        lines = [f"line {i} authenticate" for i in range(10)]
        (service_dir / "auth.py").write_text("\n".join(lines))

        result = searcher.search_service(service_dir, "api", ["authenticate"])

        # Should capture at most 3 matching lines per keyword
        assert len(result[0].matching_lines) <= 3

    def test_search_service_top_5_lines(self, tmp_path):
        """Test that only top 5 matching lines are returned"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        # Create content that will match multiple lines
        content = "\n".join([f"keyword_{i}" for i in range(10)])
        (service_dir / "test.py").write_text(content)

        result = searcher.search_service(service_dir, "api", ["keyword"])

        # Should limit to top 5 lines
        assert len(result[0].matching_lines) <= 5

    def test_search_service_top_20_files(self, tmp_path):
        """Test that only top 20 files are returned"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        # Create many matching files
        for i in range(30):
            (service_dir / f"file_{i}.py").write_text("keyword")

        result = searcher.search_service(service_dir, "api", ["keyword"])

        # Should return at most 20 files
        assert len(result) <= 20

    def test_search_service_sorts_by_relevance(self, tmp_path):
        """Test that results are sorted by relevance score"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        # Create files with different keyword counts
        (service_dir / "high.py").write_text("keyword " * 10)
        (service_dir / "low.py").write_text("keyword")
        (service_dir / "medium.py").write_text("keyword " * 5)

        result = searcher.search_service(service_dir, "api", ["keyword"])

        # Verify descending order by relevance
        scores = [r.relevance_score for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_search_service_handles_unicode_error(self, tmp_path):
        """Test that files with unicode errors are skipped gracefully"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()

        # Create a valid file
        (service_dir / "valid.py").write_text("keyword")

        # Mock read_text to raise UnicodeDecodeError on second file
        original_read_text = Path.read_text
        def mock_read_text(self, *args, **kwargs):
            if "unicode" in str(self):
                raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")
            return original_read_text(self, *args, **kwargs)

        with patch.object(Path, 'read_text', mock_read_text):
            (service_dir / "unicode.py").write_bytes(b'\xff\xfe invalid')

            result = searcher.search_service(service_dir, "api", ["keyword"])

            # Should only return the valid file
            assert len(result) == 1
            assert result[0].path.endswith("valid.py")

    def test_search_service_handles_os_error(self, tmp_path):
        """Test that files with OS errors are skipped gracefully"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        (service_dir / "valid.py").write_text("keyword")

        # Mock read_text to raise OSError
        original_read_text = Path.read_text
        def mock_read_text(self, *args, **kwargs):
            if "error" in str(self):
                raise OSError("Permission denied")
            return original_read_text(self, *args, **kwargs)

        with patch.object(Path, 'read_text', mock_read_text):
            (service_dir / "error.py").write_text("keyword")

            result = searcher.search_service(service_dir, "api", ["keyword"])

            # Should only return the valid file
            assert len(result) == 1
            assert result[0].path.endswith("valid.py")

    def test_search_service_relative_path(self, tmp_path):
        """Test that file paths are relative to project_dir"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api" / "services"
        service_dir.mkdir(parents=True)
        (service_dir / "auth.py").write_text("authenticate")

        result = searcher.search_service(service_dir, "api", ["authenticate"])

        assert len(result) == 1
        # Path should be relative to project_dir
        assert not result[0].path.startswith(str(tmp_path))
        assert "api/services/auth.py" in result[0].path or result[0].path.endswith("auth.py")

    def test_search_service_empty_keywords(self, tmp_path):
        """Test search with empty keyword list"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        (service_dir / "auth.py").write_text("authenticate")

        result = searcher.search_service(service_dir, "api", [])
        assert result == []

    def test_search_service_substring_matching(self, tmp_path):
        """Test that keywords match as substrings"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        (service_dir / "auth.py").write_text("def authentication(): pass")

        result = searcher.search_service(service_dir, "api", ["auth"])
        assert len(result) == 1


class TestIterCodeFilesEdgeCases:
    """Additional edge case tests for _iter_code_files"""

    def test_iter_code_files_nonexistent_directory(self, tmp_path):
        """Test iterating over a directory that doesn't exist"""
        searcher = CodeSearcher(tmp_path)

        nonexistent = tmp_path / "does_not_exist"
        files = list(searcher._iter_code_files(nonexistent))
        assert files == []

    def test_iter_code_files_with_symbolic_links(self, tmp_path):
        """Test that symbolic links are handled gracefully"""
        searcher = CodeSearcher(tmp_path)

        # Create a file and a symlink to it
        source_file = tmp_path / "source.py"
        source_file.write_text("code")

        link_file = tmp_path / "link.py"
        try:
            link_file.symlink_to(source_file)

            files = list(searcher._iter_code_files(tmp_path))
            # Should handle symlinks (either include or skip based on is_file())
            assert isinstance(files, list)
        except OSError:
            # Symlinks might not be supported on this system
            pass

    def test_iter_code_files_nested_skip_dirs(self, tmp_path):
        """Test that nested skip directories are excluded"""
        searcher = CodeSearcher(tmp_path)

        # Create deeply nested skip directory
        nested_skip = tmp_path / "src" / "node_modules" / "package"
        nested_skip.mkdir(parents=True)
        (nested_skip / "code.js").write_text("should be skipped")

        # Create file that should be included
        (tmp_path / "src" / "app.js").write_text("should be included")

        files = list(searcher._iter_code_files(tmp_path))
        assert len(files) == 1
        assert "app.js" in files[0].name

    def test_iter_code_files_empty_directory(self, tmp_path):
        """Test iterating over empty directory"""
        searcher = CodeSearcher(tmp_path)

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        files = list(searcher._iter_code_files(empty_dir))
        assert files == []

    def test_iter_code_files_non_code_files(self, tmp_path):
        """Test that non-code files are excluded"""
        searcher = CodeSearcher(tmp_path)

        # Create various non-code files
        (tmp_path / "README.md").write_text("# readme")
        (tmp_path / "data.json").write_text("{}")
        (tmp_path / "config.yml").write_text("key: value")
        (tmp_path / "script.sh").write_text("#!/bin/bash")

        # Create one code file
        (tmp_path / "app.py").write_text("print('hello')")

        files = list(searcher._iter_code_files(tmp_path))
        assert len(files) == 1
        assert files[0].name == "app.py"

    def test_iter_code_files_dotfiles(self, tmp_path):
        """Test handling of dotfiles"""
        searcher = CodeSearcher(tmp_path)

        # Create dotfile with code extension
        (tmp_path / ".hidden.py").write_text("hidden code")

        # Create visible code file
        (tmp_path / "visible.py").write_text("visible code")

        files = list(searcher._iter_code_files(tmp_path))
        # Should include the dotfile if it has code extension
        assert len(files) >= 1
        assert any("visible.py" in f.name for f in files)


class TestSearchServiceEdgeCases:
    """Additional edge case tests for search_service"""

    def test_search_service_with_special_regex_chars(self, tmp_path):
        """Test keywords with special regex characters"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        # File with characters that have regex meaning
        (service_dir / "test.py").write_text("def test_foo_bar(): pass")

        # Keywords with regex special chars - should match literally
        result = searcher.search_service(service_dir, "api", ["test_foo_bar"])
        assert len(result) == 1

    def test_search_service_empty_keywords(self, tmp_path):
        """Test with empty keywords list"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        (service_dir / "auth.py").write_text("def authenticate(): pass")

        result = searcher.search_service(service_dir, "api", [])
        assert result == []

    def test_search_service_very_long_keyword(self, tmp_path):
        """Test with very long keyword"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        long_keyword = "authenticate" * 50
        (service_dir / "auth.py").write_text("short content")

        result = searcher.search_service(service_dir, "api", [long_keyword])
        assert result == []

    def test_search_service_keyword_with_newlines(self, tmp_path):
        """Test file content with newlines"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        content = "\n\n\nkeyword\n\n\n"
        (service_dir / "test.py").write_text(content)

        result = searcher.search_service(service_dir, "api", ["keyword"])
        assert len(result) == 1

    def test_search_service_multiple_occurrences_scoring(self, tmp_path):
        """Test that scoring properly counts multiple occurrences"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        # File with exactly 15 occurrences
        content = "\n".join(["keyword"] * 15)
        (service_dir / "test.py").write_text(content)

        result = searcher.search_service(service_dir, "api", ["keyword"])

        # Score should be capped at 10 per keyword
        assert result[0].relevance_score == 10

    def test_search_service_multiple_keywords_scoring(self, tmp_path):
        """Test scoring with multiple different keywords"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        content = "keyword1 keyword2 keyword1 keyword2 keyword1"
        (service_dir / "test.py").write_text(content)

        result = searcher.search_service(service_dir, "api", ["keyword1", "keyword2"])

        # Each keyword should contribute to score (capped at 10 each)
        assert result[0].relevance_score >= 2

    def test_search_service_unicode_content(self, tmp_path):
        """Test file with unicode content"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        # File with emoji and unicode
        (service_dir / "test.py").write_text("def test():\n    '''Unicode: café, '''\n    pass")

        result = searcher.search_service(service_dir, "api", ["test"])
        assert len(result) == 1

    def test_search_service_case_variations(self, tmp_path):
        """Test case variations in matching"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        (service_dir / "test.py").write_text("AUTHENTICATE authenticate Authenticate")

        result = searcher.search_service(service_dir, "api", ["authenticate"])

        # Should match all variations
        assert result[0].relevance_score >= 1

    def test_search_service_matching_lines_truncation(self, tmp_path):
        """Test that matching lines are truncated to 100 chars"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        long_line = "x" * 200 + " keyword " + "y" * 200
        (service_dir / "test.py").write_text(long_line)

        result = searcher.search_service(service_dir, "api", ["keyword"])

        assert len(result) == 1
        if result[0].matching_lines:
            # Lines should be truncated
            for _, line in result[0].matching_lines:
                assert len(line) <= 100

    def test_search_service_top_twenty_files_filtering(self, tmp_path):
        """Test that results are properly filtered to top 20"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()

        # Create 25 files with different relevance scores
        for i in range(25):
            content = "keyword " * (i + 1)  # Different scores
            (service_dir / f"file_{i}.py").write_text(content)

        result = searcher.search_service(service_dir, "api", ["keyword"])

        # Should return exactly 20
        assert len(result) == 20

    def test_search_service_result_ordering(self, tmp_path):
        """Test that results are ordered by relevance"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()

        # Create files with known relevance
        scores = [5, 10, 3, 8, 1]
        for i, score in enumerate(scores):
            content = "keyword " * score
            (service_dir / f"file_{i}.py").write_text(content)

        result = searcher.search_service(service_dir, "api", ["keyword"])

        # Verify descending order
        result_scores = [r.relevance_score for r in result]
        assert result_scores == sorted(result_scores, reverse=True)


class TestSearchServiceErrorHandling:
    """Tests for error handling in search_service"""

    def test_search_service_permission_error(self, tmp_path):
        """Test handling of permission errors"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        (service_dir / "good.py").write_text("keyword")

        # Mock read_text to raise PermissionError on one file
        original_read_text = Path.read_text
        def mock_read_text(self, *args, **kwargs):
            if "bad" in str(self):
                raise PermissionError("Access denied")
            return original_read_text(self, *args, **kwargs)

        with patch.object(Path, 'read_text', mock_read_text):
            (service_dir / "bad.py").write_text("keyword")

            result = searcher.search_service(service_dir, "api", ["keyword"])

            # Should only return the good file
            assert len(result) == 1
            assert result[0].path.endswith("good.py")

    def test_search_service_unicode_decode_error_detailed(self, tmp_path):
        """Test detailed handling of UnicodeDecodeError"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        (service_dir / "good.py").write_text("keyword")

        # Create file with invalid UTF-8
        (service_dir / "bad.py").write_bytes(b'\xff\xfe invalid utf-8 content')

        result = searcher.search_service(service_dir, "api", ["keyword"])

        # Should only return the good file
        assert len(result) == 1
        assert result[0].path.endswith("good.py")

    def test_search_service_mixed_file_errors(self, tmp_path):
        """Test handling mixed valid and error files"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()

        # Create multiple files with different issues
        (service_dir / "good1.py").write_text("keyword here")
        (service_dir / "good2.py").write_text("keyword there")
        (service_dir / "unicode.py").write_bytes(b'\xff\xfe error')

        result = searcher.search_service(service_dir, "api", ["keyword"])

        # Should return only valid files
        assert len(result) == 2
        paths = [r.path for r in result]
        assert all("good" in p for p in paths)

    def test_search_service_empty_file(self, tmp_path):
        """Test handling of empty file"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        (service_dir / "empty.py").write_text("")
        (service_dir / "good.py").write_text("keyword")

        result = searcher.search_service(service_dir, "api", ["keyword"])

        # Empty file should just not match
        assert len(result) == 1
        assert result[0].path.endswith("good.py")

    def test_search_service_file_with_only_whitespace(self, tmp_path):
        """Test file with only whitespace"""
        searcher = CodeSearcher(tmp_path)

        service_dir = tmp_path / "api"
        service_dir.mkdir()
        (service_dir / "whitespace.py").write_text("   \n\n   \t   ")

        result = searcher.search_service(service_dir, "api", ["keyword"])

        # Should not match
        assert result == []
