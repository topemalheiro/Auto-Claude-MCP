"""
Root conftest for tests - adds apps/backend to Python path and provides common fixtures.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest

# Import merge fixtures for availability across all tests
from merge import (
    SemanticAnalyzer,
    ConflictDetector,
    AutoMerger,
    FileEvolutionTracker,
    AIResolver,
)

# Add project root to Python path for "apps.backend.*" style imports
# The structure is: repo_root/tests/conftest.py, repo_root/apps/backend/
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Add apps/backend to Python path so we can import modules like review, qa, etc.
backend_path = project_root / "apps" / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Set environment variable to prevent io_utils from closing stdout during tests
# This must be set BEFORE importing any modules that use safe_print
os.environ["AUTO_CLAUDE_TESTS"] = "1"


# =============================================================================
# PYTEST HOOKS - Clean up mocked modules during collection
# =============================================================================


def pytest_configure(config):
    """Pytest hook called after command line options have been parsed and all plugins initialized.

    This hook ensures that the real ui module is imported before test collection starts.
    This prevents test_spec_pipeline's mocking from affecting the ui module during
    collection of ui tests.
    """
    import importlib

    # Import the real ui module and its submodules BEFORE test collection
    # This ensures they exist in sys.modules before any test can mock them
    try:
        import ui
        import ui.icons
        import ui.progress
        import ui.capabilities
        import ui.menu
    except ImportError:
        pass  # Module may not exist on all platforms

    # Also ensure init module is real before collection
    # This prevents test_spec_pipeline's MagicMock from polluting test_init_root
    if 'init' in sys.modules and isinstance(sys.modules['init'], MagicMock):
        del sys.modules['init']
    try:
        importlib.import_module('init')
    except ImportError:
        pass


def pytest_collection_modifyitems(session, config, items):
    """Pytest hook called after test collection has been completed.

    This runs after all test modules have been imported. We ensure that any
    mocked modules are replaced with real modules before tests run.
    """
    import importlib

    # Replace any MagicMock modules with real ones before tests run
    # This is needed because test_spec_pipeline.py mocks certain modules
    # at import time, which affects other test files
    modules_to_fix = ['init', 'progress']
    for module_name in modules_to_fix:
        if module_name in sys.modules and isinstance(sys.modules[module_name], MagicMock):
            del sys.modules[module_name]
            try:
                importlib.import_module(module_name)
            except ImportError:
                pass

    # Reorder tests: put test_spec_pipeline.py tests at the end
    # This ensures UI tests run before test_spec_pipeline tests
    spec_pipeline_tests = [item for item in items if 'test_spec_pipeline.py' in str(item.fspath)]
    other_tests = [item for item in items if 'test_spec_pipeline.py' not in str(item.fspath)]
    items[:] = other_tests + spec_pipeline_tests


# =============================================================================
# COMMON TEST FIXTURES
# =============================================================================


@pytest.fixture
def temp_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide a temporary directory for testing.

    This is a thin wrapper around pytest's built-in tmp_path fixture
    for consistency with the spec_dir fixture naming.

    Args:
        tmp_path: pytest's built-in temporary directory fixture

    Yields:
        Path: Path to temporary directory that will be cleaned up automatically
    """
    yield tmp_path


@pytest.fixture
def spec_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a spec directory within the temp directory.

    Args:
        tmp_path: pytest's built-in temporary directory fixture

    Yields:
        Path: Path to spec directory (tmp_path/spec)
    """
    spec = tmp_path / "spec"
    spec.mkdir(exist_ok=True)
    yield spec


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary git repository for testing.

    This fixture:
    1. Creates a temporary directory
    2. Initializes a git repository
    3. Saves and restores original git environment variables
    4. Handles cleanup automatically

    Args:
        tmp_path: pytest's built-in temporary directory fixture

    Yields:
        Path: Path to the temporary git repository
    """
    # Save original git environment variables
    original_git_dir = os.environ.get("GIT_DIR")
    original_git_work_tree = os.environ.get("GIT_WORK_TREE")
    original_git_config = os.environ.get("GIT_CONFIG")

    try:
        # Clear any git environment variables that might interfere
        for key in ["GIT_DIR", "GIT_WORK_TREE", "GIT_CONFIG"]:
            os.environ.pop(key, None)

        # Initialize git repository
        subprocess.run(
            ["git", "init"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Configure git for tests (use local config, avoid global interference)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Rename default branch to main (for tests that expect main)
        subprocess.run(
            ["git", "branch", "-M", "main"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Create an initial commit
        test_file = tmp_path / "README.md"
        test_file.write_text("# Test Repository")
        subprocess.run(
            ["git", "add", "."],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        yield tmp_path

    finally:
        # Restore original git environment variables
        if original_git_dir is not None:
            os.environ["GIT_DIR"] = original_git_dir
        elif "GIT_DIR" in os.environ:
            del os.environ["GIT_DIR"]

        if original_git_work_tree is not None:
            os.environ["GIT_WORK_TREE"] = original_git_work_tree
        elif "GIT_WORK_TREE" in os.environ:
            del os.environ["GIT_WORK_TREE"]

        if original_git_config is not None:
            os.environ["GIT_CONFIG"] = original_git_config
        elif "GIT_CONFIG" in os.environ:
            del os.environ["GIT_CONFIG"]


# =============================================================================
# MERGE COMPONENT FIXTURES
# =============================================================================


@pytest.fixture
def semantic_analyzer() -> SemanticAnalyzer:
    """Create a SemanticAnalyzer instance."""
    return SemanticAnalyzer()


@pytest.fixture
def conflict_detector() -> ConflictDetector:
    """Create a ConflictDetector instance."""
    return ConflictDetector()


@pytest.fixture
def auto_merger() -> AutoMerger:
    """Create an AutoMerger instance."""
    return AutoMerger()


@pytest.fixture
def temp_project(temp_dir: Path) -> Path:
    """Create a temporary project directory for merge tests.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Path: Temporary project path with basic structure, sample files, and git initialization
    """
    project = temp_dir / "project"
    project.mkdir(exist_ok=True)
    (project / "src").mkdir(exist_ok=True)

    # Create sample files that tests expect to exist
    # Sample React/TypeScript component
    (project / "src" / "App.tsx").write_text("""import React from 'react';
import { useState } from 'react';

function App() {
  const [count, setCount] = useState(0);

  return (
    <div>
      <h1>Hello World</h1>
      <button onClick={() => setCount(count + 1)}>
        Count: {count}
      </button>
    </div>
  );
}

export default App;
""")

    # Sample Python module
    (project / "src" / "utils.py").write_text("""\"\"\"Sample Python module.\"\"\"
import os
from pathlib import Path

def hello():
    \"\"\"Say hello.\"\"\"
    print("Hello")

def goodbye():
    \"\"\"Say goodbye.\"\"\"
    print("Goodbye")

class Greeter:
    \"\"\"A greeter class.\"\"\"

    def greet(self, name: str) -> str:
        return f"Hello, {name}"
""")

    # Initialize as git repository with main branch for merge tests that need git
    subprocess.run(["git", "init"], cwd=project, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=project, capture_output=True, check=True)
    subprocess.run(["git", "branch", "-M", "main"], cwd=project, capture_output=True, check=True)
    subprocess.run(["git", "add", "."], cwd=project, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=project, capture_output=True, check=True)

    return project


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory for testing.

    Args:
        tmp_path: pytest's built-in temporary directory fixture

    Returns:
        Path: Temporary project directory
    """
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    return project


@pytest.fixture
def stage_files(temp_git_repo: Path) -> Callable:
    """Create and stage files in a git repository.

    Args:
        temp_git_repo: Path to temporary git repository

    Returns:
        Callable: Function that creates files and stages them in git
    """
    def _stage_files(files: dict[str, str]) -> None:
        """Create files and stage them.

        Args:
            files: Dictionary mapping filenames to their content
        """
        import subprocess

        for filename, content in files.items():
            file_path = temp_git_repo / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

            # Stage the file
            subprocess.run(
                ["git", "add", filename],
                cwd=temp_git_repo,
                check=True,
                capture_output=True,
            )

    return _stage_files


@pytest.fixture
def file_tracker(temp_project: Path) -> FileEvolutionTracker:
    """Create a FileEvolutionTracker instance.

    Args:
        temp_project: Temporary project directory

    Returns:
        FileEvolutionTracker: Tracker instance for the temp project
    """
    return FileEvolutionTracker(temp_project)


@pytest.fixture
def ai_resolver() -> AIResolver:
    """Create an AIResolver without AI function (for unit tests).

    Returns:
        AIResolver: Resolver instance without AI function
    """
    return AIResolver()


@pytest.fixture
def mock_ai_resolver() -> AIResolver:
    """Create an AIResolver with mocked AI function.

    Returns:
        AIResolver: Resolver instance with mock AI call function
    """
    def mock_ai_call(system: str, user: str) -> str:
        return """```typescript
const merged = useAuth();
const other = useOther();
return <div>Merged</div>;
```"""
    return AIResolver(ai_call_fn=mock_ai_call)


@pytest.fixture
def make_ai_resolver() -> Callable:
    """Factory for creating AIResolver with custom mock responses.

    Returns:
        Callable: Factory function that creates AIResolver instances
    """
    def _make_resolver(response: str = None) -> AIResolver:
        if response is None:
            response = """```python
def merged():
    return "auto-merged"
```"""

        def mock_ai_call(system: str, user: str) -> str:
            return response

        return AIResolver(ai_call_fn=mock_ai_call)

    return _make_resolver


# =============================================================================
# QA FIXTURES
# =============================================================================


@pytest.fixture
def qa_signoff_approved() -> dict:
    """Return an approved QA signoff structure.

    Returns:
        dict: Approved QA signoff with status, session info, and test results
    """
    return {
        "status": "approved",
        "qa_session": 1,
        "timestamp": "2024-01-01T12:00:00",
        "tests_passed": {
            "unit": True,
            "integration": True,
            "e2e": True,
        },
    }


# =============================================================================
# SPEC/MOCK FIXTURES
# =============================================================================


@pytest.fixture
def mock_run_agent_fn() -> Callable:
    """Return a factory that creates a mock run_agent function.

    Returns:
        Callable: Factory that creates async mock functions for running agents
    """
    def _create_agent_fn(success=True, output="Done", **kwargs):
        """Create a mock run_agent function with specified behavior.

        Args:
            success: Whether the agent succeeds
            output: Output to return
            **kwargs: Additional ignored parameters

        Returns:
            Callable: Async mock function for running agents
        """
        async def _run_agent(*args, **kwargs):
            return (success, output)
        return _run_agent
    return _create_agent_fn


@pytest.fixture
def mock_task_logger() -> MagicMock:
    """Return a mock task logger.

    Returns:
        MagicMock: Mock logger with common methods
    """
    logger = MagicMock()
    logger.log = MagicMock()
    logger.tool_start = MagicMock()
    logger.tool_end = MagicMock()
    logger.log_error = MagicMock()
    logger.start_phase = MagicMock()
    logger.end_phase = MagicMock()
    return logger


@pytest.fixture
def mock_ui_module() -> MagicMock:
    """Return a mock UI module.

    Returns:
        MagicMock: Mock UI module for testing
    """
    ui = MagicMock()
    ui.print = MagicMock()
    ui.input = MagicMock()
    ui.confirm = MagicMock()
    return ui


@pytest.fixture
def mock_spec_validator():
    """Return a factory function that creates a mock spec validator.

    Returns:
        callable: Factory that creates mock spec validators with configurable behavior
    """
    from dataclasses import dataclass, field
    from unittest.mock import MagicMock

    @dataclass
    class MockValidationResult:
        """Mock validation result."""
        valid: bool
        checkpoint: str
        errors: list = field(default_factory=list)
        fixes: list = field(default_factory=list)
        warnings: list = field(default_factory=list)

    def _create_validator(
        spec_valid=True,
        plan_valid=True,
        context_valid=True,
        prereqs_valid=True,
        all_valid=True,
    ):
        """Create a mock spec validator with the specified behavior.

        Args:
            spec_valid: Whether validate_spec_document returns valid
            plan_valid: Whether validate_implementation_plan returns valid
            context_valid: Whether validate_context returns valid
            prereqs_valid: Whether validate_prereqs returns valid
            all_valid: Whether validate_all returns all valid results

        Returns:
            MagicMock: Mock spec validator with appropriate methods
        """
        validator = MagicMock()

        # Setup validate_prereqs
        prereqs_result = MockValidationResult(valid=prereqs_valid, checkpoint="prereqs")
        validator.validate_prereqs = MagicMock(return_value=prereqs_result)

        # Setup validate_context
        context_result = MockValidationResult(valid=context_valid, checkpoint="context")
        validator.validate_context = MagicMock(return_value=context_result)

        # Setup validate_spec_document
        spec_result = MockValidationResult(valid=spec_valid, checkpoint="spec_document")
        validator.validate_spec_document = MagicMock(return_value=spec_result)

        # Setup validate_implementation_plan
        plan_result = MockValidationResult(valid=plan_valid, checkpoint="implementation_plan")
        validator.validate_implementation_plan = MagicMock(return_value=plan_result)

        # Setup validate_all (returns list of results)
        if all_valid:
            validator.validate_all = MagicMock(return_value=[
                MockValidationResult(valid=True, checkpoint="prereqs"),
                MockValidationResult(valid=True, checkpoint="context"),
                MockValidationResult(valid=True, checkpoint="spec_document"),
                MockValidationResult(valid=True, checkpoint="implementation_plan"),
            ])
        else:
            validator.validate_all = MagicMock(return_value=[
                MockValidationResult(valid=False, checkpoint="prereqs", errors=["Test error"]),
                MockValidationResult(valid=False, checkpoint="context", errors=["Test error"]),
                MockValidationResult(valid=False, checkpoint="spec_document", errors=["Test error"]),
                MockValidationResult(valid=False, checkpoint="implementation_plan", errors=["Test error"]),
            ])

        return validator

    return _create_validator


@pytest.fixture
def qa_signoff_rejected() -> dict:
    """Return a rejected QA signoff structure.

    Returns:
        dict: Rejected QA signoff with status, session info, and issues found
    """
    return {
        "status": "rejected",
        "qa_session": 1,
        "timestamp": "2024-01-01T12:00:00",
        "issues_found": [
            {"title": "Test failure", "type": "unit_test"},
            {"title": "Missing validation", "type": "acceptance"},
        ],
    }


@pytest.fixture
def sample_implementation_plan() -> dict:
    """Return a sample implementation plan structure.

    Returns:
        dict: Sample implementation plan with feature, workflow, and phases
    """
    return {
        "feature": "User Avatar Upload",
        "workflow_type": "feature",
        "services_involved": ["backend", "worker", "frontend"],
        "phases": [
            {
                "phase": 1,
                "name": "Backend Foundation",
                "subtasks": [
                    {"id": "subtask-1-1", "description": "Add avatar fields", "status": "completed"},
                ],
            },
        ],
    }


@pytest.fixture
def spec_with_plan(spec_dir: Path) -> Path:
    """Create a spec directory with implementation plan.

    Args:
        spec_dir: Spec directory fixture

    Returns:
        Path: Spec directory with implementation_plan.json
    """
    import json

    plan = {
        "spec_name": "test-spec",
        "qa_signoff": {
            "status": "pending",
            "qa_session": 0,
        }
    }
    plan_file = spec_dir / "implementation_plan.json"
    with open(plan_file, "w") as f:
        json.dump(plan, f)
    return spec_dir


# =============================================================================
# WORKTREE FIXTURES
# =============================================================================


@pytest.fixture
def mock_project_dir(tmp_path: Path) -> Path:
    """Create a mock project directory with git initialization.

    Args:
        tmp_path: pytest's built-in temporary directory fixture

    Returns:
        Path: Project directory initialized as git repository with main branch
    """
    project_dir = tmp_path / "project"
    project_dir.mkdir(exist_ok=True)

    # Initialize as git repo
    subprocess.run(["git", "init"], cwd=project_dir, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_dir, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=project_dir, capture_output=True, check=True)

    # Rename default branch to main (for tests that expect main)
    subprocess.run(["git", "branch", "-M", "main"], cwd=project_dir, capture_output=True, check=True)

    # Create initial commit
    (project_dir / "README.md").write_text("# Test Project")
    subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=project_dir, capture_output=True, check=True)

    return project_dir


@pytest.fixture
def worktree_manager(mock_project_dir: Path):
    """Create a WorktreeManager instance.

    Args:
        mock_project_dir: Mock project directory with git repo

    Returns:
        WorktreeManager: Instance for the test project
    """
    from core.worktree import WorktreeManager
    return WorktreeManager(mock_project_dir, base_branch="main")


@pytest.fixture
def python_project(temp_dir: Path) -> Path:
    """Create a simple Python project structure for testing.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Path: Python project directory with basic structure
    """
    # Create Python project files
    (temp_dir / "pyproject.toml").write_text("""
[project]
name = "test-project"
version = "1.0.0"
dependencies = ["flask>=2.0.0"]
""")
    (temp_dir / "requirements.txt").write_text("flask==2.0.0\n")
    (temp_dir / "app.py").write_text("print('hello')\n")
    (temp_dir / "main.py").write_text("def main(): pass\n")
    return temp_dir


# Alias for project_dir for compatibility
@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory for testing (alias for project_dir).

    Args:
        tmp_path: pytest's built-in temporary directory fixture

    Returns:
        Path: Temporary project directory
    """
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    return project


@pytest.fixture
def mock_spec_dir(tmp_path: Path) -> Path:
    """Create a mock spec directory.

    Args:
        tmp_path: pytest's built-in temporary directory fixture

    Returns:
        Path: Mock spec directory
    """
    spec_dir = tmp_path / "specs" / "001-test"
    spec_dir.mkdir(parents=True, exist_ok=True)
    return spec_dir


# =============================================================================
# MOCK CLEANUP FIXTURE - Ensures ui module mocks are properly isolated
# =============================================================================


@pytest.fixture(autouse=True, scope="function")
def ensure_modules_not_mocked(request):
    """Ensure critical modules are not mocked for tests that need real implementations.

    This fixture runs before each test to ensure that if critical modules were
    mocked by a previous test module (e.g., qa_report_helpers, test_queries_pkg_client,
    test_spec_pipeline), they get properly re-imported as the real modules.

    This is necessary because some test files mock sys.modules at import time,
    and the cleanup at module scope doesn't prevent the mock from persisting
    to other test modules.

    NOTE: This fixture is skipped for tests in the ui package since those tests
    manage their own module patching.
    """
    import importlib

    # Skip cleanup for ui tests - they manage their own mocking
    if request and hasattr(request, 'node') and 'tests/ui' in str(request.node.fspath):
        yield
        return

    # List of critical modules that should not be mocked
    # Includes modules mocked by test_spec_pipeline.py and other test files
    critical_modules = [
        'ui', 'ui.icons', 'ui.progress', 'ui.capabilities', 'ui.menu',
        'graphiti_providers', 'progress', 'claude_agent_sdk', 'claude_agent_sdk.types',
        'task_logger', 'review', 'client', 'validate_spec',
        # Note: 'init' is handled separately below because test_init_root.py
        # imports functions from it at module level. We need to update those
        # references after re-importing the real module.
    ]

    # Clean up BEFORE test execution
    modules_to_reload = []
    for module_name in critical_modules:
        module_is_mocked = False

        if module_name in sys.modules:
            module = sys.modules[module_name]
            # If it's a MagicMock (mocked module), mark for cleanup
            if hasattr(module, '_mock_name') or str(type(module)) == "<class 'unittest.mock.MagicMock'>":
                module_is_mocked = True

        # Only remove the module if it's actually mocked (MagicMock)
        # Do NOT remove it just because it has submodules - that breaks legitimate modules
        if module_is_mocked:
            modules_to_reload.append(module_name)
            # Remove the mocked module and all submodules
            if module_name in sys.modules:
                del sys.modules[module_name]
            for key in list(sys.modules.keys()):
                if key.startswith(f'{module_name}.'):
                    del sys.modules[key]

    # Invalidate importlib cache to force fresh imports
    importlib.invalidate_caches()

    # Re-import the real modules that were deleted
    # This ensures test files that imported these modules get the real versions
    for module_name in modules_to_reload:
        try:
            importlib.import_module(module_name)
        except ImportError:
            pass  # Module may not exist on all platforms

    # Special handling for 'init' module
    # test_init_root.py imports functions from init at module level, so we need
    # to update those references after re-importing the real module
    if 'init' in sys.modules and isinstance(sys.modules['init'], MagicMock):
        del sys.modules['init']
    try:
        importlib.import_module('init')
        # Update the references in test_init_root module if it's loaded
        if 'test_init_root' in sys.modules:
            test_init_root_module = sys.modules['test_init_root']
            init_module = sys.modules['init']
            # Update the module-level references
            test_init_root_module.AUTO_CLAUDE_GITIGNORE_ENTRIES = init_module.AUTO_CLAUDE_GITIGNORE_ENTRIES
            test_init_root_module._entry_exists_in_gitignore = init_module._entry_exists_in_gitignore
            test_init_root_module._is_git_repo = init_module._is_git_repo
            test_init_root_module._commit_gitignore = init_module._commit_gitignore
            test_init_root_module.ensure_gitignore_entry = init_module.ensure_gitignore_entry
            test_init_root_module.ensure_all_gitignore_entries = init_module.ensure_all_gitignore_entries
            test_init_root_module.init_auto_claude_dir = init_module.init_auto_claude_dir
            test_init_root_module.get_auto_claude_dir = init_module.get_auto_claude_dir
            test_init_root_module.repair_gitignore = init_module.repair_gitignore
    except ImportError:
        pass  # init module may not exist

    yield

    # Clean up AFTER test execution
    for module_name in critical_modules:
        module_is_mocked = False

        if module_name in sys.modules:
            module = sys.modules[module_name]
            if hasattr(module, '_mock_name') or str(type(module)) == "<class 'unittest.mock.MagicMock'>":
                module_is_mocked = True

        # Only remove the module if it's actually mocked (MagicMock)
        # Do NOT remove it just because it has submodules - that breaks legitimate modules
        if module_is_mocked:
            if module_name in sys.modules:
                del sys.modules[module_name]
            for key in list(sys.modules.keys()):
                if key.startswith(f'{module_name}.'):
                    del sys.modules[key]

    importlib.invalidate_caches()
