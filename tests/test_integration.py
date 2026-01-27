"""Integration tests for category expansion and cartesian product fix.

These tests verify the end-to-end functionality of:
- Category fetching and caching
- CTE-based query generation
- Category filtering
- Cartesian product fix (accurate totals)
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from query import get_variable_categories, preload_all_metadata
from query_builders import build_geo_filter, build_pivot_columns, build_spatial_filter


class TestCategoryFetching:
    """Test category fetching and preloading.

    NOTE: These tests require network access to data.source.coop
    """

    @pytest.mark.skip(reason="Requires network access and numpy dependency")
    def test_get_variable_categories_returns_dict(self):
        """Should return dict with categories and has_nulls keys."""
        result = get_variable_categories("PERSONA_P11")

        assert isinstance(result, dict)
        assert "categories" in result
        assert "has_nulls" in result
        assert isinstance(result["categories"], list)
        assert isinstance(result["has_nulls"], bool)

    @pytest.mark.skip(reason="Requires network access and numpy dependency")
    def test_get_variable_categories_has_categories(self):
        """Should return actual categories for variables with breakdowns."""
        result = get_variable_categories("PERSONA_P11")

        # PERSONA_P11 should have categories (it's a categorical variable)
        assert len(result["categories"]) > 0
        # Each category is a tuple of (valor, etiqueta)
        for cat in result["categories"]:
            assert isinstance(cat, tuple)
            assert len(cat) == 2
            assert isinstance(cat[0], str)  # valor
            assert isinstance(cat[1], str)  # etiqueta

    @pytest.mark.skip(reason="Requires network access and numpy dependency")
    def test_preload_all_metadata_returns_map(self):
        """Should return dict mapping all variable codes to category data."""
        metadata = preload_all_metadata()

        assert isinstance(metadata, dict)
        assert len(metadata) > 0

        # Check structure of one entry
        for var_code, cat_data in list(metadata.items())[:5]:
            assert isinstance(var_code, str)
            assert isinstance(cat_data, dict)
            assert "categories" in cat_data
            assert "has_nulls" in cat_data

    @pytest.mark.skip(reason="Requires network access and numpy dependency")
    def test_preload_caches_for_fast_lookup(self):
        """Preloading should make subsequent lookups instant."""
        # First call loads metadata
        metadata1 = preload_all_metadata()

        # Second call should return same data from cache (instant)
        metadata2 = preload_all_metadata()

        assert metadata1 == metadata2
        assert id(metadata1) == id(metadata2)  # Same object in memory


class TestCategoryFiltering:
    """Test category filtering in build_pivot_columns."""

    def test_filters_selected_categories(self):
        """Should only include selected categories in pivot columns."""
        # Simulate filtering to only include categories 1 and 2
        filtered_map = {
            "PERSONA_P11": {
                "categories": [("1", "Sí"), ("2", "No")],
                "has_nulls": False,
            }
        }

        result = build_pivot_columns(["PERSONA_P11"], filtered_map)

        # Should have columns for selected categories + total
        assert 'as "persona_p11_si"' in result
        assert 'as "persona_p11_no"' in result
        assert 'as "persona_p11_total"' in result

        # Should NOT have filtered out category
        assert "no_aplica" not in result

    def test_includes_total_column_always(self):
        """Should always include _total column even with filtered categories."""
        variable_categories_map = {"VAR1": {"categories": [("1", "Cat 1")], "has_nulls": False}}

        result = build_pivot_columns(["VAR1"], variable_categories_map)

        # Should have both the category and total
        assert result.count("SUM(CASE") == 2
        assert 'as "var1_cat_1"' in result
        assert 'as "var1_total"' in result


class TestCartesianProductFix:
    """Test that CTE-based query prevents cartesian product."""

    def test_pivot_columns_generates_correct_case_statements(self):
        """Pivot columns should have proper CASE WHEN structure."""
        variable_categories_map = {
            "PERSONA_P11": {"categories": [("1", "Sí"), ("2", "No")], "has_nulls": False}
        }

        result = build_pivot_columns(["PERSONA_P11"], variable_categories_map)

        # Should have CASE statements that filter by both variable AND category
        assert "codigo_variable = 'PERSONA_P11'" in result
        assert "valor_categoria = '1'" in result
        assert "valor_categoria = '2'" in result
        assert "THEN conteo ELSE 0 END" in result

    def test_total_column_sums_all_categories(self):
        """Total column should sum without category filter."""
        variable_categories_map = {
            "VAR1": {"categories": [("1", "A"), ("2", "B")], "has_nulls": False}
        }

        result = build_pivot_columns(["VAR1"], variable_categories_map)

        # Total column should only check variable, not category
        # Look for pattern: "codigo_variable = 'VAR1' THEN conteo"
        assert "codigo_variable = 'VAR1' THEN conteo" in result
        assert 'as "var1_total"' in result

    def test_multiple_variables_independent_case_statements(self):
        """Each variable should have independent CASE statements."""
        variable_categories_map = {
            "VAR1": {"categories": [("1", "A")], "has_nulls": False},
            "VAR2": {"categories": [("1", "X")], "has_nulls": False},
        }

        result = build_pivot_columns(["VAR1", "VAR2"], variable_categories_map)

        # Should have separate CASE statements for each variable
        assert "codigo_variable = 'VAR1'" in result
        assert "codigo_variable = 'VAR2'" in result
        # Should not mix variables in same CASE statement
        var1_cases = result.count("codigo_variable = 'VAR1'")
        var2_cases = result.count("codigo_variable = 'VAR2'")
        # Each variable should have: category column + total column
        assert var1_cases == 2  # 1 category + 1 total
        assert var2_cases == 2  # 1 category + 1 total


class TestQueryBuilders:
    """Test query builder helper functions."""

    def test_build_geo_filter_with_provincia(self):
        """Should build correct provincia filter."""
        filter_sql, params = build_geo_filter("PROV", ["02", "06"])

        assert "PROV IN (?, ?)" in filter_sql
        assert params == ["02", "06"]

    def test_build_spatial_filter_creates_polygon(self):
        """Should create proper ST_Intersects with POLYGON."""
        bbox = (-58.5, -34.7, -58.3, -34.5)
        result = build_spatial_filter(bbox)

        assert "ST_Intersects" in result
        assert "POLYGON" in result
        assert "-58.5 -34.7" in result
        assert "-58.3 -34.5" in result

    def test_build_spatial_filter_returns_empty_for_none(self):
        """Should return empty string when no bbox provided."""
        result = build_spatial_filter(None)
        assert result == ""


class TestColumnCounting:
    """Test column count calculation for validation."""

    def test_counts_categories_plus_total(self):
        """Should count all category columns plus total column."""
        variable_categories_map = {
            "VAR1": {"categories": [("1", "A"), ("2", "B")], "has_nulls": False}
        }

        # Expected: 2 categories + 1 total = 3 columns
        result = build_pivot_columns(["VAR1"], variable_categories_map)
        assert result.count("SUM(CASE") == 3

    def test_counts_null_column_when_present(self):
        """Should count NULL column if has_nulls is True."""
        variable_categories_map = {"VAR1": {"categories": [("1", "A")], "has_nulls": True}}

        # Expected: 1 category + 1 null + 1 total = 3 columns
        result = build_pivot_columns(["VAR1"], variable_categories_map)
        assert result.count("SUM(CASE") == 3
        assert 'as "var1_null"' in result

    def test_total_only_for_empty_categories(self):
        """Should create single total column for variables without categories."""
        variable_categories_map = {"POB_TOT": {"categories": [], "has_nulls": False}}

        result = build_pivot_columns(["POB_TOT"], variable_categories_map)

        # Expected: 1 total column only
        assert result.count("SUM(CASE") == 1
        assert 'as "pob_tot_total"' in result


class TestNullHandling:
    """Test NULL category handling."""

    def test_null_column_generated_when_has_nulls(self):
        """Should generate NULL column when has_nulls=True."""
        variable_categories_map = {"VAR1": {"categories": [("1", "Cat")], "has_nulls": True}}

        result = build_pivot_columns(["VAR1"], variable_categories_map)

        assert "valor_categoria IS NULL" in result
        assert 'as "var1_null"' in result

    def test_no_null_column_when_no_nulls(self):
        """Should not generate NULL column when has_nulls=False."""
        variable_categories_map = {"VAR1": {"categories": [("1", "Cat")], "has_nulls": False}}

        result = build_pivot_columns(["VAR1"], variable_categories_map)

        assert "IS NULL" not in result
        assert "_null" not in result
