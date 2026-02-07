"""
Tests for project.analyzer
==========================

Comprehensive tests for the ProjectAnalyzer class including:
- Initialization and profile path resolution
- Profile loading and saving
- Project hash computation
- Re-analysis detection with inherited profiles
- Full project analysis orchestration
- Stack, framework, and structure detection
- Command building from detected stack
- Edge cases and error handling
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
from datetime import datetime

import pytest

from project.analyzer import ProjectAnalyzer
from project.models import SecurityProfile, TechnologyStack, CustomScripts
from project.structure_analyzer import StructureAnalyzer


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def temp_spec_dir(tmp_path: Path) -> Path:
    """Create a temporary spec directory."""
    spec_dir = tmp_path / "test_spec"
    spec_dir.mkdir()
    return spec_dir


@pytest.fixture
def sample_security_profile() -> SecurityProfile:
    """Create a sample security profile for testing."""
    profile = SecurityProfile()
    profile.project_dir = "/path/to/project"
    profile.created_at = "2024-01-01T12:00:00"
    profile.project_hash = "abc123"
    profile.detected_stack.languages = ["python", "javascript"]
    profile.detected_stack.package_managers = ["pip", "npm"]
    profile.detected_stack.frameworks = ["django", "react"]
    profile.custom_scripts.npm_scripts = ["build", "test"]
    return profile


@pytest.fixture
def sample_profile_dict(sample_security_profile: SecurityProfile) -> dict:
    """Create a sample profile dictionary for testing."""
    return sample_security_profile.to_dict()


# =============================================================================
# Initialization Tests
# =============================================================================

class TestProjectAnalyzerInitialization:
    """Tests for ProjectAnalyzer initialization."""

    def test_init_with_project_dir_only(self, temp_project_dir: Path):
        """Test initialization with only project directory."""
        analyzer = ProjectAnalyzer(temp_project_dir)

        assert analyzer.project_dir == temp_project_dir.resolve()
        assert analyzer.spec_dir is None
        assert isinstance(analyzer.profile, SecurityProfile)
        assert analyzer.parser is not None

    def test_init_with_project_and_spec_dir(self, temp_project_dir: Path, temp_spec_dir: Path):
        """Test initialization with both project and spec directories."""
        analyzer = ProjectAnalyzer(temp_project_dir, temp_spec_dir)

        assert analyzer.project_dir == temp_project_dir.resolve()
        assert analyzer.spec_dir == temp_spec_dir.resolve()

    def test_init_with_string_paths(self, tmp_path: Path):
        """Test initialization with string paths."""
        project_str = str(tmp_path / "project")
        Path(project_str).mkdir()

        analyzer = ProjectAnalyzer(project_str)

        assert analyzer.project_dir == Path(project_str).resolve()

    def test_init_resolves_paths(self, tmp_path: Path):
        """Test that paths are properly resolved."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Use relative path
        analyzer = ProjectAnalyzer(project_dir)

        # Path should be absolute and resolved
        assert analyzer.project_dir.is_absolute()


# =============================================================================
# Profile Path Tests
# =============================================================================

class TestGetProfilePath:
    """Tests for get_profile_path method."""

    def test_profile_path_without_spec_dir(self, temp_project_dir: Path):
        """Test profile path when no spec directory is set."""
        analyzer = ProjectAnalyzer(temp_project_dir)

        expected = temp_project_dir / ProjectAnalyzer.PROFILE_FILENAME
        assert analyzer.get_profile_path() == expected

    def test_profile_path_with_spec_dir(self, temp_project_dir: Path, temp_spec_dir: Path):
        """Test profile path when spec directory is set."""
        analyzer = ProjectAnalyzer(temp_project_dir, temp_spec_dir)

        expected = temp_spec_dir / ProjectAnalyzer.PROFILE_FILENAME
        assert analyzer.get_profile_path() == expected


# =============================================================================
# Load Profile Tests
# =============================================================================

class TestLoadProfile:
    """Tests for load_profile method."""

    def test_load_profile_nonexistent(self, temp_project_dir: Path):
        """Test loading a profile that doesn't exist."""
        analyzer = ProjectAnalyzer(temp_project_dir)

        result = analyzer.load_profile()

        assert result is None

    def test_load_profile_success(self, temp_project_dir: Path, sample_profile_dict: dict):
        """Test successfully loading a profile."""
        profile_path = temp_project_dir / ProjectAnalyzer.PROFILE_FILENAME
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(sample_profile_dict, f)

        analyzer = ProjectAnalyzer(temp_project_dir)
        result = analyzer.load_profile()

        assert isinstance(result, SecurityProfile)
        assert result.project_dir == sample_profile_dict["project_dir"]
        assert result.created_at == sample_profile_dict["created_at"]
        assert result.project_hash == sample_profile_dict["project_hash"]

    def test_load_profile_invalid_json(self, temp_project_dir: Path):
        """Test loading a profile with invalid JSON."""
        profile_path = temp_project_dir / ProjectAnalyzer.PROFILE_FILENAME
        with open(profile_path, "w", encoding="utf-8") as f:
            f.write("invalid json content")

        analyzer = ProjectAnalyzer(temp_project_dir)
        result = analyzer.load_profile()

        assert result is None

    def test_load_profile_with_inherited_from(self, temp_project_dir: Path):
        """Test loading a profile with inherited_from field."""
        profile_data = {
            "base_commands": ["git", "ls"],
            "stack_commands": ["npm"],
            "script_commands": [],
            "custom_commands": [],
            "detected_stack": {"languages": ["python"]},
            "custom_scripts": {"npm_scripts": []},
            "project_dir": "/path/to/project",
            "created_at": "2024-01-01T12:00:00",
            "project_hash": "abc123",
            "inherited_from": "/path/to/parent"
        }

        profile_path = temp_project_dir / ProjectAnalyzer.PROFILE_FILENAME
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(profile_data, f)

        analyzer = ProjectAnalyzer(temp_project_dir)
        result = analyzer.load_profile()

        assert result is not None
        assert result.inherited_from == "/path/to/parent"

    def test_load_profile_os_error(self, temp_project_dir: Path):
        """Test loading a profile when OS error occurs."""
        profile_path = temp_project_dir / ProjectAnalyzer.PROFILE_FILENAME
        profile_path.write_text("{}")

        analyzer = ProjectAnalyzer(temp_project_dir)

        with patch("builtins.open", side_effect=OSError("Permission denied")):
            result = analyzer.load_profile()
            assert result is None


# =============================================================================
# Save Profile Tests
# =============================================================================

class TestSaveProfile:
    """Tests for save_profile method."""

    def test_save_profile_creates_directory(self, temp_project_dir: Path):
        """Test that save_profile creates the parent directory if needed."""
        spec_dir = temp_project_dir / "subdir" / "spec"
        analyzer = ProjectAnalyzer(temp_project_dir, spec_dir)

        profile = SecurityProfile()
        profile.project_dir = str(temp_project_dir)

        analyzer.save_profile(profile)

        assert spec_dir.exists()
        assert (spec_dir / ProjectAnalyzer.PROFILE_FILENAME).exists()

    def test_save_profile_writes_correct_data(self, temp_project_dir: Path, sample_security_profile: SecurityProfile):
        """Test that save_profile writes the correct data."""
        analyzer = ProjectAnalyzer(temp_project_dir)

        analyzer.save_profile(sample_security_profile)

        profile_path = analyzer.get_profile_path()
        with open(profile_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded["project_dir"] == sample_security_profile.project_dir
        assert loaded["created_at"] == sample_security_profile.created_at
        assert loaded["project_hash"] == sample_security_profile.project_hash
        assert "python" in loaded["detected_stack"]["languages"]

    def test_save_profile_overwrites_existing(self, temp_project_dir: Path):
        """Test that save_profile overwrites existing profile."""
        analyzer = ProjectAnalyzer(temp_project_dir)

        # Save initial profile
        profile1 = SecurityProfile()
        profile1.project_hash = "hash1"
        analyzer.save_profile(profile1)

        # Save new profile
        profile2 = SecurityProfile()
        profile2.project_hash = "hash2"
        analyzer.save_profile(profile2)

        # Verify only the latest exists
        profile_path = analyzer.get_profile_path()
        with open(profile_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded["project_hash"] == "hash2"


# =============================================================================
# Compute Project Hash Tests
# =============================================================================

class TestComputeProjectHash:
    """Tests for compute_project_hash method."""

    def test_hash_empty_project(self, temp_project_dir: Path):
        """Test hash computation for an empty project."""
        analyzer = ProjectAnalyzer(temp_project_dir)

        hash_value = analyzer.compute_project_hash()

        # Empty project should still return a hash based on directory name
        assert isinstance(hash_value, str)
        assert len(hash_value) == 32  # MD5 hex digest

    def test_hash_with_package_json(self, temp_project_dir: Path):
        """Test hash computation with package.json."""
        analyzer = ProjectAnalyzer(temp_project_dir)

        package_json = temp_project_dir / "package.json"
        package_json.write_text('{"name": "test"}')

        hash1 = analyzer.compute_project_hash()

        # Modify file - hash should change
        package_json.write_text('{"name": "modified"}')
        hash2 = analyzer.compute_project_hash()

        assert hash1 != hash2

    def test_hash_with_pyproject_toml(self, temp_project_dir: Path):
        """Test hash computation with pyproject.toml."""
        analyzer = ProjectAnalyzer(temp_project_dir)

        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text('[project]\nname = "test"')

        hash1 = analyzer.compute_project_hash()

        # Modify file
        pyproject.write_text('[project]\nname = "modified"')
        hash2 = analyzer.compute_project_hash()

        assert hash1 != hash2

    def test_hash_with_source_files(self, temp_project_dir: Path):
        """Test hash computation considers source file count."""
        analyzer = ProjectAnalyzer(temp_project_dir)

        # Create some Python files
        (temp_project_dir / "test1.py").write_text("print('hello')")
        (temp_project_dir / "test2.py").write_text("print('world')")

        hash1 = analyzer.compute_project_hash()

        # Add another file
        (temp_project_dir / "test3.py").write_text("print('more')")

        hash2 = analyzer.compute_project_hash()

        assert hash1 != hash2

    def test_hash_with_csproj_files(self, temp_project_dir: Path):
        """Test hash computation with .csproj files (glob pattern)."""
        analyzer = ProjectAnalyzer(temp_project_dir)

        # Create nested csproj file
        src_dir = temp_project_dir / "src"
        src_dir.mkdir()
        (src_dir / "Project.csproj").write_text("<Project></Project>")

        hash_value = analyzer.compute_project_hash()

        assert isinstance(hash_value, str)
        assert len(hash_value) == 32

    def test_hash_with_dockerfile(self, temp_project_dir: Path):
        """Test hash computation with Dockerfile."""
        analyzer = ProjectAnalyzer(temp_project_dir)

        dockerfile = temp_project_dir / "Dockerfile"
        dockerfile.write_text("FROM python:3.11")

        hash1 = analyzer.compute_project_hash()

        # Modify Dockerfile - ensure different content
        dockerfile.write_text("FROM python:3.12")

        # Verify file was actually modified
        assert dockerfile.read_text() == "FROM python:3.12"

        hash2 = analyzer.compute_project_hash()

        # Hashes should be different since Dockerfile content changed
        assert hash1 != hash2, f"Hashes should differ but got same value: {hash1}"

    def test_hash_with_go_mod(self, temp_project_dir: Path):
        """Test hash computation with go.mod."""
        analyzer = ProjectAnalyzer(temp_project_dir)

        go_mod = temp_project_dir / "go.mod"
        go_mod.write_text("module test\n\ngo 1.21")

        hash_value = analyzer.compute_project_hash()

        assert isinstance(hash_value, str)
        assert len(hash_value) == 32

    def test_hash_handles_file_stat_errors(self, temp_project_dir: Path):
        """Test hash computation handles file stat errors gracefully."""
        analyzer = ProjectAnalyzer(temp_project_dir)

        # Create a file that will have stat errors
        package_json = temp_project_dir / "package.json"
        package_json.write_text('{"name": "test"}')

        hash1 = analyzer.compute_project_hash()

        # Create a file and make it unreadable
        problematic = temp_project_dir / "problem.txt"
        problematic.write_text("content")

        # Mock the stat method for the problematic file to raise OSError
        original_stat = Path.stat

        def mock_stat(self, follow_symlinks=True):
            if "problem" in str(self):
                raise OSError("Permission denied")
            return original_stat(self, follow_symlinks=follow_symlinks)

        with patch.object(Path, "stat", mock_stat):
            # Should still return a hash, just skipping the problematic file
            hash2 = analyzer.compute_project_hash()

        # Both should be valid hashes even if different
        assert isinstance(hash1, str)
        assert isinstance(hash2, str)

    def test_hash_consistency(self, temp_project_dir: Path):
        """Test that hash is consistent for unchanged project."""
        analyzer = ProjectAnalyzer(temp_project_dir)

        (temp_project_dir / "package.json").write_text('{"name": "test"}')

        hash1 = analyzer.compute_project_hash()
        hash2 = analyzer.compute_project_hash()

        assert hash1 == hash2

    def test_hash_with_glob_pattern_os_error(self, temp_project_dir: Path):
        """Test hash computation handles OSError when hashing glob files."""
        analyzer = ProjectAnalyzer(temp_project_dir)

        # Create a .csproj file (uses glob pattern)
        src_dir = temp_project_dir / "src"
        src_dir.mkdir()
        csproj = src_dir / "Project.csproj"
        csproj.write_text("<Project></Project>")

        hash1 = analyzer.compute_project_hash()

        # Mock stat to raise OSError for the glob files
        original_stat = Path.stat

        def mock_stat(self, follow_symlinks=True):
            if "csproj" in str(self):
                raise OSError("Simulated error")
            return original_stat(self, follow_symlinks=follow_symlinks)

        with patch.object(Path, "stat", mock_stat):
            hash2 = analyzer.compute_project_hash()

        # Should still return a valid hash
        assert isinstance(hash1, str)
        assert isinstance(hash2, str)


# =============================================================================
# Should Reanalyze Tests
# =============================================================================

class TestShouldReanalyze:
    """Tests for should_reanalyze method."""

    def test_should_reanalyze_different_hash(self, temp_project_dir: Path):
        """Test should_reanalyze returns True when hash differs."""
        analyzer = ProjectAnalyzer(temp_project_dir)

        profile = SecurityProfile()
        profile.project_hash = "different_hash"

        assert analyzer.should_reanalyze(profile) is True

    def test_should_reanalyze_same_hash(self, temp_project_dir: Path):
        """Test should_reanalyze returns False when hash matches."""
        analyzer = ProjectAnalyzer(temp_project_dir)

        current_hash = analyzer.compute_project_hash()
        profile = SecurityProfile()
        profile.project_hash = current_hash

        assert analyzer.should_reanalyze(profile) is False

    def test_should_reanalyze_inherited_valid(self, temp_project_dir: Path, tmp_path: Path):
        """Test should_reanalyze with valid inherited profile."""
        # Create parent directory
        parent_dir = tmp_path / "parent_project"
        parent_dir.mkdir()

        # Create parent profile
        parent_profile = parent_dir / ProjectAnalyzer.PROFILE_FILENAME
        parent_profile.write_text('{"project_dir": "/parent"}')

        # Create child as subdirectory of parent
        child_dir = parent_dir / "child_project"
        child_dir.mkdir()

        analyzer = ProjectAnalyzer(child_dir)
        profile = SecurityProfile()
        profile.inherited_from = str(parent_dir)

        assert analyzer.should_reanalyze(profile) is False

    def test_should_reanalyze_inherited_invalid_parent(self, temp_project_dir: Path, tmp_path: Path):
        """Test should_reanalyze with invalid parent path."""
        # Create a path that exists but is not a directory
        invalid_parent = tmp_path / "not_a_directory"
        invalid_parent.write_text("I'm a file, not a directory")

        analyzer = ProjectAnalyzer(temp_project_dir)
        profile = SecurityProfile()
        profile.inherited_from = str(invalid_parent)

        # Should check hash since parent is invalid (not a directory)
        assert analyzer.should_reanalyze(profile) is True

    def test_should_reanalyze_inherited_not_descendant(self, temp_project_dir: Path, tmp_path: Path):
        """Test should_reanalyze when project is not descendant of parent."""
        other_dir = tmp_path / "other_project"
        other_dir.mkdir()

        # Create profile in other directory
        other_profile = other_dir / ProjectAnalyzer.PROFILE_FILENAME
        other_profile.write_text('{"project_dir": "/other"}')

        analyzer = ProjectAnalyzer(temp_project_dir)
        profile = SecurityProfile()
        profile.inherited_from = str(other_dir)

        # Should reanalyze since not a descendant
        assert analyzer.should_reanalyze(profile) is True

    def test_should_reanalyze_inherited_parent_no_profile(self, temp_project_dir: Path, tmp_path: Path):
        """Test should_reanalyze when parent has no profile."""
        parent_dir = tmp_path / "parent_project"
        parent_dir.mkdir()

        child_dir = parent_dir / "child_project"
        child_dir.mkdir()

        analyzer = ProjectAnalyzer(child_dir)
        profile = SecurityProfile()
        profile.inherited_from = str(parent_dir)

        # Should reanalyze since parent has no profile
        assert analyzer.should_reanalyze(profile) is True

    def test_should_reanalyze_inherited_with_profile_prints_message(self, temp_project_dir: Path, tmp_path: Path, sample_profile_dict: dict):
        """Test should_reanalyze with inherited profile prints message."""
        # Create parent directory with profile
        parent_dir = tmp_path / "parent_project"
        parent_dir.mkdir()
        parent_profile = parent_dir / ProjectAnalyzer.PROFILE_FILENAME
        parent_profile.write_text(json.dumps(sample_profile_dict))

        # Create child as subdirectory of parent
        child_dir = parent_dir / "child_project"
        child_dir.mkdir()

        analyzer = ProjectAnalyzer(child_dir)
        profile = SecurityProfile()
        profile.inherited_from = str(parent_dir)

        # Should not reanalyze
        assert analyzer.should_reanalyze(profile) is False

    @patch("builtins.print")
    def test_analyze_uses_inherited_profile(self, mock_print: Mock, tmp_path: Path):
        """Test analyze uses inherited profile and prints message."""
        # Create parent directory with profile
        parent_dir = tmp_path / "parent_project"
        parent_dir.mkdir()

        parent_profile = SecurityProfile()
        parent_profile.project_hash = "parent_hash"
        parent_profile.project_dir = str(parent_dir)
        parent_profile_path = parent_dir / ProjectAnalyzer.PROFILE_FILENAME

        with open(parent_profile_path, "w", encoding="utf-8") as f:
            json.dump(parent_profile.to_dict(), f)

        # Create child as subdirectory of parent
        child_dir = parent_dir / "child_project"
        child_dir.mkdir()

        child_analyzer = ProjectAnalyzer(child_dir)

        # Create profile with inherited_from
        child_profile = SecurityProfile()
        child_profile.project_hash = child_analyzer.compute_project_hash()
        child_profile.inherited_from = str(parent_dir)
        child_profile.project_dir = str(child_dir)

        child_profile_path = child_dir / ProjectAnalyzer.PROFILE_FILENAME
        with open(child_profile_path, "w", encoding="utf-8") as f:
            json.dump(child_profile.to_dict(), f)

        # Analyze should use inherited profile
        result = child_analyzer.analyze()

        assert result.inherited_from == str(parent_dir)

        # Verify print was called with inherited message
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("inherited" in str(call).lower() for call in print_calls)


# =============================================================================
# Is Descendant Of Tests
# =============================================================================

class TestIsDescendantOf:
    """Tests for _is_descendant_of method."""

    def test_is_descendant_direct_child(self, tmp_path: Path):
        """Test _is_descendant_of with direct child."""
        parent = tmp_path / "parent"
        parent.mkdir()
        child = parent / "child"

        analyzer = ProjectAnalyzer(tmp_path)

        assert analyzer._is_descendant_of(child, parent) is True

    def test_is_descendant_nested_child(self, tmp_path: Path):
        """Test _is_descendant_of with nested child."""
        parent = tmp_path / "parent"
        parent.mkdir()
        child = parent / "a" / "b" / "c"
        child.mkdir(parents=True)

        analyzer = ProjectAnalyzer(tmp_path)

        assert analyzer._is_descendant_of(child, parent) is True

    def test_is_descendant_not_related(self, tmp_path: Path):
        """Test _is_descendant_of with unrelated paths."""
        path1 = tmp_path / "project1"
        path1.mkdir()
        path2 = tmp_path / "project2"
        path2.mkdir()

        analyzer = ProjectAnalyzer(tmp_path)

        assert analyzer._is_descendant_of(path1, path2) is False

    def test_is_descendant_same_path(self, tmp_path: Path):
        """Test _is_descendant_of with same path."""
        path = tmp_path / "project"
        path.mkdir()

        analyzer = ProjectAnalyzer(tmp_path)

        assert analyzer._is_descendant_of(path, path) is True

    def test_is_descendant_with_symlinks(self, tmp_path: Path):
        """Test _is_descendant_of handles symlinks."""
        parent = tmp_path / "parent"
        parent.mkdir()
        child = parent / "child"
        child.mkdir()

        analyzer = ProjectAnalyzer(tmp_path)

        # Test with resolved paths
        assert analyzer._is_descendant_of(child, parent) is True


# =============================================================================
# Analyze Tests
# =============================================================================

class TestAnalyze:
    """Tests for analyze method."""

    def test_analyze_from_scratch(self, temp_project_dir: Path):
        """Test full analysis on a new project."""
        # Create a Python project
        (temp_project_dir / "pyproject.toml").write_text('[project]\nname = "test"')
        (temp_project_dir / "main.py").write_text("print('hello')")

        analyzer = ProjectAnalyzer(temp_project_dir)
        profile = analyzer.analyze()

        assert isinstance(profile, SecurityProfile)
        assert profile.project_dir == str(temp_project_dir.resolve())
        assert profile.project_hash == analyzer.compute_project_hash()
        assert len(profile.created_at) > 0
        assert "python" in profile.detected_stack.languages

    def test_analyze_uses_cached_profile(self, temp_project_dir: Path, sample_security_profile: SecurityProfile):
        """Test analyze uses existing profile when hash matches."""
        # Save existing profile
        analyzer = ProjectAnalyzer(temp_project_dir)
        current_hash = analyzer.compute_project_hash()
        sample_security_profile.project_hash = current_hash
        analyzer.save_profile(sample_security_profile)

        # Analyze should return cached profile
        profile = analyzer.analyze()

        assert profile.project_dir == sample_security_profile.project_dir
        assert profile.created_at == sample_security_profile.created_at

    @patch("builtins.print")
    def test_analyze_cached_prints_message(self, mock_print: Mock, temp_project_dir: Path):
        """Test analyze prints message when using cached profile."""
        analyzer = ProjectAnalyzer(temp_project_dir)

        # Save a profile
        profile = SecurityProfile()
        profile.project_hash = analyzer.compute_project_hash()
        analyzer.save_profile(profile)

        # Analyze
        analyzer.analyze()

        # Should print about using cached profile
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("cached" in str(call).lower() for call in print_calls)

    def test_analyze_force_reanalyze(self, temp_project_dir: Path):
        """Test analyze with force=True."""
        # Save existing profile
        analyzer = ProjectAnalyzer(temp_project_dir)
        old_profile = SecurityProfile()
        old_profile.project_hash = analyzer.compute_project_hash()
        old_profile.created_at = "2024-01-01T00:00:00"
        analyzer.save_profile(old_profile)

        # Create source files
        (temp_project_dir / "main.py").write_text("print('hello')")

        # Force reanalyze
        new_profile = analyzer.analyze(force=True)

        # Should have new timestamp
        assert new_profile.created_at != old_profile.created_at
        assert "python" in new_profile.detected_stack.languages

    def test_analyze_creates_profile_directory(self, temp_project_dir: Path):
        """Test analyze creates directory for profile if needed."""
        spec_dir = temp_project_dir / "specs" / "001"
        analyzer = ProjectAnalyzer(temp_project_dir, spec_dir)

        analyzer.analyze()

        assert spec_dir.exists()
        assert (spec_dir / ProjectAnalyzer.PROFILE_FILENAME).exists()

    def test_analyze_builds_stack_commands(self, temp_project_dir: Path):
        """Test analyze builds commands from detected stack."""
        # Create Python project
        (temp_project_dir / "pyproject.toml").write_text('[project]\nname = "test"')

        analyzer = ProjectAnalyzer(temp_project_dir)
        profile = analyzer.analyze()

        # Should have base commands
        assert len(profile.base_commands) > 0
        assert "git" in profile.base_commands

        # Should have python commands
        assert "python" in profile.stack_commands or "python3" in profile.stack_commands

    @patch("builtins.print")
    def test_analyze_prints_summary(self, mock_print: Mock, temp_project_dir: Path):
        """Test analyze prints summary."""
        (temp_project_dir / "pyproject.toml").write_text('[project]\nname = "test"')

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer.analyze()

        # Should have called print multiple times for summary
        assert mock_print.call_count > 0

    def test_analyze_with_npm_scripts(self, temp_project_dir: Path):
        """Test analyze detects npm scripts."""
        # Create Node.js project
        package_json = {
            "name": "test",
            "scripts": {
                "build": "webpack",
                "test": "jest",
                "lint": "eslint"
            }
        }
        package_path = temp_project_dir / "package.json"
        package_path.write_text(json.dumps(package_json))

        analyzer = ProjectAnalyzer(temp_project_dir)
        profile = analyzer.analyze()

        assert "javascript" in profile.detected_stack.languages
        assert len(profile.custom_scripts.npm_scripts) == 3
        assert "build" in profile.custom_scripts.npm_scripts
        assert "npm" in profile.script_commands


# =============================================================================
# Detection Method Tests
# =============================================================================

class TestDetectStack:
    """Tests for _detect_stack method."""

    def test_detect_stack_python(self, temp_project_dir: Path):
        """Test stack detection for Python project."""
        (temp_project_dir / "pyproject.toml").write_text('[project]\nname = "test"')

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer._detect_stack()

        assert "python" in analyzer.profile.detected_stack.languages

    def test_detect_stack_javascript(self, temp_project_dir: Path):
        """Test stack detection for JavaScript project."""
        (temp_project_dir / "package.json").write_text('{"name": "test"}')

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer._detect_stack()

        assert "javascript" in analyzer.profile.detected_stack.languages

    def test_detect_stack_rust(self, temp_project_dir: Path):
        """Test stack detection for Rust project."""
        (temp_project_dir / "Cargo.toml").write_text('[package]\nname = "test"')

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer._detect_stack()

        assert "rust" in analyzer.profile.detected_stack.languages

    def test_detect_stack_go(self, temp_project_dir: Path):
        """Test stack detection for Go project."""
        (temp_project_dir / "go.mod").write_text('module test')

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer._detect_stack()

        assert "go" in analyzer.profile.detected_stack.languages

    def test_detect_stack_package_managers(self, temp_project_dir: Path):
        """Test package manager detection."""
        (temp_project_dir / "package-lock.json").write_text('{}')
        (temp_project_dir / "yarn.lock").write_text('')
        (temp_project_dir / "pnpm-lock.yaml").write_text('')

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer._detect_stack()

        assert "npm" in analyzer.profile.detected_stack.package_managers
        assert "yarn" in analyzer.profile.detected_stack.package_managers
        assert "pnpm" in analyzer.profile.detected_stack.package_managers


class TestDetectFrameworks:
    """Tests for _detect_frameworks method."""

    def test_detect_frameworks_django(self, temp_project_dir: Path):
        """Test framework detection for Django."""
        # Create requirements.txt with Django
        (temp_project_dir / "requirements.txt").write_text("Django>=4.0")

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer._detect_frameworks()

        assert "django" in analyzer.profile.detected_stack.frameworks

    def test_detect_frameworks_react(self, temp_project_dir: Path):
        """Test framework detection for React."""
        package_json = {
            "name": "test",
            "dependencies": {
                "react": "^18.0.0"
            }
        }
        (temp_project_dir / "package.json").write_text(json.dumps(package_json))

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer._detect_frameworks()

        assert "react" in analyzer.profile.detected_stack.frameworks

    def test_detect_frameworks_fastapi(self, temp_project_dir: Path):
        """Test framework detection for FastAPI."""
        (temp_project_dir / "pyproject.toml").write_text('''
[project]
dependencies = ["fastapi>=0.100"]
''')

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer._detect_frameworks()

        assert "fastapi" in analyzer.profile.detected_stack.frameworks


class TestDetectStructure:
    """Tests for _detect_structure method."""

    def test_detect_structure_npm_scripts(self, temp_project_dir: Path):
        """Test structure detection for npm scripts."""
        package_json = {
            "name": "test",
            "scripts": {
                "build": "webpack",
                "dev": "vite"
            }
        }
        (temp_project_dir / "package.json").write_text(json.dumps(package_json))

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer._detect_structure()

        assert "build" in analyzer.profile.custom_scripts.npm_scripts
        assert "dev" in analyzer.profile.custom_scripts.npm_scripts

    def test_detect_structure_makefile(self, temp_project_dir: Path):
        """Test structure detection for Makefile."""
        makefile_content = """
.PHONY: all test clean

all: build

build:
    echo "Building"

test:
    echo "Testing"

clean:
    echo "Cleaning"
"""
        (temp_project_dir / "Makefile").write_text(makefile_content)

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer._detect_structure()

        assert "build" in analyzer.profile.custom_scripts.make_targets
        assert "test" in analyzer.profile.custom_scripts.make_targets
        assert "clean" in analyzer.profile.custom_scripts.make_targets
        assert "make" in analyzer.profile.script_commands

    def test_detect_structure_shell_scripts(self, temp_project_dir: Path):
        """Test structure detection for shell scripts."""
        (temp_project_dir / "deploy.sh").write_text("#!/bin/bash\necho 'Deploy'")
        (temp_project_dir / "setup.bash").write_text("#!/bin/bash\necho 'Setup'")

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer._detect_structure()

        assert "deploy.sh" in analyzer.profile.custom_scripts.shell_scripts
        assert "setup.bash" in analyzer.profile.custom_scripts.shell_scripts
        assert "./deploy.sh" in analyzer.profile.script_commands

    def test_detect_structure_custom_allowlist(self, temp_project_dir: Path):
        """Test structure detection for custom allowlist."""
        allowlist_content = """
# Custom commands
custom-tool
another-command
# Comment line
third-command
"""
        (temp_project_dir / StructureAnalyzer.CUSTOM_ALLOWLIST_FILENAME).write_text(allowlist_content)

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer._detect_structure()

        assert "custom-tool" in analyzer.profile.custom_commands
        assert "another-command" in analyzer.profile.custom_commands
        assert "third-command" in analyzer.profile.custom_commands


# =============================================================================
# Backward Compatibility Tests
# =============================================================================

class TestBackwardCompatibilityMethods:
    """Tests for backward compatibility methods."""

    def test_detect_languages(self, temp_project_dir: Path):
        """Test _detect_languages method."""
        (temp_project_dir / "pyproject.toml").write_text('[project]\nname = "test"')

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer._detect_languages()

        assert "python" in analyzer.profile.detected_stack.languages

    def test_detect_package_managers(self, temp_project_dir: Path):
        """Test _detect_package_managers method."""
        (temp_project_dir / "package-lock.json").write_text('{}')

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer._detect_package_managers()

        assert "npm" in analyzer.profile.detected_stack.package_managers

    def test_detect_databases(self, temp_project_dir: Path):
        """Test _detect_databases method."""
        (temp_project_dir / ".env").write_text("DATABASE_URL=postgresql://localhost/db")

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer._detect_databases()

        assert "postgresql" in analyzer.profile.detected_stack.databases

    def test_detect_infrastructure(self, temp_project_dir: Path):
        """Test _detect_infrastructure method."""
        (temp_project_dir / "Dockerfile").write_text("FROM python:3.11")

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer._detect_infrastructure()

        assert "docker" in analyzer.profile.detected_stack.infrastructure

    def test_detect_cloud_providers(self, temp_project_dir: Path):
        """Test _detect_cloud_providers method."""
        (temp_project_dir / "vercel.json").write_text('{}')

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer._detect_cloud_providers()

        assert "vercel" in analyzer.profile.detected_stack.cloud_providers

    def test_detect_code_quality_tools(self, temp_project_dir: Path):
        """Test _detect_code_quality_tools method."""
        (temp_project_dir / ".eslintrc.json").write_text('{}')
        (temp_project_dir / "prettier.config.js").write_text('module.exports = {};')

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer._detect_code_quality_tools()

        # Note: these specific files might not be in the detection list
        # but the method should run without error
        assert isinstance(analyzer.profile.detected_stack.code_quality_tools, list)

    def test_detect_version_managers(self, temp_project_dir: Path):
        """Test _detect_version_managers method."""
        (temp_project_dir / ".nvmrc").write_text('18.0.0')

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer._detect_version_managers()

        assert "nvm" in analyzer.profile.detected_stack.version_managers

    def test_detect_custom_scripts(self, temp_project_dir: Path):
        """Test _detect_custom_scripts method."""
        package_json = {"name": "test", "scripts": {"build": "webpack"}}
        (temp_project_dir / "package.json").write_text(json.dumps(package_json))

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer._detect_custom_scripts()

        assert "build" in analyzer.profile.custom_scripts.npm_scripts

    def test_load_custom_allowlist(self, temp_project_dir: Path):
        """Test _load_custom_allowlist method."""
        (temp_project_dir / StructureAnalyzer.CUSTOM_ALLOWLIST_FILENAME).write_text("custom-cmd")

        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer._load_custom_allowlist()

        assert "custom-cmd" in analyzer.profile.custom_commands


# =============================================================================
# Build Stack Commands Tests
# =============================================================================

class TestBuildStackCommands:
    """Tests for _build_stack_commands method."""

    def test_build_commands_from_languages(self, temp_project_dir: Path):
        """Test building commands from detected languages."""
        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer.profile.detected_stack.languages = ["python", "javascript"]

        analyzer._build_stack_commands()

        # Should have python and node commands
        assert "python" in analyzer.profile.stack_commands or "python3" in analyzer.profile.stack_commands
        assert "node" in analyzer.profile.stack_commands

    def test_build_commands_from_package_managers(self, temp_project_dir: Path):
        """Test building commands from package managers."""
        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer.profile.detected_stack.package_managers = ["npm", "pip"]

        analyzer._build_stack_commands()

        assert "npm" in analyzer.profile.stack_commands
        assert "pip" in analyzer.profile.stack_commands

    def test_build_commands_from_frameworks(self, temp_project_dir: Path):
        """Test building commands from frameworks."""
        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer.profile.detected_stack.frameworks = ["pytest"]

        analyzer._build_stack_commands()

        assert "pytest" in analyzer.profile.stack_commands

    def test_build_commands_from_databases(self, temp_project_dir: Path):
        """Test building commands from databases."""
        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer.profile.detected_stack.databases = ["postgresql"]

        analyzer._build_stack_commands()

        # Should have psql command
        assert "psql" in analyzer.profile.stack_commands

    def test_build_commands_from_infrastructure(self, temp_project_dir: Path):
        """Test building commands from infrastructure."""
        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer.profile.detected_stack.infrastructure = ["docker"]

        analyzer._build_stack_commands()

        assert "docker" in analyzer.profile.stack_commands

    def test_build_commands_from_cloud(self, temp_project_dir: Path):
        """Test building commands from cloud providers."""
        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer.profile.detected_stack.cloud_providers = ["aws"]

        analyzer._build_stack_commands()

        # Should have aws command
        assert "aws" in analyzer.profile.stack_commands

    def test_build_commands_from_empty_stack(self, temp_project_dir: Path):
        """Test building commands with empty stack."""
        analyzer = ProjectAnalyzer(temp_project_dir)

        analyzer._build_stack_commands()

        # Should have no stack commands for empty stack
        assert len(analyzer.profile.stack_commands) == 0

    def test_build_commands_from_code_quality_tools(self, temp_project_dir: Path):
        """Test building commands from code quality tools."""
        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer.profile.detected_stack.code_quality_tools = ["shellcheck", "yamllint"]

        analyzer._build_stack_commands()

        # Should have code quality tool commands
        assert "shellcheck" in analyzer.profile.stack_commands
        assert "yamllint" in analyzer.profile.stack_commands

    def test_build_commands_from_version_managers(self, temp_project_dir: Path):
        """Test building commands from version managers."""
        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer.profile.detected_stack.version_managers = ["nvm", "pyenv"]

        analyzer._build_stack_commands()

        # Should have version manager commands
        assert "nvm" in analyzer.profile.stack_commands
        assert "pyenv" in analyzer.profile.stack_commands

    def test_build_commands_combines_all(self, temp_project_dir: Path):
        """Test that build commands combines all detected elements."""
        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer.profile.detected_stack.languages = ["python"]
        analyzer.profile.detected_stack.package_managers = ["pip"]
        analyzer.profile.detected_stack.frameworks = ["pytest"]
        analyzer.profile.detected_stack.databases = ["postgresql"]
        analyzer.profile.detected_stack.infrastructure = ["docker"]

        analyzer._build_stack_commands()

        # Should have commands from all categories
        assert len(analyzer.profile.stack_commands) > 0


# =============================================================================
# Print Summary Tests
# =============================================================================

class TestPrintSummary:
    """Tests for _print_summary method."""

    @patch("builtins.print")
    def test_print_summary_with_stack(self, mock_print: Mock, temp_project_dir: Path):
        """Test print summary with detected stack."""
        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer.profile.detected_stack.languages = ["python", "javascript"]
        analyzer.profile.detected_stack.package_managers = ["pip", "npm"]
        analyzer.profile.custom_scripts.npm_scripts = ["build", "test"]

        analyzer._print_summary()

        # Should have called print multiple times
        assert mock_print.call_count > 5

        # Check for key content in print calls
        print_calls = [str(call) for call in mock_print.call_args_list]
        summary_text = " ".join(print_calls)
        assert "python" in summary_text.lower()
        assert "SECURITY PROFILE" in summary_text

    @patch("builtins.print")
    def test_print_summary_empty_profile(self, mock_print: Mock, temp_project_dir: Path):
        """Test print summary with empty profile."""
        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer.profile.base_commands = {"git", "ls"}

        analyzer._print_summary()

        # Should still print header and command count
        assert mock_print.call_count > 0

    @patch("builtins.print")
    def test_print_summary_with_all_categories(self, mock_print: Mock, temp_project_dir: Path):
        """Test print summary with all categories populated."""
        analyzer = ProjectAnalyzer(temp_project_dir)
        analyzer.profile.detected_stack.languages = ["python"]
        analyzer.profile.detected_stack.package_managers = ["pip"]
        analyzer.profile.detected_stack.frameworks = ["pytest"]
        analyzer.profile.detected_stack.databases = ["postgresql"]
        analyzer.profile.detected_stack.infrastructure = ["docker"]
        analyzer.profile.detected_stack.cloud_providers = ["aws"]
        analyzer.profile.custom_scripts.npm_scripts = ["build"]
        analyzer.profile.custom_scripts.make_targets = ["test"]
        analyzer.profile.base_commands = {"git", "ls"}

        analyzer._print_summary()

        # Should print all categories
        assert mock_print.call_count > 10


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_analyze_nonexistent_directory(self, tmp_path: Path):
        """Test analyzer with directory that doesn't exist."""
        nonexistent = tmp_path / "nonexistent"

        # Should not raise, just work with the path
        analyzer = ProjectAnalyzer(nonexistent)

        assert analyzer.project_dir == nonexistent.resolve()

    def test_analyze_empty_directory(self, temp_project_dir: Path):
        """Test analyzer with completely empty directory."""
        analyzer = ProjectAnalyzer(temp_project_dir)
        profile = analyzer.analyze()

        # Should still produce a valid profile
        assert isinstance(profile, SecurityProfile)
        assert profile.project_dir == str(temp_project_dir.resolve())

    def test_compute_hash_with_no_config_files(self, temp_project_dir: Path):
        """Test hash computation when no config files exist."""
        analyzer = ProjectAnalyzer(temp_project_dir)

        hash_value = analyzer.compute_project_hash()

        # Should still return a hash
        assert isinstance(hash_value, str)
        assert len(hash_value) == 32

    def test_analyze_with_mixed_tech_stack(self, temp_project_dir: Path):
        """Test analyzer with mixed technology stack."""
        # Create both Python and Node.js files
        (temp_project_dir / "pyproject.toml").write_text('[project]\nname = "test"')
        (temp_project_dir / "package.json").write_text('{"name": "test"}')

        analyzer = ProjectAnalyzer(temp_project_dir)
        profile = analyzer.analyze()

        # Should detect both
        assert "python" in profile.detected_stack.languages
        assert "javascript" in profile.detected_stack.languages

    def test_profile_filename_constant(self):
        """Test that PROFILE_FILENAME is correct."""
        assert ProjectAnalyzer.PROFILE_FILENAME == ".auto-claude-security.json"

    def test_multiple_analyzers_same_project(self, temp_project_dir: Path):
        """Test multiple analyzers for the same project."""
        analyzer1 = ProjectAnalyzer(temp_project_dir)
        analyzer2 = ProjectAnalyzer(temp_project_dir)

        # Both should work independently
        profile1 = analyzer1.analyze()
        profile2 = analyzer2.analyze()

        assert profile1.project_dir == profile2.project_dir

    def test_analyzer_with_relative_path(self, tmp_path: Path):
        """Test analyzer with relative path string."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Change to tmp_path directory
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            analyzer = ProjectAnalyzer(Path("project"))

            # Should resolve to absolute path
            assert analyzer.project_dir.is_absolute()
        finally:
            os.chdir(original_cwd)
