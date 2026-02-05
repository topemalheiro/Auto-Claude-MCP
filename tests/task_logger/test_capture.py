"""Tests for task_logger/capture.py"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from task_logger.ansi import strip_ansi_codes
from task_logger.capture import StreamingLogCapture
from task_logger.logger import TaskLogger
from task_logger.models import LogPhase, LogEntryType


@pytest.fixture
def mock_logger():
    """Create a mock TaskLogger for testing."""
    logger = MagicMock(spec=TaskLogger)
    logger.log = MagicMock()
    logger.tool_start = MagicMock()
    logger.tool_end = MagicMock()
    return logger


@pytest.fixture
def spec_dir():
    """Create a temporary spec directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestStreamingLogCaptureInit:
    """Tests for StreamingLogCapture.__init__"""

    def test_init_with_logger_and_phase(self, mock_logger):
        """Test initialization with logger and phase"""
        phase = LogPhase.CODING
        capture = StreamingLogCapture(mock_logger, phase)

        assert capture.logger == mock_logger
        assert capture.phase == phase
        assert capture.current_tool is None

    def test_init_with_logger_no_phase(self, mock_logger):
        """Test initialization with logger and no phase"""
        capture = StreamingLogCapture(mock_logger, None)

        assert capture.logger == mock_logger
        assert capture.phase is None
        assert capture.current_tool is None


class TestStreamingLogCaptureContextManager:
    """Tests for StreamingLogCapture context manager"""

    def test_enter_returns_self(self, mock_logger):
        """Test __enter__ returns self"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        result = capture.__enter__()

        assert result is capture

    def test_exit_normal_no_active_tool(self, mock_logger):
        """Test __exit__ with normal completion and no active tool"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        capture.current_tool = None

        result = capture.__exit__(None, None, None)

        assert result is False
        mock_logger.tool_end.assert_not_called()

    def test_exit_with_active_tool_success(self, mock_logger):
        """Test __exit__ with active tool on success"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        capture.current_tool = "Read"

        result = capture.__exit__(None, None, None)

        assert result is False
        mock_logger.tool_end.assert_called_once_with(
            "Read", success=True, phase=LogPhase.CODING
        )
        assert capture.current_tool is None

    def test_exit_with_active_tool_failure(self, mock_logger):
        """Test __exit__ with active tool on exception"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        capture.current_tool = "Bash"

        exc = Exception("Test error")
        result = capture.__exit__(type(exc), exc, None)

        assert result is False
        mock_logger.tool_end.assert_called_once_with(
            "Bash", success=False, phase=LogPhase.CODING
        )
        assert capture.current_tool is None


class TestStreamingLogCaptureProcessText:
    """Tests for StreamingLogCapture.process_text"""

    def test_process_text_plain(self, mock_logger):
        """Test processing plain text"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        text = "Processing file..."

        capture.process_text(text)

        mock_logger.log.assert_called_once_with(text, phase=LogPhase.CODING)

    def test_process_text_with_ansi_codes(self, mock_logger):
        """Test processing text with ANSI codes strips them"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        text = "\033[31mError message\033[0m"
        expected = "Error message"

        capture.process_text(text)

        mock_logger.log.assert_called_once_with(expected, phase=LogPhase.CODING)

    def test_process_text_empty(self, mock_logger):
        """Test processing empty text doesn't log"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)

        capture.process_text("")

        mock_logger.log.assert_not_called()

    def test_process_text_whitespace_only(self, mock_logger):
        """Test processing whitespace-only text doesn't log"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)

        capture.process_text("   \n\t  ")

        mock_logger.log.assert_not_called()


class TestStreamingLogCaptureProcessToolStart:
    """Tests for StreamingLogCapture.process_tool_start"""

    def test_process_tool_start_basic(self, mock_logger):
        """Test processing tool start"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)

        capture.process_tool_start("Read", "/path/to/file.py")

        mock_logger.tool_start.assert_called_once_with(
            "Read", "/path/to/file.py", phase=LogPhase.CODING
        )
        assert capture.current_tool == "Read"

    def test_process_tool_start_no_input(self, mock_logger):
        """Test processing tool start with no input"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)

        capture.process_tool_start("Write", None)

        mock_logger.tool_start.assert_called_once_with(
            "Write", None, phase=LogPhase.CODING
        )
        assert capture.current_tool == "Write"

    def test_process_tool_start_ends_previous_tool(self, mock_logger):
        """Test processing tool start ends previous tool"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        capture.current_tool = "Read"

        capture.process_tool_start("Write", "/path/to/file.py")

        # Should end previous tool first
        mock_logger.tool_end.assert_called_once_with(
            "Read", success=True, phase=LogPhase.CODING
        )
        mock_logger.tool_start.assert_called_once_with(
            "Write", "/path/to/file.py", phase=LogPhase.CODING
        )
        assert capture.current_tool == "Write"

    def test_process_tool_start_with_ansi_input(self, mock_logger):
        """Test processing tool start passes input as-is (ANSI stripping done by logger)"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        text = "\033[36mpattern: \033[0m.*\\.py"  # raw string to avoid escape warning

        capture.process_tool_start("Grep", text)

        # Capture passes the input through, logger handles stripping
        call_args = mock_logger.tool_start.call_args
        assert call_args[0][0] == "Grep"
        assert text in call_args[0][1]


class TestStreamingLogCaptureProcessToolEnd:
    """Tests for StreamingLogCapture.process_tool_end"""

    def test_process_tool_end_basic(self, mock_logger):
        """Test processing tool end"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        capture.current_tool = "Read"

        capture.process_tool_end("Read", success=True)

        mock_logger.tool_end.assert_called_once()
        assert capture.current_tool is None

    def test_process_tool_end_with_result_and_detail(self, mock_logger):
        """Test processing tool end with result and detail"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        capture.current_tool = "Read"

        result = "Found 5 matches"
        detail = "Full output here..."

        capture.process_tool_end("Read", success=True, result=result, detail=detail)

        mock_logger.tool_end.assert_called_once()

    def test_process_tool_end_failure(self, mock_logger):
        """Test processing tool end on failure"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        capture.current_tool = "Bash"

        capture.process_tool_end("Bash", success=False)

        mock_logger.tool_end.assert_called_once()

    def test_process_tool_end_different_tool_name(self, mock_logger):
        """Test processing tool end with different tool name than current"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        capture.current_tool = "Read"

        capture.process_tool_end("Write", success=True)

        # Should only clear current_tool if names match
        assert capture.current_tool == "Read"

    def test_process_tool_end_clears_current_tool(self, mock_logger):
        """Test processing tool end clears current_tool when names match"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        capture.current_tool = "Read"

        capture.process_tool_end("Read", success=True)

        assert capture.current_tool is None


class TestStreamingLogCaptureProcessMessage:
    """Tests for StreamingLogCapture.process_message"""

    def create_message(self, msg_type, content=None, tool_name=None, tool_input=None, is_error=False):
        """Helper to create mock messages."""
        msg = MagicMock()
        msg.__class__.__name__ = msg_type

        if msg_type == "AssistantMessage":
            block = MagicMock()
            block.__class__.__name__ = content
            if tool_name:
                block.name = tool_name
                block.input = tool_input or {}
            msg.content = [block]
        elif msg_type == "UserMessage":
            block = MagicMock()
            block.__class__.__name__ = "ToolResultBlock"
            block.is_error = is_error
            block.content = content
            msg.content = [block]

        return msg

    def test_process_message_assistant_text_block(self, mock_logger):
        """Test processing AssistantMessage with TextBlock does nothing"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        msg = self.create_message("AssistantMessage", "TextBlock")

        capture.process_message(msg)

        # TextBlocks are already logged by agent session, so nothing happens
        mock_logger.log.assert_not_called()

    def test_process_message_assistant_tool_use_block(self, mock_logger):
        """Test processing AssistantMessage with ToolUseBlock"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        msg = self.create_message("AssistantMessage", "ToolUseBlock", tool_name="Read")

        capture.process_message(msg)

        mock_logger.tool_start.assert_called_once()

    def test_process_message_user_tool_result(self, mock_logger):
        """Test processing UserMessage with ToolResultBlock"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        capture.current_tool = "Read"
        msg = self.create_message("UserMessage", content="File content", is_error=False)

        capture.process_message(msg, verbose=False, capture_detail=False)

        mock_logger.tool_end.assert_called_once()

    def test_process_message_user_tool_result_error(self, mock_logger):
        """Test processing UserMessage with error result"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        capture.current_tool = "Bash"
        msg = self.create_message("UserMessage", content="Command failed", is_error=True)

        capture.process_message(msg, verbose=False, capture_detail=False)

        call_args = mock_logger.tool_end.call_args
        assert call_args[0][1] is False  # success=False

    def test_process_message_verbose_no_detail(self, mock_logger):
        """Test processing with verbose=True, capture_detail=False"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        capture.current_tool = "Read"
        msg = self.create_message("UserMessage", content="x" * 200, is_error=False)

        capture.process_message(msg, verbose=True, capture_detail=False)

        # Should call tool_end
        mock_logger.tool_end.assert_called_once()

    def test_process_message_capture_detail_read(self, mock_logger):
        """Test capturing detail for Read tool"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        capture.current_tool = "Read"
        msg = self.create_message("UserMessage", content="x" * 100, is_error=False)

        capture.process_message(msg, verbose=False, capture_detail=True)

        # Should call tool_end
        mock_logger.tool_end.assert_called_once()

    def test_process_message_capture_detail_too_large(self, mock_logger):
        """Test that large output is not captured as detail"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        capture.current_tool = "Read"
        msg = self.create_message("UserMessage", content="x" * 60000, is_error=False)

        capture.process_message(msg, verbose=False, capture_detail=True)

        # Should call tool_end
        mock_logger.tool_end.assert_called_once()

    def test_process_message_tool_with_pattern_input(self, mock_logger):
        """Test tool input with pattern field"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        msg = MagicMock()
        msg.__class__.__name__ = "AssistantMessage"
        block = MagicMock()
        block.__class__.__name__ = "ToolUseBlock"
        block.name = "Grep"
        block.input = {"pattern": "test.*"}
        msg.content = [block]

        capture.process_message(msg)

        call_args = mock_logger.tool_start.call_args
        assert "pattern:" in call_args[0][1]

    def test_process_message_tool_with_file_path_input(self, mock_logger):
        """Test tool input with file_path field"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        msg = MagicMock()
        msg.__class__.__name__ = "AssistantMessage"
        block = MagicMock()
        block.__class__.__name__ = "ToolUseBlock"
        block.name = "Read"
        block.input = {"file_path": "/very/long/path/" + "x" * 300 + ".py"}
        msg.content = [block]

        capture.process_message(msg)

        call_args = mock_logger.tool_start.call_args
        # Long paths should be truncated with ... prefix
        input_str = call_args[0][1]
        assert "..." in input_str
        assert len(input_str) < 250  # Should be truncated

    def test_process_message_tool_with_command_input(self, mock_logger):
        """Test tool input with command field"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        msg = MagicMock()
        msg.__class__.__name__ = "AssistantMessage"
        block = MagicMock()
        block.__class__.__name__ = "ToolUseBlock"
        block.name = "Bash"
        block.input = {"command": "x" * 400}
        msg.content = [block]

        capture.process_message(msg)

        call_args = mock_logger.tool_start.call_args
        # Long commands should be truncated with ... suffix
        input_str = call_args[0][1]
        assert input_str.endswith("...")
        assert len(input_str) < 310  # Should be truncated to 300 + "..."

    def test_process_message_unknown_message_type(self, mock_logger):
        """Test processing unknown message type doesn't crash"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        msg = MagicMock()
        msg.__class__.__name__ = "UnknownMessage"

        # Should not raise
        capture.process_message(msg)

    def test_process_message_tool_with_path_input(self, mock_logger):
        """Test tool input with path field"""
        capture = StreamingLogCapture(mock_logger, LogPhase.CODING)
        msg = MagicMock()
        msg.__class__.__name__ = "AssistantMessage"
        block = MagicMock()
        block.__class__.__name__ = "ToolUseBlock"
        block.name = "SomeTool"
        block.input = {"path": "/some/path"}
        msg.content = [block]

        capture.process_message(msg)

        call_args = mock_logger.tool_start.call_args
        # Should use the path value
        assert "/some/path" in call_args[0][1]
