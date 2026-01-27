"""Tests for category label sanitization."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock QGIS modules before importing query
sys.modules["qgis"] = MagicMock()
sys.modules["qgis.core"] = MagicMock()
sys.modules["qgis.PyQt"] = MagicMock()
sys.modules["qgis.PyQt.QtCore"] = MagicMock()

from censo_argentino_qgis.query import sanitize_category_label  # noqa: E402


class TestSanitizeCategoryLabel:
    """Tests for sanitize_category_label function."""

    def test_removes_accents(self):
        """Should remove Spanish accents and tildes."""
        assert sanitize_category_label("Educación") == "educacion"
        assert sanitize_category_label("Año") == "ano"
        assert sanitize_category_label("más") == "mas"

    def test_handles_leading_digits(self):
        """Should prefix with 'cat_' if starts with digit."""
        assert sanitize_category_label("0-14 años") == "cat_0_14_anos"
        assert sanitize_category_label("65+") == "cat_65"
        assert sanitize_category_label("2022") == "cat_2022"

    def test_replaces_spaces_with_underscores(self):
        """Should convert spaces to underscores."""
        assert sanitize_category_label("Sin instrucción") == "sin_instruccion"
        assert sanitize_category_label("Primario completo") == "primario_completo"

    def test_removes_special_characters(self):
        """Should remove non-alphanumeric except underscores."""
        assert sanitize_category_label("A-B/C (D)") == "a_b_c_d"
        assert sanitize_category_label("Test@123!") == "test123"
        assert sanitize_category_label("Foo & Bar") == "foo_bar"

    def test_removes_consecutive_underscores(self):
        """Should collapse multiple underscores into one."""
        assert sanitize_category_label("A  -  B") == "a_b"
        assert sanitize_category_label("Test___Value") == "test_value"

    def test_removes_leading_trailing_underscores(self):
        """Should strip underscores from start and end."""
        assert sanitize_category_label("_test_") == "test"
        assert sanitize_category_label("- value -") == "value"

    def test_empty_string_returns_unknown(self):
        """Should return 'unknown' for empty or whitespace-only strings."""
        assert sanitize_category_label("") == "unknown"
        assert sanitize_category_label("   ") == "unknown"
        assert sanitize_category_label("---") == "unknown"

    def test_none_returns_unknown(self):
        """Should return 'unknown' for None input."""
        assert sanitize_category_label(None) == "unknown"

    def test_full_length_names(self):
        """Should NOT truncate to 10 characters (shapefile compatibility removed)."""
        long_name = "Very Long Category Name That Exceeds Ten Characters"
        result = sanitize_category_label(long_name)
        assert len(result) > 10
        assert result == "very_long_category_name_that_exceeds_ten_characters"

    def test_real_census_examples(self):
        """Should handle real census category labels correctly."""
        assert sanitize_category_label("Sin instrucción") == "sin_instruccion"
        assert sanitize_category_label("Primario incompleto") == "primario_incompleto"
        assert sanitize_category_label("Primario completo") == "primario_completo"
        assert sanitize_category_label("Secundario incompleto") == "secundario_incompleto"
        assert sanitize_category_label("Secundario completo") == "secundario_completo"
        assert sanitize_category_label("0-14 años") == "cat_0_14_anos"
        assert sanitize_category_label("15-64 años") == "cat_15_64_anos"
        assert sanitize_category_label("65 años y más") == "cat_65_anos_y_mas"

    def test_lowercase_conversion(self):
        """Should convert to lowercase."""
        assert sanitize_category_label("UPPERCASE") == "uppercase"
        assert sanitize_category_label("MixedCase") == "mixedcase"

    def test_handles_slashes(self):
        """Should convert slashes to underscores."""
        assert sanitize_category_label("A/B/C") == "a_b_c"
        assert sanitize_category_label("Option A/B") == "option_a_b"
