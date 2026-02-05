"""Comprehensive tests for stack_detector module."""

from pathlib import Path

import pytest

from project.models import TechnologyStack
from project.stack_detector import StackDetector


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory for testing."""
    return tmp_path


@pytest.fixture
def stack_detector(temp_project_dir: Path) -> StackDetector:
    """Create a StackDetector instance for testing."""
    return StackDetector(temp_project_dir)


class TestStackDetectorInit:
    """Tests for StackDetector.__init__"""

    def test_init_with_path(self, temp_project_dir: Path):
        """Test initialization with a project directory path."""
        detector = StackDetector(temp_project_dir)
        assert detector.project_dir == temp_project_dir.resolve()
        assert isinstance(detector.stack, TechnologyStack)

    def test_init_creates_empty_stack(self, temp_project_dir: Path):
        """Test that initialization creates empty TechnologyStack."""
        detector = StackDetector(temp_project_dir)
        assert detector.stack.languages == []
        assert detector.stack.package_managers == []
        assert detector.stack.frameworks == []


class TestDetectAll:
    """Tests for StackDetector.detect_all"""

    def test_detect_all_returns_stack(self, stack_detector: StackDetector):
        """Test that detect_all returns a TechnologyStack."""
        result = stack_detector.detect_all()
        assert isinstance(result, TechnologyStack)

    def test_detect_all_runs_all_detectors(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test that detect_all runs all detection methods."""
        # Create some indicator files
        (temp_project_dir / "package.json").write_text("{}")
        (temp_project_dir / "requirements.txt").write_text("")

        result = stack_detector.detect_all()
        # Should detect some technologies
        assert len(result.languages) > 0 or len(result.package_managers) > 0


class TestDetectLanguages:
    """Tests for StackDetector.detect_languages"""

    def test_detect_python_by_files(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Python detection from .py files."""
        (temp_project_dir / "main.py").write_text("print('hello')")

        stack_detector.detect_languages()
        assert "python" in stack_detector.stack.languages

    def test_detect_python_by_pyproject(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Python detection from pyproject.toml."""
        (temp_project_dir / "pyproject.toml").write_text("[project]\nname = 'test'")

        stack_detector.detect_languages()
        assert "python" in stack_detector.stack.languages

    def test_detect_python_by_requirements(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Python detection from requirements.txt."""
        (temp_project_dir / "requirements.txt").write_text("requests==2.0.0")

        stack_detector.detect_languages()
        assert "python" in stack_detector.stack.languages

    def test_detect_javascript(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test JavaScript detection."""
        (temp_project_dir / "package.json").write_text("{}")
        (temp_project_dir / "app.js").write_text("console.log('test')")

        stack_detector.detect_languages()
        assert "javascript" in stack_detector.stack.languages

    def test_detect_typescript(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test TypeScript detection."""
        (temp_project_dir / "tsconfig.json").write_text("{}")
        (temp_project_dir / "app.ts").write_text("console.log('test')")

        stack_detector.detect_languages()
        assert "typescript" in stack_detector.stack.languages

    def test_detect_rust(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Rust detection."""
        (temp_project_dir / "Cargo.toml").write_text("[package]\nname = 'test'")

        stack_detector.detect_languages()
        assert "rust" in stack_detector.stack.languages

    def test_detect_go(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Go detection."""
        (temp_project_dir / "go.mod").write_text("module test")

        stack_detector.detect_languages()
        assert "go" in stack_detector.stack.languages

    def test_detect_ruby(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Ruby detection."""
        (temp_project_dir / "Gemfile").write_text("source 'https://rubygems.org'")

        stack_detector.detect_languages()
        assert "ruby" in stack_detector.stack.languages

    def test_detect_php(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test PHP detection."""
        (temp_project_dir / "composer.json").write_text("{}")
        (temp_project_dir / "index.php").write_text("<?php echo 'test'; ?>")

        stack_detector.detect_languages()
        assert "php" in stack_detector.stack.languages

    def test_detect_java(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Java detection."""
        (temp_project_dir / "pom.xml").write_text("<project></project>")

        stack_detector.detect_languages()
        assert "java" in stack_detector.stack.languages

    def test_detect_kotlin(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Kotlin detection."""
        (temp_project_dir / "Main.kt").write_text("fun main() {}")

        stack_detector.detect_languages()
        assert "kotlin" in stack_detector.stack.languages

    def test_detect_scala(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Scala detection."""
        (temp_project_dir / "build.sbt").write_text("name := 'test'")

        stack_detector.detect_languages()
        assert "scala" in stack_detector.stack.languages

    def test_detect_csharp(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test C# detection."""
        (temp_project_dir / "Project.csproj").write_text("<Project></Project>")

        stack_detector.detect_languages()
        assert "csharp" in stack_detector.stack.languages

    def test_detect_c(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test C detection."""
        (temp_project_dir / "main.c").write_text("int main() { return 0; }")

        stack_detector.detect_languages()
        assert "c" in stack_detector.stack.languages

    def test_detect_cpp(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test C++ detection."""
        (temp_project_dir / "main.cpp").write_text("int main() { return 0; }")

        stack_detector.detect_languages()
        assert "cpp" in stack_detector.stack.languages

    def test_detect_elixir(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Elixir detection."""
        (temp_project_dir / "mix.exs").write_text("defmodule Test.MixProject")

        stack_detector.detect_languages()
        assert "elixir" in stack_detector.stack.languages

    def test_detect_swift(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Swift detection."""
        (temp_project_dir / "Package.swift").write_text("// swift-tools-version:5.0")

        stack_detector.detect_languages()
        assert "swift" in stack_detector.stack.languages

    def test_detect_dart(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Dart/Flutter detection."""
        (temp_project_dir / "pubspec.yaml").write_text("name: test")

        stack_detector.detect_languages()
        assert "dart" in stack_detector.stack.languages


class TestDetectPackageManagers:
    """Tests for StackDetector.detect_package_managers"""

    def test_detect_npm(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test npm detection."""
        (temp_project_dir / "package-lock.json").write_text("{}")

        stack_detector.detect_package_managers()
        assert "npm" in stack_detector.stack.package_managers

    def test_detect_yarn(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Yarn detection."""
        (temp_project_dir / "yarn.lock").write_text("")

        stack_detector.detect_package_managers()
        assert "yarn" in stack_detector.stack.package_managers

    def test_detect_pnpm(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test pnpm detection."""
        (temp_project_dir / "pnpm-lock.yaml").write_text("")

        stack_detector.detect_package_managers()
        assert "pnpm" in stack_detector.stack.package_managers

    def test_detect_bun(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Bun detection."""
        (temp_project_dir / "bun.lockb").write_text("")

        stack_detector.detect_package_managers()
        assert "bun" in stack_detector.stack.package_managers

    def test_detect_deno(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Deno detection."""
        (temp_project_dir / "deno.json").write_text("{}")

        stack_detector.detect_package_managers()
        assert "deno" in stack_detector.stack.package_managers

    def test_detect_pip(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test pip detection."""
        (temp_project_dir / "requirements.txt").write_text("requests")

        stack_detector.detect_package_managers()
        assert "pip" in stack_detector.stack.package_managers

    def test_detect_poetry(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Poetry detection."""
        (temp_project_dir / "pyproject.toml").write_text("""
[tool.poetry]
name = "test"
""")

        stack_detector.detect_package_managers()
        assert "poetry" in stack_detector.stack.package_managers

    def test_detect_uv(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test uv detection."""
        (temp_project_dir / "pyproject.toml").write_text("""
[project]
name = "test"
""")
        (temp_project_dir / "uv.lock").write_text("")

        stack_detector.detect_package_managers()
        assert "uv" in stack_detector.stack.package_managers

    def test_detect_pdm(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test PDM detection."""
        (temp_project_dir / "pyproject.toml").write_text("""
[project]
name = "test"
""")
        (temp_project_dir / "pdm.lock").write_text("")

        stack_detector.detect_package_managers()
        assert "pdm" in stack_detector.stack.package_managers

    def test_detect_pipenv(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Pipenv detection."""
        (temp_project_dir / "Pipfile").write_text("[[source]]")

        stack_detector.detect_package_managers()
        assert "pipenv" in stack_detector.stack.package_managers

    def test_detect_cargo(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Cargo detection."""
        (temp_project_dir / "Cargo.toml").write_text("[package]")

        stack_detector.detect_package_managers()
        assert "cargo" in stack_detector.stack.package_managers

    def test_detect_go_mod(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Go mod detection."""
        (temp_project_dir / "go.mod").write_text("module test")

        stack_detector.detect_package_managers()
        assert "go_mod" in stack_detector.stack.package_managers

    def test_detect_gem(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Gem detection."""
        (temp_project_dir / "Gemfile").write_text("source 'https://rubygems.org'")

        stack_detector.detect_package_managers()
        assert "gem" in stack_detector.stack.package_managers

    def test_detect_composer(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Composer detection."""
        (temp_project_dir / "composer.json").write_text("{}")

        stack_detector.detect_package_managers()
        assert "composer" in stack_detector.stack.package_managers

    def test_detect_maven(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Maven detection."""
        (temp_project_dir / "pom.xml").write_text("<project></project>")

        stack_detector.detect_package_managers()
        assert "maven" in stack_detector.stack.package_managers

    def test_detect_gradle(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Gradle detection."""
        (temp_project_dir / "build.gradle").write_text("plugins {}")

        stack_detector.detect_package_managers()
        assert "gradle" in stack_detector.stack.package_managers

    def test_detect_pub(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Pub detection."""
        (temp_project_dir / "pubspec.yaml").write_text("name: test")

        stack_detector.detect_package_managers()
        assert "pub" in stack_detector.stack.package_managers

    def test_detect_melos(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Melos detection."""
        (temp_project_dir / "melos.yaml").write_text("name: test")

        stack_detector.detect_package_managers()
        assert "melos" in stack_detector.stack.package_managers


class TestDetectDatabases:
    """Tests for StackDetector.detect_databases"""

    def test_detect_postgres_from_env(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test PostgreSQL detection from .env file."""
        (temp_project_dir / ".env").write_text("DATABASE_URL=postgresql://localhost/db")

        stack_detector.detect_databases()
        assert "postgresql" in stack_detector.stack.databases

    def test_detect_mysql_from_env(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test MySQL detection from .env file."""
        (temp_project_dir / ".env").write_text("DB_HOST=mysql")

        stack_detector.detect_databases()
        assert "mysql" in stack_detector.stack.databases

    def test_detect_mongodb_from_env(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test MongoDB detection from .env file."""
        (temp_project_dir / ".env").write_text("MONGO_URL=mongodb://localhost")

        stack_detector.detect_databases()
        assert "mongodb" in stack_detector.stack.databases

    def test_detect_redis_from_env(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Redis detection from .env file."""
        (temp_project_dir / ".env").write_text("REDIS_URL=redis://localhost")

        stack_detector.detect_databases()
        assert "redis" in stack_detector.stack.databases

    def test_detect_sqlite_from_env(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test SQLite detection from .env file."""
        (temp_project_dir / ".env").write_text("DB_TYPE=sqlite")

        stack_detector.detect_databases()
        assert "sqlite" in stack_detector.stack.databases

    def test_detect_postgres_from_prisma(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test PostgreSQL detection from Prisma schema."""
        prisma_dir = temp_project_dir / "prisma"
        prisma_dir.mkdir()
        (prisma_dir / "schema.prisma").write_text('datasource db { provider = "postgresql" }')

        stack_detector.detect_databases()
        assert "postgresql" in stack_detector.stack.databases

    def test_detect_databases_from_docker_compose(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test database detection from docker-compose.yml."""
        (temp_project_dir / "docker-compose.yml").write_text("""
services:
  postgres:
    image: postgres:latest
  redis:
    image: redis:latest
""")

        stack_detector.detect_databases()
        assert "postgresql" in stack_detector.stack.databases
        assert "redis" in stack_detector.stack.databases


class TestDetectInfrastructure:
    """Tests for StackDetector.detect_infrastructure"""

    def test_detect_docker(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Docker detection."""
        (temp_project_dir / "Dockerfile").write_text("FROM node:latest")

        stack_detector.detect_infrastructure()
        assert "docker" in stack_detector.stack.infrastructure

    def test_detect_docker_compose(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Docker Compose detection."""
        (temp_project_dir / "docker-compose.yml").write_text("version: '3'")

        stack_detector.detect_infrastructure()
        assert "docker" in stack_detector.stack.infrastructure

    def test_detect_podman(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Podman detection."""
        (temp_project_dir / "Containerfile").write_text("FROM node:latest")

        stack_detector.detect_infrastructure()
        assert "podman" in stack_detector.stack.infrastructure

    def test_detect_kubernetes(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Kubernetes detection."""
        (temp_project_dir / "deployment.yaml").write_text("""
apiVersion: apps/v1
kind: Deployment
""")

        stack_detector.detect_infrastructure()
        assert "kubernetes" in stack_detector.stack.infrastructure

    def test_detect_helm(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Helm detection."""
        (temp_project_dir / "Chart.yaml").write_text("name: test")

        stack_detector.detect_infrastructure()
        assert "helm" in stack_detector.stack.infrastructure

    def test_detect_terraform(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Terraform detection."""
        (temp_project_dir / "main.tf").write_text('resource "aws_instance" "web" {}')

        stack_detector.detect_infrastructure()
        assert "terraform" in stack_detector.stack.infrastructure

    def test_detect_ansible(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Ansible detection."""
        (temp_project_dir / "ansible.cfg").write_text("[defaults]")

        stack_detector.detect_infrastructure()
        assert "ansible" in stack_detector.stack.infrastructure

    def test_detect_vagrant(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Vagrant detection."""
        (temp_project_dir / "Vagrantfile").write_text("Vagrant.configure('2')")

        stack_detector.detect_infrastructure()
        assert "vagrant" in stack_detector.stack.infrastructure


class TestDetectCloudProviders:
    """Tests for StackDetector.detect_cloud_providers"""

    def test_detect_aws(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test AWS detection."""
        (temp_project_dir / "template.yaml").write_text("AWSTemplateFormatVersion: '2010-09-09'")

        stack_detector.detect_cloud_providers()
        assert "aws" in stack_detector.stack.cloud_providers

    def test_detect_gcp(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test GCP detection."""
        (temp_project_dir / "app.yaml").write_text("runtime: python39")

        stack_detector.detect_cloud_providers()
        assert "gcp" in stack_detector.stack.cloud_providers

    def test_detect_azure(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Azure detection."""
        (temp_project_dir / "azure-pipelines.yml").write_text("trigger: main")

        stack_detector.detect_cloud_providers()
        assert "azure" in stack_detector.stack.cloud_providers

    def test_detect_vercel(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Vercel detection."""
        (temp_project_dir / "vercel.json").write_text("{}")

        stack_detector.detect_cloud_providers()
        assert "vercel" in stack_detector.stack.cloud_providers

    def test_detect_netlify(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Netlify detection."""
        (temp_project_dir / "netlify.toml").write_text("[build]")

        stack_detector.detect_cloud_providers()
        assert "netlify" in stack_detector.stack.cloud_providers

    def test_detect_heroku(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Heroku detection."""
        (temp_project_dir / "Procfile").write_text("web: node app.js")

        stack_detector.detect_cloud_providers()
        assert "heroku" in stack_detector.stack.cloud_providers

    def test_detect_railway(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Railway detection."""
        (temp_project_dir / "railway.json").write_text("{}")

        stack_detector.detect_cloud_providers()
        assert "railway" in stack_detector.stack.cloud_providers

    def test_detect_fly(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Fly.io detection."""
        (temp_project_dir / "fly.toml").write_text("app = 'test'")

        stack_detector.detect_cloud_providers()
        assert "fly" in stack_detector.stack.cloud_providers

    def test_detect_cloudflare(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Cloudflare detection."""
        (temp_project_dir / "wrangler.toml").write_text("name = 'test'")

        stack_detector.detect_cloud_providers()
        assert "cloudflare" in stack_detector.stack.cloud_providers

    def test_detect_supabase(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Supabase detection."""
        supabase_dir = temp_project_dir / "supabase"
        supabase_dir.mkdir()

        stack_detector.detect_cloud_providers()
        assert "supabase" in stack_detector.stack.cloud_providers


class TestDetectCodeQualityTools:
    """Tests for StackDetector.detect_code_quality_tools"""

    def test_detect_shellcheck(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test ShellCheck detection."""
        (temp_project_dir / ".shellcheckrc").write_text("")

        stack_detector.detect_code_quality_tools()
        assert "shellcheck" in stack_detector.stack.code_quality_tools

    def test_detect_hadolint(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Hadolint detection."""
        (temp_project_dir / ".hadolint.yaml").write_text("")

        stack_detector.detect_code_quality_tools()
        assert "hadolint" in stack_detector.stack.code_quality_tools

    def test_detect_yamllint(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test yamllint detection."""
        (temp_project_dir / ".yamllint").write_text("")

        stack_detector.detect_code_quality_tools()
        assert "yamllint" in stack_detector.stack.code_quality_tools

    def test_detect_vale(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Vale detection."""
        (temp_project_dir / ".vale.ini").write_text("")

        stack_detector.detect_code_quality_tools()
        assert "vale" in stack_detector.stack.code_quality_tools

    def test_detect_cspell(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test cspell detection."""
        (temp_project_dir / "cspell.json").write_text("{}")

        stack_detector.detect_code_quality_tools()
        assert "cspell" in stack_detector.stack.code_quality_tools

    def test_detect_codespell(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test codespell detection."""
        (temp_project_dir / ".codespellrc").write_text("")

        stack_detector.detect_code_quality_tools()
        assert "codespell" in stack_detector.stack.code_quality_tools

    def test_detect_semgrep(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Semgrep detection."""
        (temp_project_dir / ".semgrep.yml").write_text("")

        stack_detector.detect_code_quality_tools()
        assert "semgrep" in stack_detector.stack.code_quality_tools

    def test_detect_snyk(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Snyk detection."""
        snyk_dir = temp_project_dir / ".snyk"
        snyk_dir.mkdir()

        stack_detector.detect_code_quality_tools()
        assert "snyk" in stack_detector.stack.code_quality_tools

    def test_detect_trivy(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test Trivy detection."""
        (temp_project_dir / ".trivyignore").write_text("")

        stack_detector.detect_code_quality_tools()
        assert "trivy" in stack_detector.stack.code_quality_tools


class TestDetectVersionManagers:
    """Tests for StackDetector.detect_version_managers"""

    def test_detect_asdf(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test asdf detection."""
        (temp_project_dir / ".tool-versions").write_text("nodejs 18.0.0")

        stack_detector.detect_version_managers()
        assert "asdf" in stack_detector.stack.version_managers

    def test_detect_mise(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test mise detection."""
        (temp_project_dir / ".mise.toml").write_text("")

        stack_detector.detect_version_managers()
        assert "mise" in stack_detector.stack.version_managers

    def test_detect_nvm(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test NVM detection."""
        (temp_project_dir / ".nvmrc").write_text("18")

        stack_detector.detect_version_managers()
        assert "nvm" in stack_detector.stack.version_managers

    def test_detect_pyenv(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test pyenv detection."""
        (temp_project_dir / ".python-version").write_text("3.11")

        stack_detector.detect_version_managers()
        assert "pyenv" in stack_detector.stack.version_managers

    def test_detect_rbenv(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test rbenv detection."""
        (temp_project_dir / ".ruby-version").write_text("3.2")

        stack_detector.detect_version_managers()
        assert "rbenv" in stack_detector.stack.version_managers

    def test_detect_rustup(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test rustup detection."""
        (temp_project_dir / "rust-toolchain.toml").write_text("[toolchain]")

        stack_detector.detect_version_managers()
        assert "rustup" in stack_detector.stack.version_managers

    def test_detect_fvm(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test FVM detection."""
        (temp_project_dir / ".fvm").write_text("")

        stack_detector.detect_version_managers()
        assert "fvm" in stack_detector.stack.version_managers


class TestDeduplication:
    """Tests for list deduplication"""

    def test_database_deduplication(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test that database entries are deduplicated."""
        # Create multiple sources that detect the same database
        (temp_project_dir / ".env").write_text("DB=postgresql://localhost")
        (temp_project_dir / "docker-compose.yml").write_text("""
services:
  postgres:
    image: postgres
""")

        stack_detector.detect_databases()
        # Should have only one entry for postgresql
        assert stack_detector.stack.databases.count("postgresql") == 1

    def test_infrastructure_deduplication(self, stack_detector: StackDetector, temp_project_dir: Path):
        """Test that infrastructure entries are deduplicated."""
        (temp_project_dir / "Dockerfile").write_text("FROM node")
        (temp_project_dir / "docker-compose.yml").write_text("version: '3'")

        stack_detector.detect_infrastructure()
        assert stack_detector.stack.infrastructure.count("docker") == 1
