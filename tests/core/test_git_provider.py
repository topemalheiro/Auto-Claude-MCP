"""Tests for git_provider"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.git_provider import _classify_hostname, detect_git_provider


class TestClassifyHostname:
    """Tests for _classify_hostname function"""

    def test_classify_github_dot_com(self):
        """Test classifying github.com"""
        # Act
        result = _classify_hostname("github.com")

        # Assert
        assert result == "github"

    def test_classify_subdomain_github_com(self):
        """Test classifying subdomain of github.com"""
        # Act
        result = _classify_hostname("enterprise.github.com")

        # Assert
        assert result == "github"

    def test_classify_github_in_hostname(self):
        """Test classifying hostname with 'github' in segment"""
        # Act
        result = _classify_hostname("github.example.com")

        # Assert
        assert result == "github"

    def test_classify_github_dash_prefix(self):
        """Test classifying hostname with 'github-' prefix"""
        # Act
        result = _classify_hostname("github-server.example.com")

        # Assert
        assert result == "github"

    def test_classify_gitlab_dot_com(self):
        """Test classifying gitlab.com"""
        # Act
        result = _classify_hostname("gitlab.com")

        # Assert
        assert result == "gitlab"

    def test_classify_subdomain_gitlab_com(self):
        """Test classifying subdomain of gitlab.com"""
        # Act
        result = _classify_hostname("enterprise.gitlab.com")

        # Assert
        assert result == "gitlab"

    def test_classify_gitlab_in_hostname(self):
        """Test classifying hostname with 'gitlab' in segment"""
        # Act
        result = _classify_hostname("gitlab.example.com")

        # Assert
        assert result == "gitlab"

    def test_classify_gitlab_dash_prefix(self):
        """Test classifying hostname with 'gitlab-' prefix"""
        # Act
        result = _classify_hostname("gitlab-server.example.com")

        # Assert
        assert result == "gitlab"

    def test_classify_unknown_provider(self):
        """Test classifying unknown provider"""
        # Act
        result = _classify_hostname("bitbucket.org")

        # Assert
        assert result == "unknown"

    def test_classify_case_insensitive(self):
        """Test hostname classification is case insensitive"""
        # Act
        result1 = _classify_hostname("GitHub.Com")
        result2 = _classify_hostname("GITLAB.COM")

        # Assert
        assert result1 == "github"
        assert result2 == "gitlab"


class TestDetectGitProvider:
    """Tests for detect_git_provider function"""

    def test_detect_github_ssh_url(self):
        """Test detecting GitHub from SSH URL"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "git@github.com:user/repo.git"

        with patch("core.git_provider.run_git", return_value=mock_result):
            # Act
            result = detect_git_provider("/path/to/repo")

            # Assert
            assert result == "github"

    def test_detect_github_https_url(self):
        """Test detecting GitHub from HTTPS URL"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.com/user/repo.git"

        with patch("core.git_provider.run_git", return_value=mock_result):
            # Act
            result = detect_git_provider("/path/to/repo")

            # Assert
            assert result == "github"

    def test_detect_github_ssh_protocol_url(self):
        """Test detecting GitHub from ssh:// protocol URL"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ssh://git@github.com/user/repo.git"

        with patch("core.git_provider.run_git", return_value=mock_result):
            # Act
            result = detect_git_provider("/path/to/repo")

            # Assert
            assert result == "github"

    def test_detect_gitlab_ssh_url(self):
        """Test detecting GitLab from SSH URL"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "git@gitlab.com:user/repo.git"

        with patch("core.git_provider.run_git", return_value=mock_result):
            # Act
            result = detect_git_provider("/path/to/repo")

            # Assert
            assert result == "gitlab"

    def test_detect_gitlab_https_url(self):
        """Test detecting GitLab from HTTPS URL"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://gitlab.com/user/repo.git"

        with patch("core.git_provider.run_git", return_value=mock_result):
            # Act
            result = detect_git_provider("/path/to/repo")

            # Assert
            assert result == "gitlab"

    def test_detect_gitlab_self_hosted(self):
        """Test detecting self-hosted GitLab instance"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://gitlab.company.com/user/repo.git"

        with patch("core.git_provider.run_git", return_value=mock_result):
            # Act
            result = detect_git_provider("/path/to/repo")

            # Assert
            assert result == "gitlab"

    def test_detect_gitlab_self_hosted_ssh(self):
        """Test detecting self-hosted GitLab via SSH"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "git@gitlab.example.com:user/repo.git"

        with patch("core.git_provider.run_git", return_value=mock_result):
            # Act
            result = detect_git_provider("/path/to/repo")

            # Assert
            assert result == "gitlab"

    def test_detect_gitlab_ssh_protocol_url(self):
        """Test detecting GitLab from ssh:// protocol URL"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ssh://git@gitlab.com/user/repo.git"

        with patch("core.git_provider.run_git", return_value=mock_result):
            # Act
            result = detect_git_provider("/path/to/repo")

            # Assert
            assert result == "gitlab"

    def test_detect_github_self_hosted(self):
        """Test detecting self-hosted GitHub instance"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.company.com/user/repo.git"

        with patch("core.git_provider.run_git", return_value=mock_result):
            # Act
            result = detect_git_provider("/path/to/repo")

            # Assert
            assert result == "github"

    def test_detect_github_enterprise_subdomain(self):
        """Test detecting GitHub Enterprise subdomain"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://enterprise.github.com/user/repo.git"

        with patch("core.git_provider.run_git", return_value=mock_result):
            # Act
            result = detect_git_provider("/path/to/repo")

            # Assert
            assert result == "github"

    def test_detect_unknown_provider_bitbucket(self):
        """Test detecting unknown provider (Bitbucket)"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://bitbucket.org/user/repo.git"

        with patch("core.git_provider.run_git", return_value=mock_result):
            # Act
            result = detect_git_provider("/path/to/repo")

            # Assert
            assert result == "unknown"

    def test_detect_no_remote(self):
        """Test when no remote is configured"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch("core.git_provider.run_git", return_value=mock_result):
            # Act
            result = detect_git_provider("/path/to/repo")

            # Assert
            assert result == "unknown"

    def test_detect_empty_remote_output(self):
        """Test when remote command returns empty output"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("core.git_provider.run_git", return_value=mock_result):
            # Act
            result = detect_git_provider("/path/to/repo")

            # Assert
            assert result == "unknown"

    def test_detect_custom_remote_name(self):
        """Test detecting provider with custom remote name"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "git@github.com:user/repo.git"

        with patch("core.git_provider.run_git", return_value=mock_result) as mock_run:
            # Act
            result = detect_git_provider("/path/to/repo", remote_name="upstream")

            # Assert
            assert result == "github"
            # Verify custom remote name was used
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert "upstream" in call_args

    def test_detect_with_pathlib_path(self):
        """Test detect_git_provider accepts pathlib.Path"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "git@github.com:user/repo.git"

        with patch("core.git_provider.run_git", return_value=mock_result) as mock_run:
            # Act
            result = detect_git_provider(Path("/path/to/repo"))

            # Assert
            assert result == "github"
            # Verify path was handled correctly
            mock_run.assert_called_once()

    def test_detect_windows_drive_path_not_confused(self):
        """Test Windows drive paths are not confused with SCP-like URLs"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("core.git_provider.run_git", return_value=mock_result):
            # Act
            result = detect_git_provider("/path/to/repo")

            # Assert
            assert result == "unknown"

    def test_detect_http_url(self):
        """Test detecting provider from HTTP URL (not HTTPS)"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "http://github.com/user/repo.git"

        with patch("core.git_provider.run_git", return_value=mock_result):
            # Act
            result = detect_git_provider("/path/to/repo")

            # Assert
            assert result == "github"

    def test_detect_scp_url_with_port(self):
        """Test detecting provider from SCP URL with port"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ssh://git@github.com:2222/user/repo.git"

        with patch("core.git_provider.run_git", return_value=mock_result):
            # Act
            result = detect_git_provider("/path/to/repo")

            # Assert
            assert result == "github"

    def test_detect_exception_handling(self):
        """Test exception handling returns unknown"""
        # Arrange
        with patch("core.git_provider.run_git", side_effect=Exception("Test error")):
            # Act
            result = detect_git_provider("/path/to/repo")

            # Assert
            assert result == "unknown"

    def test_detect_scp_with_different_username(self):
        """Test SCP URL with non-git username"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "user@github.com:user/repo.git"

        with patch("core.git_provider.run_git", return_value=mock_result):
            # Act
            result = detect_git_provider("/path/to/repo")

            # Assert
            assert result == "github"

    def test_detect_unrecognized_url_format(self):
        """Test unrecognized URL format returns unknown"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "weird-format-url"

        with patch("core.git_provider.run_git", return_value=mock_result):
            # Act
            result = detect_git_provider("/path/to/repo")

            # Assert
            assert result == "unknown"

    def test_detect_github_enterprise_with_dash(self):
        """Test GitHub Enterprise with 'github-' in hostname"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github-server.company.com/user/repo.git"

        with patch("core.git_provider.run_git", return_value=mock_result):
            # Act
            result = detect_git_provider("/path/to/repo")

            # Assert
            assert result == "github"

    def test_detect_gitlab_enterprise_with_dash(self):
        """Test GitLab Enterprise with 'gitlab-' in hostname"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://gitlab-server.company.com/user/repo.git"

        with patch("core.git_provider.run_git", return_value=mock_result):
            # Act
            result = detect_git_provider("/path/to/repo")

            # Assert
            assert result == "gitlab"

    def test_detect_trailing_whitespace(self):
        """Test URL with trailing whitespace is handled"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "git@github.com:user/repo.git\n"

        with patch("core.git_provider.run_git", return_value=mock_result):
            # Act
            result = detect_git_provider("/path/to/repo")

            # Assert
            assert result == "github"
