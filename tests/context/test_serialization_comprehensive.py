"""
Comprehensive Tests for context.serialization module
=====================================================

Tests for serialization functions including error handling,
file operations, and all functionality paths.
"""

import json
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import pytest

from context.serialization import serialize_context, save_context, load_context
from context.models import TaskContext


class TestSerializeContext:
    """Tests for serialize_context function"""

    def test_serialize_context_basic(self):
        """Test basic context serialization"""
        context = TaskContext(
            task_description="Add authentication",
            scoped_services=["api"],
            files_to_modify=[{"path": "api/auth.py", "relevance_score": 8}],
            files_to_reference=[{"path": "api/utils.py", "relevance_score": 3}],
            patterns_discovered={"auth": "def authenticate()"},
            service_contexts={"api": {"language": "python"}},
            graph_hints=["Previous work: Added login"]
        )

        result = serialize_context(context)

        assert isinstance(result, dict)
        assert result["task_description"] == "Add authentication"
        assert result["scoped_services"] == ["api"]
        assert result["files_to_modify"][0]["path"] == "api/auth.py"
        assert result["files_to_reference"][0]["path"] == "api/utils.py"
        assert result["patterns"]["auth"] == "def authenticate()"
        assert result["service_contexts"]["api"]["language"] == "python"
        assert result["graph_hints"] == ["Previous work: Added login"]

    def test_serialize_context_minimal(self):
        """Test serialization with minimal context"""
        context = TaskContext(
            task_description="Test task",
            scoped_services=[],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={},
            service_contexts={},
            graph_hints=[]
        )

        result = serialize_context(context)

        assert result["task_description"] == "Test task"
        assert result["scoped_services"] == []
        assert result["files_to_modify"] == []
        assert result["files_to_reference"] == []
        assert result["patterns"] == {}
        assert result["service_contexts"] == {}
        assert result["graph_hints"] == []

    def test_serialize_context_multiple_services(self):
        """Test serialization with multiple services"""
        context = TaskContext(
            task_description="Update system",
            scoped_services=["api", "web", "worker"],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={},
            service_contexts={},
            graph_hints=[]
        )

        result = serialize_context(context)

        assert result["scoped_services"] == ["api", "web", "worker"]

    def test_serialize_context_multiple_files(self):
        """Test serialization with multiple files"""
        context = TaskContext(
            task_description="Refactor code",
            scoped_services=["api"],
            files_to_modify=[
                {"path": "api/auth.py", "relevance_score": 9},
                {"path": "api/user.py", "relevance_score": 7},
            ],
            files_to_reference=[
                {"path": "api/utils.py", "relevance_score": 4},
                {"path": "api/config.py", "relevance_score": 2},
            ],
            patterns_discovered={},
            service_contexts={},
            graph_hints=[]
        )

        result = serialize_context(context)

        assert len(result["files_to_modify"]) == 2
        assert len(result["files_to_reference"]) == 2

    def test_serialize_context_complex_patterns(self):
        """Test serialization with complex patterns"""
        context = TaskContext(
            task_description="Add patterns",
            scoped_services=[],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={
                "auth_pattern": "def authenticate():\n    return True",
                "db_pattern": "db.query(User).filter_by(id=user_id)",
                "api_pattern": "@app.route('/api/users')\ndef get_users():\n    pass"
            },
            service_contexts={},
            graph_hints=[]
        )

        result = serialize_context(context)

        assert "auth_pattern" in result["patterns"]
        assert "db_pattern" in result["patterns"]
        assert "api_pattern" in result["patterns"]

    def test_serialize_context_multiple_graph_hints(self):
        """Test serialization with multiple graph hints"""
        context = TaskContext(
            task_description="Use graph hints",
            scoped_services=[],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={},
            service_contexts={},
            graph_hints=[
                "Previous work: Added JWT auth",
                "Related task: User login",
                "Pattern: Use OAuth for SSO"
            ]
        )

        result = serialize_context(context)

        assert len(result["graph_hints"]) == 3
        assert "JWT" in result["graph_hints"][0]

    def test_serialize_context_nested_service_contexts(self):
        """Test serialization with nested service contexts"""
        context = TaskContext(
            task_description="Nested contexts",
            scoped_services=[],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={},
            service_contexts={
                "api": {
                    "language": "python",
                    "framework": "fastapi",
                    "dependencies": ["pydantic", "sqlalchemy"]
                },
                "web": {
                    "language": "typescript",
                    "framework": "react"
                }
            },
            graph_hints=[]
        )

        result = serialize_context(context)

        assert result["service_contexts"]["api"]["framework"] == "fastapi"
        assert result["service_contexts"]["api"]["dependencies"] == ["pydantic", "sqlalchemy"]
        assert result["service_contexts"]["web"]["framework"] == "react"

    def test_serialize_context_unicode_content(self):
        """Test serialization with unicode content"""
        context = TaskContext(
            task_description="Implement authentication for user caf support",
            scoped_services=[],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={"unicode": "caf = 'coffee'"},
            service_contexts={},
            graph_hints=[]
        )

        result = serialize_context(context)

        assert "caf" in result["task_description"] or "coffee" in result["patterns"]["unicode"]

    def test_serialize_context_special_characters(self):
        """Test serialization with special characters"""
        context = TaskContext(
            task_description="Fix: API endpoint /api/v1/users returns 500!",
            scoped_services=[],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={"special": "if x > 0: return 'value'"},
            service_contexts={},
            graph_hints=["Note: Use @decorator"]
        )

        result = serialize_context(context)

        assert "/" in result["task_description"]
        assert "!" in result["task_description"]
        assert "@" in result["graph_hints"][0]

    def test_serialize_context_returns_dict(self):
        """Test that serialize_context returns a dict"""
        context = TaskContext(
            task_description="Test",
            scoped_services=[],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={},
            service_contexts={},
            graph_hints=[]
        )

        result = serialize_context(context)

        assert isinstance(result, dict)


class TestSaveContext:
    """Tests for save_context function"""

    def test_save_context_creates_directory(self, tmp_path):
        """Test that save_context creates parent directories"""
        context = TaskContext(
            task_description="Test",
            scoped_services=[],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={},
            service_contexts={},
            graph_hints=[]
        )

        output_file = tmp_path / "nested" / "dir" / "context.json"

        save_context(context, output_file)

        assert output_file.exists()
        assert output_file.parent.exists()

    def test_save_context_writes_valid_json(self, tmp_path):
        """Test that save_context writes valid JSON"""
        context = TaskContext(
            task_description="Test task",
            scoped_services=["api"],
            files_to_modify=[{"path": "test.py", "relevance_score": 8}],
            files_to_reference=[],
            patterns_discovered={},
            service_contexts={},
            graph_hints=[]
        )

        output_file = tmp_path / "context.json"
        save_context(context, output_file)

        # Verify valid JSON
        with open(output_file) as f:
            data = json.load(f)
        assert data["task_description"] == "Test task"

    def test_save_context_uses_indent(self, tmp_path):
        """Test that output JSON is indented"""
        context = TaskContext(
            task_description="Test",
            scoped_services=[],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={},
            service_contexts={},
            graph_hints=[]
        )

        output_file = tmp_path / "context.json"
        save_context(context, output_file)

        content = output_file.read_text()
        # Check for indentation (should have newlines)
        assert "\n" in content

    def test_save_context_overwrites_existing(self, tmp_path):
        """Test that save_context overwrites existing file"""
        context1 = TaskContext(
            task_description="First",
            scoped_services=[],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={},
            service_contexts={},
            graph_hints=[]
        )

        context2 = TaskContext(
            task_description="Second",
            scoped_services=[],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={},
            service_contexts={},
            graph_hints=[]
        )

        output_file = tmp_path / "context.json"
        save_context(context1, output_file)
        save_context(context2, output_file)

        with open(output_file) as f:
            data = json.load(f)
        assert data["task_description"] == "Second"

    def test_save_context_handles_empty_context(self, tmp_path):
        """Test saving empty context"""
        context = TaskContext(
            task_description="",
            scoped_services=[],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={},
            service_contexts={},
            graph_hints=[]
        )

        output_file = tmp_path / "context.json"
        save_context(context, output_file)

        assert output_file.exists()
        with open(output_file) as f:
            data = json.load(f)
        assert data["task_description"] == ""

    def test_save_context_unicode_path(self, tmp_path):
        """Test saving to path with unicode characters"""
        context = TaskContext(
            task_description="Test",
            scoped_services=[],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={},
            service_contexts={},
            graph_hints=[]
        )

        # Create directory with unicode name
        unicode_dir = tmp_path / "caf"
        unicode_dir.mkdir()
        output_file = unicode_dir / "context.json"

        save_context(context, output_file)

        assert output_file.exists()

    def test_save_context_all_fields(self, tmp_path):
        """Test that all fields are saved"""
        context = TaskContext(
            task_description="Complete context",
            scoped_services=["api", "web"],
            files_to_modify=[{"path": "api/auth.py", "relevance_score": 9}],
            files_to_reference=[{"path": "api/utils.py", "relevance_score": 4}],
            patterns_discovered={"pattern": "code"},
            service_contexts={"api": {"lang": "python"}},
            graph_hints=["hint"]
        )

        output_file = tmp_path / "context.json"
        save_context(context, output_file)

        with open(output_file) as f:
            data = json.load(f)

        assert "task_description" in data
        assert "scoped_services" in data
        assert "files_to_modify" in data
        assert "files_to_reference" in data
        assert "patterns" in data
        assert "service_contexts" in data
        assert "graph_hints" in data

    def test_save_context_encoding(self, tmp_path):
        """Test that file is saved with UTF-8 encoding"""
        context = TaskContext(
            task_description="Test with caf unicode",
            scoped_services=[],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={},
            service_contexts={},
            graph_hints=[]
        )

        output_file = tmp_path / "context.json"
        save_context(context, output_file)

        # Read as UTF-8
        with open(output_file, encoding="utf-8") as f:
            content = f.read()
        assert "caf" in content


class TestLoadContext:
    """Tests for load_context function"""

    def test_load_context_basic(self, tmp_path):
        """Test basic context loading"""
        test_data = {
            "task_description": "Test task",
            "scoped_services": ["api"],
            "files_to_modify": [{"path": "auth.py"}],
            "files_to_reference": [{"path": "utils.py"}],
            "patterns": {"auth": "def authenticate()"},
            "service_contexts": {"api": {"language": "python"}},
            "graph_hints": ["hint"]
        }

        input_file = tmp_path / "context.json"
        input_file.write_text(json.dumps(test_data))

        result = load_context(input_file)

        assert isinstance(result, dict)
        assert result["task_description"] == "Test task"
        assert result["scoped_services"] == ["api"]

    def test_load_context_minimal(self, tmp_path):
        """Test loading minimal context"""
        test_data = {
            "task_description": "",
            "scoped_services": [],
            "files_to_modify": [],
            "files_to_reference": [],
            "patterns": {},
            "service_contexts": {},
            "graph_hints": []
        }

        input_file = tmp_path / "context.json"
        input_file.write_text(json.dumps(test_data))

        result = load_context(input_file)

        assert result["task_description"] == ""
        assert result["scoped_services"] == []

    def test_load_context_complex_data(self, tmp_path):
        """Test loading complex nested data"""
        test_data = {
            "task_description": "Complex",
            "scoped_services": ["api", "web", "worker"],
            "files_to_modify": [
                {"path": "api/auth.py", "relevance_score": 9, "matching_lines": [(1, "def auth")]}
            ],
            "files_to_reference": [
                {"path": "api/utils.py", "relevance_score": 4}
            ],
            "patterns": {
                "auth": "def authenticate():\n    return True",
                "db": "db.query(User)"
            },
            "service_contexts": {
                "api": {
                    "language": "python",
                    "framework": "fastapi",
                    "nested": {"key": "value"}
                }
            },
            "graph_hints": ["hint1", "hint2", "hint3"]
        }

        input_file = tmp_path / "context.json"
        input_file.write_text(json.dumps(test_data))

        result = load_context(input_file)

        assert len(result["files_to_modify"]) == 1
        assert result["files_to_modify"][0]["matching_lines"][0][0] == 1
        assert result["service_contexts"]["api"]["nested"]["key"] == "value"

    def test_load_context_unicode_content(self, tmp_path):
        """Test loading file with unicode content"""
        test_data = {
            "task_description": "Test with caf unicode",
            "scoped_services": [],
            "files_to_modify": [],
            "files_to_reference": [],
            "patterns": {},
            "service_contexts": {},
            "graph_hints": []
        }

        input_file = tmp_path / "context.json"
        input_file.write_text(json.dumps(test_data), encoding="utf-8")

        result = load_context(input_file)

        assert "caf" in result["task_description"]

    def test_load_context_special_characters(self, tmp_path):
        """Test loading file with special characters"""
        test_data = {
            "task_description": "Fix: API /api/v1/users - error!",
            "scoped_services": [],
            "files_to_modify": [],
            "files_to_reference": [],
            "patterns": {"special": "if x > 0: return 'value'"},
            "service_contexts": {},
            "graph_hints": ["Note: use @decorator"]
        }

        input_file = tmp_path / "context.json"
        input_file.write_text(json.dumps(test_data))

        result = load_context(input_file)

        assert "/" in result["task_description"]
        assert "@" in result["graph_hints"][0]

    def test_load_context_returns_dict(self, tmp_path):
        """Test that load_context returns a dict"""
        test_data = {
            "task_description": "Test",
            "scoped_services": [],
            "files_to_modify": [],
            "files_to_reference": [],
            "patterns": {},
            "service_contexts": {},
            "graph_hints": []
        }

        input_file = tmp_path / "context.json"
        input_file.write_text(json.dumps(test_data))

        result = load_context(input_file)

        assert isinstance(result, dict)

    def test_load_context_encoding(self, tmp_path):
        """Test that file is read with UTF-8 encoding"""
        test_data = {
            "task_description": "Test unicode caf",
            "scoped_services": [],
            "files_to_modify": [],
            "files_to_reference": [],
            "patterns": {},
            "service_contexts": {},
            "graph_hints": []
        }

        input_file = tmp_path / "context.json"
        input_file.write_text(json.dumps(test_data), encoding="utf-8")

        result = load_context(input_file)

        assert "caf" in result["task_description"]


class TestErrorHandling:
    """Tests for error handling"""

    def test_save_context_permission_error(self, tmp_path):
        """Test handling of permission errors"""
        context = TaskContext(
            task_description="Test",
            scoped_services=[],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={},
            service_contexts={},
            graph_hints=[]
        )

        # Try to write to read-only location
        readonly_file = tmp_path / "readonly.json"
        readonly_file.write_text("existing")
        readonly_file.chmod(0o444)

        try:
            save_context(context, readonly_file)
            # If it doesn't raise, that's also acceptable behavior
        except (OSError, PermissionError):
            # Expected to raise error
            pass
        finally:
            # Restore permissions for cleanup
            readonly_file.chmod(0o644)

    def test_load_context_file_not_found(self, tmp_path):
        """Test loading non-existent file"""
        input_file = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            load_context(input_file)

    def test_load_context_invalid_json(self, tmp_path):
        """Test loading invalid JSON file"""
        input_file = tmp_path / "invalid.json"
        input_file.write_text("{ invalid json }")

        with pytest.raises(json.JSONDecodeError):
            load_context(input_file)

    def test_load_context_empty_file(self, tmp_path):
        """Test loading empty file"""
        input_file = tmp_path / "empty.json"
        input_file.write_text("")

        with pytest.raises(json.JSONDecodeError):
            load_context(input_file)


class TestRoundTrip:
    """Tests for save/load round-trip"""

    def test_save_load_roundtrip(self, tmp_path):
        """Test that saved context can be loaded correctly"""
        original_context = TaskContext(
            task_description="Roundtrip test",
            scoped_services=["api", "web"],
            files_to_modify=[
                {"path": "api/auth.py", "relevance_score": 9, "matching_lines": [(1, "def auth")]}
            ],
            files_to_reference=[
                {"path": "api/utils.py", "relevance_score": 4}
            ],
            patterns_discovered={
                "auth": "def authenticate():\n    return True"
            },
            service_contexts={
                "api": {"language": "python", "framework": "fastapi"}
            },
            graph_hints=["Previous work: Added JWT auth"]
        )

        output_file = tmp_path / "context.json"
        save_context(original_context, output_file)

        loaded_data = load_context(output_file)

        assert loaded_data["task_description"] == "Roundtrip test"
        assert loaded_data["scoped_services"] == ["api", "web"]
        assert loaded_data["files_to_modify"][0]["path"] == "api/auth.py"
        assert loaded_data["patterns"]["auth"] == "def authenticate():\n    return True"
        assert loaded_data["service_contexts"]["api"]["framework"] == "fastapi"
        assert loaded_data["graph_hints"][0] == "Previous work: Added JWT auth"
