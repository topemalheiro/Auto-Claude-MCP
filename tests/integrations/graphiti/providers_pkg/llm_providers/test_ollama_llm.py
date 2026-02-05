"""Tests for ollama_llm"""

from unittest.mock import MagicMock, patch

import pytest

from integrations.graphiti.providers_pkg.llm_providers.ollama_llm import (
    create_ollama_llm_client,
)
from integrations.graphiti.providers_pkg.exceptions import ProviderNotInstalled


def test_create_ollama_llm_client():
    """Test create_ollama_llm_client"""

    # Arrange
    config = MagicMock()
    config.ollama_llm_model = "llama3.1"
    config.ollama_base_url = "http://localhost:11434"

    # Act & Assert
    # The function requires graphiti-core which may not be installed
    with pytest.raises(ProviderNotInstalled) as exc_info:
        create_ollama_llm_client(config)
    assert "graphiti-core" in str(exc_info.value)
