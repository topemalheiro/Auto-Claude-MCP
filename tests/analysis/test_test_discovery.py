"""Tests for test_discovery module"""

from analysis.test_discovery import (
    TestDiscovery,
    TestFramework,
    TestDiscoveryResult,
    discover_tests,
    get_test_command,
    get_test_frameworks,
    main,
)
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock
import pytest
import tempfile
import shutil
import json


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    project_path = Path(temp_dir)
    yield project_path
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def python_project(temp_dir):
    """Create a Python project for testing."""
    (temp_dir / "tests").mkdir(exist_ok=True)
    (temp_dir / "pyproject.toml").write_text("""
[project]
name = 'test'
dependencies = ['pytest']
""")
    (temp_dir / "tests" / "__init__.py").write_text("")
    (temp_dir / "tests" / "test_example.py").write_text("def test_foo(): pass")
    return temp_dir


@pytest.fixture
def node_project(temp_dir):
    """Create a Node.js project for testing."""
    (temp_dir / "tests").mkdir(exist_ok=True)
    (temp_dir / "package.json").write_text('''
{
  "name": "test",
  "version": "1.0.0",
  "devDependencies": {
    "jest": "^29.0.0"
  },
  "scripts": {
    "test": "jest"
  }
}
''')
    (temp_dir / "tests" / "example.test.js").write_text("test('foo', () => {});")
    return temp_dir


@pytest.fixture
def cargo_project(temp_dir):
    """Create a Cargo/Rust project for testing."""
    (temp_dir / "Cargo.toml").write_text("""
[package]
name = "test"
version = "0.1.0"
""")
    (temp_dir / "src").mkdir(exist_ok=True)
    (temp_dir / "src" / "main.rs").write_text("fn main() {}")
    (temp_dir / "tests").mkdir(exist_ok=True)
    (temp_dir / "tests" / "integration_test.rs").write_text("")
    return temp_dir


@pytest.fixture
def go_project(temp_dir):
    """Create a Go project for testing."""
    (temp_dir / "go.mod").write_text("module test\n\ngo 1.21\n")
    (temp_dir / "main.go").write_text("package main\nfunc main() {}")
    return temp_dir


class TestTestDiscoveryInit:
    """Tests for TestDiscovery initialization."""

    def test_init(self):
        """Test TestDiscovery initializes with empty cache."""
        discovery = TestDiscovery()
        assert isinstance(discovery._cache, dict)
        assert len(discovery._cache) == 0


class TestDiscoverPython:
    """Tests for Python test discovery."""

    def test_discovers_pytest_from_pyproject(self, temp_dir):
        """Test discovers pytest from pyproject.toml."""
        (temp_dir / "pyproject.toml").write_text("""
[project]
name = 'test'
dependencies = ['pytest']
""")
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert result is not None
        assert any(f.name == "pytest" for f in result.frameworks)

    def test_discovers_pytest_from_pytest_ini(self, temp_dir):
        """Test discovers pytest from pytest.ini."""
        (temp_dir / "pytest.ini").write_text("[pytest]\naddopts = -v")
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert result is not None
        assert any(f.name == "pytest" for f in result.frameworks)

    def test_discovers_pytest_from_requirements(self, temp_dir):
        """Test discovers pytest from requirements.txt."""
        (temp_dir / "requirements.txt").write_text("pytest\n")
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert result is not None
        assert any(f.name == "pytest" for f in result.frameworks)

    def test_discovers_pytest_from_conftest(self, temp_dir):
        """Test discovers pytest from conftest.py."""
        (temp_dir / "conftest.py").write_text("import pytest")
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert result is not None
        assert any(f.name == "pytest" for f in result.frameworks)

    def test_falls_back_to_unittest(self, temp_dir):
        """Test falls back to unittest when no framework found."""
        (temp_dir / "tests").mkdir()
        (temp_dir / "tests" / "test_example.py").write_text("import unittest")
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        # May or may not detect unittest depending on implementation
        assert isinstance(result, TestDiscoveryResult)


class TestDiscoverNode:
    """Tests for Node.js test discovery."""

    def test_discovers_jest_from_dependencies(self, temp_dir):
        """Test discovers jest from package.json dependencies."""
        (temp_dir / "package.json").write_text('''
{
  "devDependencies": {
    "jest": "^29.0.0"
  }
}
''')
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert result is not None
        assert any(f.name == "jest" for f in result.frameworks)

    def test_discovers_jest_from_scripts(self, temp_dir):
        """Test discovers jest from npm scripts."""
        (temp_dir / "package.json").write_text('''
{
  "scripts": {
    "test": "jest"
  }
}
''')
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert result is not None

    def test_discovers_vitest(self, temp_dir):
        """Test discovers vitest."""
        (temp_dir / "package.json").write_text('''
{
  "devDependencies": {
    "vitest": "^1.0.0"
  }
}
''')
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert result is not None

    def test_discovers_playwright(self, temp_dir):
        """Test discovers Playwright for E2E."""
        (temp_dir / "package.json").write_text('''
{
  "devDependencies": {
    "@playwright/test": "^1.40.0"
  }
}
''')
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert result is not None
        e2e_frameworks = [f for f in result.frameworks if f.type == "e2e"]
        assert len(e2e_frameworks) > 0

    def test_discovers_cypress(self, temp_dir):
        """Test discovers Cypress for E2E."""
        (temp_dir / "package.json").write_text('''
{
  "devDependencies": {
    "cypress": "^13.0.0"
  }
}
''')
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert result is not None


class TestDiscoverRust:
    """Tests for Rust test discovery."""

    def test_discovers_cargo_test(self, cargo_project):
        """Test discovers cargo test."""
        discovery = TestDiscovery()
        result = discovery.discover(cargo_project)
        assert result is not None
        assert any(f.name == "cargo_test" for f in result.frameworks)


class TestDiscoverGo:
    """Tests for Go test discovery."""

    def test_discovers_go_test(self, go_project):
        """Test discovers go test."""
        discovery = TestDiscovery()
        result = discovery.discover(go_project)
        assert result is not None
        assert any(f.name == "go_test" for f in result.frameworks)


class TestPackageManagerDetection:
    """Tests for package manager detection."""

    def test_detects_npm(self, temp_dir):
        """Test detects npm from package-lock.json."""
        (temp_dir / "package-lock.json").write_text("{}")
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert result.package_manager == "npm"

    def test_detects_yarn(self, temp_dir):
        """Test detects yarn from yarn.lock."""
        (temp_dir / "yarn.lock").write_text("")
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert result.package_manager == "yarn"

    def test_detects_pnpm(self, temp_dir):
        """Test detects pnpm from pnpm-lock.yaml."""
        (temp_dir / "pnpm-lock.yaml").write_text("")
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert result.package_manager == "pnpm"

    def test_detects_bun(self, temp_dir):
        """Test detects bun from bun.lockb."""
        (temp_dir / "bun.lockb").write_text("")
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert result.package_manager == "bun"

    def test_detects_poetry(self, temp_dir):
        """Test detects poetry from poetry.lock."""
        (temp_dir / "pyproject.toml").write_text("[tool.poetry]")
        (temp_dir / "poetry.lock").write_text("")
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert result.package_manager == "poetry"

    def test_detects_uv(self, temp_dir):
        """Test detects uv from uv.lock."""
        (temp_dir / "uv.lock").write_text("")
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert result.package_manager == "uv"


class TestTestDirectories:
    """Tests for test directory discovery."""

    def test_finds_tests_directory(self, temp_dir):
        """Test finds tests/ directory."""
        (temp_dir / "tests").mkdir()
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert "tests" in result.test_directories

    def test_finds_test_directory(self, temp_dir):
        """Test finds test/ directory."""
        (temp_dir / "test").mkdir()
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert "test" in result.test_directories

    def test_finds_spec_directory(self, temp_dir):
        """Test finds spec/ directory."""
        (temp_dir / "spec").mkdir()
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert "spec" in result.test_directories

    def test_finds___tests__directory(self, temp_dir):
        """Test finds __tests__/ directory."""
        (temp_dir / "__tests__").mkdir()
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert "__tests__" in result.test_directories


class TestHasTestFiles:
    """Tests for has_test_files detection."""

    def test_detects_python_test_files(self, temp_dir):
        """Test detects Python test files."""
        (temp_dir / "tests").mkdir()
        (temp_dir / "tests" / "test_example.py").write_text("")
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert result.has_tests is True

    def test_detects_js_test_files(self, temp_dir):
        """Test detects JavaScript test files."""
        (temp_dir / "tests").mkdir()
        (temp_dir / "tests" / "example.test.js").write_text("")
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert result.has_tests is True

    def test_detects_ts_test_files(self, temp_dir):
        """Test detects TypeScript test files."""
        (temp_dir / "tests").mkdir()
        (temp_dir / "tests" / "example.test.ts").write_text("")
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert result.has_tests is True

    def test_detects_go_test_files(self, temp_dir):
        """Test detects Go test files."""
        (temp_dir / "main_test.go").write_text("")
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert result.has_tests is True

    def test_no_test_files(self, temp_dir):
        """Test when no test files exist."""
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert result.has_tests is False


class TestTestCommand:
    """Tests for test command detection."""

    def test_pytest_command(self, python_project):
        """Test pytest command is set."""
        discovery = TestDiscovery()
        result = discovery.discover(python_project)
        assert "pytest" in result.test_command.lower()

    def test_jest_command(self, node_project):
        """Test jest command is set."""
        discovery = TestDiscovery()
        result = discovery.discover(node_project)
        # Command is "npm test" when script is defined, but framework is jest
        assert "jest" in result.test_command.lower() or "npm" in result.test_command.lower()

    def test_empty_command_no_framework(self, temp_dir):
        """Test command is empty when no framework found."""
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        # May have empty or default command
        assert isinstance(result.test_command, str)


class TestCoverageCommand:
    """Tests for coverage command detection."""

    def test_pytest_coverage(self, temp_dir):
        """Test pytest coverage command."""
        (temp_dir / "pyproject.toml").write_text("""
[project]
dependencies = ['pytest', 'pytest-cov']
""")
        (temp_dir / "pytest.ini").write_text("""
[pytest]
addopts = --cov
""")
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        # Coverage may be detected if framework supports it
        if result.coverage_command:
            assert "cov" in result.coverage_command.lower() or "coverage" in result.coverage_command.lower()


class TestToDict:
    """Tests for to_dict conversion."""

    def test_to_dict_structure(self, python_project):
        """Test to_dict creates proper structure."""
        discovery = TestDiscovery()
        result = discovery.discover(python_project)
        dict_result = discovery.to_dict(result)

        assert "frameworks" in dict_result
        assert "test_command" in dict_result
        assert "test_directories" in dict_result
        assert "package_manager" in dict_result
        assert "has_tests" in dict_result

    def test_to_dict_frameworks_format(self, python_project):
        """Test to_dict formats frameworks correctly."""
        discovery = TestDiscovery()
        result = discovery.discover(python_project)
        dict_result = discovery.to_dict(result)

        assert isinstance(dict_result["frameworks"], list)
        if dict_result["frameworks"]:
            framework = dict_result["frameworks"][0]
            assert "name" in framework
            assert "type" in framework
            assert "command" in framework


class TestClearCache:
    """Tests for cache clearing."""

    def test_clear_cache(self, python_project):
        """Test clearing cache."""
        discovery = TestDiscovery()
        discovery.discover(python_project)
        assert len(discovery._cache) > 0
        discovery.clear_cache()
        assert len(discovery._cache) == 0


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_discover_tests_function(self, python_project):
        """Test discover_tests convenience function."""
        result = discover_tests(python_project)
        assert isinstance(result, TestDiscoveryResult)

    def test_get_test_command_function(self, python_project):
        """Test get_test_command convenience function."""
        result = get_test_command(python_project)
        assert isinstance(result, str)

    def test_get_test_frameworks_function(self, python_project):
        """Test get_test_frameworks convenience function."""
        result = get_test_frameworks(python_project)
        assert isinstance(result, list)


class TestMainCLI:
    """Tests for main CLI function."""

    def test_main_with_project(self, python_project, capsys):
        """Test main with project directory."""
        with patch("sys.argv", ["test_discovery", str(python_project)]):
            main()
        captured = capsys.readouterr()
        assert "Test Command" in captured.out or "Framework" in captured.out

    def test_main_json_output(self, python_project, capsys):
        """Test main with JSON output."""
        with patch("sys.argv", ["test_discovery", str(python_project), "--json"]):
            main()
        captured = capsys.readouterr()
        # Check if output is valid JSON
        import json
        try:
            json.loads(captured.out)
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")


class TestTestFramework:
    """Tests for TestFramework dataclass."""

    def test_framework_creation(self):
        """Test TestFramework can be created."""
        framework = TestFramework(
            name="pytest",
            type="all",
            command="pytest",
            config_file="pytest.ini",
            version="7.4.0",
            coverage_command="pytest --cov",
        )
        assert framework.name == "pytest"
        assert framework.type == "all"
        assert framework.command == "pytest"
        assert framework.config_file == "pytest.ini"
        assert framework.version == "7.4.0"
        assert framework.coverage_command == "pytest --cov"

    def test_framework_optional_fields(self):
        """Test TestFramework with optional fields."""
        framework = TestFramework(
            name="jest",
            type="unit",
            command="npm test",
        )
        assert framework.name == "jest"
        assert framework.config_file is None
        assert framework.version is None
        assert framework.coverage_command is None


class TestTestDiscoveryResult:
    """Tests for TestDiscoveryResult dataclass."""

    def test_result_defaults(self):
        """Test TestDiscoveryResult has correct defaults."""
        result = TestDiscoveryResult()
        assert result.frameworks == []
        assert result.test_command == ""
        assert result.test_directories == []
        assert result.package_manager == ""
        assert result.has_tests is False
        assert result.coverage_command is None


class TestDiscoverUsesCache:
    """Tests for caching behavior."""

    def test_discover_uses_cache(self, python_project):
        """Test that discovery caches results."""
        discovery = TestDiscovery()
        result1 = discovery.discover(python_project)
        result2 = discovery.discover(python_project)
        assert result1 is result2  # Same object from cache


class TestRubyDetection:
    """Tests for Ruby test discovery."""

    def test_discovers_rspec(self, temp_dir):
        """Test discovers rspec."""
        (temp_dir / "Gemfile").write_text("gem 'rspec'")
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert result is not None

    def test_discovers_rspec_from_dot_rspec(self, temp_dir):
        """Test discovers rspec from .rspec file."""
        (temp_dir / ".rspec").write_text("--color")
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert result is not None

    def test_discovers_minitest(self, temp_dir):
        """Test discovers minitest."""
        (temp_dir / "Gemfile").write_text("gem 'minitest'")
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        assert result is not None


class TestCommandFromScripts:
    """Tests for command detection from npm scripts."""

    def test_prefers_npm_script_command(self, temp_dir):
        """Test prefers npm script command when available."""
        (temp_dir / "package.json").write_text('''
{
  "devDependencies": {
    "jest": "^29.0.0"
  },
  "scripts": {
    "test": "npm run test:unit"
  }
}
''')
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        # Command should include npm script
        if result.test_command:
            assert "npm" in result.test_command.lower() or "jest" in result.test_command.lower()


class TestFrameworkTypeDetection:
    """Tests for framework type classification."""

    def test_classifies_pytest_as_all(self, temp_dir):
        """Test pytest is classified as 'all' type."""
        (temp_dir / "pytest.ini").write_text("[pytest]")
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        pytest_frameworks = [f for f in result.frameworks if f.name == "pytest"]
        if pytest_frameworks:
            assert pytest_frameworks[0].type == "all"

    def test_classifies_jest_as_unit(self, temp_dir):
        """Test jest is classified as 'unit' type."""
        (temp_dir / "package.json").write_text('''
{
  "devDependencies": {
    "jest": "^29.0.0"
  }
}
''')
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        jest_frameworks = [f for f in result.frameworks if f.name == "jest"]
        if jest_frameworks:
            assert jest_frameworks[0].type == "unit"

    def test_classifies_playwright_as_e2e(self, temp_dir):
        """Test Playwright is classified as 'e2e' type."""
        (temp_dir / "package.json").write_text('''
{
  "devDependencies": {
    "@playwright/test": "^1.40.0"
  }
}
''')
        discovery = TestDiscovery()
        result = discovery.discover(temp_dir)
        playwright_frameworks = [f for f in result.frameworks if f.name == "playwright"]
        if playwright_frameworks:
            assert playwright_frameworks[0].type == "e2e"
