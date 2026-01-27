# Fix Census Data Aggregation and Add Category Expansion

**Type:** Bug Fix + Feature Enhancement
**Priority:** HIGH (Phase 1), MEDIUM (Phase 2)
**Estimated Effort:** Phase 1: 6-8 hours | Phase 2: 8-10 hours
**Date Created:** 2026-01-27
**Status:** Critical Gaps Resolved - Ready for Implementation

---

## Critical Design Decisions (Resolved 2026-01-27)

### 1. Column Naming: Full Names, No Shapefile Truncation
**Decision:** Use full category labels with proper sanitization. No 10-character truncation.
- Example: `educacion_sin_instruccion` (full), not `sin_instru` (truncated)
- Rationale: Modern GIS formats (GeoPackage, GeoParquet) have no limits
- Documentation: Add note recommending GeoPackage/GeoParquet over shapefiles

### 2. Partial Category Fetch Failures: Retry Then Skip
**Decision:** Retry failed variables 3 times with exponential backoff, then skip with warning dialog.
- User sees: "Failed to fetch categories for OCUPACION after 3 attempts. Loading other variables..."
- Query continues with successfully fetched variables

### 3. NULL Category Handling: Dynamic NULL Columns
**Decision:** Create `{variable}_null` column only if NULL category rows exist.
- If EDUCACION has 50 rows with `valor_categoria IS NULL`, create `educacion_null` column
- If no NULL rows exist, no NULL column (keeps schema clean)
- Implementation: Check for NULL existence before generating column

### 4. Column Count Limits: Warn at 50, Block at 100
**Decision:** Show warning dialog at 50 columns, block with suggestions at 100.
- Warning message suggests: select fewer variables, use Phase 2 filtering, or query with Python/DuckDB directly
- User can override warning but not block

### 5. Empty Category Lists: Valid for Total-Only Variables
**Decision:** Empty category list is valid (e.g., POB_TOT population total).
- Skip category expansion for these variables
- Create single column with variable total (fallback to old behavior)
- No error message needed

---

## Overview

The plugin currently suffers from two critical data handling issues that compromise data accuracy:

1. **Inflated Totals (Bug):** Aggregated geographies (FRACC, DEPTO, PROV) return values much higher than expected due to cartesian product joins
2. **Lost Categorical Detail (Missing Feature):** Census data contains categorical breakdowns (education levels, age ranges, etc.) that are currently either lost or incorrectly aggregated

This plan addresses both issues through a two-phase approach: Phase 1 fixes the core data integrity bug and auto-expands categories, while Phase 2 adds user control over category selection.

---

## Problem Statement

### Data Structure

Census data is stored in long format with categorical breakdowns:

```
id_geo    | codigo_variable | valor_categoria | etiqueta_categoria       | conteo
----------|-----------------|-----------------|--------------------------|-------
02-007-01 | EDUCACION       | 1               | Sin instrucción          | 150
02-007-01 | EDUCACION       | 2               | Primario incompleto      | 300
02-007-01 | EDAD            | 1               | 0-14 años                | 500
```

### Current Query Problem

**Location:** `query.py:368-400`

The current implementation:
1. Joins geometry table with unpivoted census data
2. Creates cartesian product when multiple variables selected
3. For dissolved geometries (FRACC/DEPTO/PROV), each radio geometry row joins with multiple census rows
4. GROUP BY aggregates these duplicated geometry rows, inflating totals
5. Categories are summed together, losing categorical breakdown

**Example of Duplication:**

```
Radio 001 joins with EDUCACION rows (4 categories) = 4 geometry rows
Radio 001 joins with EDAD rows (3 categories) = 3 geometry rows
Total: 7 rows for a single radio instead of 1
When aggregated to FRACC, this causes 7× multiplication
```

### Root Cause Analysis

**File:** `query.py:355-400`

```python
# Lines 355-366: Current pivot logic
for var_code in variable_codes:
    if config["dissolve"]:
        pivot_columns.append(
            f"SUM(CASE WHEN c.codigo_variable = '{var_code}' THEN c.conteo ELSE 0 END) as \"{var_code}\""
        )

# Lines 368-400: Problematic query
query = f"""
    SELECT
        {config["id_field"]} as geo_id,
        ST_AsText(ST_Union_Agg(g.geometry)) as wkt,
        {pivot_sql}
    FROM (
        SELECT * FROM 'radios.parquet'
        WHERE 1=1 {geo_filter} {spatial_filter}
    ) g
    JOIN 'census-data.parquet' c
        ON g.COD_2022 = c.id_geo
    WHERE {census_where_clause}
    GROUP BY {config["group_cols"]}
"""
```

**Problem:** JOIN happens BEFORE filtering on categories, creating cartesian products.

---

## Proposed Solution: Two-Phase Approach

### Phase 1: Fix Aggregation + Auto-Expand Categories ⭐ **Priority**

**Goals:**
- ✅ Fix inflated totals with CTE-based query restructure
- ✅ Auto-expand all categories by default (one column per category)
- ✅ No UI changes required
- ✅ Maintain backward compatibility where possible

**Key Technical Approach:**
- Use CTE to pivot census data at radio level FIRST (prevents cartesian product)
- Each variable+category gets its own column
- 1:1 join between geometry and pivoted census data
- Clean aggregation on deduplicated data

### Phase 2: Add Category Selection UI (Future Enhancement)

**Goals:**
- ✅ Allow users to select specific categories instead of loading all
- ✅ Reduce column count for large variable sets
- ✅ Better control over data granularity
- ✅ Maintain "auto-expand all" as default

---

## Phase 1: Technical Implementation

### 1.1 Backend Query Logic Restructure

**Files to Modify:**
- `query.py:249-400` - Rewrite `load_census_layer()`
- `query_builders.py:75-88` - Update `build_pivot_columns()` or create new function

**New Query Pattern with CTE:**

```sql
-- For dissolve queries (FRACC, DEPTO, PROV)
WITH pivoted_census AS (
    SELECT
        c.id_geo,
        c.valor_provincia,
        c.valor_departamento,
        c.valor_fraccion,
        -- Generate one column per variable+category combination
        SUM(CASE WHEN codigo_variable = 'EDUCACION' AND valor_categoria = '1' THEN conteo ELSE 0 END) as "educacion_sin_instruccion",
        SUM(CASE WHEN codigo_variable = 'EDUCACION' AND valor_categoria = '2' THEN conteo ELSE 0 END) as "educacion_primario_incompleto",
        SUM(CASE WHEN codigo_variable = 'EDAD' AND valor_categoria = '1' THEN conteo ELSE 0 END) as "edad_0_14"
    FROM 'census-data.parquet' c
    WHERE c.codigo_variable IN ('EDUCACION', 'EDAD')
    GROUP BY c.id_geo, c.valor_provincia, c.valor_departamento, c.valor_fraccion
)
SELECT
    g.PROV || '-' || g.DEPTO || '-' || g.FRACC as geo_id,
    ST_AsText(ST_MemUnion_Agg(g.geometry)) as wkt,
    SUM(pc.educacion_sin_instruccion) as educacion_sin_instruccion,
    SUM(pc.educacion_primario_incompleto) as educacion_primario_incompleto,
    SUM(pc.edad_0_14) as edad_0_14
FROM radios.parquet g
JOIN pivoted_census pc ON g.COD_2022 = pc.id_geo
WHERE 1=1 {geo_filter} {spatial_filter}
GROUP BY g.PROV, g.DEPTO, g.FRACC
```

**Key Changes:**
1. CTE pivots census data at radio level FIRST (prevents cartesian product)
2. Each variable+category gets its own column with sanitized name
3. 1:1 join between geometry and pivoted census data
4. Use `ST_MemUnion_Agg` instead of `ST_Union_Agg` for better memory efficiency (DuckDB best practice)
5. Clean aggregation on deduplicated data

### 1.2 Add Helper Function: Get Variable Categories

**File:** `query.py` (new function around line 195)

```python
def get_variable_categories(variable_code, progress_callback=None, retry_count=3):
    """
    Query census data and return list of (valor_categoria, etiqueta_categoria)
    for a given variable code. Includes NULL category detection.

    Args:
        variable_code: Single variable code string (e.g., 'EDUCACION')
        progress_callback: Optional callback(percent, message) for progress updates
        retry_count: Number of retry attempts on failure (default 3)

    Returns:
        Dict with keys:
        - 'categories': List of tuples [(valor, etiqueta), ...]
        - 'has_nulls': Boolean indicating if NULL categories exist

        Example: {
            'categories': [('1', 'Sin instrucción'), ('2', 'Primario incompleto')],
            'has_nulls': True
        }

    Raises:
        Exception: If DuckDB connection fails after all retries
    """
    cache_key = f"categories_{variable_code}"

    # Check cache first
    cached = get_cached_data(cache_key)
    if cached is not None:
        return cached

    if progress_callback:
        progress_callback(5, f"Fetching categories for {variable_code}...")

    for attempt in range(retry_count):
        try:
            con = _connection_pool.get_connection(load_extensions=True)

            # Query for non-NULL categories
            query_categories = """
                SELECT DISTINCT
                    valor_categoria,
                    etiqueta_categoria
                FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/census-data.parquet'
                WHERE codigo_variable = ?
                  AND valor_categoria IS NOT NULL
                ORDER BY CAST(valor_categoria AS INTEGER)
            """

            result = con.execute(query_categories, [variable_code]).fetchall()
            categories = [(str(row[0]), str(row[1])) for row in result]

            # Check if NULL categories exist (DESIGN DECISION #3)
            query_nulls = """
                SELECT COUNT(*) as null_count
                FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/census-data.parquet'
                WHERE codigo_variable = ?
                  AND valor_categoria IS NULL
            """

            null_count = con.execute(query_nulls, [variable_code]).fetchone()[0]
            has_nulls = null_count > 0

            if progress_callback:
                progress_callback(10, f"Found {len(categories)} categories" +
                                 (f" + {null_count} NULL rows" if has_nulls else ""))

            result_dict = {
                'categories': categories,
                'has_nulls': has_nulls
            }

            # Save to cache
            save_cached_data(cache_key, result_dict)

            return result_dict

        except Exception as e:
            if attempt < retry_count - 1:
                # Exponential backoff: 1s, 2s, 4s
                wait_time = 2 ** attempt
                if progress_callback:
                    progress_callback(5, f"Retry {attempt + 1}/{retry_count} for {variable_code} in {wait_time}s...")
                time.sleep(wait_time)
            else:
                # All retries exhausted
                raise Exception(f"Failed to fetch categories for {variable_code} after {retry_count} attempts: {str(e)}")
```

### 1.3 Column Name Sanitization

**File:** `query.py` (new function around line 45)

```python
def sanitize_category_label(label):
    """
    Convert category label to valid QGIS field name.

    NO LENGTH TRUNCATION - Full names for modern GIS formats.
    Shapefile users should export to GeoPackage or GeoParquet instead.

    Rules:
    - Lowercase only
    - Underscores for spaces/hyphens
    - Remove accents and special characters
    - Must start with letter (prefix with 'cat_' if starts with digit)

    Args:
        label: Original category label (e.g., "Sin instrucción")

    Returns:
        Sanitized field name (e.g., "sin_instruccion")
    """
    import unicodedata
    import re

    # Remove accents/diacritics
    label = unicodedata.normalize('NFKD', label).encode('ASCII', 'ignore').decode()

    # Convert to lowercase
    label = label.lower()

    # Replace spaces, hyphens, and slashes with underscores
    label = label.replace(" ", "_").replace("-", "_").replace("/", "_")

    # Remove non-alphanumeric except underscores
    label = re.sub(r'[^a-z0-9_]', '', label)

    # Remove consecutive underscores
    label = re.sub(r'_+', '_', label)

    # Remove leading/trailing underscores
    label = label.strip('_')

    # Ensure starts with letter
    if label and label[0].isdigit():
        label = 'cat_' + label

    return label or "unknown"
```

**Output Examples (FULL NAMES):**
```
"Sin instrucción"        → "sin_instruccion"
"Primario completo"      → "primario_completo"
"0-14 años"              → "cat_0_14_anos"
"65 años y más"          → "cat_65_anos_y_mas"
"Nivel universitario"    → "nivel_universitario"
```

**Note:** Column names can be much longer than 10 characters. Users exporting to shapefiles will see truncation warnings.

### 1.4 Update Pivot Column Builder

**File:** `query_builders.py:75-88` - Replace `build_pivot_columns()`

```python
def build_pivot_columns(variable_codes, variable_categories_map):
    """
    Build SQL column list for pivoting census variables with categories.
    Includes NULL category columns when applicable (DESIGN DECISION #3).

    Args:
        variable_codes: List of variable code strings (e.g., ['EDUCACION', 'EDAD'])
        variable_categories_map: Dict mapping var_code to result dicts
            Example: {
                'EDUCACION': {
                    'categories': [('1', 'Sin instrucción'), ('2', 'Primario incompleto')],
                    'has_nulls': True
                },
                'EDAD': {
                    'categories': [('1', '0-14 años'), ('2', '15-64 años')],
                    'has_nulls': False
                }
            }

    Returns:
        str: Comma-separated SQL column definitions for CTE pivot

    Example output:
        "SUM(CASE WHEN codigo_variable = 'EDUCACION' AND valor_categoria = '1'
              THEN conteo ELSE 0 END) as \"educacion_sin_instruccion\",
         SUM(CASE WHEN codigo_variable = 'EDUCACION' AND valor_categoria = '2'
              THEN conteo ELSE 0 END) as \"educacion_primario_incompleto\",
         SUM(CASE WHEN codigo_variable = 'EDUCACION' AND valor_categoria IS NULL
              THEN conteo ELSE 0 END) as \"educacion_null\""
    """
    from query import sanitize_category_label

    pivot_cols = []

    for var_code in variable_codes:
        cat_data = variable_categories_map.get(var_code, {'categories': [], 'has_nulls': False})
        categories = cat_data['categories']
        has_nulls = cat_data['has_nulls']

        # DESIGN DECISION #5: Handle empty category lists (total-only variables)
        if not categories and not has_nulls:
            # No categories - create single total column (fallback behavior)
            col_name = f"{var_code.lower()}_total"
            case_stmt = (
                f"SUM(CASE WHEN codigo_variable = '{var_code}' "
                f"THEN conteo ELSE 0 END) as \"{col_name}\""
            )
            pivot_cols.append(case_stmt)
            continue

        # Regular categories
        for valor, etiqueta in categories:
            # DESIGN DECISION #1: Use full sanitized label (no truncation)
            clean_label = sanitize_category_label(etiqueta)
            col_name = f"{var_code.lower()}_{clean_label}"

            # Build CASE statement
            case_stmt = (
                f"SUM(CASE WHEN codigo_variable = '{var_code}' "
                f"AND valor_categoria = '{valor}' "
                f"THEN conteo ELSE 0 END) as \"{col_name}\""
            )
            pivot_cols.append(case_stmt)

        # DESIGN DECISION #3: Add NULL category column if exists
        if has_nulls:
            col_name = f"{var_code.lower()}_null"
            case_stmt = (
                f"SUM(CASE WHEN codigo_variable = '{var_code}' "
                f"AND valor_categoria IS NULL "
                f"THEN conteo ELSE 0 END) as \"{col_name}\""
            )
            pivot_cols.append(case_stmt)

    return ",\n        ".join(pivot_cols)
```

### 1.5 Update load_census_layer Function

**File:** `query.py:249-400` - Major rewrite

**New Signature:**
```python
def load_census_layer(
    variable_codes,
    geo_level="RADIO",
    geo_filters=None,
    spatial_filter=None,
    layer_name=None,
    progress_callback=None,
):
    """
    Load census data with expanded categories.

    Changes from previous version:
    - Auto-fetches categories for each variable
    - Expands categories into separate columns
    - Uses CTE to prevent cartesian products
    - Returns layer with columns like: educacion_sin_instru, edad_0_14, etc.
    """
```

**Implementation Outline:**

```python
def load_census_layer(...):
    try:
        if progress_callback:
            progress_callback(2, "Initializing DuckDB connection...")

        con = _connection_pool.get_connection(load_extensions=True)

        # NEW: Fetch categories for all variables (DESIGN DECISION #2: Retry logic)
        if progress_callback:
            progress_callback(5, "Fetching variable categories...")

        variable_categories_map = {}
        failed_variables = []

        for idx, var_code in enumerate(variable_codes):
            percent = 5 + int((idx / len(variable_codes)) * 10)

            try:
                result = get_variable_categories(var_code, progress_callback)
                variable_categories_map[var_code] = result
            except Exception as e:
                # DESIGN DECISION #2: Skip failed variable with warning
                QgsMessageLog.logMessage(
                    f"Failed to fetch categories for {var_code}: {str(e)}",
                    "Censo Argentino",
                    Qgis.Warning
                )
                failed_variables.append(var_code)

        # Show warning dialog if any variables failed (DESIGN DECISION #2)
        if failed_variables:
            from qgis.PyQt.QtWidgets import QMessageBox
            QMessageBox.warning(
                None,
                "Category Fetch Failed",
                f"Failed to fetch categories for: {', '.join(failed_variables)}\n\n"
                f"Loading data for other {len(variable_categories_map)} variable(s)."
            )

        # Exit if ALL variables failed
        if not variable_categories_map:
            raise Exception("Failed to fetch categories for all selected variables.")

        # DESIGN DECISION #4: Check total column count and warn/block
        total_columns = sum(
            len(cat_data['categories']) + (1 if cat_data['has_nulls'] else 0)
            for cat_data in variable_categories_map.values()
        )

        if total_columns > 100:
            from qgis.PyQt.QtWidgets import QMessageBox
            QMessageBox.critical(
                None,
                "Too Many Columns",
                f"This query would create {total_columns} columns!\n\n"
                f"Maximum allowed: 100 columns\n\n"
                f"Suggestions:\n"
                f"• Select fewer variables\n"
                f"• Use Phase 2 category selection (coming soon)\n"
                f"• Query directly with Python/DuckDB for full control"
            )
            raise Exception(f"Query blocked: {total_columns} columns exceeds limit of 100")

        elif total_columns > 50:
            from qgis.PyQt.QtWidgets import QMessageBox
            reply = QMessageBox.warning(
                None,
                "Many Columns Warning",
                f"This query will create {total_columns} columns.\n\n"
                f"This may impact performance and usability.\n\n"
                f"Continue anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                raise Exception("Query cancelled by user")

        # Build CTE pivot columns
        if progress_callback:
            progress_callback(15, "Building query...")

        pivot_sql = build_pivot_columns(variable_codes, variable_categories_map)

        # Build geographic configuration
        geo_config = {
            "RADIO": {
                "group_cols": "g.PROV, g.DEPTO, g.FRACC, g.RADIO",
                "id_field": "g.COD_2022",
                "dissolve": False,
            },
            "FRACC": {
                "group_cols": "g.PROV, g.DEPTO, g.FRACC",
                "id_field": "g.PROV || '-' || g.DEPTO || '-' || g.FRACC",
                "dissolve": True,
            },
            "DEPTO": {
                "group_cols": "g.PROV, g.DEPTO",
                "id_field": "g.PROV || '-' || g.DEPTO",
                "dissolve": True,
            },
            "PROV": {
                "group_cols": "g.PROV",
                "id_field": "g.PROV",
                "dissolve": True,
            },
        }

        config = geo_config[geo_level]

        # Build filters
        geo_filter = ""
        if geo_filters:
            # Use existing build_geo_filter from query_builders.py
            filter_sql, params = build_geo_filter(geo_level, geo_filters)
            geo_filter = f"AND {filter_sql}"

        spatial_filter_sql = ""
        if spatial_filter:
            # Use existing build_spatial_filter
            spatial_filter_sql = f"AND {build_spatial_filter(spatial_filter)}"

        # NEW: CTE-based query structure
        if config["dissolve"]:
            # Build list of SELECT columns for final query
            category_columns = []
            for var_code in variable_codes:
                for valor, etiqueta in variable_categories_map[var_code]:
                    clean_label = sanitize_category_label(etiqueta)
                    col_name = f"{var_code.lower()}_{clean_label}"
                    category_columns.append(f"SUM(pc.\"{col_name}\") as \"{col_name}\"")

            category_select = ",\n        ".join(category_columns)

            query = f"""
                WITH pivoted_census AS (
                    SELECT
                        c.id_geo,
                        c.valor_provincia,
                        c.valor_departamento,
                        c.valor_fraccion,
                        {pivot_sql}
                    FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/census-data.parquet' c
                    WHERE c.codigo_variable IN ({', '.join(['?' for _ in variable_codes])})
                    GROUP BY c.id_geo, c.valor_provincia, c.valor_departamento, c.valor_fraccion
                )
                SELECT
                    {config["id_field"]} as geo_id,
                    ST_AsText(ST_MemUnion_Agg(g.geometry)) as wkt,
                    {category_select}
                FROM (
                    SELECT * FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/radios.parquet'
                    WHERE 1=1 {geo_filter} {spatial_filter_sql}
                ) g
                JOIN pivoted_census pc ON g.COD_2022 = pc.id_geo
                GROUP BY {config["group_cols"]}
            """
            query_params = list(variable_codes)
        else:
            # RADIO level (no dissolve) - simpler query
            query = f"""
                WITH pivoted_census AS (
                    SELECT
                        c.id_geo,
                        {pivot_sql}
                    FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/census-data.parquet' c
                    WHERE c.codigo_variable IN ({', '.join(['?' for _ in variable_codes])})
                    GROUP BY c.id_geo
                )
                SELECT
                    g.COD_2022 as geo_id,
                    ST_AsText(g.geometry) as wkt,
                    pc.*
                FROM (
                    SELECT * FROM 'https://data.source.coop/nlebovits/censo-argentino/2022/radios.parquet'
                    WHERE 1=1 {geo_filter} {spatial_filter_sql}
                ) g
                JOIN pivoted_census pc ON g.COD_2022 = pc.id_geo
            """
            query_params = list(variable_codes)

        # Execute query
        if progress_callback:
            progress_callback(30, "Executing DuckDB query...")

        df = con.execute(query, query_params).df()

        if progress_callback:
            progress_callback(60, f"Query returned {len(df)} rows. Building QGIS layer...")

        # Create QGIS layer with category fields
        layer = _df_to_layer_with_categories(
            df,
            variable_categories_map,
            layer_name or f"Censo {geo_level}",
            progress_callback
        )

        # Store query for debugging
        layer.setCustomProperty("censo_query", query)

        if progress_callback:
            progress_callback(100, "Layer loaded successfully!")

        return layer

    except Exception as e:
        if progress_callback:
            progress_callback(0, f"Error: {str(e)}")
        raise
```

### 1.6 Update Layer Creation with Category Fields

**File:** `query.py` (new function around line 550)

```python
def _df_to_layer_with_categories(df, variable_categories_map, layer_name, progress_callback=None):
    """
    Convert DataFrame with category columns to QgsVectorLayer.

    Args:
        df: DataFrame with columns: geo_id, wkt, [category columns]
        variable_categories_map: Dict of {var_code: [(valor, etiqueta), ...]}
        layer_name: Name for the layer
        progress_callback: Optional callback

    Returns:
        QgsVectorLayer with category fields
    """
    from qgis.core import (
        QgsVectorLayer, QgsField, QgsFeature, QgsGeometry,
        QgsProject, QgsMessageLog, Qgis
    )
    from qgis.PyQt.QtCore import QVariant

    # Create memory layer
    layer = QgsVectorLayer("Polygon?crs=EPSG:4326", layer_name, "memory")
    provider = layer.dataProvider()

    # Build field list
    fields = [QgsField("geo_id", QVariant.String)]

    # Add field for each category
    for var_code, categories in variable_categories_map.items():
        for valor, etiqueta in categories:
            clean_label = sanitize_category_label(etiqueta)
            col_name = f"{var_code.lower()}_{clean_label}"

            # Store full label as field alias for readability
            field = QgsField(col_name, QVariant.Double)
            field.setAlias(f"{var_code}: {etiqueta}")
            fields.append(field)

    provider.addAttributes(fields)
    layer.updateFields()

    # Add features
    features = []
    total_rows = len(df)

    for idx, row in df.iterrows():
        feature = QgsFeature()

        # Parse geometry
        geom = QgsGeometry.fromWkt(row["wkt"])
        if geom.isNull():
            QgsMessageLog.logMessage(
                f"Invalid geometry for feature {row['geo_id']}",
                "Censo Argentino",
                Qgis.Warning
            )
            continue

        feature.setGeometry(geom)

        # Set attributes
        attributes = [row["geo_id"]]

        for var_code, categories in variable_categories_map.items():
            for valor, etiqueta in categories:
                clean_label = sanitize_category_label(etiqueta)
                col_name = f"{var_code.lower()}_{clean_label}"

                val = row.get(col_name)
                # Handle NaN/NULL properly
                if val is not None and str(val) != "nan":
                    attributes.append(float(val))
                else:
                    attributes.append(None)

        feature.setAttributes(attributes)
        features.append(feature)

        # Update progress
        if progress_callback and (idx % 50 == 0 or idx == total_rows - 1):
            percent = 75 + int((idx / total_rows) * 20)
            progress_callback(percent, f"Processing features: {idx + 1}/{total_rows}")

    provider.addFeatures(features)
    layer.updateExtents()

    if progress_callback:
        progress_callback(95, f"Layer created with {len(features)} features")

    return layer
```

### 1.7 Update Existing Tests

**File:** `tests/test_query_builders.py` - Modify existing test class

```python
class TestBuildPivotColumns:
    """Tests for build_pivot_columns with category expansion."""

    def test_builds_pivot_with_categories(self):
        """Should build CASE statements for each variable+category."""
        variable_categories_map = {
            'EDUCACION': [('1', 'Sin instrucción'), ('2', 'Primario completo')],
            'EDAD': [('1', '0-14 años')]
        }

        result = build_pivot_columns(['EDUCACION', 'EDAD'], variable_categories_map)

        # Check EDUCACION categories
        assert "codigo_variable = 'EDUCACION'" in result
        assert "valor_categoria = '1'" in result
        assert "educacion_sin_instru" in result
        assert "educacion_primario" in result

        # Check EDAD category
        assert "codigo_variable = 'EDAD'" in result
        assert "edad_0_14" in result

    def test_sanitizes_category_labels(self):
        """Should handle special characters in category labels."""
        variable_categories_map = {
            'TEST': [('1', 'Categoría con ñ'), ('2', '0-14 años')]
        }

        result = build_pivot_columns(['TEST'], variable_categories_map)

        # Check sanitization
        assert "test_categoria" in result  # removed accent and ñ
        assert "test_0_14" in result  # handled leading digit

    def test_empty_categories(self):
        """Should handle variables with no categories."""
        variable_categories_map = {'VAR1': []}

        result = build_pivot_columns(['VAR1'], variable_categories_map)

        assert result == ""  # No columns if no categories
```

### 1.8 Add Integration Tests

**File:** `tests/test_census_integration.py` (new file)

```python
"""Integration tests for census data loading with category expansion."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock QGIS modules
sys.modules["qgis"] = MagicMock()
sys.modules["qgis.core"] = MagicMock()
sys.modules["qgis.PyQt"] = MagicMock()
sys.modules["qgis.PyQt.QtCore"] = MagicMock()

from query import get_variable_categories, sanitize_category_label


class TestGetVariableCategories:
    """Test category fetching from census data."""

    @pytest.mark.integration
    def test_fetches_real_categories(self):
        """Should fetch actual categories from Source.Coop (requires network)."""
        # This test requires network access and DuckDB
        categories = get_variable_categories('EDUCACION')

        assert len(categories) > 0
        assert all(isinstance(cat, tuple) and len(cat) == 2 for cat in categories)

        # Check structure: (valor, etiqueta)
        valor, etiqueta = categories[0]
        assert isinstance(valor, str)
        assert isinstance(etiqueta, str)

    def test_caches_categories(self, temp_cache_dir):
        """Should cache categories to avoid repeated queries."""
        with patch('query.get_cache_dir', return_value=temp_cache_dir):
            # First call - fetches from network
            categories1 = get_variable_categories('TEST_VAR')

            # Second call - should use cache
            categories2 = get_variable_categories('TEST_VAR')

            assert categories1 == categories2


class TestSanitizeCategoryLabel:
    """Test field name sanitization."""

    def test_removes_accents(self):
        """Should remove Spanish accents and tildes."""
        assert sanitize_category_label("Educación") == "educacion"
        assert sanitize_category_label("Año") == "ano"

    def test_handles_leading_digits(self):
        """Should prefix with 'c_' if starts with digit."""
        assert sanitize_category_label("0-14 años") == "c_0_14_ano"
        assert sanitize_category_label("65+") == "c_65"

    def test_truncates_long_names(self):
        """Should truncate to 10 characters for shapefile compatibility."""
        long_name = "Very Long Category Name"
        result = sanitize_category_label(long_name, max_length=10)
        assert len(result) == 10
        assert result == "very_long_"

    def test_replaces_spaces_with_underscores(self):
        """Should convert spaces to underscores."""
        assert sanitize_category_label("Sin instrucción") == "sin_instru"

    def test_removes_special_characters(self):
        """Should remove non-alphanumeric except underscores."""
        assert sanitize_category_label("A-B/C (D)") == "a_b_c_d"


class TestCensusAggregation:
    """Test that aggregation doesn't inflate totals."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_no_cartesian_product_inflation(self):
        """
        Verify aggregated totals match sum of constituent parts.
        This is the critical test for the cartesian product bug fix.
        """
        # Load at RADIO level (no dissolve)
        layer_radio = load_census_layer(
            variable_codes=['POB_TOT_P'],
            geo_level='RADIO',
            geo_filters=['02-007']  # Single FRACC
        )

        # Sum totals from all radios
        radio_total = sum(
            f['pob_tot_p'] for f in layer_radio.getFeatures()
            if f['pob_tot_p'] is not None
        )

        # Load at FRACC level (with dissolve)
        layer_fracc = load_census_layer(
            variable_codes=['POB_TOT_P'],
            geo_level='FRACC',
            geo_filters=['02-007']
        )

        # Should have exactly 1 feature
        fracc_features = list(layer_fracc.getFeatures())
        assert len(fracc_features) == 1

        fracc_total = fracc_features[0]['pob_tot_p']

        # Totals MUST match (within floating point tolerance)
        assert abs(radio_total - fracc_total) < 0.01, \
            f"Totals don't match! RADIO sum={radio_total}, FRACC={fracc_total}"

    @pytest.mark.integration
    def test_multiple_variables_no_duplication(self):
        """Verify multiple variables don't create cartesian products."""
        layer = load_census_layer(
            variable_codes=['EDUCACION', 'EDAD'],
            geo_level='DEPTO',
            geo_filters=['02-007']
        )

        features = list(layer.getFeatures())

        # Should have exactly 1 feature (1 department)
        assert len(features) == 1

        # Check that all category columns exist
        field_names = [f.name() for f in layer.fields()]
        assert 'educacion_sin_instru' in field_names
        assert 'edad_0_14' in field_names

        # Check no NULL geo_id (indicates join issues)
        assert features[0]['geo_id'] is not None
```

### 1.9 Migration Notes

**Breaking Changes:**

1. **Column Structure Changed:**
   - **Old:** Single column per variable (e.g., `EDUCACION`)
   - **New:** Multiple columns per variable (e.g., `educacion_sin_instruccion`, `educacion_primario_completo`)

2. **Field Naming Convention:**
   - **Format:** `{variable_code}_{sanitized_category_label}`
   - **Example:** `EDUCACION: Sin instrucción` → `educacion_sin_instruccion`
   - **Length:** Full category names (no truncation)
   - **⚠️ Shapefile Compatibility:** Shapefiles have a 10-character field name limit and will truncate names. We recommend exporting to **GeoPackage** or **GeoParquet** instead.

3. **Impact on Existing Users:**
   - Saved QGIS styles referencing old column names will break
   - Field calculator expressions need updating
   - Symbology based on variable totals won't work

**Backward Compatibility Strategy:**

Option A: **Add toggle in UI** (for Phase 2)
```
☐ Expand categories (new behavior)
☑ Variable totals only (old behavior)
```

Option B: **Auto-detect and warn**
```python
# If variable has categories, show warning
if has_categories:
    QMessageBox.warning(
        "Category Expansion",
        "This variable has categories that will be expanded into separate columns. "
        "Old saved styles may not work."
    )
```

**Recommended:** Implement Option A in Phase 2 UI work.

---

## Phase 2: Add Category Selection UI (Future Enhancement)

### 2.1 UI Design Options

**Option A: Two-Level Selection (Simpler)**

```
Variables:
☑ EDUCACION

Categories for EDUCACION:
☑ Auto-expand all categories (default)
☐ Select specific:
  ☑ Sin instrucción
  ☑ Primario completo
  ☐ Secundario incompleto
```

**Option B: Tree Widget (Better UX)** ⭐ **Recommended**

```
▼ ☑ EDUCACION (all categories)
  ├─ ☑ Sin instrucción
  ├─ ☑ Primario incompleto
  ├─ ☑ Primario completo
  └─ ☐ Secundario completo
▼ ☑ EDAD (all categories)
  ├─ ☑ 0-14 años
  ├─ ☑ 15-64 años
  └─ ☑ 65+ años
```

### 2.2 Backend Updates for Category Filtering

**Modify `load_census_layer` signature:**

```python
def load_census_layer(
    variable_codes,
    categories=None,  # NEW: Dict: {var_code: [cat_valores]} or None for all
    geo_level="RADIO",
    geo_filters=None,
    spatial_filter=None,
    layer_name=None,
    progress_callback=None,
):
    """
    Load census data with optional category filtering.

    Args:
        categories: Optional dict specifying which categories to load per variable
            Example: {'EDUCACION': ['1', '2'], 'EDAD': None}  # None = all categories
            If None, loads all categories for all variables (default behavior)
    """
```

**Query modification:**

```python
# In CTE WHERE clause
if categories:
    # Build category filter
    category_filters = []
    for var_code in variable_codes:
        selected_cats = categories.get(var_code)
        if selected_cats is None:
            # Load all categories for this variable
            category_filters.append(f"codigo_variable = '{var_code}'")
        else:
            # Load only selected categories
            cat_list = ", ".join([f"'{c}'" for c in selected_cats])
            category_filters.append(
                f"(codigo_variable = '{var_code}' AND valor_categoria IN ({cat_list}))"
            )

    category_where = " OR ".join(category_filters)
    query = f"... WHERE ({category_where}) ..."
else:
    # Default: load all categories
    query = f"... WHERE codigo_variable IN (...) ..."
```

### 2.3 UI Implementation (PyQt5)

**File:** `dialog.ui` - Add QTreeWidget to Browse tab

**File:** `dialog.py` - Add tree widget logic

```python
def setup_category_tree(self):
    """Initialize category tree widget."""
    self.treeCategories = QtWidgets.QTreeWidget()
    self.treeCategories.setHeaderLabels(["Variable / Category", "Description"])
    self.treeCategories.setColumnWidth(0, 250)
    self.treeCategories.itemChanged.connect(self.on_category_item_changed)

    # Add to layout
    self.verticalLayout.insertWidget(3, self.treeCategories)

def populate_category_tree(self, variable_codes):
    """Populate tree with variables and their categories."""
    self.treeCategories.clear()
    self.treeCategories.blockSignals(True)

    try:
        for var_code in variable_codes:
            # Fetch categories
            categories = get_variable_categories(var_code)

            # Create root item for variable
            var_item = QtWidgets.QTreeWidgetItem(
                self.treeCategories,
                [var_code, f"{len(categories)} categories"]
            )
            var_item.setFlags(var_item.flags() | Qt.ItemIsUserCheckable)
            var_item.setCheckState(0, Qt.Checked)  # All checked by default
            var_item.setData(0, Qt.UserRole, {"type": "variable", "code": var_code})

            # Add category children
            for valor, etiqueta in categories:
                cat_item = QtWidgets.QTreeWidgetItem(var_item, [etiqueta, f"Code: {valor}"])
                cat_item.setFlags(cat_item.flags() | Qt.ItemIsUserCheckable)
                cat_item.setCheckState(0, Qt.Checked)
                cat_item.setData(0, Qt.UserRole, {
                    "type": "category",
                    "var_code": var_code,
                    "valor": valor
                })

        self.treeCategories.expandAll()
    finally:
        self.treeCategories.blockSignals(False)

def on_category_item_changed(self, item, column):
    """Handle checkbox state changes with parent/child propagation."""
    if column != 0:
        return

    self.treeCategories.blockSignals(True)

    try:
        item_data = item.data(0, Qt.UserRole)

        if item_data["type"] == "variable":
            # Parent changed - update all children
            check_state = item.checkState(0)
            for i in range(item.childCount()):
                child = item.child(i)
                child.setCheckState(0, check_state)

        elif item_data["type"] == "category":
            # Child changed - update parent state
            parent = item.parent()
            self.update_parent_check_state(parent)
    finally:
        self.treeCategories.blockSignals(False)

def update_parent_check_state(self, parent):
    """Set parent to partial if some children checked."""
    if not parent:
        return

    checked_count = 0
    total_count = parent.childCount()

    for i in range(total_count):
        if parent.child(i).checkState(0) == Qt.Checked:
            checked_count += 1

    if checked_count == 0:
        parent.setCheckState(0, Qt.Unchecked)
    elif checked_count == total_count:
        parent.setCheckState(0, Qt.Checked)
    else:
        parent.setCheckState(0, Qt.PartiallyChecked)

def get_selected_categories(self):
    """
    Extract selected categories from tree.

    Returns:
        Dict: {var_code: [list of valor_categoria]} or None if all selected
    """
    categories = {}

    for i in range(self.treeCategories.topLevelItemCount()):
        var_item = self.treeCategories.topLevelItem(i)
        var_data = var_item.data(0, Qt.UserRole)
        var_code = var_data["code"]

        # Check if all categories selected (default behavior)
        all_checked = var_item.checkState(0) == Qt.Checked

        if all_checked:
            categories[var_code] = None  # None = all categories
        else:
            # Get specific selected categories
            selected = []
            for j in range(var_item.childCount()):
                cat_item = var_item.child(j)
                if cat_item.checkState(0) == Qt.Checked:
                    cat_data = cat_item.data(0, Qt.UserRole)
                    selected.append(cat_data["valor"])

            categories[var_code] = selected if selected else None

    # If all variables have all categories, return None (simplifies query)
    if all(v is None for v in categories.values()):
        return None

    return categories
```

---

## Testing Plan

### Phase 1 Tests

#### Test 1: Single Variable, Single Geography
**Objective:** Verify category expansion works for basic case

```python
def test_single_variable_fracc():
    """Select EDUCACION for one FRACC, verify all categories appear."""
    layer = load_census_layer(
        variable_codes=['EDUCACION'],
        geo_level='FRACC',
        geo_filters=['02-007-01']
    )

    # Check field names
    field_names = [f.name() for f in layer.fields()]
    assert 'educacion_sin_instru' in field_names
    assert 'educacion_primario' in field_names

    # Verify totals are reasonable (no inflation)
    features = list(layer.getFeatures())
    assert len(features) == 1

    # Sum all education categories
    total = sum(
        features[0][fname] or 0
        for fname in field_names
        if fname.startswith('educacion_')
    )
    assert total > 0  # Should have some population
```

#### Test 2: Multiple Variables, Aggregated Geography
**Objective:** Ensure no cartesian product duplication

```python
def test_multiple_vars_depto_no_inflation():
    """Select EDUCACION + EDAD at DEPTO, verify no duplication."""
    # Load at RADIO level first
    layer_radio = load_census_layer(
        variable_codes=['EDUCACION', 'EDAD'],
        geo_level='RADIO',
        geo_filters=['02-007']  # All radios in one DEPTO
    )

    # Sum education categories across all radios
    radio_edu_total = 0
    for feature in layer_radio.getFeatures():
        for field in layer_radio.fields():
            if field.name().startswith('educacion_'):
                val = feature[field.name()]
                if val is not None:
                    radio_edu_total += val

    # Load at DEPTO level
    layer_depto = load_census_layer(
        variable_codes=['EDUCACION', 'EDAD'],
        geo_level='DEPTO',
        geo_filters=['02-007']
    )

    # Should have exactly 1 feature
    depto_features = list(layer_depto.getFeatures())
    assert len(depto_features) == 1

    # Sum education categories at DEPTO level
    depto_edu_total = 0
    for field in layer_depto.fields():
        if field.name().startswith('educacion_'):
            val = depto_features[0][field.name()]
            if val is not None:
                depto_edu_total += val

    # Totals MUST match (no inflation from cartesian product)
    assert abs(radio_edu_total - depto_edu_total) < 0.01, \
        f"Education totals don't match! RADIO={radio_edu_total}, DEPTO={depto_edu_total}"
```

#### Test 3: Edge Cases

```python
def test_variable_with_null_categories():
    """Handle variables where some records have NULL categories."""
    # Some variables may have NULL valor_categoria
    layer = load_census_layer(
        variable_codes=['VAR_WITH_NULLS'],
        geo_level='RADIO',
        geo_filters=['02-007-01-001']
    )

    # Should still load without errors
    assert layer.featureCount() > 0

def test_large_category_set():
    """Test performance with variable having 50+ categories."""
    # Some variables have many categories
    layer = load_census_layer(
        variable_codes=['VAR_MANY_CATEGORIES'],
        geo_level='PROV',
        geo_filters=['02']
    )

    # Should complete in reasonable time (<30 seconds)
    # Check all category columns present
    field_count = len([f for f in layer.fields() if f.name() != 'geo_id'])
    assert field_count > 50
```

#### Test 4: Performance

```python
def test_full_province_performance():
    """Test with full province (thousands of radios)."""
    import time

    start = time.time()
    layer = load_census_layer(
        variable_codes=['EDUCACION', 'EDAD', 'SEXO'],
        geo_level='RADIO',
        geo_filters=['06']  # Entire Buenos Aires province
    )
    elapsed = time.time() - start

    print(f"Loaded {layer.featureCount()} features in {elapsed:.2f}s")

    # Should complete in under 60 seconds
    assert elapsed < 60, f"Query too slow: {elapsed:.2f}s"
```

### Phase 2 Tests

#### Test 5: Category Filtering

```python
def test_select_specific_categories():
    """Select only 2 categories from EDUCACION (6 total)."""
    layer = load_census_layer(
        variable_codes=['EDUCACION'],
        categories={'EDUCACION': ['1', '2']},  # Only first 2 categories
        geo_level='FRACC',
        geo_filters=['02-007-01']
    )

    # Should have exactly 2 education columns (plus geo_id)
    edu_fields = [f for f in layer.fields() if f.name().startswith('educacion_')]
    assert len(edu_fields) == 2

def test_mixed_category_selection():
    """All categories for EDUCACION, specific for EDAD."""
    layer = load_census_layer(
        variable_codes=['EDUCACION', 'EDAD'],
        categories={
            'EDUCACION': None,  # All categories
            'EDAD': ['1', '2']  # Only 0-14 and 15-64
        },
        geo_level='DEPTO',
        geo_filters=['02-007']
    )

    # Check EDUCACION has all categories
    edu_fields = [f for f in layer.fields() if f.name().startswith('educacion_')]
    assert len(edu_fields) > 2  # Should have all (e.g., 6)

    # Check EDAD has only 2
    edad_fields = [f for f in layer.fields() if f.name().startswith('edad_')]
    assert len(edad_fields) == 2
```

---

## Acceptance Criteria

### Phase 1 (Must Complete)

- [ ] Aggregated totals match expected values (no inflation)
- [ ] Each category appears as separate column with meaningful name
- [ ] Column names are valid QGIS field names (full length, no special chars)
- [ ] Column names follow pattern: `{var_code}_{sanitized_category_full_name}`
- [ ] NULL categories handled: dynamic `{var_code}_null` column only if NULL rows exist
- [ ] Empty category lists handled: single total column for variables without categories
- [ ] Works for all geo levels (RADIO, FRACC, DEPTO, PROV)
- [ ] Field aliases show full category labels for readability
- [ ] Category fetch failures: retry 3 times, then skip with warning dialog
- [ ] Column count limits: warn at 50, block at 100 with helpful message
- [ ] Performance acceptable (<10s for DEPTO-level query, <60s for PROV)
- [ ] Existing tests pass with updated logic
- [ ] New integration tests verify no cartesian products
- [ ] Category metadata cached like variable metadata
- [ ] NULL/NaN values handled correctly (as NULL, not 0)
- [ ] Documentation includes shapefile export warning and GeoPackage recommendation

### Phase 2 (Optional Enhancement)

- [ ] UI allows category selection per variable (tree widget)
- [ ] "Select all" checkbox works correctly (parent/child propagation)
- [ ] Only selected categories appear in output layer
- [ ] Category selection persists when switching variables
- [ ] Clear visual indication of selection state (checked/partial/unchecked)
- [ ] "Auto-expand all" remains default behavior
- [ ] Category tree loads asynchronously with progress updates

---

## Success Metrics

### Data Integrity
- **Zero inflation:** FRACC/DEPTO/PROV totals = sum of constituent RADIO totals
- **Complete data:** All categories from source data appear in output
- **Null handling:** NULL categories don't crash or create invalid data

### Performance
- **RADIO query:** <5 seconds for single FRACC (~50 radios)
- **FRACC query:** <10 seconds for single DEPTO (~20 fracciones)
- **DEPTO query:** <30 seconds for single PROV (~100+ departments)
- **PROV query:** <60 seconds for entire province (thousands of radios)

### Usability
- **Field names readable:** Sanitized but recognizable (e.g., `educacion_primario`)
- **Field aliases descriptive:** Full label shown in attribute table
- **Column count manageable:** <50 columns for typical 3-variable query
- **Progress feedback:** Updates every 1-2 seconds during long queries

---

## Dependencies & Risks

### Dependencies

- **DuckDB 0.9.0+:** Required for `ST_MemUnion_Agg` and remote Parquet queries
- **QGIS 3.0+:** Memory layer API, QgsField, QgsGeometry
- **PyQt5:** For UI components (Phase 2)
- **Network access:** Remote Parquet files on Source.Coop

### Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Column count explosion (60+ columns) | Medium | Medium | Document expected column counts, warn users, implement Phase 2 filtering |
| Field name truncation causes collisions | Low | Medium | Smart truncation algorithm, add numeric suffix if collision detected |
| Performance degradation with many categories | Medium | High | Use ST_MemUnion_Agg, optimize CTE, add progress feedback, test with full province |
| Breaking existing saved styles | High | Low | Document migration, consider adding backward compatibility toggle |
| Cache invalidation issues | Low | Low | Include variable+category count in cache key |
| NULL category handling edge cases | Medium | Medium | Comprehensive NULL testing, filter NULL categories in query |

### Contingency Plans

**If column count becomes unmanageable:**
- Implement Phase 2 category filtering sooner
- Add UI warning when >40 columns expected
- Provide option to aggregate categories (e.g., "Primary" = Primary Complete + Primary Incomplete)

**If performance issues persist:**
- Add query timeout configuration
- Implement progressive loading (load radios first, then aggregate)
- Cache dissolved geometries for frequently-used geographic levels

**If field name collisions occur:**
- Add numeric suffix: `educacion_1`, `educacion_2`
- Increase max length to 15 chars (compromise between readability and compatibility)

---

## Migration Notes

### For Users

**What's Changing:**
- Census layers now have many more columns (one per category instead of one per variable)
- Column names are shorter and sanitized for compatibility
- Totals must be calculated by summing category columns

**Migration Steps:**
1. Update saved QGIS styles to use new column names
2. Update field calculator expressions that reference variable columns
3. Update symbology rules that filter on variable values
4. Re-create any layer joins that depend on old column names

**Example Migration:**

**Old Style (v0.3.1 and earlier):**
```
Column: EDUCACION (single column with total)
Expression: "EDUCACION" > 1000
```

**New Style (v0.4.0+):**
```
Columns: educacion_sin_instru, educacion_primario, educacion_secundario, ...
Expression: "educacion_sin_instru" + "educacion_primario" + ... > 1000
```

### For Developers

**API Changes:**

**Old:**
```python
layer = load_census_layer(
    variable_codes=['EDUCACION'],
    geo_level='FRACC'
)
# Returns layer with column: EDUCACION
```

**New:**
```python
layer = load_census_layer(
    variable_codes=['EDUCACION'],
    geo_level='FRACC'
)
# Returns layer with columns: educacion_sin_instru, educacion_primario, ...
```

**Phase 2 API (future):**
```python
layer = load_census_layer(
    variable_codes=['EDUCACION'],
    categories={'EDUCACION': ['1', '2']},  # Optional filtering
    geo_level='FRACC'
)
```

---

## Related Issues

- **Data documentation:** Add schema details to `docs/desarrollo.md` (mention `valor_categoria`, `etiqueta_categoria`)
- **Category caching:** Implement caching like `get_variables()` to avoid repeated queries
- **Column naming convention:** Document in user guide with examples
- **Error handling:** Improve error messages when categories can't be fetched
- **SQL mode compatibility:** Update `run_custom_query()` to support dynamic PIVOT if users write raw SQL

---

## Implementation Priority

| Phase | Priority | Rationale |
|-------|----------|-----------|
| Phase 1: Fix Aggregation + Auto-Expand | **HIGH** | Critical data accuracy bug affecting all aggregated queries |
| Phase 2: Category Selection UI | **MEDIUM** | UX improvement, not blocking functionality |

**Recommended Order:**
1. Implement Phase 1 core functionality (6-8 hours)
2. Write and run comprehensive tests (2-3 hours)
3. Update documentation with examples (1-2 hours)
4. **Release v0.4.0 with Phase 1 changes**
5. Gather user feedback on column counts and usability
6. Implement Phase 2 if column explosion becomes an issue (8-10 hours)

---

## Questions for Discussion

1. **Column count concerns:** Some variables may have 20+ categories. Loading 3 variables = 60+ columns. Is this acceptable for users?
   - **Recommendation:** Start with Phase 1 (auto-expand all), monitor user feedback, implement Phase 2 if needed

2. **Performance:** Should we add row/column limits or warnings?
   - **Recommendation:** Add warning if >40 columns expected, suggest using fewer variables or implementing Phase 2 filtering

3. **Default behavior:** Should "auto-expand" be opt-in or opt-out?
   - **Recommendation:** Opt-out (auto-expand by default) for data integrity, add "variable totals only" option later if needed

4. **Column naming:** Prefer `var_category` or `var_#_category` (include category code)?
   - **Recommendation:** Use `var_category` (more readable), store category code in field alias for reference

5. **Backward compatibility:** Should we maintain old behavior as option?
   - **Recommendation:** No for Phase 1 (too complex), document migration clearly, add toggle in Phase 2 if users strongly request it

---

## References & Research

### Internal References
- **Current implementation:** `query.py:249-400` (load_census_layer)
- **Query builders:** `query_builders.py:75-88` (build_pivot_columns)
- **Field creation:** `query.py:482-488` (QgsField setup)
- **Test patterns:** `tests/test_query_builders.py` (26 existing tests)
- **Cache implementation:** `query.py:45-74` (cache management)
- **Connection pooling:** `query.py:9-42` (DuckDBConnectionPool)

### External References
- **DuckDB CTE patterns:** https://duckdb.org/docs/sql/query_syntax/with.html
- **DuckDB PIVOT syntax:** https://duckdb.org/docs/sql/statements/pivot.html
- **DuckDB spatial functions:** https://duckdb.org/docs/extensions/spatial.html
- **QGIS field naming:** QGIS 3.x API documentation
- **PostgreSQL conventions:** https://stackoverflow.com/questions/2878248/postgresql-naming-conventions
- **SQL injection prevention:** Parameterized queries with DuckDB

### Design Decisions
- **Why CTE instead of PIVOT:** More control, explicit column names, better QGIS compatibility
- **Why ST_MemUnion_Agg:** Better memory efficiency for large aggregations (DuckDB 1.3+ best practice)
- **Why 10-char field names:** Shapefile compatibility (lowest common denominator)
- **Why auto-expand default:** Data integrity > convenience, prevents silent data loss

---

## Appendix: SQL Query Examples

### Before (Current Implementation - Has Bug)

```sql
-- Creates cartesian product when multiple variables × multiple categories
SELECT
    g.PROV || '-' || g.DEPTO || '-' || g.FRACC as geo_id,
    ST_AsText(ST_Union_Agg(g.geometry)) as wkt,
    SUM(CASE WHEN c.codigo_variable = 'EDUCACION' THEN c.conteo ELSE 0 END) as "EDUCACION",
    SUM(CASE WHEN c.codigo_variable = 'EDAD' THEN c.conteo ELSE 0 END) as "EDAD"
FROM (
    SELECT * FROM 'radios.parquet'
    WHERE PROV = '02'
) g
JOIN 'census-data.parquet' c
    ON g.COD_2022 = c.id_geo
WHERE c.codigo_variable IN ('EDUCACION', 'EDAD')
GROUP BY g.PROV, g.DEPTO, g.FRACC
```

**Problem:** Each radio joins with N categories × M variables, creating N×M rows per radio before GROUP BY.

### After (Phase 1 - Fixed)

```sql
-- CTE pivots first, creating 1:1 join
WITH pivoted_census AS (
    SELECT
        c.id_geo,
        c.valor_provincia,
        c.valor_departamento,
        c.valor_fraccion,
        SUM(CASE WHEN codigo_variable = 'EDUCACION' AND valor_categoria = '1' THEN conteo ELSE 0 END) as "educacion_sin_instru",
        SUM(CASE WHEN codigo_variable = 'EDUCACION' AND valor_categoria = '2' THEN conteo ELSE 0 END) as "educacion_primario",
        SUM(CASE WHEN codigo_variable = 'EDAD' AND valor_categoria = '1' THEN conteo ELSE 0 END) as "edad_0_14",
        SUM(CASE WHEN codigo_variable = 'EDAD' AND valor_categoria = '2' THEN conteo ELSE 0 END) as "edad_15_64"
    FROM 'census-data.parquet' c
    WHERE c.codigo_variable IN ('EDUCACION', 'EDAD')
    GROUP BY c.id_geo, c.valor_provincia, c.valor_departamento, c.valor_fraccion
)
SELECT
    g.PROV || '-' || g.DEPTO || '-' || g.FRACC as geo_id,
    ST_AsText(ST_MemUnion_Agg(g.geometry)) as wkt,
    SUM(pc.educacion_sin_instru) as educacion_sin_instru,
    SUM(pc.educacion_primario) as educacion_primario,
    SUM(pc.edad_0_14) as edad_0_14,
    SUM(pc.edad_15_64) as edad_15_64
FROM radios.parquet g
JOIN pivoted_census pc ON g.COD_2022 = pc.id_geo
WHERE g.PROV = '02'
GROUP BY g.PROV, g.DEPTO, g.FRACC
```

**Solution:** Each radio now has exactly 1 row in `pivoted_census` before joining with geometry. No cartesian product.

---

**Plan Status:** Ready for Implementation
**Next Steps:** Present plan to user, run /deepen-plan or /plan_review, or start /workflows:work
