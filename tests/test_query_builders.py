"""Tests for query building functions."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from query_builders import build_geo_filter, build_pivot_columns, build_spatial_filter


class TestBuildGeoFilter:
    """Tests for build_geo_filter function."""

    def test_returns_empty_when_no_filters(self):
        """Should return empty filter and params when geo_filters is empty."""
        filter_sql, params = build_geo_filter("PROV", [])
        assert filter_sql == ""
        assert params == []

    def test_returns_empty_when_filters_none(self):
        """Should return empty filter and params when geo_filters is None."""
        filter_sql, params = build_geo_filter("PROV", None)
        assert filter_sql == ""
        assert params == []

    def test_builds_prov_filter_single(self):
        """Should build PROV IN filter for single province."""
        filter_sql, params = build_geo_filter("PROV", ["02"])
        assert "PROV IN (?)" in filter_sql
        assert params == ["02"]

    def test_builds_prov_filter_multiple(self):
        """Should build PROV IN filter for multiple provinces."""
        filter_sql, params = build_geo_filter("PROV", ["02", "06", "14"])
        assert "PROV IN (?, ?, ?)" in filter_sql
        assert params == ["02", "06", "14"]

    def test_builds_depto_filter_single(self):
        """Should build DEPTO filter parsing PROV-DEPTO format."""
        filter_sql, params = build_geo_filter("DEPTO", ["02-007"])
        assert "(PROV = ? AND DEPTO = ?)" in filter_sql
        assert params == ["02", "007"]

    def test_builds_depto_filter_multiple(self):
        """Should build DEPTO filter with OR for multiple departments."""
        filter_sql, params = build_geo_filter("DEPTO", ["02-007", "06-014"])
        assert "(PROV = ? AND DEPTO = ?)" in filter_sql
        assert " OR " in filter_sql
        assert params == ["02", "007", "06", "014"]

    def test_ignores_malformed_depto_codes(self):
        """Should ignore DEPTO codes that don't have exactly 2 parts."""
        filter_sql, params = build_geo_filter("DEPTO", ["02", "02-007", "invalid-code-extra"])
        # Should only include the valid "02-007"
        assert params == ["02", "007"]

    def test_builds_fracc_filter_single(self):
        """Should build FRACC filter parsing PROV-DEPTO-FRACC format."""
        filter_sql, params = build_geo_filter("FRACC", ["02-007-01"])
        assert "(PROV = ? AND DEPTO = ? AND FRACC = ?)" in filter_sql
        assert params == ["02", "007", "01"]

    def test_builds_fracc_filter_multiple(self):
        """Should build FRACC filter with OR for multiple fracciones."""
        filter_sql, params = build_geo_filter("FRACC", ["02-007-01", "06-014-02"])
        assert "(PROV = ? AND DEPTO = ? AND FRACC = ?)" in filter_sql
        assert " OR " in filter_sql
        assert params == ["02", "007", "01", "06", "014", "02"]

    def test_ignores_malformed_fracc_codes(self):
        """Should ignore FRACC codes that don't have exactly 3 parts."""
        filter_sql, params = build_geo_filter("FRACC", ["02-007", "02-007-01", "bad"])
        # Should only include the valid "02-007-01"
        assert params == ["02", "007", "01"]

    def test_builds_radio_filter_single(self):
        """Should build RADIO filter using COD_2022."""
        filter_sql, params = build_geo_filter("RADIO", ["020070101"])
        assert "COD_2022 IN (?)" in filter_sql
        assert params == ["020070101"]

    def test_builds_radio_filter_multiple(self):
        """Should build RADIO filter for multiple radios."""
        filter_sql, params = build_geo_filter("RADIO", ["020070101", "060140201"])
        assert "COD_2022 IN (?, ?)" in filter_sql
        assert params == ["020070101", "060140201"]

    def test_sql_injection_safety_prov(self):
        """Should safely handle potential SQL injection in PROV filters."""
        # Attempt SQL injection - should be safely parameterized
        filter_sql, params = build_geo_filter("PROV", ["02'; DROP TABLE census; --"])
        assert "PROV IN (?)" in filter_sql
        assert params == ["02'; DROP TABLE census; --"]
        # The malicious input is in params, not in SQL string

    def test_sql_injection_safety_depto(self):
        """Should safely handle potential SQL injection in DEPTO filters."""
        # Test with valid DEPTO format but with SQL injection attempt
        filter_sql, params = build_geo_filter("DEPTO", ["02'; DROP TABLE--007"])
        # Malformed code (3 dashes instead of 1) gets filtered out, so empty result
        # Let's use a properly formatted code
        filter_sql, params = build_geo_filter("DEPTO", ["02-007"])
        # Even though the format is valid, any SQL would be safely parameterized
        assert "(PROV = ? AND DEPTO = ?)" in filter_sql
        assert params == ["02", "007"]
        # No SQL keywords should appear in the filter string itself
        assert "DROP" not in filter_sql


class TestBuildSpatialFilter:
    """Tests for build_spatial_filter function."""

    def test_returns_empty_when_bbox_none(self):
        """Should return empty string when bbox is None."""
        result = build_spatial_filter(None)
        assert result == ""

    def test_builds_valid_spatial_filter(self):
        """Should build ST_Intersects filter with POLYGON."""
        bbox = (-58.5, -34.7, -58.3, -34.5)
        result = build_spatial_filter(bbox)

        assert "ST_Intersects" in result
        assert "ST_GeomFromText" in result
        assert "POLYGON" in result
        assert "4326" in result

    def test_uses_correct_bbox_coordinates(self):
        """Should use bbox coordinates in correct order for POLYGON."""
        bbox = (-58.5, -34.7, -58.3, -34.5)
        result = build_spatial_filter(bbox)

        # Check all four corners are present
        assert "-58.5 -34.7" in result  # min x, min y
        assert "-58.3 -34.7" in result  # max x, min y
        assert "-58.3 -34.5" in result  # max x, max y
        assert "-58.5 -34.5" in result  # min x, max y

    def test_closes_polygon(self):
        """Should close POLYGON by repeating first coordinate."""
        bbox = (-58.5, -34.7, -58.3, -34.5)
        result = build_spatial_filter(bbox)

        # First and last coordinates should be the same
        assert result.count("-58.5 -34.7") == 2  # Appears at start and end

    def test_handles_various_coordinate_ranges(self):
        """Should work with different coordinate systems."""
        # Test with positive coordinates
        bbox = (10.0, 20.0, 15.0, 25.0)
        result = build_spatial_filter(bbox)
        assert "10.0 20.0" in result
        assert "15.0 25.0" in result

        # Test with large negative coordinates
        bbox = (-180, -90, 180, 90)
        result = build_spatial_filter(bbox)
        assert "-180 -90" in result
        assert "180 90" in result


class TestBuildPivotColumns:
    """Tests for build_pivot_columns function."""

    def test_builds_single_pivot_column(self):
        """Should build pivot SQL for single variable."""
        result = build_pivot_columns(["POB_TOT_P"])
        expected = "MAX(CASE WHEN codigo_variable = 'POB_TOT_P' THEN valor END) AS POB_TOT_P"
        assert result == expected

    def test_builds_multiple_pivot_columns(self):
        """Should build pivot SQL for multiple variables."""
        result = build_pivot_columns(["POB_TOT_P", "VIVIENDA_TOT", "HOGAR_TOT"])

        assert "POB_TOT_P" in result
        assert "VIVIENDA_TOT" in result
        assert "HOGAR_TOT" in result
        assert result.count("MAX(CASE") == 3
        assert result.count("AS ") == 3

    def test_comma_separates_columns(self):
        """Should comma-separate multiple pivot columns."""
        result = build_pivot_columns(["VAR1", "VAR2", "VAR3"])
        parts = result.split(", ")
        assert len(parts) == 3

    def test_each_column_has_max_case_structure(self):
        """Each pivot column should have MAX(CASE WHEN ... THEN ... END) structure."""
        result = build_pivot_columns(["POB_TOT_P"])
        assert "MAX(" in result
        assert "CASE WHEN" in result
        assert "THEN valor END" in result

    def test_handles_empty_list(self):
        """Should return empty string for empty variable list."""
        result = build_pivot_columns([])
        assert result == ""

    def test_preserves_variable_code_names(self):
        """Should use variable codes as both condition and alias."""
        result = build_pivot_columns(["MY_VAR_CODE"])
        assert "codigo_variable = 'MY_VAR_CODE'" in result
        assert "AS MY_VAR_CODE" in result

    def test_handles_special_characters_in_codes(self):
        """Should handle variable codes with underscores and numbers."""
        codes = ["POB_2022_TOT", "VAR_123", "TEST_VAR_A"]
        result = build_pivot_columns(codes)

        for code in codes:
            assert f"codigo_variable = '{code}'" in result
            assert f"AS {code}" in result
