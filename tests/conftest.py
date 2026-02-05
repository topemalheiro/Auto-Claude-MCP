"""
Root conftest for tests - adds apps/backend to Python path.
"""

import sys
from pathlib import Path

# Add apps/backend to Python path so we can import modules like review, qa, etc.
# The structure is: repo_root/tests/conftest.py, repo_root/apps/backend/
backend_path = Path(__file__).parent.parent / "apps" / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))
