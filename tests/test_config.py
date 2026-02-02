"""Tests for census configuration module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from censo_argentino_qgis.config import AVAILABLE_YEARS, BASE_URL, CENSUS_CONFIG


class TestCensusConfig:
    """Tests for CENSUS_CONFIG structure."""

    def test_has_2022_config(self):
        """Should have configuration for 2022 census."""
        assert "2022" in CENSUS_CONFIG

    def test_has_2010_config(self):
        """Should have configuration for 2010 census."""
        assert "2010" in CENSUS_CONFIG

    def test_2022_geo_id_column(self):
        """2022 should use COD_2022 as geo_id_column."""
        assert CENSUS_CONFIG["2022"]["geo_id_column"] == "COD_2022"

    def test_2010_geo_id_column(self):
        """2010 should use COD_2010 as geo_id_column."""
        assert CENSUS_CONFIG["2010"]["geo_id_column"] == "COD_2010"

    def test_2022_has_required_entities(self):
        """2022 should have HOGAR, PERSONA, VIVIENDA entities."""
        entities = CENSUS_CONFIG["2022"]["entities"]
        assert "HOGAR" in entities
        assert "PERSONA" in entities
        assert "VIVIENDA" in entities

    def test_2010_has_required_entities(self):
        """2010 should have HOGAR, PERSONA, VIVIENDA entities."""
        entities = CENSUS_CONFIG["2010"]["entities"]
        assert "HOGAR" in entities
        assert "PERSONA" in entities
        assert "VIVIENDA" in entities

    def test_2022_urls_use_base_url(self):
        """2022 URLs should use the base URL pattern."""
        urls = CENSUS_CONFIG["2022"]["urls"]
        assert BASE_URL in urls["census"]
        assert BASE_URL in urls["metadata"]
        assert BASE_URL in urls["radios"]
        assert "/2022/" in urls["census"]

    def test_2010_urls_use_base_url(self):
        """2010 URLs should use the base URL pattern."""
        urls = CENSUS_CONFIG["2010"]["urls"]
        assert BASE_URL in urls["census"]
        assert BASE_URL in urls["metadata"]
        assert BASE_URL in urls["radios"]
        assert "/2010/" in urls["census"]

    def test_urls_have_parquet_extension(self):
        """All URLs should point to parquet files."""
        for year in CENSUS_CONFIG:
            for url_type, url in CENSUS_CONFIG[year]["urls"].items():
                assert url.endswith(".parquet"), f"{year}/{url_type} should be parquet"


class TestAvailableYears:
    """Tests for AVAILABLE_YEARS list."""

    def test_includes_2022(self):
        """Should include 2022."""
        assert "2022" in AVAILABLE_YEARS

    def test_includes_2010(self):
        """Should include 2010."""
        assert "2010" in AVAILABLE_YEARS

    def test_2022_comes_first(self):
        """2022 should be first (most recent)."""
        assert AVAILABLE_YEARS[0] == "2022"

    def test_all_years_have_config(self):
        """All available years should have config entries."""
        for year in AVAILABLE_YEARS:
            assert year in CENSUS_CONFIG, f"Year {year} missing from CENSUS_CONFIG"
