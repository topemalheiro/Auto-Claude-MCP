"""
Helper module for testing menu.py import failure scenarios.
This module is imported during tests to trigger coverage of import exception handling.
"""
import sys


def trigger_termios_import_failure():
    """Trigger termios import failure to test except ImportError branch."""
    # Remove termios and tty from sys.modules to force import failure
    original_termios = sys.modules.pop('termios', None)
    original_tty = sys.modules.pop('tty', None)
    original_menu = sys.modules.pop('ui.menu', None)
    original_ui = sys.modules.pop('ui', None)

    # Mock builtins.__import__ to raise ImportError for termios/tty
    import builtins
    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == 'termios' or name.startswith('termios.'):
            raise ImportError(f"No module named '{name}'")
        if name == 'tty' or name.startswith('tty.'):
            raise ImportError(f"No module named '{name}'")
        return original_import(name, *args, **kwargs)

    builtins.__import__ = mock_import

    try:
        # Import menu module - termios import should fail
        import ui.menu
        # Force access to trigger module execution
        _ = ui.menu._HAS_TERMIOS
    finally:
        # Restore builtins.__import__
        builtins.__import__ = original_import

        # Restore original modules
        if original_termios is not None:
            sys.modules['termios'] = original_termios
        if original_tty is not None:
            sys.modules['tty'] = original_tty
        if original_menu is not None:
            sys.modules['ui.menu'] = original_menu
        if original_ui is not None:
            sys.modules['ui'] = original_ui


def trigger_msvcrt_import_failure():
    """Trigger msvcrt import failure to test except ImportError branch."""
    # Remove msvcrt from sys.modules to force import failure
    original_msvcrt = sys.modules.pop('msvcrt', None)
    original_menu = sys.modules.pop('ui.menu', None)
    original_ui = sys.modules.pop('ui', None)

    # Mock builtins.__import__ to raise ImportError for msvcrt
    import builtins
    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == 'msvcrt' or name.startswith('msvcrt.'):
            raise ImportError(f"No module named '{name}'")
        return original_import(name, *args, **kwargs)

    builtins.__import__ = mock_import

    try:
        # Import menu module - msvcrt import should fail
        import ui.menu
        # Force access to trigger module execution
        _ = ui.menu._HAS_MSVCRT
    finally:
        # Restore builtins.__import__
        builtins.__import__ = original_import

        # Restore original modules
        if original_msvcrt is not None:
            sys.modules['msvcrt'] = original_msvcrt
        if original_menu is not None:
            sys.modules['ui.menu'] = original_menu
        if original_ui is not None:
            sys.modules['ui'] = original_ui
