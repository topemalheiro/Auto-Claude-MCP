"""
Fixtures and configuration for review module tests.
"""

import sys
from pathlib import Path

# Add apps/backend to Python path so we can import from review module
backend_path = Path(__file__).parent.parent.parent / "apps" / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))
