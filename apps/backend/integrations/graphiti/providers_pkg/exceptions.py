"""
Graphiti Provider Exceptions
=============================

Exception classes for provider-related errors.
"""


class ProviderError(Exception):
    """Raised when a provider cannot be initialized."""

    pass  # no-op


class ProviderNotInstalled(ProviderError):
    """Raised when required packages for a provider are not installed."""

    pass  # no-op
