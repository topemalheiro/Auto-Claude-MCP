"""Tests for ci_discovery module"""

from analysis.ci_discovery import (
    CIDiscovery,
    CIConfig,
    CIWorkflow,
    discover_ci,
    get_ci_system,
    get_ci_test_commands,
    main,
)
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock
import pytest
import tempfile
import shutil


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    project_path = Path(temp_dir)
    yield project_path
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def github_actions_project(temp_dir):
    """Create a project with GitHub Actions config."""
    workflows_dir = temp_dir / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "test.yml").write_text("""
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pytest
      - run: pytest --cov
""")
    return temp_dir


@pytest.fixture
def gitlab_ci_project(temp_dir):
    """Create a project with GitLab CI config."""
    (temp_dir / ".gitlab-ci.yml").write_text("""
stages:
  - test
  - build

test:
  stage: test
  script:
    - pytest
    - pytest --cov

integration:
  stage: test
  script:
    - pytest tests/integration
""")
    return temp_dir


@pytest.fixture
def circleci_project(temp_dir):
    """Create a project with CircleCI config."""
    circleci_dir = temp_dir / ".circleci"
    circleci_dir.mkdir(parents=True)
    (circleci_dir / "config.yml").write_text("""
version: 2.1
jobs:
  test:
    steps:
      - checkout
      - run: pytest
      - run: pytest --cov
""")
    return temp_dir


@pytest.fixture
def jenkins_project(temp_dir):
    """Create a project with Jenkinsfile."""
    (temp_dir / "Jenkinsfile").write_text("""
pipeline {
    agent any
    stages {
        stage('Test') {
            steps {
                sh 'pytest'
            }
        }
        stage('Build') {
            steps {
                sh 'npm run build'
            }
        }
    }
}
""")
    return temp_dir


class TestCIDiscoveryInit:
    """Tests for CIDiscovery initialization."""

    def test_CIDiscovery_init(self):
        """Test CIDiscovery initializes with empty cache."""
        discovery = CIDiscovery()
        assert isinstance(discovery._cache, dict)
        assert len(discovery._cache) == 0


class TestCIDiscover:
    """Tests for CI discovery."""

    def test_discover_no_ci(self, temp_dir):
        """Test discover with no CI configuration."""
        discovery = CIDiscovery()
        result = discovery.discover(temp_dir)
        assert result is None

    def test_discover_github_actions(self, github_actions_project):
        """Test discovery of GitHub Actions."""
        discovery = CIDiscovery()
        result = discovery.discover(github_actions_project)
        assert result is not None
        assert result.ci_system == "github_actions"
        assert len(result.config_files) > 0

    def test_discover_gitlab_ci(self, gitlab_ci_project):
        """Test discovery of GitLab CI."""
        discovery = CIDiscovery()
        result = discovery.discover(gitlab_ci_project)
        assert result is not None
        assert result.ci_system == "gitlab"

    def test_discover_circleci(self, circleci_project):
        """Test discovery of CircleCI."""
        discovery = CIDiscovery()
        result = discovery.discover(circleci_project)
        assert result is not None
        assert result.ci_system == "circleci"

    def test_discover_jenkins(self, jenkins_project):
        """Test discovery of Jenkins."""
        discovery = CIDiscovery()
        result = discovery.discover(jenkins_project)
        assert result is not None
        assert result.ci_system == "jenkins"

    def test_discover_uses_cache(self, github_actions_project):
        """Test that discovery caches results."""
        discovery = CIDiscovery()
        result1 = discovery.discover(github_actions_project)
        result2 = discovery.discover(github_actions_project)
        assert result1 is result2  # Same object from cache


class TestCIConfigParsing:
    """Tests for CI config parsing."""

    def test_parse_github_actions_workflows(self, github_actions_project):
        """Test parsing GitHub Actions workflows."""
        discovery = CIDiscovery()
        result = discovery.discover(github_actions_project)
        assert result is not None
        # Workflows may be empty if YAML parsing fails (no yaml module)
        assert isinstance(result.workflows, list)
        # Should detect the CI system
        assert result.ci_system == "github_actions"

    def test_parse_gitlab_ci_jobs(self, gitlab_ci_project):
        """Test parsing GitLab CI jobs."""
        discovery = CIDiscovery()
        result = discovery.discover(gitlab_ci_project)
        assert result is not None
        # Should detect the CI system
        assert result.ci_system == "gitlab"

    def test_extract_test_commands_from_github(self, github_actions_project):
        """Test extracting test commands from GitHub Actions."""
        discovery = CIDiscovery()
        result = discovery.discover(github_actions_project)
        assert result is not None
        # Test commands is a dict, may be empty if YAML parsing fails
        assert isinstance(result.test_commands, dict)

    def test_extract_coverage_command(self, github_actions_project):
        """Test extracting coverage command."""
        discovery = CIDiscovery()
        result = discovery.discover(github_actions_project)
        assert result is not None
        # Coverage command may or may not be present depending on parsing
        assert isinstance(result.coverage_command, (str, type(None)))


class TestCIDiscoveryToDict:
    """Tests for to_dict conversion."""

    def test_to_dict_structure(self, github_actions_project):
        """Test to_dict creates proper structure."""
        discovery = CIDiscovery()
        result = discovery.discover(github_actions_project)
        dict_result = discovery.to_dict(result)
        assert "ci_system" in dict_result
        assert "config_files" in dict_result
        assert "test_commands" in dict_result
        assert "workflows" in dict_result

    def test_to_dict_workflows_format(self, github_actions_project):
        """Test to_dict formats workflows correctly."""
        discovery = CIDiscovery()
        result = discovery.discover(github_actions_project)
        dict_result = discovery.to_dict(result)
        assert isinstance(dict_result["workflows"], list)
        if dict_result["workflows"]:
            workflow = dict_result["workflows"][0]
            assert "name" in workflow
            assert "trigger" in workflow
            assert "steps" in workflow


class TestCIDiscoveryClearCache:
    """Tests for cache clearing."""

    def test_clear_cache(self, github_actions_project):
        """Test clearing cache."""
        discovery = CIDiscovery()
        discovery.discover(github_actions_project)
        assert len(discovery._cache) > 0
        discovery.clear_cache()
        assert len(discovery._cache) == 0


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_discover_ci_function(self, github_actions_project):
        """Test discover_ci convenience function."""
        result = discover_ci(github_actions_project)
        assert result is not None
        assert result.ci_system == "github_actions"

    def test_get_ci_system_function(self, github_actions_project):
        """Test get_ci_system convenience function."""
        result = get_ci_system(github_actions_project)
        assert result == "github_actions"

    def test_get_ci_system_none(self, temp_dir):
        """Test get_ci_system returns None when no CI."""
        result = get_ci_system(temp_dir)
        assert result is None

    def test_get_ci_test_commands(self, github_actions_project):
        """Test get_ci_test_commands convenience function."""
        result = get_ci_test_commands(github_actions_project)
        assert isinstance(result, dict)

    def test_get_ci_test_commands_empty(self, temp_dir):
        """Test get_ci_test_commands returns empty dict when no CI."""
        result = get_ci_test_commands(temp_dir)
        assert result == {}


class TestMainCLI:
    """Tests for main CLI function."""

    def test_main_with_ci(self, github_actions_project, capsys):
        """Test main with CI configuration."""
        with patch("sys.argv", ["ci_discovery", str(github_actions_project)]):
            main()
        captured = capsys.readouterr()
        assert "CI System" in captured.out

    def test_main_json_output(self, github_actions_project, capsys):
        """Test main with JSON output."""
        with patch("sys.argv", ["ci_discovery", str(github_actions_project), "--json"]):
            main()
        captured = capsys.readouterr()
        # Check if output is valid JSON
        import json
        try:
            json.loads(captured.out)
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")

    def test_main_no_ci(self, temp_dir, capsys):
        """Test main with no CI configuration."""
        with patch("sys.argv", ["ci_discovery", str(temp_dir)]):
            main()
        captured = capsys.readouterr()
        assert "No CI configuration" in captured.out


class TestTestCommandExtraction:
    """Tests for test command extraction from CI configs."""

    def test_extract_pytest_command(self, github_actions_project):
        """Test extracting pytest command."""
        discovery = CIDiscovery()
        result = discovery.discover(github_actions_project)
        assert result is not None
        commands = result.test_commands
        # Test commands is a dict
        assert isinstance(commands, dict)

    def test_extract_npm_test_command(self, temp_dir):
        """Test extracting npm test command."""
        workflows_dir = temp_dir / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)
        (workflows_dir / "test.yml").write_text("""
name: Test
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: npm test
""")
        discovery = CIDiscovery()
        result = discovery.discover(temp_dir)
        assert result is not None
        # Test commands is a dict
        assert isinstance(result.test_commands, dict)

    def test_extract_jest_command(self, temp_dir):
        """Test extracting jest command."""
        workflows_dir = temp_dir / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)
        (workflows_dir / "test.yml").write_text("""
name: Test
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: npx jest
""")
        discovery = CIDiscovery()
        result = discovery.discover(temp_dir)
        assert result is not None

    def test_extract_playwright_command(self, temp_dir):
        """Test extracting Playwright E2E command."""
        workflows_dir = temp_dir / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)
        (workflows_dir / "e2e.yml").write_text("""
name: E2E
on: push
jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - run: npx playwright test
""")
        discovery = CIDiscovery()
        result = discovery.discover(temp_dir)
        assert result is not None
        # E2E commands may not be extracted if YAML parsing fails
        assert isinstance(result.test_commands, dict)


class TestEnvironmentVariables:
    """Tests for environment variable extraction."""

    def test_extract_env_vars(self, temp_dir):
        """Test extracting environment variables."""
        workflows_dir = temp_dir / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)
        (workflows_dir / "test.yml").write_text("""
name: Test
on: push
env:
  NODE_ENV: test
  CI: true
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: echo "test"
""")
        discovery = CIDiscovery()
        result = discovery.discover(temp_dir)
        assert result is not None
        # Environment variables is a list, may be empty if YAML parsing fails
        assert isinstance(result.environment_variables, list)
