"""Tests for Bug Fix: Ambiguous column references in GROUP BY.

These tests verify that GROUP BY clauses in the geo_config_map use table-prefixed
column names to avoid "Ambiguous reference to column name" errors when multiple
tables have columns with the same name.

Bug context: When querying at DEPTO/FRACC/PROV levels, the query joins
two tables (g and cp) that both have PROV, DEPTO, FRACC, RADIO columns.
The GROUP BY in line 776 uses {geo_config_level["group_cols"]}, which must
have prefixed names like g.PROV to disambiguate.

Reference: censo_argentino_qgis/query.py, lines 700-776
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestGeoConfigGroupCols:
    """Test that geo_config_map has table-prefixed group_cols and id_field."""

    def test_depto_group_cols_has_table_prefix(self):
        """DEPTO level group_cols should be 'g.PROV, g.DEPTO'."""
        # Import the query module to access the geo_config_map
        # Since geo_config_map is defined inside load_census_layer,
        # we need to test by reading the source or extracting it.
        # For now, test by verifying the expected config structure.

        # Expected config for DEPTO level
        expected_group_cols = "g.PROV, g.DEPTO"

        # Read the query.py source to verify the config
        query_py_path = Path(__file__).parent.parent / "censo_argentino_qgis" / "query.py"
        query_source = query_py_path.read_text()

        # Find the DEPTO config section
        import re
        depto_config_match = re.search(
            r'"DEPTO":\s*\{[^}]*"group_cols":\s*"([^"]+)"',
            query_source,
            re.DOTALL
        )

        assert depto_config_match is not None, (
            "Could not find DEPTO config in query.py"
        )

        actual_group_cols = depto_config_match.group(1)

        # The bug: group_cols currently is "PROV, DEPTO"
        # Should be: "g.PROV, g.DEPTO"
        assert actual_group_cols == expected_group_cols, (
            f"DEPTO group_cols must be '{expected_group_cols}' to avoid ambiguous column error. "
            f"Current value: '{actual_group_cols}'"
        )

    def test_fracc_group_cols_has_table_prefix(self):
        """FRACC level group_cols should be 'g.PROV, g.DEPTO, g.FRACC'."""
        expected_group_cols = "g.PROV, g.DEPTO, g.FRACC"

        query_py_path = Path(__file__).parent.parent / "censo_argentino_qgis" / "query.py"
        query_source = query_py_path.read_text()

        fracc_config_match = re.search(
            r'"FRACC":\s*\{[^}]*"group_cols":\s*"([^"]+)"',
            query_source,
            re.DOTALL
        )

        assert fracc_config_match is not None, (
            "Could not find FRACC config in query.py"
        )

        actual_group_cols = fracc_config_match.group(1)

        assert actual_group_cols == expected_group_cols, (
            f"FRACC group_cols must be '{expected_group_cols}' to avoid ambiguous column error. "
            f"Current value: '{actual_group_cols}'"
        )

    def test_prov_group_cols_has_table_prefix(self):
        """PROV level group_cols should be 'g.PROV'."""
        expected_group_cols = "g.PROV"

        query_py_path = Path(__file__).parent.parent / "censo_argentino_qgis" / "query.py"
        query_source = query_py_path.read_text()

        prov_config_match = re.search(
            r'"PROV":\s*\{[^}]*"group_cols":\s*"([^"]+)"',
            query_source,
            re.DOTALL
        )

        assert prov_config_match is not None, (
            "Could not find PROV config in query.py"
        )

        actual_group_cols = prov_config_match.group(1)

        assert actual_group_cols == expected_group_cols, (
            f"PROV group_cols must be '{expected_group_cols}' to avoid ambiguous column error. "
            f"Current value: '{actual_group_cols}'"
        )

    def test_prov_id_field_has_table_prefix(self):
        """PROV level id_field should be 'g.PROV' not just 'PROV'."""
        expected_id_field = "g.PROV"

        query_py_path = Path(__file__).parent.parent / "censo_argentino_qgis" / "query.py"
        query_source = query_py_path.read_text()

        prov_config_match = re.search(
            r'"PROV":\s*\{[^}]*"id_field":\s*"([^"]+)"',
            query_source,
            re.DOTALL
        )

        assert prov_config_match is not None, (
            "Could not find PROV id_field in query.py"
        )

        actual_id_field = prov_config_match.group(1)

        assert actual_id_field == expected_id_field, (
            f"PROV id_field must be '{expected_id_field}' to avoid ambiguous column error "
            f"in SELECT clause. Current value: '{actual_id_field}'"
        )

    def test_depto_id_field_has_table_prefix(self):
        """DEPTO level id_field should use g.PROV, g.DEPTO."""
        # For concatenated fields, we need g. prefix on each part
        expected_pattern = r"g\.PROV.*g\.DEPTO"

        query_py_path = Path(__file__).parent.parent / "censo_argentino_qgis" / "query.py"
        query_source = query_py_path.read_text()

        depto_config_match = re.search(
            r'"DEPTO":\s*\{[^}]*"id_field":\s*"([^"]+)"',
            query_source,
            re.DOTALL
        )

        assert depto_config_match is not None, (
            "Could not find DEPTO id_field in query.py"
        )

        actual_id_field = depto_config_match.group(1)

        assert re.search(expected_pattern, actual_id_field), (
            f"DEPTO id_field must use table prefixes (g.PROV, g.DEPTO) "
            f"to avoid ambiguous column error. Current value: '{actual_id_field}'"
        )

    def test_fracc_id_field_has_table_prefix(self):
        """FRACC level id_field should use g.PROV, g.DEPTO, g.FRACC."""
        expected_pattern = r"g\.PROV.*g\.DEPTO.*g\.FRACC"

        query_py_path = Path(__file__).parent.parent / "censo_argentino_qgis" / "query.py"
        query_source = query_py_path.read_text()

        fracc_config_match = re.search(
            r'"FRACC":\s*\{[^}]*"id_field":\s*"([^"]+)"',
            query_source,
            re.DOTALL
        )

        assert fracc_config_match is not None, (
            "Could not find FRACC id_field in query.py"
        )

        actual_id_field = fracc_config_match.group(1)

        assert re.search(expected_pattern, actual_id_field), (
            f"FRACC id_field must use table prefixes (g.PROV, g.DEPTO, g.FRACC) "
            f"to avoid ambiguous column error. Current value: '{actual_id_field}'"
        )
