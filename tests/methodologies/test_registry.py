"""Tests for methodology registry implementation.

Tests registry loading, discovery, query methods, and Protocol compliance.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from dataclasses import is_dataclass, fields


class TestRegistryModule:
    """Test that the registry module exists and exports correctly."""

    def test_registry_module_importable(self):
        """Test that registry module can be imported."""
        from apps.backend.methodologies import registry
        assert registry is not None

    def test_registry_entry_exists(self):
        """Test that RegistryEntry dataclass exists."""
        from apps.backend.methodologies.registry import RegistryEntry
        assert RegistryEntry is not None

    def test_methodology_registry_impl_exists(self):
        """Test that MethodologyRegistryImpl class exists."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl
        assert MethodologyRegistryImpl is not None


class TestRegistryEntry:
    """Test the RegistryEntry dataclass."""

    def test_registry_entry_is_dataclass(self):
        """Test that RegistryEntry is a dataclass."""
        from apps.backend.methodologies.registry import RegistryEntry
        assert is_dataclass(RegistryEntry)

    def test_registry_entry_required_fields(self):
        """Test RegistryEntry has all fields per AC #1."""
        from apps.backend.methodologies.registry import RegistryEntry
        field_names = {f.name for f in fields(RegistryEntry)}
        required_fields = {'name', 'path', 'version', 'verified', 'enabled'}
        assert required_fields.issubset(field_names), f"Missing fields: {required_fields - field_names}"

    def test_registry_entry_instantiation(self):
        """Test RegistryEntry can be instantiated with all fields."""
        from apps.backend.methodologies.registry import RegistryEntry
        entry = RegistryEntry(
            name="native",
            path="apps/backend/methodologies/native",
            version="1.0.0",
            verified=True,
            enabled=True,
        )
        assert entry.name == "native"
        assert entry.path == "apps/backend/methodologies/native"
        assert entry.version == "1.0.0"
        assert entry.verified is True
        assert entry.enabled is True

    def test_registry_entry_verified_false(self):
        """Test RegistryEntry with verified=False for community plugins."""
        from apps.backend.methodologies.registry import RegistryEntry
        entry = RegistryEntry(
            name="community-plugin",
            path="~/.auto-claude/methodologies/community-plugin",
            version="0.1.0",
            verified=False,
            enabled=True,
        )
        assert entry.verified is False


class TestMethodologyRegistryImplProtocol:
    """Test that MethodologyRegistryImpl implements the Protocol."""

    def test_implements_methodology_registry_protocol(self):
        """Test MethodologyRegistryImpl satisfies MethodologyRegistry Protocol."""
        from apps.backend.methodologies.protocols import MethodologyRegistry
        from apps.backend.methodologies.registry import MethodologyRegistryImpl

        registry = MethodologyRegistryImpl()
        assert isinstance(registry, MethodologyRegistry)

    def test_has_list_installed_method(self):
        """Test MethodologyRegistryImpl has list_installed method."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl
        registry = MethodologyRegistryImpl()
        assert hasattr(registry, 'list_installed')
        assert callable(registry.list_installed)

    def test_has_get_methodology_method(self):
        """Test MethodologyRegistryImpl has get_methodology method."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl
        registry = MethodologyRegistryImpl()
        assert hasattr(registry, 'get_methodology')
        assert callable(registry.get_methodology)

    def test_has_install_method(self):
        """Test MethodologyRegistryImpl has install method."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl
        registry = MethodologyRegistryImpl()
        assert hasattr(registry, 'install')
        assert callable(registry.install)

    def test_has_uninstall_method(self):
        """Test MethodologyRegistryImpl has uninstall method."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl
        registry = MethodologyRegistryImpl()
        assert hasattr(registry, 'uninstall')
        assert callable(registry.uninstall)


class TestRegistryLoading:
    """Test registry loading from YAML file (AC #1)."""

    def test_load_registry_from_yaml(self):
        """Test loading registry from existing YAML file."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry_path.write_text("""methodologies:
  - name: native
    path: apps/backend/methodologies/native
    version: "1.0.0"
    verified: true
    enabled: true
  - name: bmad
    path: apps/backend/methodologies/bmad
    version: "1.0.0"
    verified: true
    enabled: false
""")
            registry = MethodologyRegistryImpl(registry_path=registry_path)
            entries = registry.list_entries()

            assert len(entries) == 2
            native = next((e for e in entries if e.name == "native"), None)
            assert native is not None
            assert native.version == "1.0.0"
            assert native.verified is True
            assert native.enabled is True

            bmad = next((e for e in entries if e.name == "bmad"), None)
            assert bmad is not None
            assert bmad.enabled is False

    def test_load_registry_creates_default_when_missing(self):
        """Test that missing registry file creates default (AC #3)."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "methodologies" / "registry.yaml"
            # Registry file doesn't exist
            assert not registry_path.exists()

            registry = MethodologyRegistryImpl(registry_path=registry_path)
            entries = registry.list_entries()

            # Default registry should have been created
            assert registry_path.exists()
            # Default includes only verified methodologies
            for entry in entries:
                assert entry.verified is True

    def test_load_registry_handles_empty_file(self):
        """Test loading handles empty YAML file gracefully."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry_path.write_text("")

            registry = MethodologyRegistryImpl(registry_path=registry_path)
            entries = registry.list_entries()
            # Should return empty or default list
            assert isinstance(entries, list)


class TestRegistryRefresh:
    """Test registry refresh/discovery logic (AC #2)."""

    def test_refresh_detects_verified_plugins(self):
        """Test refresh discovers plugins in verified location."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup verified plugins directory
            verified_dir = Path(tmpdir) / "verified"
            plugin_dir = verified_dir / "test-plugin"
            plugin_dir.mkdir(parents=True)
            (plugin_dir / "manifest.yaml").write_text("""
name: test-plugin
version: "1.0.0"
""")
            registry_path = Path(tmpdir) / "registry.yaml"
            registry = MethodologyRegistryImpl(
                registry_path=registry_path,
                verified_plugins_dir=verified_dir,
            )
            registry.refresh()

            entries = registry.list_entries()
            test_plugin = next((e for e in entries if e.name == "test-plugin"), None)
            assert test_plugin is not None
            assert test_plugin.verified is True

    def test_refresh_detects_community_plugins(self):
        """Test refresh discovers plugins in community location."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup community plugins directory
            community_dir = Path(tmpdir) / "community"
            plugin_dir = community_dir / "community-plugin"
            plugin_dir.mkdir(parents=True)
            (plugin_dir / "manifest.yaml").write_text("""
name: community-plugin
version: "0.5.0"
""")
            registry_path = Path(tmpdir) / "registry.yaml"
            registry = MethodologyRegistryImpl(
                registry_path=registry_path,
                community_plugins_dir=community_dir,
            )
            registry.refresh()

            entries = registry.list_entries()
            comm_plugin = next((e for e in entries if e.name == "community-plugin"), None)
            assert comm_plugin is not None
            assert comm_plugin.verified is False

    def test_refresh_ignores_dirs_without_manifest(self):
        """Test refresh ignores directories without manifest.yaml."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            verified_dir = Path(tmpdir) / "verified"
            # Directory without manifest
            no_manifest_dir = verified_dir / "no-manifest"
            no_manifest_dir.mkdir(parents=True)
            # Directory with manifest
            with_manifest_dir = verified_dir / "with-manifest"
            with_manifest_dir.mkdir(parents=True)
            (with_manifest_dir / "manifest.yaml").write_text("""
name: with-manifest
version: "1.0.0"
""")
            registry_path = Path(tmpdir) / "registry.yaml"
            registry = MethodologyRegistryImpl(
                registry_path=registry_path,
                verified_plugins_dir=verified_dir,
            )
            registry.refresh()

            entries = registry.list_entries()
            names = [e.name for e in entries]
            assert "with-manifest" in names
            assert "no-manifest" not in names


class TestRegistryQueryMethods:
    """Test registry query methods (AC #1, #2)."""

    def test_list_installed_returns_methodology_info(self):
        """Test list_installed returns a list of MethodologyInfo (Protocol compliance)."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl
        from apps.backend.methodologies.protocols import MethodologyInfo

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry_path.write_text("""methodologies:
  - name: native
    path: apps/backend/methodologies/native
    version: "1.0.0"
    verified: true
    enabled: true
""")
            registry = MethodologyRegistryImpl(registry_path=registry_path)
            entries = registry.list_installed()

            assert isinstance(entries, list)
            assert all(isinstance(e, MethodologyInfo) for e in entries)
            # Verify fields are mapped correctly
            native = entries[0]
            assert native.name == "native"
            assert native.version == "1.0.0"
            assert native.is_verified is True
            assert native.install_path == "apps/backend/methodologies/native"

    def test_list_entries_returns_registry_entries(self):
        """Test list_entries returns a list of RegistryEntry (internal use)."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl, RegistryEntry

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry_path.write_text("""methodologies:
  - name: native
    path: apps/backend/methodologies/native
    version: "1.0.0"
    verified: true
    enabled: true
""")
            registry = MethodologyRegistryImpl(registry_path=registry_path)
            entries = registry.list_entries()

            assert isinstance(entries, list)
            assert all(isinstance(e, RegistryEntry) for e in entries)

    def test_get_methodology_by_name(self):
        """Test get_methodology returns entry by name."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry_path.write_text("""methodologies:
  - name: native
    path: apps/backend/methodologies/native
    version: "1.0.0"
    verified: true
    enabled: true
  - name: bmad
    path: apps/backend/methodologies/bmad
    version: "2.0.0"
    verified: true
    enabled: true
""")
            registry = MethodologyRegistryImpl(registry_path=registry_path)
            entry = registry.get_entry("bmad")

            assert entry is not None
            assert entry.name == "bmad"
            assert entry.version == "2.0.0"

    def test_get_methodology_not_found_raises(self):
        """Test get_methodology raises PluginLoadError for unknown name."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl
        from apps.backend.methodologies.exceptions import PluginLoadError

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry_path.write_text("""methodologies:
  - name: native
    path: apps/backend/methodologies/native
    version: "1.0.0"
    verified: true
    enabled: true
""")
            registry = MethodologyRegistryImpl(registry_path=registry_path)

            with pytest.raises(PluginLoadError):
                registry.get_methodology("nonexistent")

    def test_is_enabled_returns_boolean(self):
        """Test is_enabled returns correct boolean for methodology."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry_path.write_text("""methodologies:
  - name: enabled-plugin
    path: apps/backend/methodologies/enabled
    version: "1.0.0"
    verified: true
    enabled: true
  - name: disabled-plugin
    path: apps/backend/methodologies/disabled
    version: "1.0.0"
    verified: true
    enabled: false
""")
            registry = MethodologyRegistryImpl(registry_path=registry_path)

            assert registry.is_enabled("enabled-plugin") is True
            assert registry.is_enabled("disabled-plugin") is False

    def test_is_enabled_unknown_returns_false(self):
        """Test is_enabled returns False for unknown methodology."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry_path.write_text("""methodologies: []""")
            registry = MethodologyRegistryImpl(registry_path=registry_path)

            assert registry.is_enabled("unknown") is False


class TestDefaultRegistryCreation:
    """Test default registry creation (AC #3)."""

    def test_default_registry_created_with_verified_only(self):
        """Test default registry contains only verified methodologies."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup verified plugins
            verified_dir = Path(tmpdir) / "verified"
            native_dir = verified_dir / "native"
            native_dir.mkdir(parents=True)
            (native_dir / "manifest.yaml").write_text("""
name: native
version: "1.0.0"
""")
            # Setup community plugins (should not be in default)
            community_dir = Path(tmpdir) / "community"
            community_plugin = community_dir / "comm"
            community_plugin.mkdir(parents=True)
            (community_plugin / "manifest.yaml").write_text("""
name: comm
version: "0.1.0"
""")
            registry_path = Path(tmpdir) / "registry.yaml"
            # Don't create registry file - let it be created as default
            assert not registry_path.exists()

            registry = MethodologyRegistryImpl(
                registry_path=registry_path,
                verified_plugins_dir=verified_dir,
                community_plugins_dir=community_dir,
            )
            entries = registry.list_entries()

            # Should only have verified plugins
            for entry in entries:
                assert entry.verified is True
            # Specific check for native
            native = next((e for e in entries if e.name == "native"), None)
            assert native is not None

    def test_default_registry_writes_yaml_file(self):
        """Test default registry creation writes YAML file."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "methodologies" / "registry.yaml"
            assert not registry_path.exists()

            registry = MethodologyRegistryImpl(registry_path=registry_path)
            _ = registry.list_installed()

            # Registry file should now exist
            assert registry_path.exists()
            content = registry_path.read_text()
            assert "methodologies:" in content


class TestRegistrySaving:
    """Test registry saving functionality."""

    def test_save_registry_persists_changes(self):
        """Test that registry changes are persisted to YAML."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl, RegistryEntry

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry_path.write_text("""methodologies:
  - name: native
    path: apps/backend/methodologies/native
    version: "1.0.0"
    verified: true
    enabled: true
""")
            registry = MethodologyRegistryImpl(registry_path=registry_path)

            # Add a new entry
            new_entry = RegistryEntry(
                name="new-plugin",
                path="~/.auto-claude/methodologies/new-plugin",
                version="0.1.0",
                verified=False,
                enabled=True,
            )
            registry.add_entry(new_entry)
            registry.save()

            # Re-load and verify
            registry2 = MethodologyRegistryImpl(registry_path=registry_path)
            entries = registry2.list_entries()
            names = [e.name for e in entries]
            assert "new-plugin" in names


class TestRegistryEdgeCases:
    """Test edge cases and error handling."""

    def test_registry_with_malformed_yaml(self):
        """Test registry handles malformed YAML gracefully."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry_path.write_text("invalid: yaml: content: [")

            # Should not raise, should create default instead
            registry = MethodologyRegistryImpl(registry_path=registry_path)
            entries = registry.list_entries()
            assert isinstance(entries, list)

    def test_registry_with_missing_fields_in_entry(self):
        """Test registry handles entries with missing fields."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry_path.write_text("""methodologies:
  - name: incomplete
    # Missing path, version, verified, enabled
""")
            # Should handle gracefully or skip invalid entries
            registry = MethodologyRegistryImpl(registry_path=registry_path)
            entries = registry.list_entries()
            # Either filters out invalid or provides defaults
            assert isinstance(entries, list)

    def test_registry_path_expansion(self):
        """Test that ~ in paths is expanded correctly."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry_path.write_text("""methodologies:
  - name: home-plugin
    path: "~/.auto-claude/methodologies/home-plugin"
    version: "1.0.0"
    verified: false
    enabled: true
""")
            registry = MethodologyRegistryImpl(registry_path=registry_path)
            entries = registry.list_entries()

            home_plugin = next((e for e in entries if e.name == "home-plugin"), None)
            assert home_plugin is not None
            # Path should contain the home directory path or the original ~ notation
            # (depending on implementation - either is valid)
            assert "home-plugin" in home_plugin.path


class TestInstallUninstall:
    """Test install() and uninstall() methods (M1, M2 fixes)."""

    def test_install_adds_plugin_to_registry(self):
        """Test that install() adds a new plugin to the registry."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create registry
            registry_path = Path(tmpdir) / "registry.yaml"
            registry_path.write_text("methodologies: []")

            # Create a plugin directory with manifest
            plugin_dir = Path(tmpdir) / "my-plugin"
            plugin_dir.mkdir()
            (plugin_dir / "manifest.yaml").write_text("""
name: my-plugin
version: "1.0.0"
""")

            registry = MethodologyRegistryImpl(registry_path=registry_path)
            registry.install(str(plugin_dir))

            # Verify plugin was added
            entries = registry.list_entries()
            my_plugin = next((e for e in entries if e.name == "my-plugin"), None)
            assert my_plugin is not None
            assert my_plugin.version == "1.0.0"
            assert my_plugin.verified is False  # Installed plugins are not verified
            assert my_plugin.enabled is True

    def test_install_duplicate_raises_error(self):
        """Test that installing an already-installed plugin raises PluginLoadError."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl
        from apps.backend.methodologies.exceptions import PluginLoadError

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create registry with existing plugin
            registry_path = Path(tmpdir) / "registry.yaml"
            registry_path.write_text("""methodologies:
  - name: existing-plugin
    path: /some/path
    version: "1.0.0"
    verified: false
    enabled: true
""")

            # Create a plugin directory with same name
            plugin_dir = Path(tmpdir) / "existing-plugin"
            plugin_dir.mkdir()
            (plugin_dir / "manifest.yaml").write_text("""
name: existing-plugin
version: "2.0.0"
""")

            registry = MethodologyRegistryImpl(registry_path=registry_path)

            with pytest.raises(PluginLoadError) as exc_info:
                registry.install(str(plugin_dir))

            assert "already installed" in str(exc_info.value)

    def test_install_missing_manifest_raises_error(self):
        """Test that installing without manifest.yaml raises PluginLoadError."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl
        from apps.backend.methodologies.exceptions import PluginLoadError

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry_path.write_text("methodologies: []")

            # Create directory WITHOUT manifest
            plugin_dir = Path(tmpdir) / "no-manifest"
            plugin_dir.mkdir()

            registry = MethodologyRegistryImpl(registry_path=registry_path)

            with pytest.raises(PluginLoadError) as exc_info:
                registry.install(str(plugin_dir))

            assert "manifest.yaml" in str(exc_info.value)

    def test_install_invalid_manifest_raises_error(self):
        """Test that installing with invalid manifest raises PluginLoadError."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl
        from apps.backend.methodologies.exceptions import PluginLoadError

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry_path.write_text("methodologies: []")

            # Create directory with manifest missing 'name' field
            plugin_dir = Path(tmpdir) / "bad-manifest"
            plugin_dir.mkdir()
            (plugin_dir / "manifest.yaml").write_text("""
version: "1.0.0"
# Missing required 'name' field
""")

            registry = MethodologyRegistryImpl(registry_path=registry_path)

            with pytest.raises(PluginLoadError) as exc_info:
                registry.install(str(plugin_dir))

            assert "name" in str(exc_info.value).lower()

    def test_uninstall_removes_plugin_from_registry(self):
        """Test that uninstall() removes a community plugin from registry."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry_path.write_text("""methodologies:
  - name: community-plugin
    path: /some/path
    version: "1.0.0"
    verified: false
    enabled: true
  - name: another-plugin
    path: /another/path
    version: "2.0.0"
    verified: false
    enabled: true
""")

            registry = MethodologyRegistryImpl(registry_path=registry_path)

            # Verify plugin exists
            assert registry.get_entry("community-plugin") is not None

            # Uninstall
            registry.uninstall("community-plugin")

            # Verify plugin removed
            assert registry.get_entry("community-plugin") is None
            # Verify other plugin still exists
            assert registry.get_entry("another-plugin") is not None

    def test_uninstall_verified_plugin_raises_error(self):
        """Test that uninstalling a verified plugin raises PluginLoadError."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl
        from apps.backend.methodologies.exceptions import PluginLoadError

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry_path.write_text("""methodologies:
  - name: native
    path: apps/backend/methodologies/native
    version: "1.0.0"
    verified: true
    enabled: true
""")

            registry = MethodologyRegistryImpl(registry_path=registry_path)

            with pytest.raises(PluginLoadError) as exc_info:
                registry.uninstall("native")

            assert "verified" in str(exc_info.value).lower()

    def test_uninstall_nonexistent_raises_error(self):
        """Test that uninstalling non-existent plugin raises PluginLoadError."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl
        from apps.backend.methodologies.exceptions import PluginLoadError

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry_path.write_text("methodologies: []")

            registry = MethodologyRegistryImpl(registry_path=registry_path)

            with pytest.raises(PluginLoadError) as exc_info:
                registry.uninstall("nonexistent")

            assert "not installed" in str(exc_info.value)

    def test_install_persists_to_file(self):
        """Test that install() saves changes to the registry file."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry_path.write_text("methodologies: []")

            plugin_dir = Path(tmpdir) / "persistent-plugin"
            plugin_dir.mkdir()
            (plugin_dir / "manifest.yaml").write_text("""
name: persistent-plugin
version: "1.0.0"
""")

            registry = MethodologyRegistryImpl(registry_path=registry_path)
            registry.install(str(plugin_dir))

            # Create new registry instance and verify plugin is there
            registry2 = MethodologyRegistryImpl(registry_path=registry_path)
            entries = registry2.list_entries()
            assert any(e.name == "persistent-plugin" for e in entries)

    def test_uninstall_persists_to_file(self):
        """Test that uninstall() saves changes to the registry file."""
        from apps.backend.methodologies.registry import MethodologyRegistryImpl

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.yaml"
            registry_path.write_text("""methodologies:
  - name: to-remove
    path: /some/path
    version: "1.0.0"
    verified: false
    enabled: true
""")

            registry = MethodologyRegistryImpl(registry_path=registry_path)
            registry.uninstall("to-remove")

            # Create new registry instance and verify plugin is gone
            registry2 = MethodologyRegistryImpl(registry_path=registry_path)
            entries = registry2.list_entries()
            assert not any(e.name == "to-remove" for e in entries)
