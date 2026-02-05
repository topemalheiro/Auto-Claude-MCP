"""
Tests for Linear integration __init__ module.

Tests that all expected exports are available and work correctly.
"""

import pytest

# Test all expected exports from __init__.py
from integrations.linear import (
    LinearConfig,
    LinearManager,
    LinearIntegration,
    LinearTaskState,
    LinearUpdater,
    is_linear_enabled,
    get_linear_api_key,
    create_linear_task,
    update_linear_status,
    STATUS_TODO,
    STATUS_IN_PROGRESS,
    STATUS_IN_REVIEW,
    STATUS_DONE,
    STATUS_CANCELED,
)


class TestInitExports:
    """Test all expected exports from __init__.py."""

    def test_linear_config_exported(self):
        """Test LinearConfig is exported."""
        from integrations.linear.config import LinearConfig as ConfigFromModule

        assert LinearConfig is ConfigFromModule

    def test_linear_manager_exported(self):
        """Test LinearManager is exported."""
        from integrations.linear.integration import LinearManager as ManagerFromModule

        assert LinearManager is ManagerFromModule

    def test_linear_integration_alias(self):
        """Test LinearIntegration is an alias for LinearManager."""
        from integrations.linear.integration import LinearManager

        assert LinearIntegration is LinearManager

    def test_linear_task_state_exported(self):
        """Test LinearTaskState is exported."""
        from integrations.linear.updater import LinearTaskState as StateFromModule

        assert LinearTaskState is StateFromModule

    def test_linear_updater_alias(self):
        """Test LinearUpdater is an alias for LinearTaskState."""
        from integrations.linear.updater import LinearTaskState

        assert LinearUpdater is LinearTaskState

    def test_status_constants(self):
        """Test all status constants are exported."""
        from integrations.linear.updater import (
            STATUS_TODO as TodoFromModule,
            STATUS_IN_PROGRESS as InProgressFromModule,
            STATUS_IN_REVIEW as InReviewFromModule,
            STATUS_DONE as DoneFromModule,
            STATUS_CANCELED as CanceledFromModule,
        )

        assert STATUS_TODO is TodoFromModule
        assert STATUS_IN_PROGRESS is InProgressFromModule
        assert STATUS_IN_REVIEW is InReviewFromModule
        assert STATUS_DONE is DoneFromModule
        assert STATUS_CANCELED is CanceledFromModule

    def test_is_linear_enabled_exported(self):
        """Test is_linear_enabled is exported."""
        from integrations.linear.updater import is_linear_enabled as EnabledFromModule

        assert is_linear_enabled is EnabledFromModule

    def test_get_linear_api_key_exported(self):
        """Test get_linear_api_key is exported."""
        from integrations.linear.updater import get_linear_api_key as ApiKeyFromModule

        assert get_linear_api_key is ApiKeyFromModule

    def test_create_linear_task_exported(self):
        """Test create_linear_task is exported."""
        from integrations.linear.updater import create_linear_task as CreateFromModule

        assert create_linear_task is CreateFromModule

    def test_update_linear_status_exported(self):
        """Test update_linear_status is exported."""
        from integrations.linear.updater import update_linear_status as UpdateFromModule

        assert update_linear_status is UpdateFromModule

    def test_all_exports_in___all__(self):
        """Test all exports are listed in __all__."""
        from integrations.linear import __all__

        expected_exports = [
            "LinearConfig",
            "LinearManager",
            "LinearIntegration",
            "LinearTaskState",
            "LinearUpdater",
            "is_linear_enabled",
            "get_linear_api_key",
            "create_linear_task",
            "update_linear_status",
            "STATUS_TODO",
            "STATUS_IN_PROGRESS",
            "STATUS_IN_REVIEW",
            "STATUS_DONE",
            "STATUS_CANCELED",
        ]

        for export in expected_exports:
            assert export in __all__, f"{export} not in __all__"

    def test_can_import_star(self):
        """Test that 'from integrations.linear import *' works."""
        # This should not raise ImportError
        import integrations.linear as linear_module

        # Check we can access the key items
        assert hasattr(linear_module, "LinearConfig")
        assert hasattr(linear_module, "LinearManager")
        assert hasattr(linear_module, "STATUS_TODO")
        assert hasattr(linear_module, "is_linear_enabled")


class TestInitFunctionality:
    """Test functionality through __init__ imports."""

    def test_linear_config_creation(self):
        """Test creating LinearConfig through __init__ import."""
        config = LinearConfig(api_key="test-key")

        assert config.api_key == "test-key"
        assert config.is_valid()

    def test_linear_manager_creation(self, tmp_path):
        """Test creating LinearManager through __init__ import."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        manager = LinearManager(spec_dir, project_dir)

        assert manager.spec_dir == spec_dir
        assert manager.project_dir == project_dir

    def test_status_constants_values(self):
        """Test status constants have correct values."""
        assert STATUS_TODO == "Todo"
        assert STATUS_IN_PROGRESS == "In Progress"
        assert STATUS_IN_REVIEW == "In Review"
        assert STATUS_DONE == "Done"
        assert STATUS_CANCELED == "Canceled"

    def test_is_linear_enabled_no_key(self):
        """Test is_linear_enabled returns False when no key."""
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {}, clear=True):
            assert is_linear_enabled() is False

    def test_get_linear_api_key_no_key(self):
        """Test get_linear_api_key returns empty string when no key."""
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {}, clear=True):
            assert get_linear_api_key() == ""

    def test_get_linear_api_key_with_key(self):
        """Test get_linear_api_key returns key when set."""
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"LINEAR_API_KEY": "test-key-123"}):
            assert get_linear_api_key() == "test-key-123"


class TestBackwardCompatibility:
    """Test backward compatibility aliases."""

    def test_linear_integration_works_as_manager(self, tmp_path):
        """Test LinearIntegration alias works the same as LinearManager."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        # Create with LinearIntegration alias
        manager1 = LinearIntegration(spec_dir, project_dir)

        # Create with LinearManager
        manager2 = LinearManager(spec_dir, project_dir)

        # Both should have same attributes
        assert manager1.spec_dir == manager2.spec_dir
        assert manager1.project_dir == manager2.project_dir
        assert type(manager1) == type(manager2)

    def test_linear_updater_works_as_state(self):
        """Test LinearUpdater alias works the same as LinearTaskState."""
        from datetime import datetime

        # Create with LinearUpdater alias
        state1 = LinearUpdater(
            task_id="LIN-123",
            status=STATUS_IN_PROGRESS,
        )

        # Create with LinearTaskState
        state2 = LinearTaskState(
            task_id="LIN-123",
            status=STATUS_IN_PROGRESS,
        )

        # Both should have same attributes
        assert state1.task_id == state2.task_id
        assert state1.status == state2.status
        assert type(state1) == type(state2)


class TestInitIntegration:
    """Integration tests using __init__ imports."""

    def test_full_workflow_with_init_imports(self, tmp_path):
        """Test a typical workflow using only __init__ imports."""
        spec_dir = tmp_path / "specs" / "001-test"
        project_dir = tmp_path / "project"
        spec_dir.mkdir(parents=True)

        # Create manager
        manager = LinearManager(spec_dir, project_dir)

        # Use status constants
        assert STATUS_TODO == "Todo"

        # Check if enabled
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {}, clear=True):
            assert is_linear_enabled() is False

        # Manager should work
        assert manager.spec_dir == spec_dir

    def test_cross_module_imports_work(self):
        """Test that imports from different modules work together."""
        # LinearConfig from config
        config = LinearConfig(api_key="test")

        # LinearManager from integration
        # (we can't fully test without paths, but we can check instantiation)
        assert LinearConfig is not None
        assert LinearManager is not None

        # Status constants from updater
        assert STATUS_TODO == "Todo"

        # Functions from updater
        assert callable(is_linear_enabled)
        assert callable(get_linear_api_key)
