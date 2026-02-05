"""Tests package - adds apps/backend to Python path."""
import sys
from pathlib import Path

# Add apps/backend to Python path so we can import modules like review, qa, etc.
backend_path = Path(__file__).parent / "apps" / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))
