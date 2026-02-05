"""
Test helper to trigger secretstorage ImportError path.

This module is executed as a subprocess to test the secretstorage import
fallback in core/auth.py lines 32-33.

The approach: We run this module with secretstorage blocked, import core.auth,
and verify that secretstorage is set to None.
"""

import sys


def main():
    """Run test with secretstorage unavailable"""
    # Block secretstorage from being imported
    class BlockSecretstorage:
        """Import hook that blocks secretstorage"""

        def find_module(self, fullname, path=None):
            if fullname == "secretstorage":
                return self
            return None

        def load_module(self, fullname):
            raise ImportError(f"No module named '{fullname}' (blocked for testing)")

    # Install import hook
    sys.meta_path.insert(0, BlockSecretstorage())

    try:
        # Import core.auth - this will trigger ImportError on secretstorage
        # Lines 32-33 should execute: except ImportError: secretstorage = None
        import core.auth

        # Verify secretstorage is None
        if core.auth.secretstorage is None:
            print("SUCCESS: secretstorage is None (ImportError path covered)")
            return 0
        else:
            print(f"FAIL: secretstorage is {core.auth.secretstorage}")
            return 1
    except Exception as e:
        print(f"FAIL: Exception during import: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
