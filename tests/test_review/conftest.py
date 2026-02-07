"""
Fixtures and configuration for review module tests.
"""

import sys
from pathlib import Path

# Add project root to Python path for "apps.backend.*" style imports
# The structure is: repo_root/tests/review/conftest.py, repo_root/apps/backend/
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Add apps/backend to Python path so we can import from review module
backend_path = project_root / "apps" / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))
