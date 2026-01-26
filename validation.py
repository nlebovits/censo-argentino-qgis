"""SQL query validation functions."""
import re


def validate_sql_placeholders(sql):
    """
    Check SQL query for unresolved placeholder variables.

    Args:
        sql: SQL query string to validate

    Returns:
        list: List of placeholder types found, empty if none
    """
    placeholders = []

    # Check for VAR_A, VAR_B, VAR_C style placeholders
    if re.search(r'\bVAR_[A-Z]\b', sql, re.IGNORECASE):
        placeholders.append("VAR_A, VAR_B, etc.")

    # Check for placeholder province names
    if re.search(r'NOMBRE_PROVINCIA', sql, re.IGNORECASE):
        placeholders.append("NOMBRE_PROVINCIA")

    # Check for placeholder department names
    if re.search(r'NOMBRE_DEPARTAMENTO', sql, re.IGNORECASE):
        placeholders.append("NOMBRE_DEPARTAMENTO")

    return placeholders
