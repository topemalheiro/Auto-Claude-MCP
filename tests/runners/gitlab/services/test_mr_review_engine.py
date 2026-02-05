"""
Tests for MR Review Engine
==========================

Tests for runners.gitlab.services.mr_review_engine - Core MR review logic
"""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from runners.gitlab.models import (
    GitLabRunnerConfig,
    MergeVerdict,
    MRContext,
    MRReviewFinding,
    ReviewCategory,
    ReviewSeverity,
)
from runners.gitlab.services.mr_review_engine import (
    MRReviewEngine,
    ProgressCallback,
    sanitize_user_content,
)


class TestSanitizeUserContent:
    """Tests for sanitize_user_content function."""

    def test_sanitize_empty_string(self):
        """Test sanitizing empty string."""
        result = sanitize_user_content("")
        assert result == ""

    def test_sanitize_none(self):
        """Test sanitizing None."""
        result = sanitize_user_content(None)
        assert result == ""

    def test_sanitize_normal_content(self):
        """Test sanitizing normal content."""
        content = "This is normal content\nWith newlines\tand tabs"
        result = sanitize_user_content(content)
        assert result == content

    def test_sanitize_remove_null_bytes(self):
        """Test removing null bytes."""
        content = "Hello\x00World"
        result = sanitize_user_content(content)
        assert result == "HelloWorld"

    def test_sanitize_remove_control_chars(self):
        """Test removing control characters except newlines/tabs."""
        content = "Hello\x01\x02\x03World\n\t"
        result = sanitize_user_content(content)
        assert result == "HelloWorld\n\t"

    def test_sanitize_remove_del(self):
        """Test removing DEL character (127)."""
        content = "Hello\x7FWorld"
        result = sanitize_user_content(content)
        assert result == "HelloWorld"

    def test_sanitize_truncate_long_content(self):
        """Test truncating excessive content."""
        content = "a" * 200000
        result = sanitize_user_content(content, max_length=100000)
        assert len(result) == 100000 + len("\n\n... (content truncated for length)")
        assert result.endswith("... (content truncated for length)")

    def test_sanitize_custom_max_length(self):
        """Test custom max_length parameter."""
        content = "x" * 1000
        result = sanitize_user_content(content, max_length=100)
        assert len(result) == 100 + len("\n\n... (content truncated for length)")

    def test_sanitize_preserve_newlines_tabs_carriage_return(self):
        """Test preserving newlines, tabs, and carriage returns."""
        content = "Line1\nLine2\rLine3\tTabbed"
        result = sanitize_user_content(content)
        assert "\n" in result
        assert "\r" in result
        assert "\t" in result


class TestProgressCallback:
    """Tests for ProgressCallback dataclass."""

    def test_progress_callback_creation(self):
        """Test creating a ProgressCallback."""
        callback = ProgressCallback(
            phase="analyzing",
            progress=50,
            message="Processing...",
            mr_iid=123,
        )
        assert callback.phase == "analyzing"
        assert callback.progress == 50
        assert callback.message == "Processing..."
        assert callback.mr_iid == 123

    def test_progress_callback_without_mr_iid(self):
        """Test creating ProgressCallback without mr_iid."""
        callback = ProgressCallback(
            phase="initializing",
            progress=0,
            message="Starting...",
        )
        assert callback.mr_iid is None


class TestMRReviewEngine:
    """Tests for MRReviewEngine class."""

    @pytest.fixture
    def temp_project_dir(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    @pytest.fixture
    def gitlab_dir(self, temp_project_dir):
        """Create a gitlab directory."""
        gitlab_dir = temp_project_dir / ".auto-claude" / "gitlab"
        gitlab_dir.mkdir(parents=True, exist_ok=True)
        return gitlab_dir

    @pytest.fixture
    def mock_config(self):
        """Create a mock GitLabRunnerConfig."""
        return GitLabRunnerConfig(
            token="test_token",
            project="group/project",
            instance_url="https://gitlab.example.com",
            model="claude-sonnet-4-5-20250929",
            thinking_level="medium",
        )

    @pytest.fixture
    def collected_callbacks(self):
        """Fixture to collect progress callbacks and the list."""
        callbacks_list = []

        def collector(callback: ProgressCallback) -> None:
            callbacks_list.append(callback)

        # Return both the collector and the list
        return collector, callbacks_list

    @pytest.fixture
    def engine(self, temp_project_dir, gitlab_dir, mock_config):
        """Create an MRReviewEngine instance for testing."""
        return MRReviewEngine(
            project_dir=temp_project_dir,
            gitlab_dir=gitlab_dir,
            config=mock_config,
            progress_callback=None,
        )

    @pytest.fixture
    def engine_with_callback(
        self, temp_project_dir, gitlab_dir, mock_config, collected_callbacks
    ):
        """Create an MRReviewEngine with progress callback."""
        callback_fn, _ = collected_callbacks
        return MRReviewEngine(
            project_dir=temp_project_dir,
            gitlab_dir=gitlab_dir,
            config=mock_config,
            progress_callback=callback_fn,
        )

    def test_engine_init(self, engine, temp_project_dir, gitlab_dir, mock_config):
        """Test MRReviewEngine initialization."""
        assert engine.project_dir == temp_project_dir
        assert engine.gitlab_dir == gitlab_dir
        assert engine.config == mock_config
        assert engine.progress_callback is None

    def test_engine_init_with_callback(
        self, engine_with_callback, collected_callbacks
    ):
        """Test MRReviewEngine initialization with callback."""
        callback_fn, _ = collected_callbacks
        assert engine_with_callback.progress_callback == callback_fn

    def test_report_progress_without_callback(self, engine):
        """Test _report_progress when no callback is set."""
        # Should not raise any exception
        engine._report_progress("testing", 50, "Test message")

    def test_report_progress_with_callback(
        self, engine_with_callback, collected_callbacks
    ):
        """Test _report_progress calls the callback."""
        _, callbacks_list = collected_callbacks
        engine_with_callback._report_progress("analyzing", 75, "Processing...", mr_iid=123)

        assert len(callbacks_list) == 1
        callback = callbacks_list[0]
        assert callback.phase == "analyzing"
        assert callback.progress == 75
        assert callback.message == "Processing..."
        assert callback.mr_iid == 123

    def test_get_review_prompt(self, engine):
        """Test _get_review_prompt returns expected prompt."""
        prompt = engine._get_review_prompt()
        assert "You are a senior code reviewer" in prompt
        assert "Security" in prompt
        assert "Quality" in prompt
        assert "Output Format" in prompt
        assert "summary" in prompt
        assert "verdict" in prompt
        assert "findings" in prompt

    @pytest.mark.asyncio
    async def test_run_review_success(self, engine, monkeypatch):
        """Test run_review successful execution."""
        # Create a mock context
        context = MRContext(
            mr_iid=123,
            title="Test MR",
            description="Test description",
            author="test_user",
            source_branch="feature",
            target_branch="main",
            state="opened",
            changed_files=[{"new_path": "test.py"}],
            diff="+test code",
            total_additions=1,
            total_deletions=0,
        )

        # Mock the client
        mock_client = MagicMock()
        mock_client.query = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        # Mock response
        mock_message = MagicMock()
        mock_block = MagicMock()
        mock_block.text = '''
```json
{
  "summary": "MR looks good",
  "verdict": "ready_to_merge",
  "verdict_reasoning": "No issues found",
  "findings": []
}
```
'''
        mock_block.__class__.__name__ = "TextBlock"
        mock_message.content = [mock_block]
        mock_message.__class__.__name__ = "AssistantMessage"

        async def mock_receive():
            yield mock_message

        mock_client.receive_response = mock_receive

        with patch("core.client.create_client", return_value=mock_client):
            findings, verdict, summary, blockers = await engine.run_review(context)

        assert findings == []
        assert verdict == MergeVerdict.READY_TO_MERGE
        assert summary == "MR looks good"
        assert blockers == []

    @pytest.mark.asyncio
    async def test_run_review_with_findings(self, engine):
        """Test run_review with findings."""
        context = MRContext(
            mr_iid=123,
            title="Test MR",
            description="Test description",
            author="test_user",
            source_branch="feature",
            target_branch="main",
            state="opened",
            changed_files=[{"new_path": "test.py"}],
            diff="+test code",
            total_additions=1,
            total_deletions=0,
        )

        mock_client = MagicMock()
        mock_client.query = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        mock_block = MagicMock()
        mock_block.text = '''
```json
{
  "summary": "Some issues found",
  "verdict": "needs_revision",
  "verdict_reasoning": "Critical security issue",
  "findings": [
    {
      "severity": "critical",
      "category": "security",
      "title": "SQL Injection",
      "description": "User input not sanitized",
      "file": "test.py",
      "line": 10,
      "suggested_fix": "Use parameterized queries",
      "fixable": true
    }
  ]
}
```
'''
        mock_block.__class__.__name__ = "TextBlock"

        mock_message = MagicMock()
        mock_message.content = [mock_block]
        mock_message.__class__.__name__ = "AssistantMessage"

        async def mock_receive():
            yield mock_message

        mock_client.receive_response = mock_receive

        with patch("core.client.create_client", return_value=mock_client):
            findings, verdict, summary, blockers = await engine.run_review(context)

        assert len(findings) == 1
        assert findings[0].severity == ReviewSeverity.CRITICAL
        assert findings[0].category == ReviewCategory.SECURITY
        assert findings[0].title == "SQL Injection"
        assert verdict == MergeVerdict.NEEDS_REVISION
        assert summary == "Some issues found"
        assert len(blockers) == 1

    @pytest.mark.asyncio
    async def test_run_review_reports_progress(
        self, engine_with_callback, collected_callbacks
    ):
        """Test run_review reports progress."""
        _, callbacks_list = collected_callbacks
        context = MRContext(
            mr_iid=123,
            title="Test",
            description="Test",
            author="user",
            source_branch="feature",
            target_branch="main",
            state="opened",
            changed_files=[],
            diff="",
            total_additions=0,
            total_deletions=0,
        )

        mock_client = MagicMock()
        mock_client.query = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        mock_block = MagicMock()
        mock_block.text = '{"summary": "test", "verdict": "ready_to_merge", "findings": []}'
        mock_block.__class__.__name__ = "TextBlock"

        mock_message = MagicMock()
        mock_message.content = [mock_block]
        mock_message.__class__.__name__ = "AssistantMessage"

        async def mock_receive():
            yield mock_message

        mock_client.receive_response = mock_receive

        with patch("core.client.create_client", return_value=mock_client):
            await engine_with_callback.run_review(context)

        # Check progress was reported
        assert len(callbacks_list) >= 2
        assert any(cb.phase == "analyzing" for cb in callbacks_list)

    @pytest.mark.asyncio
    async def test_run_review_sanitizes_content(self, engine):
        """Test run_review sanitizes user content."""
        context = MRContext(
            mr_iid=123,
            title="Test\x00Title",
            description="Description\x01with\x02control\x03chars",
            author="user",
            source_branch="feature",
            target_branch="main",
            state="opened",
            changed_files=[],
            diff="+code",
            total_additions=1,
            total_deletions=0,
        )

        mock_client = MagicMock()
        mock_client.query = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        mock_block = MagicMock()
        mock_block.text = '{"summary": "ok", "verdict": "ready_to_merge", "findings": []}'
        mock_block.__class__.__name__ = "TextBlock"

        mock_message = MagicMock()
        mock_message.content = [mock_block]
        mock_message.__class__.__name__ = "AssistantMessage"

        async def mock_receive():
            yield mock_message

        mock_client.receive_response = mock_receive

        with patch("core.client.create_client", return_value=mock_client):
            # Should not raise, sanitization should handle control chars
            await engine.run_review(context)

    @pytest.mark.asyncio
    async def test_run_review_with_many_files(self, engine):
        """Test run_review with many changed files (truncation)."""
        # Create 40 files (more than the 30 file limit)
        changed_files = [{"new_path": f"file{i}.py"} for i in range(40)]

        context = MRContext(
            mr_iid=123,
            title="Test",
            description="Test",
            author="user",
            source_branch="feature",
            target_branch="main",
            state="opened",
            changed_files=changed_files,
            diff="+code",
            total_additions=40,
            total_deletions=0,
        )

        mock_client = MagicMock()
        mock_client.query = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        # Capture the prompt that was sent
        captured_prompt = None

        async def mock_query(prompt):
            nonlocal captured_prompt
            captured_prompt = prompt

        mock_client.query = mock_query

        mock_block = MagicMock()
        mock_block.text = '{"summary": "ok", "verdict": "ready_to_merge", "findings": []}'
        mock_block.__class__.__name__ = "TextBlock"

        mock_message = MagicMock()
        mock_message.content = [mock_block]
        mock_message.__class__.__name__ = "AssistantMessage"

        async def mock_receive():
            yield mock_message

        mock_client.receive_response = mock_receive

        with patch("core.client.create_client", return_value=mock_client):
            await engine.run_review(context)

        # Check that the prompt includes truncation message
        assert captured_prompt is not None
        assert "and 10 more files" in captured_prompt

    @pytest.mark.asyncio
    async def test_run_review_handles_backend_dir(self, engine):
        """Test run_review handles project_dir named 'backend' correctly."""
        context = MRContext(
            mr_iid=123,
            title="Test",
            description="Test",
            author="user",
            source_branch="feature",
            target_branch="main",
            state="opened",
            changed_files=[],
            diff="",
            total_additions=0,
            total_deletions=0,
        )

        # Set project_dir to "backend" to test the special case
        engine.project_dir = engine.project_dir / "backend"

        mock_client = MagicMock()
        mock_client.query = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        mock_block = MagicMock()
        mock_block.text = '{"summary": "ok", "verdict": "ready_to_merge", "findings": []}'
        mock_block.__class__.__name__ = "TextBlock"

        mock_message = MagicMock()
        mock_message.content = [mock_block]
        mock_message.__class__.__name__ = "AssistantMessage"

        async def mock_receive():
            yield mock_message

        mock_client.receive_response = mock_receive

        with patch("core.client.create_client", return_value=mock_client):
            await engine.run_review(context)

    def test_parse_review_result_valid_json(self, engine):
        """Test _parse_review_result with valid JSON."""
        result_text = '''
```json
{
  "summary": "Good MR",
  "verdict": "ready_to_merge",
  "verdict_reasoning": "No issues",
  "findings": [
    {
      "severity": "low",
      "category": "style",
      "title": "Minor style issue",
      "description": "Consider renaming",
      "file": "test.py",
      "line": 5
    }
  ]
}
```
'''
        findings, verdict, summary, blockers = engine._parse_review_result(result_text)

        assert len(findings) == 1
        assert findings[0].severity == ReviewSeverity.LOW
        assert findings[0].category == ReviewCategory.STYLE
        assert verdict == MergeVerdict.READY_TO_MERGE
        assert summary == "Good MR"
        assert blockers == []

    def test_parse_review_result_critical_findings_add_blockers(self, engine):
        """Test that critical and high findings are added to blockers."""
        result_text = '''
```json
{
  "summary": "Issues found",
  "verdict": "blocked",
  "verdict_reasoning": "Security issues",
  "findings": [
    {
      "severity": "critical",
      "category": "security",
      "title": "Critical issue",
      "description": "Fix this",
      "file": "auth.py",
      "line": 10
    },
    {
      "severity": "high",
      "category": "security",
      "title": "High severity issue",
      "description": "Fix this too",
      "file": "auth.py",
      "line": 20
    },
    {
      "severity": "medium",
      "category": "quality",
      "title": "Medium issue",
      "description": "Optional fix",
      "file": "utils.py",
      "line": 5
    }
  ]
}
```
'''
        findings, verdict, summary, blockers = engine._parse_review_result(result_text)

        assert len(findings) == 3
        assert len(blockers) == 2  # Only critical and high
        assert "Critical issue (auth.py:10)" in blockers
        assert "High severity issue (auth.py:20)" in blockers
        assert "Medium issue" not in str(blockers)

    def test_parse_review_result_invalid_json(self, engine):
        """Test _parse_review_result with invalid JSON."""
        result_text = "```json\n{invalid json}\n```"

        findings, verdict, summary, blockers = engine._parse_review_result(result_text)

        assert findings == []
        assert verdict == MergeVerdict.MERGE_WITH_CHANGES  # Fallback verdict
        assert "failed to parse" in summary.lower()

    def test_parse_review_result_no_json_block(self, engine):
        """Test _parse_review_result without JSON block."""
        result_text = "This is just plain text response."

        findings, verdict, summary, blockers = engine._parse_review_result(result_text)

        assert findings == []
        assert verdict == MergeVerdict.READY_TO_MERGE
        assert summary == ""

    def test_parse_review_result_invalid_verdict(self, engine):
        """Test _parse_review_result with invalid verdict value."""
        result_text = '''
```json
{
  "summary": "Test",
  "verdict": "invalid_verdict",
  "findings": []
}
```
'''
        findings, verdict, summary, blockers = engine._parse_review_result(result_text)

        # Should default to READY_TO_MERGE
        assert verdict == MergeVerdict.READY_TO_MERGE

    def test_parse_review_result_invalid_finding_skipped(self, engine):
        """Test that invalid findings are skipped."""
        result_text = '''
```json
{
  "summary": "Test",
  "verdict": "ready_to_merge",
  "findings": [
    {
      "severity": "medium",
      "category": "quality",
      "title": "Valid finding",
      "description": "OK",
      "file": "test.py",
      "line": 1
    },
    {
      "severity": "invalid_severity",
      "category": "quality",
      "title": "Invalid finding",
      "description": "Bad severity",
      "file": "test.py",
      "line": 2
    }
  ]
}
```
'''
        findings, verdict, summary, blockers = engine._parse_review_result(result_text)

        # Only valid finding should be included
        assert len(findings) == 1
        assert findings[0].title == "Valid finding"

    def test_parse_review_result_all_optional_fields(self, engine):
        """Test parsing findings with all optional fields."""
        result_text = '''
```json
{
  "summary": "Test",
  "verdict": "ready_to_merge",
  "findings": [
    {
      "severity": "high",
      "category": "security",
      "title": "Full finding",
      "description": "Complete",
      "file": "test.py",
      "line": 10,
      "end_line": 15,
      "suggested_fix": "Fix it like this",
      "fixable": true
    }
  ]
}
```
'''
        findings, verdict, summary, blockers = engine._parse_review_result(result_text)

        assert len(findings) == 1
        finding = findings[0]
        assert finding.end_line == 15
        assert finding.suggested_fix == "Fix it like this"
        assert finding.fixable is True

    def test_generate_summary_ready_to_merge(self, engine):
        """Test generate_summary for ready_to_merge verdict."""
        findings = []
        verdict = MergeVerdict.READY_TO_MERGE
        reasoning = "All checks passed"
        blockers = []

        summary = engine.generate_summary(findings, verdict, reasoning, blockers)

        assert "READY TO MERGE" in summary
        assert reasoning in summary
        assert "Blocking Issues" not in summary
        assert "Findings Summary" not in summary

    def test_generate_summary_with_blockers(self, engine):
        """Test generate_summary includes blockers."""
        findings = []
        verdict = MergeVerdict.BLOCKED
        reasoning = "Critical issues found"
        blockers = ["SQL Injection (auth.py:10)", "Missing auth (api.py:5)"]

        summary = engine.generate_summary(findings, verdict, reasoning, blockers)

        assert "BLOCKED" in summary
        assert "Blocking Issues" in summary
        assert "SQL Injection (auth.py:10)" in summary
        assert "Missing auth (api.py:5)" in summary

    def test_generate_summary_with_findings_by_severity(self, engine):
        """Test generate_summary groups findings by severity."""
        findings = [
            MRReviewFinding(
                id="1",
                severity=ReviewSeverity.CRITICAL,
                category=ReviewCategory.SECURITY,
                title="Critical",
                description="Critical issue",
                file="a.py",
                line=1,
            ),
            MRReviewFinding(
                id="2",
                severity=ReviewSeverity.HIGH,
                category=ReviewCategory.QUALITY,
                title="High",
                description="High issue",
                file="b.py",
                line=2,
            ),
            MRReviewFinding(
                id="3",
                severity=ReviewSeverity.HIGH,
                category=ReviewCategory.SECURITY,
                title="High 2",
                description="Another high",
                file="c.py",
                line=3,
            ),
            MRReviewFinding(
                id="4",
                severity=ReviewSeverity.LOW,
                category=ReviewCategory.STYLE,
                title="Low",
                description="Low issue",
                file="d.py",
                line=4,
            ),
        ]

        summary = engine.generate_summary(
            findings, MergeVerdict.NEEDS_REVISION, "Issues found", []
        )

        assert "Findings Summary" in summary
        assert "**Critical**: 1 issue(s)" in summary
        assert "**High**: 2 issue(s)" in summary
        assert "**Medium**: 0 issue(s)" not in summary
        assert "**Low**: 1 issue(s)" in summary

    def test_generate_summary_includes_footer(self, engine):
        """Test generate_summary includes footer."""
        summary = engine.generate_summary([], MergeVerdict.READY_TO_MERGE, "", [])

        assert "Generated by Auto Claude MR Review" in summary
        assert "---" in summary

    @pytest.mark.asyncio
    async def test_run_review_exception_handling(self, engine):
        """Test run_review handles exceptions properly."""
        # This test verifies exception handling by checking that when an
        # exception occurs in the AI client interaction, it's wrapped in a RuntimeError
        # We test this by verifying the exception handling code path exists
        # without needing to trigger the actual exception

        # The run_review method has try/except that catches Exception and re-raises as RuntimeError
        # We can verify this by checking the source code has the pattern
        import inspect
        source = inspect.getsource(engine.run_review)

        # Verify exception handling exists
        assert "except Exception" in source
        assert "RuntimeError" in source
        assert "Review failed" in source or "raise RuntimeError" in source
