"""
Comprehensive tests for commit_message module.

Tests for commit message generation using Claude AI, including:
- Sync and async variants
- Spec context extraction
- Category to commit type mapping
- Prompt building
- Fallback message generation
"""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from datetime import datetime

import pytest


# =============================================================================
# Helper fixtures
# =============================================================================


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory with spec structure."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create spec directory
    spec_dir = project_dir / ".auto-claude" / "specs" / "001-test-feature"
    spec_dir.mkdir(parents=True)

    return project_dir, spec_dir


@pytest.fixture
def spec_dir_with_files(temp_project_dir):
    """Create spec directory with test files."""
    project_dir, spec_dir = temp_project_dir

    # Create spec.md
    spec_md = spec_dir / "spec.md"
    spec_md.write_text("# Test Feature\n\n## Overview\nThis is a test feature for commit message generation.")

    # Create requirements.json
    requirements = {
        "feature": "Test Feature",
        "workflow_type": "feature",
        "task_description": "Add test feature for commit messages"
    }
    req_file = spec_dir / "requirements.json"
    req_file.write_text(json.dumps(requirements))

    # Create implementation_plan.json
    plan = {
        "feature": "Test Feature",
        "title": "Test Feature",
        "metadata": {
            "githubIssueNumber": 42
        },
        "phases": []
    }
    plan_file = spec_dir / "implementation_plan.json"
    plan_file.write_text(json.dumps(plan))

    return project_dir, spec_dir


# =============================================================================
# Test _get_spec_context function
# =============================================================================


class TestGetSpecContext:
    """Tests for _get_spec_context function."""

    def test_get_spec_context_from_spec_md(self, spec_dir_with_files):
        """Test extracting context from spec.md file."""
        project_dir, spec_dir = spec_dir_with_files

        from commit_message import _get_spec_context

        result = _get_spec_context(spec_dir)

        assert result["title"] == "Test Feature"
        assert "test feature for commit message generation" in result["description"].lower()

    def test_get_spec_context_from_requirements_json(self, spec_dir_with_files):
        """Test extracting context from requirements.json."""
        project_dir, spec_dir = spec_dir_with_files

        from commit_message import _get_spec_context

        result = _get_spec_context(spec_dir)

        assert result["title"] == "Test Feature"
        assert result["category"] == "feature"

    def test_get_spec_context_from_implementation_plan(self, spec_dir_with_files):
        """Test extracting GitHub issue from implementation_plan.json."""
        project_dir, spec_dir = spec_dir_with_files

        from commit_message import _get_spec_context

        result = _get_spec_context(spec_dir)

        assert result["github_issue"] == 42

    def test_get_spec_context_all_sources(self, spec_dir_with_files):
        """Test combining context from all sources."""
        project_dir, spec_dir = spec_dir_with_files

        from commit_message import _get_spec_context

        result = _get_spec_context(spec_dir)

        assert result["title"] == "Test Feature"
        assert result["category"] == "feature"
        assert result["github_issue"] == 42
        assert len(result["description"]) > 0

    def test_get_spec_context_no_files(self, temp_project_dir):
        """Test context extraction when no files exist."""
        project_dir, spec_dir = temp_project_dir

        from commit_message import _get_spec_context

        result = _get_spec_context(spec_dir)

        assert result["title"] == ""
        assert result["category"] == "chore"
        assert result["description"] == ""
        assert result["github_issue"] is None

    def test_get_spec_context_spec_md_only(self, temp_project_dir):
        """Test context extraction with only spec.md."""
        project_dir, spec_dir = temp_project_dir

        spec_md = spec_dir / "spec.md"
        spec_md.write_text("# Only Spec\n\nNo other files.")

        from commit_message import _get_spec_context

        result = _get_spec_context(spec_dir)

        assert result["title"] == "Only Spec"
        assert result["category"] == "chore"  # Default

    def test_get_spec_context_requirements_only(self, temp_project_dir):
        """Test context extraction with only requirements.json."""
        project_dir, spec_dir = temp_project_dir

        requirements = {
            "feature": "Req Only",
            "workflow_type": "bug_fix"
        }
        req_file = spec_dir / "requirements.json"
        req_file.write_text(json.dumps(requirements))

        from commit_message import _get_spec_context

        result = _get_spec_context(spec_dir)

        assert result["title"] == "Req Only"
        assert result["category"] == "bug_fix"

    def test_get_spec_context_invalid_json(self, temp_project_dir):
        """Test handling invalid JSON in requirements files."""
        project_dir, spec_dir = temp_project_dir

        req_file = spec_dir / "requirements.json"
        req_file.write_text("{ invalid json }")

        from commit_message import _get_spec_context

        result = _get_spec_context(spec_dir)

        # Should not crash, just skip invalid data
        assert result["category"] == "chore"  # Default

    def test_get_spec_context_overview_extraction(self, temp_project_dir):
        """Test extracting overview section from spec.md."""
        project_dir, spec_dir = temp_project_dir

        spec_md = spec_dir / "spec.md"
        spec_md.write_text("""
# Feature

## Overview
This is the detailed description of the feature.
It can span multiple lines.

## Other Section
Other content.
""")

        from commit_message import _get_spec_context

        result = _get_spec_context(spec_dir)

        assert "detailed description" in result["description"]


# =============================================================================
# Test _build_prompt function
# =============================================================================


class TestBuildPrompt:
    """Tests for _build_prompt function."""

    def test_build_prompt_basic(self):
        """Test basic prompt building."""
        from commit_message import _build_prompt

        spec_context = {
            "title": "Test Feature",
            "category": "feature",
            "description": "A test feature",
            "github_issue": None
        }
        diff_summary = "Fixed bug in parser"
        files_changed = ["parser.py", "tests/test_parser.py"]

        result = _build_prompt(spec_context, diff_summary, files_changed)

        assert "Test Feature" in result
        assert "feat" in result  # Commit type for feature
        assert "2" in result  # Number of files
        assert "parser.py" in result
        assert "Fixed bug in parser" in result

    def test_build_prompt_with_github_issue(self):
        """Test prompt building with GitHub issue."""
        from commit_message import _build_prompt

        spec_context = {
            "title": "Bug Fix",
            "category": "bug_fix",
            "description": "Fix critical bug",
            "github_issue": 123
        }
        diff_summary = "Fixed the bug"
        files_changed = ["fix.py"]

        result = _build_prompt(spec_context, diff_summary, files_changed)

        assert "#123" in result
        assert "Fixes #123" in result

    def test_build_prompt_many_files_truncates(self):
        """Test prompt truncation for many files."""
        from commit_message import _build_prompt

        spec_context = {
            "title": "Big Change",
            "category": "refactor",
            "description": "Many files changed",
            "github_issue": None
        }

        # Create 25 files (more than 20 threshold)
        files_changed = [f"file{i}.py" for i in range(25)]
        diff_summary = "Large refactor"

        result = _build_prompt(spec_context, diff_summary, files_changed)

        assert "25" in result  # Total count
        assert "file0.py" in result
        assert "file19.py" in result  # 20th file (0-indexed)
        assert "and 5 more files" in result

    def test_build_prompt_no_files(self):
        """Test prompt building with no files changed."""
        from commit_message import _build_prompt

        spec_context = {
            "title": "No Changes",
            "category": "chore",
            "description": "No files changed",
            "github_issue": None
        }
        diff_summary = ""
        files_changed = []

        result = _build_prompt(spec_context, diff_summary, files_changed)

        assert "(no files listed)" in result

    def test_build_prompt_long_diff_truncates(self):
        """Test diff summary truncation."""
        from commit_message import _build_prompt

        spec_context = {
            "title": "Test",
            "category": "test",
            "description": "Test",
            "github_issue": None
        }

        # Create a very long diff (over 2000 chars)
        long_diff = "a" * 3000
        files_changed = ["test.py"]

        result = _build_prompt(spec_context, long_diff, files_changed)

        # Should truncate to 2000 chars
        assert len(result) < len(long_diff) + 1000  # Account for other text

    def test_build_prompt_category_mapping(self):
        """Test category to commit type mapping."""
        from commit_message import _build_prompt, CATEGORY_TO_COMMIT_TYPE

        test_cases = [
            ("feature", "feat"),
            ("bug_fix", "fix"),
            ("bug", "fix"),
            ("refactoring", "refactor"),
            ("documentation", "docs"),
            ("testing", "test"),
            ("performance", "perf"),
            ("security", "security"),
            ("chore", "chore"),
        ]

        for category, expected_type in test_cases:
            spec_context = {
                "title": "Test",
                "category": category,
                "description": "Test",
                "github_issue": None
            }

            result = _build_prompt(spec_context, "", [])

            assert f"Type: {expected_type}" in result


# =============================================================================
# Test generate_commit_message_sync function
# =============================================================================


class TestGenerateCommitMessageSync:
    """Tests for generate_commit_message_sync function."""

    def test_generate_commit_message_sync_fallback_no_auth(self, spec_dir_with_files):
        """Test fallback message when no auth token."""
        project_dir, spec_dir = spec_dir_with_files

        from commit_message import generate_commit_message_sync

        with patch("core.auth.get_auth_token", return_value=None):
            result = generate_commit_message_sync(
                project_dir,
                "001-test-feature",
                diff_summary="Test changes",
                files_changed=["test.py"]
            )

        # Should return fallback message
        assert result is not None
        assert "feat" in result.lower() or "test feature" in result.lower()

    def test_generate_commit_message_sync_with_github_override(self, spec_dir_with_files):
        """Test GitHub issue number override."""
        project_dir, spec_dir = spec_dir_with_files

        from commit_message import generate_commit_message_sync

        with patch("core.auth.get_auth_token", return_value=None):
            result = generate_commit_message_sync(
                project_dir,
                "001-test-feature",
                github_issue=999  # Override the 42 from spec files
            )

        assert "#999" in result or "Fixes #999" in result

    def test_generate_commit_message_sync_fallback_format(self, spec_dir_with_files):
        """Test fallback message format."""
        project_dir, spec_dir = spec_dir_with_files

        from commit_message import generate_commit_message_sync

        with patch("core.auth.get_auth_token", return_value=None):
            result = generate_commit_message_sync(
                project_dir,
                "001-test-feature"
            )

        # Should have commit type and title
        lines = result.strip().split("\n")
        assert len(lines) >= 1

        # First line should be commit type: title
        first_line = lines[0]
        assert ":" in first_line

    def test_generate_commit_message_sync_spec_dir_not_found(self, temp_project_dir):
        """Test when spec directory doesn't exist."""
        project_dir, _ = temp_project_dir

        from commit_message import generate_commit_message_sync

        with patch("core.auth.get_auth_token", return_value=None):
            result = generate_commit_message_sync(
                project_dir,
                "999-nonexistent"
            )

        # Should still return a fallback message
        assert result is not None
        assert "999-nonexistent" in result or "chore" in result.lower()

    def test_generate_commit_message_sync_alternative_spec_location(self, tmp_path):
        """Test alternative spec directory location."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Create spec in alternative location (auto-claude instead of .auto-claude)
        spec_dir = project_dir / "auto-claude" / "specs" / "001-alt"
        spec_dir.mkdir(parents=True)
        spec_md = spec_dir / "spec.md"
        spec_md.write_text("# Alt Spec")

        from commit_message import generate_commit_message_sync

        with patch("core.auth.get_auth_token", return_value=None):
            result = generate_commit_message_sync(
                project_dir,
                "001-alt"
            )

        assert result is not None

    @pytest.mark.asyncio
    async def test_generate_commit_message_sync_runs_async_in_thread(self, spec_dir_with_files):
        """Test that sync version runs async code in thread."""
        project_dir, spec_dir = spec_dir_with_files

        from commit_message import generate_commit_message_sync

        # Mock the async function
        with patch("commit_message._call_claude", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "feat: AI generated message\n\nAI description here"

            # Create a running loop scenario
            loop = asyncio.get_running_loop()

            result = generate_commit_message_sync(
                project_dir,
                "001-test-feature"
            )

            # Should get the AI-generated result
            assert result == "feat: AI generated message\n\nAI description here"


# =============================================================================
# Test generate_commit_message function (async)
# =============================================================================


class TestGenerateCommitMessageAsync:
    """Tests for generate_commit_message async function."""

    @pytest.mark.asyncio
    async def test_generate_commit_message_success(self, spec_dir_with_files):
        """Test successful commit message generation."""
        project_dir, spec_dir = spec_dir_with_files

        from commit_message import generate_commit_message

        with patch("commit_message._call_claude", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "feat: AI message\n\nGenerated by AI"

            result = await generate_commit_message(
                project_dir,
                "001-test-feature"
            )

            assert result == "feat: AI message\n\nGenerated by AI"
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_commit_message_fallback_on_error(self, spec_dir_with_files):
        """Test fallback when AI generation fails."""
        project_dir, spec_dir = spec_dir_with_files

        from commit_message import generate_commit_message

        with patch("commit_message._call_claude", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("AI failed")

            result = await generate_commit_message(
                project_dir,
                "001-test-feature"
            )

            # Should return fallback message
            assert result is not None
            assert "feat" in result.lower() or "test" in result.lower()

    @pytest.mark.asyncio
    async def test_generate_commit_message_fallback_on_empty_response(self, spec_dir_with_files):
        """Test fallback when AI returns empty response."""
        project_dir, spec_dir = spec_dir_with_files

        from commit_message import generate_commit_message

        with patch("commit_message._call_claude", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = ""

            result = await generate_commit_message(
                project_dir,
                "001-test-feature"
            )

            # Should return fallback message
            assert result is not None
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_generate_commit_message_with_files_and_diff(self, spec_dir_with_files):
        """Test with files changed and diff summary."""
        project_dir, spec_dir = spec_dir_with_files

        from commit_message import generate_commit_message

        with patch("commit_message._call_claude", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "fix: Fix parser\n\nFixed parsing bug"

            result = await generate_commit_message(
                project_dir,
                "001-test-feature",
                diff_summary="Fixed critical parser bug",
                files_changed=["parser.py", "tests/parser_test.py"]
            )

            assert result == "fix: Fix parser\n\nFixed parsing bug"
            # Verify prompt included the files and diff
            call_args = mock_call.call_args[0][0]
            assert "parser.py" in call_args
            assert "Fixed critical parser bug" in call_args

    @pytest.mark.asyncio
    async def test_generate_commit_message_github_override(self, spec_dir_with_files):
        """Test GitHub issue override in async version."""
        project_dir, spec_dir = spec_dir_with_files

        from commit_message import generate_commit_message

        with patch("commit_message._call_claude", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "feat: Add feature\n\nFixes #999"

            result = await generate_commit_message(
                project_dir,
                "001-test-feature",
                github_issue=999  # Override spec's issue 42
            )

            assert "#999" in result
            call_args = mock_call.call_args[0][0]
            assert "#999" in call_args


# =============================================================================
# Test _call_claude function
# =============================================================================


class TestCallClaude:
    """Tests for _call_claude function (via main functions)."""

    @pytest.mark.asyncio
    async def test_call_claude_via_generate_message_no_auth(self, spec_dir_with_files):
        """Test commit generation fails gracefully with no auth token."""
        project_dir, spec_dir = spec_dir_with_files

        from commit_message import generate_commit_message

        with patch("core.auth.get_auth_token", return_value=None):
            result = await generate_commit_message(
                project_dir,
                "001-test-feature"
            )

        # Should fall back to generated message
        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_call_claude_via_generate_message_with_mock(self, spec_dir_with_files):
        """Test commit generation with mocked AI response."""
        project_dir, spec_dir = spec_dir_with_files

        from commit_message import generate_commit_message

        # Create mock async iterator for receive_response
        async def mock_receive_iter():
            mock_response = MagicMock()
            mock_response.__class__.__name__ = "AssistantMessage"
            mock_text_block = MagicMock()
            mock_text_block.__class__.__name__ = "TextBlock"
            mock_text_block.text = "feat: AI Generated Message"
            mock_response.content = [mock_text_block]
            yield mock_response

        mock_client = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.receive_response = mock_receive_iter
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch("core.auth.get_auth_token", return_value="test-token"), \
             patch("core.simple_client.create_simple_client", return_value=mock_client), \
             patch("core.model_config.get_utility_model_config", return_value=("model", 1024)):

            result = await generate_commit_message(
                project_dir,
                "001-test-feature"
            )

            assert result == "feat: AI Generated Message"


# =============================================================================
# Test CATEGORY_TO_COMMIT_TYPE mapping
# =============================================================================


class TestCategoryMapping:
    """Tests for CATEGORY_TO_COMMIT_TYPE mapping."""

    def test_all_commit_types_valid(self):
        """Test all mapped types are valid conventional commits."""
        from commit_message import CATEGORY_TO_COMMIT_TYPE

        valid_types = {
            "feat", "fix", "refactor", "docs", "test",
            "perf", "security", "chore", "style", "ci", "build"
        }

        for category, commit_type in CATEGORY_TO_COMMIT_TYPE.items():
            assert commit_type in valid_types, f"{commit_type} is not a valid commit type"

    def test_common_categories_mapped(self):
        """Test common workflow categories are mapped."""
        from commit_message import CATEGORY_TO_COMMIT_TYPE

        common_categories = [
            "feature", "bug_fix", "bug", "refactoring",
            "documentation", "testing", "performance", "security"
        ]

        for category in common_categories:
            assert category in CATEGORY_TO_COMMIT_TYPE, f"{category} not mapped"

    def test_unknown_category_defaults_to_chore(self):
        """Test that unknown categories in context get handled."""
        from commit_message import _build_prompt

        # Use an unknown category
        spec_context = {
            "title": "Test",
            "category": "unknown_category_xyz",
            "description": "Test",
            "github_issue": None
        }

        result = _build_prompt(spec_context, "", [])

        # Should default to "chore"
        assert "Type: chore" in result


# =============================================================================
# Integration tests
# =============================================================================


class TestCommitMessageIntegration:
    """Integration tests for commit message generation."""

    @pytest.mark.asyncio
    async def test_full_flow_with_ai(self, spec_dir_with_files):
        """Test complete flow from spec to AI-generated message."""
        project_dir, spec_dir = spec_dir_with_files

        from commit_message import generate_commit_message

        ai_message = """feat: Add comprehensive commit message generation

Implement AI-powered commit message generation using Claude.
Supports conventional commits format with GitHub issue references.

Fixes #42"""

        with patch("commit_message._call_claude", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = ai_message

            result = await generate_commit_message(
                project_dir,
                "001-test-feature",
                diff_summary="Added commit message module",
                files_changed=["commit_message.py", "tests/test_commit_message.py"]
            )

            assert result == ai_message
            assert "feat:" in result
            assert "#42" in result

    @pytest.mark.asyncio
    async def test_full_flow_fallback_chain(self, spec_dir_with_files):
        """Test fallback chain when AI is unavailable."""
        project_dir, spec_dir = spec_dir_with_files

        from commit_message import generate_commit_message

        # Simulate AI failure
        with patch("commit_message._call_claude", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("Service unavailable")

            result = await generate_commit_message(
                project_dir,
                "001-test-feature"
            )

            # Should fall back to generated message
            assert result is not None
            assert "feat" in result.lower()  # From category
            assert "test feature" in result.lower()  # From title

    def test_sync_and_async_consistency(self, spec_dir_with_files):
        """Test that sync and async versions handle same inputs consistently."""
        project_dir, spec_dir = spec_dir_with_files

        from commit_message import generate_commit_message, generate_commit_message_sync

        # Both should use fallback when no auth
        with patch("core.auth.get_auth_token", return_value=None):
            # Sync version
            sync_result = generate_commit_message_sync(
                project_dir,
                "001-test-feature",
                diff_summary="Test diff",
                files_changed=["test.py"]
            )

            # Async version (need to run it)
            async def get_async_result():
                with patch("commit_message._call_claude", new_callable=AsyncMock) as mock_call:
                    mock_call.side_effect = Exception("No AI")
                    return await generate_commit_message(
                        project_dir,
                        "001-test-feature",
                        diff_summary="Test diff",
                        files_changed=["test.py"]
                    )

            async_result = asyncio.run(get_async_result())

            # Both should return fallback messages with similar structure
            assert sync_result is not None
            assert async_result is not None
            assert ":" in sync_result  # Has commit type
            assert ":" in async_result


# =============================================================================
# Edge cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_spec_name(self, temp_project_dir):
        """Test with empty spec name."""
        project_dir, _ = temp_project_dir

        from commit_message import generate_commit_message_sync

        with patch("core.auth.get_auth_token", return_value=None):
            result = generate_commit_message_sync(
                project_dir,
                ""
            )

        # Should still return something
        assert result is not None

    def test_special_characters_in_title(self, temp_project_dir):
        """Test spec title with special characters."""
        project_dir, spec_dir = temp_project_dir

        spec_md = spec_dir / "spec.md"
        spec_md.write_text("# Feature: Fix 'quote' and \"double\"")

        from commit_message import generate_commit_message_sync

        with patch("core.auth.get_auth_token", return_value=None):
            result = generate_commit_message_sync(
                project_dir,
                "001-test"
            )

        # Should handle special characters
        assert result is not None

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows console cannot encode certain Unicode characters (charmap codec limitation)")
    def test_unicode_in_description(self, temp_project_dir):
        """Test spec with Unicode characters."""
        project_dir, spec_dir = temp_project_dir

        spec_md = spec_dir / "spec.md"
        spec_md.write_text("# Feature\n\nDescription with emoji: ✓ and unicode: café")

        from commit_message import generate_commit_message_sync

        with patch("core.auth.get_auth_token", return_value=None):
            result = generate_commit_message_sync(
                project_dir,
                "001-test"
            )

        # Should handle unicode
        assert result is not None

    def test_very_long_spec_title(self, temp_project_dir):
        """Test with very long spec title."""
        project_dir, spec_dir = temp_project_dir

        long_title = "A" * 500
        spec_md = spec_dir / "spec.md"
        spec_md.write_text(f"# {long_title}")

        from commit_message import generate_commit_message_sync

        with patch("core.auth.get_auth_token", return_value=None):
            result = generate_commit_message_sync(
                project_dir,
                "001-test"
            )

        # Should handle long titles
        assert result is not None

    @pytest.mark.asyncio
    async def test_concurrent_calls(self, spec_dir_with_files):
        """Test multiple concurrent calls to generate_commit_message."""
        project_dir, spec_dir = spec_dir_with_files

        from commit_message import generate_commit_message

        with patch("commit_message._call_claude", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "feat: Test"

            # Run multiple concurrent calls
            tasks = [
                generate_commit_message(project_dir, "001-test-feature")
                for _ in range(5)
            ]

            results = await asyncio.gather(*tasks)

            # All should succeed
            assert len(results) == 5
            assert all(r == "feat: Test" for r in results)


# =============================================================================
# Test constants
# =============================================================================


class TestConstants:
    """Tests for module constants."""

    def test_system_prompt_exists(self):
        """Test SYSTEM_PROMPT is defined."""
        from commit_message import SYSTEM_PROMPT

        assert SYSTEM_PROMPT is not None
        assert len(SYSTEM_PROMPT) > 0
        assert "conventional commits" in SYSTEM_PROMPT.lower()

    def test_category_mapping_complete(self):
        """Test CATEGORY_TO_COMMIT_TYPE has all expected mappings."""
        from commit_message import CATEGORY_TO_COMMIT_TYPE

        # Should have mappings for common types
        expected_mappings = [
            ("feature", "feat"),
            ("bug_fix", "fix"),
            ("refactoring", "refactor"),
            ("documentation", "docs"),
            ("testing", "test"),
        ]

        for category, expected_type in expected_mappings:
            assert CATEGORY_TO_COMMIT_TYPE[category] == expected_type
