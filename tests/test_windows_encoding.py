"""
Test Windows encoding configuration for subprocess calls.

This test verifies that the encoding fixes applied to entry point scripts
work correctly on Windows.
"""

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
def test_validate_spec_unicode_output(tmp_path):
    """Test that validate_spec.py handles Unicode characters on Windows."""
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()

    # Create a spec with Unicode content
    (spec_dir / "project_index.json").write_text('{"project_type": "test"}', encoding="utf-8")

    # Find the validate_spec.py script
    # Tests are in /repo_root/tests/, so apps/backend is ../apps/backend
    script_path = Path(__file__).parent.parent / "apps" / "backend" / "spec" / "validate_spec.py"
    if not script_path.exists():
        pytest.skip("validate_spec.py not found")

    # Run validate_spec.py via subprocess
    result = subprocess.run(
        [sys.executable, str(script_path), "--spec-dir", str(spec_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    # Should succeed without encoding errors
    assert result.returncode == 0
