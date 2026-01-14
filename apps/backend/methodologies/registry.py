"""Methodology plugin registry implementation.

This module provides a file-based registry that tracks available methodology plugins.
The registry supports verified (bundled) and community (user-installed) plugins.

Architecture Source: architecture.md#Plugin-Registry
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

from apps.backend.methodologies.exceptions import PluginLoadError
from apps.backend.methodologies.protocols import MethodologyInfo, MethodologyRunner

logger = logging.getLogger(__name__)


def _entry_to_info(entry: "RegistryEntry") -> MethodologyInfo:
    """Convert a RegistryEntry to MethodologyInfo for Protocol compliance.

    Args:
        entry: The registry entry to convert

    Returns:
        MethodologyInfo with fields populated from RegistryEntry
    """
    return MethodologyInfo(
        name=entry.name,
        version=entry.version,
        description="",  # Not stored in registry, loaded from manifest
        author="",  # Not stored in registry, loaded from manifest
        complexity_levels=[],  # Not stored in registry, loaded from manifest
        execution_modes=[],  # Not stored in registry, loaded from manifest
        is_verified=entry.verified,
        install_path=entry.path,
    )


@dataclass
class RegistryEntry:
    """Entry in the methodology registry.

    Each entry represents a methodology plugin that is registered with the system.
    Verified plugins are bundled with the application; community plugins are user-installed.

    Attributes:
        name: Unique identifier for the methodology (kebab-case)
        path: Path to the methodology directory (relative or absolute)
        version: Semver version string
        verified: Whether this is a verified (bundled) plugin
        enabled: Whether the methodology is currently enabled
    """

    name: str
    path: str
    version: str
    verified: bool
    enabled: bool


class MethodologyRegistryImpl:
    """Implementation of the MethodologyRegistry protocol.

    This class provides a file-based registry that:
    - Loads and saves registry state to YAML file
    - Discovers plugins in verified and community directories
    - Provides query methods for installed methodologies

    Architecture Source: architecture.md#Plugin-Registry
    """

    def __init__(
        self,
        registry_path: Path | None = None,
        verified_plugins_dir: Path | None = None,
        community_plugins_dir: Path | None = None,
    ) -> None:
        """Initialize the registry.

        Args:
            registry_path: Path to registry YAML file.
                Defaults to ~/.auto-claude/methodologies/registry.yaml
            verified_plugins_dir: Path to verified plugins directory.
                Defaults to apps/backend/methodologies/
            community_plugins_dir: Path to community plugins directory.
                Defaults to ~/.auto-claude/methodologies/
        """
        self._registry_path = registry_path or self._default_registry_path()
        self._verified_plugins_dir = verified_plugins_dir
        self._community_plugins_dir = (
            community_plugins_dir or self._default_community_dir()
        )
        self._entries: list[RegistryEntry] = []
        self._loaded = False

    @staticmethod
    def _default_registry_path() -> Path:
        """Get the default registry file path."""
        return Path.home() / ".auto-claude" / "methodologies" / "registry.yaml"

    @staticmethod
    def _default_community_dir() -> Path:
        """Get the default community plugins directory."""
        return Path.home() / ".auto-claude" / "methodologies"

    def _ensure_loaded(self) -> None:
        """Ensure the registry is loaded from disk."""
        if not self._loaded:
            self._load()

    def _load(self) -> None:
        """Load registry from YAML file, creating default if missing."""
        if not self._registry_path.exists():
            logger.info(
                f"Registry file not found at {self._registry_path}, creating default"
            )
            self._create_default_registry()
        else:
            try:
                self._load_from_yaml()
            except Exception as e:
                logger.warning(
                    f"Failed to load registry from {self._registry_path}: {e}"
                )
                logger.info("Creating default registry instead")
                self._entries = []
                self._create_default_registry()

        self._loaded = True

    def _load_from_yaml(self) -> None:
        """Load registry entries from YAML file."""
        content = self._registry_path.read_text()
        if not content.strip():
            self._entries = []
            return

        data = yaml.safe_load(content)
        if not data or "methodologies" not in data:
            self._entries = []
            return

        methodologies = data.get("methodologies", [])
        if not isinstance(methodologies, list):
            self._entries = []
            return

        self._entries = []
        for entry_data in methodologies:
            if not isinstance(entry_data, dict):
                continue
            try:
                entry = RegistryEntry(
                    name=entry_data.get("name", ""),
                    path=entry_data.get("path", ""),
                    version=entry_data.get("version", "0.0.0"),
                    verified=entry_data.get("verified", False),
                    enabled=entry_data.get("enabled", True),
                )
                if entry.name:  # Only add entries with a name
                    self._entries.append(entry)
            except (TypeError, ValueError) as e:
                logger.warning(
                    f"Skipping invalid registry entry: {entry_data}, error: {e}"
                )
                continue

    def _create_default_registry(self) -> None:
        """Create a default registry with verified plugins only."""
        # Scan verified plugins directory
        verified_entries = self._discover_verified_plugins()
        self._entries = verified_entries

        # Save the default registry
        self.save()

    def _discover_verified_plugins(self) -> list[RegistryEntry]:
        """Discover plugins in the verified plugins directory."""
        entries: list[RegistryEntry] = []

        if self._verified_plugins_dir is None:
            return entries

        if not self._verified_plugins_dir.exists():
            return entries

        for plugin_dir in self._verified_plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue

            manifest_path = plugin_dir / "manifest.yaml"
            if not manifest_path.exists():
                continue

            try:
                manifest_data = yaml.safe_load(manifest_path.read_text())
                if not manifest_data:
                    continue

                entry = RegistryEntry(
                    name=manifest_data.get("name", plugin_dir.name),
                    path=str(plugin_dir),
                    version=manifest_data.get("version", "0.0.0"),
                    verified=True,
                    enabled=True,
                )
                entries.append(entry)
            except Exception as e:
                logger.warning(f"Failed to load manifest from {manifest_path}: {e}")
                continue

        return entries

    def _discover_community_plugins(self) -> list[RegistryEntry]:
        """Discover plugins in the community plugins directory."""
        entries: list[RegistryEntry] = []

        if self._community_plugins_dir is None:
            return entries

        if not self._community_plugins_dir.exists():
            return entries

        for plugin_dir in self._community_plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue

            # Skip registry.yaml file itself and other non-plugin items
            if plugin_dir.name.startswith(".") or plugin_dir.name == "registry.yaml":
                continue

            manifest_path = plugin_dir / "manifest.yaml"
            if not manifest_path.exists():
                continue

            try:
                manifest_data = yaml.safe_load(manifest_path.read_text())
                if not manifest_data:
                    continue

                entry = RegistryEntry(
                    name=manifest_data.get("name", plugin_dir.name),
                    path=str(plugin_dir),
                    version=manifest_data.get("version", "0.0.0"),
                    verified=False,
                    enabled=True,
                )
                entries.append(entry)
            except Exception as e:
                logger.warning(f"Failed to load manifest from {manifest_path}: {e}")
                continue

        return entries

    def refresh(self) -> None:
        """Refresh registry by rediscovering plugins.

        Scans both verified and community plugin directories for new plugins
        and updates the registry accordingly.
        """
        verified = self._discover_verified_plugins()
        community = self._discover_community_plugins()

        # Merge with existing entries, preserving enabled state
        existing_by_name = {e.name: e for e in self._entries}

        new_entries: list[RegistryEntry] = []

        for entry in verified + community:
            if entry.name in existing_by_name:
                # Preserve enabled state from existing entry
                existing = existing_by_name[entry.name]
                entry = RegistryEntry(
                    name=entry.name,
                    path=entry.path,
                    version=entry.version,
                    verified=entry.verified,
                    enabled=existing.enabled,
                )
            new_entries.append(entry)

        self._entries = new_entries
        self.save()

    def save(self) -> None:
        """Save registry to YAML file."""
        # Ensure parent directory exists
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "methodologies": [
                {
                    "name": e.name,
                    "path": e.path,
                    "version": e.version,
                    "verified": e.verified,
                    "enabled": e.enabled,
                }
                for e in self._entries
            ]
        }

        self._registry_path.write_text(
            yaml.dump(data, default_flow_style=False, sort_keys=False)
        )

    def list_installed(self) -> list[MethodologyInfo]:
        """List all installed methodology plugins.

        Returns:
            List of MethodologyInfo objects for installed methodologies
        """
        self._ensure_loaded()
        return [_entry_to_info(entry) for entry in self._entries]

    def list_entries(self) -> list[RegistryEntry]:
        """List all registry entries (internal use).

        Returns:
            List of RegistryEntry objects for installed methodologies
        """
        self._ensure_loaded()
        return list(self._entries)

    def get_entry(self, name: str) -> RegistryEntry | None:
        """Get a registry entry by name.

        Args:
            name: Name of the methodology

        Returns:
            RegistryEntry if found, None otherwise
        """
        self._ensure_loaded()
        for entry in self._entries:
            if entry.name == name:
                return entry
        return None

    def get_methodology(self, name: str) -> MethodologyRunner:
        """Get a methodology runner by name.

        This method loads the methodology plugin and returns its runner instance.

        Args:
            name: Name of the methodology to retrieve

        Returns:
            MethodologyRunner instance for the methodology

        Raises:
            PluginLoadError: If methodology is not installed or fails to load
        """
        self._ensure_loaded()

        entry = self.get_entry(name)
        if entry is None:
            raise PluginLoadError(f"Methodology '{name}' is not installed")

        # Note: Actual plugin loading will be implemented in Story 1.4
        # For now, raise an error indicating the plugin cannot be loaded
        raise PluginLoadError(
            f"Plugin loading not yet implemented. Methodology '{name}' found at {entry.path}"
        )

    def install(self, path: str) -> None:
        """Install a methodology plugin from a path.

        Args:
            path: Path to the methodology plugin directory

        Raises:
            ManifestValidationError: If manifest.yaml is invalid
            PluginLoadError: If plugin cannot be loaded
        """
        self._ensure_loaded()

        plugin_path = Path(path).expanduser().resolve()
        manifest_path = plugin_path / "manifest.yaml"

        if not manifest_path.exists():
            raise PluginLoadError(f"No manifest.yaml found at {plugin_path}")

        try:
            manifest_data = yaml.safe_load(manifest_path.read_text())
        except Exception as e:
            raise PluginLoadError(f"Failed to parse manifest.yaml: {e}")

        if not manifest_data or "name" not in manifest_data:
            raise PluginLoadError("Invalid manifest.yaml: missing 'name' field")

        name = manifest_data["name"]

        # Check if already installed
        if self.get_entry(name) is not None:
            raise PluginLoadError(f"Methodology '{name}' is already installed")

        entry = RegistryEntry(
            name=name,
            path=str(plugin_path),
            version=manifest_data.get("version", "0.0.0"),
            verified=False,  # Installed plugins are not verified
            enabled=True,
        )

        self._entries.append(entry)
        self.save()

    def uninstall(self, name: str) -> None:
        """Uninstall a methodology plugin.

        Args:
            name: Name of the methodology to uninstall

        Raises:
            PluginLoadError: If methodology is not installed
        """
        self._ensure_loaded()

        entry = self.get_entry(name)
        if entry is None:
            raise PluginLoadError(f"Methodology '{name}' is not installed")

        if entry.verified:
            raise PluginLoadError(f"Cannot uninstall verified methodology '{name}'")

        self._entries = [e for e in self._entries if e.name != name]
        self.save()

    def is_enabled(self, name: str) -> bool:
        """Check if a methodology is enabled.

        Args:
            name: Name of the methodology

        Returns:
            True if enabled, False if disabled or not installed
        """
        self._ensure_loaded()

        entry = self.get_entry(name)
        if entry is None:
            return False
        return entry.enabled

    def add_entry(self, entry: RegistryEntry) -> None:
        """Add an entry to the registry.

        Args:
            entry: RegistryEntry to add
        """
        self._ensure_loaded()

        # Remove existing entry with same name if present
        self._entries = [e for e in self._entries if e.name != entry.name]
        self._entries.append(entry)
