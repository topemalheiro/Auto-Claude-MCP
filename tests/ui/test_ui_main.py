"""
Tests for ui.main module.

This is a re-export module that aggregates all UI components.
Tests verify all exports are accessible and backward compatibility aliases work.
"""

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest


class TestMainImports:
    """Test that all public symbols can be imported from ui.main."""

    @pytest.fixture
    def clear_ui_imports(self):
        """Clear ui-related modules to ensure fresh imports."""
        modules_to_clear = [
            name for name in sys.modules
            if name.startswith("ui.") or name == "ui"
        ]
        saved_modules = {}
        for name in modules_to_clear:
            saved_modules[name] = sys.modules.pop(name, None)
        yield
        # Restore modules
        for name, module in saved_modules.items():
            if module is not None:
                sys.modules[name] = module

    def test_import_all_from_main(self, clear_ui_imports):
        """Test importing all symbols defined in __all__ from ui.main."""
        # First import to populate __all__
        import ui.main

        # Get the actual __all__ from the module
        all_exports = ui.main.__all__

        # Verify each export exists and can be accessed
        for name in all_exports:
            assert hasattr(ui.main, name), f"Missing export: {name}"
            # Ensure it's not None (unless None is a valid value)
            value = getattr(ui.main, name)
            # Functions, classes, and constants should not be None
            if name not in ("_FANCY_UI", "_UNICODE", "_COLOR", "_INTERACTIVE"):
                # Capabilities can be False, which is falsy but valid
                if name in ("FANCY_UI", "UNICODE", "COLOR", "INTERACTIVE"):
                    assert isinstance(value, bool), f"{name} should be bool"
                else:
                    assert value is not None, f"{name} should not be None"

    def test_capability_constants(self, clear_ui_imports):
        """Test backward compatibility capability aliases."""
        import ui.main

        # Test that all capability constants are accessible
        assert hasattr(ui.main, "FANCY_UI")
        assert hasattr(ui.main, "UNICODE")
        assert hasattr(ui.main, "COLOR")
        assert hasattr(ui.main, "INTERACTIVE")

        # Test backward compatibility aliases (underscore versions)
        assert hasattr(ui.main, "_FANCY_UI")
        assert hasattr(ui.main, "_UNICODE")
        assert hasattr(ui.main, "_COLOR")
        assert hasattr(ui.main, "_INTERACTIVE")

        # Verify aliases match their counterparts
        assert ui.main._FANCY_UI == ui.main.FANCY_UI
        assert ui.main._UNICODE == ui.main.UNICODE
        assert ui.main._COLOR == ui.main.COLOR
        assert ui.main._INTERACTIVE == ui.main.INTERACTIVE

    def test_capability_support_functions(self, clear_ui_imports):
        """Test capability support functions are exported."""
        import ui.main

        # Test support functions exist and are callable
        assert hasattr(ui.main, "supports_unicode")
        assert callable(ui.main.supports_unicode)

        assert hasattr(ui.main, "supports_color")
        assert callable(ui.main.supports_color)

        assert hasattr(ui.main, "supports_interactive")
        assert callable(ui.main.supports_interactive)

    def test_icon_exports(self, clear_ui_imports):
        """Test icon-related exports."""
        import ui.main

        # Icons class and icon function should be accessible
        assert hasattr(ui.main, "Icons")
        assert hasattr(ui.main, "icon")
        assert callable(ui.main.icon)

    def test_color_exports(self, clear_ui_imports):
        """Test color and styling exports."""
        import ui.main

        # Color enum/class
        assert hasattr(ui.main, "Color")

        # Color functions should be callable
        for func_name in ["color", "success", "error", "warning",
                          "info", "muted", "highlight", "bold"]:
            assert hasattr(ui.main, func_name)
            func = getattr(ui.main, func_name)
            assert callable(func), f"{func_name} should be callable"

    def test_box_exports(self, clear_ui_imports):
        """Test box drawing exports."""
        import ui.main

        assert hasattr(ui.main, "box")
        assert hasattr(ui.main, "divider")
        assert callable(ui.main.box)
        assert callable(ui.main.divider)

    def test_progress_exports(self, clear_ui_imports):
        """Test progress indicator exports."""
        import ui.main

        assert hasattr(ui.main, "progress_bar")
        assert callable(ui.main.progress_bar)

    def test_menu_exports(self, clear_ui_imports):
        """Test interactive menu exports."""
        import ui.main

        assert hasattr(ui.main, "MenuOption")
        assert hasattr(ui.main, "select_menu")
        assert callable(ui.main.select_menu)

    def test_status_exports(self, clear_ui_imports):
        """Test status management exports."""
        import ui.main

        # Classes should be available
        assert hasattr(ui.main, "BuildState")
        assert hasattr(ui.main, "BuildStatus")
        assert hasattr(ui.main, "StatusManager")

    def test_formatter_exports(self, clear_ui_imports):
        """Test formatter function exports."""
        import ui.main

        formatter_names = [
            "print_header",
            "print_section",
            "print_status",
            "print_key_value",
            "print_phase_status",
        ]

        for name in formatter_names:
            assert hasattr(ui.main, name)
            func = getattr(ui.main, name)
            assert callable(func), f"{name} should be callable"

    def test_spinner_exports(self, clear_ui_imports):
        """Test spinner class exports."""
        import ui.main

        assert hasattr(ui.main, "Spinner")

    def test_main_module_docstring(self, clear_ui_imports):
        """Test that main module has proper documentation."""
        import ui.main

        assert ui.main.__doc__ is not None
        assert len(ui.main.__doc__) > 0
        # Check for key documentation elements
        doc_lower = ui.main.__doc__.lower()
        assert "ui" in doc_lower or "utilities" in doc_lower

    def test_all_list_completeness(self, clear_ui_imports):
        """Test that __all__ list is properly defined and non-empty."""
        import ui.main

        assert hasattr(ui.main, "__all__")
        assert isinstance(ui.main.__all__, list)
        assert len(ui.main.__all__) > 0

        # Ensure no duplicates in __all__
        assert len(ui.main.__all__) == len(set(ui.main.__all__)), \
            "__all__ contains duplicate entries"

        # Ensure all __all__ entries are strings
        for item in ui.main.__all__:
            assert isinstance(item, str), f"__all__ entry {item} is not a string"

    def test_import_from_submodules(self, clear_ui_imports):
        """Test that main properly imports from its submodules."""
        import ui.main

        # The module should import from ui.boxes, ui.capabilities, etc.
        # Verify the module has been fully loaded by checking key imports
        expected_attributes = [
            # From capabilities
            "FANCY_UI",
            "UNICODE",
            "COLOR",
            "INTERACTIVE",
            # From icons
            "Icons",
            "icon",
            # From colors
            "Color",
            "color",
            # From boxes
            "box",
            "divider",
            # From progress
            "progress_bar",
            # From menu
            "select_menu",
            # From status
            "BuildState",
            "BuildStatus",
            "StatusManager",
            # From formatters
            "print_header",
            # From spinner
            "Spinner",
        ]

        for attr in expected_attributes:
            assert hasattr(ui.main, attr), f"Missing expected attribute: {attr}"

    def test_module_reloading(self, clear_ui_imports):
        """Test that the module can be reloaded without issues."""
        import ui.main as main_module

        # Get initial state
        initial_all = list(main_module.__all__)
        initial_fancy_ui = main_module.FANCY_UI

        # Reload the module
        importlib.reload(main_module)

        # Verify state is preserved
        assert main_module.__all__ == initial_all
        assert main_module.FANCY_UI == initial_fancy_ui

    def test_star_import(self, clear_ui_imports):
        """Test that star import from ui.main works correctly."""
        # Create a fresh namespace
        ns = {}

        # Execute star import
        exec("from ui.main import *", ns)

        # Verify __all__ items were imported
        import ui.main
        for name in ui.main.__all__:
            assert name in ns, f"{name} not imported via star import"

    def test_backward_compatibility_aliases_consistency(self, clear_ui_imports):
        """Test that backward compatibility aliases remain consistent."""
        import ui.main

        # All underscore-prefixed capability variables should match
        # their non-prefixed counterparts
        alias_pairs = [
            ("_FANCY_UI", "FANCY_UI"),
            ("_UNICODE", "UNICODE"),
            ("_COLOR", "COLOR"),
            ("_INTERACTIVE", "INTERACTIVE"),
        ]

        for alias, original in alias_pairs:
            assert hasattr(ui.main, alias), f"Missing alias: {alias}"
            assert hasattr(ui.main, original), f"Missing original: {original}"
            assert getattr(ui.main, alias) == getattr(ui.main, original), \
                f"Alias {alias} doesn't match {original}"

    def test_capability_types(self, clear_ui_imports):
        """Test that capability exports are boolean values."""
        import ui.main

        for capability in ["FANCY_UI", "UNICODE", "COLOR", "INTERACTIVE",
                           "_FANCY_UI", "_UNICODE", "_COLOR", "_INTERACTIVE"]:
            value = getattr(ui.main, capability)
            assert isinstance(value, bool), f"{capability} should be bool, got {type(value)}"

    def test_exports_are_not_none(self, clear_ui_imports):
        """Test that all __all__ exports have actual values (not None)."""
        import ui.main

        for name in ui.main.__all__:
            value = getattr(ui.main, name)
            # Capabilities can be False, which is falsy but valid
            # Everything else should have a meaningful value
            if name not in ("FANCY_UI", "UNICODE", "COLOR", "INTERACTIVE",
                           "_FANCY_UI", "_UNICODE", "_COLOR", "_INTERACTIVE"):
                assert value is not None, f"Export {name} is None"
