"""Tests for insight_extractor module"""

from analysis.insight_extractor import (
    is_extraction_enabled,
    get_extraction_model,
    get_session_diff,
    get_changed_files,
    get_commit_messages,
    gather_extraction_inputs,
    parse_insights,
    _get_subtask_description,
    _get_attempt_history,
    _get_generic_insights,
)
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock, Mock
import pytest
import tempfile
import shutil
import json
import asyncio


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    project_path = Path(temp_dir)
    yield project_path
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def spec_dir(temp_dir):
    """Create a spec directory with implementation plan."""
    spec_path = temp_dir / ".auto-claude" / "specs" / "001"
    spec_path.mkdir(parents=True)
    plan_data = {
        "phases": [
            {
                "subtasks": [
                    {
                        "id": "subtask-1",
                        "description": "Implement feature X",
                    }
                ]
            }
        ]
    }
    (spec_path / "implementation_plan.json").write_text(json.dumps(plan_data))
    return spec_path


@pytest.fixture
def mock_git_repo(temp_dir):
    """Create a mock git repository."""
    import subprocess
    subprocess.run(["git", "init"], cwd=temp_dir, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=temp_dir, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=temp_dir, capture_output=True)
    (temp_dir / "test.txt").write_text("content")
    subprocess.run(["git", "add", "."], cwd=temp_dir, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_dir, capture_output=True)
    return temp_dir


@pytest.fixture
def mock_recovery_manager():
    """Create a mock recovery manager."""
    manager = Mock()
    manager.get_subtask_history = Mock(return_value={
        "attempts": [
            {"success": False, "approach": "First attempt", "error": "Syntax error"},
            {"success": True, "approach": "Second attempt", "error": ""},
        ]
    })
    return manager


class TestIsExtractionEnabled:
    """Tests for is_extraction_enabled function."""

    @patch("analysis.insight_extractor.SDK_AVAILABLE", True)
    @patch("analysis.insight_extractor.get_auth_token")
    def test_enabled_when_sdk_and_token(self, mock_token):
        """Test extraction is enabled when SDK available and has token."""
        mock_token.return_value = "test-token"
        with patch.dict("os.environ", {"INSIGHT_EXTRACTION_ENABLED": "true"}):
            result = is_extraction_enabled()
            assert result is True

    @patch("analysis.insight_extractor.SDK_AVAILABLE", False)
    def test_disabled_when_no_sdk(self):
        """Test extraction is disabled when SDK not available."""
        result = is_extraction_enabled()
        assert result is False

    @patch("analysis.insight_extractor.SDK_AVAILABLE", True)
    @patch("analysis.insight_extractor.get_auth_token")
    def test_disabled_when_no_token(self, mock_token):
        """Test extraction is disabled when no auth token."""
        mock_token.return_value = None
        result = is_extraction_enabled()
        assert result is False

    @patch("analysis.insight_extractor.SDK_AVAILABLE", True)
    @patch("analysis.insight_extractor.get_auth_token")
    def test_respects_env_var_false(self, mock_token):
        """Test extraction respects INSIGHT_EXTRACTION_ENABLED=false."""
        mock_token.return_value = "test-token"
        with patch.dict("os.environ", {"INSIGHT_EXTRACTION_ENABLED": "false"}):
            result = is_extraction_enabled()
            assert result is False

    @patch("analysis.insight_extractor.SDK_AVAILABLE", True)
    @patch("analysis.insight_extractor.get_auth_token")
    def test_respects_env_var_true(self, mock_token):
        """Test extraction respects INSIGHT_EXTRACTION_ENABLED=true."""
        mock_token.return_value = "test-token"
        with patch.dict("os.environ", {"INSIGHT_EXTRACTION_ENABLED": "true"}):
            result = is_extraction_enabled()
            assert result is True


class TestGetExtractionModel:
    """Tests for get_extraction_model function."""

    def test_returns_default_model(self):
        """Test returns default model when env var not set."""
        with patch.dict("os.environ", {}, clear=True):
            result = get_extraction_model()
            assert result == "claude-haiku-4-5-20251001"

    def test_returns_custom_model(self):
        """Test returns custom model from env var."""
        with patch.dict("os.environ", {"INSIGHT_EXTRACTOR_MODEL": "claude-sonnet-4-20250514"}):
            result = get_extraction_model()
            assert result == "claude-sonnet-4-20250514"


class TestGetSessionDiff:
    """Tests for get_session_diff function."""

    def test_no_commits(self):
        """Test returns message when commits not provided."""
        result = get_session_diff(Path("/tmp"), None, None)
        assert "No commits" in result

    def test_same_commit(self):
        """Test returns message when commits are the same."""
        result = get_session_diff(Path("/tmp"), "abc123", "abc123")
        assert "same commit" in result.lower()

    @patch("subprocess.run")
    def test_successful_diff(self, mock_run):
        """Test successful git diff."""
        mock_run.return_value = Mock(
            stdout="@@ -1,1 +1,1 @@\n-old line\n+new line",
            returncode=0
        )
        result = get_session_diff(Path("/tmp"), "abc123", "def456")
        assert "old line" in result or "new line" in result

    @patch("subprocess.run")
    def test_timeout(self, mock_run):
        """Test handles timeout gracefully."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("git", 30)
        result = get_session_diff(Path("/tmp"), "abc123", "def456")
        assert "timed out" in result.lower()

    @patch("subprocess.run")
    def test_exception(self, mock_run):
        """Test handles exception gracefully."""
        mock_run.side_effect = Exception("Git error")
        result = get_session_diff(Path("/tmp"), "abc123", "def456")
        assert "Failed" in result or "error" in result.lower()

    @patch("subprocess.run")
    def test_truncates_large_diff(self, mock_run):
        """Test truncates diff that exceeds MAX_DIFF_CHARS."""
        large_diff = "x" * 20000
        mock_run.return_value = Mock(stdout=large_diff, returncode=0)
        result = get_session_diff(Path("/tmp"), "abc123", "def456")
        assert len(result) < 20000
        assert "truncated" in result.lower()


class TestGetChangedFiles:
    """Tests for get_changed_files function."""

    def test_no_commits(self):
        """Test returns empty list when commits not provided."""
        result = get_changed_files(Path("/tmp"), None, None)
        assert result == []

    def test_same_commit(self):
        """Test returns empty list when commits are the same."""
        result = get_changed_files(Path("/tmp"), "abc123", "abc123")
        assert result == []

    @patch("subprocess.run")
    def test_successful_files(self, mock_run):
        """Test successful file list retrieval."""
        mock_run.return_value = Mock(
            stdout="file1.py\nfile2.py\nfile3.py\n",
            returncode=0
        )
        result = get_changed_files(Path("/tmp"), "abc123", "def456")
        assert len(result) == 3
        assert "file1.py" in result

    @patch("subprocess.run")
    def test_exception_handling(self, mock_run):
        """Test handles exception gracefully."""
        mock_run.side_effect = Exception("Git error")
        result = get_changed_files(Path("/tmp"), "abc123", "def456")
        assert result == []


class TestGetCommitMessages:
    """Tests for get_commit_messages function."""

    def test_no_commits(self):
        """Test returns message when commits not provided."""
        result = get_commit_messages(Path("/tmp"), None, None)
        assert "No commits" in result

    def test_same_commit(self):
        """Test returns message when commits are the same."""
        result = get_commit_messages(Path("/tmp"), "abc123", "abc123")
        assert "No commits" in result

    @patch("subprocess.run")
    def test_successful_messages(self, mock_run):
        """Test successful commit messages retrieval."""
        mock_run.return_value = Mock(
            stdout="abc123 First commit\ndef456 Second commit\n",
            returncode=0
        )
        result = get_commit_messages(Path("/tmp"), "abc123", "def456")
        assert "First commit" in result or "Second commit" in result

    @patch("subprocess.run")
    def test_exception_handling(self, mock_run):
        """Test handles exception gracefully."""
        mock_run.side_effect = Exception("Git error")
        result = get_commit_messages(Path("/tmp"), "abc123", "def456")
        assert "Failed" in result or "error" in result.lower()


class TestGatherExtractionInputs:
    """Tests for gather_extraction_inputs function."""

    def test_gather_all_inputs(self, spec_dir, temp_dir, mock_recovery_manager):
        """Test gathering all extraction inputs."""
        with patch("analysis.insight_extractor.get_session_diff", return_value="test diff"):
            with patch("analysis.insight_extractor.get_changed_files", return_value=["file1.py"]):
                with patch("analysis.insight_extractor.get_commit_messages", return_value="test commit"):
                    result = gather_extraction_inputs(
                        spec_dir=spec_dir,
                        project_dir=temp_dir,
                        subtask_id="subtask-1",
                        session_num=1,
                        commit_before="abc123",
                        commit_after="def456",
                        success=True,
                        recovery_manager=mock_recovery_manager,
                    )
                    assert result["subtask_id"] == "subtask-1"
                    assert result["session_num"] == 1
                    assert result["success"] is True
                    assert "diff" in result
                    assert "changed_files" in result
                    assert "commit_messages" in result
                    assert "attempt_history" in result

    def test_subtask_description_from_plan(self, spec_dir, temp_dir, mock_recovery_manager):
        """Test subtask description is extracted from plan."""
        with patch("analysis.insight_extractor.get_session_diff", return_value=""):
            with patch("analysis.insight_extractor.get_changed_files", return_value=[]):
                with patch("analysis.insight_extractor.get_commit_messages", return_value=""):
                    result = gather_extraction_inputs(
                        spec_dir=spec_dir,
                        project_dir=temp_dir,
                        subtask_id="subtask-1",
                        session_num=1,
                        commit_before="abc123",
                        commit_after="def456",
                        success=True,
                        recovery_manager=mock_recovery_manager,
                    )
                    assert "Implement feature X" in result["subtask_description"]

    def test_no_recovery_manager(self, spec_dir, temp_dir):
        """Test handles missing recovery manager."""
        with patch("analysis.insight_extractor.get_session_diff", return_value=""):
            with patch("analysis.insight_extractor.get_changed_files", return_value=[]):
                with patch("analysis.insight_extractor.get_commit_messages", return_value=""):
                    result = gather_extraction_inputs(
                        spec_dir=spec_dir,
                        project_dir=temp_dir,
                        subtask_id="subtask-1",
                        session_num=1,
                        commit_before="abc123",
                        commit_after="def456",
                        success=True,
                        recovery_manager=None,
                    )
                    assert result["attempt_history"] == []


class TestParseInsights:
    """Tests for parse_insights function."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON response."""
        response = '{"file_insights": [], "patterns_discovered": [], "gotchas_discovered": [], "approach_outcome": {}, "recommendations": []}'
        result = parse_insights(response)
        assert result is not None
        assert "file_insights" in result
        assert "patterns_discovered" in result

    def test_parse_markdown_json(self):
        """Test parsing JSON from markdown code block."""
        response = '''```json
{
    "file_insights": [],
    "patterns_discovered": []
}
```'''
        result = parse_insights(response)
        assert result is not None
        assert "file_insights" in result

    def test_parse_empty_response(self):
        """Test parsing empty response returns None."""
        result = parse_insights("")
        assert result is None

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON returns None."""
        result = parse_insights("{invalid json}")
        assert result is None

    def test_parse_non_dict_response(self):
        """Test parsing non-dict JSON returns None."""
        result = parse_insights('["array", "not", "object"]')
        assert result is None

    def test_adds_default_keys(self):
        """Test adds default keys if missing."""
        response = '{"file_insights": []}'
        result = parse_insights(response)
        assert result is not None
        assert "patterns_discovered" in result
        assert "gotchas_discovered" in result
        assert "approach_outcome" in result
        assert "recommendations" in result


class TestGetGenericInsights:
    """Tests for _get_generic_insights function."""

    def test_returns_generic_insights_success(self):
        """Test returns generic insights for success case."""
        result = _get_generic_insights("subtask-1", True)
        assert result["subtask_id"] == "subtask-1"
        assert result["success"] is True
        assert result["file_insights"] == []
        assert result["patterns_discovered"] == []

    def test_returns_generic_insights_failure(self):
        """Test returns generic insights for failure case."""
        result = _get_generic_insights("subtask-1", False)
        assert result["subtask_id"] == "subtask-1"
        assert result["success"] is False
        assert result["approach_outcome"]["success"] is False


class TestGetSubtaskDescription:
    """Tests for _get_subtask_description function."""

    def test_from_implementation_plan(self, spec_dir):
        """Test getting description from implementation plan."""
        result = _get_subtask_description(spec_dir, "subtask-1")
        assert "Implement feature X" in result

    def test_no_plan_file(self, temp_dir):
        """Test handles missing plan file."""
        result = _get_subtask_description(temp_dir, "subtask-1")
        assert "subtask-1" in result

    def test_subtask_not_found(self, spec_dir):
        """Test handles subtask not found in plan."""
        result = _get_subtask_description(spec_dir, "unknown-subtask")
        assert "unknown-subtask" in result


class TestGetAttemptHistory:
    """Tests for _get_attempt_history function."""

    def test_gets_history_from_manager(self, mock_recovery_manager):
        """Test gets history from recovery manager."""
        result = _get_attempt_history(mock_recovery_manager, "subtask-1")
        assert len(result) == 2
        assert result[0]["success"] is False
        assert result[1]["success"] is True

    def test_no_recovery_manager(self):
        """Test handles missing recovery manager."""
        result = _get_attempt_history(None, "subtask-1")
        assert result == []

    def test_exception_handling(self):
        """Test handles exceptions from recovery manager."""
        manager = Mock()
        manager.get_subtask_history = Mock(side_effect=Exception("Error"))
        result = _get_attempt_history(manager, "subtask-1")
        assert result == []

    def test_limits_attempts(self, mock_recovery_manager):
        """Test limits attempts to MAX_ATTEMPTS_TO_INCLUDE."""
        manager = Mock()
        # Create more attempts than the limit
        attempts = [{"success": True, "approach": f"Attempt {i}"} for i in range(10)]
        manager.get_subtask_history = Mock(return_value={"attempts": attempts})
        result = _get_attempt_history(manager, "subtask-1")
        # Should be limited to MAX_ATTEMPTS_TO_INCLUDE (3)
        assert len(result) <= 3


class TestBuildExtractionPrompt:
    """Tests for _build_extraction_prompt function."""

    def test_prompt_includes_session_data(self):
        """Test prompt includes session data."""
        from analysis.insight_extractor import _build_extraction_prompt

        inputs = {
            "subtask_id": "test-subtask",
            "subtask_description": "Test feature",
            "session_num": 1,
            "success": True,
            "changed_files": ["file1.py", "file2.py"],
            "commit_messages": "abc123 Add feature",
            "diff": "+new code",
            "attempt_history": [],
        }

        prompt = _build_extraction_prompt(inputs)

        assert "test-subtask" in prompt
        assert "Test feature" in prompt
        assert "file1.py" in prompt
        assert "Add feature" in prompt

    def test_prompt_with_failed_session(self):
        """Test prompt includes FAILED status for failed session."""
        from analysis.insight_extractor import _build_extraction_prompt

        inputs = {
            "subtask_id": "test-subtask",
            "subtask_description": "Test feature",
            "session_num": 1,
            "success": False,
            "changed_files": ["file1.py"],
            "commit_messages": "abc123 WIP",
            "diff": "+new code",
            "attempt_history": [],
        }

        prompt = _build_extraction_prompt(inputs)
        assert "FAILED" in prompt

    def test_prompt_with_no_changed_files(self):
        """Test prompt handles no changed files."""
        from analysis.insight_extractor import _build_extraction_prompt

        inputs = {
            "subtask_id": "test-subtask",
            "subtask_description": "Test feature",
            "session_num": 1,
            "success": True,
            "changed_files": [],
            "commit_messages": "",
            "diff": "",
            "attempt_history": [],
        }

        prompt = _build_extraction_prompt(inputs)
        assert "No files changed" in prompt

    def test_prompt_uses_fallback_when_prompt_file_missing(self, tmp_path):
        """Test uses fallback prompt when prompt file doesn't exist."""
        from analysis.insight_extractor import _build_extraction_prompt
        import analysis.insight_extractor as ie_module

        # Save original prompt file path
        original_path = Path(ie_module.__file__).parent / "prompts" / "insight_extractor.md"

        # Mock the prompt file to not exist
        with patch.object(ie_module.Path, "__new__", side_effect=lambda cls, *args, **kwargs: original_path):
            with patch.object(ie_module.Path, "exists", return_value=False):
                inputs = {
                    "subtask_id": "test",
                    "subtask_description": "Test",
                    "session_num": 1,
                    "success": True,
                    "changed_files": [],
                    "commit_messages": "",
                    "diff": "",
                    "attempt_history": [],
                }

                prompt = _build_extraction_prompt(inputs)
                assert "Extract structured insights" in prompt


class TestFormatAttemptHistory:
    """Tests for _format_attempt_history function."""

    def test_empty_history(self):
        """Test formatting empty attempt history."""
        from analysis.insight_extractor import _format_attempt_history

        result = _format_attempt_history([])
        assert "First attempt" in result
        assert "no previous history" in result

    def test_single_attempt_success(self):
        """Test formatting single successful attempt."""
        from analysis.insight_extractor import _format_attempt_history

        attempts = [{"success": True, "approach": "Direct implementation", "error": ""}]
        result = _format_attempt_history(attempts)

        assert "Attempt 1" in result
        assert "SUCCESS" in result
        assert "Direct implementation" in result

    def test_single_attempt_failure(self):
        """Test formatting single failed attempt."""
        from analysis.insight_extractor import _format_attempt_history

        attempts = [{"success": False, "approach": "Wrong approach", "error": "Syntax error on line 42"}]
        result = _format_attempt_history(attempts)

        assert "FAILED" in result
        assert "Wrong approach" in result
        assert "Syntax error on line 42" in result

    def test_multiple_attempts(self):
        """Test formatting multiple attempts."""
        from analysis.insight_extractor import _format_attempt_history

        attempts = [
            {"success": False, "approach": "First try", "error": "Error 1"},
            {"success": False, "approach": "Second try", "error": "Error 2"},
            {"success": True, "approach": "Third try", "error": ""},
        ]
        result = _format_attempt_history(attempts)

        assert "Attempt 1" in result
        assert "Attempt 2" in result
        assert "Attempt 3" in result
        assert result.count("SUCCESS") == 1
        assert result.count("FAILED") == 2

    def test_attempt_without_error(self):
        """Test formatting attempt without error message."""
        from analysis.insight_extractor import _format_attempt_history

        attempts = [{"success": False, "approach": "Some approach", "error": ""}]
        result = _format_attempt_history(attempts)

        assert "FAILED" in result
        assert "Some approach" in result
        # Should not show "Error:" when error is empty
        assert "Error:" not in result


class TestParseInsightsEdgeCases:
    """Additional edge case tests for parse_insights function."""

    def test_parse_json_with_only_code_blocks(self):
        """Test parsing response with only markdown code blocks."""
        # Empty after stripping code blocks
        result = parse_insights("```json\n```")
        assert result is None

    def test_parse_json_with_whitespace_only(self):
        """Test parsing whitespace-only response."""
        result = parse_insights("   \n  \t  ")
        assert result is None

    def test_parse_json_with_large_response(self):
        """Test parsing very large JSON response."""
        from analysis.insight_extractor import MAX_DIFF_CHARS

        # Create a large JSON response
        large_data = {
            "file_insights": [{"file": f"file{i}.py", "insight": "x" * 100} for i in range(100)],
            "patterns_discovered": ["pattern"] * 50,
            "gotchas_discovered": ["gotcha"] * 50,
            "approach_outcome": {"success": True, "approach_used": "test"},
            "recommendations": ["rec"] * 50,
        }
        response = json.dumps(large_data)

        result = parse_insights(response)
        assert result is not None
        assert len(result["file_insights"]) == 100

    def test_parse_json_preserves_valid_data(self):
        """Test that parsing preserves all valid insight data."""
        response = '''{
            "file_insights": [{"file": "test.py", "insight": "Good code"}],
            "patterns_discovered": ["pattern1", "pattern2"],
            "gotchas_discovered": ["gotcha1"],
            "approach_outcome": {"success": true, "approach_used": "TDD"},
            "recommendations": ["use type hints"]
        }'''

        result = parse_insights(response)
        assert result is not None
        assert result["file_insights"][0]["file"] == "test.py"
        assert len(result["patterns_discovered"]) == 2
        assert result["approach_outcome"]["approach_used"] == "TDD"


class TestRunInsightExtraction:
    """Tests for run_insight_extraction async function."""

    @pytest.mark.asyncio
    async def test_returns_none_when_sdk_unavailable(self):
        """Test returns None when SDK is not available."""
        from analysis.insight_extractor import run_insight_extraction

        with patch("analysis.insight_extractor.SDK_AVAILABLE", False):
            result = await run_insight_extraction({"subtask_id": "test"})
            assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_auth_token(self):
        """Test returns None when no auth token available."""
        from analysis.insight_extractor import run_insight_extraction

        with patch("analysis.insight_extractor.SDK_AVAILABLE", True):
            with patch("analysis.insight_extractor.get_auth_token", return_value=None):
                result = await run_insight_extraction({"subtask_id": "test"})
                assert result is None

    @pytest.mark.asyncio
    async def test_successful_extraction(self):
        """Test successful insight extraction."""
        from analysis.insight_extractor import run_insight_extraction

        inputs = {
            "subtask_id": "test-subtask",
            "subtask_description": "Test",
            "session_num": 1,
            "success": True,
            "changed_files": ["test.py"],
            "commit_messages": "Add test",
            "diff": "+code",
            "attempt_history": [],
        }

        # Create a simple mock message
        mock_message = Mock()
        mock_message.__class__.__name__ = "AssistantMessage"

        # Create a mock text block
        mock_block = Mock()
        mock_block.__class__.__name__ = "TextBlock"
        mock_block.text = '{"file_insights": [], "patterns_discovered": [], "gotchas_discovered": [], "approach_outcome": {}, "recommendations": []}'

        mock_message.content = [mock_block]

        # Mock the simple client
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Make receive_response yield the mock message
        async def mock_receive():
            yield mock_message

        mock_client.receive_response = mock_receive
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch("analysis.insight_extractor.SDK_AVAILABLE", True):
            with patch("analysis.insight_extractor.get_auth_token", return_value="test-token"):
                with patch("core.simple_client.create_simple_client", return_value=mock_client):
                    with patch("analysis.insight_extractor.ensure_claude_code_oauth_token"):
                        result = await run_insight_extraction(inputs)
                        assert result is not None
                        assert "file_insights" in result

    @pytest.mark.asyncio
    async def test_extraction_with_empty_response(self):
        """Test extraction when AI returns empty response."""
        from analysis.insight_extractor import run_insight_extraction

        inputs = {
            "subtask_id": "test-subtask",
            "subtask_description": "Test",
            "session_num": 1,
            "success": True,
            "changed_files": [],
            "commit_messages": "",
            "diff": "",
            "attempt_history": [],
        }

        # Mock client that returns empty text
        mock_client = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        # Mock empty response
        mock_msg = Mock()
        mock_msg.__class__.__name__ = "AssistantMessage"
        mock_content = Mock()
        mock_content.__class__.__name__ = "TextBlock"
        mock_content.text = ""
        mock_msg.content = [mock_content]

        async def mock_receive_empty():
            yield mock_msg

        mock_client.receive_response = mock_receive_empty

        with patch("analysis.insight_extractor.SDK_AVAILABLE", True):
            with patch("analysis.insight_extractor.get_auth_token", return_value="test-token"):
                with patch("core.simple_client.create_simple_client", return_value=mock_client):
                    with patch("analysis.insight_extractor.ensure_claude_code_oauth_token"):
                        result = await run_insight_extraction(inputs)
                        assert result is None

    @pytest.mark.asyncio
    async def test_extraction_handles_exception(self):
        """Test extraction handles exceptions gracefully."""
        from analysis.insight_extractor import run_insight_extraction

        inputs = {
            "subtask_id": "test-subtask",
            "subtask_description": "Test",
            "session_num": 1,
            "success": True,
            "changed_files": [],
            "commit_messages": "",
            "diff": "",
            "attempt_history": [],
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(side_effect=Exception("SDK connection failed"))
        mock_client.__aexit__ = AsyncMock()

        with patch("analysis.insight_extractor.SDK_AVAILABLE", True):
            with patch("analysis.insight_extractor.get_auth_token", return_value="test-token"):
                with patch("core.simple_client.create_simple_client", return_value=mock_client):
                    with patch("analysis.insight_extractor.ensure_claude_code_oauth_token"):
                        result = await run_insight_extraction(inputs)
                        assert result is None


class TestExtractSessionInsights:
    """Tests for extract_session_insights main entry point."""

    @pytest.mark.asyncio
    async def test_returns_generic_when_disabled(self, spec_dir, temp_dir):
        """Test returns generic insights when extraction is disabled."""
        from analysis.insight_extractor import extract_session_insights

        with patch("analysis.insight_extractor.is_extraction_enabled", return_value=False):
            result = await extract_session_insights(
                spec_dir=spec_dir,
                project_dir=temp_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_after="def456",
                success=True,
                recovery_manager=None,
            )

            assert result["subtask_id"] == "subtask-1"
            assert result["file_insights"] == []

    @pytest.mark.asyncio
    async def test_returns_generic_when_no_changes(self, spec_dir, temp_dir):
        """Test returns generic insights when no changes made."""
        from analysis.insight_extractor import extract_session_insights

        with patch("analysis.insight_extractor.is_extraction_enabled", return_value=True):
            result = await extract_session_insights(
                spec_dir=spec_dir,
                project_dir=temp_dir,
                subtask_id="subtask-1",
                session_num=1,
                commit_before="abc123",
                commit_after="abc123",  # Same commit
                success=True,
                recovery_manager=None,
            )

            assert result["subtask_id"] == "subtask-1"
            assert result["file_insights"] == []

    @pytest.mark.asyncio
    async def test_successful_extraction_with_metadata(self, spec_dir, temp_dir):
        """Test successful extraction adds metadata."""
        from analysis.insight_extractor import extract_session_insights

        inputs = {
            "subtask_id": "subtask-1",
            "subtask_description": "Test feature",
            "session_num": 2,
            "success": True,
            "changed_files": ["test.py"],
            "commit_messages": "Add feature",
            "diff": "+code",
            "attempt_history": [],
        }

        extracted_insights = {
            "file_insights": [{"file": "test.py", "insight": "Good code"}],
            "patterns_discovered": ["pattern1"],
            "gotchas_discovered": [],
            "approach_outcome": {"success": True},
            "recommendations": [],
        }

        with patch("analysis.insight_extractor.is_extraction_enabled", return_value=True):
            with patch("analysis.insight_extractor.gather_extraction_inputs", return_value=inputs):
                with patch("analysis.insight_extractor.run_insight_extraction", return_value=extracted_insights):
                    result = await extract_session_insights(
                        spec_dir=spec_dir,
                        project_dir=temp_dir,
                        subtask_id="subtask-1",
                        session_num=2,
                        commit_before="abc123",
                        commit_after="def456",
                        success=True,
                        recovery_manager=None,
                    )

                    assert result["subtask_id"] == "subtask-1"
                    assert result["session_num"] == 2
                    assert result["success"] is True
                    assert result["changed_files"] == ["test.py"]
                    assert len(result["file_insights"]) == 1

    @pytest.mark.asyncio
    async def test_falls_back_to_generic_on_extraction_failure(self, spec_dir, temp_dir):
        """Test falls back to generic insights when extraction fails."""
        from analysis.insight_extractor import extract_session_insights

        inputs = {
            "subtask_id": "subtask-1",
            "subtask_description": "Test",
            "session_num": 1,
            "success": False,
            "changed_files": [],
            "commit_messages": "",
            "diff": "",
            "attempt_history": [],
        }

        with patch("analysis.insight_extractor.is_extraction_enabled", return_value=True):
            with patch("analysis.insight_extractor.gather_extraction_inputs", return_value=inputs):
                with patch("analysis.insight_extractor.run_insight_extraction", return_value=None):
                    result = await extract_session_insights(
                        spec_dir=spec_dir,
                        project_dir=temp_dir,
                        subtask_id="subtask-1",
                        session_num=1,
                        commit_before="abc123",
                        commit_after="def456",
                        success=False,
                        recovery_manager=None,
                    )

                    assert result["subtask_id"] == "subtask-1"
                    assert result["success"] is False
                    assert result["file_insights"] == []

    @pytest.mark.asyncio
    async def test_handles_exceptions_gracefully(self, spec_dir, temp_dir):
        """Test handles exceptions and returns generic insights."""
        from analysis.insight_extractor import extract_session_insights

        with patch("analysis.insight_extractor.is_extraction_enabled", return_value=True):
            with patch("analysis.insight_extractor.gather_extraction_inputs", side_effect=Exception("Unexpected error")):
                result = await extract_session_insights(
                    spec_dir=spec_dir,
                    project_dir=temp_dir,
                    subtask_id="subtask-1",
                    session_num=1,
                    commit_before="abc123",
                    commit_after="def456",
                    success=True,
                    recovery_manager=None,
                )

                # Should return generic insights instead of raising
                assert result["subtask_id"] == "subtask-1"
                assert "file_insights" in result


class TestSubtaskDescriptionErrorHandling:
    """Tests for _get_subtask_description error handling."""

    def test_handles_corrupt_json(self, temp_dir):
        """Test handles corrupt JSON in implementation plan."""
        from analysis.insight_extractor import _get_subtask_description

        plan_file = temp_dir / "implementation_plan.json"
        plan_file.write_text("{invalid json")

        result = _get_subtask_description(temp_dir, "subtask-1")
        assert "subtask-1" in result

    def test_handles_json_decode_error(self, temp_dir):
        """Test handles JSON decode errors."""
        from analysis.insight_extractor import _get_subtask_description

        plan_file = temp_dir / "implementation_plan.json"
        plan_file.write_text('{"phases": [{"subtasks": [{"id": "1"}]}')  # Missing closing braces

        result = _get_subtask_description(temp_dir, "subtask-1")
        assert "subtask-1" in result


class TestGetSubtaskDescriptionMultiPhase:
    """Tests for _get_subtask_description with multiple phases."""

    def test_finds_subtask_across_multiple_phases(self, temp_dir):
        """Test finding subtask across multiple phases."""
        from analysis.insight_extractor import _get_subtask_description

        plan_data = {
            "phases": [
                {
                    "subtasks": [
                        {"id": "subtask-1", "description": "Phase 1 task"}
                    ]
                },
                {
                    "subtasks": [
                        {"id": "subtask-2", "description": "Phase 2 task"},
                        {"id": "subtask-3", "description": "Another Phase 2 task"}
                    ]
                }
            ]
        }

        spec_path = temp_dir / ".auto-claude" / "specs" / "001"
        spec_path.mkdir(parents=True)
        (spec_path / "implementation_plan.json").write_text(json.dumps(plan_data))

        result = _get_subtask_description(spec_path, "subtask-3")
        assert "Another Phase 2 task" in result

    def test_returns_subtask_id_when_description_missing(self, temp_dir):
        """Test returns subtask ID when description is missing."""
        from analysis.insight_extractor import _get_subtask_description

        plan_data = {
            "phases": [
                {
                    "subtasks": [
                        {"id": "subtask-1"}  # No description
                    ]
                }
            ]
        }

        spec_path = temp_dir / ".auto-claude" / "specs" / "001"
        spec_path.mkdir(parents=True)
        (spec_path / "implementation_plan.json").write_text(json.dumps(plan_data))

        result = _get_subtask_description(spec_path, "subtask-1")
        assert "subtask-1" in result


class TestAttemptHistoryEdgeCases:
    """Additional edge case tests for _get_attempt_history."""

    def test_empty_attempts_list(self):
        """Test handling of empty attempts list."""
        from analysis.insight_extractor import _get_attempt_history

        manager = Mock()
        manager.get_subtask_history = Mock(return_value={"attempts": []})

        result = _get_attempt_history(manager, "subtask-1")
        assert result == []

    def test_missing_attempts_key(self):
        """Test handling when attempts key is missing."""
        from analysis.insight_extractor import _get_attempt_history

        manager = Mock()
        manager.get_subtask_history = Mock(return_value={})

        result = _get_attempt_history(manager, "subtask-1")
        assert result == []

    def test_attempt_missing_optional_fields(self):
        """Test attempts with missing optional fields."""
        from analysis.insight_extractor import _get_attempt_history

        manager = Mock()
        manager.get_subtask_history = Mock(return_value={
            "attempts": [
                {"success": True, "approach": "Test"},  # No error field
                {"success": False}  # No approach or error
            ]
        })

        result = _get_attempt_history(manager, "subtask-1")
        assert len(result) == 2
