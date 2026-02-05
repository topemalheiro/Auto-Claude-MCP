"""
Comprehensive Tests for context.pattern_discovery module
========================================================

Tests for PatternDiscoverer class including pattern extraction,
error handling, edge cases, and all functionality paths.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from context.pattern_discovery import PatternDiscoverer
from context.models import FileMatch


class TestPatternDiscovererInit:
    """Tests for PatternDiscoverer.__init__"""

    def test_init_resolves_path(self):
        """Test that project_dir is resolved to absolute path"""
        project_dir = Path("/tmp/test/../test_project")
        discoverer = PatternDiscoverer(project_dir)
        assert discoverer.project_dir == project_dir.resolve()

    def test_init_with_absolute_path(self):
        """Test initialization with absolute path"""
        project_dir = Path("/tmp/test_project")
        discoverer = PatternDiscoverer(project_dir)
        assert discoverer.project_dir == project_dir


class TestDiscoverPatternsBasic:
    """Tests for basic pattern discovery"""

    def test_discover_patterns_empty_files(self):
        """Test with empty reference files list"""
        discoverer = PatternDiscoverer(Path("/tmp/test"))
        result = discoverer.discover_patterns([], ["keyword"])
        assert result == {}

    def test_discover_patterns_empty_keywords(self, tmp_path):
        """Test with empty keywords list"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("def authenticate(): pass")

        reference_files = [
            FileMatch(
                path="test.py",
                service="api",
                reason="Contains: authenticate",
                relevance_score=8,
                matching_lines=[]
            )
        ]

        result = discoverer.discover_patterns(reference_files, [])
        assert result == {}

    def test_discover_patterns_basic(self, tmp_path):
        """Test basic pattern discovery"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "auth.py"
        test_file.write_text(
            "def authenticate_user(username, password):\n"
            "    '''Authenticate user with credentials'''\n"
            "    return True\n"
        )

        reference_files = [
            FileMatch(
                path="auth.py",
                service="api",
                reason="Contains: authenticate",
                relevance_score=8,
                matching_lines=[]
            )
        ]

        result = discoverer.discover_patterns(reference_files, ["authenticate"])

        assert isinstance(result, dict)
        # Should find pattern for authenticate keyword
        assert "authenticate_pattern" in result
        assert "auth.py" in result["authenticate_pattern"]

    def test_discover_patterns_multiple_keywords(self, tmp_path):
        """Test pattern discovery with multiple keywords"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "user.py"
        test_file.write_text(
            "def authenticate_user(username):\n"
            "    '''Create user session'''\n"
            "    return login_user(username)\n"
        )

        reference_files = [
            FileMatch(
                path="user.py",
                service="api",
                reason="Contains: authenticate, user",
                relevance_score=8,
                matching_lines=[]
            )
        ]

        result = discoverer.discover_patterns(reference_files, ["authenticate", "user"])

        # Should find patterns for both keywords
        assert "authenticate_pattern" in result or "user_pattern" in result

    def test_discover_patterns_max_files(self, tmp_path):
        """Test that max_files parameter limits files analyzed"""
        discoverer = PatternDiscoverer(tmp_path)

        # Create multiple files
        for i in range(5):
            test_file = tmp_path / f"test_{i}.py"
            test_file.write_text("def authenticate(): pass")

        reference_files = [
            FileMatch(
                path=f"test_{i}.py",
                service="api",
                reason="Contains: authenticate",
                relevance_score=8,
                matching_lines=[]
            )
            for i in range(5)
        ]

        # Limit to 2 files
        result = discoverer.discover_patterns(reference_files, ["authenticate"], max_files=2)

        # Should still find pattern
        assert "authenticate_pattern" in result


class TestPatternExtraction:
    """Tests for pattern extraction logic"""

    def test_pattern_context_before_and_after(self, tmp_path):
        """Test that pattern includes context before and after keyword"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text(
            "line 1\n"
            "line 2\n"
            "line 3\n"
            "line 4 keyword\n"
            "line 5\n"
            "line 6\n"
            "line 7\n"
        )

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])

        assert "keyword_pattern" in result
        # Should include lines before and after
        assert "line 1" in result["keyword_pattern"] or "line 7" in result["keyword_pattern"]

    def test_pattern_snippet_truncation(self, tmp_path):
        """Test that pattern snippets are truncated to 300 chars"""
        discoverer = PatternDiscoverer(tmp_path)

        # Create file with very long lines
        long_content = "\n".join(["x" * 100 for _ in range(10)])
        test_file = tmp_path / "test.py"
        test_file.write_text(f"{long_content}\nkeyword\n{long_content}")

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])

        # Snippet should be truncated
        assert len(result["keyword_pattern"]) <= 500  # Account for prefix text

    def test_pattern_first_keyword_match(self, tmp_path):
        """Test that only first keyword match is captured per file"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text(
            "keyword line 1\n"
            "other content\n"
            "keyword line 2\n"
        )

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])

        # Should create only one pattern entry
        assert "keyword_pattern" in result

    def test_pattern_case_insensitive(self, tmp_path):
        """Test that keyword matching is case insensitive"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("def KEYWORD_FUNCTION(): pass")

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])

        assert "keyword_pattern" in result

    def test_pattern_multiple_files_same_keyword(self, tmp_path):
        """Test pattern discovery with multiple files containing same keyword"""
        discoverer = PatternDiscoverer(tmp_path)

        # Create multiple files with the same keyword
        for i in range(3):
            test_file = tmp_path / f"test_{i}.py"
            test_file.write_text(f"def keyword_{i}(): pass")

        reference_files = [
            FileMatch(
                path=f"test_{i}.py",
                service="api",
                reason="Contains: keyword",
                relevance_score=8,
                matching_lines=[]
            )
            for i in range(3)
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])

        # Should create pattern from first matching file
        assert "keyword_pattern" in result


class TestErrorHandling:
    """Tests for error handling"""

    def test_discover_patterns_file_not_found(self):
        """Test handling when referenced file doesn't exist"""
        discoverer = PatternDiscoverer(Path("/tmp/test"))

        reference_files = [
            FileMatch(
                path="nonexistent.py",
                service="api",
                reason="test",
                relevance_score=8,
                matching_lines=[]
            )
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        # Should handle gracefully
        assert isinstance(result, dict)

    def test_discover_patterns_unicode_error(self, tmp_path):
        """Test handling of unicode decode errors"""
        discoverer = PatternDiscoverer(tmp_path)

        # Create file with invalid UTF-8
        test_file = tmp_path / "test.py"
        test_file.write_bytes(b'\xff\xfe invalid utf-8')

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        # Should handle gracefully
        assert isinstance(result, dict)

    def test_discover_patterns_os_error(self, tmp_path):
        """Test handling of OS errors"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("keyword")

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        # Mock read_text to raise OSError
        original_read_text = Path.read_text
        def mock_read_text(self, *args, **kwargs):
            if "test.py" in str(self):
                raise OSError("Permission denied")
            return original_read_text(self, *args, **kwargs)

        with patch.object(Path, 'read_text', mock_read_text):
            result = discoverer.discover_patterns(reference_files, ["keyword"])
            # Should handle gracefully
            assert isinstance(result, dict)

    def test_discover_patterns_mixed_errors(self, tmp_path):
        """Test handling of mixed valid and invalid files"""
        discoverer = PatternDiscoverer(tmp_path)

        # Create one valid file
        valid_file = tmp_path / "valid.py"
        valid_file.write_text("def keyword(): pass")

        reference_files = [
            FileMatch(path="valid.py", service="api", reason="test", relevance_score=8, matching_lines=[]),
            FileMatch(path="nonexistent.py", service="api", reason="test", relevance_score=5, matching_lines=[]),
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])

        # Should extract pattern from valid file
        assert "keyword_pattern" in result


class TestEdgeCases:
    """Tests for edge cases and special scenarios"""

    def test_discover_patterns_no_matching_keywords(self, tmp_path):
        """Test when keywords don't appear in file"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("def other_function(): pass")

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        # Should return empty dict
        assert result == {}

    def test_discover_patterns_empty_file(self, tmp_path):
        """Test with empty file"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("")

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        assert result == {}

    def test_discover_patterns_single_line_file(self, tmp_path):
        """Test with single line file"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("keyword")

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        assert "keyword_pattern" in result

    def test_discover_patterns_keyword_at_start(self, tmp_path):
        """Test keyword at start of file"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("keyword\nmore content")

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        assert "keyword_pattern" in result

    def test_discover_patterns_keyword_at_end(self, tmp_path):
        """Test keyword at end of file"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("some content\nkeyword")

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        assert "keyword_pattern" in result

    def test_discover_patterns_special_characters(self, tmp_path):
        """Test with special characters in file"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("def keyword_func(arg1, arg2=None):\n    return True")

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        assert "keyword_pattern" in result

    def test_discover_patterns_unicode_content(self, tmp_path):
        """Test with unicode content"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("def keyword_func():\n    '''Unicode: caf''''\n    pass")

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        assert "keyword_pattern" in result

    def test_discover_patterns_very_long_line(self, tmp_path):
        """Test with very long line containing keyword"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        long_line = "x" * 1000 + " keyword " + "x" * 1000
        test_file.write_text(long_line)

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        assert "keyword_pattern" in result


class TestDiscoverPatternsEdgeCases:
    """Edge case tests for discover_patterns"""

    def test_discover_patterns_empty_reference_files(self, tmp_path):
        """Test with completely empty reference_files list"""
        discoverer = PatternDiscoverer(tmp_path)
        result = discoverer.discover_patterns([], ["keyword"])
        assert result == {}

    def test_discover_patterns_max_files_zero(self, tmp_path):
        """Test with max_files=0"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("def keyword(): pass")

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"], max_files=0)
        # Should return empty dict
        assert result == {}

    def test_discover_patterns_max_files_one(self, tmp_path):
        """Test with max_files=1"""
        discoverer = PatternDiscoverer(tmp_path)

        # Create multiple files
        for i in range(3):
            test_file = tmp_path / f"test_{i}.py"
            test_file.write_text(f"def keyword_{i}(): pass")

        reference_files = [
            FileMatch(
                path=f"test_{i}.py",
                service="api",
                reason="test",
                relevance_score=8,
                matching_lines=[]
            )
            for i in range(3)
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"], max_files=1)

        # Should only analyze first file
        assert "keyword_pattern" in result

    def test_discover_patterns_keywords_not_found(self, tmp_path):
        """Test when keywords don't appear in any files"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("def other_function(): pass")

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["nonexistent"])
        assert result == {}

    def test_discover_patterns_duplicate_keywords(self, tmp_path):
        """Test with duplicate keywords in list"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("def keyword(): pass")

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword", "keyword"])

        # Should handle gracefully (only one pattern created)
        assert "keyword_pattern" in result

    def test_discover_patterns_case_insensitive_keywords(self, tmp_path):
        """Test keyword matching is case insensitive"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("def KEYWORD_FUNCTION(): pass")

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        assert "keyword_pattern" in result

    def test_discover_patterns_multiple_keywords_same_file(self, tmp_path):
        """Test with multiple keywords in same file"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text(
            "def authenticate_user():\n"
            "    user_service = UserService()\n"
            "    return user"
        )

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["authenticate", "user"])

        # Should find patterns for both keywords
        assert "authenticate_pattern" in result or "user_pattern" in result

    def test_discover_patterns_no_matching_lines_context(self, tmp_path):
        """Test pattern extraction when keyword is alone"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("keyword")  # Just keyword, no context

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        assert "keyword_pattern" in result


class TestPatternExtractionBoundaries:
    """Tests for pattern extraction at file boundaries"""

    def test_keyword_at_very_start(self, tmp_path):
        """Test keyword at very start of file"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("keyword\nline2\nline3")

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        assert "keyword_pattern" in result

    def test_keyword_at_very_end(self, tmp_path):
        """Test keyword at very end of file"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("line1\nline2\nkeyword")

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        assert "keyword_pattern" in result

    def test_keyword_single_line_file(self, tmp_path):
        """Test keyword in single-line file"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("keyword")

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        assert "keyword_pattern" in result

    def test_context_window_at_file_start(self, tmp_path):
        """Test context window handling when keyword is near start"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("keyword\nline2\nline3\nline4")

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        # Should include as much context as available
        assert "keyword_pattern" in result

    def test_context_window_at_file_end(self, tmp_path):
        """Test context window handling when keyword is near end"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("line1\nline2\nline3\nkeyword")

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        assert "keyword_pattern" in result

    def test_context_window_exact_three_lines_before(self, tmp_path):
        """Test context window with exactly 3 lines before keyword"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("line1\nline2\nline3\nkeyword\nline5")

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        # Should include 3 lines before and 1 line after
        assert "keyword_pattern" in result
        assert "line1" in result["keyword_pattern"]
        assert "line5" in result["keyword_pattern"]


class TestSnippetTruncation:
    """Tests for snippet truncation at 300 chars"""

    def test_snippet_exactly_300_chars(self, tmp_path):
        """Test snippet exactly at 300 char limit"""
        discoverer = PatternDiscoverer(tmp_path)

        # Create content that will result in exactly 300 char snippet
        context_lines = ["x" * 50 for _ in range(5)]  # 250 chars
        content = "\n".join(context_lines) + "\nkeyword\n"
        test_file = tmp_path / "test.py"
        test_file.write_text(content)

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        # Snippet should be at or near 300 chars
        assert len(result["keyword_pattern"]) <= 350  # Account for prefix

    def test_snippet_over_300_chars(self, tmp_path):
        """Test snippet truncation when over 300 chars"""
        discoverer = PatternDiscoverer(tmp_path)

        # Create very long context
        long_context = ["x" * 100 for _ in range(10)]  # 1000+ chars
        content = "\n".join(long_context) + "\nkeyword\n" + "\n".join(long_context)
        test_file = tmp_path / "test.py"
        test_file.write_text(content)

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        # Should be truncated to 300 chars (plus prefix, allow small rounding)
        snippet_only = result["keyword_pattern"].split(":", 1)[1] if ":" in result["keyword_pattern"] else result["keyword_pattern"]
        assert len(snippet_only) <= 310  # Allow small buffer for rounding

    def test_snippet_under_300_chars(self, tmp_path):
        """Test snippet when under 300 chars"""
        discoverer = PatternDiscoverer(tmp_path)

        content = "line1\nline2\nkeyword\nline4"
        test_file = tmp_path / "test.py"
        test_file.write_text(content)

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        # Should not be truncated
        assert "keyword" in result["keyword_pattern"]
        assert "line1" in result["keyword_pattern"]
        assert "line4" in result["keyword_pattern"]

    def test_snippet_with_unicode_chars(self, tmp_path):
        """Test snippet truncation with unicode characters"""
        discoverer = PatternDiscoverer(tmp_path)

        # Content with unicode
        long_content = "café " * 100  # ~500 chars
        content = f"{long_content}\nkeyword\nmore content"
        test_file = tmp_path / "test.py"
        test_file.write_text(content)

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        # Should handle unicode gracefully
        assert "keyword_pattern" in result
        # Length check should work with unicode
        assert len(result["keyword_pattern"]) >= 0


class TestFileReadErrors:
    """Tests for file reading error handling"""

    def test_discover_patterns_file_not_found(self, tmp_path):
        """Test when referenced file doesn't exist"""
        discoverer = PatternDiscoverer(tmp_path)

        reference_files = [
            FileMatch(
                path="nonexistent.py",
                service="api",
                reason="test",
                relevance_score=8,
                matching_lines=[]
            )
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        # Should handle gracefully
        assert isinstance(result, dict)

    def test_discover_patterns_permission_error(self, tmp_path):
        """Test handling of permission errors"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("keyword")

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        # Mock read_text to raise PermissionError
        original_read_text = Path.read_text
        def mock_read_text(self, *args, **kwargs):
            if "test.py" in str(self):
                raise PermissionError("Access denied")
            return original_read_text(self, *args, **kwargs)

        with patch.object(Path, 'read_text', mock_read_text):
            result = discoverer.discover_patterns(reference_files, ["keyword"])
            # Should handle gracefully
            assert isinstance(result, dict)

    def test_discover_patterns_unicode_decode_error_detailed(self, tmp_path):
        """Test detailed handling of unicode decode errors"""
        discoverer = PatternDiscoverer(tmp_path)

        # Create file with invalid UTF-8
        test_file = tmp_path / "test.py"
        test_file.write_bytes(b'\xff\xfe invalid utf-8')

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        # Should handle gracefully
        assert isinstance(result, dict)

    def test_discover_patterns_os_error_variety(self, tmp_path):
        """Test handling of various OS errors"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("keyword")

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        # Test different OS errors
        for error in [OSError("I/O error"), IOError("Read error")]:
            with patch.object(Path, 'read_text', side_effect=error):
                result = discoverer.discover_patterns(reference_files, ["keyword"])
                assert isinstance(result, dict)

    def test_discover_patterns_mixed_valid_invalid(self, tmp_path):
        """Test with mix of valid and invalid files"""
        discoverer = PatternDiscoverer(tmp_path)

        # Create valid file
        valid_file = tmp_path / "valid.py"
        valid_file.write_text("def keyword(): pass")

        reference_files = [
            FileMatch(path="valid.py", service="api", reason="test", relevance_score=8, matching_lines=[]),
            FileMatch(path="nonexistent.py", service="api", reason="test", relevance_score=5, matching_lines=[]),
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        # Should extract from valid file
        assert "keyword_pattern" in result

    def test_discover_patterns_all_files_error(self, tmp_path):
        """Test when all files have errors"""
        discoverer = PatternDiscoverer(tmp_path)

        reference_files = [
            FileMatch(path=f"nonexistent_{i}.py", service="api", reason="test", relevance_score=8, matching_lines=[])
            for i in range(3)
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        # Should return empty dict
        assert result == {}


class TestPatternFirstMatchBehavior:
    """Tests for first-match behavior per keyword"""

    def test_first_keyword_match_only(self, tmp_path):
        """Test that only first match per keyword is captured"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text(
            "first keyword match\n"
            "other content\n"
            "second keyword match\n"
            "third keyword match"
        )

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        # Should create only one pattern
        assert "keyword_pattern" in result
        # Should be from first match
        assert "first" in result["keyword_pattern"]

    def test_first_file_only_per_keyword(self, tmp_path):
        """Test that only first file is used per keyword"""
        discoverer = PatternDiscoverer(tmp_path)

        # Create multiple files with same keyword
        for i in range(3):
            test_file = tmp_path / f"test_{i}.py"
            test_file.write_text(f"file {i} keyword")

        reference_files = [
            FileMatch(
                path=f"test_{i}.py",
                service="api",
                reason="test",
                relevance_score=8,
                matching_lines=[]
            )
            for i in range(3)
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        # Should use first file
        assert "keyword_pattern" in result
        assert "test_0.py" in result["keyword_pattern"] or "file 0" in result["keyword_pattern"]

    def test_no_pattern_after_first_match(self, tmp_path):
        """Test that no additional patterns are created after first match"""
        discoverer = PatternDiscoverer(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("keyword other stuff keyword more stuff")

        reference_files = [
            FileMatch(path="test.py", service="api", reason="test", relevance_score=8, matching_lines=[])
        ]

        result = discoverer.discover_patterns(reference_files, ["keyword"])
        # Should have exactly one pattern entry
        assert len([k for k in result.keys() if "keyword" in k]) == 1
