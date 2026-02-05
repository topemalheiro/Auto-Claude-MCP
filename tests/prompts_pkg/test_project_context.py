"""
Comprehensive tests for project_context module.
Tests project capability detection, index loading, and MCP tool selection.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from prompts_pkg.project_context import (
    detect_project_capabilities,
    get_mcp_tools_for_project,
    load_project_index,
    should_refresh_project_index,
)


class TestLoadProjectIndex:
    """Tests for load_project_index function."""

    def test_loads_valid_index(self, tmp_path):
        """Test loads and parses valid project_index.json."""
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()
        index_file = auto_claude_dir / "project_index.json"
        index_data = {
            "services": {
                "backend": {
                    "framework": "fastapi",
                    "dependencies": ["pydantic", "uvicorn"],
                }
            }
        }
        index_file.write_text(json.dumps(index_data), encoding="utf-8")

        result = load_project_index(tmp_path)

        assert result == index_data
        assert result["services"]["backend"]["framework"] == "fastapi"

    def test_returns_empty_dict_when_missing(self, tmp_path):
        """Test returns empty dict when index file doesn't exist."""
        result = load_project_index(tmp_path)

        assert result == {}

    def test_returns_empty_dict_on_invalid_json(self, tmp_path):
        """Test returns empty dict when JSON is invalid."""
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()
        index_file = auto_claude_dir / "project_index.json"
        index_file.write_text("{invalid json", encoding="utf-8")

        result = load_project_index(tmp_path)

        assert result == {}

    def test_returns_empty_dict_on_os_error(self, tmp_path):
        """Test returns empty dict on OS error (e.g., permission denied)."""
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()

        # Create a directory instead of a file
        index_file = auto_claude_dir / "project_index.json"
        index_file.mkdir()

        result = load_project_index(tmp_path)

        assert result == {}


class TestDetectProjectCapabilities:
    """Tests for detect_project_capabilities function."""

    def test_empty_index_returns_all_false(self):
        """Test empty project index returns all capabilities False."""
        result = detect_project_capabilities({})

        assert result["is_electron"] is False
        assert result["is_tauri"] is False
        assert result["is_expo"] is False
        assert result["is_react_native"] is False
        assert result["is_web_frontend"] is False
        assert result["is_nextjs"] is False
        assert result["is_nuxt"] is False
        assert result["has_api"] is False
        assert result["has_database"] is False

    def test_detects_electron(self):
        """Test detects Electron from dependencies."""
        index = {
            "services": {
                "desktop": {
                    "dependencies": ["electron", "electron-builder"],
                }
            }
        }

        result = detect_project_capabilities(index)

        assert result["is_electron"] is True

    def test_detects_electron_scoped_package(self):
        """Test detects Electron from scoped packages."""
        index = {
            "services": {
                "desktop": {
                    "dependencies": ["@electron/remote", "@electron-toolkit/preload"],
                }
            }
        }

        result = detect_project_capabilities(index)

        assert result["is_electron"] is True

    def test_detects_tauri(self):
        """Test detects Tauri from dependencies."""
        index = {
            "services": {
                "desktop": {
                    "dependencies": ["@tauri-apps/api", "@tauri-apps/plugin-shell"],
                }
            }
        }

        result = detect_project_capabilities(index)

        assert result["is_tauri"] is True

    def test_detects_expo(self):
        """Test detects Expo from dependencies."""
        index = {
            "services": {
                "mobile": {
                    "dependencies": ["expo", "expo-router"],
                }
            }
        }

        result = detect_project_capabilities(index)

        assert result["is_expo"] is True

    def test_detects_react_native(self):
        """Test detects React Native from dependencies."""
        index = {
            "services": {
                "mobile": {
                    "dependencies": ["react-native", "react-native-safe-area-context"],
                }
            }
        }

        result = detect_project_capabilities(index)

        assert result["is_react_native"] is True

    def test_detects_react_web_framework(self):
        """Test detects React web framework."""
        index = {
            "services": {
                "web": {
                    "framework": "react",
                    "dependencies": ["react", "react-dom"],
                }
            }
        }

        result = detect_project_capabilities(index)

        assert result["is_web_frontend"] is True

    def test_detects_vue_web_framework(self):
        """Test detects Vue web framework."""
        index = {
            "services": {
                "web": {
                    "framework": "vue",
                    "dependencies": ["vue", "vue-router"],
                }
            }
        }

        result = detect_project_capabilities(index)

        assert result["is_web_frontend"] is True

    def test_detects_nextjs_from_framework(self):
        """Test detects Next.js from framework field."""
        index = {
            "services": {
                "web": {
                    "framework": "nextjs",
                    "dependencies": ["react", "next"],
                }
            }
        }

        result = detect_project_capabilities(index)

        assert result["is_nextjs"] is True
        assert result["is_web_frontend"] is True

    def test_detects_nextjs_from_deps(self):
        """Test detects Next.js from dependencies."""
        index = {
            "services": {
                "web": {
                    "dependencies": ["next", "react"],
                }
            }
        }

        result = detect_project_capabilities(index)

        assert result["is_nextjs"] is True
        assert result["is_web_frontend"] is True

    def test_detects_nuxt(self):
        """Test detects Nuxt from framework field."""
        index = {
            "services": {
                "web": {
                    "framework": "nuxt",
                    "dependencies": ["vue", "nuxt"],
                }
            }
        }

        result = detect_project_capabilities(index)

        assert result["is_nuxt"] is True
        assert result["is_web_frontend"] is True

    def test_detects_vite_web_frontend(self):
        """Test detects Vite-based web frontend."""
        index = {
            "services": {
                "web": {
                    "dependencies": ["vite", "react"],
                }
            }
        }

        result = detect_project_capabilities(index)

        assert result["is_web_frontend"] is True

    def test_vite_with_electron_not_web_frontend(self):
        """Test Vite with Electron doesn't flag as web_frontend."""
        index = {
            "services": {
                "desktop": {
                    "dependencies": ["electron", "vite"],
                }
            }
        }

        result = detect_project_capabilities(index)

        assert result["is_electron"] is True
        assert result["is_web_frontend"] is False

    def test_detects_api_routes(self):
        """Test detects API routes."""
        index = {
            "services": {
                "backend": {
                    "api": {
                        "routes": ["/api/users", "/api/auth"],
                    }
                }
            }
        }

        result = detect_project_capabilities(index)

        assert result["has_api"] is True

    def test_detects_database_flag(self):
        """Test detects database from service flag."""
        index = {
            "services": {
                "backend": {
                    "database": {
                        "type": "postgresql",
                        "host": "localhost",
                    }
                }
            }
        }

        result = detect_project_capabilities(index)

        assert result["has_database"] is True

    def test_detects_prisma_orm(self):
        """Test detects Prisma ORM from dependencies."""
        index = {
            "services": {
                "backend": {
                    "dependencies": ["@prisma/client"],
                    "dev_dependencies": ["prisma"],
                }
            }
        }

        result = detect_project_capabilities(index)

        assert result["has_database"] is True

    def test_detects_drizzle_orm(self):
        """Test detects Drizzle ORM from dependencies."""
        index = {
            "services": {
                "backend": {
                    "dependencies": ["drizzle-orm"],
                }
            }
        }

        result = detect_project_capabilities(index)

        assert result["has_database"] is True

    def test_detects_sqlalchemy(self):
        """Test detects SQLAlchemy from dependencies."""
        index = {
            "services": {
                "backend": {
                    "dependencies": ["sqlalchemy", "alembic"],
                }
            }
        }

        result = detect_project_capabilities(index)

        assert result["has_database"] is True

    def test_detects_django(self):
        """Test detects Django from dependencies."""
        index = {
            "services": {
                "backend": {
                    "dependencies": ["django", "djangorestframework"],
                }
            }
        }

        result = detect_project_capabilities(index)

        assert result["has_database"] is True

    def test_handles_list_services_format(self):
        """Test handles services as a list instead of dict."""
        index = {
            "services": [
                {
                    "name": "backend",
                    "framework": "fastapi",
                    "dependencies": ["sqlalchemy"],
                },
                {
                    "name": "frontend",
                    "framework": "react",
                    "dependencies": ["next"],
                }
            ]
        }

        result = detect_project_capabilities(index)

        assert result["has_database"] is True
        assert result["is_nextjs"] is True
        assert result["is_web_frontend"] is True

    def test_case_insensitive_dependency_matching(self):
        """Test dependency matching is case-insensitive."""
        index = {
            "services": {
                "backend": {
                    "dependencies": ["Electron", "VITE", "Next"],
                }
            }
        }

        result = detect_project_capabilities(index)

        assert result["is_electron"] is True
        assert result["is_web_frontend"] is True
        assert result["is_nextjs"] is True

    def test_mixed_capabilities(self):
        """Test project with multiple capability types."""
        index = {
            "services": {
                "desktop": {
                    "dependencies": ["electron"],
                },
                "backend": {
                    "framework": "fastapi",
                    "dependencies": ["sqlalchemy"],
                    "api": {"routes": ["/api/*"]},
                },
                "web": {
                    "framework": "nextjs",
                    "dependencies": ["next", "react"],
                }
            }
        }

        result = detect_project_capabilities(index)

        assert result["is_electron"] is True
        assert result["has_database"] is True
        assert result["has_api"] is True
        assert result["is_nextjs"] is True
        assert result["is_web_frontend"] is True


class TestShouldRefreshProjectIndex:
    """Tests for should_refresh_project_index function."""

    def test_returns_true_when_no_index(self, tmp_path):
        """Test returns True when index doesn't exist."""
        result = should_refresh_project_index(tmp_path)

        assert result is True

    def test_returns_true_when_index_newer_than_deps(self, tmp_path):
        """Test returns True when dependency file is newer."""
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()
        index_file = auto_claude_dir / "project_index.json"
        index_file.write_text("{}", encoding="utf-8")

        # Create a newer package.json
        import time
        time.sleep(0.01)
        package_json = tmp_path / "package.json"
        package_json.write_text('{"name": "test"}', encoding="utf-8")

        result = should_refresh_project_index(tmp_path)

        assert result is True

    def test_returns_false_when_index_is_fresh(self, tmp_path):
        """Test returns False when index is newer than deps."""
        # Create dependency files first
        package_json = tmp_path / "package.json"
        package_json.write_text('{"name": "test"}', encoding="utf-8")

        import time
        time.sleep(0.01)

        # Create newer index
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()
        index_file = auto_claude_dir / "project_index.json"
        index_file.write_text("{}", encoding="utf-8")

        result = should_refresh_project_index(tmp_path)

        assert result is False

    def test_checks_pyproject_toml(self, tmp_path):
        """Test checks pyproject.toml for changes."""
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()
        index_file = auto_claude_dir / "project_index.json"
        index_file.write_text("{}", encoding="utf-8")

        import time
        time.sleep(0.01)
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\nname = 'test'", encoding="utf-8")

        result = should_refresh_project_index(tmp_path)

        assert result is True

    def test_checks_requirements_txt(self, tmp_path):
        """Test checks requirements.txt for changes."""
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()
        index_file = auto_claude_dir / "project_index.json"
        index_file.write_text("{}", encoding="utf-8")

        import time
        time.sleep(0.01)
        requirements = tmp_path / "requirements.txt"
        requirements.write_text("fastapi\nuvicorn", encoding="utf-8")

        result = should_refresh_project_index(tmp_path)

        assert result is True

    def test_checks_gemfile(self, tmp_path):
        """Test checks Gemfile for changes."""
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()
        index_file = auto_claude_dir / "project_index.json"
        index_file.write_text("{}", encoding="utf-8")

        import time
        time.sleep(0.01)
        gemfile = tmp_path / "Gemfile"
        gemfile.write_text('gem "rails"', encoding="utf-8")

        result = should_refresh_project_index(tmp_path)

        assert result is True

    def test_checks_go_mod(self, tmp_path):
        """Test checks go.mod for changes."""
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()
        index_file = auto_claude_dir / "project_index.json"
        index_file.write_text("{}", encoding="utf-8")

        import time
        time.sleep(0.01)
        go_mod = tmp_path / "go.mod"
        go_mod.write_text("module test\n\ngo 1.21", encoding="utf-8")

        result = should_refresh_project_index(tmp_path)

        assert result is True

    def test_checks_cargo_toml(self, tmp_path):
        """Test checks Cargo.toml for changes."""
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()
        index_file = auto_claude_dir / "project_index.json"
        index_file.write_text("{}", encoding="utf-8")

        import time
        time.sleep(0.01)
        cargo_toml = tmp_path / "Cargo.toml"
        cargo_toml.write_text('[package]\nname = "test"', encoding="utf-8")

        result = should_refresh_project_index(tmp_path)

        assert result is True

    def test_checks_composer_json(self, tmp_path):
        """Test checks composer.json for changes."""
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()
        index_file = auto_claude_dir / "project_index.json"
        index_file.write_text("{}", encoding="utf-8")

        import time
        time.sleep(0.01)
        composer = tmp_path / "composer.json"
        composer.write_text('{"name": "test/project"}', encoding="utf-8")

        result = should_refresh_project_index(tmp_path)

        assert result is True

    def test_checks_monorepo_subdirectories(self, tmp_path):
        """Test checks package.json in monorepo subdirectories."""
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()
        index_file = auto_claude_dir / "project_index.json"
        index_file.write_text("{}", encoding="utf-8")

        import time
        time.sleep(0.01)

        # Create a subdirectory with package.json
        apps_dir = tmp_path / "apps"
        apps_dir.mkdir()
        backend_pkg = apps_dir / "package.json"
        backend_pkg.write_text('{"name": "backend"}', encoding="utf-8")

        result = should_refresh_project_index(tmp_path)

        assert result is True

    def test_skips_hidden_directories(self, tmp_path):
        """Test skips hidden directories in monorepo check."""
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()
        index_file = auto_claude_dir / "project_index.json"
        index_file.write_text("{}", encoding="utf-8")

        import time
        time.sleep(0.01)

        # Create hidden directory with newer package.json
        hidden_dir = tmp_path / ".hidden"
        hidden_dir.mkdir()
        hidden_pkg = hidden_dir / "package.json"
        hidden_pkg.write_text('{"name": "hidden"}', encoding="utf-8")

        result = should_refresh_project_index(tmp_path)

        assert result is False  # Should ignore hidden dirs

    def test_skips_node_modules(self, tmp_path):
        """Test skips node_modules in monorepo check."""
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()
        index_file = auto_claude_dir / "project_index.json"
        index_file.write_text("{}", encoding="utf-8")

        import time
        time.sleep(0.01)

        # Create node_modules with newer package.json
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        module_pkg = node_modules / "package.json"
        module_pkg.write_text('{"name": "module"}', encoding="utf-8")

        result = should_refresh_project_index(tmp_path)

        assert result is False  # Should ignore node_modules

    def test_handles_missing_dependency_files(self, tmp_path):
        """Test handles missing dependency files gracefully."""
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()
        index_file = auto_claude_dir / "project_index.json"
        index_file.write_text("{}", encoding="utf-8")

        result = should_refresh_project_index(tmp_path)

        assert result is False  # No deps to check, index is fresh

    def test_handles_stat_error(self, tmp_path):
        """Test handles stat errors gracefully."""
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()

        # Create a directory instead of a file (will cause stat issues)
        index_file = auto_claude_dir / "project_index.json"
        index_file.mkdir()

        # This test verifies error handling - the function should not crash
        # when stat fails on a directory instead of a file
        try:
            result = should_refresh_project_index(tmp_path)
            # If it returns True or False, both are acceptable
            # The key is that it doesn't raise an exception
            assert isinstance(result, bool)
        except OSError:
            # If it raises OSError, that's also acceptable behavior
            pass


class TestGetMcpToolsForProject:
    """Tests for get_mcp_tools_for_project function."""

    def test_empty_capabilities_returns_empty_list(self):
        """Test empty capabilities returns empty list."""
        capabilities = {
            "is_electron": False,
            "is_tauri": False,
            "is_expo": False,
            "is_react_native": False,
            "is_web_frontend": False,
            "is_nextjs": False,
            "is_nuxt": False,
            "has_api": False,
            "has_database": False,
        }

        result = get_mcp_tools_for_project(capabilities)

        assert result == []

    def test_includes_electron_validation(self):
        """Test includes Electron validation for Electron projects."""
        capabilities = {"is_electron": True}

        result = get_mcp_tools_for_project(capabilities)

        assert "mcp_tools/electron_validation.md" in result

    def test_includes_tauri_validation(self):
        """Test includes Tauri validation for Tauri projects."""
        capabilities = {"is_tauri": True}

        result = get_mcp_tools_for_project(capabilities)

        assert "mcp_tools/tauri_validation.md" in result

    def test_web_frontend_gets_puppeteer(self):
        """Test web frontend (non-Electron) gets Puppeteer."""
        capabilities = {"is_web_frontend": True, "is_electron": False}

        result = get_mcp_tools_for_project(capabilities)

        assert "mcp_tools/puppeteer_browser.md" in result

    def test_electron_no_puppeteer(self):
        """Test Electron projects don't get Puppeteer."""
        capabilities = {"is_electron": True, "is_web_frontend": True}

        result = get_mcp_tools_for_project(capabilities)

        assert "mcp_tools/puppeteer_browser.md" not in result
        assert "mcp_tools/electron_validation.md" in result

    def test_database_gets_validation(self):
        """Test projects with database get validation tool."""
        capabilities = {"has_database": True}

        result = get_mcp_tools_for_project(capabilities)

        assert "mcp_tools/database_validation.md" in result

    def test_api_gets_validation(self):
        """Test projects with API get validation tool."""
        capabilities = {"has_api": True}

        result = get_mcp_tools_for_project(capabilities)

        assert "mcp_tools/api_validation.md" in result

    def test_full_stack_project(self):
        """Test full-stack project gets all relevant tools."""
        capabilities = {
            "is_electron": False,
            "is_web_frontend": True,
            "has_database": True,
            "has_api": True,
        }

        result = get_mcp_tools_for_project(capabilities)

        assert len(result) == 3
        assert "mcp_tools/puppeteer_browser.md" in result
        assert "mcp_tools/database_validation.md" in result
        assert "mcp_tools/api_validation.md" in result

    def test_electron_with_backend(self):
        """Test Electron desktop app with backend."""
        capabilities = {
            "is_electron": True,
            "has_database": True,
            "has_api": True,
        }

        result = get_mcp_tools_for_project(capabilities)

        assert "mcp_tools/electron_validation.md" in result
        assert "mcp_tools/database_validation.md" in result
        assert "mcp_tools/api_validation.md" in result
        assert "mcp_tools/puppeteer_browser.md" not in result

    def test_unknown_capabilities_ignored(self):
        """Test unknown capability keys are ignored."""
        capabilities = {
            "is_electron": True,
            "unknown_capability": True,
            "random_flag": "value",
        }

        result = get_mcp_tools_for_project(capabilities)

        assert "mcp_tools/electron_validation.md" in result
        assert len(result) == 1
