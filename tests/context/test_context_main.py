"""
Tests for context.main module
==============================

Comprehensive tests for the build_task_context() CLI entry point and
main() function that handle task context building from command-line.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock, call
import argparse

import pytest


class TestBuildTaskContext:
    """Tests for build_task_context() function"""

    def test_build_task_context_basic(self, tmp_path):
        """Test basic task context building without output file"""
        from context.main import build_task_context
        from context.models import FileMatch, TaskContext

        # Create a test service directory
        service_dir = tmp_path / "api"
        service_dir.mkdir(parents=True)
        (service_dir / "auth.py").write_text(
            "def authenticate(username, password):\n"
            "    return True\n"
        )

        # Mock the ContextBuilder
        mock_context = TaskContext(
            task_description="Add authentication",
            scoped_services=["api"],
            files_to_modify=[],
            files_to_reference=[],
            patterns_discovered={},
            service_contexts={"api": {"source": "generated"}},
        )

        with patch('context.main.ContextBuilder') as MockBuilder:
            mock_builder = MagicMock()
            mock_builder.build_context.return_value = mock_context
            MockBuilder.return_value = mock_builder

            with patch('context.main.serialize_context') as mock_serialize:
                mock_serialize.return_value = {
                    "task_description": "Add authentication",
                    "scoped_services": ["api"],
                    "files_to_modify": [],
                    "files_to_reference": [],
                    "patterns": {},
                    "service_contexts": {"api": {"source": "generated"}},
                    "graph_hints": [],
                }

                result = build_task_context(
                    project_dir=tmp_path,
                    task="Add authentication",
                )

                # Verify ContextBuilder was initialized correctly
                MockBuilder.assert_called_once_with(tmp_path)

                # Verify build_context was called
                mock_builder.build_context.assert_called_once_with(
                    "Add authentication", None, None
                )

                # Verify serialization was called
                mock_serialize.assert_called_once_with(mock_context)

                # Verify result
                assert result["task_description"] == "Add authentication"
                assert result["scoped_services"] == ["api"]

    def test_build_task_context_with_services(self, tmp_path):
        """Test task context building with explicit services"""
        from context.main import build_task_context

        with patch('context.main.ContextBuilder') as MockBuilder:
            mock_builder = MagicMock()
            mock_builder.build_context.return_value = MagicMock(
                task_description="Add user auth",
                scoped_services=["backend", "auth-service"],
                files_to_modify=[],
                files_to_reference=[],
                patterns_discovered={},
                service_contexts={},
                graph_hints=[],
            )
            MockBuilder.return_value = mock_builder

            with patch('context.main.serialize_context') as mock_serialize:
                mock_serialize.return_value = {"task_description": "Add user auth"}

                build_task_context(
                    project_dir=tmp_path,
                    task="Add user auth",
                    services=["backend", "auth-service"],
                )

                # Verify services were passed correctly
                mock_builder.build_context.assert_called_once_with(
                    "Add user auth", ["backend", "auth-service"], None
                )

    def test_build_task_context_with_keywords(self, tmp_path):
        """Test task context building with explicit keywords"""
        from context.main import build_task_context

        with patch('context.main.ContextBuilder') as MockBuilder:
            mock_builder = MagicMock()
            mock_builder.build_context.return_value = MagicMock(
                task_description="Add retry logic",
                scoped_services=["scraper"],
                files_to_modify=[],
                files_to_reference=[],
                patterns_discovered={},
                service_contexts={},
                graph_hints=[],
            )
            MockBuilder.return_value = mock_builder

            with patch('context.main.serialize_context') as mock_serialize:
                mock_serialize.return_value = {"task_description": "Add retry logic"}

                build_task_context(
                    project_dir=tmp_path,
                    task="Add retry logic",
                    keywords=["retry", "error", "proxy"],
                )

                # Verify keywords were passed correctly
                mock_builder.build_context.assert_called_once_with(
                    "Add retry logic", None, ["retry", "error", "proxy"]
                )

    def test_build_task_context_with_output_file(self, tmp_path):
        """Test task context building with output file"""
        from context.main import build_task_context

        output_file = tmp_path / "output" / "context.json"

        with patch('context.main.ContextBuilder') as MockBuilder:
            mock_builder = MagicMock()
            mock_builder.build_context.return_value = MagicMock(
                task_description="Test task",
                scoped_services=["api"],
                files_to_modify=[],
                files_to_reference=[],
                patterns_discovered={},
                service_contexts={},
                graph_hints=[],
            )
            MockBuilder.return_value = mock_builder

            expected_result = {
                "task_description": "Test task",
                "scoped_services": ["api"],
                "files_to_modify": [],
                "files_to_reference": [],
                "patterns": {},
                "service_contexts": {},
                "graph_hints": [],
            }

            with patch('context.main.serialize_context') as mock_serialize:
                mock_serialize.return_value = expected_result

                result = build_task_context(
                    project_dir=tmp_path,
                    task="Test task",
                    output_file=output_file,
                )

                # Verify output file was created
                assert output_file.exists()

                # Verify content was written correctly
                with open(output_file, encoding="utf-8") as f:
                    written_data = json.load(f)

                assert written_data == expected_result

                # Verify parent directories were created
                assert output_file.parent.exists()

                # Verify result is returned
                assert result == expected_result

    def test_build_task_context_output_file_unicode(self, tmp_path):
        """Test output file with Unicode content"""
        from context.main import build_task_context

        output_file = tmp_path / "output" / "context.json"

        with patch('context.main.ContextBuilder') as MockBuilder:
            mock_builder = MagicMock()
            mock_builder.build_context.return_value = MagicMock(
                task_description="Add emoji support 😊",
                scoped_services=["ui"],
                files_to_modify=[],
                files_to_reference=[],
                patterns_discovered={"pattern": "Use UTF-8 encoding éàü"},
                service_contexts={"ui": {"content": "French: Bonjour, Spanish: Hola"}},
                graph_hints=[],
            )
            MockBuilder.return_value = mock_builder

            expected_result = {
                "task_description": "Add emoji support 😊",
                "scoped_services": ["ui"],
                "files_to_modify": [],
                "files_to_reference": [],
                "patterns": {"pattern": "Use UTF-8 encoding éàü"},
                "service_contexts": {"ui": {"content": "French: Bonjour, Spanish: Hola"}},
                "graph_hints": [],
            }

            with patch('context.main.serialize_context') as mock_serialize:
                mock_serialize.return_value = expected_result

                build_task_context(
                    project_dir=tmp_path,
                    task="Add emoji support 😊",
                    output_file=output_file,
                )

                # Verify file was written with UTF-8 encoding
                with open(output_file, encoding="utf-8") as f:
                    written_data = json.load(f)

                assert written_data["task_description"] == "Add emoji support 😊"
                assert "éàü" in str(written_data["patterns"])

    def test_build_task_context_all_parameters(self, tmp_path):
        """Test with all parameters provided"""
        from context.main import build_task_context

        output_file = tmp_path / "output.json"

        with patch('context.main.ContextBuilder') as MockBuilder:
            mock_builder = MagicMock()
            mock_builder.build_context.return_value = MagicMock(
                task_description="Full test",
                scoped_services=["svc1", "svc2"],
                files_to_modify=[],
                files_to_reference=[],
                patterns_discovered={},
                service_contexts={},
                graph_hints=[],
            )
            MockBuilder.return_value = mock_builder

            expected_result = {"task_description": "Full test"}

            with patch('context.main.serialize_context') as mock_serialize:
                mock_serialize.return_value = expected_result

                result = build_task_context(
                    project_dir=tmp_path,
                    task="Full test",
                    services=["svc1", "svc2"],
                    keywords=["key1", "key2"],
                    output_file=output_file,
                )

                # Verify all parameters were passed correctly
                mock_builder.build_context.assert_called_once_with(
                    "Full test", ["svc1", "svc2"], ["key1", "key2"]
                )

                # Verify output file was created
                assert output_file.exists()

                # Verify result
                assert result == expected_result

    def test_build_task_context_empty_project(self, tmp_path):
        """Test context building for empty project"""
        from context.main import build_task_context

        # Empty project - no files
        with patch('context.main.ContextBuilder') as MockBuilder:
            mock_builder = MagicMock()
            mock_builder.build_context.return_value = MagicMock(
                task_description="Add feature",
                scoped_services=[],
                files_to_modify=[],
                files_to_reference=[],
                patterns_discovered={},
                service_contexts={},
                graph_hints=[],
            )
            MockBuilder.return_value = mock_builder

            with patch('context.main.serialize_context') as mock_serialize:
                mock_serialize.return_value = {
                    "task_description": "Add feature",
                    "scoped_services": [],
                }

                result = build_task_context(
                    project_dir=tmp_path,
                    task="Add feature",
                )

                assert result["scoped_services"] == []

    def test_build_task_context_with_files_and_patterns(self, tmp_path):
        """Test context building returns files and patterns"""
        from context.main import build_task_context
        from context.models import FileMatch

        with patch('context.main.ContextBuilder') as MockBuilder:
            file_match = FileMatch(
                path="api/auth.py",
                service="api",
                reason="Contains authentication logic",
                relevance_score=0.9,
                matching_lines=[(1, "def authenticate"), (10, "return token")],
            )

            mock_builder = MagicMock()
            mock_builder.build_context.return_value = MagicMock(
                task_description="Add auth",
                scoped_services=["api"],
                files_to_modify=[file_match],
                files_to_reference=[],
                patterns_discovered={"retry": "def retry_wrapper(): pass"},
                service_contexts={"api": {"source": "generated"}},
                graph_hints=[],
            )
            MockBuilder.return_value = mock_builder

            expected_result = {
                "task_description": "Add auth",
                "scoped_services": ["api"],
                "files_to_modify": [
                    {
                        "path": "api/auth.py",
                        "service": "api",
                        "reason": "Contains authentication logic",
                        "relevance_score": 0.9,
                        "matching_lines": [(1, "def authenticate"), (10, "return token")],
                    }
                ],
                "files_to_reference": [],
                "patterns": {"retry": "def retry_wrapper(): pass"},
                "service_contexts": {"api": {"source": "generated"}},
                "graph_hints": [],
            }

            with patch('context.main.serialize_context') as mock_serialize:
                mock_serialize.return_value = expected_result

                result = build_task_context(
                    project_dir=tmp_path,
                    task="Add auth",
                )

                assert len(result["files_to_modify"]) == 1
                assert result["files_to_modify"][0]["relevance_score"] == 0.9
                assert result["patterns"]["retry"] == "def retry_wrapper(): pass"


class TestMainFunction:
    """Tests for main() CLI entry point"""

    def test_main_basic(self, tmp_path, capsys):
        """Test basic main() with minimal arguments"""
        from context.main import main

        with patch('context.main.build_task_context') as mock_build:
            mock_build.return_value = {
                "task_description": "Test task",
                "scoped_services": ["api"],
            }

            # Mock sys.argv to provide arguments
            with patch('sys.argv', [
                'context.py',
                '--task', 'Test task',
                '--project-dir', str(tmp_path),
            ]):
                main()

                # Verify build_task_context was called correctly
                mock_build.assert_called_once()

                # Check positional arguments
                call_args = mock_build.call_args[0]
                assert call_args[0] == tmp_path  # project_dir
                assert call_args[1] == 'Test task'  # task
                assert call_args[2] is None  # services
                assert call_args[3] is None  # keywords
                assert call_args[4] is None  # output_file

                # Verify JSON output was printed
                captured = capsys.readouterr()
                assert 'Test task' in captured.out
                assert 'api' in captured.out

    def test_main_with_services(self, tmp_path, capsys):
        """Test main() with services argument"""
        from context.main import main

        with patch('context.main.build_task_context') as mock_build:
            mock_build.return_value = {"task_description": "Test"}

            with patch('sys.argv', [
                'context.py',
                '--task', 'Test',
                '--project-dir', str(tmp_path),
                '--services', 'backend,frontend,auth',
            ]):
                main()

                call_args = mock_build.call_args[0]
                assert call_args[2] == ['backend', 'frontend', 'auth']

    def test_main_with_keywords(self, tmp_path, capsys):
        """Test main() with keywords argument"""
        from context.main import main

        with patch('context.main.build_task_context') as mock_build:
            mock_build.return_value = {"task_description": "Test"}

            with patch('sys.argv', [
                'context.py',
                '--task', 'Test',
                '--project-dir', str(tmp_path),
                '--keywords', 'retry,error,timeout',
            ]):
                main()

                call_args = mock_build.call_args[0]
                assert call_args[3] == ['retry', 'error', 'timeout']

    def test_main_with_output(self, tmp_path, capsys):
        """Test main() with output file argument"""
        from context.main import main

        output_file = tmp_path / "output.json"

        with patch('context.main.build_task_context') as mock_build:
            mock_build.return_value = {
                "task_description": "Test",
                "result": "data",
            }

            with patch('sys.argv', [
                'context.py',
                '--task', 'Test',
                '--project-dir', str(tmp_path),
                '--output', str(output_file),
            ]):
                main()

                call_args = mock_build.call_args[0]
                assert call_args[4] == output_file

    def test_main_with_quiet(self, tmp_path, capsys):
        """Test main() with quiet flag"""
        from context.main import main

        output_file = tmp_path / "output.json"

        with patch('context.main.build_task_context') as mock_build:
            mock_build.return_value = {"task_description": "Test"}

            with patch('sys.argv', [
                'context.py',
                '--task', 'Test',
                '--project-dir', str(tmp_path),
                '--output', str(output_file),
                '--quiet',
            ]):
                main()

                # With quiet and output, json.dumps in main() is not executed
                # Only the save message from build_task_context is printed
                # The condition is: if not args.quiet or not args.output
                # When quiet=True AND output is set, both are truthy, so print is skipped
                captured = capsys.readouterr()
                # With our mock, build_task_context doesn't actually write the file or print
                # So the output should be empty (no json.dumps from main)
                assert captured.out == ""

    def test_main_quiet_without_output(self, tmp_path, capsys):
        """Test main() with quiet but no output file"""
        from context.main import main

        with patch('context.main.build_task_context') as mock_build:
            mock_build.return_value = {"task_description": "Test"}

            with patch('sys.argv', [
                'context.py',
                '--task', 'Test',
                '--project-dir', str(tmp_path),
                '--quiet',
            ]):
                main()

                # Without output, quiet flag is ignored for JSON output
                captured = capsys.readouterr()
                assert 'Test' in captured.out

    def test_main_with_all_arguments(self, tmp_path, capsys):
        """Test main() with all arguments provided"""
        from context.main import main

        output_file = tmp_path / "result.json"

        with patch('context.main.build_task_context') as mock_build:
            mock_build.return_value = {
                "task_description": "Complete task",
                "scoped_services": ["svc1", "svc2"],
            }

            with patch('sys.argv', [
                'context.py',
                '--project-dir', str(tmp_path),
                '--task', 'Complete task',
                '--services', 'svc1,svc2',
                '--keywords', 'auth,user,login',
                '--output', str(output_file),
                '--quiet',
            ]):
                main()

                call_args = mock_build.call_args[0]
                assert call_args[0] == tmp_path  # project_dir
                assert call_args[1] == 'Complete task'  # task
                assert call_args[2] == ['svc1', 'svc2']  # services
                assert call_args[3] == ['auth', 'user', 'login']  # keywords
                assert call_args[4] == output_file  # output_file

    def test_main_single_service(self, tmp_path, capsys):
        """Test main() with single service (no comma)"""
        from context.main import main

        with patch('context.main.build_task_context') as mock_build:
            mock_build.return_value = {"task_description": "Test"}

            with patch('sys.argv', [
                'context.py',
                '--task', 'Test',
                '--project-dir', str(tmp_path),
                '--services', 'api',
            ]):
                main()

                call_args = mock_build.call_args[0]
                assert call_args[2] == ['api']

    def test_main_single_keyword(self, tmp_path, capsys):
        """Test main() with single keyword (no comma)"""
        from context.main import main

        with patch('context.main.build_task_context') as mock_build:
            mock_build.return_value = {"task_description": "Test"}

            with patch('sys.argv', [
                'context.py',
                '--task', 'Test',
                '--project-dir', str(tmp_path),
                '--keywords', 'auth',
            ]):
                main()

                call_args = mock_build.call_args[0]
                assert call_args[3] == ['auth']

    def test_main_empty_services_string(self, tmp_path, capsys):
        """Test main() with empty services string"""
        from context.main import main

        with patch('context.main.build_task_context') as mock_build:
            mock_build.return_value = {"task_description": "Test"}

            with patch('sys.argv', [
                'context.py',
                '--task', 'Test',
                '--project-dir', str(tmp_path),
                '--services', '',
            ]):
                main()

                call_args = mock_build.call_args[0]
                # Empty string is falsy in the conditional, so it becomes None
                # "".split(",") if args.services else None
                # Empty string "" is falsy, so the result is None
                assert call_args[2] is None

    def test_main_default_project_dir(self, tmp_path, capsys):
        """Test main() uses current directory as default project-dir"""
        from context.main import main

        with patch('context.main.build_task_context') as mock_build:
            mock_build.return_value = {"task_description": "Test"}

            with patch('sys.argv', [
                'context.py',
                '--task', 'Test',
            ]):
                with patch('pathlib.Path.cwd', return_value=tmp_path):
                    main()

                    call_args = mock_build.call_args[0]
                    # Should default to current working directory
                    assert call_args[0] == tmp_path


class TestMainIntegration:
    """Integration tests for main module behavior"""

    def test_print_output_format(self, tmp_path, capsys):
        """Test that JSON output is properly formatted"""
        from context.main import build_task_context

        with patch('context.main.ContextBuilder') as MockBuilder:
            mock_builder = MagicMock()
            mock_builder.build_context.return_value = MagicMock(
                task_description="Format test",
                scoped_services=["api"],
                files_to_modify=[],
                files_to_reference=[],
                patterns_discovered={},
                service_contexts={},
                graph_hints=[],
            )
            MockBuilder.return_value = mock_builder

            result = {
                "task_description": "Format test",
                "scoped_services": ["api"],
            }

            with patch('context.main.serialize_context') as mock_serialize:
                mock_serialize.return_value = result

                # Call build_task_context and print result
                result = build_task_context(
                    project_dir=tmp_path,
                    task="Format test",
                )

                # Print as the module would
                import json
                printed = json.dumps(result, indent=2)
                assert printed == '{\n  "task_description": "Format test",\n  "scoped_services": [\n    "api"\n  ]\n}'

    def test_save_message_format(self, tmp_path, capsys):
        """Test that save message includes full file path"""
        from context.main import build_task_context

        output_file = tmp_path / "subdir" / "context.json"

        with patch('context.main.ContextBuilder') as MockBuilder:
            mock_builder = MagicMock()
            mock_builder.build_context.return_value = MagicMock(
                task_description="Test",
                scoped_services=[],
                files_to_modify=[],
                files_to_reference=[],
                patterns_discovered={},
                service_contexts={},
                graph_hints=[],
            )
            MockBuilder.return_value = mock_builder

            with patch('context.main.serialize_context') as mock_serialize:
                mock_serialize.return_value = {}

                build_task_context(
                    project_dir=tmp_path,
                    task="Test",
                    output_file=output_file,
                )

                captured = capsys.readouterr()
                assert str(output_file) in captured.out
                assert 'saved to' in captured.out.lower()

    def test_nested_directory_creation(self, tmp_path):
        """Test that nested directories are created for output file"""
        from context.main import build_task_context

        # Create deeply nested output path
        output_file = tmp_path / "a" / "b" / "c" / "d" / "context.json"

        with patch('context.main.ContextBuilder') as MockBuilder:
            mock_builder = MagicMock()
            mock_builder.build_context.return_value = MagicMock(
                task_description="Test",
                scoped_services=[],
                files_to_modify=[],
                files_to_reference=[],
                patterns_discovered={},
                service_contexts={},
                graph_hints=[],
            )
            MockBuilder.return_value = mock_builder

            with patch('context.main.serialize_context') as mock_serialize:
                mock_serialize.return_value = {}

                build_task_context(
                    project_dir=tmp_path,
                    task="Test",
                    output_file=output_file,
                )

                # Verify all parent directories were created
                assert output_file.exists()
                assert (tmp_path / "a" / "b" / "c" / "d").exists()


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_none_services_parameter(self, tmp_path):
        """Test with None services parameter"""
        from context.main import build_task_context

        with patch('context.main.ContextBuilder') as MockBuilder:
            mock_builder = MagicMock()
            mock_builder.build_context.return_value = MagicMock(
                task_description="Test",
                scoped_services=[],
                files_to_modify=[],
                files_to_reference=[],
                patterns_discovered={},
                service_contexts={},
                graph_hints=[],
            )
            MockBuilder.return_value = mock_builder

            with patch('context.main.serialize_context') as mock_serialize:
                mock_serialize.return_value = {}

                build_task_context(
                    project_dir=tmp_path,
                    task="Test",
                    services=None,
                )

                mock_builder.build_context.assert_called_once_with("Test", None, None)

    def test_none_keywords_parameter(self, tmp_path):
        """Test with None keywords parameter"""
        from context.main import build_task_context

        with patch('context.main.ContextBuilder') as MockBuilder:
            mock_builder = MagicMock()
            mock_builder.build_context.return_value = MagicMock(
                task_description="Test",
                scoped_services=[],
                files_to_modify=[],
                files_to_reference=[],
                patterns_discovered={},
                service_contexts={},
                graph_hints=[],
            )
            MockBuilder.return_value = mock_builder

            with patch('context.main.serialize_context') as mock_serialize:
                mock_serialize.return_value = {}

                build_task_context(
                    project_dir=tmp_path,
                    task="Test",
                    keywords=None,
                )

                mock_builder.build_context.assert_called_once_with("Test", None, None)

    def test_none_output_file_parameter(self, tmp_path):
        """Test with None output_file parameter"""
        from context.main import build_task_context

        with patch('context.main.ContextBuilder') as MockBuilder:
            mock_builder = MagicMock()
            mock_builder.build_context.return_value = MagicMock(
                task_description="Test",
                scoped_services=[],
                files_to_modify=[],
                files_to_reference=[],
                patterns_discovered={},
                service_contexts={},
                graph_hints=[],
            )
            MockBuilder.return_value = mock_builder

            with patch('context.main.serialize_context') as mock_serialize:
                mock_serialize.return_value = {}

                build_task_context(
                    project_dir=tmp_path,
                    task="Test",
                    output_file=None,
                )

                # No file should be created
                assert not (tmp_path / "context.json").exists()

    def test_empty_services_list(self, tmp_path):
        """Test with empty services list"""
        from context.main import build_task_context

        with patch('context.main.ContextBuilder') as MockBuilder:
            mock_builder = MagicMock()
            mock_builder.build_context.return_value = MagicMock(
                task_description="Test",
                scoped_services=[],
                files_to_modify=[],
                files_to_reference=[],
                patterns_discovered={},
                service_contexts={},
                graph_hints=[],
            )
            MockBuilder.return_value = mock_builder

            with patch('context.main.serialize_context') as mock_serialize:
                mock_serialize.return_value = {}

                build_task_context(
                    project_dir=tmp_path,
                    task="Test",
                    services=[],
                )

                mock_builder.build_context.assert_called_once_with("Test", [], None)

    def test_empty_keywords_list(self, tmp_path):
        """Test with empty keywords list"""
        from context.main import build_task_context

        with patch('context.main.ContextBuilder') as MockBuilder:
            mock_builder = MagicMock()
            mock_builder.build_context.return_value = MagicMock(
                task_description="Test",
                scoped_services=[],
                files_to_modify=[],
                files_to_reference=[],
                patterns_discovered={},
                service_contexts={},
                graph_hints=[],
            )
            MockBuilder.return_value = mock_builder

            with patch('context.main.serialize_context') as mock_serialize:
                mock_serialize.return_value = {}

                build_task_context(
                    project_dir=tmp_path,
                    task="Test",
                    keywords=[],
                )

                mock_builder.build_context.assert_called_once_with("Test", None, [])

    def test_special_characters_in_task(self, tmp_path):
        """Test with special characters in task description"""
        from context.main import build_task_context

        special_task = "Fix bug: Can't login with email@domain.com"

        with patch('context.main.ContextBuilder') as MockBuilder:
            mock_builder = MagicMock()
            mock_builder.build_context.return_value = MagicMock(
                task_description=special_task,
                scoped_services=[],
                files_to_modify=[],
                files_to_reference=[],
                patterns_discovered={},
                service_contexts={},
                graph_hints=[],
            )
            MockBuilder.return_value = mock_builder

            with patch('context.main.serialize_context') as mock_serialize:
                mock_serialize.return_value = {"task_description": special_task}

                result = build_task_context(
                    project_dir=tmp_path,
                    task=special_task,
                )

                assert result["task_description"] == special_task

    def test_long_task_description(self, tmp_path):
        """Test with very long task description"""
        from context.main import build_task_context

        long_task = "Add feature " + "with details " * 50

        with patch('context.main.ContextBuilder') as MockBuilder:
            mock_builder = MagicMock()
            mock_builder.build_context.return_value = MagicMock(
                task_description=long_task,
                scoped_services=[],
                files_to_modify=[],
                files_to_reference=[],
                patterns_discovered={},
                service_contexts={},
                graph_hints=[],
            )
            MockBuilder.return_value = mock_builder

            with patch('context.main.serialize_context') as mock_serialize:
                mock_serialize.return_value = {"task_description": long_task}

                result = build_task_context(
                    project_dir=tmp_path,
                    task=long_task,
                )

                assert result["task_description"] == long_task

    def test_context_with_graph_hints(self, tmp_path):
        """Test context building with graph hints"""
        from context.main import build_task_context

        with patch('context.main.ContextBuilder') as MockBuilder:
            mock_builder = MagicMock()
            mock_builder.build_context.return_value = MagicMock(
                task_description="Test",
                scoped_services=[],
                files_to_modify=[],
                files_to_reference=[],
                patterns_discovered={},
                service_contexts={},
                graph_hints=[
                    {"type": "previous_work", "content": "Added login feature"},
                    {"type": "suggestion", "content": "Use existing auth service"},
                ],
            )
            MockBuilder.return_value = mock_builder

            expected_result = {
                "task_description": "Test",
                "graph_hints": [
                    {"type": "previous_work", "content": "Added login feature"},
                    {"type": "suggestion", "content": "Use existing auth service"},
                ],
            }

            with patch('context.main.serialize_context') as mock_serialize:
                mock_serialize.return_value = expected_result

                result = build_task_context(
                    project_dir=tmp_path,
                    task="Test",
                )

                assert len(result["graph_hints"]) == 2
                assert result["graph_hints"][0]["type"] == "previous_work"


class TestModuleExports:
    """Tests for module exports"""

    def test_module_exports(self):
        """Test that main module exports expected symbols"""
        import context.main

        expected_exports = [
            "ContextBuilder",
            "FileMatch",
            "TaskContext",
            "build_task_context",
        ]

        for export in expected_exports:
            assert export in context.main.__all__

    def test_all_list_is_complete(self):
        """Test that __all__ contains all expected exports"""
        import context.main

        assert len(context.main.__all__) == 4
        assert "build_task_context" in context.main.__all__
        assert "ContextBuilder" in context.main.__all__
        assert "FileMatch" in context.main.__all__
        assert "TaskContext" in context.main.__all__
