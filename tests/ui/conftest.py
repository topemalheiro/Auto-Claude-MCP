"""Pytest configuration for UI tests to ensure proper isolation."""

import pytest


@pytest.fixture(autouse=True, scope="function")
def reset_ui_capabilities(monkeypatch):
    """
    Reset UI capability flags before each test to ensure isolation.
    This prevents tests from affecting each other through shared module state.
    """
    import ui.capabilities as caps
    import ui.progress
    import ui.menu

    # Store original values
    orig_interactive = caps.INTERACTIVE
    orig_color = caps.COLOR
    orig_unicode = caps.UNICODE

    # Also store original progress.COLOR (since it's imported from capabilities)
    orig_progress_color = ui.progress.COLOR

    # Set INTERACTIVE to False by default for tests (prevents interactive menu issues)
    monkeypatch.setattr(caps, "INTERACTIVE", False, raising=False)

    yield

    # Restore original values after each test
    caps.INTERACTIVE = orig_interactive
    caps.COLOR = orig_color
    caps.UNICODE = orig_unicode

    # Restore progress.COLOR and menu.INTERACTIVE by reloading modules
    import importlib
    importlib.reload(ui.progress)
    importlib.reload(ui.menu)
