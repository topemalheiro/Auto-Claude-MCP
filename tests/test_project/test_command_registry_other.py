"""
Tests for project.command_registry modules (package_managers, frameworks, databases, etc.)
========================================================================================

Comprehensive tests for the remaining command registry modules including:
- PACKAGE_MANAGER_COMMANDS
- FRAMEWORK_COMMANDS
- DATABASE_COMMANDS
- INFRASTRUCTURE_COMMANDS
- CLOUD_COMMANDS
- CODE_QUALITY_COMMANDS
- VERSION_MANAGER_COMMANDS
"""

import pytest

from project.command_registry.package_managers import PACKAGE_MANAGER_COMMANDS
from project.command_registry.frameworks import FRAMEWORK_COMMANDS
from project.command_registry.databases import DATABASE_COMMANDS
from project.command_registry.infrastructure import INFRASTRUCTURE_COMMANDS
from project.command_registry.cloud import CLOUD_COMMANDS
from project.command_registry.code_quality import CODE_QUALITY_COMMANDS
from project.command_registry.version_managers import VERSION_MANAGER_COMMANDS


# =============================================================================
# PACKAGE_MANAGER_COMMANDS Tests
# =============================================================================

class TestPackageManagerCommands:
    """Tests for PACKAGE_MANAGER_COMMANDS dictionary."""

    def test_package_manager_commands_is_dict(self):
        """Test that PACKAGE_MANAGER_COMMANDS is a dictionary."""
        assert isinstance(PACKAGE_MANAGER_COMMANDS, dict)

    def test_package_manager_commands_not_empty(self):
        """Test that PACKAGE_MANAGER_COMMANDS is not empty."""
        assert len(PACKAGE_MANAGER_COMMANDS) > 0

    def test_package_manager_commands_all_values_sets(self):
        """Test that all values are sets."""
        assert all(isinstance(value, set) for value in PACKAGE_MANAGER_COMMANDS.values())

    def test_npm_key_exists(self):
        """Test that npm key exists."""
        assert "npm" in PACKAGE_MANAGER_COMMANDS

    def test_npm_has_commands(self):
        """Test that npm has expected commands."""
        assert "npm" in PACKAGE_MANAGER_COMMANDS["npm"]
        assert "npx" in PACKAGE_MANAGER_COMMANDS["npm"]

    def test_yarn_key_exists(self):
        """Test that yarn key exists."""
        assert "yarn" in PACKAGE_MANAGER_COMMANDS

    def test_pnpm_key_exists(self):
        """Test that pnpm key exists."""
        assert "pnpm" in PACKAGE_MANAGER_COMMANDS

    def test_bun_key_exists(self):
        """Test that bun key exists."""
        assert "bun" in PACKAGE_MANAGER_COMMANDS

    def test_pip_key_exists(self):
        """Test that pip key exists."""
        assert "pip" in PACKAGE_MANAGER_COMMANDS

    def test_pip_has_commands(self):
        """Test that pip has expected commands."""
        assert "pip" in PACKAGE_MANAGER_COMMANDS["pip"]
        assert "pip3" in PACKAGE_MANAGER_COMMANDS["pip"]

    def test_poetry_key_exists(self):
        """Test that poetry key exists."""
        assert "poetry" in PACKAGE_MANAGER_COMMANDS

    def test_uv_key_exists(self):
        """Test that uv key exists."""
        assert "uv" in PACKAGE_MANAGER_COMMANDS

    def test_cargo_key_exists(self):
        """Test that cargo key exists."""
        assert "cargo" in PACKAGE_MANAGER_COMMANDS

    def test_composer_key_exists(self):
        """Test that composer key exists."""
        assert "composer" in PACKAGE_MANAGER_COMMANDS

    def test_brew_key_exists(self):
        """Test that brew key exists."""
        assert "brew" in PACKAGE_MANAGER_COMMANDS

    def test_nix_key_exists(self):
        """Test that nix key exists."""
        assert "nix" in PACKAGE_MANAGER_COMMANDS

    def test_dart_package_managers(self):
        """Test Dart/Flutter package managers."""
        assert "pub" in PACKAGE_MANAGER_COMMANDS
        assert "melos" in PACKAGE_MANAGER_COMMANDS


# =============================================================================
# FRAMEWORK_COMMANDS Tests
# =============================================================================

class TestFrameworkCommands:
    """Tests for FRAMEWORK_COMMANDS dictionary."""

    def test_framework_commands_is_dict(self):
        """Test that FRAMEWORK_COMMANDS is a dictionary."""
        assert isinstance(FRAMEWORK_COMMANDS, dict)

    def test_framework_commands_not_empty(self):
        """Test that FRAMEWORK_COMMANDS is not empty."""
        assert len(FRAMEWORK_COMMANDS) > 0

    def test_framework_commands_all_values_sets(self):
        """Test that all values are sets."""
        assert all(isinstance(value, set) for value in FRAMEWORK_COMMANDS.values())

    def test_python_web_frameworks(self):
        """Test Python web frameworks are covered."""
        python_frameworks = {"flask", "django", "fastapi", "starlette", "tornado"}
        assert python_frameworks.issubset(FRAMEWORK_COMMANDS.keys())

    def test_django_has_gunicorn(self):
        """Test that Django has gunicorn."""
        assert "gunicorn" in FRAMEWORK_COMMANDS["django"]

    def test_fastapi_has_uvicorn(self):
        """Test that FastAPI has uvicorn."""
        assert "uvicorn" in FRAMEWORK_COMMANDS["fastapi"]

    def test_nodejs_frameworks(self):
        """Test Node.js frameworks are covered."""
        node_frameworks = {"nextjs", "nuxt", "react", "vue", "angular", "svelte"}
        assert node_frameworks.issubset(FRAMEWORK_COMMANDS.keys())

    def test_nextjs_has_next(self):
        """Test that Next.js has next command."""
        assert "next" in FRAMEWORK_COMMANDS["nextjs"]

    def test_react_has_react_scripts(self):
        """Test that React has react-scripts."""
        assert "react-scripts" in FRAMEWORK_COMMANDS["react"]

    def test_ruby_on_rails(self):
        """Test Ruby on Rails is covered."""
        assert "rails" in FRAMEWORK_COMMANDS
        assert "rails" in FRAMEWORK_COMMANDS["rails"]
        assert "rake" in FRAMEWORK_COMMANDS["rails"]

    def test_php_frameworks(self):
        """Test PHP frameworks are covered."""
        php_frameworks = {"laravel", "symfony", "wordpress"}
        assert php_frameworks.issubset(FRAMEWORK_COMMANDS.keys())

    def test_laravel_has_artisan(self):
        """Test that Laravel has artisan command."""
        assert "artisan" in FRAMEWORK_COMMANDS["laravel"]

    def test_rust_frameworks(self):
        """Test Rust frameworks are covered."""
        rust_frameworks = {"actix", "rocket", "axum"}
        assert rust_frameworks.issubset(FRAMEWORK_COMMANDS.keys())

    def test_testing_frameworks(self):
        """Test testing frameworks are covered."""
        testing_frameworks = {"pytest", "jest", "vitest", "mocha", "cypress", "playwright"}
        assert testing_frameworks.issubset(FRAMEWORK_COMMANDS.keys())

    def test_linting_frameworks(self):
        """Test linting tools are covered."""
        linting = {"eslint", "prettier", "biome", "ruff", "black", "flake8"}
        assert linting.issubset(FRAMEWORK_COMMANDS.keys())

    def test_flutter_has_dart_commands(self):
        """Test that Flutter framework has dart commands."""
        assert "flutter" in FRAMEWORK_COMMANDS
        assert "dart" in FRAMEWORK_COMMANDS["flutter"]


# =============================================================================
# DATABASE_COMMANDS Tests
# =============================================================================

class TestDatabaseCommands:
    """Tests for DATABASE_COMMANDS dictionary."""

    def test_database_commands_is_dict(self):
        """Test that DATABASE_COMMANDS is a dictionary."""
        assert isinstance(DATABASE_COMMANDS, dict)

    def test_database_commands_not_empty(self):
        """Test that DATABASE_COMMANDS is not empty."""
        assert len(DATABASE_COMMANDS) > 0

    def test_database_commands_all_values_sets(self):
        """Test that all values are sets."""
        assert all(isinstance(value, set) for value in DATABASE_COMMANDS.values())

    def test_postgresql_key_exists(self):
        """Test that PostgreSQL key exists."""
        assert "postgresql" in DATABASE_COMMANDS

    def test_postgresql_has_psql(self):
        """Test that PostgreSQL has psql command."""
        assert "psql" in DATABASE_COMMANDS["postgresql"]

    def test_postgresql_has_tools(self):
        """Test that PostgreSQL has management tools."""
        pg_tools = {"pg_dump", "pg_restore", "createdb", "dropdb"}
        assert pg_tools.issubset(DATABASE_COMMANDS["postgresql"])

    def test_mysql_key_exists(self):
        """Test that MySQL key exists."""
        assert "mysql" in DATABASE_COMMANDS

    def test_mysql_has_client(self):
        """Test that MySQL has mysql client."""
        assert "mysql" in DATABASE_COMMANDS["mysql"]

    def test_mariadb_key_exists(self):
        """Test that MariaDB key exists."""
        assert "mariadb" in DATABASE_COMMANDS

    def test_mongodb_key_exists(self):
        """Test that MongoDB key exists."""
        assert "mongodb" in DATABASE_COMMANDS

    def test_mongodb_has_mongosh(self):
        """Test that MongoDB has mongosh command."""
        assert "mongosh" in DATABASE_COMMANDS["mongodb"]

    def test_redis_key_exists(self):
        """Test that Redis key exists."""
        assert "redis" in DATABASE_COMMANDS

    def test_redis_has_cli(self):
        """Test that Redis has redis-cli."""
        assert "redis-cli" in DATABASE_COMMANDS["redis"]

    def test_sqlite_key_exists(self):
        """Test that SQLite key exists."""
        assert "sqlite" in DATABASE_COMMANDS

    def test_sqlite_has_commands(self):
        """Test that SQLite has sqlite3 command."""
        assert "sqlite3" in DATABASE_COMMANDS["sqlite"]

    def test_orm_tools_included(self):
        """Test that ORM tools are included."""
        assert "prisma" in DATABASE_COMMANDS
        assert "drizzle" in DATABASE_COMMANDS
        assert "typeorm" in DATABASE_COMMANDS
        assert "sequelize" in DATABASE_COMMANDS


# =============================================================================
# INFRASTRUCTURE_COMMANDS Tests
# =============================================================================

class TestInfrastructureCommands:
    """Tests for INFRASTRUCTURE_COMMANDS dictionary."""

    def test_infrastructure_commands_is_dict(self):
        """Test that INFRASTRUCTURE_COMMANDS is a dictionary."""
        assert isinstance(INFRASTRUCTURE_COMMANDS, dict)

    def test_infrastructure_commands_not_empty(self):
        """Test that INFRASTRUCTURE_COMMANDS is not empty."""
        assert len(INFRASTRUCTURE_COMMANDS) > 0

    def test_infrastructure_commands_all_values_sets(self):
        """Test that all values are sets."""
        assert all(isinstance(value, set) for value in INFRASTRUCTURE_COMMANDS.values())

    def test_docker_key_exists(self):
        """Test that Docker key exists."""
        assert "docker" in INFRASTRUCTURE_COMMANDS

    def test_docker_has_docker_command(self):
        """Test that Docker has docker command."""
        assert "docker" in INFRASTRUCTURE_COMMANDS["docker"]

    def test_docker_has_compose(self):
        """Test that Docker has docker-compose."""
        assert "docker-compose" in INFRASTRUCTURE_COMMANDS["docker"]

    def test_podman_key_exists(self):
        """Test that Podman key exists."""
        assert "podman" in INFRASTRUCTURE_COMMANDS

    def test_kubernetes_key_exists(self):
        """Test that Kubernetes key exists."""
        assert "kubernetes" in INFRASTRUCTURE_COMMANDS

    def test_kubernetes_has_kubectl(self):
        """Test that Kubernetes has kubectl."""
        assert "kubectl" in INFRASTRUCTURE_COMMANDS["kubernetes"]

    def test_kubernetes_has_tools(self):
        """Test that Kubernetes has k9s and other tools."""
        k8s_tools = {"k9s", "kubectx", "kubens"}
        assert k8s_tools.issubset(INFRASTRUCTURE_COMMANDS["kubernetes"])

    def test_helm_key_exists(self):
        """Test that Helm key exists."""
        assert "helm" in INFRASTRUCTURE_COMMANDS

    def test_terraform_key_exists(self):
        """Test that Terraform key exists."""
        assert "terraform" in INFRASTRUCTURE_COMMANDS

    def test_ansible_key_exists(self):
        """Test that Ansible key exists."""
        assert "ansible" in INFRASTRUCTURE_COMMANDS

    def test_vagrant_key_exists(self):
        """Test that Vagrant key exists."""
        assert "vagrant" in INFRASTRUCTURE_COMMANDS


# =============================================================================
# CLOUD_COMMANDS Tests
# =============================================================================

class TestCloudCommands:
    """Tests for CLOUD_COMMANDS dictionary."""

    def test_cloud_commands_is_dict(self):
        """Test that CLOUD_COMMANDS is a dictionary."""
        assert isinstance(CLOUD_COMMANDS, dict)

    def test_cloud_commands_not_empty(self):
        """Test that CLOUD_COMMANDS is not empty."""
        assert len(CLOUD_COMMANDS) > 0

    def test_cloud_commands_all_values_sets(self):
        """Test that all values are sets."""
        assert all(isinstance(value, set) for value in CLOUD_COMMANDS.values())

    def test_aws_key_exists(self):
        """Test that AWS key exists."""
        assert "aws" in CLOUD_COMMANDS

    def test_aws_has_aws_command(self):
        """Test that AWS has aws command."""
        assert "aws" in CLOUD_COMMANDS["aws"]

    def test_aws_has_cdk(self):
        """Test that AWS has CDK."""
        assert "cdk" in CLOUD_COMMANDS["aws"]

    def test_gcp_key_exists(self):
        """Test that GCP key exists."""
        assert "gcp" in CLOUD_COMMANDS

    def test_gcp_has_gcloud(self):
        """Test that GCP has gcloud command."""
        assert "gcloud" in CLOUD_COMMANDS["gcp"]

    def test_azure_key_exists(self):
        """Test that Azure key exists."""
        assert "azure" in CLOUD_COMMANDS

    def test_azure_has_az_command(self):
        """Test that Azure has az command."""
        assert "az" in CLOUD_COMMANDS["azure"]

    def test_vercel_key_exists(self):
        """Test that Vercel key exists."""
        assert "vercel" in CLOUD_COMMANDS

    def test_netlify_key_exists(self):
        """Test that Netlify key exists."""
        assert "netlify" in CLOUD_COMMANDS

    def test_heroku_key_exists(self):
        """Test that Heroku key exists."""
        assert "heroku" in CLOUD_COMMANDS

    def test_railway_key_exists(self):
        """Test that Railway key exists."""
        assert "railway" in CLOUD_COMMANDS

    def test_fly_key_exists(self):
        """Test that Fly.io key exists."""
        assert "fly" in CLOUD_COMMANDS

    def test_cloudflare_key_exists(self):
        """Test that Cloudflare key exists."""
        assert "cloudflare" in CLOUD_COMMANDS


# =============================================================================
# CODE_QUALITY_COMMANDS Tests
# =============================================================================

class TestCodeQualityCommands:
    """Tests for CODE_QUALITY_COMMANDS dictionary."""

    def test_code_quality_commands_is_dict(self):
        """Test that CODE_QUALITY_COMMANDS is a dictionary."""
        assert isinstance(CODE_QUALITY_COMMANDS, dict)

    def test_code_quality_commands_not_empty(self):
        """Test that CODE_QUALITY_COMMANDS is not empty."""
        assert len(CODE_QUALITY_COMMANDS) > 0

    def test_code_quality_commands_all_values_sets(self):
        """Test that all values are sets."""
        assert all(isinstance(value, set) for value in CODE_QUALITY_COMMANDS.values())

    def test_shellcheck_key_exists(self):
        """Test that shellcheck key exists."""
        assert "shellcheck" in CODE_QUALITY_COMMANDS

    def test_hadolint_key_exists(self):
        """Test that hadolint key exists."""
        assert "hadolint" in CODE_QUALITY_COMMANDS

    def test_yamllint_key_exists(self):
        """Test that yamllint key exists."""
        assert "yamllint" in CODE_QUALITY_COMMANDS

    def test_markdownlint_key_exists(self):
        """Test that markdownlint key exists."""
        assert "markdownlint" in CODE_QUALITY_COMMANDS

    def test_security_scanners(self):
        """Test that security scanners are included."""
        security_tools = {"gitleaks", "trufflehog", "detect-secrets"}
        assert security_tools.issubset(CODE_QUALITY_COMMANDS.keys())

    def test_semgrep_key_exists(self):
        """Test that semgrep key exists."""
        assert "semgrep" in CODE_QUALITY_COMMANDS

    def test_snyk_key_exists(self):
        """Test that snyk key exists."""
        assert "snyk" in CODE_QUALITY_COMMANDS

    def test_trivy_key_exists(self):
        """Test that trivy key exists."""
        assert "trivy" in CODE_QUALITY_COMMANDS

    def test_code_counting_tools(self):
        """Test that code counting tools are included."""
        counting_tools = {"cloc", "scc", "tokei"}
        assert counting_tools.issubset(CODE_QUALITY_COMMANDS.keys())


# =============================================================================
# VERSION_MANAGER_COMMANDS Tests
# =============================================================================

class TestVersionManagerCommands:
    """Tests for VERSION_MANAGER_COMMANDS dictionary."""

    def test_version_manager_commands_is_dict(self):
        """Test that VERSION_MANAGER_COMMANDS is a dictionary."""
        assert isinstance(VERSION_MANAGER_COMMANDS, dict)

    def test_version_manager_commands_not_empty(self):
        """Test that VERSION_MANAGER_COMMANDS is not empty."""
        assert len(VERSION_MANAGER_COMMANDS) > 0

    def test_version_manager_commands_all_values_sets(self):
        """Test that all values are sets."""
        assert all(isinstance(value, set) for value in VERSION_MANAGER_COMMANDS.values())

    def test_asdf_key_exists(self):
        """Test that asdf key exists."""
        assert "asdf" in VERSION_MANAGER_COMMANDS

    def test_mise_key_exists(self):
        """Test that mise key exists."""
        assert "mise" in VERSION_MANAGER_COMMANDS

    def test_nvm_key_exists(self):
        """Test that nvm key exists."""
        assert "nvm" in VERSION_MANAGER_COMMANDS

    def test_fnm_key_exists(self):
        """Test that fnm key exists."""
        assert "fnm" in VERSION_MANAGER_COMMANDS

    def test_pyenv_key_exists(self):
        """Test that pyenv key exists."""
        assert "pyenv" in VERSION_MANAGER_COMMANDS

    def test_rbenv_key_exists(self):
        """Test that rbenv key exists."""
        assert "rbenv" in VERSION_MANAGER_COMMANDS

    def test_rvm_key_exists(self):
        """Test that rvm key exists."""
        assert "rvm" in VERSION_MANAGER_COMMANDS

    def test_goenv_key_exists(self):
        """Test that goenv key exists."""
        assert "goenv" in VERSION_MANAGER_COMMANDS

    def test_rustup_key_exists(self):
        """Test that rustup key exists."""
        assert "rustup" in VERSION_MANAGER_COMMANDS

    def test_sdkman_key_exists(self):
        """Test that sdkman key exists."""
        assert "sdkman" in VERSION_MANAGER_COMMANDS

    def test_fvm_key_exists(self):
        """Test that fvm (Flutter Version Manager) key exists."""
        assert "fvm" in VERSION_MANAGER_COMMANDS

    def test_fvm_has_flutter(self):
        """Test that fvm includes flutter command."""
        assert "flutter" in VERSION_MANAGER_COMMANDS["fvm"]


# =============================================================================
# Data Integrity Tests (All Modules)
# =============================================================================

class TestAllModulesDataIntegrity:
    """Tests for data integrity across all modules."""

    def test_no_empty_keys_in_any_module(self):
        """Test no empty keys in any module."""
        modules = [
            PACKAGE_MANAGER_COMMANDS,
            FRAMEWORK_COMMANDS,
            DATABASE_COMMANDS,
            INFRASTRUCTURE_COMMANDS,
            CLOUD_COMMANDS,
            CODE_QUALITY_COMMANDS,
            VERSION_MANAGER_COMMANDS,
        ]
        for module in modules:
            assert "" not in module

    def test_no_empty_command_sets_in_any_module(self):
        """Test no empty command sets in any module."""
        modules = [
            PACKAGE_MANAGER_COMMANDS,
            FRAMEWORK_COMMANDS,
            DATABASE_COMMANDS,
            INFRASTRUCTURE_COMMANDS,
            CLOUD_COMMANDS,
            CODE_QUALITY_COMMANDS,
            VERSION_MANAGER_COMMANDS,
        ]
        for module in modules:
            for key, commands in module.items():
                assert len(commands) > 0, f"{key} has empty command set"

    def test_all_commands_are_strings(self):
        """Test all commands are strings."""
        modules = [
            PACKAGE_MANAGER_COMMANDS,
            FRAMEWORK_COMMANDS,
            DATABASE_COMMANDS,
            INFRASTRUCTURE_COMMANDS,
            CLOUD_COMMANDS,
            CODE_QUALITY_COMMANDS,
            VERSION_MANAGER_COMMANDS,
        ]
        for module in modules:
            for commands in module.values():
                assert all(isinstance(cmd, str) for cmd in commands)

    def test_no_leading_trailing_whitespace(self):
        """Test no commands have leading/trailing whitespace."""
        modules = [
            PACKAGE_MANAGER_COMMANDS,
            FRAMEWORK_COMMANDS,
            DATABASE_COMMANDS,
            INFRASTRUCTURE_COMMANDS,
            CLOUD_COMMANDS,
            CODE_QUALITY_COMMANDS,
            VERSION_MANAGER_COMMANDS,
        ]
        for module in modules:
            for commands in module.values():
                for cmd in commands:
                    assert cmd == cmd.strip()

    def test_all_keys_lowercase(self):
        """Test all keys are lowercase."""
        modules = [
            PACKAGE_MANAGER_COMMANDS,
            FRAMEWORK_COMMANDS,
            DATABASE_COMMANDS,
            INFRASTRUCTURE_COMMANDS,
            CLOUD_COMMANDS,
            CODE_QUALITY_COMMANDS,
            VERSION_MANAGER_COMMANDS,
        ]
        for module in modules:
            for key in module.keys():
                assert key.islower() or "_" in key or "-" in key


# =============================================================================
# Coverage Tests (All Modules)
# =============================================================================

class TestAllModulesCoverage:
    """Tests for comprehensive coverage across all modules."""

    def test_javascript_ecosystem_coverage(self):
        """Test comprehensive JavaScript ecosystem coverage."""
        js_package_managers = {"npm", "yarn", "pnpm", "bun"}
        assert js_package_managers.issubset(PACKAGE_MANAGER_COMMANDS.keys())

        js_frameworks = {"nextjs", "nuxt", "react", "vue", "angular"}
        assert js_frameworks.issubset(FRAMEWORK_COMMANDS.keys())

    def test_python_ecosystem_coverage(self):
        """Test comprehensive Python ecosystem coverage."""
        python_package_managers = {"pip", "poetry", "uv", "pdm"}
        assert python_package_managers.issubset(PACKAGE_MANAGER_COMMANDS.keys())

        python_frameworks = {"django", "flask", "fastapi"}
        assert python_frameworks.issubset(FRAMEWORK_COMMANDS.keys())

    def test_container_ecosystem_coverage(self):
        """Test container/DevOps ecosystem coverage."""
        container_tools = {"docker", "podman", "kubernetes"}
        assert container_tools.issubset(INFRASTRUCTURE_COMMANDS.keys())

        orchestration = {"helm", "terraform", "ansible"}
        assert orchestration.issubset(INFRASTRUCTURE_COMMANDS.keys())

    def test_cloud_platforms_coverage(self):
        """Test major cloud platforms coverage."""
        major_clouds = {"aws", "gcp", "azure"}
        assert major_clouds.issubset(CLOUD_COMMANDS.keys())

        modern_platforms = {"vercel", "netlify", "railway", "fly"}
        assert modern_platforms.issubset(CLOUD_COMMANDS.keys())

    def test_database_variety_coverage(self):
        """Test variety of databases covered."""
        sql_dbs = {"postgresql", "mysql", "mariadb"}
        assert sql_dbs.issubset(DATABASE_COMMANDS.keys())

        nosql_dbs = {"mongodb", "redis", "sqlite"}
        assert nosql_dbs.issubset(DATABASE_COMMANDS.keys())

    def test_security_tools_coverage(self):
        """Test security scanning tools coverage."""
        security_tools = {"semgrep", "snyk", "trivy", "gitleaks"}
        assert security_tools.issubset(CODE_QUALITY_COMMANDS.keys())

    def test_version_managers_variety(self):
        """Test variety of version managers covered."""
        language_managers = {"nvm", "pyenv", "rbenv", "rustup"}
        assert language_managers.issubset(VERSION_MANAGER_COMMANDS.keys())

        universal_managers = {"asdf", "mise"}
        assert universal_managers.issubset(VERSION_MANAGER_COMMANDS.keys())


# =============================================================================
# Edge Cases (All Modules)
# =============================================================================

class TestAllModulesEdgeCases:
    """Tests for edge cases across all modules."""

    def test_commands_with_special_characters(self):
        """Test handling of commands with special characters."""
        # Check for hyphens, dots in commands
        for module in [
            PACKAGE_MANAGER_COMMANDS,
            FRAMEWORK_COMMANDS,
            DATABASE_COMMANDS,
            INFRASTRUCTURE_COMMANDS,
            CLOUD_COMMANDS,
            CODE_QUALITY_COMMANDS,
            VERSION_MANAGER_COMMANDS,
        ]:
            for commands in module.values():
                for cmd in commands:
                    # Commands can have hyphens, dots, but should be valid
                    if "-" in cmd:
                        parts = cmd.split("-")
                        assert all(p.isalnum() or p.isdigit() for p in parts)
                    if "." in cmd:
                        parts = cmd.split(".")
                        assert all(p.isalnum() or p.isdigit() for p in parts)

    def test_no_single_character_commands(self):
        """Test handling of single-character commands (if any)."""
        # Single-char commands are rare but valid (e.g., 'w' for who)
        for module in [
            PACKAGE_MANAGER_COMMANDS,
            FRAMEWORK_COMMANDS,
            DATABASE_COMMANDS,
            INFRASTRUCTURE_COMMANDS,
            CLOUD_COMMANDS,
            CODE_QUALITY_COMMANDS,
            VERSION_MANAGER_COMMANDS,
        ]:
            for commands in module.values():
                for cmd in commands:
                    if len(cmd) == 1:
                        assert cmd.isalnum()

    def test_dart_flutter_integration(self):
        """Test Dart/Flutter integration across modules."""
        # Check for consistency
        assert "pub" in PACKAGE_MANAGER_COMMANDS
        assert "fvm" in VERSION_MANAGER_COMMANDS
        assert "flutter" in FRAMEWORK_COMMANDS

    def test_npx_usage_across_modules(self):
        """Test npx is referenced appropriately."""
        # npx appears in multiple contexts
        assert "npx" in PACKAGE_MANAGER_COMMANDS.get("npm", set())
        # Some frameworks use npx
        frameworks_with_npx = [k for k, v in FRAMEWORK_COMMANDS.items() if "npx" in v]
        assert len(frameworks_with_npx) > 0

    def test_dot_command_consistency(self):
        """Test consistency of dot-related commands."""
        # dotnet is in nuget package managers
        assert "dotnet" in PACKAGE_MANAGER_COMMANDS.get("nuget", set())
        # Note: FRAMEWORK_COMMANDS doesn't have csharp as a key
        # .NET frameworks are handled through the package manager
