"""Methodology plugin source handlers for multiple distribution types.

This module defines the source types and verification statuses for methodology plugins,
enabling a flexible multi-source plugin distribution system.

Plugin Classification:
- Native: The built-in AutoClaude methodology (not a plugin, always available)
- Verified: Plugins maintained and tested by Auto Claude team
- Community: Third-party/user-created plugins without verification guarantee

Distribution Sources:
- NATIVE: Built-in, no installation required
- NPM: npm/pnpm/yarn packages
- GITHUB: GitHub releases or repositories
- LOCAL: Manual installation to plugins directory

Architecture Source: This implements the methodology plugin system design
with project-level settings and multi-source versioning.
"""

from dataclasses import dataclass
from enum import Enum


class SourceType(Enum):
    """Distribution source types for methodology plugins."""

    NATIVE = "native"  # The built-in AutoClaude methodology (not a plugin)
    NPM = "npm"  # npm/pnpm/yarn packages
    GITHUB = "github"  # GitHub releases or repos
    LOCAL = "local"  # Manual copy to plugins directory


class VerificationStatus(Enum):
    """Verification status for methodology plugins."""

    NATIVE = "native"  # The AutoClaude methodology itself
    VERIFIED = "verified"  # Maintained and tested by Auto Claude team
    COMMUNITY = "community"  # Third-party, no verification


@dataclass
class MethodologySource:
    """Configuration for a methodology's distribution source.

    Attributes:
        type: Distribution source type (native, npm, github, local)
        verification: Verification status (native, verified, community)
        package_name: Package identifier (NPM: package name, GitHub: owner/repo)
        install_command: Override default install command (optional)
        version_command: Command to check installed version (optional)
        min_version: Minimum supported version for verified plugins
        max_version: Maximum supported version (exclusive, optional)
    """

    type: SourceType
    verification: VerificationStatus
    package_name: str | None = None
    install_command: str | None = None
    version_command: str | None = None
    min_version: str = "1.0.0"
    max_version: str | None = None


# Registry of known methodologies and their sources
# Verified plugins are maintained by Auto Claude and tested for compatibility
METHODOLOGY_SOURCES: dict[str, MethodologySource] = {
    "native": MethodologySource(
        type=SourceType.NATIVE,
        verification=VerificationStatus.NATIVE,
    ),
    "bmad": MethodologySource(
        type=SourceType.NPM,
        verification=VerificationStatus.VERIFIED,
        package_name="bmad-method",
        install_command="npx bmad-method@alpha install",
        version_command="npx bmad-method@alpha --version",
        min_version="1.0.0",
    ),
}


def get_methodology_source(name: str) -> MethodologySource | None:
    """Get the source configuration for a methodology.

    Args:
        name: Name of the methodology (e.g., 'native', 'bmad')

    Returns:
        MethodologySource if found, None otherwise
    """
    return METHODOLOGY_SOURCES.get(name)


def is_verified_methodology(name: str) -> bool:
    """Check if a methodology is verified (maintained by Auto Claude team).

    Args:
        name: Name of the methodology

    Returns:
        True if methodology is verified or native, False otherwise
    """
    source = get_methodology_source(name)
    if source is None:
        return False
    return source.verification in (VerificationStatus.NATIVE, VerificationStatus.VERIFIED)


def is_native_methodology(name: str) -> bool:
    """Check if a methodology is the native (built-in) methodology.

    Args:
        name: Name of the methodology

    Returns:
        True if methodology is native, False otherwise
    """
    source = get_methodology_source(name)
    if source is None:
        return False
    return source.verification == VerificationStatus.NATIVE


def get_install_command(name: str) -> str | None:
    """Get the install command for a methodology.

    Args:
        name: Name of the methodology

    Returns:
        Install command string if available, None for native or unknown
    """
    source = get_methodology_source(name)
    if source is None or source.type == SourceType.NATIVE:
        return None
    return source.install_command


def get_version_command(name: str) -> str | None:
    """Get the version check command for a methodology.

    Args:
        name: Name of the methodology

    Returns:
        Version command string if available, None for native or unknown
    """
    source = get_methodology_source(name)
    if source is None or source.type == SourceType.NATIVE:
        return None
    return source.version_command


def list_available_methodologies() -> list[dict]:
    """List all registered methodologies with their source info.

    Returns:
        List of dictionaries with methodology source information
    """
    return [
        {
            "name": name,
            "type": source.type.value,
            "verification": source.verification.value,
            "package_name": source.package_name,
            "min_version": source.min_version,
            "max_version": source.max_version,
        }
        for name, source in METHODOLOGY_SOURCES.items()
    ]
