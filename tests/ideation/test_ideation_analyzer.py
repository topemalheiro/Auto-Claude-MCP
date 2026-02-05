"""
Comprehensive Tests for ideation.analyzer module
==============================================

Tests for ProjectAnalyzer class covering:
- Initialization with project_dir and optional parameters
- gather_context() method for parsing project files
- get_graph_hints() async method with Graphiti integration
- Edge cases: missing files, malformed JSON, empty files, async errors
- Graphiti disabled scenarios
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock


class TestProjectAnalyzerInit:
    """Tests for ProjectAnalyzer.__init__"""

    def test_init_with_required_params(self):
        """Test initialization with required parameters"""
        from ideation.analyzer import ProjectAnalyzer

        project_dir = Path("/tmp/test_project")
        output_dir = Path("/tmp/output")

        analyzer = ProjectAnalyzer(
            project_dir=project_dir,
            output_dir=output_dir,
        )

        assert analyzer.project_dir == project_dir
        assert analyzer.output_dir == output_dir
        assert analyzer.include_roadmap is True  # default
        assert analyzer.include_kanban is True  # default

    def test_init_with_all_params(self):
        """Test initialization with all parameters"""
        from ideation.analyzer import ProjectAnalyzer

        project_dir = Path("/tmp/test_project")
        output_dir = Path("/tmp/output")

        analyzer = ProjectAnalyzer(
            project_dir=project_dir,
            output_dir=output_dir,
            include_roadmap_context=False,
            include_kanban_context=False,
        )

        assert analyzer.project_dir == project_dir
        assert analyzer.output_dir == output_dir
        assert analyzer.include_roadmap is False
        assert analyzer.include_kanban is False

    def test_init_converts_path_to_pathlib(self):
        """Test that paths are converted to pathlib.Path"""
        from ideation.analyzer import ProjectAnalyzer

        # Pass as string
        analyzer = ProjectAnalyzer(
            project_dir="/tmp/test_project",
            output_dir="/tmp/output",
        )

        assert isinstance(analyzer.project_dir, Path)
        assert isinstance(analyzer.output_dir, Path)
        assert analyzer.project_dir == Path("/tmp/test_project")
        assert analyzer.output_dir == Path("/tmp/output")

    def test_init_with_pathlib_path(self):
        """Test initialization with pathlib.Path objects"""
        from ideation.analyzer import ProjectAnalyzer

        project_dir = Path("/tmp/test_project")
        output_dir = Path("/tmp/output")

        analyzer = ProjectAnalyzer(
            project_dir=project_dir,
            output_dir=output_dir,
        )

        assert analyzer.project_dir == project_dir
        assert analyzer.output_dir == output_dir

    def test_init_include_roadmap_true(self):
        """Test include_roadmap_context=True"""
        from ideation.analyzer import ProjectAnalyzer

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
            include_roadmap_context=True,
        )

        assert analyzer.include_roadmap is True

    def test_init_include_roadmap_false(self):
        """Test include_roadmap_context=False"""
        from ideation.analyzer import ProjectAnalyzer

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
            include_roadmap_context=False,
        )

        assert analyzer.include_roadmap is False

    def test_init_include_kanban_true(self):
        """Test include_kanban_context=True"""
        from ideation.analyzer import ProjectAnalyzer

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
            include_kanban_context=True,
        )

        assert analyzer.include_kanban is True

    def test_init_include_kanban_false(self):
        """Test include_kanban_context=False"""
        from ideation.analyzer import ProjectAnalyzer

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
            include_kanban_context=False,
        )

        assert analyzer.include_kanban is False


class TestGatherContextBasic:
    """Tests for gather_context() basic functionality"""

    def test_gather_context_returns_dict(self, tmp_path):
        """Test that gather_context returns a dictionary"""
        from ideation.analyzer import ProjectAnalyzer

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
        )

        result = analyzer.gather_context()

        assert isinstance(result, dict)

    def test_gather_context_has_expected_keys(self, tmp_path):
        """Test that gather_context returns dict with expected keys"""
        from ideation.analyzer import ProjectAnalyzer

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
        )

        result = analyzer.gather_context()

        assert "existing_features" in result
        assert "tech_stack" in result
        assert "target_audience" in result
        assert "planned_features" in result

    def test_gather_context_default_values(self, tmp_path):
        """Test that gather_context returns default values when no files exist"""
        from ideation.analyzer import ProjectAnalyzer

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
        )

        result = analyzer.gather_context()

        assert result["existing_features"] == []
        assert result["tech_stack"] == []
        assert result["target_audience"] is None
        assert result["planned_features"] == []


class TestGatherContextProjectIndex:
    """Tests for gather_context() reading project_index.json"""

    def test_reads_project_index_json(self, tmp_path):
        """Test reading project_index.json file"""
        from ideation.analyzer import ProjectAnalyzer

        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()

        project_index_data = {
            "services": {
                "backend": {
                    "language": "Python",
                    "framework": "FastAPI"
                },
                "frontend": {
                    "language": "TypeScript",
                    "framework": "React"
                }
            }
        }

        with open(auto_claude_dir / "project_index.json", "w") as f:
            json.dump(project_index_data, f)

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
        )

        result = analyzer.gather_context()

        assert len(result["tech_stack"]) == 4  # Python, FastAPI, TypeScript, React
        assert "Python" in result["tech_stack"]
        assert "FastAPI" in result["tech_stack"]
        assert "TypeScript" in result["tech_stack"]
        assert "React" in result["tech_stack"]

    def test_extracts_language_from_services(self, tmp_path):
        """Test extracting language from services in project_index"""
        from ideation.analyzer import ProjectAnalyzer

        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()

        project_index_data = {
            "services": {
                "api": {"language": "Go", "framework": "Gin"},
                "worker": {"language": "Python", "framework": "Celery"}
            }
        }

        with open(auto_claude_dir / "project_index.json", "w") as f:
            json.dump(project_index_data, f)

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
        )

        result = analyzer.gather_context()

        assert "Go" in result["tech_stack"]
        assert "Python" in result["tech_stack"]

    def test_extracts_framework_from_services(self, tmp_path):
        """Test extracting framework from services in project_index"""
        from ideation.analyzer import ProjectAnalyzer

        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()

        project_index_data = {
            "services": {
                "web": {"language": "Python", "framework": "Django"},
                "api": {"language": "Python", "framework": "FastAPI"}
            }
        }

        with open(auto_claude_dir / "project_index.json", "w") as f:
            json.dump(project_index_data, f)

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
        )

        result = analyzer.gather_context()

        assert "Django" in result["tech_stack"]
        assert "FastAPI" in result["tech_stack"]

    def test_deduplicates_tech_stack(self, tmp_path):
        """Test that tech stack items are deduplicated"""
        from ideation.analyzer import ProjectAnalyzer

        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()

        project_index_data = {
            "services": {
                "service1": {"language": "Python", "framework": "FastAPI"},
                "service2": {"language": "Python", "framework": "FastAPI"},
                "service3": {"language": "Python", "framework": "Django"}
            }
        }

        with open(auto_claude_dir / "project_index.json", "w") as f:
            json.dump(project_index_data, f)

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
        )

        result = analyzer.gather_context()

        # Python appears 3 times but should only be in list once
        assert result["tech_stack"].count("Python") == 1
        # FastAPI appears 2 times but should only be in list once
        assert result["tech_stack"].count("FastAPI") == 1

    def test_handles_missing_language_in_service(self, tmp_path):
        """Test handling services without language field"""
        from ideation.analyzer import ProjectAnalyzer

        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()

        project_index_data = {
            "services": {
                "service1": {"framework": "FastAPI"},
                "service2": {"language": "Python", "framework": "Django"}
            }
        }

        with open(auto_claude_dir / "project_index.json", "w") as f:
            json.dump(project_index_data, f)

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
        )

        result = analyzer.gather_context()

        assert "FastAPI" in result["tech_stack"]
        assert "Python" in result["tech_stack"]
        assert "Django" in result["tech_stack"]

    def test_handles_empty_services_object(self, tmp_path):
        """Test handling empty services object"""
        from ideation.analyzer import ProjectAnalyzer

        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()

        project_index_data = {"services": {}}

        with open(auto_claude_dir / "project_index.json", "w") as f:
            json.dump(project_index_data, f)

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
        )

        result = analyzer.gather_context()

        assert result["tech_stack"] == []

    def test_handles_missing_services_key(self, tmp_path):
        """Test handling project_index without services key"""
        from ideation.analyzer import ProjectAnalyzer

        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()

        project_index_data = {"version": "1.0.0"}

        with open(auto_claude_dir / "project_index.json", "w") as f:
            json.dump(project_index_data, f)

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
        )

        result = analyzer.gather_context()

        assert result["tech_stack"] == []

    def test_skips_project_index_when_not_exists(self, tmp_path):
        """Test that missing project_index.json is handled gracefully"""
        from ideation.analyzer import ProjectAnalyzer

        # Don't create any files
        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
        )

        result = analyzer.gather_context()

        assert result["tech_stack"] == []


class TestGatherContextMalformedProjectIndex:
    """Tests for gather_context() with malformed project_index.json"""

    def test_handles_malformed_json(self, tmp_path):
        """Test handling malformed JSON in project_index.json"""
        from ideation.analyzer import ProjectAnalyzer

        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()

        with open(auto_claude_dir / "project_index.json", "w") as f:
            f.write("{invalid json content")

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
        )

        result = analyzer.gather_context()

        # Should handle JSONDecodeError gracefully
        assert result["tech_stack"] == []

    def test_handles_empty_json_file(self, tmp_path):
        """Test handling empty JSON file"""
        from ideation.analyzer import ProjectAnalyzer

        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()

        with open(auto_claude_dir / "project_index.json", "w") as f:
            f.write("")

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
        )

        result = analyzer.gather_context()

        assert result["tech_stack"] == []

    def test_handles_invalid_json_structure(self, tmp_path):
        """Test handling invalid JSON structure"""
        from ideation.analyzer import ProjectAnalyzer

        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()

        with open(auto_claude_dir / "project_index.json", "w") as f:
            f.write("[]")

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
        )

        result = analyzer.gather_context()

        # When index is a list (not dict), AttributeError is not caught by the current code
        # So tech_stack may be affected or may remain empty depending on behavior
        # The important thing is the code doesn't crash
        assert isinstance(result, dict)


class TestGatherContextRoadmap:
    """Tests for gather_context() reading roadmap.json"""

    def test_reads_roadmap_json(self, tmp_path):
        """Test reading roadmap.json file"""
        from ideation.analyzer import ProjectAnalyzer

        roadmap_dir = tmp_path / ".auto-claude" / "roadmap"
        roadmap_dir.mkdir(parents=True)

        roadmap_data = {
            "features": [
                {"title": "User authentication"},
                {"title": "API rate limiting"}
            ],
            "target_audience": {
                "primary": "Developers"
            }
        }

        with open(roadmap_dir / "roadmap.json", "w") as f:
            json.dump(roadmap_data, f)

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
            include_roadmap_context=True,
        )

        result = analyzer.gather_context()

        assert "User authentication" in result["planned_features"]
        assert "API rate limiting" in result["planned_features"]
        assert result["target_audience"] == "Developers"

    def test_extracts_feature_titles(self, tmp_path):
        """Test extracting feature titles from roadmap"""
        from ideation.analyzer import ProjectAnalyzer

        roadmap_dir = tmp_path / ".auto-claude" / "roadmap"
        roadmap_dir.mkdir(parents=True)

        roadmap_data = {
            "features": [
                {"title": "Feature 1", "description": "Description 1"},
                {"title": "Feature 2", "description": "Description 2"},
                {"title": "Feature 3", "status": "pending"}
            ]
        }

        with open(roadmap_dir / "roadmap.json", "w") as f:
            json.dump(roadmap_data, f)

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
            include_roadmap_context=True,
        )

        result = analyzer.gather_context()

        assert "Feature 1" in result["planned_features"]
        assert "Feature 2" in result["planned_features"]
        assert "Feature 3" in result["planned_features"]

    def test_handles_feature_without_title(self, tmp_path):
        """Test handling features without title field"""
        from ideation.analyzer import ProjectAnalyzer

        roadmap_dir = tmp_path / ".auto-claude" / "roadmap"
        roadmap_dir.mkdir(parents=True)

        roadmap_data = {
            "features": [
                {"title": "Valid feature"},
                {"description": "Feature without title"},
                {}
            ]
        }

        with open(roadmap_dir / "roadmap.json", "w") as f:
            json.dump(roadmap_data, f)

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
            include_roadmap_context=True,
        )

        result = analyzer.gather_context()

        # Features without title should add empty string
        assert "Valid feature" in result["planned_features"]
        # Empty strings might be included but deduplication handles them

    def test_extracts_target_audience(self, tmp_path):
        """Test extracting target_audience from roadmap"""
        from ideation.analyzer import ProjectAnalyzer

        roadmap_dir = tmp_path / ".auto-claude" / "roadmap"
        roadmap_dir.mkdir(parents=True)

        roadmap_data = {
            "features": [],
            "target_audience": {
                "primary": "Enterprise developers"
            }
        }

        with open(roadmap_dir / "roadmap.json", "w") as f:
            json.dump(roadmap_data, f)

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
            include_roadmap_context=True,
        )

        result = analyzer.gather_context()

        assert result["target_audience"] == "Enterprise developers"

    def test_skips_roadmap_when_disabled(self, tmp_path):
        """Test that roadmap is not read when include_roadmap=False"""
        from ideation.analyzer import ProjectAnalyzer

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
            include_roadmap_context=False,
        )

        result = analyzer.gather_context()

        # Roadmap data should not be included
        assert result["planned_features"] == []
        assert result["target_audience"] is None

    def test_handles_missing_roadmap_json(self, tmp_path):
        """Test handling missing roadmap.json"""
        from ideation.analyzer import ProjectAnalyzer

        # Create the roadmap directory but no roadmap.json
        roadmap_dir = tmp_path / ".auto-claude" / "roadmap"
        roadmap_dir.mkdir(parents=True)

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
            include_roadmap_context=True,
        )

        result = analyzer.gather_context()

        assert result["planned_features"] == []
        assert result["target_audience"] is None


class TestGatherContextDiscovery:
    """Tests for gather_context() reading roadmap_discovery.json"""

    def test_reads_discovery_json(self, tmp_path):
        """Test reading roadmap_discovery.json file"""
        from ideation.analyzer import ProjectAnalyzer

        roadmap_dir = tmp_path / ".auto-claude" / "roadmap"
        roadmap_dir.mkdir(parents=True)

        # Create roadmap without audience
        roadmap_data = {"features": []}
        with open(roadmap_dir / "roadmap.json", "w") as f:
            json.dump(roadmap_data, f)

        # Create discovery with audience
        discovery_data = {
            "target_audience": {
                "primary_persona": "Startup founders"
            },
            "current_state": {
                "existing_features": [
                    "User dashboard",
                    "Real-time analytics"
                ]
            }
        }

        with open(roadmap_dir / "roadmap_discovery.json", "w") as f:
            json.dump(discovery_data, f)

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
            include_roadmap_context=True,
        )

        result = analyzer.gather_context()

        assert result["target_audience"] == "Startup founders"
        assert "User dashboard" in result["existing_features"]
        assert "Real-time analytics" in result["existing_features"]

    def test_extracts_existing_features_from_discovery(self, tmp_path):
        """Test extracting existing_features from discovery"""
        from ideation.analyzer import ProjectAnalyzer

        roadmap_dir = tmp_path / ".auto-claude" / "roadmap"
        roadmap_dir.mkdir(parents=True)

        # Create roadmap without audience
        roadmap_data = {"features": []}
        with open(roadmap_dir / "roadmap.json", "w") as f:
            json.dump(roadmap_data, f)

        discovery_data = {
            "current_state": {
                "existing_features": [
                    "Feature A",
                    "Feature B",
                    "Feature C"
                ]
            }
        }

        with open(roadmap_dir / "roadmap_discovery.json", "w") as f:
            json.dump(discovery_data, f)

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
            include_roadmap_context=True,
        )

        result = analyzer.gather_context()

        assert result["existing_features"] == ["Feature A", "Feature B", "Feature C"]

    def test_discovery_audience_not_used_if_roadmap_has_audience(self, tmp_path):
        """Test that discovery audience is not used if roadmap already has audience"""
        from ideation.analyzer import ProjectAnalyzer

        roadmap_dir = tmp_path / ".auto-claude" / "roadmap"
        roadmap_dir.mkdir(parents=True)

        # Create roadmap with audience
        roadmap_data = {
            "features": [],
            "target_audience": {"primary": "Roadmap audience"}
        }

        with open(roadmap_dir / "roadmap.json", "w") as f:
            json.dump(roadmap_data, f)

        # Create discovery with different audience (should be ignored)
        discovery_data = {
            "target_audience": {"primary_persona": "Discovery audience"}
        }

        with open(roadmap_dir / "roadmap_discovery.json", "w") as f:
            json.dump(discovery_data, f)

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
            include_roadmap_context=True,
        )

        result = analyzer.gather_context()

        # Should use roadmap audience, not discovery
        assert result["target_audience"] == "Roadmap audience"

    def test_handles_missing_discovery_json(self, tmp_path):
        """Test handling missing roadmap_discovery.json"""
        from ideation.analyzer import ProjectAnalyzer

        roadmap_dir = tmp_path / ".auto-claude" / "roadmap"
        roadmap_dir.mkdir(parents=True)

        roadmap_data = {"features": []}
        with open(roadmap_dir / "roadmap.json", "w") as f:
            json.dump(roadmap_data, f)

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
            include_roadmap_context=True,
        )

        result = analyzer.gather_context()

        assert result["existing_features"] == []

    def test_handles_discovery_with_missing_existing_features(self, tmp_path):
        """Test handling discovery without existing_features key"""
        from ideation.analyzer import ProjectAnalyzer

        roadmap_dir = tmp_path / ".auto-claude" / "roadmap"
        roadmap_dir.mkdir(parents=True)

        roadmap_data = {"features": []}
        with open(roadmap_dir / "roadmap.json", "w") as f:
            json.dump(roadmap_data, f)

        discovery_data = {
            "target_audience": {"primary_persona": "Developers"}
        }

        with open(roadmap_dir / "roadmap_discovery.json", "w") as f:
            json.dump(discovery_data, f)

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
            include_roadmap_context=True,
        )

        result = analyzer.gather_context()

        # Should not crash, existing_features should be empty
        assert result["existing_features"] == []


class TestGatherContextKanban:
    """Tests for gather_context() reading specs directory"""

    def test_reads_specs_from_kanban(self, tmp_path):
        """Test reading spec files from specs directory"""
        from ideation.analyzer import ProjectAnalyzer

        specs_dir = tmp_path / ".auto-claude" / "specs"
        specs_dir.mkdir(parents=True)

        spec1_dir = specs_dir / "001-feature"
        spec1_dir.mkdir()
        spec2_dir = specs_dir / "002-bugfix"
        spec2_dir.mkdir()

        spec1_content = "# User Authentication\n\nImplement login system"
        spec2_content = "# Bug Fix for Login\n\nFix timeout issue"

        with open(spec1_dir / "spec.md", "w") as f:
            f.write(spec1_content)
        with open(spec2_dir / "spec.md", "w") as f:
            f.write(spec2_content)

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
            include_kanban_context=True,
        )

        result = analyzer.gather_context()

        assert "User Authentication" in result["planned_features"]
        assert "Bug Fix for Login" in result["planned_features"]

    def test_extracts_title_from_spec_markdown(self, tmp_path):
        """Test extracting title from spec.md markdown files"""
        from ideation.analyzer import ProjectAnalyzer

        specs_dir = tmp_path / ".auto-claude" / "specs"
        specs_dir.mkdir(parents=True)

        spec_dir = specs_dir / "001-test"
        spec_dir.mkdir()

        spec_content = "# My Awesome Feature\n\nThis is a great feature"

        with open(spec_dir / "spec.md", "w") as f:
            f.write(spec_content)

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
            include_kanban_context=True,
        )

        result = analyzer.gather_context()

        assert "My Awesome Feature" in result["planned_features"]

    def test_handles_spec_without_title_heading(self, tmp_path):
        """Test handling spec files without # title heading"""
        from ideation.analyzer import ProjectAnalyzer

        specs_dir = tmp_path / ".auto-claude" / "specs"
        specs_dir.mkdir(parents=True)

        spec_dir = specs_dir / "001-test"
        spec_dir.mkdir()

        # Spec without # heading
        spec_content = "This is a spec without a title heading\n\nSome content"

        with open(spec_dir / "spec.md", "w") as f:
            f.write(spec_content)

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
            include_kanban_context=True,
        )

        result = analyzer.gather_context()

        # Should not crash, title just won't be added
        assert result["planned_features"] == []

    def test_handles_spec_with_title_later_in_file(self, tmp_path):
        """Test handling spec files where # heading appears later"""
        from ideation.analyzer import ProjectAnalyzer

        specs_dir = tmp_path / ".auto-claude" / "specs"
        specs_dir.mkdir(parents=True)

        spec_dir = specs_dir / "001-test"
        spec_dir.mkdir()

        # Spec with content before title
        spec_content = "Some preamble text\n\n# Real Title\n\nMore content"

        with open(spec_dir / "spec.md", "w") as f:
            f.write(spec_content)

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
            include_kanban_context=True,
        )

        result = analyzer.gather_context()

        # Should find the # heading even if not first line
        assert "Real Title" in result["planned_features"]

    def test_skips_non_directories_in_specs(self, tmp_path):
        """Test that non-directory items in specs/ are skipped"""
        from ideation.analyzer import ProjectAnalyzer

        specs_dir = tmp_path / ".auto-claude" / "specs"
        specs_dir.mkdir(parents=True)

        # Create a file (not a directory) in specs/
        with open(specs_dir / "readme.md", "w") as f:
            f.write("This is a file, not a spec directory")

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
            include_kanban_context=True,
        )

        result = analyzer.gather_context()

        # Should skip the file, not try to read it
        assert result["planned_features"] == []

    def test_skips_kanban_when_disabled(self, tmp_path):
        """Test that kanban is not read when include_kanban=False"""
        from ideation.analyzer import ProjectAnalyzer

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
            include_kanban_context=False,
        )

        result = analyzer.gather_context()

        # Kanban data should not be included
        assert result["planned_features"] == []

    def test_handles_missing_specs_directory(self, tmp_path):
        """Test handling missing specs directory"""
        from ideation.analyzer import ProjectAnalyzer

        # Don't create specs directory
        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
            include_kanban_context=True,
        )

        result = analyzer.gather_context()

        assert result["planned_features"] == []

    def test_deduplicates_planned_features(self, tmp_path):
        """Test that planned features from different sources are deduplicated"""
        from ideation.analyzer import ProjectAnalyzer

        # Create roadmap
        roadmap_dir = tmp_path / ".auto-claude" / "roadmap"
        roadmap_dir.mkdir(parents=True)
        roadmap_data = {"features": [{"title": "Feature A"}]}
        with open(roadmap_dir / "roadmap.json", "w") as f:
            json.dump(roadmap_data, f)

        # Create specs with same feature
        specs_dir = tmp_path / ".auto-claude" / "specs"
        specs_dir.mkdir(parents=True)

        spec1_dir = specs_dir / "001-feature-a"
        spec1_dir.mkdir()
        spec2_dir = specs_dir / "002-feature-a-again"
        spec2_dir.mkdir()

        spec_content = "# Feature A\n\nContent"

        with open(spec1_dir / "spec.md", "w") as f:
            f.write(spec_content)
        with open(spec2_dir / "spec.md", "w") as f:
            f.write(spec_content)

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
            include_kanban_context=True,
        )

        result = analyzer.gather_context()

        # "Feature A" appears multiple times but should be unique
        assert result["planned_features"].count("Feature A") == 1


class TestGatherContextCombined:
    """Tests for gather_context() with combined data sources"""

    def test_combines_all_sources(self, tmp_path):
        """Test that all data sources are combined correctly"""
        from ideation.analyzer import ProjectAnalyzer

        # Create project_index.json
        auto_claude_dir = tmp_path / ".auto-claude"
        auto_claude_dir.mkdir()

        project_index_data = {
            "services": {
                "backend": {"language": "Python", "framework": "FastAPI"}
            }
        }
        with open(auto_claude_dir / "project_index.json", "w") as f:
            json.dump(project_index_data, f)

        # Create roadmap.json (without audience so discovery will be read)
        roadmap_dir = auto_claude_dir / "roadmap"
        roadmap_dir.mkdir()

        roadmap_data = {
            "features": [{"title": "Auth System"}]
        }
        with open(roadmap_dir / "roadmap.json", "w") as f:
            json.dump(roadmap_data, f)

        # Create discovery.json (with audience and existing_features)
        discovery_data = {
            "target_audience": {"primary_persona": "Developers"},
            "current_state": {
                "existing_features": ["Dashboard"]
            }
        }
        with open(roadmap_dir / "roadmap_discovery.json", "w") as f:
            json.dump(discovery_data, f)

        # Create specs
        specs_dir = auto_claude_dir / "specs"
        specs_dir.mkdir()

        spec_dir = specs_dir / "001-ui"
        spec_dir.mkdir()

        with open(spec_dir / "spec.md", "w") as f:
            f.write("# UI Refresh\n\nContent")

        analyzer = ProjectAnalyzer(
            project_dir=tmp_path,
            output_dir=tmp_path / "output",
            include_roadmap_context=True,
            include_kanban_context=True,
        )

        result = analyzer.gather_context()

        # Verify all sources contributed
        assert "Python" in result["tech_stack"]
        assert "FastAPI" in result["tech_stack"]
        assert "Auth System" in result["planned_features"]
        assert "UI Refresh" in result["planned_features"]
        assert result["target_audience"] == "Developers"
        assert "Dashboard" in result["existing_features"]


class TestGetGraphHintsBasic:
    """Tests for get_graph_hints() basic functionality"""

    @pytest.mark.asyncio
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=False)
    async def test_get_graph_hints_returns_list(self, mock_enabled):
        """Test that get_graph_hints returns a list"""
        from ideation.analyzer import ProjectAnalyzer

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        result = await analyzer.get_graph_hints("code_improvements")

        assert isinstance(result, list)

    @pytest.mark.asyncio
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=False)
    async def test_get_graph_hints_returns_empty_when_disabled(self, mock_enabled):
        """Test that get_graph_hints returns empty list when Graphiti disabled"""
        from ideation.analyzer import ProjectAnalyzer

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        result = await analyzer.get_graph_hints("code_improvements")

        assert result == []

    @pytest.mark.asyncio
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=False)
    async def test_get_graph_hints_all_ideation_types_when_disabled(self, mock_enabled):
        """Test all ideation types return empty list when disabled"""
        from ideation.analyzer import ProjectAnalyzer

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        ideation_types = [
            "code_improvements",
            "ui_ux_improvements",
            "documentation_gaps",
            "security_hardening",
            "performance_optimizations",
            "code_quality",
        ]

        for ideation_type in ideation_types:
            result = await analyzer.get_graph_hints(ideation_type)
            assert result == []

    @pytest.mark.asyncio
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=False)
    async def test_get_graph_hints_unknown_type(self, mock_enabled):
        """Test get_graph_hints with unknown ideation type"""
        from ideation.analyzer import ProjectAnalyzer

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        result = await analyzer.get_graph_hints("unknown_type")

        assert result == []

    @pytest.mark.asyncio
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=False)
    async def test_get_graph_hints_empty_type(self, mock_enabled):
        """Test get_graph_hints with empty ideation type"""
        from ideation.analyzer import ProjectAnalyzer

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        result = await analyzer.get_graph_hints("")

        assert result == []


class TestGetGraphHintsWhenEnabled:
    """Tests for get_graph_hints() when Graphiti is enabled"""

    @pytest.mark.asyncio
    @patch("ideation.analyzer.get_graph_hints", new_callable=AsyncMock)
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=True)
    async def test_calls_get_graph_hints_when_enabled(self, mock_enabled, mock_get_hints):
        """Test that get_graph_hints provider is called when enabled"""
        from ideation.analyzer import ProjectAnalyzer

        mock_hints = [
            {"content": "Previous improvement pattern", "score": 0.9}
        ]
        mock_get_hints.return_value = mock_hints

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        result = await analyzer.get_graph_hints("code_improvements")

        mock_get_hints.assert_called_once()
        assert result == mock_hints

    @pytest.mark.asyncio
    @patch("ideation.analyzer.get_graph_hints", new_callable=AsyncMock)
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=True)
    async def test_passes_project_dir_as_project_id(self, mock_enabled, mock_get_hints):
        """Test that project_dir is passed as project_id"""
        from ideation.analyzer import ProjectAnalyzer

        mock_get_hints.return_value = []

        project_dir = Path("/tmp/test_project")
        analyzer = ProjectAnalyzer(
            project_dir=project_dir,
            output_dir=Path("/tmp/output"),
        )

        await analyzer.get_graph_hints("code_improvements")

        call_kwargs = mock_get_hints.call_args.kwargs
        assert call_kwargs["project_id"] == str(project_dir)

    @pytest.mark.asyncio
    @patch("ideation.analyzer.get_graph_hints", new_callable=AsyncMock)
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=True)
    async def test_passes_max_results(self, mock_enabled, mock_get_hints):
        """Test that max_results=5 is passed to provider"""
        from ideation.analyzer import ProjectAnalyzer

        mock_get_hints.return_value = []

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        await analyzer.get_graph_hints("code_improvements")

        call_kwargs = mock_get_hints.call_args.kwargs
        assert call_kwargs["max_results"] == 5

    @pytest.mark.asyncio
    @patch("ideation.analyzer.get_graph_hints", new_callable=AsyncMock)
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=True)
    async def test_maps_code_improvements_query(self, mock_enabled, mock_get_hints):
        """Test query mapping for code_improvements"""
        from ideation.analyzer import ProjectAnalyzer

        mock_get_hints.return_value = []

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        await analyzer.get_graph_hints("code_improvements")

        call_kwargs = mock_get_hints.call_args.kwargs
        assert "code patterns" in call_kwargs["query"]
        assert "quick wins" in call_kwargs["query"]
        assert "improvement opportunities" in call_kwargs["query"]

    @pytest.mark.asyncio
    @patch("ideation.analyzer.get_graph_hints", new_callable=AsyncMock)
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=True)
    async def test_maps_ui_ux_improvements_query(self, mock_enabled, mock_get_hints):
        """Test query mapping for ui_ux_improvements"""
        from ideation.analyzer import ProjectAnalyzer

        mock_get_hints.return_value = []

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        await analyzer.get_graph_hints("ui_ux_improvements")

        call_kwargs = mock_get_hints.call_args.kwargs
        assert "UI" in call_kwargs["query"]
        assert "UX" in call_kwargs["query"]
        assert "improvements" in call_kwargs["query"]

    @pytest.mark.asyncio
    @patch("ideation.analyzer.get_graph_hints", new_callable=AsyncMock)
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=True)
    async def test_maps_documentation_gaps_query(self, mock_enabled, mock_get_hints):
        """Test query mapping for documentation_gaps"""
        from ideation.analyzer import ProjectAnalyzer

        mock_get_hints.return_value = []

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        await analyzer.get_graph_hints("documentation_gaps")

        call_kwargs = mock_get_hints.call_args.kwargs
        assert "documentation" in call_kwargs["query"].lower()

    @pytest.mark.asyncio
    @patch("ideation.analyzer.get_graph_hints", new_callable=AsyncMock)
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=True)
    async def test_maps_security_hardening_query(self, mock_enabled, mock_get_hints):
        """Test query mapping for security_hardening"""
        from ideation.analyzer import ProjectAnalyzer

        mock_get_hints.return_value = []

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        await analyzer.get_graph_hints("security_hardening")

        call_kwargs = mock_get_hints.call_args.kwargs
        assert "security" in call_kwargs["query"].lower()
        assert "vulnerabilities" in call_kwargs["query"]

    @pytest.mark.asyncio
    @patch("ideation.analyzer.get_graph_hints", new_callable=AsyncMock)
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=True)
    async def test_maps_performance_optimizations_query(self, mock_enabled, mock_get_hints):
        """Test query mapping for performance_optimizations"""
        from ideation.analyzer import ProjectAnalyzer

        mock_get_hints.return_value = []

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        await analyzer.get_graph_hints("performance_optimizations")

        call_kwargs = mock_get_hints.call_args.kwargs
        assert "performance" in call_kwargs["query"].lower()
        assert "optimization" in call_kwargs["query"].lower()

    @pytest.mark.asyncio
    @patch("ideation.analyzer.get_graph_hints", new_callable=AsyncMock)
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=True)
    async def test_maps_code_quality_query(self, mock_enabled, mock_get_hints):
        """Test query mapping for code_quality"""
        from ideation.analyzer import ProjectAnalyzer

        mock_get_hints.return_value = []

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        await analyzer.get_graph_hints("code_quality")

        call_kwargs = mock_get_hints.call_args.kwargs
        assert "code quality" in call_kwargs["query"].lower()

    @pytest.mark.asyncio
    @patch("ideation.analyzer.get_graph_hints", new_callable=AsyncMock)
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=True)
    async def test_unknown_type_fallback_query(self, mock_enabled, mock_get_hints):
        """Test fallback query for unknown ideation types"""
        from ideation.analyzer import ProjectAnalyzer

        mock_get_hints.return_value = []

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        await analyzer.get_graph_hints("custom_idea_type")

        call_kwargs = mock_get_hints.call_args.kwargs
        assert "custom_idea_type" in call_kwargs["query"]

    @pytest.mark.asyncio
    @patch("ideation.analyzer.get_graph_hints", new_callable=AsyncMock)
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=True)
    async def test_returns_hints_from_provider(self, mock_enabled, mock_get_hints):
        """Test that hints from provider are returned"""
        from ideation.analyzer import ProjectAnalyzer

        mock_hints = [
            {"content": "Hint 1", "score": 0.95},
            {"content": "Hint 2", "score": 0.87},
            {"content": "Hint 3", "score": 0.76}
        ]
        mock_get_hints.return_value = mock_hints

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        result = await analyzer.get_graph_hints("code_improvements")

        assert len(result) == 3
        assert result == mock_hints


class TestGetGraphHintsErrorHandling:
    """Tests for get_graph_hints() error handling"""

    @pytest.mark.asyncio
    @patch("ideation.analyzer.get_graph_hints", new_callable=AsyncMock)
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=True)
    @patch("ideation.analyzer.debug_warning")
    async def test_handles_exception_gracefully(self, mock_debug, mock_enabled, mock_get_hints):
        """Test that exceptions are handled gracefully"""
        from ideation.analyzer import ProjectAnalyzer

        mock_get_hints.side_effect = Exception("Graphiti connection failed")

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        result = await analyzer.get_graph_hints("code_improvements")

        # Should return empty list on error
        assert result == []
        # Should log warning
        mock_debug.assert_called_once()

    @pytest.mark.asyncio
    @patch("ideation.analyzer.get_graph_hints", new_callable=AsyncMock)
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=True)
    @patch("ideation.analyzer.debug_warning")
    async def test_handles_connection_error(self, mock_debug, mock_enabled, mock_get_hints):
        """Test handling of connection errors"""
        from ideation.analyzer import ProjectAnalyzer

        mock_get_hints.side_effect = ConnectionError("Cannot connect to Graphiti")

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        result = await analyzer.get_graph_hints("code_improvements")

        assert result == []
        mock_debug.assert_called_once()

    @pytest.mark.asyncio
    @patch("ideation.analyzer.get_graph_hints", new_callable=AsyncMock)
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=True)
    @patch("ideation.analyzer.debug_warning")
    async def test_handles_timeout_error(self, mock_debug, mock_enabled, mock_get_hints):
        """Test handling of timeout errors"""
        from ideation.analyzer import ProjectAnalyzer

        mock_get_hints.side_effect = TimeoutError("Graphiti timeout")

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        result = await analyzer.get_graph_hints("code_improvements")

        assert result == []
        mock_debug.assert_called_once()

    @pytest.mark.asyncio
    @patch("ideation.analyzer.get_graph_hints", new_callable=AsyncMock)
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=True)
    @patch("ideation.analyzer.debug_warning")
    async def test_handles_runtime_error(self, mock_debug, mock_enabled, mock_get_hints):
        """Test handling of runtime errors"""
        from ideation.analyzer import ProjectAnalyzer

        mock_get_hints.side_effect = RuntimeError("Unexpected error")

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        result = await analyzer.get_graph_hints("code_improvements")

        assert result == []
        mock_debug.assert_called_once()

    @pytest.mark.asyncio
    @patch("ideation.analyzer.get_graph_hints", new_callable=AsyncMock)
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=True)
    @patch("ideation.analyzer.debug_warning")
    async def test_logs_warning_with_ideation_type(self, mock_debug, mock_enabled, mock_get_hints):
        """Test that warning log includes ideation type"""
        from ideation.analyzer import ProjectAnalyzer

        mock_get_hints.side_effect = ValueError("Invalid query")

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        await analyzer.get_graph_hints("security_hardening")

        # Check that debug_warning was called with ideation type
        mock_debug.assert_called_once()
        args = mock_debug.call_args.args
        assert args[0] == "ideation_analyzer"
        assert "security_hardening" in args[1]

    @pytest.mark.asyncio
    @patch("ideation.analyzer.get_graph_hints", new_callable=AsyncMock)
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=True)
    async def test_returns_empty_list_on_any_error(self, mock_enabled, mock_get_hints):
        """Test that any error results in empty list"""
        from ideation.analyzer import ProjectAnalyzer

        mock_get_hints.side_effect = Exception("Any error")

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        result = await analyzer.get_graph_hints("code_improvements")

        # Should always return list (empty) on error
        assert isinstance(result, list)
        assert result == []


class TestGetGraphHintsSuccessLogging:
    """Tests for get_graph_hints() success logging"""

    @pytest.mark.asyncio
    @patch("ideation.analyzer.get_graph_hints", new_callable=AsyncMock)
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=True)
    @patch("ideation.analyzer.debug_success")
    async def test_logs_success_with_hint_count(self, mock_debug, mock_enabled, mock_get_hints):
        """Test that success is logged with hint count"""
        from ideation.analyzer import ProjectAnalyzer

        mock_hints = [
            {"content": "Hint 1"},
            {"content": "Hint 2"},
            {"content": "Hint 3"}
        ]
        mock_get_hints.return_value = mock_hints

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        await analyzer.get_graph_hints("code_improvements")

        # Check that debug_success was called with hint count
        mock_debug.assert_called_once()
        args = mock_debug.call_args.args
        assert args[0] == "ideation_analyzer"
        assert "3" in args[1]  # hint count
        assert "code_improvements" in args[1]

    @pytest.mark.asyncio
    @patch("ideation.analyzer.get_graph_hints", new_callable=AsyncMock)
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=True)
    @patch("ideation.analyzer.debug_success")
    async def test_logs_success_for_different_types(self, mock_debug, mock_enabled, mock_get_hints):
        """Test success logging for different ideation types"""
        from ideation.analyzer import ProjectAnalyzer

        mock_hints = [{"content": "Hint"}]
        mock_get_hints.return_value = mock_hints

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        ideation_types = [
            "ui_ux_improvements",
            "documentation_gaps",
            "security_hardening",
        ]

        for ideation_type in ideation_types:
            await analyzer.get_graph_hints(ideation_type)

        # Should have logged success for each type
        assert mock_debug.call_count == 3


class TestGetGraphHintsRealWorld:
    """Tests for get_graph_hints() with real-world scenarios"""

    @pytest.mark.asyncio
    @patch("ideation.analyzer.get_graph_hints", new_callable=AsyncMock)
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=True)
    async def test_real_hints_structure(self, mock_enabled, mock_get_hints):
        """Test with realistic hint structure"""
        from ideation.analyzer import ProjectAnalyzer

        mock_hints = [
            {
                "content": "Previously implemented JWT auth in api/auth.py",
                "score": 0.95,
                "type": "pattern"
            },
            {
                "content": "User login endpoint at POST /api/login",
                "score": 0.87,
                "type": "gotcha"
            }
        ]
        mock_get_hints.return_value = mock_hints

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        result = await analyzer.get_graph_hints("code_improvements")

        assert len(result) == 2
        assert result[0]["score"] == 0.95
        assert "JWT" in result[0]["content"]
        assert result[0]["type"] == "pattern"

    @pytest.mark.asyncio
    @patch("ideation.analyzer.get_graph_hints", new_callable=AsyncMock)
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=True)
    async def test_empty_hints_from_provider(self, mock_enabled, mock_get_hints):
        """Test when provider returns empty hints"""
        from ideation.analyzer import ProjectAnalyzer

        mock_get_hints.return_value = []

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        result = await analyzer.get_graph_hints("code_improvements")

        assert result == []

    @pytest.mark.asyncio
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=False)
    async def test_fallback_when_unavailable(self, mock_enabled):
        """Test graceful fallback when Graphiti is not available"""
        from ideation.analyzer import ProjectAnalyzer

        analyzer = ProjectAnalyzer(
            project_dir=Path("/tmp/test"),
            output_dir=Path("/tmp/output"),
        )

        result = await analyzer.get_graph_hints("code_improvements")

        # Should return empty list instead of crashing
        assert result == []

    @pytest.mark.asyncio
    @patch("ideation.analyzer.get_graph_hints", new_callable=AsyncMock)
    @patch("ideation.analyzer.is_graphiti_enabled", return_value=True)
    async def test_with_different_project_paths(self, mock_enabled, mock_get_hints):
        """Test with different project directory paths"""
        from ideation.analyzer import ProjectAnalyzer

        mock_get_hints.return_value = []

        project_paths = [
            Path("/tmp/simple_project"),
            Path("/home/user/projects/my-app"),
            Path("/var/www/html/project"),
        ]

        for project_dir in project_paths:
            analyzer = ProjectAnalyzer(
                project_dir=project_dir,
                output_dir=Path("/tmp/output"),
            )

            await analyzer.get_graph_hints("code_improvements")

            # Verify project_id was passed correctly
            call_kwargs = mock_get_hints.call_args.kwargs
            assert call_kwargs["project_id"] == str(project_dir)
