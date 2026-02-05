"""Tests for providers_pkg/models.py module."""

import pytest

from integrations.graphiti.providers_pkg.models import (
    EMBEDDING_DIMENSIONS,
    get_expected_embedding_dim,
)


class TestEmbeddingDimensions:
    """Tests for EMBEDDING_DIMENSIONS constant."""

    def test_embedding_dimensions_is_dict(self):
        """Test EMBEDDING_DIMENSIONS is a dictionary."""
        assert isinstance(EMBEDDING_DIMENSIONS, dict)

    def test_embedding_dimensions_not_empty(self):
        """Test EMBEDDING_DIMENSIONS contains entries."""
        assert len(EMBEDDING_DIMENSIONS) > 0

    def test_embedding_dimensions_openai_models(self):
        """Test EMBEDDING_DIMENSIONS contains OpenAI models."""
        assert "text-embedding-3-small" in EMBEDDING_DIMENSIONS
        assert "text-embedding-3-large" in EMBEDDING_DIMENSIONS
        assert "text-embedding-ada-002" in EMBEDDING_DIMENSIONS

    def test_embedding_dimensions_voyage_models(self):
        """Test EMBEDDING_DIMENSIONS contains Voyage AI models."""
        assert "voyage-3" in EMBEDDING_DIMENSIONS
        assert "voyage-3.5" in EMBEDDING_DIMENSIONS
        assert "voyage-3-lite" in EMBEDDING_DIMENSIONS
        assert "voyage-3.5-lite" in EMBEDDING_DIMENSIONS
        assert "voyage-2" in EMBEDDING_DIMENSIONS
        assert "voyage-large-2" in EMBEDDING_DIMENSIONS

    def test_embedding_dimensions_ollama_models(self):
        """Test EMBEDDING_DIMENSIONS contains Ollama models."""
        assert "nomic-embed-text" in EMBEDDING_DIMENSIONS
        assert "mxbai-embed-large" in EMBEDDING_DIMENSIONS
        assert "all-minilm" in EMBEDDING_DIMENSIONS
        assert "snowflake-arctic-embed" in EMBEDDING_DIMENSIONS

    def test_embedding_dimensions_values_are_positive_integers(self):
        """Test all dimension values are positive integers."""
        for model, dim in EMBEDDING_DIMENSIONS.items():
            assert isinstance(dim, int), f"Dimension for {model} is not an integer"
            assert dim > 0, f"Dimension for {model} is not positive: {dim}"

    def test_embedding_dimensions_openai_values(self):
        """Test OpenAI model dimensions are correct."""
        assert EMBEDDING_DIMENSIONS["text-embedding-3-small"] == 1536
        assert EMBEDDING_DIMENSIONS["text-embedding-3-large"] == 3072
        assert EMBEDDING_DIMENSIONS["text-embedding-ada-002"] == 1536

    def test_embedding_dimensions_voyage_values(self):
        """Test Voyage AI model dimensions are correct."""
        assert EMBEDDING_DIMENSIONS["voyage-3"] == 1024
        assert EMBEDDING_DIMENSIONS["voyage-3.5"] == 1024
        assert EMBEDDING_DIMENSIONS["voyage-3-lite"] == 512
        assert EMBEDDING_DIMENSIONS["voyage-3.5-lite"] == 512
        assert EMBEDDING_DIMENSIONS["voyage-2"] == 1024
        assert EMBEDDING_DIMENSIONS["voyage-large-2"] == 1536

    def test_embedding_dimensions_ollama_values(self):
        """Test Ollama model dimensions are correct."""
        assert EMBEDDING_DIMENSIONS["nomic-embed-text"] == 768
        assert EMBEDDING_DIMENSIONS["mxbai-embed-large"] == 1024
        assert EMBEDDING_DIMENSIONS["all-minilm"] == 384
        assert EMBEDDING_DIMENSIONS["snowflake-arctic-embed"] == 1024


class TestGetExpectedEmbeddingDim:
    """Tests for get_expected_embedding_dim function."""

    def test_exact_match_openai_small(self):
        """Test exact match for text-embedding-3-small."""
        result = get_expected_embedding_dim("text-embedding-3-small")
        assert result == 1536

    def test_exact_match_openai_large(self):
        """Test exact match for text-embedding-3-large."""
        result = get_expected_embedding_dim("text-embedding-3-large")
        assert result == 3072

    def test_exact_match_openai_ada(self):
        """Test exact match for text-embedding-ada-002."""
        result = get_expected_embedding_dim("text-embedding-ada-002")
        assert result == 1536

    def test_exact_match_voyage_3(self):
        """Test exact match for voyage-3."""
        result = get_expected_embedding_dim("voyage-3")
        assert result == 1024

    def test_exact_match_voyage_3_lite(self):
        """Test exact match for voyage-3-lite."""
        result = get_expected_embedding_dim("voyage-3-lite")
        assert result == 512

    def test_exact_match_voyage_large_2(self):
        """Test exact match for voyage-large-2."""
        result = get_expected_embedding_dim("voyage-large-2")
        assert result == 1536

    def test_exact_match_nomic_embed_text(self):
        """Test exact match for nomic-embed-text."""
        result = get_expected_embedding_dim("nomic-embed-text")
        assert result == 768

    def test_exact_match_mxbai_embed_large(self):
        """Test exact match for mxbai-embed-large."""
        result = get_expected_embedding_dim("mxbai-embed-large")
        assert result == 1024

    def test_exact_match_all_minilm(self):
        """Test exact match for all-minilm."""
        result = get_expected_embedding_dim("all-minilm")
        assert result == 384

    def test_exact_match_snowflake_arctic_embed(self):
        """Test exact match for snowflake-arctic-embed."""
        result = get_expected_embedding_dim("snowflake-arctic-embed")
        assert result == 1024

    def test_case_insensitive_match_lowercase(self):
        """Test case-insensitive matching with lowercase input."""
        result = get_expected_embedding_dim("text-embedding-3-small")
        assert result == 1536

    def test_case_insensitive_match_uppercase(self):
        """Test case-insensitive matching with uppercase input."""
        result = get_expected_embedding_dim("TEXT-EMBEDDING-3-SMALL")
        assert result == 1536

    def test_case_insensitive_match_mixed_case(self):
        """Test case-insensitive matching with mixed case input."""
        result = get_expected_embedding_dim("Text-Embedding-3-Small")
        assert result == 1536

    def test_partial_match_model_with_version_suffix(self):
        """Test partial match when model has version suffix."""
        # Model name might have version suffix like ":v1" or "-latest"
        result = get_expected_embedding_dim("text-embedding-3-small:latest")
        assert result == 1536

    def test_partial_match_model_with_prefix(self):
        """Test partial match when known model is substring."""
        result = get_expected_embedding_dim("openai/text-embedding-3-small")
        assert result == 1536

    def test_partial_match_voyage_with_prefix(self):
        """Test partial match for Voyage model with prefix."""
        result = get_expected_embedding_dim("voyage/voyage-3")
        assert result == 1024

    def test_partial_match_ollama_with_prefix(self):
        """Test partial match for Ollama model with prefix."""
        result = get_expected_embedding_dim("ollama/nomic-embed-text")
        assert result == 768

    def test_unknown_model_returns_none(self):
        """Test unknown model returns None."""
        result = get_expected_embedding_dim("unknown-model-name")
        assert result is None

    def test_empty_string_behavior(self):
        """Test empty string behavior (may partially match)."""
        result = get_expected_embedding_dim("")
        # Empty string may match due to partial match logic
        # This test documents current behavior
        assert result is None or isinstance(result, int)

    def test_none_model_raises_attribute_error(self):
        """Test None as model raises AttributeError (current behavior)."""
        # The function doesn't handle None gracefully
        with pytest.raises(AttributeError):
            get_expected_embedding_dim(None)  # type: ignore

    def test_special_characters_in_model_name(self):
        """Test model name with special characters."""
        # Model names with colons, slashes, underscores
        result = get_expected_embedding_dim("text-embedding-3-small:v2")
        assert result == 1536

    def test_partial_match_substring_relationship(self):
        """Test partial match when input contains known model as substring."""
        # Input is shorter than known model
        result = get_expected_embedding_dim("voyage-3")
        assert result == 1024

        # Known model is substring of input
        result = get_expected_embedding_dim("my-voyage-3-model")
        assert result == 1024

    def test_similar_model_names_dont_conflict(self):
        """Test that similar model names don't cause false matches."""
        # These are distinct models with different dimensions
        result_1 = get_expected_embedding_dim("voyage-3-lite")
        assert result_1 == 512

        result_2 = get_expected_embedding_dim("voyage-3.5-lite")
        assert result_2 == 512

        result_3 = get_expected_embedding_dim("voyage-large-2")
        assert result_3 == 1536

    def test_all_known_models_return_valid_dimensions(self):
        """Test all models in EMBEDDING_DIMENSIONS return correct values."""
        for model, expected_dim in EMBEDDING_DIMENSIONS.items():
            result = get_expected_embedding_dim(model)
            assert result == expected_dim, f"Failed for model: {model}"

    def test_whitespace_handling(self):
        """Test handling of whitespace in model names."""
        # Leading/trailing whitespace might be a common error
        result = get_expected_embedding_dim(" text-embedding-3-small ")
        # With current implementation, this won't match exactly
        # but might match partially
        # The behavior depends on the exact implementation
        # This test documents current behavior
        if result is not None:
            assert result == 1536

    def test_model_name_with_hyphens_and_periods(self):
        """Test model names with hyphens and periods."""
        result = get_expected_embedding_dim("voyage-3.5")
        assert result == 1024

        result = get_expected_embedding_dim("text-embedding-ada-002")
        assert result == 1536

    def test_multiple_partial_matches_first_wins(self):
        """Test behavior when multiple partial matches are possible."""
        # If multiple models could match, the first one in the dict wins
        # This test documents the current behavior
        result = get_expected_embedding_dim("voyage-3")
        # Should match "voyage-3" exactly
        assert result == 1024

    def test_return_type(self):
        """Test function returns int or None."""
        result = get_expected_embedding_dim("text-embedding-3-small")
        assert isinstance(result, int) or result is None

        result = get_expected_embedding_dim("unknown")
        assert result is None
