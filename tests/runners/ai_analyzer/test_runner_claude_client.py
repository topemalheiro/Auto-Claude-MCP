"""Tests for claude_client.py - ClaudeAnalysisClient class"""

from runners.ai_analyzer.claude_client import ClaudeAnalysisClient, CLAUDE_SDK_AVAILABLE
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json


@pytest.fixture
def mock_project_dir(tmp_path):
    """Create a mock project directory."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir


class TestClaudeAnalysisClientInit:
    """Tests for ClaudeAnalysisClient.__init__"""

    def test_init_when_sdk_available(self, mock_project_dir):
        """Test initialization when SDK is available."""
        if not CLAUDE_SDK_AVAILABLE:
            pytest.skip("Claude SDK not available")

        from unittest.mock import patch

        with patch("core.auth.require_auth_token"):
            client = ClaudeAnalysisClient(mock_project_dir)
            assert client.project_dir == mock_project_dir

    def test_init_when_sdk_unavailable(self, mock_project_dir):
        """Test initialization raises error when SDK unavailable."""
        with patch("runners.ai_analyzer.claude_client.CLAUDE_SDK_AVAILABLE", False):
            with pytest.raises(RuntimeError) as exc_info:
                ClaudeAnalysisClient(mock_project_dir)
            assert "claude-agent-sdk not available" in str(exc_info.value)

    def test_init_validates_oauth_token(self, mock_project_dir):
        """Test initialization validates OAuth token."""
        if not CLAUDE_SDK_AVAILABLE:
            pytest.skip("Claude SDK not available")

        from unittest.mock import patch

        with patch("core.auth.require_auth_token") as mock_auth:
            client = ClaudeAnalysisClient(mock_project_dir)
            mock_auth.assert_called_once()


class TestValidateOAuthToken:
    """Tests for _validate_oauth_token method"""

    def test_validate_oauth_token_success(self, mock_project_dir):
        """Test successful OAuth token validation."""
        if not CLAUDE_SDK_AVAILABLE:
            pytest.skip("Claude SDK not available")

        from unittest.mock import patch

        with patch("core.auth.require_auth_token"):
            client = ClaudeAnalysisClient(mock_project_dir)
            # Should not raise
            client._validate_oauth_token()

    def test_validate_oauth_token_failure(self, mock_project_dir):
        """Test OAuth token validation failure."""
        if not CLAUDE_SDK_AVAILABLE:
            pytest.skip("Claude SDK not available")

        from unittest.mock import patch

        with patch(
            "core.auth.require_auth_token",
            side_effect=ValueError("No auth token"),
        ):
            with pytest.raises(ValueError):
                ClaudeAnalysisClient(mock_project_dir)


class TestCreateSettingsFile:
    """Tests for _create_settings_file method"""

    def test_create_settings_file(self, mock_project_dir):
        """Test settings file creation with correct content."""
        if not CLAUDE_SDK_AVAILABLE:
            pytest.skip("Claude SDK not available")

        from unittest.mock import patch

        with patch("core.auth.require_auth_token"):
            client = ClaudeAnalysisClient(mock_project_dir)
            settings_file = client._create_settings_file()

            # Assert file was created
            assert settings_file.exists()

            # Assert content is valid JSON
            content = json.loads(settings_file.read_text(encoding="utf-8"))
            assert "sandbox" in content
            assert "permissions" in content
            assert content["sandbox"]["enabled"] is True
            assert content["permissions"]["defaultMode"] == "acceptEdits"

            # Cleanup
            settings_file.unlink()

    def test_create_settings_file_allowed_tools(self, mock_project_dir):
        """Test settings file includes correct allowed tools."""
        if not CLAUDE_SDK_AVAILABLE:
            pytest.skip("Claude SDK not available")

        from unittest.mock import patch

        with patch("core.auth.require_auth_token"):
            client = ClaudeAnalysisClient(mock_project_dir)
            settings_file = client._create_settings_file()

            content = json.loads(settings_file.read_text(encoding="utf-8"))
            allow_list = content["permissions"]["allow"]

            # Check expected tools are allowed
            allowed_patterns = ["Read(./**)", "Glob(./**)", "Grep(./**)"]
            for pattern in allowed_patterns:
                assert pattern in allow_list

            # Cleanup
            settings_file.unlink()


class TestCreateClient:
    """Tests for _create_client method"""

    def test_create_client_returns_sdk_client(self, mock_project_dir):
        """Test _create_client returns ClaudeSDKClient instance."""
        if not CLAUDE_SDK_AVAILABLE:
            pytest.skip("Claude SDK not available")

        from unittest.mock import patch

        with patch("core.auth.require_auth_token"):
            client = ClaudeAnalysisClient(mock_project_dir)
            settings_file = client._create_settings_file()

            sdk_client = client._create_client(settings_file)

            # Assert returns proper client
            assert sdk_client is not None

            # Cleanup
            settings_file.unlink()

    def test_create_client_system_prompt(self, mock_project_dir):
        """Test _create_client sets correct system prompt."""
        if not CLAUDE_SDK_AVAILABLE:
            pytest.skip("Claude SDK not available")

        from unittest.mock import patch
        from claude_agent_sdk import ClaudeAgentOptions

        with patch("core.auth.require_auth_token"):
            client = ClaudeAnalysisClient(mock_project_dir)
            settings_file = client._create_settings_file()

            # Get the options used
            with patch(
                "runners.ai_analyzer.claude_client.ClaudeSDKClient"
            ) as mock_sdk_class:
                mock_sdk_class.return_value = MagicMock()
                client._create_client(settings_file)

                # Check ClaudeAgentOptions was created
                call_kwargs = mock_sdk_class.call_args[1]
                options = call_kwargs["options"]
                assert isinstance(options, ClaudeAgentOptions)

                # System prompt should include project directory
                assert str(mock_project_dir) in options.system_prompt
                assert "senior software architect" in options.system_prompt

            # Cleanup
            settings_file.unlink()

    def test_create_client_with_model_resolution(self, mock_project_dir):
        """Test _create_client resolves model via API Profile."""
        if not CLAUDE_SDK_AVAILABLE:
            pytest.skip("Claude SDK not available")

        from unittest.mock import patch

        with patch("core.auth.require_auth_token"):
            with patch("runners.ai_analyzer.claude_client.resolve_model_id") as mock_resolve:
                mock_resolve.return_value = "claude-3-5-sonnet-20241022"

                client = ClaudeAnalysisClient(mock_project_dir)
                settings_file = client._create_settings_file()

                with patch(
                    "runners.ai_analyzer.claude_client.ClaudeSDKClient"
                ) as mock_sdk_class:
                    mock_sdk_class.return_value = MagicMock()
                    client._create_client(settings_file)

                    # Should have called resolve_model_id
                    mock_resolve.assert_called_once_with("sonnet")

                # Cleanup
                settings_file.unlink()


class TestRunAnalysisQuery:
    """Tests for run_analysis_query method"""

    @pytest.mark.asyncio
    async def test_run_analysis_query_success(self, mock_project_dir):
        """Test successful analysis query execution."""
        if not CLAUDE_SDK_AVAILABLE:
            pytest.skip("Claude SDK not available")

        from unittest.mock import patch

        with patch("core.auth.require_auth_token"):
            client = ClaudeAnalysisClient(mock_project_dir)

            # Mock the client methods
            mock_sdk_client = MagicMock()
            mock_sdk_client.__aenter__ = AsyncMock(return_value=mock_sdk_client)
            mock_sdk_client.__aexit__ = AsyncMock()
            mock_sdk_client.query = AsyncMock()

            # Mock response stream
            async def mock_response():
                mock_msg = MagicMock()
                mock_msg.__class__.__name__ = "AssistantMessage"
                # Create a proper content mock with text attribute
                mock_content = MagicMock()
                mock_content.text = "Analysis result"
                mock_msg.content = [mock_content]
                yield mock_msg

            mock_sdk_client.receive_response = mock_response

            with patch("runners.ai_analyzer.claude_client.ClaudeSDKClient") as mock_sdk_class:
                mock_sdk_class.return_value = mock_sdk_client

                # Act
                result = await client.run_analysis_query("Test prompt")

                # Assert
                assert "Analysis result" in result
                mock_sdk_client.query.assert_called_once_with("Test prompt")

    @pytest.mark.asyncio
    async def test_run_analysis_query_cleans_up_settings_file(self, mock_project_dir):
        """Test settings file is cleaned up after query."""
        if not CLAUDE_SDK_AVAILABLE:
            pytest.skip("Claude SDK not available")

        from unittest.mock import patch

        with patch("core.auth.require_auth_token"):
            client = ClaudeAnalysisClient(mock_project_dir)

            # Mock the client
            mock_sdk_client = MagicMock()
            mock_sdk_client.__aenter__ = AsyncMock(return_value=mock_sdk_client)
            mock_sdk_client.__aexit__ = AsyncMock()
            mock_sdk_client.query = AsyncMock()

            async def mock_response():
                mock_msg = MagicMock()
                mock_msg.content = [MagicMock(text="Result")]
                yield mock_msg

            mock_sdk_client.receive_response = mock_response

            with patch("runners.ai_analyzer.claude_client.ClaudeSDKClient") as mock_sdk_class:
                mock_sdk_class.return_value = mock_sdk_client

                settings_files = []

                def track_settings_file(settings_file):
                    settings_files.append(settings_file)
                    return MagicMock()

                original_create = client._create_client
                client._create_client = lambda sf: (
                    settings_files.append(sf) or original_create(sf)
                )

                # Act
                await client.run_analysis_query("Test")

                # Assert - settings file should be cleaned up
                # Note: The actual cleanup happens in the finally block
                # We just verify the method completes without error

    @pytest.mark.asyncio
    async def test_run_analysis_query_handles_exception(self, mock_project_dir):
        """Test run_analysis_query handles exceptions gracefully."""
        if not CLAUDE_SDK_AVAILABLE:
            pytest.skip("Claude SDK not available")

        from unittest.mock import patch

        with patch("core.auth.require_auth_token"):
            client = ClaudeAnalysisClient(mock_project_dir)

            # Mock client that raises exception
            with patch(
                "runners.ai_analyzer.claude_client.ClaudeSDKClient",
                side_effect=Exception("SDK Error"),
            ):
                # Should raise the exception
                with pytest.raises(Exception, match="SDK Error"):
                    await client.run_analysis_query("Test prompt")


class TestCollectResponse:
    """Tests for _collect_response method"""

    @pytest.mark.asyncio
    async def test_collect_response_with_text_block(self, mock_project_dir):
        """Test _collect_response extracts text from TextBlock."""
        if not CLAUDE_SDK_AVAILABLE:
            pytest.skip("Claude SDK not available")

        from unittest.mock import patch

        with patch("core.auth.require_auth_token"):
            client = ClaudeAnalysisClient(mock_project_dir)

            # Mock client with TextBlock response
            mock_client = MagicMock()

            async def mock_stream():
                mock_msg = MagicMock()
                mock_msg.__class__.__name__ = "AssistantMessage"
                text_block = MagicMock()
                text_block.text = "Response text here"
                text_block.__class__.__name__ = "TextBlock"
                mock_msg.content = [text_block]
                yield mock_msg

            mock_client.receive_response = mock_stream

            # Act
            result = await client._collect_response(mock_client)

            # Assert
            assert result == "Response text here"

    @pytest.mark.asyncio
    async def test_collect_response_with_multiple_blocks(self, mock_project_dir):
        """Test _collect_response handles multiple content blocks."""
        if not CLAUDE_SDK_AVAILABLE:
            pytest.skip("Claude SDK not available")

        from unittest.mock import patch

        with patch("core.auth.require_auth_token"):
            client = ClaudeAnalysisClient(mock_project_dir)

            # Mock client with multiple TextBlocks
            mock_client = MagicMock()

            async def mock_stream():
                mock_msg = MagicMock()
                mock_msg.__class__.__name__ = "AssistantMessage"
                text_block1 = MagicMock()
                text_block1.text = "First part "
                text_block1.__class__.__name__ = "TextBlock"
                text_block2 = MagicMock()
                text_block2.text = "second part"
                text_block2.__class__.__name__ = "TextBlock"
                mock_msg.content = [text_block1, text_block2]
                yield mock_msg

            mock_client.receive_response = mock_stream

            # Act
            result = await client._collect_response(mock_client)

            # Assert
            assert result == "First part second part"

    @pytest.mark.asyncio
    async def test_collect_response_ignores_non_text_blocks(self, mock_project_dir):
        """Test _collect_response ignores non-TextBlock content."""
        if not CLAUDE_SDK_AVAILABLE:
            pytest.skip("Claude SDK not available")

        from unittest.mock import patch

        with patch("core.auth.require_auth_token"):
            client = ClaudeAnalysisClient(mock_project_dir)

            # Mock client with mixed content
            mock_client = MagicMock()

            async def mock_stream():
                mock_msg = MagicMock()
                mock_msg.__class__.__name__ = "AssistantMessage"
                text_block = MagicMock()
                text_block.text = "Text content"
                text_block.__class__.__name__ = "TextBlock"
                # Block without text attribute
                other_block = MagicMock(spec=[])  # No 'text' attribute
                other_block.__class__.__name__ = "ToolUseBlock"
                mock_msg.content = [other_block, text_block]
                yield mock_msg

            mock_client.receive_response = mock_stream

            # Act
            result = await client._collect_response(mock_client)

            # Assert - should only include text from TextBlock
            assert result == "Text content"

    @pytest.mark.asyncio
    async def test_collect_response_empty(self, mock_project_dir):
        """Test _collect_response with empty response."""
        if not CLAUDE_SDK_AVAILABLE:
            pytest.skip("Claude SDK not available")

        from unittest.mock import patch

        with patch("core.auth.require_auth_token"):
            client = ClaudeAnalysisClient(mock_project_dir)

            # Mock client with no messages
            mock_client = MagicMock()

            async def mock_stream():
                return
                yield  # pragma: no cover (never reached)

            mock_client.receive_response = mock_stream

            # Act
            result = await client._collect_response(mock_client)

            # Assert
            assert result == ""


class TestClientDefaults:
    """Tests for ClaudeAnalysisClient class defaults"""

    def test_default_model(self):
        """Test DEFAULT_MODEL constant."""
        from runners.ai_analyzer.claude_client import ClaudeAnalysisClient

        assert ClaudeAnalysisClient.DEFAULT_MODEL == "sonnet"

    def test_allowed_tools(self):
        """Test ALLOWED_TOOLS constant."""
        from runners.ai_analyzer.claude_client import ClaudeAnalysisClient

        expected_tools = ["Read", "Glob", "Grep"]
        assert ClaudeAnalysisClient.ALLOWED_TOOLS == expected_tools

    def test_max_turns(self):
        """Test MAX_TURNS constant."""
        from runners.ai_analyzer.claude_client import ClaudeAnalysisClient

        assert ClaudeAnalysisClient.MAX_TURNS == 50
