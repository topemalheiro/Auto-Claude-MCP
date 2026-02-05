"""Comprehensive tests for structure_analyzer module."""

import json
from pathlib import Path

import pytest

from project.models import CustomScripts
from project.structure_analyzer import StructureAnalyzer


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory for testing."""
    return tmp_path


@pytest.fixture
def structure_analyzer(temp_project_dir: Path) -> StructureAnalyzer:
    """Create a StructureAnalyzer instance for testing."""
    return StructureAnalyzer(temp_project_dir)


class TestStructureAnalyzerInit:
    """Tests for StructureAnalyzer.__init__"""

    def test_init_with_path(self, temp_project_dir: Path):
        """Test initialization with a project directory path."""
        analyzer = StructureAnalyzer(temp_project_dir)
        assert analyzer.project_dir == temp_project_dir.resolve()
        assert isinstance(analyzer.custom_scripts, CustomScripts)
        assert analyzer.custom_commands == set()
        assert analyzer.script_commands == set()

    def test_custom_allowlist_filename(self):
        """Test the custom allowlist filename constant."""
        assert StructureAnalyzer.CUSTOM_ALLOWLIST_FILENAME == ".auto-claude-allowlist"


class TestAnalyze:
    """Tests for StructureAnalyzer.analyze"""

    def test_analyze_returns_tuple(self, structure_analyzer: StructureAnalyzer):
        """Test that analyze returns a tuple."""
        result = structure_analyzer.analyze()
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_analyze_returns_custom_scripts(self, structure_analyzer: StructureAnalyzer):
        """Test that analyze returns CustomScripts object."""
        custom_scripts, _, _ = structure_analyzer.analyze()
        assert isinstance(custom_scripts, CustomScripts)

    def test_analyze_returns_script_commands(self, structure_analyzer: StructureAnalyzer):
        """Test that analyze returns script_commands set."""
        _, script_commands, _ = structure_analyzer.analyze()
        assert isinstance(script_commands, set)

    def test_analyze_returns_custom_commands(self, structure_analyzer: StructureAnalyzer):
        """Test that analyze returns custom_commands set."""
        _, _, custom_commands = structure_analyzer.analyze()
        assert isinstance(custom_commands, set)

    def test_analyze_with_npm_scripts(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test analyze detects npm scripts."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "scripts": {
                "dev": "next dev",
                "build": "next build"
            }
        }))

        custom_scripts, script_commands, custom_commands = structure_analyzer.analyze()
        assert "dev" in custom_scripts.npm_scripts
        assert "build" in custom_scripts.npm_scripts
        assert "npm" in script_commands
        assert "yarn" in script_commands


class TestDetectCustomScripts:
    """Tests for StructureAnalyzer.detect_custom_scripts"""

    def test_detect_custom_scripts_calls_sub_detectors(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test that detect_custom_scripts calls all sub-detectors."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "scripts": {"test": "jest"}
        }))
        (temp_project_dir / "Makefile").write_text("test:\n\techo test")
        (temp_project_dir / "pyproject.toml").write_text("""
[tool.poetry.scripts]
test = "pytest"
""")
        (temp_project_dir / "script.sh").write_text("#!/bin/bash\necho test")

        structure_analyzer.detect_custom_scripts()
        assert len(structure_analyzer.custom_scripts.npm_scripts) > 0
        assert len(structure_analyzer.custom_scripts.make_targets) > 0
        assert len(structure_analyzer.custom_scripts.poetry_scripts) > 0
        assert len(structure_analyzer.custom_scripts.shell_scripts) > 0


class TestDetectNpmScripts:
    """Tests for StructureAnalyzer._detect_npm_scripts"""

    def test_detect_npm_scripts_empty(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test npm script detection with no scripts."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "name": "test",
            "version": "1.0.0"
        }))

        structure_analyzer._detect_npm_scripts()
        assert structure_analyzer.custom_scripts.npm_scripts == []

    def test_detect_npm_scripts_with_scripts(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test npm script detection with scripts."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "scripts": {
                "dev": "next dev",
                "build": "next build",
                "test": "jest",
                "lint": "eslint"
            }
        }))

        structure_analyzer._detect_npm_scripts()
        assert "dev" in structure_analyzer.custom_scripts.npm_scripts
        assert "build" in structure_analyzer.custom_scripts.npm_scripts
        assert "test" in structure_analyzer.custom_scripts.npm_scripts
        assert "lint" in structure_analyzer.custom_scripts.npm_scripts

    def test_detect_npm_scripts_adds_package_managers(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test that npm scripts detection adds package manager commands."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "scripts": {"test": "jest"}
        }))

        structure_analyzer._detect_npm_scripts()
        assert "npm" in structure_analyzer.script_commands
        assert "yarn" in structure_analyzer.script_commands
        assert "pnpm" in structure_analyzer.script_commands
        assert "bun" in structure_analyzer.script_commands

    def test_detect_npm_scripts_no_package_json(self, structure_analyzer: StructureAnalyzer):
        """Test npm script detection without package.json."""
        structure_analyzer._detect_npm_scripts()
        assert structure_analyzer.custom_scripts.npm_scripts == []

    def test_detect_npm_scripts_invalid_json(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test npm script detection with invalid package.json."""
        (temp_project_dir / "package.json").write_text("{invalid json")

        structure_analyzer._detect_npm_scripts()
        assert structure_analyzer.custom_scripts.npm_scripts == []


class TestDetectMakefileTargets:
    """Tests for StructureAnalyzer._detect_makefile_targets"""

    def test_detect_makefile_no_makefile(self, structure_analyzer: StructureAnalyzer):
        """Test Makefile target detection without Makefile."""
        structure_analyzer._detect_makefile_targets()
        assert structure_analyzer.custom_scripts.make_targets == []

    def test_detect_makefile_with_targets(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test Makefile target detection with valid targets."""
        (temp_project_dir / "Makefile").write_text("""
.PHONY: test build

dev:
	npm run dev

build:
	npm run build

test:
	npm test

install:
	npm install
""")

        structure_analyzer._detect_makefile_targets()
        assert "dev" in structure_analyzer.custom_scripts.make_targets
        assert "build" in structure_analyzer.custom_scripts.make_targets
        assert "test" in structure_analyzer.custom_scripts.make_targets
        assert "install" in structure_analyzer.custom_scripts.make_targets

    def test_detect_makefile_skips_dot_targets(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test that Makefile detection skips dot targets."""
        (temp_project_dir / "Makefile").write_text("""
.SILENT:
.PHONY: test

build:
	npm run build
""")

        structure_analyzer._detect_makefile_targets()
        # Should not include .SILENT or .PHONY
        assert ".SILENT" not in structure_analyzer.custom_scripts.make_targets
        assert ".PHONY" not in structure_analyzer.custom_scripts.make_targets

    def test_detect_makefile_adds_make_command(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test that Makefile detection adds make to script_commands."""
        (temp_project_dir / "Makefile").write_text("""
test:
	echo test
""")

        structure_analyzer._detect_makefile_targets()
        assert "make" in structure_analyzer.script_commands

    def test_detect_makefile_with_dependencies(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test Makefile target detection with dependencies."""
        (temp_project_dir / "Makefile").write_text("""
build: dep1 dep2
	npm run build

dep1:
	echo dep1

dep2:
	echo dep2
""")

        structure_analyzer._detect_makefile_targets()
        assert "build" in structure_analyzer.custom_scripts.make_targets
        assert "dep1" in structure_analyzer.custom_scripts.make_targets
        assert "dep2" in structure_analyzer.custom_scripts.make_targets

    def test_detect_makefile_empty(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test Makefile detection with empty file."""
        (temp_project_dir / "Makefile").write_text("")

        structure_analyzer._detect_makefile_targets()
        assert structure_analyzer.custom_scripts.make_targets == []


class TestDetectPoetryScripts:
    """Tests for StructureAnalyzer._detect_poetry_scripts"""

    def test_detect_poetry_no_pyproject(self, structure_analyzer: StructureAnalyzer):
        """Test Poetry script detection without pyproject.toml."""
        structure_analyzer._detect_poetry_scripts()
        assert structure_analyzer.custom_scripts.poetry_scripts == []

    def test_detect_poetry_tool_poetry_scripts(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test Poetry script detection from [tool.poetry.scripts]."""
        (temp_project_dir / "pyproject.toml").write_text("""
[tool.poetry]
name = "test"

[tool.poetry.scripts]
test = "pytest:main"
lint = "flake8 main"
format = "black main"
""")

        structure_analyzer._detect_poetry_scripts()
        assert "test" in structure_analyzer.custom_scripts.poetry_scripts
        assert "lint" in structure_analyzer.custom_scripts.poetry_scripts
        assert "format" in structure_analyzer.custom_scripts.poetry_scripts

    def test_detect_pep621_scripts(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test script detection from PEP 621 [project.scripts]."""
        (temp_project_dir / "pyproject.toml").write_text("""
[project]
name = "test"

[project.scripts]
mycli = "mypackage.cli:main"
mytool = "mypackage.tool:run"
""")

        structure_analyzer._detect_poetry_scripts()
        assert "mycli" in structure_analyzer.custom_scripts.poetry_scripts
        assert "mytool" in structure_analyzer.custom_scripts.poetry_scripts

    def test_detect_poetry_both_formats(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test Poetry script detection with both formats combined."""
        (temp_project_dir / "pyproject.toml").write_text("""
[tool.poetry]
name = "test"

[tool.poetry.scripts]
poetry-script = "pytest:main"

[project]
name = "test"

[project.scripts]
pep-script = "mypackage.cli:main"
""")

        structure_analyzer._detect_poetry_scripts()
        assert "poetry-script" in structure_analyzer.custom_scripts.poetry_scripts
        assert "pep-script" in structure_analyzer.custom_scripts.poetry_scripts

    def test_detect_poetry_empty_scripts(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test Poetry script detection with empty scripts section."""
        (temp_project_dir / "pyproject.toml").write_text("""
[tool.poetry]
name = "test"

[tool.poetry.scripts]
""")

        structure_analyzer._detect_poetry_scripts()
        assert structure_analyzer.custom_scripts.poetry_scripts == []


class TestDetectShellScripts:
    """Tests for StructureAnalyzer._detect_shell_scripts"""

    def test_detect_shell_scripts_no_scripts(self, structure_analyzer: StructureAnalyzer):
        """Test shell script detection with no scripts."""
        structure_analyzer._detect_shell_scripts()
        assert structure_analyzer.custom_scripts.shell_scripts == []

    def test_detect_shell_scripts_bash(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test shell script detection for .sh files."""
        (temp_project_dir / "deploy.sh").write_text("#!/bin/bash\necho deploy")
        (temp_project_dir / "build.sh").write_text("#!/bin/bash\necho build")

        structure_analyzer._detect_shell_scripts()
        assert "deploy.sh" in structure_analyzer.custom_scripts.shell_scripts
        assert "build.sh" in structure_analyzer.custom_scripts.shell_scripts

    def test_detect_shell_scripts_bash_extension(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test shell script detection for .bash files."""
        (temp_project_dir / "setup.bash").write_text("#!/bin/bash\necho setup")

        structure_analyzer._detect_shell_scripts()
        assert "setup.bash" in structure_analyzer.custom_scripts.shell_scripts

    def test_detect_shell_scripts_adds_to_script_commands(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test that shell scripts are added to script_commands."""
        (temp_project_dir / "deploy.sh").write_text("#!/bin/bash")

        structure_analyzer._detect_shell_scripts()
        assert "./deploy.sh" in structure_analyzer.script_commands

    def test_detect_shell_scripts_nested(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test that shell script detection only looks at root directory."""
        scripts_dir = temp_project_dir / "scripts"
        scripts_dir.mkdir()
        (temp_project_dir / "root.sh").write_text("#!/bin/bash")
        (scripts_dir / "nested.sh").write_text("#!/bin/bash")

        structure_analyzer._detect_shell_scripts()
        # Should only detect root.sh, not nested.sh
        assert "root.sh" in structure_analyzer.custom_scripts.shell_scripts
        assert "nested.sh" not in structure_analyzer.custom_scripts.shell_scripts


class TestLoadCustomAllowlist:
    """Tests for StructureAnalyzer.load_custom_allowlist"""

    def test_load_custom_allowlist_no_file(self, structure_analyzer: StructureAnalyzer):
        """Test custom allowlist loading without file."""
        structure_analyzer.load_custom_allowlist()
        assert structure_analyzer.custom_commands == set()

    def test_load_custom_allowlist_with_commands(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test custom allowlist loading with commands."""
        (temp_project_dir / ".auto-claude-allowlist").write_text("""
custom-command-1
custom-command-2
/custom/script.sh
docker-compose up
""")

        structure_analyzer.load_custom_allowlist()
        assert "custom-command-1" in structure_analyzer.custom_commands
        assert "custom-command-2" in structure_analyzer.custom_commands
        assert "/custom/script.sh" in structure_analyzer.custom_commands
        assert "docker-compose up" in structure_analyzer.custom_commands

    def test_load_custom_allowlist_skips_comments(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test that custom allowlist skips comment lines."""
        (temp_project_dir / ".auto-claude-allowlist").write_text("""
# This is a comment
command-1
# Another comment
command-2
""")

        structure_analyzer.load_custom_allowlist()
        assert "command-1" in structure_analyzer.custom_commands
        assert "command-2" in structure_analyzer.custom_commands
        assert "# This is a comment" not in structure_analyzer.custom_commands
        assert "# Another comment" not in structure_analyzer.custom_commands

    def test_load_custom_allowlist_skips_empty_lines(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test that custom allowlist skips empty lines."""
        (temp_project_dir / ".auto-claude-allowlist").write_text("""
command-1

command-2

""")

        structure_analyzer.load_custom_allowlist()
        assert "command-1" in structure_analyzer.custom_commands
        assert "command-2" in structure_analyzer.custom_commands

    def test_load_custom_allowlist_whitespace_trim(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test that custom allowlist trims whitespace."""
        (temp_project_dir / ".auto-claude-allowlist").write_text("""
  command-1
command-2
  command-3
""")

        structure_analyzer.load_custom_allowlist()
        assert "command-1" in structure_analyzer.custom_commands
        assert "command-2" in structure_analyzer.custom_commands
        assert "command-3" in structure_analyzer.custom_commands

    def test_load_custom_allowlist_empty_file(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test custom allowlist loading with empty file."""
        (temp_project_dir / ".auto-claude-allowlist").write_text("")

        structure_analyzer.load_custom_allowlist()
        assert structure_analyzer.custom_commands == set()


class TestFullAnalysis:
    """Tests for complete analysis workflow"""

    def test_full_analysis_comprehensive(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test comprehensive analysis with all script types."""
        # Create package.json
        (temp_project_dir / "package.json").write_text(json.dumps({
            "scripts": {
                "dev": "next dev",
                "build": "next build",
                "test": "jest"
            }
        }))

        # Create Makefile
        (temp_project_dir / "Makefile").write_text("""
.PHONY: deploy

deploy:
	npm run deploy

lint:
	npm run lint
""")

        # Create pyproject.toml
        (temp_project_dir / "pyproject.toml").write_text("""
[tool.poetry.scripts]
check = "mypy"
""")

        # Create shell script
        (temp_project_dir / "setup.sh").write_text("#!/bin/bash")

        # Create allowlist
        (temp_project_dir / ".auto-claude-allowlist").write_text("""
custom-cmd
docker-compose up
""")

        custom_scripts, script_commands, custom_commands = structure_analyzer.analyze()

        # Check npm scripts
        assert "dev" in custom_scripts.npm_scripts
        assert "build" in custom_scripts.npm_scripts

        # Check makefile targets
        assert "deploy" in custom_scripts.make_targets
        assert "lint" in custom_scripts.make_targets

        # Check poetry scripts
        assert "check" in custom_scripts.poetry_scripts

        # Check shell scripts
        assert "setup.sh" in custom_scripts.shell_scripts

        # Check script commands
        assert "npm" in script_commands
        assert "make" in script_commands
        assert "./setup.sh" in script_commands

        # Check custom commands
        assert "custom-cmd" in custom_commands
        assert "docker-compose up" in custom_commands

    def test_analysis_empty_project(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test analysis of empty project."""
        (temp_project_dir / "README.md").write_text("# Empty Project")

        custom_scripts, script_commands, custom_commands = structure_analyzer.analyze()

        assert custom_scripts.npm_scripts == []
        assert custom_scripts.make_targets == []
        assert custom_scripts.poetry_scripts == []
        assert custom_scripts.shell_scripts == []
        assert script_commands == set()
        assert custom_commands == set()

    def test_analysis_caches_results(self, structure_analyzer: StructureAnalyzer, temp_project_dir: Path):
        """Test that subsequent analyses update the results."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "scripts": {"test": "jest"}
        }))

        # First analysis
        custom_scripts, _, _ = structure_analyzer.analyze()
        assert "test" in custom_scripts.npm_scripts

        # Add new script
        (temp_project_dir / "package.json").write_text(json.dumps({
            "scripts": {"test": "jest", "build": "webpack"}
        }))

        # Second analysis should update results
        custom_scripts, _, _ = structure_analyzer.analyze()
        assert "test" in custom_scripts.npm_scripts
        assert "build" in custom_scripts.npm_scripts


class TestCustomScriptsDataclass:
    """Tests for CustomScripts dataclass"""

    def test_custom_scripts_empty_initialization(self):
        """Test CustomScripts initializes with empty lists."""
        scripts = CustomScripts()
        assert scripts.npm_scripts == []
        assert scripts.make_targets == []
        assert scripts.poetry_scripts == []
        assert scripts.cargo_aliases == []
        assert scripts.shell_scripts == []

    def test_custom_scripts_with_values(self):
        """Test CustomScripts initialization with values."""
        scripts = CustomScripts(
            npm_scripts=["dev", "build"],
            make_targets=["test"],
            poetry_scripts=["check"],
            shell_scripts=["deploy.sh"]
        )
        assert scripts.npm_scripts == ["dev", "build"]
        assert scripts.make_targets == ["test"]
        assert scripts.poetry_scripts == ["check"]
        assert scripts.shell_scripts == ["deploy.sh"]
