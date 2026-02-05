"""Tests for cache_manager"""

from runners.ai_analyzer.cache_manager import CacheManager
from pathlib import Path
import pytest


def test_CacheManager___init__():
    """Test CacheManager.__init__"""
    # Arrange
    cache_dir = Path("/tmp/test_cache")

    # Act
    instance = CacheManager(cache_dir)

    # Assert
    assert instance is not None
    assert instance.cache_dir == cache_dir
    assert instance.cache_file == cache_dir / "ai_insights.json"


def test_CacheManager_get_cached_result_skip_cache():
    """Test CacheManager.get_cached_result with skip_cache=True"""
    # Arrange
    cache_dir = Path("/tmp/test_cache_skip")
    instance = CacheManager(cache_dir)
    skip_cache = True

    # Act
    result = instance.get_cached_result(skip_cache)

    # Assert
    assert result is None


def test_CacheManager_get_cached_result_no_file():
    """Test CacheManager.get_cached_result with no cache file"""
    # Arrange
    cache_dir = Path("/tmp/test_cache_no_file")
    instance = CacheManager(cache_dir)
    skip_cache = False

    # Act
    result = instance.get_cached_result(skip_cache)

    # Assert
    assert result is None


def test_CacheManager_save_and_get_result():
    """Test CacheManager.save_result and get_cached_result"""
    # Arrange
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir)
        instance = CacheManager(cache_dir)
        test_result = {"test": "data", "score": 85}

        # Act - Save result
        instance.save_result(test_result)

        # Assert - File should exist
        assert instance.cache_file.exists()

        # Act - Get cached result
        result = instance.get_cached_result(skip_cache=False)

        # Assert
        assert result is not None
        assert result["test"] == "data"
        assert result["score"] == 85
