"""Tests for security profile management"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from security.profile import (
    _get_profile_path,
    _get_allowlist_path,
    _get_profile_mtime,
    _get_allowlist_mtime,
    get_security_profile,
    reset_profile_cache,
)


class TestHelperFunctions:
    """Tests for helper functions"""

    def test_get_profile_path(self):
        """Test _get_profile_path returns correct path"""
        project_dir = Path("/tmp/test_project")
        profile_path = _get_profile_path(project_dir)
        assert profile_path == project_dir / ".auto-claude-security.json"

    def test_get_allowlist_path(self):
        """Test _get_allowlist_path returns correct path"""
        project_dir = Path("/tmp/test_project")
        allowlist_path = _get_allowlist_path(project_dir)
        assert allowlist_path == project_dir / ".auto-claude-allowlist"

    def test_get_profile_mtime_existing_file(self, tmp_path):
        """Test _get_profile_mtime returns mtime for existing file"""
        # Create the profile file
        profile_file = tmp_path / ".auto-claude-security.json"
        profile_file.write_text("{}")

        mtime = _get_profile_mtime(tmp_path)
        assert mtime is not None
        assert isinstance(mtime, float)

    def test_get_profile_mtime_nonexistent_file(self, tmp_path):
        """Test _get_profile_mtime returns None for non-existent file"""
        mtime = _get_profile_mtime(tmp_path)
        assert mtime is None

    def test_get_allowlist_mtime_existing_file(self, tmp_path):
        """Test _get_allowlist_mtime returns mtime for existing file"""
        # Create the allowlist file
        allowlist_file = tmp_path / ".auto-claude-allowlist"
        allowlist_file.write_text("ls\ncat\n")

        mtime = _get_allowlist_mtime(tmp_path)
        assert mtime is not None
        assert isinstance(mtime, float)

    def test_get_allowlist_mtime_nonexistent_file(self, tmp_path):
        """Test _get_allowlist_mtime returns None for non-existent file"""
        mtime = _get_allowlist_mtime(tmp_path)
        assert mtime is None


class TestResetProfileCache:
    """Tests for reset_profile_cache"""

    def test_reset_cache_clears_all_cache_variables(self):
        """Test that reset_profile_cache clears all cached values"""
        # First, populate the cache by calling get_security_profile
        with patch("security.profile.get_or_create_profile") as mock_get:
            mock_profile = MagicMock()
            mock_get.return_value = mock_profile

            with patch("security.profile._get_profile_mtime", return_value=None):
                with patch("security.profile._get_allowlist_mtime", return_value=None):
                    profile1 = get_security_profile(Path("/tmp/test"))
                    assert profile1 is not None

        # Now reset the cache
        reset_profile_cache()

        # Verify cache is cleared by checking that get_or_create_profile is called again
        with patch("security.profile.get_or_create_profile") as mock_get:
            mock_profile2 = MagicMock()
            mock_get.return_value = mock_profile2

            with patch("security.profile._get_profile_mtime", return_value=None):
                with patch("security.profile._get_allowlist_mtime", return_value=None):
                    profile2 = get_security_profile(Path("/tmp/test"))
                    assert profile2 is not None
                    # Verify the function was called (meaning cache was cleared)
                    assert mock_get.called

    def test_reset_cache_is_idempotent(self):
        """Test that reset_profile_cache can be called multiple times safely"""
        reset_profile_cache()
        reset_profile_cache()
        reset_profile_cache()
        # Should not raise any exceptions


class TestGetSecurityProfile:
    """Tests for get_security_profile"""

    def test_creates_profile_on_first_call(self):
        """Test that profile is created on first call"""
        from unittest.mock import ANY

        project_dir = Path("/tmp/test_project")

        with patch("security.profile.get_or_create_profile") as mock_get:
            mock_profile = MagicMock()
            mock_get.return_value = mock_profile

            with patch("security.profile._get_profile_mtime", return_value=None):
                with patch("security.profile._get_allowlist_mtime", return_value=None):
                    profile = get_security_profile(project_dir)
                    assert profile is mock_profile
                    # Use ANY for project_dir since get_security_profile resolves the path
                    # and on macOS /tmp resolves to /private/tmp
                    mock_get.assert_called_once_with(ANY, None)

    def test_uses_cached_profile_on_subsequent_calls(self):
        """Test that cached profile is returned on subsequent calls"""
        # This test requires actual file operations since the cache uses real Path operations
        # Reset cache first
        reset_profile_cache()

        project_dir = Path("/tmp/test_profile_cache")

        with patch("security.profile.get_or_create_profile") as mock_get:
            mock_profile = MagicMock()
            mock_get.return_value = mock_profile

            # Call with no files existing
            profile1 = get_security_profile(project_dir)
            profile2 = get_security_profile(project_dir)

            # Should use cache (both mtimes are None and match)
            assert mock_get.call_count == 1
            assert profile1 is profile2

    def test_invalidates_cache_on_profile_file_creation(self):
        """Test that cache is invalidated when profile file is created"""
        # Reset cache first
        reset_profile_cache()

        project_dir = Path("/tmp/test_profile_invalidation")
        project_dir.mkdir(parents=True, exist_ok=True)

        with patch("security.profile.get_or_create_profile") as mock_get:
            mock_profile = MagicMock()
            mock_get.return_value = mock_profile

            # First call - no file exists
            profile1 = get_security_profile(project_dir)

            # Create the profile file
            (project_dir / ".auto-claude-security.json").write_text("{}")

            # Second call - file now exists
            profile2 = get_security_profile(project_dir)

            # Should have called get_or_create_profile twice due to mtime change
            assert mock_get.call_count == 2

    def test_invalidates_cache_on_profile_file_modification(self):
        """Test that cache is invalidated when profile file is modified"""
        project_dir = Path("/tmp/test_project")

        with patch("security.profile.get_or_create_profile") as mock_get:
            mock_profile = MagicMock()
            mock_get.return_value = mock_profile

            # First call - file has mtime 100
            with patch("security.profile._get_profile_mtime", return_value=100.0):
                with patch("security.profile._get_allowlist_mtime", return_value=None):
                    profile1 = get_security_profile(project_dir)

            # Second call - file has different mtime
            with patch("security.profile._get_profile_mtime", return_value=200.0):
                with patch("security.profile._get_allowlist_mtime", return_value=None):
                    profile2 = get_security_profile(project_dir)

            # Should have called get_or_create_profile twice
            assert mock_get.call_count == 2

    def test_invalidates_cache_on_allowlist_change(self):
        """Test that cache is invalidated when allowlist is created/modified/deleted"""
        project_dir = Path("/tmp/test_project")

        with patch("security.profile.get_or_create_profile") as mock_get:
            mock_profile = MagicMock()
            mock_get.return_value = mock_profile

            # First call - no allowlist
            with patch("security.profile._get_profile_mtime", return_value=None):
                with patch("security.profile._get_allowlist_mtime", return_value=None):
                    profile1 = get_security_profile(project_dir)

            # Second call - allowlist now exists
            with patch("security.profile._get_profile_mtime", return_value=None):
                with patch("security.profile._get_allowlist_mtime", return_value=300.0):
                    profile2 = get_security_profile(project_dir)

            # Should have called get_or_create_profile twice
            assert mock_get.call_count == 2

    def test_different_project_dirs_create_different_caches(self):
        """Test that different project directories create separate cache entries"""
        project1 = Path("/tmp/project1")
        project2 = Path("/tmp/project2")

        with patch("security.profile.get_or_create_profile") as mock_get:
            mock_profile1 = MagicMock()
            mock_profile2 = MagicMock()
            mock_get.side_effect = [mock_profile1, mock_profile2]

            with patch("security.profile._get_profile_mtime", return_value=None):
                with patch("security.profile._get_allowlist_mtime", return_value=None):
                    profile1 = get_security_profile(project1)
                    profile2 = get_security_profile(project2)

                    assert profile1 is mock_profile1
                    assert profile2 is mock_profile2

    def test_resolves_project_dir_to_absolute_path(self):
        """Test that project_dir is resolved to absolute path"""
        project_dir = Path("/tmp/test/../project")  # Contains ..

        with patch("security.profile.get_or_create_profile") as mock_get:
            mock_profile = MagicMock()
            mock_get.return_value = mock_profile

            with patch("security.profile._get_profile_mtime", return_value=None):
                with patch("security.profile._get_allowlist_mtime", return_value=None):
                    get_security_profile(project_dir)

                    # Verify that the path was resolved
                    called_path = mock_get.call_args[0][0]
                    assert str(called_path) == str(project_dir.resolve())

    def test_spec_dir_affects_cache_key(self):
        """Test that spec_dir is part of the cache key"""
        project_dir = Path("/tmp/test_project")
        spec_dir1 = Path("/tmp/specs/001")
        spec_dir2 = Path("/tmp/specs/002")

        with patch("security.profile.get_or_create_profile") as mock_get:
            mock_profile1 = MagicMock()
            mock_profile2 = MagicMock()
            mock_get.side_effect = [mock_profile1, mock_profile2]

            with patch("security.profile._get_profile_mtime", return_value=None):
                with patch("security.profile._get_allowlist_mtime", return_value=None):
                    profile1 = get_security_profile(project_dir, spec_dir1)
                    profile2 = get_security_profile(project_dir, spec_dir2)

                    # Should create two separate profiles
                    assert mock_get.call_count == 2

    def test_none_spec_dir_in_cache_key(self):
        """Test that None spec_dir is handled correctly"""
        project_dir = Path("/tmp/test_project")

        with patch("security.profile.get_or_create_profile") as mock_get:
            mock_profile = MagicMock()
            mock_get.return_value = mock_profile

            with patch("security.profile._get_profile_mtime", return_value=None):
                with patch("security.profile._get_allowlist_mtime", return_value=None):
                    profile1 = get_security_profile(project_dir, None)
                    profile2 = get_security_profile(project_dir, None)

                    # Should use cache (same project_dir, both None spec_dir)
                    assert mock_get.call_count == 1

    def test_cache_hit_when_mtimes_unchanged(self):
        """Test that cache is used when mtimes are unchanged"""
        project_dir = Path("/tmp/test_project")

        with patch("security.profile.get_or_create_profile") as mock_get:
            mock_profile = MagicMock()
            mock_get.return_value = mock_profile

            # First call
            with patch("security.profile._get_profile_mtime", return_value=100.0):
                with patch("security.profile._get_allowlist_mtime", return_value=200.0):
                    profile1 = get_security_profile(project_dir)

            # Second call with same mtimes
            with patch("security.profile._get_profile_mtime", return_value=100.0):
                with patch("security.profile._get_allowlist_mtime", return_value=200.0):
                    profile2 = get_security_profile(project_dir)

            # Should only call once (cache hit)
            assert mock_get.call_count == 1
