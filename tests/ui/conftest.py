"""
UI test package conftest.py - ensures ui module is properly imported for tests.

This conftest ensures that the ui module and its submodules are properly imported
as real modules (not mocks) before each test in this package runs.
"""

import sys
import pytest
import importlib


@pytest.fixture(autouse=True, scope="session")
def ensure_real_ui_modules():
    """Ensure real ui modules are imported and available.

    This session-scoped fixture runs once at the beginning of the test session
    to ensure that the ui module and its submodules are imported as real modules
    before any test collection happens.
    """
    # Remove any mocked ui modules that might exist
    if 'ui' in sys.modules:
        ui_module = sys.modules['ui']
        if hasattr(ui_module, '_mock_name') or str(type(ui_module)) == "<class 'unittest.mock.MagicMock'>":
            del sys.modules['ui']
            for key in list(sys.modules.keys()):
                if key.startswith('ui.') and key != 'ui':
                    del sys.modules[key]

    importlib.invalidate_caches()

    # Import the real ui modules
    try:
        import ui
        import ui.icons
        import ui.progress
        import ui.capabilities
        import ui.menu
    except ImportError:
        pass

    yield


@pytest.fixture(autouse=True, scope="function")
def ensure_real_ui_modules_per_test(request):
    """Ensure ui modules are real imports, not mocks, before each UI test.

    This fixture runs before each test to update the test module's namespace
    with real ui module references.
    """
    # Force import of real ui modules and update test module's namespace
    if 'ui' in sys.modules:
        ui_module = sys.modules['ui']
        if hasattr(ui_module, '_mock_name') or str(type(ui_module)) == "<class 'unittest.mock.MagicMock'>":
            del sys.modules['ui']
            for key in list(sys.modules.keys()):
                if key.startswith('ui.') and key != 'ui':
                    del sys.modules[key]

    importlib.invalidate_caches()

    # Import the real ui modules
    real_modules = {}
    try:
        import ui
        real_modules['ui'] = ui
        import ui.progress
        real_modules['ui.progress'] = ui.progress
        import ui.icons
        real_modules['ui.icons'] = ui.icons
        import ui.capabilities
        real_modules['ui.capabilities'] = ui.capabilities
        import ui.menu
        real_modules['ui.menu'] = ui.menu
    except ImportError:
        pass

    # Update the test module's namespace to point to the real modules
    if request.module is not None and real_modules:
        # Update module references
        for name, module in real_modules.items():
            request.module.__dict__[name] = module

        # Also update specific symbols that are imported directly
        if 'ui.menu' in real_modules:
            ui_menu = real_modules['ui.menu']
            for attr in ['MenuOption', 'select_menu', '_getch', '_HAS_TERMIOS', '_HAS_MSVCRT']:
                if hasattr(ui_menu, attr):
                    request.module.__dict__[attr] = getattr(ui_menu, attr)
            request.module.__dict__['menu_module'] = ui_menu

        if 'ui.icons' in real_modules:
            ui_icons = real_modules['ui.icons']
            if hasattr(ui_icons, 'Icons'):
                request.module.__dict__['Icons'] = ui_icons.Icons

    yield
