"""Tests for SQL validation functions."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from validation import validate_sql_placeholders


class TestValidateSqlPlaceholders:
    """Tests for validate_sql_placeholders function."""

    def test_returns_empty_list_for_valid_sql(self):
        """Should return empty list when SQL has no placeholders."""
        sql = "SELECT * FROM census WHERE codigo_variable = 'POB_TOT_P'"
        result = validate_sql_placeholders(sql)
        assert result == []

    def test_detects_var_a_placeholder(self):
        """Should detect VAR_A style placeholders."""
        sql = "SELECT * FROM census WHERE codigo_variable = 'VAR_A'"
        result = validate_sql_placeholders(sql)
        assert "VAR_A, VAR_B, etc." in result

    def test_detects_var_b_placeholder(self):
        """Should detect VAR_B placeholder."""
        sql = "SELECT VAR_B FROM census"
        result = validate_sql_placeholders(sql)
        assert "VAR_A, VAR_B, etc." in result

    def test_detects_var_placeholder_case_insensitive(self):
        """Should detect VAR placeholders regardless of case."""
        sql_lower = "SELECT var_a FROM census"
        sql_upper = "SELECT VAR_A FROM census"
        sql_mixed = "SELECT Var_A FROM census"

        assert len(validate_sql_placeholders(sql_lower)) > 0
        assert len(validate_sql_placeholders(sql_upper)) > 0
        assert len(validate_sql_placeholders(sql_mixed)) > 0

    def test_detects_nombre_provincia_placeholder(self):
        """Should detect NOMBRE_PROVINCIA placeholder."""
        sql = "SELECT * FROM geo WHERE provincia = 'NOMBRE_PROVINCIA'"
        result = validate_sql_placeholders(sql)
        assert "NOMBRE_PROVINCIA" in result

    def test_detects_nombre_departamento_placeholder(self):
        """Should detect NOMBRE_DEPARTAMENTO placeholder."""
        sql = "SELECT * FROM geo WHERE departamento = 'NOMBRE_DEPARTAMENTO'"
        result = validate_sql_placeholders(sql)
        assert "NOMBRE_DEPARTAMENTO" in result

    def test_detects_multiple_placeholders(self):
        """Should detect multiple different placeholder types."""
        sql = """
        SELECT VAR_A, VAR_B
        FROM census
        WHERE provincia = 'NOMBRE_PROVINCIA'
        AND departamento = 'NOMBRE_DEPARTAMENTO'
        """
        result = validate_sql_placeholders(sql)
        assert len(result) == 3
        assert "VAR_A, VAR_B, etc." in result
        assert "NOMBRE_PROVINCIA" in result
        assert "NOMBRE_DEPARTAMENTO" in result

    def test_does_not_detect_var_in_real_variable_names(self):
        """Should not falsely detect VAR in legitimate variable names."""
        # Real census variables might contain VAR but not follow placeholder pattern
        sql = "SELECT codigo_variable FROM census"
        result = validate_sql_placeholders(sql)
        assert result == []

    def test_handles_empty_string(self):
        """Should return empty list for empty SQL."""
        result = validate_sql_placeholders("")
        assert result == []

    def test_handles_multiline_sql(self):
        """Should work with multiline SQL queries."""
        sql = """
        SELECT
            codigo_variable,
            VAR_A as value
        FROM census
        WHERE provincia = 'NOMBRE_PROVINCIA'
        """
        result = validate_sql_placeholders(sql)
        assert "VAR_A, VAR_B, etc." in result
        assert "NOMBRE_PROVINCIA" in result

    def test_placeholder_must_be_word_boundary(self):
        """VAR_ should only match at word boundaries."""
        # These should NOT trigger (VAR_A is part of a larger word)
        sql = "SELECT MYVAR_ABLE FROM table"
        result = validate_sql_placeholders(sql)
        # Should not detect VAR_A placeholder in MYVAR_ABLE
        assert result == []
