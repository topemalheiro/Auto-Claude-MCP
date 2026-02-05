"""Comprehensive tests for framework_detector module."""

import json
from pathlib import Path

import pytest

from project.framework_detector import FrameworkDetector


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory for testing."""
    return tmp_path


@pytest.fixture
def framework_detector(temp_project_dir: Path) -> FrameworkDetector:
    """Create a FrameworkDetector instance for testing."""
    return FrameworkDetector(temp_project_dir)


class TestFrameworkDetectorInit:
    """Tests for FrameworkDetector.__init__"""

    def test_init_with_path(self, temp_project_dir: Path):
        """Test initialization with a project directory path."""
        detector = FrameworkDetector(temp_project_dir)
        assert detector.project_dir == temp_project_dir.resolve()
        assert detector.frameworks == []

    def test_init_creates_empty_frameworks_list(self, temp_project_dir: Path):
        """Test that initialization creates empty frameworks list."""
        detector = FrameworkDetector(temp_project_dir)
        assert detector.frameworks == []


class TestDetectAll:
    """Tests for FrameworkDetector.detect_all"""

    def test_detect_all_returns_list(self, framework_detector: FrameworkDetector):
        """Test that detect_all returns a list."""
        result = framework_detector.detect_all()
        assert isinstance(result, list)

    def test_detect_all_runs_all_detectors(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test that detect_all runs all detection methods."""
        # Create package.json with dependencies
        (temp_project_dir / "package.json").write_text(json.dumps({
            "dependencies": {
                "next": "^14.0.0",
                "react": "^18.0.0"
            }
        }))

        result = framework_detector.detect_all()
        # Should detect frameworks
        assert "nextjs" in result or "react" in result


class TestDetectNodejsFrameworks:
    """Tests for FrameworkDetector.detect_nodejs_frameworks"""

    def test_detect_nextjs(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Next.js detection."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "dependencies": {"next": "^14.0.0"}
        }))

        framework_detector.detect_nodejs_frameworks()
        assert "nextjs" in framework_detector.frameworks

    def test_detect_nuxt(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Nuxt detection."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "dependencies": {"nuxt": "^3.0.0"}
        }))

        framework_detector.detect_nodejs_frameworks()
        assert "nuxt" in framework_detector.frameworks

    def test_detect_react(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test React detection."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "dependencies": {"react": "^18.0.0"}
        }))

        framework_detector.detect_nodejs_frameworks()
        assert "react" in framework_detector.frameworks

    def test_detect_vue(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Vue detection."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "dependencies": {"vue": "^3.0.0"}
        }))

        framework_detector.detect_nodejs_frameworks()
        assert "vue" in framework_detector.frameworks

    def test_detect_angular(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Angular detection."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "dependencies": {"@angular/core": "^17.0.0"}
        }))

        framework_detector.detect_nodejs_frameworks()
        assert "angular" in framework_detector.frameworks

    def test_detect_svelte(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Svelte detection."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "dependencies": {"svelte": "^4.0.0"}
        }))

        framework_detector.detect_nodejs_frameworks()
        assert "svelte" in framework_detector.frameworks

    def test_detect_astro(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Astro detection."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "dependencies": {"astro": "^4.0.0"}
        }))

        framework_detector.detect_nodejs_frameworks()
        assert "astro" in framework_detector.frameworks

    def test_detect_express(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Express detection."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "dependencies": {"express": "^4.18.0"}
        }))

        framework_detector.detect_nodejs_frameworks()
        assert "express" in framework_detector.frameworks

    def test_detect_nestjs(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test NestJS detection."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "dependencies": {"@nestjs/core": "^10.0.0"}
        }))

        framework_detector.detect_nodejs_frameworks()
        assert "nestjs" in framework_detector.frameworks

    def test_detect_fastify(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Fastify detection."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "dependencies": {"fastify": "^4.0.0"}
        }))

        framework_detector.detect_nodejs_frameworks()
        assert "fastify" in framework_detector.frameworks

    def test_detect_electron(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Electron detection."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "dependencies": {"electron": "^28.0.0"}
        }))

        framework_detector.detect_nodejs_frameworks()
        assert "electron" in framework_detector.frameworks

    def test_detect_vite(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Vite detection."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "devDependencies": {"vite": "^5.0.0"}
        }))

        framework_detector.detect_nodejs_frameworks()
        assert "vite" in framework_detector.frameworks

    def test_detect_webpack(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Webpack detection."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "devDependencies": {"webpack": "^5.0.0"}
        }))

        framework_detector.detect_nodejs_frameworks()
        assert "webpack" in framework_detector.frameworks

    def test_detect_jest(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Jest detection."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "devDependencies": {"jest": "^29.0.0"}
        }))

        framework_detector.detect_nodejs_frameworks()
        assert "jest" in framework_detector.frameworks

    def test_detect_vitest(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Vitest detection."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "devDependencies": {"vitest": "^1.0.0"}
        }))

        framework_detector.detect_nodejs_frameworks()
        assert "vitest" in framework_detector.frameworks

    def test_detect_playwright(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Playwright detection."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "devDependencies": {"@playwright/test": "^1.40.0"}
        }))

        framework_detector.detect_nodejs_frameworks()
        assert "playwright" in framework_detector.frameworks

    def test_detect_cypress(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Cypress detection."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "devDependencies": {"cypress": "^13.0.0"}
        }))

        framework_detector.detect_nodejs_frameworks()
        assert "cypress" in framework_detector.frameworks

    def test_detect_eslint(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test ESLint detection."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "devDependencies": {"eslint": "^8.0.0"}
        }))

        framework_detector.detect_nodejs_frameworks()
        assert "eslint" in framework_detector.frameworks

    def test_detect_prettier(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Prettier detection."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "devDependencies": {"prettier": "^3.0.0"}
        }))

        framework_detector.detect_nodejs_frameworks()
        assert "prettier" in framework_detector.frameworks

    def test_detect_biome(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Biome detection."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "devDependencies": {"@biomejs/biome": "^1.0.0"}
        }))

        framework_detector.detect_nodejs_frameworks()
        assert "biome" in framework_detector.frameworks

    def test_detect_prisma(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Prisma detection."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "dependencies": {"prisma": "^5.0.0"}
        }))

        framework_detector.detect_nodejs_frameworks()
        assert "prisma" in framework_detector.frameworks

    def test_detect_drizzle(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Drizzle ORM detection."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "dependencies": {"drizzle-orm": "^0.29.0"}
        }))

        framework_detector.detect_nodejs_frameworks()
        assert "drizzle" in framework_detector.frameworks

    def test_no_package_json(self, framework_detector: FrameworkDetector):
        """Test behavior when package.json doesn't exist."""
        framework_detector.detect_nodejs_frameworks()
        assert framework_detector.frameworks == []


class TestDetectPythonFrameworks:
    """Tests for FrameworkDetector.detect_python_frameworks"""

    def test_detect_django(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Django detection from requirements.txt."""
        (temp_project_dir / "requirements.txt").write_text("Django==5.0.0")

        framework_detector.detect_python_frameworks()
        assert "django" in framework_detector.frameworks

    def test_detect_flask(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Flask detection."""
        (temp_project_dir / "requirements.txt").write_text("Flask==3.0.0")

        framework_detector.detect_python_frameworks()
        assert "flask" in framework_detector.frameworks

    def test_detect_fastapi(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test FastAPI detection."""
        (temp_project_dir / "requirements.txt").write_text("fastapi==0.109.0")

        framework_detector.detect_python_frameworks()
        assert "fastapi" in framework_detector.frameworks

    def test_detect_starlette(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Starlette detection."""
        (temp_project_dir / "requirements.txt").write_text("starlette==0.27.0")

        framework_detector.detect_python_frameworks()
        assert "starlette" in framework_detector.frameworks

    def test_detect_tornado(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Tornado detection."""
        (temp_project_dir / "requirements.txt").write_text("tornado==6.4.0")

        framework_detector.detect_python_frameworks()
        assert "tornado" in framework_detector.frameworks

    def test_detect_aiohttp(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test aiohttp detection."""
        (temp_project_dir / "requirements.txt").write_text("aiohttp==3.9.0")

        framework_detector.detect_python_frameworks()
        assert "aiohttp" in framework_detector.frameworks

    def test_detect_celery(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Celery detection."""
        (temp_project_dir / "requirements.txt").write_text("celery==5.3.0")

        framework_detector.detect_python_frameworks()
        assert "celery" in framework_detector.frameworks

    def test_detect_streamlit(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Streamlit detection."""
        (temp_project_dir / "requirements.txt").write_text("streamlit==1.31.0")

        framework_detector.detect_python_frameworks()
        assert "streamlit" in framework_detector.frameworks

    def test_detect_pytest(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test pytest detection."""
        (temp_project_dir / "requirements.txt").write_text("pytest==8.0.0")

        framework_detector.detect_python_frameworks()
        assert "pytest" in framework_detector.frameworks

    def test_detect_mypy(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test mypy detection."""
        (temp_project_dir / "requirements.txt").write_text("mypy==1.8.0")

        framework_detector.detect_python_frameworks()
        assert "mypy" in framework_detector.frameworks

    def test_detect_ruff(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Ruff detection."""
        (temp_project_dir / "requirements.txt").write_text("ruff==0.1.0")

        framework_detector.detect_python_frameworks()
        assert "ruff" in framework_detector.frameworks

    def test_detect_black(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Black detection."""
        (temp_project_dir / "requirements.txt").write_text("black==24.0.0")

        framework_detector.detect_python_frameworks()
        assert "black" in framework_detector.frameworks

    def test_detect_poetry_django(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Django detection from Poetry."""
        (temp_project_dir / "pyproject.toml").write_text("""
[tool.poetry]
name = "test"

[tool.poetry.dependencies]
python = "^3.11"
django = "^5.0"
""")

        framework_detector.detect_python_frameworks()
        assert "django" in framework_detector.frameworks

    def test_detect_modern_pyproject(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test framework detection from modern pyproject.toml."""
        (temp_project_dir / "pyproject.toml").write_text("""
[project]
name = "test"
dependencies = ["fastapi>=0.109.0"]
""")

        framework_detector.detect_python_frameworks()
        assert "fastapi" in framework_detector.frameworks

    def test_detect_optional_dependencies(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test framework detection from optional dependencies."""
        (temp_project_dir / "pyproject.toml").write_text("""
[project]
name = "test"
dependencies = []

[project.optional-dependencies]
test = ["pytest>=8.0.0"]
""")

        framework_detector.detect_python_frameworks()
        assert "pytest" in framework_detector.frameworks

    def test_requirements_with_comments_and_flags(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test parsing requirements.txt with comments and install flags."""
        (temp_project_dir / "requirements.txt").write_text("""
# This is a comment
-r base.txt
flask==3.0.0
--extra-index-url https://example.com
pytest>=8.0.0
""")

        framework_detector.detect_python_frameworks()
        assert "flask" in framework_detector.frameworks
        assert "pytest" in framework_detector.frameworks

    def test_no_python_files(self, framework_detector: FrameworkDetector):
        """Test behavior when no Python files exist."""
        framework_detector.detect_python_frameworks()
        assert framework_detector.frameworks == []


class TestDetectRubyFrameworks:
    """Tests for FrameworkDetector.detect_ruby_frameworks"""

    def test_detect_rails(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Rails detection from Gemfile."""
        (temp_project_dir / "Gemfile").write_text("gem 'rails'")

        framework_detector.detect_ruby_frameworks()
        assert "rails" in framework_detector.frameworks

    def test_detect_sinatra(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Sinatra detection."""
        (temp_project_dir / "Gemfile").write_text("gem 'sinatra'")

        framework_detector.detect_ruby_frameworks()
        assert "sinatra" in framework_detector.frameworks

    def test_detect_rspec(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test RSpec detection."""
        (temp_project_dir / "Gemfile").write_text("gem 'rspec-rails'")

        framework_detector.detect_ruby_frameworks()
        assert "rspec" in framework_detector.frameworks

    def test_detect_rubocop(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test RuboCop detection."""
        (temp_project_dir / "Gemfile").write_text("gem 'rubocop'")

        framework_detector.detect_ruby_frameworks()
        assert "rubocop" in framework_detector.frameworks

    def test_no_gemfile(self, framework_detector: FrameworkDetector):
        """Test behavior when Gemfile doesn't exist."""
        framework_detector.detect_ruby_frameworks()
        assert framework_detector.frameworks == []


class TestDetectPhpFrameworks:
    """Tests for FrameworkDetector.detect_php_frameworks"""

    def test_detect_laravel(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Laravel detection from composer.json."""
        (temp_project_dir / "composer.json").write_text(json.dumps({
            "require": {
                "laravel/framework": "^11.0"
            }
        }))

        framework_detector.detect_php_frameworks()
        assert "laravel" in framework_detector.frameworks

    def test_detect_symfony(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Symfony detection."""
        (temp_project_dir / "composer.json").write_text(json.dumps({
            "require": {
                "symfony/framework-bundle": "^7.0"
            }
        }))

        framework_detector.detect_php_frameworks()
        assert "symfony" in framework_detector.frameworks

    def test_detect_phpunit(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test PHPUnit detection."""
        (temp_project_dir / "composer.json").write_text(json.dumps({
            "require-dev": {
                "phpunit/phpunit": "^11.0"
            }
        }))

        framework_detector.detect_php_frameworks()
        assert "phpunit" in framework_detector.frameworks

    def test_no_composer_json(self, framework_detector: FrameworkDetector):
        """Test behavior when composer.json doesn't exist."""
        framework_detector.detect_php_frameworks()
        assert framework_detector.frameworks == []


class TestDetectDartFrameworks:
    """Tests for FrameworkDetector.detect_dart_frameworks"""

    def test_detect_flutter(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Flutter detection from pubspec.yaml."""
        (temp_project_dir / "pubspec.yaml").write_text("""
name: test
flutter:
  sdk: flutter
""")

        framework_detector.detect_dart_frameworks()
        assert "flutter" in framework_detector.frameworks

    def test_detect_flutter_sdk_key(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Flutter detection with sdk: flutter key."""
        (temp_project_dir / "pubspec.yaml").write_text("""
name: test
dependencies:
  flutter:
    sdk: flutter
""")

        framework_detector.detect_dart_frameworks()
        assert "flutter" in framework_detector.frameworks

    def test_detect_dart_frog(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Dart Frog detection."""
        (temp_project_dir / "pubspec.yaml").write_text("""
name: test
dependencies:
  dart_frog: ^1.0.0
""")

        framework_detector.detect_dart_frameworks()
        assert "dart_frog" in framework_detector.frameworks

    def test_detect_serverpod(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Serverpod detection."""
        (temp_project_dir / "pubspec.yaml").write_text("""
name: test
dependencies:
  serverpod: ^1.0.0
""")

        framework_detector.detect_dart_frameworks()
        assert "serverpod" in framework_detector.frameworks

    def test_detect_shelf(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Shelf detection."""
        (temp_project_dir / "pubspec.yaml").write_text("""
name: test
dependencies:
  shelf: ^1.0.0
""")

        framework_detector.detect_dart_frameworks()
        assert "shelf" in framework_detector.frameworks

    def test_detect_aqueduct(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Aqueduct detection."""
        (temp_project_dir / "pubspec.yaml").write_text("""
name: test
dependencies:
  aqueduct: ^5.0.0
""")

        framework_detector.detect_dart_frameworks()
        assert "aqueduct" in framework_detector.frameworks

    def test_no_pubspec(self, framework_detector: FrameworkDetector):
        """Test behavior when pubspec.yaml doesn't exist."""
        framework_detector.detect_dart_frameworks()
        assert framework_detector.frameworks == []


class TestFrameworkAccumulation:
    """Tests for framework accumulation across multiple detections"""

    def test_multiple_frameworks_from_single_package_json(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test detecting multiple frameworks from a single package.json."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "dependencies": {
                "next": "^14.0.0",
                "react": "^18.0.0",
                "prisma": "^5.0.0"
            },
            "devDependencies": {
                "jest": "^29.0.0",
                "eslint": "^8.0.0"
            }
        }))

        framework_detector.detect_nodejs_frameworks()
        assert "nextjs" in framework_detector.frameworks
        assert "react" in framework_detector.frameworks
        assert "prisma" in framework_detector.frameworks
        assert "jest" in framework_detector.frameworks
        assert "eslint" in framework_detector.frameworks

    def test_cross_language_frameworks(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test detecting frameworks from multiple languages."""
        # Node.js
        (temp_project_dir / "package.json").write_text(json.dumps({
            "dependencies": {"next": "^14.0.0"}
        }))
        # Python
        (temp_project_dir / "requirements.txt").write_text("Django==5.0.0")

        framework_detector.detect_all()
        assert "nextjs" in framework_detector.frameworks
        assert "django" in framework_detector.frameworks

    def test_frameworks_case_insensitive(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test that framework detection handles case variations."""
        (temp_project_dir / "requirements.txt").write_text("FASTAPI==0.109.0")

        framework_detector.detect_python_frameworks()
        assert "fastapi" in framework_detector.frameworks


class TestEmptyProject:
    """Tests for projects with no detectable frameworks"""

    def test_empty_project_returns_empty_list(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test that empty project returns empty frameworks list."""
        # Create some non-framework files
        (temp_project_dir / "README.md").write_text("# Test Project")
        (temp_project_dir / "src").mkdir()
        (temp_project_dir / "src" / "main.txt").write_text("Hello")

        result = framework_detector.detect_all()
        assert result == []

    def test_project_with_no_frameworks(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test project that has dependencies but no known frameworks."""
        (temp_project_dir / "package.json").write_text(json.dumps({
            "dependencies": {
                "unknown-package": "^1.0.0",
                "another-unknown": "^2.0.0"
            }
        }))

        framework_detector.detect_nodejs_frameworks()
        assert framework_detector.frameworks == []


class TestSpecialDependencyFormats:
    """Tests for various dependency file formats"""

    def test_requirements_with_version_ranges(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test parsing requirements with different version specifiers."""
        (temp_project_dir / "requirements.txt").write_text("""
Django>=4.0,<6.0
flask~=3.0
requests>=2.28.0
pytest>=8.0.0; python_version>='3.8'
""")

        framework_detector.detect_python_frameworks()
        assert "django" in framework_detector.frameworks
        assert "flask" in framework_detector.frameworks
        assert "pytest" in framework_detector.frameworks

    def test_requirements_with_git_urls(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test parsing requirements with git URLs."""
        (temp_project_dir / "requirements.txt").write_text("""
git+https://github.com/django/django.git@main
fastapi>=0.109.0
-e git+https://github.com/user/repo.git#egg=package
""")

        framework_detector.detect_python_frameworks()
        # fastapi should still be detected
        assert "fastapi" in framework_detector.frameworks

    def test_poetry_groups(self, framework_detector: FrameworkDetector, temp_project_dir: Path):
        """Test Poetry dependency groups."""
        (temp_project_dir / "pyproject.toml").write_text("""
[tool.poetry]
name = "test"

[tool.poetry.dependencies]
python = "^3.11"
django = "^5.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
black = "^24.0"

[tool.poetry.group.test.dependencies]
ruff = "^0.1"
""")

        framework_detector.detect_python_frameworks()
        assert "django" in framework_detector.frameworks
        assert "pytest" in framework_detector.frameworks
        assert "black" in framework_detector.frameworks
        assert "ruff" in framework_detector.frameworks
