"""Funciones de construcción de consultas extraídas de query.py para facilitar pruebas."""


def build_geo_filter(geo_level, geo_filters):
    """
    Construir fragmento SQL de filtro geográfico y parámetros de consulta.

    Args:
        geo_level: Nivel geográfico ('PROV', 'DEPTO', 'FRACC', 'RADIO')
        geo_filters: Lista de códigos de filtro geográfico

    Returns:
        tuple: (fragmento_sql_filtro, lista_parámetros)
            fragmento_sql_filtro será string vacío si no hay filtros
            lista_parámetros contiene valores a vincular a placeholders
    """
    if not geo_filters or len(geo_filters) == 0:
        return "", []

    query_params = []
    geo_filter = ""

    if geo_level == "PROV":
        placeholders = ", ".join(["?" for _ in geo_filters])
        geo_filter = f" AND PROV IN ({placeholders})"
        query_params.extend(geo_filters)

    elif geo_level == "DEPTO":
        # Parse "PROV-DEPTO" format
        filter_conditions = []
        for gf in geo_filters:
            parts = gf.split("-")
            if len(parts) == 2:
                filter_conditions.append("(PROV = ? AND DEPTO = ?)")
                query_params.extend(parts)
        if filter_conditions:
            geo_filter = f" AND ({' OR '.join(filter_conditions)})"

    elif geo_level == "FRACC":
        # Parse "PROV-DEPTO-FRACC" format
        filter_conditions = []
        for gf in geo_filters:
            parts = gf.split("-")
            if len(parts) == 3:
                filter_conditions.append("(PROV = ? AND DEPTO = ? AND FRACC = ?)")
                query_params.extend(parts)
        if filter_conditions:
            geo_filter = f" AND ({' OR '.join(filter_conditions)})"

    elif geo_level == "RADIO":
        placeholders = ", ".join(["?" for _ in geo_filters])
        geo_filter = f" AND COD_2022 IN ({placeholders})"
        query_params.extend(geo_filters)

    return geo_filter, query_params


def build_spatial_filter(bbox):
    """
    Construir fragmento SQL de filtro de bounding box espacial.

    Args:
        bbox: Tupla de (xmin, ymin, xmax, ymax) en EPSG:4326

    Returns:
        str: Fragmento SQL con condición ST_Intersects, o string vacío si bbox es None
    """
    if not bbox:
        return ""

    xmin, ymin, xmax, ymax = bbox
    # DuckDB spatial doesn't support SRID parameter in ST_GeomFromText
    bbox_wkt = (
        f"POLYGON(({xmin} {ymin}, {xmax} {ymin}, {xmax} {ymax}, {xmin} {ymax}, {xmin} {ymin}))"
    )
    return f" AND ST_Intersects(geometry, ST_GeomFromText('{bbox_wkt}'))"


def build_pivot_columns(variable_codes, variable_categories_map):
    """
    Construir lista de columnas SQL para pivotar variables del censo con categorías.
    Incluye columnas de categoría NULL cuando sea aplicable (DECISIÓN DE DISEÑO #3).

    Args:
        variable_codes: Lista de strings de códigos de variable (ej., ['EDUCACION', 'EDAD'])
        variable_categories_map: Dict mapeando var_code a dicts de resultado
            Ejemplo: {
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
        str: Definiciones de columnas SQL separadas por comas para pivoteo CTE

    Ejemplo de salida:
        "SUM(CASE WHEN codigo_variable = 'EDUCACION' AND valor_categoria = '1'
              THEN conteo ELSE 0 END) as \"educacion_sin_instruccion\",
         SUM(CASE WHEN codigo_variable = 'EDUCACION' AND valor_categoria = '2'
              THEN conteo ELSE 0 END) as \"educacion_primario_incompleto\",
         SUM(CASE WHEN codigo_variable = 'EDUCACION' AND valor_categoria IS NULL
              THEN conteo ELSE 0 END) as \"educacion_null\""
    """
    # Try to import sanitize_category_label
    try:
        from query import sanitize_category_label
    except ImportError:
        # Fallback if query module not available (for testing)
        import re
        import unicodedata

        def sanitize_category_label(label):
            if not label:
                return "unknown"
            label = unicodedata.normalize("NFKD", label).encode("ASCII", "ignore").decode()
            label = label.lower()
            label = label.replace(" ", "_").replace("-", "_").replace("/", "_")
            label = re.sub(r"[^a-z0-9_]", "", label)
            label = re.sub(r"_+", "_", label)
            label = label.strip("_")
            if label and label[0].isdigit():
                label = "cat_" + label
            return label or "unknown"

    pivot_cols = []

    for var_code in variable_codes:
        cat_data = variable_categories_map.get(var_code, {"categories": [], "has_nulls": False})
        categories = cat_data["categories"]
        has_nulls = cat_data["has_nulls"]

        # DESIGN DECISION #5: Handle empty category lists (total-only variables)
        if not categories and not has_nulls:
            # No categories - create single total column (fallback behavior)
            col_name = f"{var_code.lower()}_total"
            case_stmt = (
                f"SUM(CASE WHEN codigo_variable = '{var_code}' "
                f'THEN conteo ELSE 0 END) as "{col_name}"'
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
                f'THEN conteo ELSE 0 END) as "{col_name}"'
            )
            pivot_cols.append(case_stmt)

        # DESIGN DECISION #3: Add NULL category column if exists
        if has_nulls:
            col_name = f"{var_code.lower()}_null"
            case_stmt = (
                f"SUM(CASE WHEN codigo_variable = '{var_code}' "
                f"AND valor_categoria IS NULL "
                f'THEN conteo ELSE 0 END) as "{col_name}"'
            )
            pivot_cols.append(case_stmt)

        # Add total column for this variable (sum of all categories including NULLs)
        col_name = f"{var_code.lower()}_total"
        case_stmt = (
            f"SUM(CASE WHEN codigo_variable = '{var_code}' "
            f'THEN conteo ELSE 0 END) as "{col_name}"'
        )
        pivot_cols.append(case_stmt)

    return ",\n        ".join(pivot_cols)
