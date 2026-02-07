"""Tests for discovery module

NOTE: These tests run actual discovery scripts - integration tests marked as slow.
Can be excluded with: pytest -m "not slow"
"""

import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from spec.discovery import get_project_index_stats, run_discovery_script

pytestmark = pytest.mark.slow


class TestRunDiscoveryScript:
    """Tests for run_discovery_script function"""

    def test_copies_existing_index_from_auto_claude(self, tmp_path):
        """Test copying existing index from auto-claude directory"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude_dir = project_dir / "auto-claude"
        auto_claude_dir.mkdir()
        auto_build_index = auto_claude_dir / "project_index.json"
        auto_build_index.write_text('{"project_type": "test"}', encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        success, message = run_discovery_script(project_dir, spec_dir)

        assert success is True
        assert "Copied existing" in message
        assert (spec_dir / "project_index.json").exists()

    def test_returns_success_when_index_already_exists(self, tmp_path):
        """Test returns success when spec_index already exists"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        existing_index = spec_dir / "project_index.json"
        existing_index.write_text('{"project_type": "existing"}', encoding="utf-8")

        success, message = run_discovery_script(project_dir, spec_dir)

        assert success is True
        assert "already exists" in message

    def test_runs_analyzer_script(self, tmp_path):
        """Test running the analyzer script"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create a mock analyzer script path
        analyzer_path = tmp_path / "analyzer.py"
        analyzer_path.write_text("# mock analyzer", encoding="utf-8")

        # Mock subprocess.run to simulate successful analyzer run
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Analyzer output"
        mock_result.stderr = ""

        # Create the index file after subprocess runs (simulating analyzer)
        def side_effect(*args, **kwargs):
            index_file = spec_dir / "project_index.json"
            index_file.write_text('{"project_type": "analyzed"}', encoding="utf-8")
            return mock_result

        # Patch Path(__file__).parent to return our mock script location
        with patch("spec.discovery.Path") as mock_path:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_instance.__truediv__ = MagicMock(return_value=analyzer_path)
            mock_path_instance.parent.parent.parent = tmp_path
            mock_path.return_value = mock_path_instance

            with patch("subprocess.run", side_effect=side_effect):
                success, message = run_discovery_script(project_dir, spec_dir)

        assert success is True
        assert "Created" in message

    def test_returns_failure_when_script_not_found(self, tmp_path):
        """Test handling missing analyzer script"""
        # Create a temporary directory structure where we know the script won't exist
        import tempfile
        import shutil

        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "project"
            project_dir.mkdir()
            spec_dir = Path(temp_dir) / "spec"
            spec_dir.mkdir()

            # Patch the Path class to make __file__ point to a non-existent location
            # so the script check will fail
            original_path = Path

            class FakePath:
                """A fake Path that makes script_path not exist"""
                def __init__(self, *args, **kwargs):
                    if args and args[0] == "":
                        # When Path() is called with empty string in the module
                        self._path = original_path(temp_dir)
                    else:
                        self._path = original_path(*args, **kwargs) if args else original_path(temp_dir)

                def __truediv__(self, other):
                    result = FakePath()
                    result._path = self._path / other
                    return result

                @property
                def parent(self):
                    result = FakePath()
                    result._path = self._path.parent
                    return result

                def exists(self):
                    # Make the script path not exist
                    return False

                def __getattr__(self, name):
                    return getattr(self._path, name)

                def __fspath__(self):
                    return self._path.__fspath__()

                def __str__(self):
                    return str(self._path)

            with patch("spec.discovery.Path", FakePath):
                success, message = run_discovery_script(project_dir, spec_dir)

            # Should fail because analyzer script doesn't exist
            assert success is False
            # The error message should indicate failure
            assert message and len(message) > 0

    def test_handles_script_timeout(self, tmp_path):
        """Test handling script timeout"""
        from subprocess import TimeoutExpired

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create a mock script path
        analyzer_path = tmp_path / "analyzer.py"
        analyzer_path.write_text("# mock", encoding="utf-8")

        with patch("spec.discovery.Path") as mock_path:
            # Configure Path to return our mock script
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_instance.__truediv__ = MagicMock(return_value=analyzer_path)
            mock_path.return_value = mock_path_instance

            with patch("subprocess.run", side_effect=TimeoutExpired("cmd", 300)):
                success, message = run_discovery_script(project_dir, spec_dir)

        assert success is False
        assert "timed out" in message.lower()

    def test_handles_general_exception(self, tmp_path):
        """Test handling general exceptions"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        analyzer_path = tmp_path / "analyzer.py"
        analyzer_path.write_text("# mock", encoding="utf-8")

        with patch("spec.discovery.Path") as mock_path:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_instance.__truediv__ = MagicMock(return_value=analyzer_path)
            mock_path.return_value = mock_path_instance

            with patch("subprocess.run", side_effect=Exception("Unexpected error")):
                success, message = run_discovery_script(project_dir, spec_dir)

        assert success is False
        assert "Unexpected error" in message

    def test_returns_failure_on_nonzero_exit_code(self, tmp_path):
        """Test handling non-zero exit code from script"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        analyzer_path = tmp_path / "analyzer.py"
        analyzer_path.write_text("# mock", encoding="utf-8")

        with patch("spec.discovery.Path") as mock_path:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_instance.__truediv__ = MagicMock(return_value=analyzer_path)
            mock_path.return_value = mock_path_instance

            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "Error running analyzer"
            mock_result.stdout = ""

            with patch("subprocess.run", return_value=mock_result):
                success, message = run_discovery_script(project_dir, spec_dir)

        assert success is False


class TestGetProjectIndexStats:
    """Tests for get_project_index_stats function"""

    def test_returns_empty_dict_when_no_index(self, tmp_path):
        """Test returns empty dict when index doesn't exist"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = get_project_index_stats(spec_dir)

        assert result == {}

    def test_returns_empty_dict_on_invalid_json(self, tmp_path):
        """Test returns empty dict on invalid JSON"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        index_file = spec_dir / "project_index.json"
        index_file.write_text("{invalid json", encoding="utf-8")

        result = get_project_index_stats(spec_dir)

        assert result == {}

    def test_reads_old_format_with_files_array(self, tmp_path):
        """Test reading old format with top-level files array"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        index_file = spec_dir / "project_index.json"
        old_format = {
            "project_type": "monorepo",
            "files": [{"path": "file1.py"}, {"path": "file2.py"}, {"path": "file3.py"}],
        }
        index_file.write_text(json.dumps(old_format), encoding="utf-8")

        result = get_project_index_stats(spec_dir)

        assert result["file_count"] == 3
        assert result["project_type"] == "monorepo"

    def test_reads_new_format_with_services(self, tmp_path):
        """Test reading new format with services"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        index_file = spec_dir / "project_index.json"
        new_format = {
            "project_type": "monorepo",
            "services": {
                "frontend": {
                    "entry_point": "src/main.tsx",
                    "dependencies": ["react", "vue"],
                    "dev_dependencies": ["vitest", "typescript"],
                    "key_directories": {"src": {}, "components": {}},
                    "test_directory": "tests",
                    "dockerfile": "Dockerfile.frontend",
                },
                "backend": {
                    "dependencies": ["fastapi", "uvicorn", "pydantic"],
                    "key_directories": {"api": {}, "models": {}},
                    "dockerfile": "Dockerfile.backend",
                },
            },
            "infrastructure": {
                "docker_compose": ["docker-compose.yml"],
                "dockerfiles": ["Dockerfile"],
            },
            "conventions": {
                "linting": "eslint.config.js",
                "formatting": "prettier.config.js",
                "git_hooks": ".husky",
            },
        }
        index_file.write_text(json.dumps(new_format), encoding="utf-8")

        result = get_project_index_stats(spec_dir)

        assert result["file_count"] > 0
        assert result["project_type"] == "monorepo"

    def test_handles_exception_on_read_error(self, tmp_path):
        """Test returns empty dict on read error"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        index_file = spec_dir / "project_index.json"
        index_file.write_text('{"test": "data"}', encoding="utf-8")

        with patch("builtins.open", side_effect=OSError("Read error")):
            result = get_project_index_stats(spec_dir)

        assert result == {}

    def test_default_project_type_when_missing(self, tmp_path):
        """Test default project type when not specified"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        index_file = spec_dir / "project_index.json"
        index_file.write_text('{"files": []}', encoding="utf-8")

        result = get_project_index_stats(spec_dir)

        assert result["project_type"] == "unknown"


class TestGetProjectIndexStatsNewFormatCoverage:
    """Additional tests for new format coverage - lines 86-127"""

    def test_estimates_files_from_service_entry_point(self, tmp_path):
        """Test file count estimation with entry_point (line 91-92)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        index_file = spec_dir / "project_index.json"

        new_format = {
            "project_type": "monorepo",
            "services": {
                "frontend": {
                    "entry_point": "src/main.tsx",  # Should add 1 file
                }
            },
        }
        index_file.write_text(json.dumps(new_format), encoding="utf-8")

        result = get_project_index_stats(spec_dir)

        # Base: 3 (config files) + 1 (entry_point) = 4
        assert result["file_count"] >= 4

    def test_estimates_files_from_dependencies(self, tmp_path):
        """Test file count estimation from dependencies (line 95-98)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        index_file = spec_dir / "project_index.json"

        new_format = {
            "project_type": "monorepo",
            "services": {
                "frontend": {
                    "dependencies": ["dep1", "dep2", "dep3", "dep4"],  # 4 deps // 2 = 2 files
                    "dev_dependencies": ["dev1", "dev2", "dev3", "dev4"],  # 4 deps // 4 = 1 file
                }
            },
        }
        index_file.write_text(json.dumps(new_format), encoding="utf-8")

        result = get_project_index_stats(spec_dir)

        # Base: 3 (config) + 2 (deps) + 1 (dev_deps) = 6
        assert result["file_count"] >= 6

    def test_estimates_files_from_key_directories(self, tmp_path):
        """Test file count estimation from key_directories (line 101-102)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        index_file = spec_dir / "project_index.json"

        new_format = {
            "project_type": "monorepo",
            "services": {
                "frontend": {
                    "key_directories": {
                        "src": {},
                        "components": {},
                        "utils": {},
                    }
                }
            },
        }
        index_file.write_text(json.dumps(new_format), encoding="utf-8")

        result = get_project_index_stats(spec_dir)

        # Base: 3 (config) + 3 dirs * 8 = 27
        assert result["file_count"] >= 27

    def test_estimates_files_from_dockerfile(self, tmp_path):
        """Test file count estimation with dockerfile (line 105-106)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        index_file = spec_dir / "project_index.json"

        new_format = {
            "project_type": "monorepo",
            "services": {
                "frontend": {
                    "dockerfile": "Dockerfile.frontend",
                }
            },
        }
        index_file.write_text(json.dumps(new_format), encoding="utf-8")

        result = get_project_index_stats(spec_dir)

        # Base: 3 (config) + 1 (dockerfile) = 4
        assert result["file_count"] >= 4

    def test_estimates_files_from_test_directory(self, tmp_path):
        """Test file count estimation with test_directory (line 107-108)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        index_file = spec_dir / "project_index.json"

        new_format = {
            "project_type": "monorepo",
            "services": {
                "frontend": {
                    "test_directory": "tests",
                }
            },
        }
        index_file.write_text(json.dumps(new_format), encoding="utf-8")

        result = get_project_index_stats(spec_dir)

        # Base: 3 (config) + 3 (test files) = 6
        assert result["file_count"] >= 6

    def test_estimates_files_from_infrastructure(self, tmp_path):
        """Test file count estimation from infrastructure (line 111-116)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        index_file = spec_dir / "project_index.json"

        new_format = {
            "project_type": "monorepo",
            "services": {},
            "infrastructure": {
                "docker_compose": ["docker-compose.yml", "docker-compose.dev.yml"],
                "dockerfiles": ["Dockerfile", "Dockerfile.prod"],
            },
        }
        index_file.write_text(json.dumps(new_format), encoding="utf-8")

        result = get_project_index_stats(spec_dir)

        # Should count infrastructure files
        assert result["file_count"] >= 4

    def test_estimates_files_from_conventions_linting(self, tmp_path):
        """Test file count estimation from linting convention (line 121-122)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        index_file = spec_dir / "project_index.json"

        new_format = {
            "project_type": "monorepo",
            "services": {},
            "conventions": {
                "linting": "eslint.config.js",
            },
        }
        index_file.write_text(json.dumps(new_format), encoding="utf-8")

        result = get_project_index_stats(spec_dir)

        assert result["file_count"] >= 1

    def test_estimates_files_from_conventions_formatting(self, tmp_path):
        """Test file count estimation from formatting convention (line 123-124)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        index_file = spec_dir / "project_index.json"

        new_format = {
            "project_type": "monorepo",
            "services": {},
            "conventions": {
                "formatting": "prettier.config.js",
            },
        }
        index_file.write_text(json.dumps(new_format), encoding="utf-8")

        result = get_project_index_stats(spec_dir)

        assert result["file_count"] >= 1

    def test_estimates_files_from_conventions_git_hooks(self, tmp_path):
        """Test file count estimation from git_hooks convention (line 125-126)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        index_file = spec_dir / "project_index.json"

        new_format = {
            "project_type": "monorepo",
            "services": {},
            "conventions": {
                "git_hooks": ".husky",
            },
        }
        index_file.write_text(json.dumps(new_format), encoding="utf-8")

        result = get_project_index_stats(spec_dir)

        assert result["file_count"] >= 1

    def test_service_data_not_dict_skips_file_count(self, tmp_path):
        """Test when service_data is not a dict (line 86)"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        index_file = spec_dir / "project_index.json"

        new_format = {
            "project_type": "monorepo",
            "services": {
                "frontend": "not_a_dict",  # Should skip
                "backend": {},  # Empty dict
            },
        }
        index_file.write_text(json.dumps(new_format), encoding="utf-8")

        result = get_project_index_stats(spec_dir)

        # Should still have some files from the empty dict (base config files)
        # and the string value should be skipped
        assert result["file_count"] >= 3  # At least config files

    def test_full_new_format_all_features(self, tmp_path):
        """Test full new format with all features"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        index_file = spec_dir / "project_index.json"

        new_format = {
            "project_type": "monorepo",
            "services": {
                "frontend": {
                    "entry_point": "src/main.tsx",
                    "dependencies": ["react", "vue", "axios"],
                    "dev_dependencies": ["jest", "vitest", "typescript", "eslint"],
                    "key_directories": {"src": {}, "components": {}, "hooks": {}},
                    "test_directory": "tests",
                    "dockerfile": "Dockerfile.frontend",
                },
                "backend": {
                    "dependencies": ["fastapi", "uvicorn"],
                    "key_directories": {"api": {}},
                },
            },
            "infrastructure": {
                "docker_compose": ["docker-compose.yml"],
                "dockerfiles": ["Dockerfile"],
            },
            "conventions": {
                "linting": "eslint.config.js",
                "formatting": "prettier.config.js",
                "git_hooks": ".husky",
            },
        }
        index_file.write_text(json.dumps(new_format), encoding="utf-8")

        result = get_project_index_stats(spec_dir)

        assert result["file_count"] > 0
        assert result["project_type"] == "monorepo"


class TestRunDiscoveryScriptAdditionalCoverage:
    """Additional tests for run_discovery_script - edge cases"""

    def test_script_runs_but_doesnt_create_file(self, tmp_path):
        """Test when script runs but doesn't create index file"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        analyzer_path = tmp_path / "analyzer.py"
        analyzer_path.write_text("# mock", encoding="utf-8")

        # Mock result where script succeeds but file is not created
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Success"
        mock_result.stderr = ""

        with patch("spec.discovery.Path") as mock_path:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_instance.__truediv__ = MagicMock(return_value=analyzer_path)
            mock_path.return_value = mock_path_instance

            with patch("subprocess.run", return_value=mock_result):
                # Don't create the file, simulating script failure
                success, message = run_discovery_script(project_dir, spec_dir)

        assert success is False
        # Should return stderr or stdout
        assert message

    def test_script_returns_nonzero_with_stderr(self, tmp_path):
        """Test when script returns non-zero with stderr message"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        analyzer_path = tmp_path / "analyzer.py"
        analyzer_path.write_text("# mock", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Module not found error"
        mock_result.stdout = ""

        with patch("spec.discovery.Path") as mock_path:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_instance.__truediv__ = MagicMock(return_value=analyzer_path)
            mock_path.return_value = mock_path_instance

            with patch("subprocess.run", return_value=mock_result):
                success, message = run_discovery_script(project_dir, spec_dir)

        assert success is False
        assert "Module not found error" in message

    def test_auto_claude_index_exists_spec_index_doesnt(self, tmp_path):
        """Test copying from auto-claude when spec_index doesn't exist"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()
        auto_index = auto_claude / "project_index.json"
        auto_index.write_text('{"project_type": "test"}', encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        success, message = run_discovery_script(project_dir, spec_dir)

        assert success is True
        assert "Copied existing" in message
        assert (spec_dir / "project_index.json").exists()

    def test_auto_claude_index_exists_spec_index_also_exists(self, tmp_path):
        """Test when both indices exist - spec takes priority"""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        auto_claude = project_dir / "auto-claude"
        auto_claude.mkdir()
        auto_index = auto_claude / "project_index.json"
        auto_index.write_text('{"project_type": "auto"}', encoding="utf-8")

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_index = spec_dir / "project_index.json"
        spec_index.write_text('{"project_type": "spec"}', encoding="utf-8")

        success, message = run_discovery_script(project_dir, spec_dir)

        assert success is True
        assert "already exists" in message
        # Spec index should be unchanged
        with open(spec_index, encoding="utf-8") as f:
            data = json.load(f)
        assert data["project_type"] == "spec"
