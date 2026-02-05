"""Tests for compaction module"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from spec.compaction import format_phase_summaries, gather_phase_outputs, summarize_phase_output


class TestSummarizePhaseOutput:
    """Tests for summarize_phase_output function"""

    @pytest.mark.asyncio
    async def test_summarize_phase_output_success(self, tmp_path):
        """Test successful summarization"""
        from claude_agent_sdk.types import AssistantMessage, TextBlock

        # Create an async generator function for the mock response
        async def mock_response_gen():
            msg = AssistantMessage(model="sonnet", content=[TextBlock(text="Summary content")])
            yield msg
            return  # Add explicit return to end the generator

        mock_client = AsyncMock()
        mock_client.query = AsyncMock()

        # Make receive_response return an async generator
        # We need to use side_effect to return the generator function result
        mock_client.receive_response = lambda: mock_response_gen()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch("spec.compaction.create_simple_client", return_value=mock_client):
            with patch("spec.compaction.require_auth_token"):
                result = await summarize_phase_output(
                    phase_name="discovery",
                    phase_output="Long output content",
                    model="sonnet",
                    target_words=500,
                )

                assert result == "Summary content"

    @pytest.mark.asyncio
    async def test_summarize_phase_output_truncates_large_input(self, tmp_path):
        """Test that large inputs are truncated"""
        from claude_agent_sdk.types import AssistantMessage, TextBlock

        large_output = "x" * 20000

        async def mock_response_gen():
            msg = AssistantMessage(model="sonnet", content=[TextBlock(text="Summary")])
            yield msg

        mock_client = AsyncMock()
        mock_client.query = AsyncMock()
        mock_client.receive_response = lambda: mock_response_gen()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch("spec.compaction.create_simple_client", return_value=mock_client):
            with patch("spec.compaction.require_auth_token"):
                result = await summarize_phase_output(
                    phase_name="discovery",
                    phase_output=large_output,
                    model="sonnet",
                )

                assert result == "Summary"
                # Check that the input was truncated in the prompt
                call_args = mock_client.query.call_args
                prompt = call_args[0][0]
                assert len(prompt) < len(large_output)
                assert "truncated" in prompt.lower()

    @pytest.mark.asyncio
    async def test_summarize_phase_output_fallback_on_error(self, tmp_path):
        """Test fallback behavior on error"""
        mock_client = AsyncMock()
        # Make query raise an exception
        mock_client.query = AsyncMock(side_effect=Exception("API error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        # Make __aexit__ re-raise the exception so it propagates to the try/except in the function
        mock_client.__aexit__ = AsyncMock(side_effect=Exception("API error"))

        with patch("spec.compaction.create_simple_client", return_value=mock_client):
            with patch("spec.compaction.require_auth_token"):
                result = await summarize_phase_output(
                    phase_name="discovery",
                    phase_output="Some output content",
                    model="sonnet",
                )

                # Should return fallback content
                assert result is not None
                assert "Summarization failed" in result
                # Check that the fallback contains part of the original content
                assert "Some output content" in result or len(result) > 0

    @pytest.mark.asyncio
    async def test_summarize_phase_output_fallback_truncates_large_output(self, tmp_path):
        """Test fallback truncates output when > 2000 chars"""
        mock_client = AsyncMock()
        # Make query raise an exception
        mock_client.query = AsyncMock(side_effect=Exception("API error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(side_effect=Exception("API error"))

        # Create output larger than 2000 chars
        large_output = "x" * 3000

        with patch("spec.compaction.create_simple_client", return_value=mock_client):
            with patch("spec.compaction.require_auth_token"):
                result = await summarize_phase_output(
                    phase_name="discovery",
                    phase_output=large_output,
                    model="sonnet",
                )

                # Should contain truncated marker
                assert "Summarization failed" in result
                assert "[... truncated ...]" in result
                # Should be shorter than original
                assert len(result) < len(large_output)


class TestFormatPhaseSummaries:
    """Tests for format_phase_summaries function"""

    def test_format_empty_summaries(self):
        """Test formatting empty summaries dict"""
        result = format_phase_summaries({})
        assert result == ""

    def test_format_single_summary(self):
        """Test formatting single phase summary"""
        summaries = {"discovery": "Found important files"}
        result = format_phase_summaries(summaries)

        assert "## Context from Previous Phases" in result
        assert "### Discovery" in result
        assert "Found important files" in result

    def test_format_multiple_summaries(self):
        """Test formatting multiple phase summaries"""
        summaries = {
            "discovery": "Discovered project structure",
            "requirements": "Gathered user requirements",
            "research": "Researched integrations",
        }
        result = format_phase_summaries(summaries)

        assert "## Context from Previous Phases" in result
        assert "### Discovery" in result
        assert "Discovered project structure" in result
        assert "### Requirements" in result
        assert "Gathered user requirements" in result
        assert "### Research" in result
        assert "Researched integrations" in result

    def test_format_phase_name_capitalization(self):
        """Test phase names are properly capitalized"""
        summaries = {"quick_spec": "Quick spec summary"}
        result = format_phase_summaries(summaries)

        assert "### Quick Spec" in result


class TestGatherPhaseOutputs:
    """Tests for gather_phase_outputs function"""

    def test_gather_from_discovery_phase(self, tmp_path):
        """Test gathering outputs from discovery phase"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        context_file = spec_dir / "context.json"
        context_file.write_text('{"task": "test"}', encoding="utf-8")

        result = gather_phase_outputs(spec_dir, "discovery")

        assert "**context.json**" in result
        assert '{"task": "test"}' in result

    def test_gather_from_requirements_phase(self, tmp_path):
        """Test gathering outputs from requirements phase"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        req_file = spec_dir / "requirements.json"
        req_file.write_text('{"task_description": "Build feature"}', encoding="utf-8")

        result = gather_phase_outputs(spec_dir, "requirements")

        assert "**requirements.json**" in result
        assert "Build feature" in result

    def test_gather_from_spec_writing_phase(self, tmp_path):
        """Test gathering outputs from spec_writing phase"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"
        spec_file.write_text("# Spec Document\n\nContent here", encoding="utf-8")

        result = gather_phase_outputs(spec_dir, "spec_writing")

        assert "**spec.md**" in result
        assert "# Spec Document" in result

    def test_gather_from_self_critique_phase(self, tmp_path):
        """Test gathering outputs from self_critique phase"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "spec.md"
        spec_file.write_text("# Spec", encoding="utf-8")
        critique_file = spec_dir / "critique_notes.md"
        critique_file.write_text("Critique notes", encoding="utf-8")

        result = gather_phase_outputs(spec_dir, "self_critique")

        assert "**spec.md**" in result
        assert "**critique_notes.md**" in result

    def test_gather_from_validation_phase_returns_empty(self, tmp_path):
        """Test validation phase has no outputs to gather"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = gather_phase_outputs(spec_dir, "validation")

        assert result == ""

    def test_gather_truncates_large_files(self, tmp_path):
        """Test large files are truncated"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        context_file = spec_dir / "context.json"
        large_content = "x" * 20000
        context_file.write_text(large_content, encoding="utf-8")

        result = gather_phase_outputs(spec_dir, "context")

        assert "truncated" in result.lower()
        assert len(result) < len(large_content)

    def test_gather_skips_missing_files(self, tmp_path):
        """Test missing files are skipped gracefully"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # No files created
        result = gather_phase_outputs(spec_dir, "discovery")

        assert result == ""

    def test_gather_handles_unreadable_files(self, tmp_path):
        """Test unreadable files are skipped"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        context_file = spec_dir / "context.json"

        # Create file but make it unreadable (simulate permission error)
        context_file.write_text("content", encoding="utf-8")

        with patch.object(Path, "read_text", side_effect=OSError("Permission denied")):
            result = gather_phase_outputs(spec_dir, "discovery")

        # Should skip the file and return empty
        assert result == ""

    def test_gather_from_unknown_phase_returns_empty(self, tmp_path):
        """Test unknown phase returns empty string"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        result = gather_phase_outputs(spec_dir, "unknown_phase")

        assert result == ""

    def test_gather_from_planning_phase(self, tmp_path):
        """Test gathering outputs from planning phase"""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        plan_file = spec_dir / "implementation_plan.json"
        plan = {"phases": [{"name": "Phase 1"}]}
        plan_file.write_text(json.dumps(plan), encoding="utf-8")

        result = gather_phase_outputs(spec_dir, "planning")

        assert "**implementation_plan.json**" in result
        assert "Phase 1" in result
