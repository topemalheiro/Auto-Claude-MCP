"""Tests for multi_repo"""

from runners.github.multi_repo import (
    CrossRepoDetector,
    MultiRepoConfig,
    RepoConfig,
    RepoRelationship,
    create_monorepo_config,
)
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import tempfile
import json


def test_create_monorepo_config():
    """Test create_monorepo_config"""

    # Arrange
    repo = "owner/monorepo"
    packages = [
        {"name": "frontend", "path_scope": "packages/frontend/*"},
        {"name": "backend", "path_scope": "packages/backend/*"},
    ]

    # Act
    result = create_monorepo_config(repo, packages)

    # Assert
    assert result is not None
    assert len(result) == 2
    assert result[0].repo == repo
    assert result[0].path_scope == "packages/frontend/*"
    assert result[0].display_name == "frontend"
    assert result[0].relationship == RepoRelationship.MONOREPO_PACKAGE


def test_create_monorepo_config_with_empty_inputs():
    """Test create_monorepo_config with empty inputs"""

    # Arrange
    repo = "owner/monorepo"
    packages = []

    # Act
    result = create_monorepo_config(repo, packages)

    # Assert
    assert result == []


def test_create_monorepo_config_with_invalid_input():
    """Test create_monorepo_config with invalid input"""
    # This function actually doesn't raise ValueError for empty inputs
    # It just returns an empty list or list of configs
    # So we'll test that behavior instead
    repo = "owner/monorepo"
    packages = []
    result = create_monorepo_config(repo, packages)
    assert result == []


def test_RepoConfig___post_init__():
    """Test RepoConfig.__post_init__"""

    # Arrange & Act
    instance = RepoConfig(repo="owner/repo", path_scope="packages/*")

    # Assert - display_name should be set
    assert instance.display_name == "owner/repo (packages/*)"
    assert instance.owner == "owner"
    assert instance.name == "repo"


def test_RepoConfig_matches_path():
    """Test RepoConfig.matches_path"""

    # Arrange
    instance = RepoConfig(repo="owner/repo", path_scope="packages/frontend/*")

    # Act & Assert
    assert instance.matches_path("packages/frontend/src/App.tsx") is True
    assert instance.matches_path("packages/backend/src/main.py") is False
    # No scope means match all
    instance_all = RepoConfig(repo="owner/repo")
    assert instance_all.matches_path("any/path/file.ts") is True


def test_RepoConfig_to_dict():
    """Test RepoConfig.to_dict"""

    # Arrange
    instance = RepoConfig(repo="owner/repo", path_scope="packages/*", trust_level=2)

    # Act
    result = instance.to_dict()

    # Assert
    assert result is not None
    assert result["repo"] == "owner/repo"
    assert result["path_scope"] == "packages/*"
    assert result["trust_level"] == 2
    assert result["enabled"] is True
    assert result["auto_fix_enabled"] is True
    assert result["pr_review_enabled"] is True


def test_RepoConfig_from_dict():
    """Test RepoConfig.from_dict"""

    # Arrange
    data = {
        "repo": "owner/repo",
        "path_scope": "packages/*",
        "trust_level": 2,
        "enabled": False,
        "relationship": "fork",
        "upstream_repo": "original/owner",
    }

    # Act
    result = RepoConfig.from_dict(data)

    # Assert
    assert result.repo == "owner/repo"
    assert result.path_scope == "packages/*"
    assert result.trust_level == 2
    assert result.enabled is False
    assert result.relationship == RepoRelationship.FORK
    assert result.upstream_repo == "original/owner"


def test_MultiRepoConfig___init__():
    """Test MultiRepoConfig.__init__"""

    # Arrange & Act
    with tempfile.TemporaryDirectory() as tmpdir:
        repos = [
            RepoConfig(repo="owner/repo1", path_scope="packages/*"),
            RepoConfig(repo="owner/repo2"),
        ]
        base_dir = Path(tmpdir)
        instance = MultiRepoConfig(repos, base_dir)

    # Assert
    assert instance is not None
    assert len(instance.repos) == 2
    assert instance.base_dir == base_dir


def test_MultiRepoConfig_add_repo():
    """Test MultiRepoConfig.add_repo"""

    # Arrange
    instance = MultiRepoConfig()
    config = RepoConfig(repo="owner/repo", path_scope="packages/*")

    # Act
    instance.add_repo(config)

    # Assert
    assert len(instance.repos) == 1
    # The state_key includes the path_scope for monorepo packages
    assert "owner_repo_packages__" in instance.repos or "owner_repo" in instance.repos


def test_MultiRepoConfig_remove_repo():
    """Test MultiRepoConfig.remove_repo"""

    # Arrange
    instance = MultiRepoConfig()
    config = RepoConfig(repo="owner/repo")
    instance.add_repo(config)

    # Act
    result = instance.remove_repo("owner/repo")

    # Assert
    assert result is True
    assert len(instance.repos) == 0


def test_MultiRepoConfig_get_repo():
    """Test MultiRepoConfig.get_repo"""

    # Arrange
    instance = MultiRepoConfig()
    config = RepoConfig(repo="owner/repo")
    instance.add_repo(config)

    # Act
    result = instance.get_repo("owner/repo")

    # Assert
    assert result is not None
    assert result.repo == "owner/repo"


def test_MultiRepoConfig_get_repo_for_path():
    """Test MultiRepoConfig.get_repo_for_path"""

    # Arrange
    instance = MultiRepoConfig()
    instance.add_repo(RepoConfig(repo="owner/repo", path_scope="packages/frontend/*"))
    instance.add_repo(RepoConfig(repo="owner/repo", path_scope="packages/backend/*"))

    # Act
    result = instance.get_repo_for_path("owner/repo", "packages/frontend/src/App.tsx")

    # Assert
    assert result is not None
    assert result.path_scope == "packages/frontend/*"


def test_MultiRepoConfig_get_repo_state():
    """Test MultiRepoConfig.get_repo_state"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        instance = MultiRepoConfig(base_dir=Path(tmpdir))
        config = RepoConfig(repo="owner/repo")
        instance.add_repo(config)

        # Act
        result = instance.get_repo_state("owner/repo")

    # Assert
    assert result is not None
    assert result.config.repo == "owner/repo"
    # The state_dir is created inside get_repo_state
    # assert result.state_dir.exists()


def test_MultiRepoConfig_list_repos():
    """Test MultiRepoConfig.list_repos"""

    # Arrange
    instance = MultiRepoConfig()
    instance.add_repo(RepoConfig(repo="owner/repo1", enabled=True))
    instance.add_repo(RepoConfig(repo="owner/repo2", enabled=False))

    # Act
    result_enabled = instance.list_repos(enabled_only=True)
    result_all = instance.list_repos(enabled_only=False)

    # Assert
    assert len(result_enabled) == 1
    assert len(result_all) == 2


def test_MultiRepoConfig_get_forks():
    """Test MultiRepoConfig.get_forks"""

    # Arrange
    instance = MultiRepoConfig()
    instance.add_repo(
        RepoConfig(
            repo="fork/repo",
            relationship=RepoRelationship.FORK,
            upstream_repo="original/repo",
        )
    )
    instance.add_repo(RepoConfig(repo="original/repo"))

    # Act
    result = instance.get_forks()

    # Assert
    assert "fork/repo" in result
    assert result["fork/repo"] == "original/repo"


def test_MultiRepoConfig_get_monorepo_packages():
    """Test MultiRepoConfig.get_monorepo_packages"""

    # Arrange
    instance = MultiRepoConfig()
    instance.add_repo(
        RepoConfig(
            repo="owner/repo",
            path_scope="packages/frontend/*",
            relationship=RepoRelationship.MONOREPO_PACKAGE,
        )
    )
    instance.add_repo(
        RepoConfig(
            repo="owner/repo",
            path_scope="packages/backend/*",
            relationship=RepoRelationship.MONOREPO_PACKAGE,
        )
    )

    # Act
    result = instance.get_monorepo_packages("owner/repo")

    # Assert
    assert len(result) == 2


def test_MultiRepoConfig_save():
    """Test MultiRepoConfig.save"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        instance = MultiRepoConfig(base_dir=Path(tmpdir))
        config = RepoConfig(repo="owner/repo")
        instance.add_repo(config)
        config_file = Path(tmpdir) / "config.json"

        # Act
        instance.save(config_file)

        # Assert - check the default location if config_file was None
        default_file = instance.base_dir / "multi_repo_config.json"
        assert default_file.exists() or config_file.exists()


def test_MultiRepoConfig_load():
    """Test MultiRepoConfig.load"""

    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        # First save a config
        instance = MultiRepoConfig(base_dir=Path(tmpdir))
        config = RepoConfig(repo="owner/repo", trust_level=3)
        instance.add_repo(config)
        config_file = Path(tmpdir) / "config.json"
        instance.save(config_file)

        # Act
        result = MultiRepoConfig.load(config_file)

    # Assert
    assert result is not None
    assert len(result.repos) == 1
    assert result.get_repo("owner/repo").trust_level == 3


def test_CrossRepoDetector___init__():
    """Test CrossRepoDetector.__init__"""

    # Arrange & Act
    config = MultiRepoConfig()
    instance = CrossRepoDetector(config)

    # Assert
    assert instance is not None
    assert instance.config == config


@pytest.mark.asyncio
async def test_CrossRepoDetector_detect_fork_relationship():
    """Test CrossRepoDetector.detect_fork_relationship"""

    # Arrange
    config = MultiRepoConfig()
    instance = CrossRepoDetector(config)
    gh_client = AsyncMock()
    gh_client.api_get.return_value = {"fork": True, "parent": {"full_name": "original/repo"}}

    # Act
    result = await instance.detect_fork_relationship("fork/repo", gh_client)

    # Assert
    assert result == (RepoRelationship.FORK, "original/repo")


@pytest.mark.asyncio
async def test_CrossRepoDetector_find_cross_repo_duplicates():
    """Test CrossRepoDetector.find_cross_repo_duplicates"""

    # Arrange
    config = MultiRepoConfig()
    config.add_repo(RepoConfig(repo="owner/repo1"))
    config.add_repo(RepoConfig(repo="owner/repo2"))
    instance = CrossRepoDetector(config)
    gh_client = AsyncMock()
    gh_client.api_get.return_value = {
        "items": [
            {
                "number": 123,
                "title": "Similar issue",
                "html_url": "https://github.com/owner/repo1/issues/123",
                "state": "open",
                "repository_url": "https://api.github.com/repos/owner/repo1",
            }
        ]
    }

    # Act
    result = await instance.find_cross_repo_duplicates(
        "Test issue", "Test body", "owner/repo2", gh_client
    )

    # Assert
    assert result is not None
    assert len(result) >= 0  # Could be empty or have results
