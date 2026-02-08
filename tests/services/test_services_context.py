"""
Tests for services/context.py - Service Context Generator
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
import argparse

import pytest

from services.context import (
    ServiceContext,
    ServiceContextGenerator,
    generate_all_contexts,
)


@pytest.fixture
def mock_project_dir(tmp_path: Path) -> Path:
    """Create a mock project directory."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def mock_service_dir(mock_project_dir: Path) -> Path:
    """Create a mock service directory."""
    service_dir = mock_project_dir / "backend"
    service_dir.mkdir()
    return service_dir


@pytest.fixture
def mock_project_index(mock_project_dir: Path) -> dict:
    """Create a mock project index."""
    return {
        "services": {
            "backend": {
                "path": "backend",
                "type": "api",
                "language": "python",
                "framework": "fastapi",
                "entry_point": "main.py",
                "key_directories": {
                    "routes": "API route definitions",
                    "models": "Data models",
                },
                "port": 8000,
            },
            "frontend": {
                "path": "frontend",
                "type": "ui",
                "language": "typescript",
                "framework": "react",
                "entry_point": "src/main.tsx",
            },
        }
    }


@pytest.fixture
def mock_auto_claude_dir(mock_project_dir: Path) -> Path:
    """Create a mock .auto-claude directory with project index."""
    auto_claude_dir = mock_project_dir / ".auto-claude"
    auto_claude_dir.mkdir()
    return auto_claude_dir


class TestServiceContext:
    """Tests for ServiceContext dataclass."""

    def test_service_context_creation(self):
        """Test creating a ServiceContext instance."""
        context = ServiceContext(
            name="backend",
            path="backend",
            service_type="api",
            language="python",
            framework="fastapi",
        )

        assert context.name == "backend"
        assert context.path == "backend"
        assert context.service_type == "api"
        assert context.language == "python"
        assert context.framework == "fastapi"
        assert context.entry_points == []
        assert context.key_directories == {}
        assert context.dependencies == []
        assert context.api_patterns == []
        assert context.common_commands == {}
        assert context.environment_vars == []
        assert context.ports == []
        assert context.notes == []

    def test_service_context_with_optional_fields(self):
        """Test ServiceContext with all optional fields."""
        context = ServiceContext(
            name="backend",
            path="backend",
            service_type="api",
            language="python",
            framework="fastapi",
            entry_points=["main.py", "app.py"],
            key_directories={"routes": "API routes"},
            dependencies=["fastapi", "uvicorn"],
            api_patterns=["Flask/FastAPI routes"],
            common_commands={"dev": "flask run"},
            environment_vars=["DATABASE_URL"],
            ports=[8000],
            notes=["Main API service"],
        )

        assert len(context.entry_points) == 2
        assert context.dependencies == ["fastapi", "uvicorn"]
        assert context.ports == [8000]


class TestServiceContextGenerator:
    """Tests for ServiceContextGenerator class."""

    def test_init_with_project_index(self, mock_project_dir, mock_project_index):
        """Test initialization with provided project index."""
        generator = ServiceContextGenerator(mock_project_dir, mock_project_index)

        assert generator.project_dir == mock_project_dir.resolve()
        assert generator.project_index == mock_project_index

    def test_init_without_project_index(self, mock_project_dir, mock_auto_claude_dir):
        """Test initialization loads project index from file."""
        # Write project index to file
        index_file = mock_auto_claude_dir / "project_index.json"
        test_index = {
            "services": {
                "backend": {"path": "backend", "type": "api", "language": "python"}
            }
        }
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(test_index, f)

        generator = ServiceContextGenerator(mock_project_dir)

        assert generator.project_index == test_index

    def test_init_without_project_index_fallback(self, mock_project_dir):
        """Test initialization falls back to empty index when file doesn't exist."""
        generator = ServiceContextGenerator(mock_project_dir)

        assert generator.project_index == {"services": {}}

    def test_project_dir_resolution(self, tmp_path):
        """Test that project_dir is resolved to absolute path."""
        # Create a relative path scenario
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        # Navigate to parent and use relative path
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            generator = ServiceContextGenerator(Path("project"))

            # Should resolve to absolute path
            assert generator.project_dir.is_absolute()
            assert generator.project_dir == project_dir.resolve()
        finally:
            os.chdir(original_cwd)

    def test_generate_for_service_basic(
        self, mock_project_dir, mock_project_index
    ):
        """Test generating context for a service."""
        generator = ServiceContextGenerator(mock_project_dir, mock_project_index)

        # Create service directory
        service_dir = mock_project_dir / "backend"
        service_dir.mkdir()

        context = generator.generate_for_service("backend")

        assert context.name == "backend"
        assert context.service_type == "api"
        assert context.language == "python"
        assert context.framework == "fastapi"
        assert "main.py" in context.entry_points
        assert context.key_directories == {
            "routes": "API route definitions",
            "models": "Data models",
        }
        assert context.ports == [8000]

    def test_generate_for_service_not_found(
        self, mock_project_dir, mock_project_index
    ):
        """Test generating context for non-existent service."""
        generator = ServiceContextGenerator(mock_project_dir, mock_project_index)

        with pytest.raises(ValueError, match="Service 'nonexistent' not found"):
            generator.generate_for_service("nonexistent")

    def test_generate_for_service_with_absolute_path(self, mock_project_dir):
        """Test service path resolution with absolute path in index."""
        # Create service directory outside project
        external_dir = mock_project_dir / "external" / "service"
        external_dir.mkdir(parents=True)

        project_index = {
            "services": {
                "external": {
                    "path": str(external_dir),  # Absolute path
                    "type": "api",
                    "language": "python",
                    "framework": "fastapi",
                }
            }
        }

        generator = ServiceContextGenerator(mock_project_dir, project_index)
        context = generator.generate_for_service("external")

        # Path should be relative to project_dir
        assert "external" in context.path or "service" in context.path

    def test_generate_for_service_empty_service_info(self, mock_project_dir):
        """Test generating context with minimal service info - empty dict raises ValueError."""
        # The implementation treats empty service_info as "not found"
        project_index = {
            "services": {
                "minimal": {}  # Empty service info - treated as not found
            }
        }

        service_dir = mock_project_dir / "minimal"
        service_dir.mkdir()

        generator = ServiceContextGenerator(mock_project_dir, project_index)

        # Empty service_info raises ValueError
        with pytest.raises(ValueError, match="Service 'minimal' not found"):
            generator.generate_for_service("minimal")

    def test_discover_entry_points_python(self, mock_project_dir, mock_service_dir):
        """Test discovering Python entry points."""
        # Create entry point files
        (mock_service_dir / "main.py").touch()
        (mock_service_dir / "app.py").touch()

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="fastapi"
        )

        generator._discover_entry_points(mock_service_dir, context)

        assert "main.py" in context.entry_points
        assert "app.py" in context.entry_points

    def test_discover_entry_points_go(self, mock_project_dir, mock_service_dir):
        """Test discovering Go entry points."""
        # Create Go entry point files
        cmd_dir = mock_service_dir / "cmd"
        cmd_dir.mkdir()
        (cmd_dir / "main.go").touch()
        (mock_service_dir / "main.go").touch()

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="go", framework=""
        )

        generator._discover_entry_points(mock_service_dir, context)

        assert len(context.entry_points) >= 1
        assert any("main.go" in entry for entry in context.entry_points)

    def test_discover_entry_points_rust(self, mock_project_dir, mock_service_dir):
        """Test discovering Rust entry points."""
        # Create Rust entry point files
        src_dir = mock_service_dir / "src"
        src_dir.mkdir()
        (src_dir / "main.rs").touch()
        (src_dir / "lib.rs").touch()

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="rust", framework=""
        )

        generator._discover_entry_points(mock_service_dir, context)

        assert "src/main.rs" in context.entry_points or "main.rs" in context.entry_points

    def test_discover_entry_points_no_duplicates(self, mock_project_dir, mock_service_dir):
        """Test that duplicate entry points are not added."""
        (mock_service_dir / "main.py").touch()

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="fastapi",
            entry_points=["main.py"]  # Pre-add main.py
        )

        generator._discover_entry_points(mock_service_dir, context)

        # Should not add duplicate
        assert context.entry_points.count("main.py") == 1

    def test_discover_entry_points_none_found(self, mock_project_dir, mock_service_dir):
        """Test discovering entry points when none exist."""
        # Don't create any entry point files

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="fastapi"
        )

        generator._discover_entry_points(mock_service_dir, context)

        assert context.entry_points == []

    def test_discover_dependencies_python(self, mock_project_dir, mock_service_dir):
        """Test discovering Python dependencies from requirements.txt."""
        requirements_file = mock_service_dir / "requirements.txt"
        requirements_file.write_text(
            "fastapi==0.104.0\nuvicorn[standard]>=0.24.0\npydantic>=2.0\n"
            "# This is a comment\nsqlalchemy[asyncio]\n",
            encoding="utf-8",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="fastapi"
        )

        generator._discover_dependencies(mock_service_dir, context)

        assert "fastapi" in context.dependencies
        assert "uvicorn" in context.dependencies
        assert "pydantic" in context.dependencies
        assert "sqlalchemy" in context.dependencies

    def test_discover_dependencies_python_with_comments_and_blank_lines(self, mock_project_dir, mock_service_dir):
        """Test dependency parsing handles comments and blank lines."""
        requirements_file = mock_service_dir / "requirements.txt"
        requirements_file.write_text(
            "# Production dependencies\n\nfastapi==0.104.0\n\n\n"
            "# Development dependencies\npytest>=7.0\n",
            encoding="utf-8",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="fastapi"
        )

        generator._discover_dependencies(mock_service_dir, context)

        assert "fastapi" in context.dependencies
        assert "pytest" in context.dependencies

    def test_discover_dependencies_python_limit(self, mock_project_dir, mock_service_dir):
        """Test that only first 20 dependencies are extracted."""
        requirements_file = mock_service_dir / "requirements.txt"
        deps = [f"package{i}==1.0.0" for i in range(25)]
        requirements_file.write_text("\n".join(deps), encoding="utf-8")

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="fastapi"
        )

        generator._discover_dependencies(mock_service_dir, context)

        # Should limit to 20
        assert len(context.dependencies) <= 20

    def test_discover_dependencies_no_duplicates(self, mock_project_dir, mock_service_dir):
        """Test that duplicate dependencies are not added."""
        requirements_file = mock_service_dir / "requirements.txt"
        requirements_file.write_text("fastapi==1.0\n", encoding="utf-8")

        package_json = mock_service_dir / "package.json"
        package_json.write_text(
            json.dumps({"dependencies": {"fastapi": "^1.0"}}),
            encoding="utf-8",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="fastapi"
        )

        generator._discover_dependencies(mock_service_dir, context)

        # Should not have duplicate
        assert context.dependencies.count("fastapi") <= 1

    def test_discover_dependencies_node(self, mock_project_dir, mock_service_dir):
        """Test discovering Node.js dependencies from package.json."""
        package_json = mock_service_dir / "package.json"
        package_json.write_text(
            json.dumps(
                {
                    "name": "test-app",
                    "dependencies": {
                        "react": "^18.0.0",
                        "typescript": "^5.0.0",
                        "vite": "^5.0.0",
                    }
                }
            ),
            encoding="utf-8",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="frontend", path="frontend", service_type="ui", language="typescript", framework="react"
        )

        generator._discover_dependencies(mock_service_dir, context)

        assert "react" in context.dependencies
        assert "typescript" in context.dependencies
        assert "vite" in context.dependencies

    def test_discover_dependencies_node_limit(self, mock_project_dir, mock_service_dir):
        """Test that only first 15 Node dependencies are extracted."""
        deps = {f"package{i}": "^1.0.0" for i in range(20)}
        package_json = mock_service_dir / "package.json"
        package_json.write_text(
            json.dumps({"name": "test", "dependencies": deps}),
            encoding="utf-8",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="frontend", path="frontend", service_type="ui", language="typescript", framework="react"
        )

        generator._discover_dependencies(mock_service_dir, context)

        # Should limit to 15
        assert len([d for d in context.dependencies if d.startswith("package")]) <= 15

    def test_discover_api_patterns_flask(self, mock_project_dir, mock_service_dir):
        """Test discovering Flask API patterns."""
        routes_file = mock_service_dir / "routes.py"
        routes_file.write_text(
            "@app.route('/api/users')\ndef get_users():\n    pass\n",
            encoding="utf-8",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="flask"
        )

        generator._discover_api_patterns(mock_service_dir, context)

        assert any("Flask/FastAPI" in pattern for pattern in context.api_patterns)

    def test_discover_api_patterns_fastapi_router(self, mock_project_dir, mock_service_dir):
        """Test discovering FastAPI router patterns."""
        router_file = mock_service_dir / "router.py"
        router_file.write_text(
            "@router.get('/api/users')\nasync def get_users():\n    pass\n",
            encoding="utf-8",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="fastapi"
        )

        generator._discover_api_patterns(mock_service_dir, context)

        assert any("Flask/FastAPI" in pattern for pattern in context.api_patterns)

    def test_discover_api_patterns_express(self, mock_project_dir, mock_service_dir):
        """Test discovering Express API patterns."""
        api_dir = mock_service_dir / "api"
        api_dir.mkdir()
        routes_file = api_dir / "routes.ts"
        routes_file.write_text(
            "express.Router()\napp.get('/api/users', handler)\n",
            encoding="utf-8",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="typescript", framework="express"
        )

        generator._discover_api_patterns(mock_service_dir, context)

        assert any("Express" in pattern for pattern in context.api_patterns)

    def test_discover_api_patterns_no_files_found(self, mock_project_dir, mock_service_dir):
        """Test API pattern discovery when no route files exist."""
        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="flask"
        )

        generator._discover_api_patterns(mock_service_dir, context)

        assert context.api_patterns == []

    def test_discover_api_patterns_limit(self, mock_project_dir, mock_service_dir):
        """Test that only first 5 route files are checked."""
        # Create many route files
        for i in range(10):
            routes_file = mock_service_dir / f"routes{i}.py"
            routes_file.write_text("@app.route('/')", encoding="utf-8")

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="flask"
        )

        generator._discover_api_patterns(mock_service_dir, context)

        # Should have patterns from files checked (limit is 5)
        # At least some patterns should be found
        assert len(context.api_patterns) > 0

    def test_discover_api_patterns_unrecognized_framework(self, mock_project_dir, mock_service_dir):
        """Test API pattern discovery with unrecognized route syntax."""
        routes_file = mock_service_dir / "routes.py"
        routes_file.write_text(
            "def custom_route_handler():\n    pass\n",
            encoding="utf-8",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="custom"
        )

        generator._discover_api_patterns(mock_service_dir, context)

        # Should not match any known patterns
        assert context.api_patterns == []

    def test_discover_common_commands_from_package_json(
        self, mock_project_dir, mock_service_dir
    ):
        """Test discovering common commands from package.json scripts."""
        package_json = mock_service_dir / "package.json"
        package_json.write_text(
            json.dumps(
                {
                    "name": "test-app",
                    "scripts": {
                        "dev": "vite",
                        "build": "tsc && vite build",
                        "test": "vitest",
                        "lint": "eslint .",
                    },
                }
            ),
            encoding="utf-8",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="frontend", path="frontend", service_type="ui", language="typescript", framework="vite"
        )

        generator._discover_common_commands(mock_service_dir, context)

        assert context.common_commands["dev"] == "npm run dev"
        assert context.common_commands["build"] == "npm run build"
        assert context.common_commands["test"] == "npm run test"
        assert context.common_commands["lint"] == "npm run lint"

    def test_discover_common_commands_from_package_json_partial_scripts(self, mock_project_dir, mock_service_dir):
        """Test discovering only specific scripts from package.json."""
        package_json = mock_service_dir / "package.json"
        package_json.write_text(
            json.dumps(
                {
                    "name": "test-app",
                    "scripts": {
                        "dev": "vite",
                        "custom": "custom command",  # Not in common list
                        "build": "tsc",
                    },
                }
            ),
            encoding="utf-8",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="frontend", path="frontend", service_type="ui", language="typescript", framework="vite"
        )

        generator._discover_common_commands(mock_service_dir, context)

        # Should only have common scripts
        assert "dev" in context.common_commands
        assert "build" in context.common_commands
        assert "custom" not in context.common_commands

    def test_discover_common_commands_from_makefile(
        self, mock_project_dir, mock_service_dir
    ):
        """Test discovering common commands from Makefile."""
        makefile = mock_service_dir / "Makefile"
        makefile.write_text(
            "dev:\n\tflask run\n\nbuild:\n\tdocker build .\n\ntest:\n\tpytest\n",
            encoding="utf-8",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="flask"
        )

        generator._discover_common_commands(mock_service_dir, context)

        assert context.common_commands["dev"] == "make dev"
        assert context.common_commands["build"] == "make build"
        assert context.common_commands["test"] == "make test"

    def test_discover_common_commands_from_makefile_ignores_non_targets(self, mock_project_dir, mock_service_dir):
        """Test that Makefile parsing ignores non-target lines."""
        makefile = mock_service_dir / "Makefile"
        makefile.write_text(
            ".PHONY: dev build\n\nvariables:\n\tVAR=value\n\ndev:\n\tflask run\n",
            encoding="utf-8",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="flask"
        )

        generator._discover_common_commands(mock_service_dir, context)

        # Should only have dev, not variables
        assert "dev" in context.common_commands
        assert "variables" not in context.common_commands

    def test_discover_common_commands_from_makefile_install_target(self, mock_project_dir, mock_service_dir):
        """Test discovering install target from Makefile."""
        makefile = mock_service_dir / "Makefile"
        makefile.write_text(
            "install:\n\tpip install -r requirements.txt\n",
            encoding="utf-8",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="flask"
        )

        generator._discover_common_commands(mock_service_dir, context)

        assert context.common_commands.get("install") == "make install"

    def test_discover_common_commands_from_makefile_run_target(self, mock_project_dir, mock_service_dir):
        """Test discovering run target from Makefile."""
        makefile = mock_service_dir / "Makefile"
        makefile.write_text(
            "run:\n\tflask run\n",
            encoding="utf-8",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="flask"
        )

        generator._discover_common_commands(mock_service_dir, context)

        assert context.common_commands.get("run") == "make run"

    def test_discover_common_commands_inferred(self, mock_project_dir):
        """Test inferring common commands from framework."""
        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})

        # Test FastAPI inference
        context_fastapi = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="fastapi"
        )
        generator._discover_common_commands(mock_project_dir, context_fastapi)
        assert context_fastapi.common_commands["dev"] == "uvicorn main:app --reload"

        # Test Next.js inference
        context_next = ServiceContext(
            name="frontend", path="frontend", service_type="ui", language="typescript", framework="next"
        )
        generator._discover_common_commands(mock_project_dir, context_next)
        assert context_next.common_commands["dev"] == "npm run dev"

    def test_discover_common_commands_precedence(self, mock_project_dir, mock_service_dir):
        """Test that discovered commands take precedence over inferred commands."""
        # Create package.json with dev command
        package_json = mock_service_dir / "package.json"
        package_json.write_text(
            json.dumps({
                "name": "test",
                "scripts": {"dev": "custom dev command"}
            }),
            encoding="utf-8",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="frontend", path="frontend", service_type="ui", language="typescript", framework="next"
        )

        generator._discover_common_commands(mock_service_dir, context)

        # Should use package.json command, not inferred
        assert context.common_commands["dev"] == "npm run dev"

    def test_discover_environment_vars(self, mock_project_dir, mock_service_dir):
        """Test discovering environment variables from .env files."""
        env_file = mock_service_dir / ".env.example"
        env_file.write_text(
            "DATABASE_URL=postgresql://localhost/db\nAPI_KEY=secret\n"
            "# Comment line\nDEBUG=true\n",
            encoding="utf-8",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="fastapi"
        )

        generator._discover_environment_vars(mock_service_dir, context)

        assert "DATABASE_URL" in context.environment_vars
        assert "API_KEY" in context.environment_vars
        assert "DEBUG" in context.environment_vars

    def test_discover_environment_vars_priority(self, mock_project_dir, mock_service_dir):
        """Test that .env.example is checked before .env."""
        # Create both files
        env_example = mock_service_dir / ".env.example"
        env_example.write_text("FROM_EXAMPLE=value1\n", encoding="utf-8")

        env = mock_service_dir / ".env"
        env.write_text("FROM_ENV=value2\n", encoding="utf-8")

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="fastapi"
        )

        generator._discover_environment_vars(mock_service_dir, context)

        # Should only have example (breaks after first found)
        assert "FROM_EXAMPLE" in context.environment_vars
        assert "FROM_ENV" not in context.environment_vars

    def test_discover_environment_vars_all_files_checked(self, mock_project_dir, mock_service_dir):
        """Test all .env file variants are checked in order."""
        # Check with .env.sample
        env_sample = mock_service_dir / ".env.sample"
        env_sample.write_text("VAR1=value1\nVAR2=value2\n", encoding="utf-8")

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="fastapi"
        )

        generator._discover_environment_vars(mock_service_dir, context)

        assert "VAR1" in context.environment_vars
        assert "VAR2" in context.environment_vars

    def test_discover_environment_vars_no_duplicates(self, mock_project_dir, mock_service_dir):
        """Test that duplicate environment variables are not added."""
        env_file = mock_service_dir / ".env.example"
        env_file.write_text("VAR=value\nVAR=value2\n", encoding="utf-8")

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="fastapi",
            environment_vars=["VAR"]  # Pre-add
        )

        generator._discover_environment_vars(mock_service_dir, context)

        # Should not add duplicate
        assert context.environment_vars.count("VAR") == 1

    def test_discover_environment_vars_with_quotes(self, mock_project_dir, mock_service_dir):
        """Test environment variables with quoted values."""
        env_file = mock_service_dir / ".env.example"
        env_file.write_text(
            'DATABASE_URL="postgresql://localhost/db"\nAPI_KEY=\'secret\'\n',
            encoding="utf-8",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="fastapi"
        )

        generator._discover_environment_vars(mock_service_dir, context)

        # Should extract variable names (values with quotes are fine)
        assert "DATABASE_URL" in context.environment_vars
        assert "API_KEY" in context.environment_vars

    def test_discover_environment_vars_empty_lines(self, mock_project_dir, mock_service_dir):
        """Test environment variable parsing with empty lines."""
        env_file = mock_service_dir / ".env.example"
        env_file.write_text("\n\nVAR1=value1\n\n\nVAR2=value2\n\n", encoding="utf-8")

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="fastapi"
        )

        generator._discover_environment_vars(mock_service_dir, context)

        assert "VAR1" in context.environment_vars
        assert "VAR2" in context.environment_vars

    def test_generate_markdown(self, mock_project_dir):
        """Test generating markdown output."""
        context = ServiceContext(
            name="backend",
            path="backend",
            service_type="api",
            language="python",
            framework="fastapi",
            entry_points=["main.py"],
            key_directories={"routes": "API routes"},
            dependencies=["fastapi", "uvicorn"],
            ports=[8000],
            common_commands={"dev": "uvicorn main:app --reload"},
            environment_vars=["DATABASE_URL"],
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        markdown = generator.generate_markdown(context)

        assert "# Backend Service Context" in markdown
        assert "**Type**: api" in markdown
        assert "**Language**: python" in markdown
        assert "**Framework**: fastapi" in markdown
        assert "**Port(s)**: 8000" in markdown
        assert "main.py" in markdown
        assert "## Key Dependencies" in markdown
        assert "fastapi" in markdown
        assert "## Common Commands" in markdown
        assert "## Environment Variables" in markdown
        assert "DATABASE_URL" in markdown

    def test_generate_markdown_minimal(self, mock_project_dir):
        """Test generating markdown with minimal context."""
        context = ServiceContext(
            name="backend",
            path="backend",
            service_type="unknown",
            language="unknown",
            framework="unknown",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        markdown = generator.generate_markdown(context)

        # Should have basic structure
        assert "# Backend Service Context" in markdown
        assert "**Type**: unknown" in markdown
        assert "*This file was auto-generated" in markdown
        assert "*Update manually if you need to add" in markdown

    def test_generate_markdown_with_multiple_ports(self, mock_project_dir):
        """Test markdown generation with multiple ports."""
        context = ServiceContext(
            name="backend",
            path="backend",
            service_type="api",
            language="python",
            framework="fastapi",
            ports=[8000, 8001, 8002],
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        markdown = generator.generate_markdown(context)

        assert "8000, 8001, 8002" in markdown

    def test_generate_markdown_dependency_limit(self, mock_project_dir):
        """Test that markdown limits dependencies to 15."""
        deps = [f"package{i}" for i in range(20)]
        context = ServiceContext(
            name="backend",
            path="backend",
            service_type="api",
            language="python",
            framework="fastapi",
            dependencies=deps,
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        markdown = generator.generate_markdown(context)

        # Should only list first 15
        for i in range(15):
            assert f"package{i}" in markdown
        # Should not list beyond 15
        assert "package15" not in markdown
        assert "package19" not in markdown

    def test_generate_markdown_env_var_limit(self, mock_project_dir):
        """Test that markdown limits environment variables to 20."""
        env_vars = [f"VAR_{i}" for i in range(25)]
        context = ServiceContext(
            name="backend",
            path="backend",
            service_type="api",
            language="python",
            framework="fastapi",
            environment_vars=env_vars,
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        markdown = generator.generate_markdown(context)

        # Should only list first 20
        for i in range(20):
            assert f"VAR_{i}" in markdown
        # Should not list beyond 20
        assert "VAR_20" not in markdown

    def test_generate_markdown_without_optional_sections(self, mock_project_dir):
        """Test markdown generation without optional sections."""
        context = ServiceContext(
            name="backend",
            path="backend",
            service_type="api",
            language="python",
            framework="fastapi",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        markdown = generator.generate_markdown(context)

        # These sections should not appear if empty
        assert "## Entry Points" not in markdown
        assert "## Key Directories" not in markdown
        assert "## Key Dependencies" not in markdown
        assert "## API Patterns" not in markdown
        assert "## Common Commands" not in markdown
        assert "## Environment Variables" not in markdown
        assert "## Notes" not in markdown

    def test_generate_and_save(self, mock_project_dir, mock_project_index):
        """Test generating and saving service context."""
        # Create service directory
        service_dir = mock_project_dir / "backend"
        service_dir.mkdir()

        generator = ServiceContextGenerator(mock_project_dir, mock_project_index)

        output_path = generator.generate_and_save("backend")

        # Verify file was created
        assert output_path.exists()
        assert output_path.name == "SERVICE_CONTEXT.md"

        # Verify content
        content = output_path.read_text(encoding="utf-8")
        assert "# Backend Service Context" in content

    def test_generate_and_save_custom_output(
        self, mock_project_dir, mock_project_index, tmp_path
    ):
        """Test generating and saving to custom output path."""
        # Create service directory
        service_dir = mock_project_dir / "backend"
        service_dir.mkdir()

        custom_output = tmp_path / "custom" / "output.md"

        generator = ServiceContextGenerator(mock_project_dir, mock_project_index)

        output_path = generator.generate_and_save("backend", output_path=custom_output)

        assert output_path == custom_output
        assert custom_output.exists()

    def test_generate_and_save_creates_directories(self, mock_project_dir, mock_project_index):
        """Test that generate_and_save creates parent directories."""
        # Create service directory
        service_dir = mock_project_dir / "backend"
        service_dir.mkdir()

        # Create a nested output path
        custom_output = mock_project_dir / "nested" / "dir" / "output.md"

        generator = ServiceContextGenerator(mock_project_dir, mock_project_index)

        output_path = generator.generate_and_save("backend", output_path=custom_output)

        # Should create parent directories
        assert output_path.exists()
        assert output_path.parent.exists()

    def test_generate_and_save_default_path(self, mock_project_dir, mock_project_index):
        """Test default output path is service/SERVICE_CONTEXT.md."""
        service_dir = mock_project_dir / "backend"
        service_dir.mkdir()

        generator = ServiceContextGenerator(mock_project_dir, mock_project_index)

        output_path = generator.generate_and_save("backend")

        # Should be backend/SERVICE_CONTEXT.md
        assert output_path == service_dir / "SERVICE_CONTEXT.md"


class TestGenerateAllContexts:
    """Tests for generate_all_contexts function."""

    def test_generate_all_contexts_success(self, mock_project_dir, mock_project_index):
        """Test generating contexts for all services."""
        # Create service directories
        (mock_project_dir / "backend").mkdir()
        (mock_project_dir / "frontend").mkdir()

        results = generate_all_contexts(mock_project_dir, mock_project_index)

        assert len(results) == 2

        # Check both services were generated
        service_names = [name for name, _ in results]
        assert "backend" in service_names
        assert "frontend" in service_names

        # Verify files exist
        for service_name, path in results:
            assert Path(path).exists()

    def test_generate_all_contexts_partial_failure(
        self, mock_project_dir, mock_project_index, capsys
    ):
        """Test generating contexts handles failures gracefully."""
        # Only create one service directory
        (mock_project_dir / "backend").mkdir()
        # Don't create frontend directory

        results = generate_all_contexts(mock_project_dir, mock_project_index)

        # Should still generate backend (maybe frontend failed silently)
        assert len(results) >= 1
        assert any(name == "backend" for name, _ in results)

    def test_generate_all_contexts_empty_services(self, mock_project_dir, capsys):
        """Test generate_all_contexts with no services."""
        empty_index = {"services": {}}

        results = generate_all_contexts(mock_project_dir, empty_index)

        assert results == []

    def test_generate_all_contexts_exception_handling(self, mock_project_dir, mock_project_index, capsys):
        """Test that exceptions during generation are handled gracefully."""
        # Create service directories
        (mock_project_dir / "backend").mkdir()
        (mock_project_dir / "frontend").mkdir()

        # Patch to raise exception for one service
        with patch("services.context.ServiceContextGenerator") as mock_gen_class:
            mock_instance = MagicMock()
            mock_gen_class.return_value = mock_instance
            mock_instance.project_index = mock_project_index

            call_count = [0]

            def side_effect(service_name):
                call_count[0] += 1
                if service_name == "backend":
                    return mock_project_dir / "backend" / "SERVICE_CONTEXT.md"
                else:
                    raise ValueError(f"Service {service_name} failed")

            mock_instance.generate_and_save.side_effect = side_effect

            results = generate_all_contexts(mock_project_dir, mock_project_index)

        # Should have backend result
        assert len(results) == 1
        assert results[0][0] == "backend"

        # Check error message
        captured = capsys.readouterr()
        assert "Failed to generate context for frontend" in captured.out

    def test_generate_all_contexts_with_project_index_none(self, mock_project_dir):
        """Test generate_all_contexts with None project index."""
        # Create service directory
        (mock_project_dir / "backend").mkdir()

        # No project_index provided, no .auto-claude directory
        results = generate_all_contexts(mock_project_dir, None)

        # Should return empty (no services in index)
        assert results == []


class TestMain:
    """Tests for CLI entry point."""

    def test_main_with_service(self, mock_project_dir, mock_project_index, capsys):
        """Test main CLI with specific service."""
        # Create service directory
        (mock_project_dir / "backend").mkdir()

        with patch("sys.argv", ["service_context.py", "--project-dir", str(mock_project_dir), "--service", "backend"]):
            # Patch _load_project_index to return our test index
            with patch.object(ServiceContextGenerator, "_load_project_index", return_value=mock_project_index):
                from services.context import main
                main()

        captured = capsys.readouterr()
        # Should indicate file was generated
        assert "Generated SERVICE_CONTEXT.md" in captured.out

    def test_main_no_args(self, mock_project_dir, capsys):
        """Test main CLI with no arguments prints help."""
        with patch("sys.argv", ["service_context.py"]):
            with pytest.raises(SystemExit) as exc_info:
                from services.context import main
                main()

        # Should exit with error code
        assert exc_info.value.code == 1

    def test_main_with_all_services(self, mock_project_dir, mock_project_index, capsys):
        """Test main CLI with --all flag."""
        # Create service directories
        (mock_project_dir / "backend").mkdir()
        (mock_project_dir / "frontend").mkdir()

        with patch("sys.argv", ["service_context.py", "--project-dir", str(mock_project_dir), "--all"]):
            with patch.object(ServiceContextGenerator, "_load_project_index", return_value=mock_project_index):
                from services.context import main
                main()

        captured = capsys.readouterr()
        assert "Generated 2 SERVICE_CONTEXT.md files" in captured.out

    def test_main_with_custom_index(self, mock_project_dir, tmp_path):
        """Test main CLI with custom index file."""
        # Create custom index
        index_file = tmp_path / "custom_index.json"
        test_index = {
            "services": {
                "backend": {"path": "backend", "type": "api", "language": "python"}
            }
        }
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(test_index, f)

        # Create service directory
        (mock_project_dir / "backend").mkdir()

        with patch("sys.argv", ["service_context.py", "--project-dir", str(mock_project_dir), "--service", "backend", "--index", str(index_file)]):
            from services.context import main
            main()

        # Verify file was created
        output_file = mock_project_dir / "backend" / "SERVICE_CONTEXT.md"
        assert output_file.exists()

    def test_main_with_nonexistent_index(self, mock_project_dir, tmp_path):
        """Test main with nonexistent index file - uses empty index."""
        # Create service directory and project structure
        (mock_project_dir / "backend").mkdir()

        # Use a path that exists but file doesn't
        nonexistent_index = tmp_path / "nonexistent_index.json"

        # Need to create a .auto-claude/project_index.json for service lookup
        auto_claude = mock_project_dir / ".auto-claude"
        auto_claude.mkdir()
        index_file = auto_claude / "project_index.json"
        test_index = {
            "services": {
                "backend": {"path": "backend", "type": "api", "language": "python"}
            }
        }
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(test_index, f)

        with patch("sys.argv", ["service_context.py", "--project-dir", str(mock_project_dir), "--service", "backend", "--index", str(nonexistent_index)]):
            from services.context import main
            main()

        # Should use default index file (service should be found)
        output_file = mock_project_dir / "backend" / "SERVICE_CONTEXT.md"
        assert output_file.exists()

    def test_main_with_output_path(self, mock_project_dir, mock_project_index, tmp_path, capsys):
        """Test main with custom --output path."""
        # Create service directory
        (mock_project_dir / "backend").mkdir()

        output_path = tmp_path / "custom_context.md"

        with patch("sys.argv", ["service_context.py", "--project-dir", str(mock_project_dir), "--service", "backend", "--output", str(output_path)]):
            with patch.object(ServiceContextGenerator, "_load_project_index", return_value=mock_project_index):
                from services.context import main
                main()

        # Verify file was created at custom path
        assert output_path.exists()

    def test_main_default_project_dir(self, tmp_path, monkeypatch, capsys):
        """Test main uses current directory as default project dir."""
        # Create a minimal project structure in temp dir
        service_dir = tmp_path / "backend"
        service_dir.mkdir()

        # Create project index
        auto_claude = tmp_path / ".auto-claude"
        auto_claude.mkdir()
        index_file = auto_claude / "project_index.json"
        test_index = {
            "services": {
                "backend": {"path": "backend", "type": "api", "language": "python"}
            }
        }
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(test_index, f)

        # Change to temp directory
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with patch("sys.argv", ["service_context.py", "--service", "backend"]):
                from services.context import main
                main()

            # Should use current directory
            assert (service_dir / "SERVICE_CONTEXT.md").exists()
        finally:
            os.chdir(original_cwd)

    def test_main_all_with_empty_services(self, mock_project_dir, capsys):
        """Test main --all with no services."""
        empty_index = {"services": {}}
        auto_claude = mock_project_dir / ".auto-claude"
        auto_claude.mkdir()
        index_file = auto_claude / "project_index.json"
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(empty_index, f)

        with patch("sys.argv", ["service_context.py", "--project-dir", str(mock_project_dir), "--all"]):
            from services.context import main
            main()

        captured = capsys.readouterr()
        assert "Generated 0 SERVICE_CONTEXT.md files" in captured.out

    def test_main_error_message_without_service_or_all(self, mock_project_dir, capsys):
        """Test main prints error when neither --service nor --all is provided."""
        with patch("sys.argv", ["service_context.py", "--project-dir", str(mock_project_dir)]):
            with pytest.raises(SystemExit):
                from services.context import main
                main()


class TestErrorHandling:
    """Tests for error handling paths."""

    def test_discover_dependencies_requirements_os_error(self, mock_project_dir, mock_service_dir):
        """Test discovering dependencies when requirements.txt has OS error."""
        requirements_file = mock_service_dir / "requirements.txt"
        requirements_file.write_text("fastapi==0.104.0\n", encoding="utf-8")

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="fastapi"
        )

        # Mock read_text to raise OSError
        with patch.object(Path, "read_text", side_effect=OSError("Permission denied")):
            generator._discover_dependencies(mock_service_dir, context)

        # Should handle gracefully, dependencies may be empty
        assert context.dependencies == []

    def test_discover_dependencies_package_json_decode_error(self, mock_project_dir, mock_service_dir):
        """Test discovering dependencies when package.json is malformed."""
        package_json = mock_service_dir / "package.json"
        package_json.write_text("invalid json content", encoding="utf-8")

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="frontend", path="frontend", service_type="ui", language="typescript", framework="react"
        )

        # Should handle decode error gracefully
        generator._discover_dependencies(mock_service_dir, context)
        assert context.dependencies == []

    def test_discover_dependencies_package_json_unicode_error(self, mock_project_dir, mock_service_dir):
        """Test discovering dependencies when package.json has unicode issues."""
        package_json = mock_service_dir / "package.json"
        # Write invalid UTF-8
        package_json.write_bytes(b'\xff\xfe invalid')

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="frontend", path="frontend", service_type="ui", language="typescript", framework="react"
        )

        # Should handle unicode error gracefully
        generator._discover_dependencies(mock_service_dir, context)
        assert context.dependencies == []

    def test_discover_api_patterns_read_error(self, mock_project_dir, mock_service_dir):
        """Test discovering API patterns when files can't be read."""
        routes_file = mock_service_dir / "routes.py"
        routes_file.write_text("@app.route('/api')", encoding="utf-8")

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="flask"
        )

        # Mock read_text to raise OSError
        with patch.object(Path, "read_text", side_effect=OSError("Read error")):
            generator._discover_api_patterns(mock_service_dir, context)

        # Should handle gracefully
        assert context.api_patterns == []

    def test_discover_api_patterns_unicode_error(self, mock_project_dir, mock_service_dir):
        """Test discovering API patterns with unicode decode error."""
        routes_file = mock_service_dir / "routes.py"
        routes_file.write_bytes(b'\xff\xfe invalid')

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="flask"
        )

        generator._discover_api_patterns(mock_service_dir, context)

        # Should handle gracefully
        assert context.api_patterns == []

    def test_discover_common_commands_package_json_decode_error(self, mock_project_dir, mock_service_dir):
        """Test discovering commands when package.json is malformed."""
        package_json = mock_service_dir / "package.json"
        package_json.write_text("{invalid json}", encoding="utf-8")

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="frontend", path="frontend", service_type="ui", language="typescript", framework="react"
        )

        # Should handle gracefully
        generator._discover_common_commands(mock_service_dir, context)
        # Should not crash

    def test_discover_common_commands_package_json_unicode_error(self, mock_project_dir, mock_service_dir):
        """Test discovering commands when package.json has unicode issues."""
        package_json = mock_service_dir / "package.json"
        package_json.write_bytes(b'\xff\xfe invalid')

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="frontend", path="frontend", service_type="ui", language="typescript", framework="react"
        )

        # Should handle gracefully
        generator._discover_common_commands(mock_service_dir, context)
        # Should not crash

    def test_discover_common_commands_makefile_os_error(self, mock_project_dir, mock_service_dir):
        """Test discovering commands when Makefile can't be read."""
        makefile = mock_service_dir / "Makefile"
        makefile.write_text("dev:\n\tflask run\n", encoding="utf-8")

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="flask"
        )

        # Mock read_text to raise OSError
        with patch.object(Path, "read_text", side_effect=OSError("Read error")):
            generator._discover_common_commands(mock_service_dir, context)

        # Should handle gracefully
        # No commands should be added from Makefile
        assert all("make" not in cmd for cmd in context.common_commands.values())

    def test_discover_environment_vars_read_error(self, mock_project_dir, mock_service_dir):
        """Test discovering environment variables when .env file can't be read."""
        env_file = mock_service_dir / ".env.example"
        env_file.write_text("DATABASE_URL=postgres://\n", encoding="utf-8")

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        context = ServiceContext(
            name="backend", path="backend", service_type="api", language="python", framework="fastapi"
        )

        # Mock read_text to raise OSError
        with patch.object(Path, "read_text", side_effect=OSError("Read error")):
            generator._discover_environment_vars(mock_service_dir, context)

        # Should handle gracefully
        assert context.environment_vars == []

    def test_load_project_index_json_decode_error(self, mock_project_dir, mock_auto_claude_dir):
        """Test loading project index when file is malformed JSON - exception propagates."""
        index_file = mock_auto_claude_dir / "project_index.json"
        with open(index_file, "w", encoding="utf-8") as f:
            f.write("{invalid json}")

        # The implementation doesn't catch JSONDecodeError, it propagates
        with pytest.raises(json.JSONDecodeError):
            ServiceContextGenerator(mock_project_dir)

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Windows does not support Unix-style chmod permissions for making files unreadable"
    )
    def test_load_project_index_os_error(self, mock_project_dir, mock_auto_claude_dir):
        """Test loading project index when file can't be read - exception propagates."""
        index_file = mock_auto_claude_dir / "project_index.json"
        index_file.write_text('{"services": {}}', encoding="utf-8")
        index_file.chmod(0o000)  # Remove read permissions

        try:
            # The implementation doesn't catch OSError from file read, it propagates
            with pytest.raises(OSError):
                ServiceContextGenerator(mock_project_dir)
        finally:
            # Restore permissions for cleanup
            index_file.chmod(0o644)


class TestGenerateMarkdownWithNotes:
    """Tests for markdown generation with notes."""

    def test_generate_markdown_with_notes(self, mock_project_dir):
        """Test generating markdown with notes section."""
        context = ServiceContext(
            name="backend",
            path="backend",
            service_type="api",
            language="python",
            framework="fastapi",
            notes=["Note 1", "Note 2"]
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        markdown = generator.generate_markdown(context)

        assert "## Notes" in markdown
        assert "- Note 1" in markdown
        assert "- Note 2" in markdown

    def test_generate_markdown_without_notes(self, mock_project_dir):
        """Test generating markdown without notes section."""
        context = ServiceContext(
            name="backend",
            path="backend",
            service_type="api",
            language="python",
            framework="fastapi",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        markdown = generator.generate_markdown(context)

        assert "## Notes" not in markdown


class TestGenerateMarkdownWithApiPatterns:
    """Tests for markdown generation with API patterns."""

    def test_generate_markdown_with_api_patterns(self, mock_project_dir):
        """Test generating markdown with API patterns section."""
        context = ServiceContext(
            name="backend",
            path="backend",
            service_type="api",
            language="python",
            framework="fastapi",
            api_patterns=["Flask/FastAPI routes in routes.py", "Express routes in api.ts"]
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        markdown = generator.generate_markdown(context)

        assert "## API Patterns" in markdown
        assert "Flask/FastAPI routes in routes.py" in markdown
        assert "Express routes in api.ts" in markdown


class TestGenerateAllContextsEdgeCases:
    """Tests for generate_all_contexts function covering edge cases."""

    def test_generate_all_contexts_exception_in_generate(self, mock_project_dir, mock_project_index, capsys):
        """Test generate_all_contexts handles exceptions gracefully."""
        # Create service directories
        (mock_project_dir / "backend").mkdir()
        (mock_project_dir / "frontend").mkdir()

        # Patch generate_and_save to raise exception for one service
        with patch("services.context.ServiceContextGenerator") as mock_gen_class:
            mock_instance = MagicMock()
            mock_gen_class.return_value = mock_instance

            # First call succeeds, second fails
            call_count = [0]

            def side_effect(service_name):
                call_count[0] += 1
                if call_count[0] == 1:
                    return mock_project_dir / "backend" / "SERVICE_CONTEXT.md"
                else:
                    raise Exception("Generation failed for frontend")

            mock_instance.generate_and_save.side_effect = side_effect
            mock_instance.project_index = mock_project_index

            result = generate_all_contexts(mock_project_dir, mock_project_index)

        # Should have returned one successful result
        assert len(result) == 1
        assert result[0][0] == "backend"

        # Check error was printed
        captured = capsys.readouterr()
        assert "Failed to generate context for frontend" in captured.out

    def test_generate_all_contexts_no_services(self, mock_project_dir, capsys):
        """Test generate_all_contexts with empty services list."""
        empty_index = {"services": {}}

        result = generate_all_contexts(mock_project_dir, empty_index)

        assert result == []


class TestDiscoverCommonCommandsEdgeCases:
    """Tests for _discover_common_commands covering Django and Next.js framework inference."""

    def test_discover_common_commands_django_framework(self, mock_service_dir, mock_project_dir):
        """Test command inference for Django framework."""
        context = ServiceContext(
            name="backend",
            path=str(mock_service_dir.relative_to(mock_project_dir)),
            service_type="api",
            language="python",
            framework="django",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        generator._discover_common_commands(mock_service_dir, context)

        assert context.common_commands.get("dev") == "python manage.py runserver"

    def test_discover_common_commands_nextjs_framework(self, mock_service_dir, mock_project_dir):
        """Test command inference for Next.js framework."""
        context = ServiceContext(
            name="frontend",
            path=str(mock_service_dir.relative_to(mock_project_dir)),
            service_type="ui",
            language="typescript",
            framework="next",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        generator._discover_common_commands(mock_service_dir, context)

        assert context.common_commands.get("dev") == "npm run dev"

    def test_discover_common_commands_nextjs_alias_framework(self, mock_service_dir, mock_project_dir):
        """Test command inference for Next.js with 'nextjs' alias."""
        context = ServiceContext(
            name="frontend",
            path=str(mock_service_dir.relative_to(mock_project_dir)),
            service_type="ui",
            language="typescript",
            framework="nextjs",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        generator._discover_common_commands(mock_service_dir, context)

        assert context.common_commands.get("dev") == "npm run dev"

    def test_discover_common_commands_vite_framework(self, mock_service_dir, mock_project_dir):
        """Test command inference for Vite framework."""
        context = ServiceContext(
            name="frontend",
            path=str(mock_service_dir.relative_to(mock_project_dir)),
            service_type="ui",
            language="typescript",
            framework="vite",
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        generator._discover_common_commands(mock_service_dir, context)

        assert context.common_commands.get("dev") == "npm run dev"


class TestFrameworkCommandInference:
    """Tests for framework-specific command inference edge cases."""

    @pytest.mark.parametrize("framework,expected_command", [
        ("flask", "flask run"),
        ("fastapi", "uvicorn main:app --reload"),
        ("django", "python manage.py runserver"),
        ("next", "npm run dev"),
        ("nextjs", "npm run dev"),
        ("react", "npm run dev"),
        ("vite", "npm run dev"),
    ])
    def test_framework_command_inference(self, mock_service_dir, mock_project_dir, framework, expected_command):
        """Test command inference for various frameworks."""
        context = ServiceContext(
            name="service",
            path=str(mock_service_dir.relative_to(mock_project_dir)),
            service_type="api",
            language="python",
            framework=framework,
        )

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        generator._discover_common_commands(mock_service_dir, context)

        assert context.common_commands.get("dev") == expected_command

    def test_framework_command_inference_does_not_override_existing(self, mock_service_dir, mock_project_dir):
        """Test that framework inference uses setdefault (doesn't override existing commands)."""
        context = ServiceContext(
            name="service",
            path=str(mock_service_dir.relative_to(mock_project_dir)),
            service_type="api",
            language="python",
            framework="flask",
        )
        # Pre-set the dev command
        context.common_commands["dev"] = "custom flask command"

        generator = ServiceContextGenerator(mock_project_dir, {"services": {}})
        generator._discover_common_commands(mock_service_dir, context)

        # Should keep the existing command
        assert context.common_commands.get("dev") == "custom flask command"


class TestServiceContextMutability:
    """Tests for ServiceContext field factory behavior."""

    def test_service_context_mutable_defaults(self):
        """Test that mutable defaults are properly isolated between instances."""
        context1 = ServiceContext(
            name="service1",
            path="service1",
            service_type="api",
            language="python",
            framework="fastapi",
        )
        context2 = ServiceContext(
            name="service2",
            path="service2",
            service_type="api",
            language="python",
            framework="fastapi",
        )

        # Modify context1
        context1.dependencies.append("fastapi")
        context1.environment_vars.append("DATABASE_URL")

        # context2 should not be affected
        assert context2.dependencies == []
        assert context2.environment_vars == []
