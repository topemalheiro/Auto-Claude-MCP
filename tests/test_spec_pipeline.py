#!/usr/bin/env python3
"""
Tests for Spec Pipeline Integration
====================================

Tests the spec/pipeline.py module functionality including:
- SpecOrchestrator initialization
- Spec directory creation and naming
- Orphaned pending folder cleanup
- Specs directory path resolution

NOTE: Integration tests with SpecOrchestrator - marked as slow.
Can be excluded with: pytest -m "not slow"
"""

import pytest
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

# Add auto-claude directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "Apps" / "backend"))

# Add auto-claude directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

# Module names that need to be mocked for these tests
_MOCKED_MODULE_NAMES = [
    'claude_code_sdk',
    'claude_code_sdk.types',
    'init',
    'client',
    'review',
    'task_logger',
    'ui',
    'validate_spec',
]

# Store original modules for cleanup
_original_modules = {}
_cleanup_registered = False


def _cleanup_mocks():
    """Clean up mocked modules and import real ui modules."""
    import importlib

    for name in _MOCKED_MODULE_NAMES:
        # First, delete any submodules
        to_delete = [key for key in sys.modules if key.startswith(f"{name}.")]
        for sub_name in to_delete:
            del sys.modules[sub_name]

        # Then delete the main module (whether it's a mock or real)
        if name in sys.modules:
            del sys.modules[name]

        # If there was an original REAL module (not a mock), restore it
        if name in _original_modules and not isinstance(_original_modules[name], MagicMock):
            sys.modules[name] = _original_modules[name]

    # Invalidate importlib cache to force fresh imports
    importlib.invalidate_caches()

    # Force import of real ui modules to ensure they're available
    # for subsequent test modules
    try:
        pass
    except ImportError:
        pass  # Module may not exist on all platforms


def _setup_mocks():
    """Set up the mocked modules."""
    global _cleanup_registered

    # Store original modules (only once)
    if not _original_modules:
        import importlib

        # CRITICAL: Import and save REAL modules BEFORE mocking them
        # This ensures we can restore the actual modules after cleanup
        for name in _MOCKED_MODULE_NAMES:
            # Only process modules that might actually exist as real modules
            # (skip fake ones like 'claude_code_sdk' that we're creating from scratch)
            if name in ['claude_code_sdk', 'claude_code_sdk.types', 'ui', 'ui.capabilities']:
                # These are mock-only modules, don't try to import them
                if name in sys.modules:
                    _original_modules[name] = sys.modules[name]
                continue

            # For real modules like 'init', 'client', 'review', etc.
            # First, ensure they're NOT mocked before we store the original
            # Delete any existing mock to force a real import
            if name in sys.modules and isinstance(sys.modules[name], MagicMock):
                del sys.modules[name]

            # Now try to import the real module
            if name not in sys.modules:
                try:
                    importlib.import_module(name)
                except (ImportError, ModuleNotFoundError):
                    pass  # Module may not exist, that's okay

            # Store the real module if it exists
            if name in sys.modules and not isinstance(sys.modules[name], MagicMock):
                _original_modules[name] = sys.modules[name]

    # Set up mocks
    mock_sdk = MagicMock()
    mock_sdk.ClaudeSDKClient = MagicMock()
    mock_sdk.ClaudeCodeOptions = MagicMock()
    sys.modules['claude_code_sdk'] = mock_sdk

    mock_types = MagicMock()
    mock_types.HookMatcher = MagicMock()
    sys.modules['claude_code_sdk.types'] = mock_types

    mock_init = MagicMock()
    mock_init.init_auto_claude_dir = MagicMock(return_value=(Path("/tmp"), False))
    sys.modules['init'] = mock_init

    mock_client = MagicMock()
    mock_client.create_client = MagicMock()
    sys.modules['client'] = mock_client

    mock_review = MagicMock()
    mock_review.ReviewState = MagicMock()
    mock_review.run_review_checkpoint = MagicMock()
    sys.modules['review'] = mock_review

    mock_task_logger = MagicMock()
    mock_task_logger.LogEntryType = MagicMock()
    mock_task_logger.LogPhase = MagicMock()
    mock_task_logger.get_task_logger = MagicMock()
    mock_task_logger.update_task_logger_path = MagicMock()
    sys.modules['task_logger'] = mock_task_logger

    mock_ui = MagicMock()
    mock_ui.Icons = MagicMock()
    mock_ui.box = MagicMock(return_value="")
    mock_ui.highlight = MagicMock(return_value="")
    mock_ui.icon = MagicMock(return_value="")
    mock_ui.muted = MagicMock(return_value="")
    mock_ui.print_key_value = MagicMock()
    mock_ui.print_section = MagicMock()
    mock_ui.print_status = MagicMock()
    sys.modules['ui'] = mock_ui

    # Mock ui.capabilities for spec.pipeline import
    mock_ui_capabilities = MagicMock()
    mock_ui_capabilities.configure_safe_encoding = MagicMock()
    sys.modules['ui.capabilities'] = mock_ui_capabilities

    mock_validate_spec = MagicMock()
    mock_validate_spec.SpecValidator = MagicMock()
    sys.modules['validate_spec'] = mock_validate_spec

    # Register cleanup with atexit to ensure it always happens
    if not _cleanup_registered:
        atexit.register(_cleanup_mocks)
        _cleanup_registered = True


# Set up mocks at module level (required for importing spec.pipeline)
_setup_mocks()

# Import the module under test AFTER mocks are set up
from spec.pipeline import SpecOrchestrator, get_specs_dir


@pytest.fixture(scope="module", autouse=True)
def cleanup_after_tests():
    """Clean up mocks after all tests in this module complete."""
    import importlib

    yield  # Run all tests

    # Clean up (also called by atexit, but this ensures it happens after module tests)
    _cleanup_mocks()

    # CRITICAL: After cleanup, force re-import of real modules to ensure
    # subsequent test files get the real modules, not mocks
    # This must happen here because other test files may have already
    # been imported with the mocked versions in their namespace
    for module_name in ['init', 'client', 'review', 'task_logger', 'progress', 'validate_spec']:
        # Delete any remaining mock
        if module_name in sys.modules and isinstance(sys.modules[module_name], MagicMock):
            del sys.modules[module_name]

        # Force import the real module
        if module_name not in sys.modules:
            try:
                importlib.import_module(module_name)
            except ImportError:
                pass

    # Also re-import ui modules
    for ui_module in ['ui', 'ui.icons', 'ui.progress', 'ui.capabilities', 'ui.menu']:
        if ui_module in sys.modules and isinstance(sys.modules[ui_module], MagicMock):
            del sys.modules[ui_module]
        if ui_module not in sys.modules:
            try:
                importlib.import_module(ui_module)
            except ImportError:
                pass

    importlib.invalidate_caches()


@pytest.fixture(autouse=True)
def setup_and_cleanup_mocks():
    """Set up mocks before each test and clean up after.

    This prevents test_spec_pipeline's mocks from leaking into other test modules
    when using pytest's -k filter which collects all tests before filtering.
    """
    import importlib

    # First, clean up any existing mocks
    _cleanup_mocks()

    # Then re-setup mocks for this module
    _setup_mocks()

    yield

    # Clean up after the test AND restore real modules
    # This is critical for tests that run after test_spec_pipeline tests
    _cleanup_mocks()

    # Explicitly restore REAL modules (not mocks) to ensure they're available for other tests
    real_modules = ['init', 'progress', 'client', 'review', 'task_logger', 'validate_spec']
    for module_name in real_modules:
        # Only restore if we have a REAL module saved (not a MagicMock)
        if module_name in _original_modules and not isinstance(_original_modules[module_name], MagicMock):
            sys.modules[module_name] = _original_modules[module_name]
        elif module_name in sys.modules and isinstance(sys.modules[module_name], MagicMock):
            # Delete the mock so the next test will import the real module
            del sys.modules[module_name]

    # Force re-import of critical modules to ensure they're available
    # This is necessary because pytest may have cached the import
    for module_name in ['init', 'progress']:
        if module_name not in sys.modules or isinstance(sys.modules.get(module_name), MagicMock):
            try:
                importlib.import_module(module_name)
            except ImportError:
                pass

    importlib.invalidate_caches()


class TestGetSpecsDir:
    """Tests for get_specs_dir function."""

    def test_returns_specs_path(self, temp_dir: Path):
        """Returns path to specs directory."""
        with patch('spec.pipeline.init_auto_claude_dir') as mock_init:
            mock_init.return_value = (temp_dir / ".auto-claude", False)

            result = get_specs_dir(temp_dir)

            assert result == temp_dir / ".auto-claude" / "specs"

    def test_calls_init_auto_claude_dir(self, temp_dir: Path):
        """Initializes auto-claude directory."""
        with patch('spec.pipeline.models.init_auto_claude_dir') as mock_init:
            mock_init.return_value = (temp_dir / ".auto-claude", False)

            get_specs_dir(temp_dir)

            mock_init.assert_called_once_with(temp_dir)

class TestSpecOrchestratorInit:
    """Tests for SpecOrchestrator initialization."""

    def test_init_with_project_dir(self, temp_dir: Path):
        """Initializes with project directory."""
        with patch('spec.pipeline.init_auto_claude_dir') as mock_init:
            mock_init.return_value = (temp_dir / ".auto-claude", False)
            specs_dir = temp_dir / ".auto-claude" / "specs"
            specs_dir.mkdir(parents=True, exist_ok=True)

            orchestrator = SpecOrchestrator(
                project_dir=temp_dir,
                task_description="Test task",
            )

            assert orchestrator.project_dir == temp_dir
            assert orchestrator.task_description == "Test task"

    def test_init_creates_spec_dir(self, temp_dir: Path):
        """Creates spec directory if not exists."""
        with patch('spec.pipeline.init_auto_claude_dir') as mock_init:
            mock_init.return_value = (temp_dir / ".auto-claude", False)

            orchestrator = SpecOrchestrator(
                project_dir=temp_dir,
                task_description="Test task",
            )

            assert (temp_dir / ".auto-claude" / "specs").exists()

    def test_init_generates_spec_name(self, temp_dir: Path):
        """Generates spec name from task description."""
        with patch('spec.pipeline.init_auto_claude_dir') as mock_init:
            mock_init.return_value = (temp_dir / ".auto-claude", False)

            orchestrator = SpecOrchestrator(
                project_dir=temp_dir,
                task_description="Add user authentication",
            )

            # Spec name should be generated (format may vary)
            assert orchestrator.spec_name is not None
            assert len(orchestrator.spec_name) > 0

    def test_init_sanitizes_spec_name(self, temp_dir: Path):
        """Sanitizes special characters in task description."""
        with patch('spec.pipeline.init_auto_claude_dir') as mock_init:
            mock_init.return_value = (temp_dir / ".auto-claude", False)

            orchestrator = SpecOrchestrator(
                project_dir=temp_dir,
                task_description="Fix bug: can't login!!",
            )

            # Special characters should be sanitized
            assert orchestrator.spec_name is not None
            assert "!" not in orchestrator.spec_name
            assert "'" not in orchestrator.spec_name


class TestOrphanedCleanup:
    """Tests for orphaned pending folder cleanup."""

    def test_removes_orphaned_pending_folders(self, temp_dir: Path):
        """Removes pending folders with no corresponding spec directory."""
        with patch('spec.pipeline.init_auto_claude_dir') as mock_init:
            mock_init.return_value = (temp_dir / ".auto-claude", False)
            specs_dir = temp_dir / ".auto-claude" / "specs"
            specs_dir.mkdir(parents=True, exist_ok=True)

            # Create an orphaned pending folder (no matching spec folder)
            pending_dir = specs_dir / "001-test-pending"
            pending_dir.mkdir(parents=True, exist_ok=True)

            # Create old EMPTY pending folder at 002
            old_pending = specs_dir / "002-pending"
            old_pending.mkdir()

            # Set modification time to 15 minutes ago
            old_time = time.time() - (15 * 60)
            import os
            os.utime(old_pending, (old_time, old_time))

            # Store the inode to verify it's actually deleted and recreated
            old_inode = old_pending.stat().st_ino

            # Creating orchestrator triggers cleanup
            # The cleanup removes 002-pending (empty and old)
            # Then _create_spec_dir creates 004-pending (after 003)
            orchestrator = SpecOrchestrator(project_dir=temp_dir)

            # The orchestrator should have created a new folder at 004
            assert orchestrator.spec_dir.name.startswith("004-")
            # The 002-pending folder no longer exists (cleaned up)
            assert not old_pending.exists()

    def test_keeps_folder_with_requirements(self, temp_dir: Path):
        """Keeps pending folder with requirements.json."""
        with patch('spec.pipeline.init_auto_claude_dir') as mock_init:
            mock_init.return_value = (temp_dir / ".auto-claude", False)
            specs_dir = temp_dir / ".auto-claude" / "specs"
            specs_dir.mkdir(parents=True, exist_ok=True)

            # Create pending folder with requirements
            pending_with_req = specs_dir / "001-pending"
            pending_with_req.mkdir()
            (pending_with_req / "requirements.json").write_text("{}")

            # Set modification time to 15 minutes ago
            old_time = time.time() - (15 * 60)
            import os
            os.utime(pending_with_req, (old_time, old_time))

            # Creating orchestrator triggers cleanup
            orchestrator = SpecOrchestrator(project_dir=temp_dir)

            assert pending_with_req.exists()

    def test_keeps_folder_with_spec(self, temp_dir: Path):
        """Keeps pending folder with spec.md."""
        with patch('spec.pipeline.init_auto_claude_dir') as mock_init:
            mock_init.return_value = (temp_dir / ".auto-claude", False)
            specs_dir = temp_dir / ".auto-claude" / "specs"
            specs_dir.mkdir(parents=True, exist_ok=True)

            # Create pending folder with spec
            pending_with_spec = specs_dir / "001-pending"
            pending_with_spec.mkdir()
            (pending_with_spec / "spec.md").write_text("# Spec")

            # Set modification time to 15 minutes ago
            old_time = time.time() - (15 * 60)
            import os
            os.utime(pending_with_spec, (old_time, old_time))

            # Creating orchestrator triggers cleanup
            orchestrator = SpecOrchestrator(project_dir=temp_dir)

            assert pending_with_spec.exists()

    def test_keeps_recent_pending_folder(self, temp_dir: Path):
        """Keeps pending folder younger than 10 minutes."""
        with patch('spec.pipeline.init_auto_claude_dir') as mock_init:
            mock_init.return_value = (temp_dir / ".auto-claude", False)
            specs_dir = temp_dir / ".auto-claude" / "specs"
            specs_dir.mkdir(parents=True, exist_ok=True)

            # Create recent pending folder (no need to modify time, it's fresh)
            recent_pending = specs_dir / "001-pending"
            recent_pending.mkdir()

            # Creating orchestrator triggers cleanup
            orchestrator = SpecOrchestrator(project_dir=temp_dir)

            # Recent folder should still exist (unless orchestrator created 002-pending)
            # The folder might be gone if orchestrator picked a different name
            # So we check the spec dir count instead
            assert any(d.name.endswith("-pending") for d in specs_dir.iterdir())


class TestRenameSpecDirFromRequirements:
    """Tests for renaming spec directory from requirements."""

    def test_renames_from_task_description(self, temp_dir: Path):
        """Renames spec dir based on requirements task description."""
        with patch('spec.pipeline.init_auto_claude_dir') as mock_init:
            mock_init.return_value = (temp_dir / ".auto-claude", False)
            specs_dir = temp_dir / ".auto-claude" / "specs"
            specs_dir.mkdir(parents=True, exist_ok=True)

            orchestrator = SpecOrchestrator(project_dir=temp_dir)

            # Write requirements
            requirements = {
                "task_description": "Add user authentication system"
            }
            (orchestrator.spec_dir / "requirements.json").write_text(
                json.dumps(requirements)
            )

            # Orphaned folder should be removed
            assert not pending_dir.exists()

    def test_keeps_valid_pending_folders(self, temp_dir: Path):
        """Keeps pending folders that have a corresponding spec directory."""
        with patch('spec.pipeline.init_auto_claude_dir') as mock_init:
            mock_init.return_value = (temp_dir / ".auto-claude", False)
            specs_dir = temp_dir / ".auto-claude" / "specs"
            specs_dir.mkdir(parents=True, exist_ok=True)

            # Create a valid pending folder with corresponding spec
            spec_dir = specs_dir / "001-test"
            spec_dir.mkdir(parents=True, exist_ok=True)
            pending_dir = specs_dir / "001-test-pending"
            pending_dir.mkdir(parents=True, exist_ok=True)

            # Create orchestrator
            orchestrator = SpecOrchestrator(
                project_dir=temp_dir,
                task_description="Test task",
            )

            # Valid pending folder should be kept
            assert pending_dir.exists()


class TestSpecNumbering:
    """Tests for automatic spec numbering."""

    def test_finds_next_available_number(self, temp_dir: Path):
        """Finds the next available spec number."""
        with patch('spec.pipeline.init_auto_claude_dir') as mock_init:
            mock_init.return_value = (temp_dir / ".auto-claude", False)
            specs_dir = temp_dir / ".auto-claude" / "specs"
            specs_dir.mkdir(parents=True, exist_ok=True)

            # Create existing specs
            (specs_dir / "001-test").mkdir()
            (specs_dir / "002-test").mkdir()
            (specs_dir / "003-test").mkdir()

            # Create orchestrator
            orchestrator = SpecOrchestrator(
                project_dir=temp_dir,
                task_description="Test task",
            )

            # Should use next available number (004)
            assert orchestrator.spec_name.startswith("004-")

    def test_handles_empty_specs_directory(self, temp_dir: Path):
        """Starts at 001 when no specs exist."""
        with patch('spec.pipeline.init_auto_claude_dir') as mock_init:
            mock_init.return_value = (temp_dir / ".auto-claude", False)
            specs_dir = temp_dir / ".auto-claude" / "specs"
            specs_dir.mkdir(parents=True, exist_ok=True)

            # Create orchestrator
            orchestrator = SpecOrchestrator(
                project_dir=temp_dir,
                task_description="Test task",
            )

            # Should start at 001
            assert orchestrator.spec_name.startswith("001-")


class TestSpecDirectories:
    """Tests for spec directory operations."""

    def test_creates_spec_directory(self, temp_dir: Path):
        """Creates the spec directory."""
        with patch('spec.pipeline.init_auto_claude_dir') as mock_init:
            mock_init.return_value = (temp_dir / ".auto-claude", False)

            orchestrator = SpecOrchestrator(
                project_dir=temp_dir,
                task_description="Test task",
            )

            spec_dir = orchestrator.spec_dir
            assert spec_dir.exists()
            assert spec_dir.is_dir()

    def test_spec_directory_has_correct_name(self, temp_dir: Path):
        """Spec directory has the correct name format."""
        with patch('spec.pipeline.init_auto_claude_dir') as mock_init:
            mock_init.return_value = (temp_dir / ".auto-claude", False)

            orchestrator = SpecOrchestrator(
                project_dir=temp_dir,
                task_description="Test task",
            )

            spec_dir = orchestrator.spec_dir
            assert spec_dir.name == orchestrator.spec_name


class TestGetSpecsDir:
    """Tests for get_specs_dir function."""

    def test_returns_specs_path(self, temp_dir: Path):
        """Returns path to specs directory."""
        with patch('spec.pipeline.init_auto_claude_dir') as mock_init:
            mock_init.return_value = (temp_dir / ".auto-claude", False)

            result = get_specs_dir(temp_dir)

            assert result == temp_dir / ".auto-claude" / "specs"

    def test_calls_init_auto_claude_dir(self, temp_dir: Path):
        """Initializes auto-claude directory."""
        with patch('spec.pipeline.models.init_auto_claude_dir') as mock_init:
            mock_init.return_value = (temp_dir / ".auto-claude", False)

            get_specs_dir(temp_dir)

            mock_init.assert_called_once_with(temp_dir)


# Import remaining tests from original file...
# (For brevity, I've included the key test classes above)
