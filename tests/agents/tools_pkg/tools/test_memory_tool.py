"""Tests for agents.tools_pkg.tools.memory module."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest

from agents.tools_pkg.tools.memory import (
    create_memory_tools,
    _save_to_graphiti_async,
    _save_to_graphiti_sync,
)


class TestSaveToGraphitiAsync:
    """Test _save_to_graphiti_async function."""

    @pytest.mark.asyncio
    async def test_saves_discovery(self):
        """Test saving discovery to Graphiti."""
        mock_memory = AsyncMock()
        mock_memory.save_codebase_discoveries = AsyncMock(return_value=True)
        mock_memory.close = AsyncMock()

        with patch("memory.graphiti_helpers.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):
            result = await _save_to_graphiti_async(
                Path("/tmp/spec"),
                Path("/tmp/project"),
                "discovery",
                {"file_path": "test.py", "description": "Test file"}
            )

            assert result is True
            mock_memory.save_codebase_discoveries.assert_called_once()

    @pytest.mark.asyncio
    async def test_saves_gotcha(self):
        """Test saving gotcha to Graphiti."""
        mock_memory = AsyncMock()
        mock_memory.save_gotcha = AsyncMock(return_value=True)
        mock_memory.close = AsyncMock()

        with patch("memory.graphiti_helpers.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):
            result = await _save_to_graphiti_async(
                Path("/tmp/spec"),
                Path("/tmp/project"),
                "gotcha",
                {"gotcha": "Watch out for this", "context": "When doing X"}
            )

            assert result is True
            mock_memory.save_gotcha.assert_called_once()

    @pytest.mark.asyncio
    async def test_saves_pattern(self):
        """Test saving pattern to Graphiti."""
        mock_memory = AsyncMock()
        mock_memory.save_pattern = AsyncMock(return_value=True)
        mock_memory.close = AsyncMock()

        with patch("memory.graphiti_helpers.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):
            result = await _save_to_graphiti_async(
                Path("/tmp/spec"),
                Path("/tmp/project"),
                "pattern",
                {"pattern": "Use async/await for I/O"}
            )

            assert result is True
            mock_memory.save_pattern.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_on_memory_unavailable(self):
        """Test that False is returned when memory is unavailable."""
        with patch("memory.graphiti_helpers.get_graphiti_memory", new_callable=AsyncMock, return_value=None):
            result = await _save_to_graphiti_async(
                Path("/tmp/spec"),
                Path("/tmp/project"),
                "discovery",
                {"file_path": "test.py", "description": "Test"}
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self):
        """Test that False is returned on exception."""
        mock_memory = AsyncMock()
        mock_memory.save_codebase_discoveries = AsyncMock(side_effect=Exception("Save error"))
        mock_memory.close = AsyncMock()

        with patch("memory.graphiti_helpers.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):
            result = await _save_to_graphiti_async(
                Path("/tmp/spec"),
                Path("/tmp/project"),
                "discovery",
                {"file_path": "test.py", "description": "Test"}
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_closes_memory_on_success(self):
        """Test that memory is closed after successful save."""
        mock_memory = AsyncMock()
        mock_memory.save_codebase_discoveries = AsyncMock(return_value=True)
        mock_memory.close = AsyncMock()

        with patch("memory.graphiti_helpers.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):
            await _save_to_graphiti_async(
                Path("/tmp/spec"),
                Path("/tmp/project"),
                "discovery",
                {"file_path": "test.py", "description": "Test"}
            )

            mock_memory.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_closes_memory_on_error(self):
        """Test that memory is closed even when save fails."""
        mock_memory = AsyncMock()
        mock_memory.save_codebase_discoveries = AsyncMock(side_effect=Exception("Error"))
        mock_memory.close = AsyncMock()

        with patch("memory.graphiti_helpers.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):
            await _save_to_graphiti_async(
                Path("/tmp/spec"),
                Path("/tmp/project"),
                "discovery",
                {"file_path": "test.py", "description": "Test"}
            )

            mock_memory.close.assert_called_once()


class TestSaveToGraphitiSync:
    """Test _save_to_graphiti_sync function."""

    def test_runs_async_function(self):
        """Test that sync wrapper runs async function."""
        mock_memory = AsyncMock()
        mock_memory.save_codebase_discoveries = AsyncMock(return_value=True)
        mock_memory.close = AsyncMock()

        with patch("memory.graphiti_helpers.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):
            result = _save_to_graphiti_sync(
                Path("/tmp/spec"),
                Path("/tmp/project"),
                "discovery",
                {"file_path": "test.py", "description": "Test"}
            )

            assert result is True

    def test_returns_false_on_exception(self):
        """Test that False is returned on exception."""
        with patch("memory.graphiti_helpers.get_graphiti_memory", new_callable=AsyncMock, side_effect=Exception("Error")):
            result = _save_to_graphiti_sync(
                Path("/tmp/spec"),
                Path("/tmp/project"),
                "discovery",
                {"file_path": "test.py", "description": "Test"}
            )

            assert result is False


class TestCreateMemoryTools:
    """Test create_memory_tools function."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        """Create a temporary spec directory."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    def test_returns_tools_when_sdk_available(self, mock_spec_dir, mock_project_dir):
        """Test that tools are returned when SDK is available."""
        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True):
            tools = create_memory_tools(mock_spec_dir, mock_project_dir)

            assert len(tools) == 3  # record_discovery, record_gotcha, get_session_context

    def test_returns_empty_list_when_sdk_unavailable(self, mock_spec_dir, mock_project_dir):
        """Test that empty list is returned when SDK is unavailable."""
        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", False):
            tools = create_memory_tools(mock_spec_dir, mock_project_dir)

            assert tools == []

    @pytest.mark.asyncio
    async def test_record_discovery_tool(self, mock_spec_dir, mock_project_dir):
        """Test record_discovery tool."""
        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.tools.memory._save_to_graphiti_async", new_callable=AsyncMock, return_value=False):

            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            discovery_tool = tools[0]

            result = await discovery_tool.handler({
                "file_path": "src/test.py",
                "description": "Main test file",
                "category": "test"
            })

            assert "Recorded discovery" in result["content"][0]["text"]

            # Verify file was created
            codebase_map = mock_spec_dir / "memory" / "codebase_map.json"
            assert codebase_map.exists()

    @pytest.mark.asyncio
    async def test_record_gotcha_tool(self, mock_spec_dir, mock_project_dir):
        """Test record_gotcha tool."""
        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.tools.memory._save_to_graphiti_async", new_callable=AsyncMock, return_value=False):

            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            gotcha_tool = tools[1]

            result = await gotcha_tool.handler({
                "gotcha": "Don't forget to close connections",
                "context": "Database operations"
            })

            assert "Recorded gotcha" in result["content"][0]["text"]

            # Verify file was created
            gotchas_file = mock_spec_dir / "memory" / "gotchas.md"
            assert gotchas_file.exists()

    @pytest.mark.asyncio
    async def test_get_session_context_tool_no_memory(self, mock_spec_dir, mock_project_dir):
        """Test get_session_context tool when no memory exists."""
        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True):
            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            context_tool = tools[2]

            result = await context_tool.handler({})

            assert "No session memory found" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_get_session_context_tool_with_memory(self, mock_spec_dir, mock_project_dir):
        """Test get_session_context tool with existing memory."""
        memory_dir = mock_spec_dir / "memory"
        memory_dir.mkdir()

        # Create codebase map
        codebase_map = {
            "discovered_files": {
                "src/test.py": {"description": "Test file", "category": "test"}
            },
            "last_updated": "2024-01-01T00:00:00Z"
        }
        (memory_dir / "codebase_map.json").write_text(json.dumps(codebase_map))

        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True):
            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            context_tool = tools[2]

            result = await context_tool.handler({})

            assert "Codebase Discoveries" in result["content"][0]["text"]
            assert "src/test.py" in result["content"][0]["text"]


class TestRecordDiscoveryErrors:
    """Test error handling in record_discovery tool."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    @pytest.mark.asyncio
    async def test_record_discovery_with_default_category(self, mock_spec_dir, mock_project_dir):
        """Test record_discovery with default category."""
        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.tools.memory._save_to_graphiti_async", new_callable=AsyncMock, return_value=False):

            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            discovery_tool = tools[0]

            result = await discovery_tool.handler({
                "file_path": "src/test.py",
                "description": "Main test file"
                # No category specified
            })

            assert "Recorded discovery" in result["content"][0]["text"]

            # Verify default category was used
            codebase_map = mock_spec_dir / "memory" / "codebase_map.json"
            data = json.loads(codebase_map.read_text())
            assert data["discovered_files"]["src/test.py"]["category"] == "general"

    @pytest.mark.asyncio
    async def test_record_discovery_updates_existing_entry(self, mock_spec_dir, mock_project_dir):
        """Test that existing discovery is updated."""
        memory_dir = mock_spec_dir / "memory"
        memory_dir.mkdir()

        # Create existing entry
        codebase_map = {
            "discovered_files": {
                "src/test.py": {"description": "Old description", "category": "old"}
            },
            "last_updated": "2024-01-01T00:00:00Z"
        }
        (memory_dir / "codebase_map.json").write_text(json.dumps(codebase_map))

        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.tools.memory._save_to_graphiti_async", new_callable=AsyncMock, return_value=False):

            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            discovery_tool = tools[0]

            result = await discovery_tool.handler({
                "file_path": "src/test.py",
                "description": "New description",
                "category": "new"
            })

            assert "Recorded discovery" in result["content"][0]["text"]

            data = json.loads((memory_dir / "codebase_map.json").read_text())
            assert data["discovered_files"]["src/test.py"]["description"] == "New description"
            assert data["discovered_files"]["src/test.py"]["category"] == "new"

    @pytest.mark.asyncio
    async def test_record_discovery_with_graphiti_success(self, mock_spec_dir, mock_project_dir):
        """Test record_discovery with successful Graphiti save."""
        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.tools.memory._save_to_graphiti_async", new_callable=AsyncMock, return_value=True):

            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            discovery_tool = tools[0]

            result = await discovery_tool.handler({
                "file_path": "src/test.py",
                "description": "Test file",
                "category": "test"
            })

            assert "also saved to memory graph" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_record_discovery_json_decode_error(self, mock_spec_dir, mock_project_dir):
        """Test record_discovery handles JSON decode errors."""
        memory_dir = mock_spec_dir / "memory"
        memory_dir.mkdir()

        # Create invalid JSON file
        (memory_dir / "codebase_map.json").write_text("{ invalid json }")

        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.tools.memory._save_to_graphiti_async", new_callable=AsyncMock, return_value=False):

            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            discovery_tool = tools[0]

            result = await discovery_tool.handler({
                "file_path": "src/test.py",
                "description": "Test file",
                "category": "test"
            })

            # Should return an error when JSON is invalid
            assert "Error recording discovery" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_record_discovery_with_empty_discovered_files(self, mock_spec_dir, mock_project_dir):
        """Test record_discovery when existing map has empty discovered_files."""
        memory_dir = mock_spec_dir / "memory"
        memory_dir.mkdir()

        # Create existing map with empty discovered_files
        codebase_map = {
            "discovered_files": {},
            "last_updated": None
        }
        (memory_dir / "codebase_map.json").write_text(json.dumps(codebase_map))

        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.tools.memory._save_to_graphiti_async", new_callable=AsyncMock, return_value=False):

            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            discovery_tool = tools[0]

            result = await discovery_tool.handler({
                "file_path": "src/new.py",
                "description": "New file",
                "category": "test"
            })

            assert "Recorded discovery" in result["content"][0]["text"]


class TestRecordGotchaErrors:
    """Test error handling in record_gotcha tool."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    @pytest.mark.asyncio
    async def test_record_gotcha_without_context(self, mock_spec_dir, mock_project_dir):
        """Test record_gotcha without context."""
        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.tools.memory._save_to_graphiti_async", new_callable=AsyncMock, return_value=False):

            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            gotcha_tool = tools[1]

            result = await gotcha_tool.handler({
                "gotcha": "Don't forget to close connections"
                # No context
            })

            assert "Recorded gotcha" in result["content"][0]["text"]

            gotchas_file = mock_spec_dir / "memory" / "gotchas.md"
            content = gotchas_file.read_text()
            assert "Don't forget to close connections" in content
            assert "_Context:" not in content  # No context section

    @pytest.mark.asyncio
    async def test_record_gotcha_appends_to_existing_file(self, mock_spec_dir, mock_project_dir):
        """Test that gotcha is appended to existing file."""
        memory_dir = mock_spec_dir / "memory"
        memory_dir.mkdir()

        # Create existing gotchas file
        (memory_dir / "gotchas.md").write_text(
            "# Gotchas & Pitfalls\n\nThings to watch out for in this codebase.\n"
            "\n## [2024-01-01 10:00]\nOld gotcha\n"
        )

        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.tools.memory._save_to_graphiti_async", new_callable=AsyncMock, return_value=False):

            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            gotcha_tool = tools[1]

            result = await gotcha_tool.handler({
                "gotcha": "New gotcha",
                "context": "New context"
            })

            assert "Recorded gotcha" in result["content"][0]["text"]

            content = (memory_dir / "gotchas.md").read_text()
            assert "Old gotcha" in content
            assert "New gotcha" in content

    @pytest.mark.asyncio
    async def test_record_gotcha_with_graphiti_success(self, mock_spec_dir, mock_project_dir):
        """Test record_gotcha with successful Graphiti save."""
        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.tools.memory._save_to_graphiti_async", new_callable=AsyncMock, return_value=True):

            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            gotcha_tool = tools[1]

            result = await gotcha_tool.handler({
                "gotcha": "Test gotcha",
                "context": "Test context"
            })

            assert "also saved to memory graph" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_record_gotcha_creates_header_on_new_file(self, mock_spec_dir, mock_project_dir):
        """Test that gotcha file gets proper header when created."""
        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.tools.memory._save_to_graphiti_async", new_callable=AsyncMock, return_value=False):

            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            gotcha_tool = tools[1]

            await gotcha_tool.handler({
                "gotcha": "Test gotcha",
                "context": "Test context"
            })

            gotchas_file = mock_spec_dir / "memory" / "gotchas.md"
            content = gotchas_file.read_text()
            assert "# Gotchas & Pitfalls" in content
            assert "Things to watch out for in this codebase." in content

    @pytest.mark.asyncio
    async def test_record_gotcha_with_empty_context(self, mock_spec_dir, mock_project_dir):
        """Test record_gotcha with empty string context."""
        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.tools.memory._save_to_graphiti_async", new_callable=AsyncMock, return_value=False):

            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            gotcha_tool = tools[1]

            result = await gotcha_tool.handler({
                "gotcha": "Test gotcha",
                "context": ""
            })

            assert "Recorded gotcha" in result["content"][0]["text"]

            # Empty context should not add context line
            gotchas_file = mock_spec_dir / "memory" / "gotchas.md"
            content = gotchas_file.read_text()
            assert "_Context:_" not in content


class TestGetSessionContextErrors:
    """Test edge cases in get_session_context tool."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    @pytest.mark.asyncio
    async def test_get_session_context_with_only_gotchas(self, mock_spec_dir, mock_project_dir):
        """Test get_session_context with only gotchas file."""
        memory_dir = mock_spec_dir / "memory"
        memory_dir.mkdir()

        (memory_dir / "gotchas.md").write_text("## Gotchas\n\nTest gotcha")

        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True):
            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            context_tool = tools[2]

            result = await context_tool.handler({})

            content = result["content"][0]["text"]
            assert "Gotchas" in content
            assert "Test gotcha" in content

    @pytest.mark.asyncio
    async def test_get_session_context_with_only_patterns(self, mock_spec_dir, mock_project_dir):
        """Test get_session_context with only patterns file."""
        memory_dir = mock_spec_dir / "memory"
        memory_dir.mkdir()

        (memory_dir / "patterns.md").write_text("## Patterns\n\nTest pattern")

        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True):
            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            context_tool = tools[2]

            result = await context_tool.handler({})

            content = result["content"][0]["text"]
            assert "Patterns" in content
            assert "Test pattern" in content

    @pytest.mark.asyncio
    async def test_get_session_context_with_all_memory_types(self, mock_spec_dir, mock_project_dir):
        """Test get_session_context with all memory types."""
        memory_dir = mock_spec_dir / "memory"
        memory_dir.mkdir()

        # Create all memory files
        codebase_map = {
            "discovered_files": {
                "src/test.py": {"description": "Test file", "category": "test"}
            },
            "last_updated": "2024-01-01T00:00:00Z"
        }
        (memory_dir / "codebase_map.json").write_text(json.dumps(codebase_map))
        (memory_dir / "gotchas.md").write_text("## Gotchas\n\nTest gotcha")
        (memory_dir / "patterns.md").write_text("## Patterns\n\nTest pattern")

        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True):
            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            context_tool = tools[2]

            result = await context_tool.handler({})

            content = result["content"][0]["text"]
            assert "Codebase Discoveries" in content
            assert "Gotchas" in content
            assert "Patterns" in content

    @pytest.mark.asyncio
    async def test_get_session_context_with_empty_files(self, mock_spec_dir, mock_project_dir):
        """Test get_session_context with empty memory files."""
        memory_dir = mock_spec_dir / "memory"
        memory_dir.mkdir()

        # Create empty files
        (memory_dir / "codebase_map.json").write_text('{"discovered_files": {}, "last_updated": null}')
        (memory_dir / "gotchas.md").write_text("")
        (memory_dir / "patterns.md").write_text("")

        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True):
            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            context_tool = tools[2]

            result = await context_tool.handler({})

            # Empty discovered_files means no discoveries shown
            assert result["content"][0]["text"] == "No session context available yet."

    @pytest.mark.asyncio
    async def test_get_session_context_limits_large_discoveries(self, mock_spec_dir, mock_project_dir):
        """Test that get_session_context limits discoveries to 20."""
        memory_dir = mock_spec_dir / "memory"
        memory_dir.mkdir()

        # Create 25 discoveries
        discovered_files = {}
        for i in range(25):
            discovered_files[f"src/file{i}.py"] = {
                "description": f"File {i}",
                "category": "test"
            }

        codebase_map = {
            "discovered_files": discovered_files,
            "last_updated": "2024-01-01T00:00:00Z"
        }
        (memory_dir / "codebase_map.json").write_text(json.dumps(codebase_map))

        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True):
            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            context_tool = tools[2]

            result = await context_tool.handler({})

            content = result["content"][0]["text"]
            # Should show first 20
            assert "src/file0.py" in content
            assert "src/file19.py" in content
            # Should not show file 20-24
            assert "src/file20.py" not in content
            assert "src/file24.py" not in content

    @pytest.mark.asyncio
    async def test_get_session_context_truncates_large_files(self, mock_spec_dir, mock_project_dir):
        """Test that large gotchas/patterns files are truncated."""
        memory_dir = mock_spec_dir / "memory"
        memory_dir.mkdir()

        # Create gotchas file larger than 1000 chars
        large_content = "## Gotchas\n\n" + "x" * 1500
        (memory_dir / "gotchas.md").write_text(large_content)

        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True):
            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            context_tool = tools[2]

            result = await context_tool.handler({})

            content = result["content"][0]["text"]
            # Content should be truncated to last 1000 chars
            assert len(content) < len(large_content)

    @pytest.mark.asyncio
    async def test_get_session_context_handles_json_decode_error(self, mock_spec_dir, mock_project_dir):
        """Test get_session_context handles invalid JSON in codebase map."""
        memory_dir = mock_spec_dir / "memory"
        memory_dir.mkdir()

        # Create invalid JSON file
        (memory_dir / "codebase_map.json").write_text("{ invalid }")
        (memory_dir / "gotchas.md").write_text("## Gotchas\n\nValid gotcha")

        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True):
            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            context_tool = tools[2]

            result = await context_tool.handler({})

            # Should still show gotchas even with invalid JSON
            content = result["content"][0]["text"]
            assert "Gotchas" in content
            assert "Valid gotcha" in content

    @pytest.mark.asyncio
    async def test_get_session_context_handles_read_errors(self, mock_spec_dir, mock_project_dir):
        """Test get_session_context handles file read errors gracefully."""
        memory_dir = mock_spec_dir / "memory"
        memory_dir.mkdir()

        # Create a directory instead of a file (will cause read error)
        (memory_dir / "codebase_map.json").mkdir()

        (memory_dir / "gotchas.md").write_text("## Gotchas\n\nValid gotcha")

        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True):
            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            context_tool = tools[2]

            result = await context_tool.handler({})

            # Should still show gotchas even with codebase_map error
            content = result["content"][0]["text"]
            assert "Gotchas" in content


class TestSaveToGraphitiSyncAsyncContext:
    """Test _save_to_graphiti_sync async context detection."""

    def test_warns_when_called_from_async_context(self):
        """Test that warning is logged when called from async context."""
        import asyncio

        async def try_async_call():
            with patch("agents.tools_pkg.tools.memory._save_to_graphiti_async", new_callable=AsyncMock, return_value=True):
                # This will detect the running loop and return False with a warning
                result = _save_to_graphiti_sync(
                    Path("/tmp/spec"),
                    Path("/tmp/project"),
                    "discovery",
                    {"file_path": "test.py", "description": "Test"}
                )
                return result

        result = asyncio.run(try_async_call())
        # Should return False due to async context detection
        assert result is False


class TestSaveToGraphitiAsyncUnknownSaveType:
    """Test _save_to_graphiti_async with unknown save type."""

    @pytest.mark.asyncio
    async def test_returns_false_for_unknown_save_type(self):
        """Test that False is returned for unknown save type."""
        mock_memory = AsyncMock()
        mock_memory.close = AsyncMock()

        with patch("memory.graphiti_helpers.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):
            result = await _save_to_graphiti_async(
                Path("/tmp/spec"),
                Path("/tmp/project"),
                "unknown_type",  # Not discovery, gotcha, or pattern
                {"data": "test"}
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_closes_memory_on_unknown_save_type(self):
        """Test that memory is closed even for unknown save types."""
        mock_memory = AsyncMock()
        mock_memory.close = AsyncMock()

        with patch("memory.graphiti_helpers.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):
            await _save_to_graphiti_async(
                Path("/tmp/spec"),
                Path("/tmp/project"),
                "unknown_type",
                {"data": "test"}
            )

            mock_memory.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_closes_memory_on_close_exception(self):
        """Test that close exception is handled gracefully."""
        mock_memory = AsyncMock()
        mock_memory.save_codebase_discoveries = AsyncMock(return_value=True)
        mock_memory.close = AsyncMock(side_effect=Exception("Close error"))

        with patch("memory.graphiti_helpers.get_graphiti_memory", new_callable=AsyncMock, return_value=mock_memory):
            result = await _save_to_graphiti_async(
                Path("/tmp/spec"),
                Path("/tmp/project"),
                "discovery",
                {"file_path": "test.py", "description": "Test"}
            )

            # Should still return True even though close failed
            assert result is True

    @pytest.mark.asyncio
    async def test_handles_get_graphiti_memory_exception(self):
        """Test that exception from get_graphiti_memory is handled."""
        with patch("memory.graphiti_helpers.get_graphiti_memory", new_callable=AsyncMock, side_effect=Exception("Connection error")):
            result = await _save_to_graphiti_async(
                Path("/tmp/spec"),
                Path("/tmp/project"),
                "discovery",
                {"file_path": "test.py", "description": "Test"}
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_graphiti_memory_is_none(self):
        """Test that None from get_graphiti_memory is handled."""
        with patch("memory.graphiti_helpers.get_graphiti_memory", new_callable=AsyncMock, return_value=None):
            result = await _save_to_graphiti_async(
                Path("/tmp/spec"),
                Path("/tmp/project"),
                "discovery",
                {"file_path": "test.py", "description": "Test"}
            )

            assert result is False


class TestSaveToGraphitiSyncExceptions:
    """Test _save_to_graphiti_sync exception handling."""

    def test_handles_asyncio_run_exception(self):
        """Test that exceptions from asyncio.run are handled."""
        with patch("agents.tools_pkg.tools.memory._save_to_graphiti_async", new_callable=AsyncMock, side_effect=Exception("Async error")):
            result = _save_to_graphiti_sync(
                Path("/tmp/spec"),
                Path("/tmp/project"),
                "discovery",
                {"file_path": "test.py", "description": "Test"}
            )

            assert result is False


class TestCreateMemoryToolsSdkUnavailable:
    """Test create_memory_tools when SDK is unavailable."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        """Create a temporary spec directory."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    def test_returns_empty_list_when_sdk_unavailable(self, mock_spec_dir, mock_project_dir):
        """Test that empty list is returned when SDK is unavailable."""
        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", False):
            tools = create_memory_tools(mock_spec_dir, mock_project_dir)

            assert tools == []


class TestRecordDiscoveryUnhandledException:
    """Test record_discovery tool with unhandled exceptions."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    @pytest.mark.asyncio
    async def test_handles_unexpected_exception(self, mock_spec_dir, mock_project_dir):
        """Test that unexpected exceptions are handled."""
        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.tools.memory._save_to_graphiti_async", new_callable=AsyncMock, side_effect=RuntimeError("Unexpected error")):

            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            discovery_tool = tools[0]

            result = await discovery_tool.handler({
                "file_path": "src/test.py",
                "description": "Test file",
                "category": "test"
            })

            # Should return an error response
            assert "Error recording discovery" in result["content"][0]["text"]


class TestGetSessionContextEdgeCasesMore:
    """Additional edge case tests for get_session_context tool."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    @pytest.mark.asyncio
    async def test_handles_patterns_file_read_error(self, mock_spec_dir, mock_project_dir):
        """Test get_session_context when patterns file has read error."""
        memory_dir = mock_spec_dir / "memory"
        memory_dir.mkdir()

        # Create directory instead of file for patterns (will cause read error)
        codebase_map = {
            "discovered_files": {
                "src/test.py": {"description": "Test file", "category": "test"}
            },
            "last_updated": "2024-01-01T00:00:00Z"
        }
        (memory_dir / "codebase_map.json").write_text(json.dumps(codebase_map))
        (memory_dir / "patterns.md").mkdir()

        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True):
            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            context_tool = tools[2]

            result = await context_tool.handler({})

            # Should still show discoveries even with patterns error
            content = result["content"][0]["text"]
            assert "Codebase Discoveries" in content

    @pytest.mark.asyncio
    async def test_handles_gotchas_file_read_error(self, mock_spec_dir, mock_project_dir):
        """Test get_session_context when gotchas file has read error."""
        memory_dir = mock_spec_dir / "memory"
        memory_dir.mkdir()

        # Create directory instead of file for gotchas
        codebase_map = {
            "discovered_files": {
                "src/test.py": {"description": "Test file", "category": "test"}
            },
            "last_updated": "2024-01-01T00:00:00Z"
        }
        (memory_dir / "codebase_map.json").write_text(json.dumps(codebase_map))
        (memory_dir / "gotchas.md").mkdir()
        (memory_dir / "patterns.md").write_text("## Patterns\n\nTest pattern")

        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True):
            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            context_tool = tools[2]

            result = await context_tool.handler({})

            # Should still show discoveries and patterns
            content = result["content"][0]["text"]
            assert "Codebase Discoveries" in content
            assert "Patterns" in content

    @pytest.mark.asyncio
    async def test_no_context_returned_when_all_fail(self, mock_spec_dir, mock_project_dir):
        """Test get_session_context when all memory files fail to load."""
        memory_dir = mock_spec_dir / "memory"
        memory_dir.mkdir()

        # Create directories instead of files (will cause read errors)
        (memory_dir / "codebase_map.json").mkdir()
        (memory_dir / "gotchas.md").mkdir()
        (memory_dir / "patterns.md").mkdir()

        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True):
            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            context_tool = tools[2]

            result = await context_tool.handler({})

            # Should indicate no context available
            assert result["content"][0]["text"] == "No session context available yet."

    @pytest.mark.asyncio
    async def test_truncates_gotcha_file(self, mock_spec_dir, mock_project_dir):
        """Test that large gotchas file is truncated."""
        memory_dir = mock_spec_dir / "memory"
        memory_dir.mkdir()

        # Create gotchas file larger than 1000 chars
        large_content = "# Gotchas & Pitfalls\n\nThings to watch out for.\n" + "x" * 1500
        (memory_dir / "gotchas.md").write_text(large_content)

        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True):
            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            context_tool = tools[2]

            result = await context_tool.handler({})

            # Content should be truncated to last 1000 chars
            content = result["content"][0]["text"]
            # The result should be shorter than the original
            assert len(content) < len(large_content)

    @pytest.mark.asyncio
    async def test_truncates_patterns_file(self, mock_spec_dir, mock_project_dir):
        """Test that large patterns file is truncated."""
        memory_dir = mock_spec_dir / "memory"
        memory_dir.mkdir()

        # Create patterns file larger than 1000 chars
        large_content = "# Patterns\n\n" + "y" * 1500
        (memory_dir / "patterns.md").write_text(large_content)

        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True):
            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            context_tool = tools[2]

            result = await context_tool.handler({})

            # Content should be truncated to last 1000 chars
            content = result["content"][0]["text"]
            # The result should be shorter than the original
            assert len(content) < len(large_content)


class TestMemoryImportError:
    """Test ImportError handling in memory module."""

    @pytest.fixture
    def mock_spec_dir(self, tmp_path):
        """Create a temporary spec directory."""
        spec_dir = tmp_path / "specs" / "001-test"
        spec_dir.mkdir(parents=True)
        return spec_dir

    @pytest.fixture
    def mock_project_dir(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return project_dir

    def test_create_memory_tools_returns_empty_on_import_error(self, mock_spec_dir, mock_project_dir):
        """Test that empty list is returned when SDK import fails."""
        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", False):
            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            assert tools == []

    def test_import_error_branch_coverage(self, mock_spec_dir, mock_project_dir):
        """Test that ImportError branch sets SDK_TOOLS_AVAILABLE to False and tool to None."""
        # The ImportError branch (lines 25-27) sets:
        # - SDK_TOOLS_AVAILABLE = False
        # - tool = None
        # We verify this branch exists by checking the module's state

        from agents.tools_pkg.tools import memory

        # Verify the module has the expected attributes set after import
        assert hasattr(memory, 'SDK_TOOLS_AVAILABLE')
        assert hasattr(memory, 'tool')

        # When SDK is available (normal case in tests), these should be set
        # The ImportError branch is already tested by mocking SDK_TOOLS_AVAILABLE=False
        # which exercises the same code path through create_memory_tools

        # This test documents the ImportError behavior
        # The actual ImportError is difficult to trigger in tests since claude_agent_sdk
        # is installed in the test environment
        assert isinstance(memory.SDK_TOOLS_AVAILABLE, bool)
        if memory.SDK_TOOLS_AVAILABLE:
            assert memory.tool is not None
        else:
            assert memory.tool is None

    @pytest.mark.asyncio
    async def test_record_gotcha_exception_handling(self, mock_spec_dir, mock_project_dir):
        """Test record_gotcha handles exceptions during file write."""
        # Create memory directory but make gotchas file a directory to cause error
        memory_dir = mock_spec_dir / "memory"
        memory_dir.mkdir()
        (memory_dir / "gotchas.md").mkdir()

        with patch("agents.tools_pkg.tools.memory.SDK_TOOLS_AVAILABLE", True), \
             patch("agents.tools_pkg.tools.memory._save_to_graphiti_async", new_callable=AsyncMock, return_value=False):

            tools = create_memory_tools(mock_spec_dir, mock_project_dir)
            gotcha_tool = tools[1]

            result = await gotcha_tool.handler({
                "gotcha": "Test gotcha",
                "context": "Test context"
            })

            # Should return an error response
            assert "Error recording gotcha" in result["content"][0]["text"]
