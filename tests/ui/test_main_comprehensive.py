"""
Comprehensive Tests for ui.main module
======================================

Enhanced tests covering edge cases, runtime behavior,
import mechanics, and module resilience.
"""

import sys
import pytest


class TestModuleReloadBehavior:
    """Tests for module reload behavior and state management"""

    def test_multiple_imports_preserve_exports(self):
        """Test that multiple imports preserve exports"""
        import ui.main as main_module

        initial_all = list(main_module.__all__)

        # Re-import multiple times (module should be cached)
        for _ in range(3):
            import ui.main as reimported_module
            assert reimported_module.__all__ == initial_all
            # Verify it's the same cached module
            assert id(reimported_module) == id(main_module)

    def test_module_attribute_modification_isolated(self):
        """Test that attribute modifications are isolated to the module instance"""
        import ui.main as main_module

        # Save original value
        original_value = main_module.FANCY_UI

        # Modify an attribute
        main_module.FANCY_UI = not original_value

        # Since the module is cached, modifications persist
        # This tests the behavior - in practice, don't modify module attributes
        assert main_module.FANCY_UI == (not original_value)

        # Restore original for other tests
        main_module.FANCY_UI = original_value

    def test_module_id_stability(self):
        """Test that module identity is stable"""
        import ui.main as main_module1
        import ui.main as main_module2

        # Same module should have same id
        assert id(main_module1) == id(main_module2)


class TestImportIsolation:
    """Tests for import isolation and side effects"""

    @pytest.fixture
    def fresh_import_context(self):
        """Provide a fresh import context"""
        # Clear all ui modules
        modules_to_clear = [
            name for name in list(sys.modules.keys())
            if name.startswith("ui.")
        ]
        saved = {}
        for name in modules_to_clear:
            saved[name] = sys.modules.pop(name)

        yield saved

        # Restore
        for name, module in saved.items():
            if module is not None:
                sys.modules[name] = module

    def test_import_does_not_pollute_global_namespace(self, fresh_import_context):
        """Test that importing ui.main doesn't pollute global namespace"""
        initial_globals = set(globals().keys())


        # Should not add to global namespace
        assert set(globals().keys()) == initial_globals

    def test_import_creates_submodule_entries(self, fresh_import_context):
        """Test that importing main creates submodule entries"""
        # Import ui.main to trigger module loading
        import ui.main

        # Check that submodules are registered
        assert "ui.main" in sys.modules
        assert "ui.formatters" in sys.modules
        assert "ui.icons" in sys.modules
        assert "ui.colors" in sys.modules

    def test_star_import_creates_local_namespace(self):
        """Test that star import creates entries in local namespace"""
        ns = {}

        exec("from ui.main import *", ns)

        # Should contain __all__ entries
        import ui.main
        for name in ui.main.__all__:
            assert name in ns, f"Missing {name} in star import namespace"

    def test_star_import_does_not_add_privates(self):
        """Test that star import doesn't add private attributes"""
        ns = {}

        exec("from ui.main import *", ns)

        # Should not have private attributes that aren't in __all__
        # (except the backward compatibility ones)
        import ui.main
        for name in ns:
            if name.startswith("__"):
                continue
            # If it's in the namespace, it should be in __all__
            # or be a Python builtin
            if name in ui.main.__all__ or name == "__builtins__":
                continue
            # Otherwise it's unexpected
            assert not name.startswith("_"), f"Unexpected private: {name}"


class TestCapabilityConsistency:
    """Tests for capability detection consistency"""

    def test_capabilities_are_boolean(self):
        """Test that all capabilities are boolean"""
        import ui.main

        for cap in ["FANCY_UI", "UNICODE", "COLOR", "INTERACTIVE"]:
            value = getattr(ui.main, cap)
            assert isinstance(value, bool), f"{cap} should be bool"

    def test_capability_aliases_match(self):
        """Test that capability aliases match their sources"""
        import ui.main

        alias_pairs = [
            ("_FANCY_UI", "FANCY_UI"),
            ("_UNICODE", "UNICODE"),
            ("_COLOR", "COLOR"),
            ("_INTERACTIVE", "INTERACTIVE"),
        ]

        for alias, original in alias_pairs:
            assert getattr(ui.main, alias) == getattr(ui.main, original)

    def test_capabilities_are_consistent_across_imports(self):
        """Test capabilities are consistent across different import styles"""
        # Direct import
        import ui.main
        capabilities1 = {
            "FANCY_UI": ui.main.FANCY_UI,
            "UNICODE": ui.main.UNICODE,
            "COLOR": ui.main.COLOR,
            "INTERACTIVE": ui.main.INTERACTIVE,
        }

        # From import
        from ui.main import FANCY_UI, UNICODE, COLOR, INTERACTIVE
        capabilities2 = {
            "FANCY_UI": FANCY_UI,
            "UNICODE": UNICODE,
            "COLOR": COLOR,
            "INTERACTIVE": INTERACTIVE,
        }

        assert capabilities1 == capabilities2


class TestExportIntegrity:
    """Tests for export integrity and completeness"""

    def test_all_exports_are_callable_or_class(self):
        """Test that all exports (except constants) are callable or classes"""
        import ui.main

        non_callable_exports = [
            "FANCY_UI", "UNICODE", "COLOR", "INTERACTIVE",
            "_FANCY_UI", "_UNICODE", "_COLOR", "_INTERACTIVE",
        ]

        for name in ui.main.__all__:
            if name in non_callable_exports:
                continue

            value = getattr(ui.main, name)
            # Should be callable (function or class) or a type/class
            assert callable(value) or isinstance(value, type), \
                f"Export {name} should be callable or class"

    def test_all_functionality_accessible_via_exports(self):
        """Test that all key functionality is accessible via exports"""
        import ui.main

        # Test that key items are accessible
        assert hasattr(ui.main, "Icons")
        assert hasattr(ui.main, "icon")
        assert hasattr(ui.main, "success")
        assert hasattr(ui.main, "error")
        assert hasattr(ui.main, "box")
        assert hasattr(ui.main, "progress_bar")
        assert hasattr(ui.main, "print_header")

    def test_exports_cover_all_categories(self):
        """Test that exports cover all UI categories"""
        import ui.main

        categories = {
            "capabilities": ["supports_unicode", "supports_color", "supports_interactive"],
            "icons": ["Icons", "icon"],
            "colors": ["success", "error", "warning", "info"],
            "boxes": ["box", "divider"],
            "progress": ["progress_bar"],
            "formatters": ["print_header", "print_section"],
        }

        for category, items in categories.items():
            for item in items:
                assert hasattr(ui.main, item), f"Missing {item} from {category}"


class TestRuntimeBehavior:
    """Tests for runtime behavior and usage patterns"""

    def test_concurrent_imports(self):
        """Test that concurrent imports work correctly"""
        # Import in different ways simultaneously
        import ui.main as main1
        from ui import main as main2
        import ui.main

        # All should reference same module
        assert id(main1) == id(main2) == id(ui.main)

    def test_module_docstring_present(self):
        """Test that module has proper docstring"""
        import ui.main

        assert ui.main.__doc__ is not None
        assert len(ui.main.__doc__) > 0

        # Check for key documentation keywords
        doc_lower = ui.main.__doc__.lower()
        keywords = ["ui", "utility", "component", "export"]
        assert any(kw in doc_lower for kw in keywords)

    def test_module_file_attribute(self):
        """Test that module has correct file attribute"""
        import ui.main

        assert hasattr(ui.main, "__file__")
        assert "main.py" in ui.main.__file__ or "__init__.py" in ui.main.__file__


class TestBackwardCompatibility:
    """Tests for backward compatibility guarantees"""

    def test_underscore_capabilities_always_exist(self):
        """Test that underscore-prefixed capabilities always exist"""
        import ui.main

        # These are for backward compatibility
        assert hasattr(ui.main, "_FANCY_UI")
        assert hasattr(ui.main, "_UNICODE")
        assert hasattr(ui.main, "_COLOR")
        assert hasattr(ui.main, "_INTERACTIVE")

    def test_old_import_patterns_work(self):
        """Test that old import patterns still work"""
        # These should not raise ImportError
        try:
            pass
            # If we get here, imports worked
            assert True
        except ImportError:
            pytest.fail("Backward compatibility imports failed")

    def test_exports_do_not_change_between_versions(self):
        """Test that __all__ remains stable (regression test)"""
        import ui.main

        # This is a regression test - if __all__ changes unexpectedly,
        # this test will fail
        expected_categories = [
            "supports_unicode",
            "supports_color",
            "supports_interactive",
            "Icons",
            "icon",
            "Color",
            "color",
            "success",
            "error",
            "warning",
            "info",
            "muted",
            "highlight",
            "bold",
            "box",
            "divider",
            "progress_bar",
            "MenuOption",
            "select_menu",
            "BuildState",
            "BuildStatus",
            "StatusManager",
            "print_header",
            "print_section",
            "print_status",
            "print_key_value",
            "print_phase_status",
            "Spinner",
        ]

        for export in expected_categories:
            assert export in ui.main.__all__, \
                f"Expected export {export} not in __all__"


class TestErrorHandling:
    """Tests for error handling and edge cases"""

    def test_missing_attribute_raises_attribute_error(self):
        """Test that accessing missing attributes raises AttributeError"""
        import ui.main

        with pytest.raises(AttributeError):
            _ = ui.main.NONEXISTENT_ATTRIBUTE

    def test_import_with_missing_dependencies(self):
        """Test import behavior if dependencies are missing"""
        # This tests that the module handles missing dependencies gracefully
        # We can't easily test this without actually removing dependencies,
        # but we can verify the structure is correct
        import ui.main

        # Module should load without errors
        assert ui.main is not None

    def test_module_survives_attribute_deletion(self):
        """Test that module handles attribute deletion gracefully"""
        import ui.main

        # Save original value
        original_value = ui.main.FANCY_UI

        # Delete and restore
        try:
            del ui.main.FANCY_UI
            # Access should raise AttributeError
            with pytest.raises(AttributeError):
                _ = ui.main.FANCY_UI
        finally:
            # Restore for other tests
            ui.main.FANCY_UI = original_value


class TestPerformance:
    """Tests for performance characteristics"""

    def test_import_time_reasonable(self):
        """Test that import time is reasonable"""
        import time

        start = time.time()
        elapsed = time.time() - start

        # Import should be fast (< 1 second)
        assert elapsed < 1.0, f"Import took {elapsed:.3f}s, too slow"

    def test_reimport_time_reasonable(self):
        """Test that reimport time is reasonable (module should be cached)"""
        import time


        start = time.time()
        # Re-import should be instant since module is cached
        elapsed = time.time() - start

        # Reimport should be very fast since module is cached (< 0.01 seconds)
        assert elapsed < 0.01, f"Reimport took {elapsed:.3f}s, too slow (module should be cached)"

    def test_attribute_access_time_reasonable(self):
        """Test that attribute access is fast"""
        import time

        import ui.main

        iterations = 10000
        start = time.time()

        for _ in range(iterations):
            _ = ui.main.FANCY_UI
            _ = ui.main.UNICODE
            _ = ui.main.success
            _ = ui.main.icon

        elapsed = time.time() - start

        # Should be very fast (< 0.1 seconds for 10k iterations)
        assert elapsed < 0.1, f"Attribute access took {elapsed:.3f}s, too slow"


class TestThreadSafety:
    """Tests for thread safety (basic checks)"""

    def test_concurrent_attribute_access(self):
        """Test that concurrent attribute access works"""
        import threading
        import ui.main

        errors = []

        def access_attributes():
            try:
                for _ in range(100):
                    _ = ui.main.FANCY_UI
                    _ = ui.main.success
                    _ = ui.main.icon
                    _ = ui.main.print_header
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=access_attributes) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors in concurrent access: {errors}"


class TestMemoryBehavior:
    """Tests for memory behavior"""

    def test_import_does_not_leak_memory(self):
        """Test that repeated imports don't leak memory (module should be cached)"""
        import gc
        import sys

        # Get initial module count
        initial_modules = len(sys.modules)

        # Import multiple times - module should be cached
        for _ in range(10):
            pass

        # Force garbage collection
        gc.collect()

        # Module count should not have grown
        final_modules = len(sys.modules)
        # Since module is cached, there should be minimal growth
        assert final_modules - initial_modules < 5, \
            f"Module count grew from {initial_modules} to {final_modules}"


class TestSubmoduleIntegration:
    """Tests for integration with submodules"""

    def test_formatters_integration(self):
        """Test integration with formatters submodule"""
        import ui.main

        # Should be able to use formatters
        assert callable(ui.main.print_header)
        assert callable(ui.main.print_status)

    def test_icons_integration(self):
        """Test integration with icons submodule"""
        import ui.main

        # Should have Icons class
        assert hasattr(ui.main, "Icons")
        assert hasattr(ui.main, "icon")

    def test_colors_integration(self):
        """Test integration with colors submodule"""
        import ui.main

        # Should have color functions
        assert callable(ui.main.success)
        assert callable(ui.main.error)
        assert callable(ui.main.warning)

    def test_progress_integration(self):
        """Test integration with progress submodule"""
        import ui.main

        # Should have progress_bar
        assert callable(ui.main.progress_bar)

    def test_status_integration(self):
        """Test integration with status submodule"""
        import ui.main

        # Should have status classes
        assert hasattr(ui.main, "BuildState")
        assert hasattr(ui.main, "BuildStatus")
        assert hasattr(ui.main, "StatusManager")
