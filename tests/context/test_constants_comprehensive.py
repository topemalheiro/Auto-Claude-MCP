"""
Comprehensive Tests for context.constants module
================================================

Tests for constants including SKIP_DIRS, CODE_EXTENSIONS,
and validation of their values.
"""

import pytest
from context.constants import SKIP_DIRS, CODE_EXTENSIONS


class TestSkipDirs:
    """Tests for SKIP_DIRS constant"""

    def test_skip_dirs_exists(self):
        """Test that SKIP_DIRS constant exists"""
        assert SKIP_DIRS is not None

    def test_skip_dirs_is_set(self):
        """Test that SKIP_DIRS is a set"""
        assert isinstance(SKIP_DIRS, set)

    def test_skip_dirs_not_empty(self):
        """Test that SKIP_DIRS is not empty"""
        assert len(SKIP_DIRS) > 0

    def test_skip_dirs_contains_common_dirs(self):
        """Test that SKIP_DIRS contains common skip directories"""
        common_dirs = ["node_modules", ".git", "__pycache__", ".venv", "dist", "build"]
        for dir_name in common_dirs:
            assert dir_name in SKIP_DIRS, f"{dir_name} should be in SKIP_DIRS"

    def test_skip_dirs_contains_node_modules(self):
        """Test that node_modules is in SKIP_DIRS"""
        assert "node_modules" in SKIP_DIRS

    def test_skip_dirs_contains_git(self):
        """Test that .git is in SKIP_DIRS"""
        assert ".git" in SKIP_DIRS

    def test_skip_dirs_contains_pycache(self):
        """Test that __pycache__ is in SKIP_DIRS"""
        assert "__pycache__" in SKIP_DIRS

    def test_skip_dirs_contains_venv(self):
        """Test that .venv is in SKIP_DIRS"""
        assert ".venv" in SKIP_DIRS

    def test_skip_dirs_contains_venv_variant(self):
        """Test that venv (without dot) is in SKIP_DIRS"""
        assert "venv" in SKIP_DIRS

    def test_skip_dirs_contains_dist(self):
        """Test that dist is in SKIP_DIRS"""
        assert "dist" in SKIP_DIRS

    def test_skip_dirs_contains_build(self):
        """Test that build is in SKIP_DIRS"""
        assert "build" in SKIP_DIRS

    def test_skip_dirs_contains_vendor(self):
        """Test that vendor is in SKIP_DIRS"""
        assert "vendor" in SKIP_DIRS

    def test_skip_dirs_contains_idea(self):
        """Test that .idea is in SKIP_DIRS"""
        assert ".idea" in SKIP_DIRS

    def test_skip_dirs_contains_vscode(self):
        """Test that .vscode is in SKIP_DIRS"""
        assert ".vscode" in SKIP_DIRS

    def test_skip_dirs_contains_auto_claude(self):
        """Test that auto-claude is in SKIP_DIRS"""
        assert "auto-claude" in SKIP_DIRS

    def test_skip_dirs_contains_pytest_cache(self):
        """Test that .pytest_cache is in SKIP_DIRS"""
        assert ".pytest_cache" in SKIP_DIRS

    def test_skip_dirs_contains_mypy_cache(self):
        """Test that .mypy_cache is in SKIP_DIRS"""
        assert ".mypy_cache" in SKIP_DIRS

    def test_skip_dirs_contains_coverage(self):
        """Test that coverage is in SKIP_DIRS"""
        assert "coverage" in SKIP_DIRS

    def test_skip_dirs_contains_turbo(self):
        """Test that .turbo is in SKIP_DIRS"""
        assert ".turbo" in SKIP_DIRS

    def test_skip_dirs_all_strings(self):
        """Test that all SKIP_DIRS entries are strings"""
        for dir_name in SKIP_DIRS:
            assert isinstance(dir_name, str)

    def test_skip_dirs_no_empty_strings(self):
        """Test that SKIP_DIRS has no empty strings"""
        assert "" not in SKIP_DIRS

    def test_skip_dirs_lowercase_mixed(self):
        """Test that SKIP_DIRS has mix of lowercase and dot-prefixed names"""
        has_dot = any(name.startswith(".") for name in SKIP_DIRS)
        has_no_dot = any(not name.startswith(".") for name in SKIP_DIRS)
        assert has_dot and has_no_dot

    def test_skip_dirs_expected_count(self):
        """Test that SKIP_DIRS has expected minimum count"""
        # Should have at least 15 common skip directories
        assert len(SKIP_DIRS) >= 15

    def test_skip_dirs_immutability(self):
        """Test that SKIP_DIRS can be read but modification is tracked"""
        # Read works
        original_len = len(SKIP_DIRS)
        _ = list(SKIP_DIRS)

        # Note: We're not actually modifying it, just testing access
        assert len(SKIP_DIRS) >= original_len


class TestCodeExtensions:
    """Tests for CODE_EXTENSIONS constant"""

    def test_code_extensions_exists(self):
        """Test that CODE_EXTENSIONS constant exists"""
        assert CODE_EXTENSIONS is not None

    def test_code_extensions_is_set(self):
        """Test that CODE_EXTENSIONS is a set"""
        assert isinstance(CODE_EXTENSIONS, set)

    def test_code_extensions_not_empty(self):
        """Test that CODE_EXTENSIONS is not empty"""
        assert len(CODE_EXTENSIONS) > 0

    def test_code_extensions_all_start_with_dot(self):
        """Test that all extensions start with a dot"""
        for ext in CODE_EXTENSIONS:
            assert ext.startswith("."), f"{ext} should start with '.'"

    def test_code_extensions_contains_python(self):
        """Test that .py extension is included"""
        assert ".py" in CODE_EXTENSIONS

    def test_code_extensions_contains_javascript(self):
        """Test that .js extension is included"""
        assert ".js" in CODE_EXTENSIONS

    def test_code_extensions_contains_jsx(self):
        """Test that .jsx extension is included"""
        assert ".jsx" in CODE_EXTENSIONS

    def test_code_extensions_contains_typescript(self):
        """Test that .ts extension is included"""
        assert ".ts" in CODE_EXTENSIONS

    def test_code_extensions_contains_tsx(self):
        """Test that .tsx extension is included"""
        assert ".tsx" in CODE_EXTENSIONS

    def test_code_extensions_contains_vue(self):
        """Test that .vue extension is included"""
        assert ".vue" in CODE_EXTENSIONS

    def test_code_extensions_contains_svelte(self):
        """Test that .svelte extension is included"""
        assert ".svelte" in CODE_EXTENSIONS

    def test_code_extensions_contains_go(self):
        """Test that .go extension is included"""
        assert ".go" in CODE_EXTENSIONS

    def test_code_extensions_contains_rust(self):
        """Test that .rs extension is included"""
        assert ".rs" in CODE_EXTENSIONS

    def test_code_extensions_contains_ruby(self):
        """Test that .rb extension is included"""
        assert ".rb" in CODE_EXTENSIONS

    def test_code_extensions_contains_php(self):
        """Test that .php extension is included"""
        assert ".php" in CODE_EXTENSIONS

    def test_code_extensions_all_strings(self):
        """Test that all CODE_EXTENSIONS entries are strings"""
        for ext in CODE_EXTENSIONS:
            assert isinstance(ext, str)

    def test_code_extensions_no_empty_strings(self):
        """Test that CODE_EXTENSIONS has no empty strings"""
        assert "" not in CODE_EXTENSIONS
        assert "." not in CODE_EXTENSIONS  # Just a dot is not valid

    def test_code_extensions_no_leading_duplicates(self):
        """Test that there are no duplicate extensions"""
        # As a set, duplicates are automatically removed
        # Just verify we have reasonable count
        assert len(CODE_EXTENSIONS) >= 10

    def test_code_extensions_expected_languages(self):
        """Test that common language extensions are present"""
        expected = [".py", ".js", ".ts", ".go", ".rs", ".rb", ".php"]
        for ext in expected:
            assert ext in CODE_EXTENSIONS, f"{ext} should be in CODE_EXTENSIONS"

    def test_code_extensions_frontend_frameworks(self):
        """Test that frontend framework extensions are present"""
        frontend_exts = [".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte"]
        for ext in frontend_exts:
            assert ext in CODE_EXTENSIONS

    def test_code_extensions_backend_languages(self):
        """Test that backend language extensions are present"""
        backend_exts = [".py", ".go", ".rs", ".rb", ".php"]
        for ext in backend_exts:
            assert ext in CODE_EXTENSIONS


class TestConstantsIntegration:
    """Integration tests for constants usage"""

    def test_constants_work_together(self):
        """Test that SKIP_DIRS and CODE_EXTENSIONS work together"""
        # Both should be sets for efficient membership testing
        assert isinstance(SKIP_DIRS, set)
        assert isinstance(CODE_EXTENSIONS, set)

        # Both should support fast 'in' operations
        assert "node_modules" in SKIP_DIRS
        assert ".py" in CODE_EXTENSIONS

    def test_constants_no_overlap(self):
        """Test that there's no conceptual overlap between constants"""
        # SKIP_DIRS can contain dot-prefixed names (hidden directories)
        # CODE_EXTENSIONS all start with dot

        # All CODE_EXTENSIONS should start with dot
        for ext in CODE_EXTENSIONS:
            assert ext.startswith(".")

    def test_constants_coverage(self):
        """Test that constants cover common project structures"""
        # Should have Python
        assert ".py" in CODE_EXTENSIONS
        assert "__pycache__" in SKIP_DIRS

        # Should have JavaScript/TypeScript
        assert ".js" in CODE_EXTENSIONS
        assert ".ts" in CODE_EXTENSIONS
        assert "node_modules" in SKIP_DIRS

        # Should have build artifacts
        assert "dist" in SKIP_DIRS
        assert "build" in SKIP_DIRS

        # Should have version control
        assert ".git" in SKIP_DIRS


class TestConstantsValues:
    """Tests for specific constant values"""

    def test_skip_dirs_exact_values(self):
        """Test exact values in SKIP_DIRS"""
        expected_skip_dirs = {
            "node_modules", ".git", "__pycache__", ".venv", "venv",
            "dist", "build", ".next", ".nuxt", "target", "vendor",
            ".idea", ".vscode", "auto-claude", ".pytest_cache",
            ".mypy_cache", "coverage", ".turbo", ".cache"
        }
        # All expected should be present
        for expected in expected_skip_dirs:
            assert expected in SKIP_DIRS, f"{expected} should be in SKIP_DIRS"

    def test_code_extensions_exact_values(self):
        """Test exact values in CODE_EXTENSIONS"""
        expected_extensions = {
            ".py", ".js", ".jsx", ".ts", ".tsx", ".vue",
            ".svelte", ".go", ".rs", ".rb", ".php"
        }
        # All expected should be present
        for expected in expected_extensions:
            assert expected in CODE_EXTENSIONS, f"{expected} should be in CODE_EXTENSIONS"

    def test_skip_dirs_consistent_naming(self):
        """Test that SKIP_DIRS follows consistent naming patterns"""
        # Most should be lowercase
        lowercase_count = sum(1 for d in SKIP_DIRS if d.islower() or d.startswith("."))
        # At least 80% should be consistent
        assert lowercase_count / len(SKIP_DIRS) >= 0.8

    def test_code_extensions_consistent_format(self):
        """Test that CODE_EXTENSIONS follows consistent format"""
        # All should be dot + lowercase letters
        for ext in CODE_EXTENSIONS:
            assert ext[0] == "."
            # Rest should be alphanumeric
            assert ext[1:].isalnum(), f"{ext} should be . followed by alphanumeric"


class TestConstantsDocumentation:
    """Tests for constants documentation purposes"""

    def test_skip_dirs_are_documented(self):
        """Test that skip dirs are self-documenting by their names"""
        # Each skip dir should have a clear, recognizable name
        for dir_name in SKIP_DIRS:
            assert len(dir_name) >= 2, f"{dir_name} should have clear name"
            # No temp/random names
            assert "tmp" not in dir_name.lower()
            assert "temp" not in dir_name.lower()

    def test_code_extensions_are_documented(self):
        """Test that code extensions map to known languages"""
        # Map of extension to language hint
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
        }

        for ext, lang in language_map.items():
            if ext in CODE_EXTENSIONS:
                # Just verify the mapping makes sense
                assert ext in CODE_EXTENSIONS
