"""Tests for Bug Fix: Incorrect import statement in dialog.py.

Tests verify that dialog.py uses relative imports for modules within
the censo_argentino_qgis package.

Bug context: Line 727 in dialog.py has:
    from validation import validate_sql_placeholders

This should be:
    from .validation import validate_sql_placeholders

Without the dot prefix, Python looks for an external package named
'validation' instead of the validation.py module within censo_argentino_qgis.

Reference: censo_argentino_qgis/dialog.py, line 727
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDialogImports:
    """Test that dialog.py uses correct relative imports."""

    def test_validation_import_is_relative(self):
        """Import of validate_sql_placeholders should use relative import."""
        # Read dialog.py source
        dialog_py_path = Path(__file__).parent.parent / "censo_argentino_qgis" / "dialog.py"
        dialog_source = dialog_py_path.read_text(encoding="utf-8")

        # Find the validation import line
        # Should match: from .validation import validate_sql_placeholders
        # Should NOT match: from validation import validate_sql_placeholders
        import_match = re.search(
            r"from\s+(\.)?validation\s+import\s+validate_sql_placeholders", dialog_source
        )

        assert import_match is not None, (
            "Could not find 'from validation import validate_sql_placeholders' "
            "or 'from .validation import validate_sql_placeholders' in dialog.py"
        )

        # Check if the dot is present (group 1 will be '.' if relative import)
        has_dot = import_match.group(1) is not None

        assert has_dot, (
            "validation import must use relative import syntax: "
            "'from .validation import validate_sql_placeholders' "
            "not 'from validation import validate_sql_placeholders'"
        )

    def test_validation_import_can_be_executed(self):
        """The import should actually work when executed."""
        # This test verifies the import doesn't raise ModuleNotFoundError
        from censo_argentino_qgis.validation import validate_sql_placeholders

        # If we get here, the import worked
        assert callable(validate_sql_placeholders)
