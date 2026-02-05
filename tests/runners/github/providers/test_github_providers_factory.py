"""Tests for factory"""

import pytest
from unittest.mock import MagicMock

from runners.github.providers.factory import (
    get_provider,
    is_provider_available,
    list_available_providers,
    register_provider,
)
from runners.github.providers.protocol import ProviderType


@pytest.fixture
def clear_registry():
    """Clear the provider registry before each test."""
    from runners.github.providers import factory

    original_registry = factory._PROVIDER_REGISTRY.copy()
    factory._PROVIDER_REGISTRY.clear()
    yield
    factory._PROVIDER_REGISTRY.clear()
    factory._PROVIDER_REGISTRY.update(original_registry)


def test_register_provider(clear_registry):
    """Test register_provider"""
    # Arrange
    mock_factory = MagicMock()
    mock_factory.return_value = MagicMock()

    # Act
    register_provider(ProviderType.GITLAB, mock_factory)

    # Assert - provider is now registered
    assert ProviderType.GITLAB in list_available_providers()


def test_register_provider_with_empty_inputs(clear_registry):
    """Test register_provider with None factory"""
    # Arrange & Act & Assert
    # None factory can be registered (it's a callable value)
    # When get_provider is called later with None, it will fail appropriately
    register_provider(ProviderType.GITLAB, None)
    assert ProviderType.GITLAB in list_available_providers()


def test_register_provider_with_invalid_input(clear_registry):
    """Test register_provider with invalid input"""
    # Arrange & Act & Assert
    # Can register None as provider_type since it's just a dict key
    # The factory should handle this appropriately
    register_provider(None, lambda: MagicMock())


def test_get_provider(clear_registry):
    """Test get_provider"""
    # Act
    provider = get_provider("github", "owner/repo")

    # Assert
    assert provider is not None
    assert provider.provider_type == ProviderType.GITHUB
    assert provider.repo == "owner/repo"


def test_get_provider_with_enum(clear_registry):
    """Test get_provider with ProviderType enum"""
    # Act
    provider = get_provider(ProviderType.GITHUB, "owner/repo")

    # Assert
    assert provider is not None
    assert provider.provider_type == ProviderType.GITHUB


def test_get_provider_with_empty_inputs(clear_registry):
    """Test get_provider with empty repo string"""
    # Act & Assert - empty repo is accepted, provider is created
    provider = get_provider("github", "")
    assert provider is not None
    assert provider.repo == ""


def test_get_provider_with_invalid_input():
    """Test get_provider with invalid provider type"""
    # Act & Assert
    with pytest.raises(ValueError, match="Unknown provider type"):
        get_provider("invalid_provider", "owner/repo")


def test_get_provider_not_implemented(clear_registry):
    """Test get_provider for not-yet-implemented providers"""
    # Act & Assert - GitLab is registered but not implemented
    with pytest.raises(NotImplementedError, match="GitLab provider not yet implemented"):
        get_provider(ProviderType.GITLAB, "owner/repo")


def test_list_available_providers():
    """Test list_available_providers"""
    # Act
    result = list_available_providers()

    # Assert
    assert result is not None
    assert isinstance(result, list)
    assert ProviderType.GITHUB in result


def test_list_available_providers_with_registry(clear_registry):
    """Test list_available_providers with custom registered provider"""
    # Arrange
    register_provider(ProviderType.GITLAB, lambda repo, **kwargs: MagicMock())

    # Act
    result = list_available_providers()

    # Assert
    assert ProviderType.GITHUB in result
    assert ProviderType.GITLAB in result


def test_is_provider_available():
    """Test is_provider_available"""
    # Act & Assert
    assert is_provider_available("github") is True
    assert is_provider_available(ProviderType.GITHUB) is True


def test_is_provider_available_with_string():
    """Test is_provider_available with string input"""
    # Act & Assert
    assert is_provider_available("GITHUB") is True  # Case insensitive
    assert is_provider_available("github") is True


def test_is_provider_available_with_invalid_input():
    """Test is_provider_available with invalid input"""
    # Act & Assert
    assert is_provider_available("invalid_provider") is False
    assert is_provider_available(ProviderType.GITLAB) is False


def test_is_provider_available_with_registry(clear_registry):
    """Test is_provider_available with custom registered provider"""
    # Arrange
    register_provider(ProviderType.GITLAB, lambda repo, **kwargs: MagicMock())

    # Act & Assert
    assert is_provider_available(ProviderType.GITLAB) is True
    assert is_provider_available("gitlab") is True


def test_get_provider_with_custom_registry(clear_registry):
    """Test get_provider with custom registered provider"""
    # Arrange
    mock_provider = MagicMock()
    mock_provider.provider_type = ProviderType.GITLAB
    mock_provider.repo = "test/repo"

    def gitlab_factory(repo: str, **kwargs):
        mock_provider.repo = repo
        return mock_provider

    register_provider(ProviderType.GITLAB, gitlab_factory)

    # Act
    provider = get_provider(ProviderType.GITLAB, "test/repo")

    # Assert
    assert provider is mock_provider
    assert provider.repo == "test/repo"


def test_get_provider_string_to_enum_conversion(clear_registry):
    """Test that get_provider converts strings to ProviderType enum"""
    # Act & Assert - various case formats
    provider1 = get_provider("github", "owner/repo")
    assert provider1.provider_type == ProviderType.GITHUB

    provider2 = get_provider("GITHUB", "owner/repo")
    assert provider2.provider_type == ProviderType.GITHUB

    provider3 = get_provider("Github", "owner/repo")
    assert provider3.provider_type == ProviderType.GITHUB
