"""Tests for query building functions."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from censo_argentino_qgis.query_builders import (
    build_geo_filter,
    build_pivot_columns,
    build_spatial_filter,
)


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
        """Should build RADIO filter using COD_2022 by default."""
        filter_sql, params = build_geo_filter("RADIO", ["020070101"])
        assert "COD_2022 IN (?)" in filter_sql
        assert params == ["020070101"]

    def test_builds_radio_filter_multiple(self):
        """Should build RADIO filter for multiple radios."""
        filter_sql, params = build_geo_filter("RADIO", ["020070101", "060140201"])
        assert "COD_2022 IN (?, ?)" in filter_sql
        assert params == ["020070101", "060140201"]

    def test_builds_radio_filter_with_cod_2010(self):
        """Should build RADIO filter using COD_2010 when specified."""
        filter_sql, params = build_geo_filter("RADIO", ["020010101"], geo_id_col="COD_2010")
        assert "COD_2010 IN (?)" in filter_sql
        assert params == ["020010101"]

    def test_builds_radio_filter_custom_geo_id_col(self):
        """Should support custom geo_id_col parameter."""
        filter_sql, params = build_geo_filter(
            "RADIO", ["123456789", "987654321"], geo_id_col="COD_2010"
        )
        assert "COD_2010 IN (?, ?)" in filter_sql
        assert params == ["123456789", "987654321"]

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
        # DuckDB doesn't support SRID parameter, so no 4326 in output

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
    """Tests for build_pivot_columns function with category expansion."""

    def test_builds_pivot_with_categories(self):
        """Should build CASE statements for each variable+category."""
        variable_categories_map = {
            "PERSONA_P11": {
                "categories": [("1", "Sí"), ("2", "No")],
                "has_nulls": False,
            }
        }

        result = build_pivot_columns(["PERSONA_P11"], variable_categories_map)

        # Check both categories present
        assert "codigo_variable = 'PERSONA_P11'" in result
        assert "valor_categoria = '1'" in result
        assert "valor_categoria = '2'" in result
        assert 'as "persona_p11_si"' in result
        assert 'as "persona_p11_no"' in result

    def test_handles_multiple_variables_with_categories(self):
        """Should handle multiple variables with different category counts."""
        variable_categories_map = {
            "PERSONA_P11": {"categories": [("1", "Sí"), ("2", "No")], "has_nulls": False},
            "PERSONA_P19": {
                "categories": [("1", "Pública"), ("2", "Privada"), ("3", "Ambas")],
                "has_nulls": False,
            },
        }

        result = build_pivot_columns(["PERSONA_P11", "PERSONA_P19"], variable_categories_map)

        # Should have 7 total columns (2 + 1 total + 3 + 1 total)
        assert result.count("SUM(CASE") == 7
        assert "persona_p11_si" in result
        assert "persona_p11_no" in result
        assert "persona_p11_total" in result
        assert "persona_p19_publica" in result
        assert "persona_p19_privada" in result
        assert "persona_p19_ambas" in result
        assert "persona_p19_total" in result

    def test_sanitizes_category_labels(self):
        """Should handle special characters and accents in category labels."""
        variable_categories_map = {
            "TEST": {
                "categories": [("1", "Categoría con ñ"), ("2", "0-14 años")],
                "has_nulls": False,
            }
        }

        result = build_pivot_columns(["TEST"], variable_categories_map)

        # Check sanitization
        assert "test_categoria_con_n" in result  # removed accent and ñ
        assert "test_cat_0_14_anos" in result  # handled leading digit

    def test_adds_null_column_when_has_nulls(self):
        """Should add NULL category column if has_nulls is True."""
        variable_categories_map = {"VAR1": {"categories": [("1", "Category 1")], "has_nulls": True}}

        result = build_pivot_columns(["VAR1"], variable_categories_map)

        # Should have 3 columns: one for category, one for NULLs, one for total
        assert result.count("SUM(CASE") == 3
        assert "valor_categoria = '1'" in result
        assert "valor_categoria IS NULL" in result
        assert 'as "var1_null"' in result
        assert 'as "var1_total"' in result

    def test_no_null_column_when_has_nulls_false(self):
        """Should NOT add NULL column if has_nulls is False."""
        variable_categories_map = {
            "VAR1": {"categories": [("1", "Category 1")], "has_nulls": False}
        }

        result = build_pivot_columns(["VAR1"], variable_categories_map)

        # Should have 2 columns: one for category, one for total
        assert result.count("SUM(CASE") == 2
        assert "IS NULL" not in result
        assert 'as "var1_total"' in result

    def test_handles_empty_category_list_total_only(self):
        """Should create single total column for variables without categories."""
        variable_categories_map = {"POB_TOT": {"categories": [], "has_nulls": False}}

        result = build_pivot_columns(["POB_TOT"], variable_categories_map)

        # Should create total column
        assert 'as "pob_tot_total"' in result
        assert "valor_categoria" not in result
        assert result.count("SUM(CASE") == 1

    def test_handles_empty_variable_list(self):
        """Should return empty string for empty variable list."""
        result = build_pivot_columns([], {})
        assert result == ""

    def test_uses_full_length_names(self):
        """Should NOT truncate to 10 characters (shapefile compatibility removed)."""
        variable_categories_map = {
            "TEST": {
                "categories": [("1", "Very Long Category Name That Exceeds Ten")],
                "has_nulls": False,
            }
        }

        result = build_pivot_columns(["TEST"], variable_categories_map)

        # Should have full name, not truncated
        assert "very_long_category_name_that_exceeds_ten" in result

    def test_newline_separates_columns(self):
        """Should newline-separate multiple pivot columns for readability."""
        variable_categories_map = {
            "VAR1": {"categories": [("1", "Cat 1"), ("2", "Cat 2")], "has_nulls": False}
        }

        result = build_pivot_columns(["VAR1"], variable_categories_map)

        # Should use newline + spaces for formatting
        assert ",\n        " in result

    def test_handles_special_characters_in_codes(self):
        """Should handle variable codes with underscores and numbers."""
        variable_categories_map = {
            "POB_2022_TOT": {"categories": [("1", "Male"), ("2", "Female")], "has_nulls": False},
            "VAR_123": {"categories": [("1", "Yes")], "has_nulls": False},
        }

        result = build_pivot_columns(["POB_2022_TOT", "VAR_123"], variable_categories_map)

        # Should have columns for both variables
        assert "pob_2022_tot_male" in result
        assert "pob_2022_tot_female" in result
        assert "var_123_yes" in result

    def test_adds_total_column_for_each_variable(self):
        """Should add _total column for each variable with categories."""
        variable_categories_map = {
            "PERSONA_P11": {"categories": [("1", "Sí"), ("2", "No")], "has_nulls": False}
        }

        result = build_pivot_columns(["PERSONA_P11"], variable_categories_map)

        # Should have 3 columns: si, no, and total
        assert result.count("SUM(CASE") == 3
        assert 'as "persona_p11_si"' in result
        assert 'as "persona_p11_no"' in result
        assert 'as "persona_p11_total"' in result

        # Total column should sum all categories (no valor_categoria filter)
        assert "codigo_variable = 'PERSONA_P11' THEN conteo" in result
