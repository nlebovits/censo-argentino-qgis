"""Tests for cache functions in query.py."""
import json
from pathlib import Path
from unittest.mock import patch
import pytest

# Import functions to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from query import get_cache_dir, get_cached_data, save_cached_data


class TestGetCacheDir:
    """Tests for get_cache_dir function."""

    def test_returns_path_object(self):
        """get_cache_dir should return a Path object."""
        result = get_cache_dir()
        assert isinstance(result, Path)

    def test_creates_directory_if_missing(self, temp_cache_dir):
        """get_cache_dir should create directory if it doesn't exist."""
        with patch('query.Path.home', return_value=temp_cache_dir):
            cache_dir = get_cache_dir()
            assert cache_dir.exists()
            assert cache_dir.is_dir()

    def test_directory_name_is_correct(self, temp_cache_dir):
        """Cache directory should be named 'qgis-censo-argentino'."""
        with patch('query.Path.home', return_value=temp_cache_dir):
            cache_dir = get_cache_dir()
            assert cache_dir.name == 'qgis-censo-argentino'


class TestGetCachedData:
    """Tests for get_cached_data function."""

    def test_returns_none_when_cache_missing(self, temp_cache_dir):
        """Should return None when cache file doesn't exist."""
        with patch('query.get_cache_dir', return_value=temp_cache_dir):
            result = get_cached_data('nonexistent')
            assert result is None

    def test_returns_data_when_cache_exists(self, temp_cache_dir):
        """Should return cached data when file exists."""
        # Setup: Create a cache file
        cache_file = temp_cache_dir / "test_key.json"
        test_data = {"key": "value", "number": 42}
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)

        # Test
        with patch('query.get_cache_dir', return_value=temp_cache_dir):
            result = get_cached_data('test_key')
            assert result == test_data

    def test_returns_none_when_cache_corrupted(self, temp_cache_dir):
        """Should return None when cache file is corrupted JSON."""
        # Setup: Create corrupted cache file
        cache_file = temp_cache_dir / "corrupted.json"
        with open(cache_file, 'w') as f:
            f.write("{ this is not valid json }")

        # Test
        with patch('query.get_cache_dir', return_value=temp_cache_dir):
            result = get_cached_data('corrupted')
            assert result is None

    def test_handles_unicode_correctly(self, temp_cache_dir):
        """Should handle Spanish characters correctly."""
        cache_file = temp_cache_dir / "unicode.json"
        test_data = {"provincia": "Córdoba", "descripción": "Población total"}
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False)

        with patch('query.get_cache_dir', return_value=temp_cache_dir):
            result = get_cached_data('unicode')
            assert result == test_data


class TestSaveCachedData:
    """Tests for save_cached_data function."""

    def test_creates_cache_file(self, temp_cache_dir):
        """Should create cache file with correct data."""
        test_data = {"key": "value"}

        with patch('query.get_cache_dir', return_value=temp_cache_dir):
            save_cached_data('test_key', test_data)

        cache_file = temp_cache_dir / "test_key.json"
        assert cache_file.exists()

        with open(cache_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        assert saved_data == test_data

    def test_overwrites_existing_cache(self, temp_cache_dir):
        """Should overwrite existing cache file."""
        cache_file = temp_cache_dir / "overwrite.json"
        old_data = {"old": "data"}
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(old_data, f)

        new_data = {"new": "data"}
        with patch('query.get_cache_dir', return_value=temp_cache_dir):
            save_cached_data('overwrite', new_data)

        with open(cache_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        assert saved_data == new_data

    def test_handles_unicode_correctly(self, temp_cache_dir):
        """Should save Spanish characters correctly."""
        test_data = {"provincia": "Córdoba", "año": 2022}

        with patch('query.get_cache_dir', return_value=temp_cache_dir):
            save_cached_data('unicode', test_data)

        cache_file = temp_cache_dir / "unicode.json"
        with open(cache_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Córdoba" in content  # Should not be escaped

    def test_does_not_raise_on_write_failure(self, temp_cache_dir):
        """Should handle write failures gracefully without raising."""
        # Make directory read-only to simulate write failure
        temp_cache_dir.chmod(0o444)

        try:
            with patch('query.get_cache_dir', return_value=temp_cache_dir):
                # Should not raise an exception
                save_cached_data('readonly', {"data": "test"})
        finally:
            temp_cache_dir.chmod(0o755)  # Restore permissions
