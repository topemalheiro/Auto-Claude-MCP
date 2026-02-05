"""
Comprehensive tests for project/analyzer.py
============================================

Tests for the ProjectAnalyzer class and utility functions:
- ProjectAnalyzer initialization and configuration
- Profile loading and persistence (load_profile, save_profile)
- Project hash computation (compute_project_hash)
- Re-analysis logic (should_reanalyze)
- Path validation (_is_descendant_of)
- Main orchestration method (analyze)
- Utility functions (get_or_create_profile, is_command_allowed, needs_validation)
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from project.analyzer import ProjectAnalyzer
from project.models import SecurityProfile, TechnologyStack, CustomScripts


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_project_dir(tmp_path: Path):
    """Create a temporary project directory with some files."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create some common project files
    (project_dir / "package.json").write_text('{"name": "test"}')
    (project_dir / "README.md").write_text("# Test Project")

    # Create a source file
    src_dir = project_dir / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("print('hello')")

    return project_dir


@pytest.fixture
def temp_spec_dir(tmp_path: Path):
    """Create a temporary spec directory."""
    spec_dir = tmp_path / ".auto-claude" / "specs" / "001"
    spec_dir.mkdir(parents=True)
    return spec_dir


@pytest.fixture
def sample_profile(temp_project_dir: Path):
    """Create a sample security profile."""
    profile = SecurityProfile()
    profile.project_dir = str(temp_project_dir)
    profile.created_at = datetime.now().isoformat()
    profile.project_hash = "abc123"
    profile.base_commands = {"git", "ls", "cat"}
    profile.stack_commands = {"npm", "node"}
    return profile


@pytest.fixture
def analyzer(temp_project_dir: Path, temp_spec_dir: Path):
    """Create a ProjectAnalyzer instance with temp directories."""
    return ProjectAnalyzer(temp_project_dir, temp_spec_dir)


# =============================================================================
# PROJECTANALYZER INITIALIZATION TESTS
# =============================================================================

class TestProjectAnalyzerInit:
    """Tests for ProjectAnalyzer.__init__"""

    def test_init_with_project_and_spec_dir(self, tmp_path: Path):
        """Test initialization with both project and spec directories."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        analyzer = ProjectAnalyzer(project_dir, spec_dir)

        assert analyzer.project_dir == project_dir.resolve()
        assert analyzer.spec_dir == spec_dir.resolve()
        assert isinstance(analyzer.profile, SecurityProfile)
        assert analyzer.parser is not None

    def test_init_with_project_dir_only(self, tmp_path: Path):
        """Test initialization with project directory only."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        analyzer = ProjectAnalyzer(project_dir)

        assert analyzer.project_dir == project_dir.resolve()
        assert analyzer.spec_dir is None

    def test_init_resolves_paths(self, tmp_path: Path):
        """Test that paths are resolved to absolute paths."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create with relative path components
        analyzer = ProjectAnalyzer(project_dir / ".." / "project")

        # Should be resolved without .. components
        assert ".." not in str(analyzer.project_dir)
        assert analyzer.project_dir.is_absolute()


# =============================================================================
# GET_PROFILE_PATH TESTS
# =============================================================================

class TestGetProfilePath:
    """Tests for ProjectAnalyzer.get_profile_path"""

    def test_profile_path_with_spec_dir(self, analyzer):
        """Test profile path when spec_dir is set."""
        profile_path = analyzer.get_profile_path()

        assert profile_path == analyzer.spec_dir / ProjectAnalyzer.PROFILE_FILENAME

    def test_profile_path_without_spec_dir(self, temp_project_dir: Path):
        """Test profile path when spec_dir is None."""
        analyzer = ProjectAnalyzer(temp_project_dir)
        profile_path = analyzer.get_profile_path()

        assert profile_path == temp_project_dir / ProjectAnalyzer.PROFILE_FILENAME


# =============================================================================
# LOAD_PROFILE TESTS
# =============================================================================

class TestLoadProfile:
    """Tests for ProjectAnalyzer.load_profile"""

    def test_load_profile_from_file(self, analyzer: ProjectAnalyzer, sample_profile: SecurityProfile):
        """Test loading an existing profile from disk."""
        profile_path = analyzer.get_profile_path()
        profile_path.parent.mkdir(parents=True, exist_ok=True)

        # Save a profile
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(sample_profile.to_dict(), f)

        # Load it
        loaded = analyzer.load_profile()

        assert loaded is not None
        assert loaded.project_dir == sample_profile.project_dir
        assert loaded.project_hash == sample_profile.project_hash
        assert loaded.base_commands == sample_profile.base_commands

    def test_load_profile_returns_none_when_not_exists(self, analyzer: ProjectAnalyzer):
        """Test that load_profile returns None when file doesn't exist."""
        loaded = analyzer.load_profile()
        assert loaded is None

    def test_load_profile_handles_invalid_json(self, analyzer: ProjectAnalyzer):
        """Test that load_profile returns None for invalid JSON."""
        profile_path = analyzer.get_profile_path()
        profile_path.parent.mkdir(parents=True, exist_ok=True)

        # Write invalid JSON
        profile_path.write_text("{invalid json")

        loaded = analyzer.load_profile()
        assert loaded is None

    def test_load_profile_handles_os_error(self, analyzer: ProjectAnalyzer):
        """Test that load_profile returns None on OS errors."""
        profile_path = analyzer.get_profile_path()
        profile_path.parent.mkdir(parents=True, exist_ok=True)

        # Write valid JSON but mock open to raise OSError
        profile_path.write_text("{}")

        with patch("builtins.open", side_effect=OSError("Permission denied")):
            loaded = analyzer.load_profile()
            assert loaded is None


# =============================================================================
# SAVE_PROFILE TESTS
# =============================================================================

class TestSaveProfile:
    """Tests for ProjectAnalyzer.save_profile"""

    def test_save_profile_creates_directory(self, analyzer: ProjectAnalyzer, sample_profile: SecurityProfile):
        """Test that save_profile creates parent directories."""
        profile_path = analyzer.get_profile_path()

        # Remove parent directory
        if profile_path.parent.exists():
            profile_path.parent.rmdir()

        analyzer.save_profile(sample_profile)

        assert profile_path.exists()
        assert profile_path.parent.exists()

    def test_save_profile_writes_valid_json(self, analyzer: ProjectAnalyzer, sample_profile: SecurityProfile):
        """Test that save_profile writes valid JSON."""
        analyzer.save_profile(sample_profile)

        profile_path = analyzer.get_profile_path()

        with open(profile_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["project_dir"] == sample_profile.project_dir
        assert data["project_hash"] == sample_profile.project_hash

    def test_save_profile_overwrites_existing(self, analyzer: ProjectAnalyzer, sample_profile: SecurityProfile):
        """Test that save_profile overwrites existing profile."""
        # Save initial profile
        sample_profile.project_hash = "hash1"
        analyzer.save_profile(sample_profile)

        # Save updated profile
        sample_profile.project_hash = "hash2"
        analyzer.save_profile(sample_profile)

        # Load and verify
        loaded = analyzer.load_profile()
        assert loaded.project_hash == "hash2"


# =============================================================================
# COMPUTE_PROJECT_HASH TESTS
# =============================================================================

class TestComputeProjectHash:
    """Tests for ProjectAnalyzer.compute_project_hash"""

    def test_hash_with_package_json(self, temp_project_dir: Path):
        """Test hash computation with package.json."""
        analyzer = ProjectAnalyzer(temp_project_dir)

        hash1 = analyzer.compute_project_hash()

        # Modify package.json
        (temp_project_dir / "package.json").write_text('{"name": "modified"}')

        hash2 = analyzer.compute_project_hash()

        assert hash1 != hash2

    def test_hash_with_pyproject_toml(self, temp_project_dir: Path):
        """Test hash computation with pyproject.toml."""
        (temp_project_dir / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'")

        analyzer = ProjectAnalyzer(temp_project_dir)
        hash1 = analyzer.compute_project_hash()

        # Modify file
        (temp_project_dir / "pyproject.toml").write_text("[tool.poetry]\nname = 'modified'")

        hash2 = analyzer.compute_project_hash()

        assert hash1 != hash2

    def test_hash_with_dockerfile(self, temp_project_dir: Path):
        """Test hash computation with Dockerfile."""
        (temp_project_dir / "Dockerfile").write_text("FROM python:3.11")

        analyzer = ProjectAnalyzer(temp_project_dir)
        hash1 = analyzer.compute_project_hash()

        # Modify Dockerfile
        (temp_project_dir / "Dockerfile").write_text("FROM python:3.12")

        hash2 = analyzer.compute_project_hash()

        assert hash1 != hash2

    def test_hash_with_makefile(self, temp_project_dir: Path):
        """Test hash computation with Makefile."""
        (temp_project_dir / "Makefile").write_text("build:\n\techo building")

        analyzer = ProjectAnalyzer(temp_project_dir)
        hash1 = analyzer.compute_project_hash()

        # Modify Makefile
        (temp_project_dir / "Makefile").write_text("build:\n\techo modified")

        hash2 = analyzer.compute_project_hash()

        assert hash1 != hash2

    def test_hash_with_glob_patterns(self, temp_project_dir: Path):
        """Test hash computation with glob patterns (*.csproj, *.sln, etc.)."""
        # Create a .csproj file in a subdirectory
        src_dir = temp_project_dir / "csharp"
        src_dir.mkdir(exist_ok=True)
        (src_dir / "project.csproj").write_text("<Project></Project>")

        analyzer = ProjectAnalyzer(temp_project_dir)
        hash1 = analyzer.compute_project_hash()

        # Modify the file
        (src_dir / "project.csproj").write_text("<Project><Modified/></Project>")

        hash2 = analyzer.compute_project_hash()

        assert hash1 != hash2

    def test_hash_fallback_to_source_count(self, temp_project_dir: Path):
        """Test hash falls back to source file count when no config files."""
        # Remove package.json if it exists
        pkg_json = temp_project_dir / "package.json"
        if pkg_json.exists():
            pkg_json.unlink()

        analyzer = ProjectAnalyzer(temp_project_dir)
        hash1 = analyzer.compute_project_hash()

        # Add a new Python file
        (temp_project_dir / "new_file.py").write_text("# new file")

        hash2 = analyzer.compute_project_hash()

        assert hash1 != hash2

    def test_hash_is_consistent(self, temp_project_dir: Path):
        """Test that hash is consistent for unchanged project."""
        analyzer = ProjectAnalyzer(temp_project_dir)

        hash1 = analyzer.compute_project_hash()
        hash2 = analyzer.compute_project_hash()

        assert hash1 == hash2

    def test_hash_includes_project_name(self, tmp_path: Path):
        """Test that hash includes project directory name."""
        project1 = tmp_path / "project1"
        project2 = tmp_path / "project2"
        project1.mkdir()
        project2.mkdir()

        # Create identical files
        (project1 / "README.md").write_text("# Test")
        (project2 / "README.md").write_text("# Test")

        analyzer1 = ProjectAnalyzer(project1)
        analyzer2 = ProjectAnalyzer(project2)

        hash1 = analyzer1.compute_project_hash()
        hash2 = analyzer2.compute_project_hash()

        # Hashes should differ because project names differ
        assert hash1 != hash2


# =============================================================================
# SHOULD_REANALYZE TESTS
# =============================================================================

class TestShouldReanalyze:
    """Tests for ProjectAnalyzer.should_reanalyze"""

    def test_should_reanalyze_with_changed_hash(self, analyzer: ProjectAnalyzer, sample_profile: SecurityProfile):
        """Test re-analysis is triggered when hash changes."""
        sample_profile.project_hash = "old_hash"

        result = analyzer.should_reanalyze(sample_profile)

        assert result is True

    def test_should_not_reanalyze_with_same_hash(self, analyzer: ProjectAnalyzer, sample_profile: SecurityProfile):
        """Test re-analysis is not triggered when hash matches."""
        current_hash = analyzer.compute_project_hash()
        sample_profile.project_hash = current_hash

        result = analyzer.should_reanalyze(sample_profile)

        assert result is False

    def test_should_reanalyze_valid_inherited_profile(self, tmp_path: Path):
        """Test that valid inherited profiles don't trigger re-analysis."""
        # Create parent project
        parent_dir = tmp_path / "parent"
        parent_dir.mkdir()

        # Create child project (worktree)
        child_dir = parent_dir / "child"
        child_dir.mkdir()

        # Create parent profile
        parent_profile = SecurityProfile()
        parent_profile.project_dir = str(parent_dir)
        parent_profile.project_hash = "parent_hash"
        parent_profile_path = parent_dir / ProjectAnalyzer.PROFILE_FILENAME
        with open(parent_profile_path, "w") as f:
            json.dump(parent_profile.to_dict(), f)

        # Create child profile with inherited_from
        child_profile = SecurityProfile()
        child_profile.inherited_from = str(parent_dir)

        analyzer = ProjectAnalyzer(child_dir)
        result = analyzer.should_reanalyze(child_profile)

        # Should not reanalyze inherited profile
        assert result is False

    def test_should_reanalyze_invalid_inherited_profile(self, tmp_path: Path):
        """Test that invalid inherited profiles trigger re-analysis."""
        # Create child profile with non-existent parent
        child_dir = tmp_path / "child"
        child_dir.mkdir()

        child_profile = SecurityProfile()
        child_profile.inherited_from = str(tmp_path / "nonexistent")
        child_profile.project_hash = "some_hash"

        analyzer = ProjectAnalyzer(child_dir)
        result = analyzer.should_reanalyze(child_profile)

        # Should reanalyze when parent doesn't exist
        assert result is True

    def test_should_reanalyze_inherited_not_descendant(self, tmp_path: Path):
        """Test that inherited profile from non-parent triggers re-analysis."""
        # Create two unrelated projects
        project1 = tmp_path / "project1"
        project2 = tmp_path / "project2"
        project1.mkdir()
        project2.mkdir()

        # Create profile in project1
        profile1 = SecurityProfile()
        profile1_path = project1 / ProjectAnalyzer.PROFILE_FILENAME
        with open(profile1_path, "w") as f:
            json.dump(profile1.to_dict(), f)

        # Project2 tries to inherit from project1 (not a parent)
        profile2 = SecurityProfile()
        profile2.inherited_from = str(project1)
        profile2.project_hash = "some_hash"

        analyzer = ProjectAnalyzer(project2)
        result = analyzer.should_reanalyze(profile2)

        # Should reanalyze when not a descendant
        assert result is True


# =============================================================================
# _IS_DESCENDANT_OF TESTS
# =============================================================================

class TestIsDescendantOf:
    """Tests for ProjectAnalyzer._is_descendant_of"""

    def test_is_descendant_direct_child(self, tmp_path: Path):
        """Test direct child is detected as descendant."""
        parent = tmp_path / "parent"
        child = parent / "child"
        parent.mkdir()
        child.mkdir()

        analyzer = ProjectAnalyzer(tmp_path)
        result = analyzer._is_descendant_of(child, parent)

        assert result is True

    def test_is_descendant_nested_child(self, tmp_path: Path):
        """Test nested child is detected as descendant."""
        parent = tmp_path / "parent"
        child = parent / "a" / "b" / "c"
        child.mkdir(parents=True)

        analyzer = ProjectAnalyzer(tmp_path)
        result = analyzer._is_descendant_of(child, parent)

        assert result is True

    def test_is_not_descendant_sibling(self, tmp_path: Path):
        """Test sibling is not detected as descendant."""
        parent = tmp_path / "parent"
        sibling = tmp_path / "sibling"
        parent.mkdir()
        sibling.mkdir()

        analyzer = ProjectAnalyzer(tmp_path)
        result = analyzer._is_descendant_of(sibling, parent)

        assert result is False

    def test_is_not_descendant_unrelated(self, tmp_path: Path):
        """Test unrelated path is not detected as descendant."""
        path1 = tmp_path / "path1"
        path2 = tmp_path / "path2"
        path1.mkdir()
        path2.mkdir()

        analyzer = ProjectAnalyzer(tmp_path)
        result = analyzer._is_descendant_of(path2, path1)

        assert result is False

    def test_is_descendant_same_path(self, tmp_path: Path):
        """Test that a path is considered descendant of itself."""
        path = tmp_path / "same"
        path.mkdir()

        analyzer = ProjectAnalyzer(tmp_path)
        result = analyzer._is_descendant_of(path, path)

        assert result is True

    def test_is_descendant_resolves_symlinks(self, tmp_path: Path):
        """Test that symlinks are resolved."""
        parent = tmp_path / "parent"
        parent.mkdir()

        link = tmp_path / "link"
        link.symlink_to(parent)

        analyzer = ProjectAnalyzer(tmp_path)
        result = analyzer._is_descendant_of(link, parent)

        # After resolution, link should point to parent
        assert result is True


# =============================================================================
# ANALYZE TESTS
# =============================================================================

class TestAnalyze:
    """Tests for ProjectAnalyzer.analyze"""

    def test_analyze_creates_new_profile(self, analyzer: ProjectAnalyzer):
        """Test analyze creates a new profile."""
        with patch("sys.stdout"):  # Suppress print output
            profile = analyzer.analyze()

        assert isinstance(profile, SecurityProfile)
        assert profile.project_dir == str(analyzer.project_dir)
        assert profile.project_hash == analyzer.compute_project_hash()
        assert len(profile.base_commands) > 0

    def test_analyze_saves_profile(self, analyzer: ProjectAnalyzer):
        """Test analyze saves profile to disk."""
        with patch("sys.stdout"):
            profile = analyzer.analyze()

        # Load from disk
        loaded = analyzer.load_profile()

        assert loaded is not None
        assert loaded.project_hash == profile.project_hash

    def test_analyze_uses_cached_profile(self, analyzer: ProjectAnalyzer):
        """Test analyze uses cached profile when unchanged."""
        with patch("sys.stdout"):
            profile1 = analyzer.analyze()

        # Analyze again without force
        with patch("sys.stdout") as mock_stdout:
            profile2 = analyzer.analyze()

        assert profile1.project_hash == profile2.project_hash
        # Should print "Using cached" message
        assert any("cached" in str(call).lower() for call in mock_stdout.write.call_args_list)

    def test_analyze_force_recreates_profile(self, analyzer: ProjectAnalyzer):
        """Test analyze with force recreates profile."""
        with patch("sys.stdout"):
            profile1 = analyzer.analyze()
            original_hash = profile1.project_hash

        # Force re-analysis
        with patch("sys.stdout") as mock_stdout:
            profile2 = analyzer.analyze(force=True)

        # Hashes should be the same (project unchanged) but profile recreated
        assert profile2.project_hash == original_hash
        # Should print "Analyzing" message
        output = "".join(str(call) for call in mock_stdout.write.call_args_list)
        assert "analyzing" in output.lower()

    def test_analyze_detects_stack(self, analyzer: ProjectAnalyzer):
        """Test analyze detects technology stack."""
        # Create package.json for Node.js detection
        (analyzer.project_dir / "package.json").write_text('{"name": "test"}')

        with patch("sys.stdout"):
            profile = analyzer.analyze()

        assert profile.detected_stack is not None
        assert isinstance(profile.detected_stack, TechnologyStack)

    def test_analyze_sets_timestamp(self, analyzer: ProjectAnalyzer):
        """Test analyze sets created_at timestamp."""
        with patch("sys.stdout"):
            profile = analyzer.analyze()

        assert profile.created_at != ""
        # Should be valid ISO format
        datetime.fromisoformat(profile.created_at)

    @patch("project.analyzer.StructureAnalyzer")
    @patch("project.analyzer.FrameworkDetector")
    @patch("project.analyzer.StackDetector")
    def test_analyze_orchestration(self, mock_stack_detector, mock_framework_detector,
                                   mock_structure_analyzer, analyzer: ProjectAnalyzer):
        """Test analyze orchestrates all detection steps."""
        from project.models import TechnologyStack

        # Setup mocks with proper TechnologyStack
        mock_stack = TechnologyStack(
            languages=["python"],
            package_managers=["pip"]
        )

        mock_stack_inst = MagicMock()
        mock_stack_inst.detect_all.return_value = mock_stack
        mock_stack_detector.return_value = mock_stack_inst

        mock_framework_inst = MagicMock()
        mock_framework_inst.detect_all.return_value = ["django"]
        mock_framework_detector.return_value = mock_framework_inst

        from project.models import CustomScripts
        mock_scripts = CustomScripts(npm_scripts=["build"])
        mock_structure_inst = MagicMock()
        mock_structure_inst.analyze.return_value = (mock_scripts, set(), set())
        mock_structure_analyzer.return_value = mock_structure_inst

        with patch("sys.stdout"):
            profile = analyzer.analyze()

        # Verify all detectors were called
        mock_stack_inst.detect_all.assert_called_once()
        mock_framework_inst.detect_all.assert_called_once()
        mock_structure_inst.analyze.assert_called_once()

    def test_analyze_with_inherited_profile(self, tmp_path: Path):
        """Test analyze uses inherited profile when valid."""
        parent_dir = tmp_path / "parent"
        child_dir = parent_dir / "child"
        parent_dir.mkdir()
        child_dir.mkdir()

        # Create parent profile
        parent_profile = SecurityProfile()
        parent_profile.project_dir = str(parent_dir)
        parent_profile.project_hash = "parent_hash"
        parent_profile_path = parent_dir / ProjectAnalyzer.PROFILE_FILENAME
        with open(parent_profile_path, "w") as f:
            json.dump(parent_profile.to_dict(), f)

        # Create inherited profile in child
        child_profile_path = child_dir / ProjectAnalyzer.PROFILE_FILENAME
        child_profile = SecurityProfile()
        child_profile.inherited_from = str(parent_dir)
        child_profile.project_hash = "child_hash"
        with open(child_profile_path, "w") as f:
            json.dump(child_profile.to_dict(), f)

        analyzer = ProjectAnalyzer(child_dir)

        with patch("sys.stdout") as mock_stdout:
            profile = analyzer.analyze()

        # Should use inherited profile
        assert profile.inherited_from == str(parent_dir)
        output = "".join(str(call) for call in mock_stdout.write.call_args_list)
        assert "inherited" in output.lower()


# =============================================================================
# UTILITY FUNCTION TESTS
# =============================================================================

class TestGetOrCreateProfile:
    """Tests for get_or_create_profile utility function"""

    def test_get_or_create_profile_new(self, temp_project_dir: Path, temp_spec_dir: Path):
        """Test get_or_create_profile creates new profile."""
        from project import get_or_create_profile

        with patch("sys.stdout"):
            profile = get_or_create_profile(temp_project_dir, temp_spec_dir)

        assert isinstance(profile, SecurityProfile)
        assert profile.project_dir == str(temp_project_dir.resolve())

    def test_get_or_create_profile_existing(self, temp_project_dir: Path, temp_spec_dir: Path):
        """Test get_or_create_profile uses existing profile."""
        from project import get_or_create_profile

        with patch("sys.stdout"):
            profile1 = get_or_create_profile(temp_project_dir, temp_spec_dir)

        # Call again
        with patch("sys.stdout"):
            profile2 = get_or_create_profile(temp_project_dir, temp_spec_dir)

        # Should use cached profile
        assert profile1.project_hash == profile2.project_hash

    def test_get_or_create_profile_force_reanalyze(self, temp_project_dir: Path, temp_spec_dir: Path):
        """Test get_or_create_profile with force_reanalyze."""
        from project import get_or_create_profile

        with patch("sys.stdout"):
            profile1 = get_or_create_profile(temp_project_dir, temp_spec_dir)

        # Force re-analysis
        with patch("sys.stdout"):
            profile2 = get_or_create_profile(temp_project_dir, temp_spec_dir, force_reanalyze=True)

        # Should have new timestamps but same hash (project unchanged)
        assert profile2.created_at != profile1.created_at


class TestIsCommandAllowed:
    """Tests for is_command_allowed utility function"""

    def test_is_command_allowed_base_command(self):
        """Test is_command_allowed with base command."""
        from project import is_command_allowed

        profile = SecurityProfile()
        profile.base_commands = {"git", "ls", "cat"}

        allowed, reason = is_command_allowed("git", profile)

        assert allowed is True
        assert reason == ""

    def test_is_command_allowed_stack_command(self):
        """Test is_command_allowed with stack command."""
        from project import is_command_allowed

        profile = SecurityProfile()
        profile.stack_commands = {"npm", "node"}

        allowed, reason = is_command_allowed("npm", profile)

        assert allowed is True
        assert reason == ""

    def test_is_command_allowed_not_allowed(self):
        """Test is_command_allowed with disallowed command."""
        from project import is_command_allowed

        profile = SecurityProfile()
        profile.base_commands = {"git", "ls"}

        allowed, reason = is_command_allowed("rm", profile)

        assert allowed is False
        assert "not in the allowed commands" in reason.lower()

    def test_is_command_allowed_shell_script(self):
        """Test is_command_allowed with shell script."""
        from project import is_command_allowed

        profile = SecurityProfile()
        profile.custom_scripts.shell_scripts = ["deploy.sh", "build.sh"]
        profile.script_commands = {"./deploy.sh"}

        allowed, reason = is_command_allowed("./deploy.sh", profile)

        assert allowed is True
        assert reason == ""

    def test_is_command_allowed_absolute_path(self):
        """Test is_command_allowed with absolute path."""
        from project import is_command_allowed

        profile = SecurityProfile()
        profile.custom_scripts.shell_scripts = ["test.sh"]
        profile.script_commands = {"/usr/local/bin/test.sh"}

        allowed, reason = is_command_allowed("/usr/local/bin/test.sh", profile)

        assert allowed is True
        assert reason == ""

    def test_is_command_allowed_all_command_types(self):
        """Test is_command_allowed checks all command sets."""
        from project import is_command_allowed

        profile = SecurityProfile()
        profile.base_commands = {"git"}
        profile.stack_commands = {"npm"}
        profile.script_commands = {"./build.sh"}
        profile.custom_commands = {"custom-tool"}

        # Test each set
        assert is_command_allowed("git", profile)[0] is True
        assert is_command_allowed("npm", profile)[0] is True
        assert is_command_allowed("./build.sh", profile)[0] is True
        assert is_command_allowed("custom-tool", profile)[0] is True
        assert is_command_allowed("disallowed", profile)[0] is False


class TestNeedsValidation:
    """Tests for needs_validation utility function"""

    def test_needs_validation_rm(self):
        """Test needs_validation for 'rm' command."""
        from project import needs_validation

        result = needs_validation("rm")

        assert result == "validate_rm"

    def test_needs_validation_chmod(self):
        """Test needs_validation for 'chmod' command."""
        from project import needs_validation

        result = needs_validation("chmod")

        assert result == "validate_chmod"

    def test_needs_validation_kill(self):
        """Test needs_validation for 'kill' command."""
        from project import needs_validation

        result = needs_validation("kill")

        assert result == "validate_kill"

    def test_needs_validation_pkill(self):
        """Test needs_validation for 'pkill' command."""
        from project import needs_validation

        result = needs_validation("pkill")

        assert result == "validate_pkill"

    def test_needs_validation_killall(self):
        """Test needs_validation for 'killall' command."""
        from project import needs_validation

        result = needs_validation("killall")

        assert result == "validate_killall"

    def test_needs_validation_shell_interpreters(self):
        """Test needs_validation for shell interpreters."""
        from project import needs_validation

        assert needs_validation("bash") == "validate_shell_c"
        assert needs_validation("sh") == "validate_shell_c"
        assert needs_validation("zsh") == "validate_shell_c"

    def test_needs_validation_none(self):
        """Test needs_validation returns None for non-validated commands."""
        from project import needs_validation

        result = needs_validation("git")

        assert result is None

    def test_needs_validation_all_validated_commands(self):
        """Test that all commands in VALIDATED_COMMANDS are detected."""
        from project import needs_validation, VALIDATED_COMMANDS

        for cmd, expected_func in VALIDATED_COMMANDS.items():
            result = needs_validation(cmd)
            assert result == expected_func, f"Failed for {cmd}"
