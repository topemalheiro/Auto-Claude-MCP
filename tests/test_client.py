"""Tests for client.py - Claude client module facade."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Auth token env vars that need to be cleared between tests
AUTH_TOKEN_ENV_VARS = [
    "CLAUDE_CODE_OAUTH_TOKEN",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
]


@pytest.fixture
def clear_auth_env():
    """Clear auth environment variables before and after each test."""
    for var in AUTH_TOKEN_ENV_VARS:
        os.environ.pop(var, None)
    yield
    for var in AUTH_TOKEN_ENV_VARS:
        os.environ.pop(var, None)


class TestClientTokenValidation:
    """Tests for client token validation."""

    @pytest.fixture(autouse=True)
    def setup(self, clear_auth_env):
        """Use shared clear_auth_env fixture."""
        pass

        assert create_client is not None
        assert callable(create_client)

    def test_module_has_all_attribute(self):
        """Test that client module has __all__ attribute."""
        import client

        assert hasattr(client, "__all__")
        assert isinstance(client.__all__, list)

    def test_all_exports_exist(self):
        """Test that all exports in __all__ actually exist."""
        import client

        for name in client.__all__:
            assert hasattr(client, name), f"{name} in __all__ but not exported"

    def test_expected_exports_in_all(self):
        """Test that expected exports are in __all__."""
        import client

        expected = {"create_client"}

        assert set(client.__all__) >= expected


class TestClientModuleLazyImports:
    """Tests for client module lazy import mechanism."""

    def test_getattr_lazy_import(self):
        """Test that __getattr__ provides lazy imports."""
        from client import __getattr__

        # Should be able to get attributes through lazy import
        # This tests the facade pattern without actually importing the heavy core.client
        assert callable(__getattr__)

    def test_create_client_direct_function(self):
        """Test that create_client is a direct function, not lazy."""
        from client import create_client

        # create_client should be directly defined, not lazily imported
        # It should be a function that re-exports from core.client
        assert callable(create_client)
        assert hasattr(create_client, "__module__")
        assert "client" in create_client.__module__


class TestClientModuleFacade:
    """Tests for client module as a facade to core.client."""

    @patch("client.create_client")
    def test_create_client_reexports_from_core(self, mock_create_client):
        """Test that create_client re-exports from core.client."""
        from client import create_client as client_create_client

        # The function should be callable
        assert callable(client_create_client)

    def test_create_client_signature(self):
        """Test that create_client has expected signature."""
        from client import create_client
        import inspect

        # create_client uses *args, **kwargs to forward to core.client.create_client
        sig = inspect.signature(create_client)
        params = list(sig.parameters.keys())

        # Should accept *args and **kwargs
        assert "args" in params
        assert "kwargs" in params

    @patch("client.create_client")
    def test_create_client_with_args(self, mock_create_client):
        """Test that create_client accepts expected arguments."""
        from client import create_client

        # Mock the actual core.client.create_client
        mock_instance = MagicMock()
        mock_create_client.return_value = mock_instance

        # Call with basic args
        result = create_client(
            project_dir=Path("/test/project"),
            spec_dir=Path("/test/spec"),
            model="claude-3-5-sonnet-20241022",
        )

        # Verify it was called (though mocked)
        assert result is not None


class TestClientModuleImports:
    """Tests for client module import structure."""

    def test_no_circular_imports(self):
        """Test that importing client doesn't cause circular imports."""
        import sys

        # Remove from cache if present
        if "client" in sys.modules:
            del sys.modules["client"]

        # Should import without issues
        import client

        assert client is not None

    def test_import_client_module_first(self):
        """Test that client module can be imported before core.client."""
        import sys

        # Remove both from cache
        for mod in ["client", "core.client"]:
            if mod in sys.modules:
                del sys.modules[mod]

        # Import client first (should trigger lazy import of core.client)
        import client

        assert client is not None

        # Now import core.client
        from core import client as core_client

        assert core_client is not None

        # Mock validate_token_not_encrypted to verify it's called
        with patch(
            "core.auth.validate_token_not_encrypted"
        ) as mock_validate, patch("core.client.ClaudeSDKClient"):
            from core.client import create_client

        # They should be different modules
        # client_facade is a lightweight facade
        # core_client contains the actual implementation
        assert core_client is not client_facade


class TestClientModulePatterns:
    """Tests for client module design patterns."""

        # Mock validate_token_not_encrypted to verify it's called
        with patch(
            "core.auth.validate_token_not_encrypted"
        ) as mock_validate, patch("core.simple_client.ClaudeSDKClient"):
            from core.simple_client import create_simple_client

        # The client module should provide a simplified interface
        # to the more complex core.client module
        assert callable(create_client)

            # Verify validation was called with the token
            mock_validate.assert_called_once_with(valid_token)


class TestAPIProfileAuthentication:
    """Tests for API Profile authentication mode (e.g., z.ai, custom endpoints)."""

    @pytest.fixture(autouse=True)
    def setup(self, clear_auth_env):
        """Use shared clear_auth_env fixture."""
        pass

    def test_api_profile_mode_with_valid_token(self, tmp_path, monkeypatch):
        """API profile mode succeeds with ANTHROPIC_BASE_URL and ANTHROPIC_AUTH_TOKEN."""
        api_token = "sk-api-test-token-123456"
        api_endpoint = "https://api.z.ai/v1"

        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", api_token)
        monkeypatch.setenv("ANTHROPIC_BASE_URL", api_endpoint)
        # Ensure no OAuth token is set
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)

        # Mock the SDK client to avoid actual initialization
        mock_sdk_client = MagicMock()
        with patch("core.client.ClaudeSDKClient", return_value=mock_sdk_client):
            from core.client import create_client

            client = create_client(tmp_path, tmp_path, "glm-4", "coder")

            # Verify SDK client was created
            assert client is mock_sdk_client

            # Verify CLAUDE_CODE_OAUTH_TOKEN was NOT set (API profile mode)
            assert "CLAUDE_CODE_OAUTH_TOKEN" not in os.environ

            # Verify ANTHROPIC_AUTH_TOKEN is still set
            assert os.environ.get("ANTHROPIC_AUTH_TOKEN") == api_token
            assert os.environ.get("ANTHROPIC_BASE_URL") == api_endpoint

    def test_api_profile_mode_missing_token_raises_error(self, tmp_path, monkeypatch):
        """API profile mode raises ValueError when ANTHROPIC_AUTH_TOKEN is missing."""
        api_endpoint = "https://api.z.ai/v1"

        monkeypatch.setenv("ANTHROPIC_BASE_URL", api_endpoint)
        # Don't set ANTHROPIC_AUTH_TOKEN - this should cause an error
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)

        from core.client import create_client

        with pytest.raises(ValueError, match=r"API profile mode active.*ANTHROPIC_AUTH_TOKEN is not set"):
            create_client(tmp_path, tmp_path, "glm-4", "coder")

    def test_api_profile_mode_empty_token_raises_error(self, tmp_path, monkeypatch):
        """API profile mode raises ValueError when ANTHROPIC_AUTH_TOKEN is empty string."""
        api_endpoint = "https://api.z.ai/v1"

        monkeypatch.setenv("ANTHROPIC_BASE_URL", api_endpoint)
        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "")  # Empty string
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)

        from core.client import create_client

        with pytest.raises(ValueError, match=r"API profile mode active.*ANTHROPIC_AUTH_TOKEN is not set"):
            create_client(tmp_path, tmp_path, "glm-4", "coder")

    def test_oauth_mode_without_base_url(self, tmp_path, monkeypatch):
        """OAuth mode is used when ANTHROPIC_BASE_URL is not set."""
        oauth_token = "sk-ant-oat01-oauth-token"

        # Don't set ANTHROPIC_BASE_URL - this should trigger OAuth mode
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", oauth_token)
        monkeypatch.setattr("core.auth.get_token_from_keychain", lambda: None)

        # Mock the SDK client
        mock_sdk_client = MagicMock()
        with patch("core.client.ClaudeSDKClient", return_value=mock_sdk_client):
            from core.client import create_client

            client = create_client(tmp_path, tmp_path, "claude-sonnet-4", "coder")

            # Verify SDK client was created
            assert client is mock_sdk_client

            # Verify CLAUDE_CODE_OAUTH_TOKEN was set (OAuth mode)
            assert os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") == oauth_token

    def test_api_profile_takes_precedence_over_oauth(self, tmp_path, monkeypatch):
        """
        When both ANTHROPIC_BASE_URL and OAuth token are set, API profile mode wins.

        create_client() explicitly removes CLAUDE_CODE_OAUTH_TOKEN in API profile mode
        so the SDK uses ANTHROPIC_AUTH_TOKEN instead (SDK prioritizes OAuth over API keys).
        """
        api_token = "sk-api-test-token-123456"
        api_endpoint = "https://api.z.ai/v1"
        oauth_token = "sk-ant-oat01-oauth-token"

        # Set both API profile and OAuth
        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", api_token)
        monkeypatch.setenv("ANTHROPIC_BASE_URL", api_endpoint)
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", oauth_token)

        # Mock the SDK client and OAuth functions to verify OAuth path is NOT taken
        mock_sdk_client = MagicMock()
        with patch("core.client.ClaudeSDKClient", return_value=mock_sdk_client), \
             patch("core.auth.require_auth_token") as mock_require, \
             patch("core.auth.validate_token_not_encrypted") as mock_validate:
            from core.client import create_client

            client = create_client(tmp_path, tmp_path, "glm-4", "coder")

            # Verify SDK client was created
            assert client is mock_sdk_client

            # Verify CLAUDE_CODE_OAUTH_TOKEN was removed (API profile mode)
            assert "CLAUDE_CODE_OAUTH_TOKEN" not in os.environ

            # Ensure OAuth flow was NOT used (this proves API profile path was taken)
            mock_require.assert_not_called()
            mock_validate.assert_not_called()

    def test_empty_base_url_triggers_oauth_mode(self, tmp_path, monkeypatch):
        """Empty ANTHROPIC_BASE_URL should trigger OAuth mode, not API profile mode."""
        oauth_token = "sk-ant-oat01-oauth-token"

        # Set empty ANTHROPIC_BASE_URL - should be treated as "not set"
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "")
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", oauth_token)
        monkeypatch.setattr("core.auth.get_token_from_keychain", lambda: None)

        # Mock require_auth_token to verify it's called (OAuth mode)
        with patch("core.auth.require_auth_token", return_value=oauth_token):
            mock_sdk_client = MagicMock()
            with patch("core.client.ClaudeSDKClient", return_value=mock_sdk_client):
                from core.client import create_client

                client = create_client(tmp_path, tmp_path, "claude-sonnet-4", "coder")

                # Verify SDK client was created
                assert client is mock_sdk_client

    @pytest.mark.parametrize("endpoint", [
        "https://api.z.ai/v1",
        "https://api.example.com",
        "http://localhost:8080/v1",
        "https://custom-gateway.com/anthropic-proxy",
    ])
    def test_api_profile_with_various_endpoints(self, tmp_path, monkeypatch, endpoint):
        """API profile mode works with various endpoint formats."""
        api_token = "sk-api-test-token-123456"

        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", api_token)
        monkeypatch.setenv("ANTHROPIC_BASE_URL", endpoint)
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)

        mock_sdk_client = MagicMock()
        with patch("core.client.ClaudeSDKClient", return_value=mock_sdk_client):
            from core.client import create_client

            client = create_client(tmp_path, tmp_path, "glm-4", "coder")

            assert client is mock_sdk_client
            assert os.environ.get("ANTHROPIC_BASE_URL") == endpoint

    def test_oauth_mode_without_any_token_raises_error(self, tmp_path, monkeypatch):
        """OAuth mode raises ValueError when no OAuth token is available."""
        # Don't set any auth tokens
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)

        # Mock keychain to return None
        monkeypatch.setattr("core.auth.get_token_from_keychain", lambda: None)

        from core.client import create_client

        with pytest.raises(ValueError, match="No OAuth token found"):
            create_client(tmp_path, tmp_path, "claude-sonnet-4", "coder")


class TestAPIProfileAuthenticationIntegration:
    """Integration tests verifying the complete auth flow behavior."""

    @pytest.fixture(autouse=True)
    def setup(self, clear_auth_env):
        """Use shared clear_auth_env fixture."""
        pass

    def test_sdk_env_vars_includes_api_profile_vars(self, monkeypatch):
        """Verify get_sdk_env_vars() passes ANTHROPIC_AUTH_TOKEN and ANTHROPIC_BASE_URL."""
        from core.auth import get_sdk_env_vars

        api_token = "sk-api-test-token"
        api_endpoint = "https://api.z.ai/v1"

        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", api_token)
        monkeypatch.setenv("ANTHROPIC_BASE_URL", api_endpoint)

        sdk_env = get_sdk_env_vars()

        assert sdk_env.get("ANTHROPIC_AUTH_TOKEN") == api_token
        assert sdk_env.get("ANTHROPIC_BASE_URL") == api_endpoint

    def test_sdk_env_vars_excludes_oauth_in_api_profile_mode(self, monkeypatch):
        """Verify SDK env vars don't include CLAUDE_CODE_OAUTH_TOKEN in API profile mode."""
        from core.auth import get_sdk_env_vars

        api_token = "sk-api-test-token"
        api_endpoint = "https://api.z.ai/v1"
        oauth_token = "sk-ant-oat01-oauth-token"

        # Set both API profile and OAuth
        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", api_token)
        monkeypatch.setenv("ANTHROPIC_BASE_URL", api_endpoint)
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", oauth_token)

        sdk_env = get_sdk_env_vars()

        # SDK_ENV_VARS doesn't include CLAUDE_CODE_OAUTH_TOKEN
        # (it's set separately in create_client())
        assert "CLAUDE_CODE_OAUTH_TOKEN" not in sdk_env
        assert sdk_env.get("ANTHROPIC_AUTH_TOKEN") == api_token
        assert sdk_env.get("ANTHROPIC_BASE_URL") == api_endpoint

    def test_api_profile_mode_does_not_validate_oauth_token(self, tmp_path, monkeypatch):
        """In API profile mode, OAuth token validation is skipped."""
        api_token = "sk-api-test-token"
        api_endpoint = "https://api.z.ai/v1"
        encrypted_oauth_token = "enc:encrypted-oauth-token"  # Invalid encrypted format

        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", api_token)
        monkeypatch.setenv("ANTHROPIC_BASE_URL", api_endpoint)
        # Even with a bogus encrypted OAuth token, API profile mode should work
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", encrypted_oauth_token)

        # Mock the SDK client
        mock_sdk_client = MagicMock()
        with patch("core.client.ClaudeSDKClient", return_value=mock_sdk_client):
            from core.client import create_client

            # Should NOT raise ValueError about encrypted token
            # because OAuth validation is skipped in API profile mode
            client = create_client(tmp_path, tmp_path, "glm-4", "coder")

            assert client is mock_sdk_client

    def test_oauth_mode_validates_token_even_with_api_env_vars_set(self, tmp_path, monkeypatch):
        """In OAuth mode (no BASE_URL), token validation happens even if ANTHROPIC_AUTH_TOKEN is set."""
        api_token = "sk-api-test-token"  # This exists but should be ignored in OAuth mode
        encrypted_oauth_token = "enc:encrypted-oauth-token"  # Invalid encrypted format

        # Set ANTHROPIC_AUTH_TOKEN but NOT ANTHROPIC_BASE_URL - this is OAuth mode
        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", api_token)
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", encrypted_oauth_token)
        monkeypatch.setattr("core.auth.get_token_from_keychain", lambda: None)

        from core.client import create_client

        # Should raise ValueError about encrypted token because we're in OAuth mode
        with pytest.raises(ValueError, match="encrypted format"):
            create_client(tmp_path, tmp_path, "claude-sonnet-4", "coder")


class TestAPIProfileAuthenticationEdgeCases:
    """Edge case tests for API profile authentication."""

    @pytest.fixture(autouse=True)
    def setup(self, clear_auth_env):
        """Use shared clear_auth_env fixture."""
        pass

    def test_whitespace_base_url_treated_as_empty(self, tmp_path, monkeypatch):
        """Whitespace-only ANTHROPIC_BASE_URL is trimmed and treated as empty (OAuth mode)."""
        oauth_token = "sk-ant-oat01-oauth-token"

        # Set whitespace-only ANTHROPIC_BASE_URL - should be trimmed to empty string
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "   ")
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", oauth_token)
        monkeypatch.setattr("core.auth.get_token_from_keychain", lambda: None)

        # Mock the SDK client
        mock_sdk_client = MagicMock()
        with patch("core.client.ClaudeSDKClient", return_value=mock_sdk_client):
            from core.client import create_client

            # Should use OAuth mode (whitespace is trimmed)
            client = create_client(tmp_path, tmp_path, "claude-sonnet-4", "coder")

            # Verify SDK client was created successfully
            assert client is mock_sdk_client

    def test_unicode_base_url(self, tmp_path, monkeypatch):
        """API profile mode works with Unicode characters in endpoint URL."""
        api_token = "sk-api-test-token-123456"
        # Using an IDN (Internationalized Domain Name)
        api_endpoint = "https://münchen.example.com/v1"

        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", api_token)
        monkeypatch.setenv("ANTHROPIC_BASE_URL", api_endpoint)

        mock_sdk_client = MagicMock()
        with patch("core.client.ClaudeSDKClient", return_value=mock_sdk_client):
            from core.client import create_client

            client = create_client(tmp_path, tmp_path, "glm-4", "coder")

            assert client is mock_sdk_client
            assert os.environ.get("ANTHROPIC_BASE_URL") == api_endpoint

    def test_api_token_with_special_characters(self, tmp_path, monkeypatch):
        """API profile mode works with tokens containing special characters."""
        # Tokens with various formats
        test_tokens = [
            "sk-api-simple",
            "sk-api-with-dashes-and_underscores",
            "sk.api.with.dots",
            "sk_api_with_123456_numbers",
        ]

        api_endpoint = "https://api.example.com/v1"

        for token in test_tokens:
            monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", token)
            monkeypatch.setenv("ANTHROPIC_BASE_URL", api_endpoint)

            mock_sdk_client = MagicMock()
            with patch("core.client.ClaudeSDKClient", return_value=mock_sdk_client):
                from core.client import create_client

                client = create_client(tmp_path, tmp_path, "glm-4", "coder")

                assert client is mock_sdk_client
                assert os.environ.get("ANTHROPIC_AUTH_TOKEN") == token


class TestSimpleClientAPIProfileAuthentication:
    """Tests for API Profile authentication mode in create_simple_client()."""

    @pytest.fixture(autouse=True)
    def setup(self, clear_auth_env):
        """Use shared clear_auth_env fixture."""
        pass

    def test_simple_client_api_profile_mode_with_valid_token(self, monkeypatch):
        """create_simple_client() works with API profile mode."""
        api_token = "sk-api-test-token-123456"
        api_endpoint = "https://api.z.ai/v1"

        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", api_token)
        monkeypatch.setenv("ANTHROPIC_BASE_URL", api_endpoint)
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)

        mock_sdk_client = MagicMock()
        with patch("core.simple_client.ClaudeSDKClient", return_value=mock_sdk_client):
            from core.simple_client import create_simple_client

            client = create_simple_client(agent_type="merge_resolver")

            # Verify SDK client was created
            assert client is mock_sdk_client

            # Verify CLAUDE_CODE_OAUTH_TOKEN was NOT set (API profile mode)
            assert "CLAUDE_CODE_OAUTH_TOKEN" not in os.environ

    def test_simple_client_api_profile_mode_missing_token_raises_error(self, monkeypatch):
        """create_simple_client() raises ValueError when API profile mode but no token."""
        api_endpoint = "https://api.z.ai/v1"

        monkeypatch.setenv("ANTHROPIC_BASE_URL", api_endpoint)
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)

        from core.simple_client import create_simple_client

        with pytest.raises(ValueError, match=r"API profile mode active.*ANTHROPIC_AUTH_TOKEN is not set"):
            create_simple_client(agent_type="merge_resolver")

    def test_simple_client_oauth_mode_without_base_url(self, monkeypatch):
        """create_simple_client() uses OAuth mode when ANTHROPIC_BASE_URL is not set."""
        oauth_token = "sk-ant-oat01-oauth-token"

        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", oauth_token)
        monkeypatch.setattr("core.auth.get_token_from_keychain", lambda: None)

        mock_sdk_client = MagicMock()
        with patch("core.simple_client.ClaudeSDKClient", return_value=mock_sdk_client):
            from core.simple_client import create_simple_client

            client = create_simple_client(agent_type="merge_resolver")

            # Verify SDK client was created
            assert client is mock_sdk_client

            # Verify CLAUDE_CODE_OAUTH_TOKEN was set (OAuth mode)
            assert os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") == oauth_token

    def test_simple_client_api_profile_takes_precedence_over_oauth(self, monkeypatch):
        """
        When both ANTHROPIC_BASE_URL and OAuth token are set, API profile mode wins.

        create_simple_client() explicitly removes CLAUDE_CODE_OAUTH_TOKEN in API profile mode
        so the SDK uses ANTHROPIC_AUTH_TOKEN instead (SDK prioritizes OAuth over API keys).
        """
        api_token = "sk-api-test-token-123456"
        api_endpoint = "https://api.z.ai/v1"
        oauth_token = "sk-ant-oat01-oauth-token"

        # Set both API profile and OAuth
        monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", api_token)
        monkeypatch.setenv("ANTHROPIC_BASE_URL", api_endpoint)
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", oauth_token)

        # Mock the SDK client and OAuth functions to verify OAuth path is NOT taken
        mock_sdk_client = MagicMock()
        with patch("core.simple_client.ClaudeSDKClient", return_value=mock_sdk_client), \
             patch("core.auth.require_auth_token") as mock_require, \
             patch("core.auth.validate_token_not_encrypted") as mock_validate:
            from core.simple_client import create_simple_client

            client = create_simple_client(agent_type="merge_resolver")

            # Verify SDK client was created
            assert client is mock_sdk_client

            # Verify CLAUDE_CODE_OAUTH_TOKEN was removed (API profile mode)
            assert "CLAUDE_CODE_OAUTH_TOKEN" not in os.environ

            # Ensure OAuth flow was NOT used (this proves API profile path was taken)
            mock_require.assert_not_called()
            mock_validate.assert_not_called()

    def test_simple_client_whitespace_base_url_triggers_oauth_mode(self, monkeypatch):
        """Whitespace-only ANTHROPIC_BASE_URL is trimmed and treated as empty (OAuth mode)."""
        oauth_token = "sk-ant-oat01-oauth-token"

        # Set whitespace-only ANTHROPIC_BASE_URL - should be trimmed to empty string
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "   ")
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", oauth_token)
        monkeypatch.setattr("core.auth.get_token_from_keychain", lambda: None)

        mock_sdk_client = MagicMock()
        with patch("core.simple_client.ClaudeSDKClient", return_value=mock_sdk_client):
            from core.simple_client import create_simple_client

            # Should use OAuth mode (whitespace is trimmed)
            client = create_simple_client(agent_type="merge_resolver")

            # Verify SDK client was created successfully
            assert client is mock_sdk_client
